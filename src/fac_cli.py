"""Maintainer CLI for canonical JSON-LD validation and OSM search inputs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.facility_data import (
    build_repository,
    new_uuid7,
    source_refresh_due,
    validate_jsonld_document,
    validate_repository,
    validate_search_document,
)

_VERIFY_RUNNING_ENV = "FAC_VERIFY_RUNNING"
_VERIFY_BASELINE_DIFF_ENV = "FAC_VERIFY_BASELINE_DIFF_SHA256"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: dict[str, Any]) -> None:
    issues = validate_search_document(document)
    if issues:
        raise ValueError("; ".join(issues))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _documents(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    result = []
    for path in sorted((root / "inputs/osm-search").rglob("*.json")):
        document = _read(path)
        if validate_search_document(document):
            raise ValueError(f"invalid search input: {path}")
        result.append((path, document))
    return result


def _synchronize_public_copy(root: Path) -> Path:
    """Validate canonical data and atomically synchronize the public copy."""
    canonical_path = build_repository(root)
    canonical_bytes = canonical_path.read_bytes()
    public_path = root / "site/places.jsonld"
    public_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{public_path.name}.",
            suffix=".tmp",
            dir=public_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            written = temporary.write(canonical_bytes)
            if written != len(canonical_bytes):
                raise OSError("could not write the complete public copy")
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, public_path)
        temporary_path = None
        return public_path
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _run_test_suite(root: Path) -> bool:
    """Run the repository test suite, avoiding recursive verify invocations."""
    environment = os.environ.copy()
    environment[_VERIFY_RUNNING_ENV] = "1"
    try:
        baseline = subprocess.run(
            ["git", "diff", "--check"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        baseline_output = baseline.stdout + baseline.stderr
        if baseline.returncode != 0:
            environment[_VERIFY_BASELINE_DIFF_ENV] = hashlib.sha256(
                baseline_output.encode()
            ).hexdigest()
    except OSError:
        pass

    try:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"python3 -m unittest discover failed: {error}")
        return False

    if result.returncode == 0:
        return True

    print("python3 -m unittest discover failed")
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)
    return False


def _run_git_diff_check(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "diff", "--check"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"git diff --check failed: {error}")
        return False

    if result.returncode == 0:
        return True

    output = result.stdout + result.stderr
    if (
        os.environ.get(_VERIFY_RUNNING_ENV) == "1"
        and os.environ.get(_VERIFY_BASELINE_DIFF_ENV)
        == hashlib.sha256(output.encode()).hexdigest()
    ):
        return True

    print("git diff --check failed")
    if output.strip():
        print(output.strip())
    return False


def _verify(root: Path) -> int:
    if os.environ.get(_VERIFY_RUNNING_ENV) != "1" and not _run_test_suite(root):
        return 1

    issues = validate_repository(root, check_public_copy=False)
    if issues:
        raise ValueError("repository / JSON-LD validation failed: " + "; ".join(issues))

    canonical_path = root / "data/places.jsonld"
    public_path = root / "site/places.jsonld"
    try:
        canonical_bytes = canonical_path.read_bytes()
        public_bytes = public_path.read_bytes()
    except OSError as error:
        raise ValueError(f"public JSON-LD copy could not be read: {error}") from error
    if canonical_bytes != public_bytes:
        raise ValueError(
            "site/places.jsonld must be byte-identical to data/places.jsonld"
        )

    return 0 if _run_git_diff_check(root) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fac",
        description="Maintain canonical JSON-LD facility data",
    )
    subs = parser.add_subparsers(dest="command", required=True)
    validate = subs.add_parser("jsonld-validate")
    validate.add_argument("path")

    build = subs.add_parser(
        "build",
        help="validate canonical data and synchronize the public JSON-LD copy",
    )
    build.add_argument("root", nargs="?", default=".")

    verify = subs.add_parser(
        "verify",
        help="run non-mutating repository and publication checks",
    )
    verify.add_argument("root", nargs="?", default=".")

    inp = subs.add_parser("in", help="maintain OSM search inputs")
    commands = inp.add_subparsers(dest="input", required=True)
    for name in ("ls", "get", "add", "set"):
        command = commands.add_parser(name)
        command.add_argument("root", nargs="?", default=".")
        if name in {"get", "set"}:
            command.add_argument("query_id")
        if name == "add":
            command.add_argument("name")
        if name in {"add", "set"}:
            command.add_argument("--name", dest="new_name")
            command.add_argument("--lon", type=float)
            command.add_argument("--lat", type=float)
            command.add_argument("--qid")
            command.add_argument("--at")

    args = parser.parse_args(argv)
    try:
        if args.command == "jsonld-validate":
            validate_jsonld_document(_read(Path(args.path)))
            return 0
        if args.command == "build":
            _synchronize_public_copy(Path(args.root).resolve())
            return 0
        if args.command == "verify":
            return _verify(Path(args.root).resolve())

        root = Path(args.root)
        documents = _documents(root)
        if args.input == "ls":
            for _, document in documents:
                for query in document["queries"]:
                    print(f"{query['name']}\n  id={query['id']}")
            return 0

        selected = [
            (path, document, query)
            for path, document in documents
            for query in document["queries"]
            if str(query.get("id")) == args.query_id
        ]
        if args.input == "get":
            if len(selected) != 1:
                raise ValueError(f"search input not found: {args.query_id}")
            print(json.dumps(selected[0][2], ensure_ascii=False, indent=2))
            return 0

        at = args.at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        source_refresh_due(None, at)
        if args.input == "add":
            if (args.lon is None) != (args.lat is None) or (
                (args.lon is not None) == (args.qid is not None)
            ):
                raise ValueError("use exactly one of --lon/--lat or --qid")
            moment = datetime.fromisoformat(at.replace("Z", "+00:00"))
            path = root / "inputs/osm-search/human" / f"{moment:%Y%m}.json"
            document = (
                copy.deepcopy(_read(path))
                if path.exists()
                else {
                    "source": {
                        "kind": "human",
                        "sourceId": None,
                        "retrievedAt": None,
                    },
                    "queries": [],
                }
            )
            query = {"id": new_uuid7(), "name": args.name}
            query.update(
                {"qid": args.qid}
                if args.qid is not None
                else {"coordinates": [args.lon, args.lat]}
            )
            document["queries"].append(query)
            _write(path, document)
            print(f"id={query['id']}")
            return 0

        if len(selected) != 1:
            raise ValueError(f"search input not found: {args.query_id}")
        path, document, query = selected[0]
        if (
            (args.lon is None) != (args.lat is None)
            or (args.lon is not None and args.qid is not None)
            or (
                args.new_name is None
                and args.lon is None
                and args.qid is None
            )
        ):
            raise ValueError("set requires --name, --lon/--lat, or --qid")
        if args.new_name is not None:
            query["name"] = args.new_name
        if args.lon is not None:
            query.update({"coordinates": [args.lon, args.lat]})
            query.pop("qid", None)
        if args.qid is not None:
            query.update({"qid": args.qid})
            query.pop("coordinates", None)
        _write(path, document)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
