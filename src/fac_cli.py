"""Maintainer CLI for canonical JSON-LD validation, OSM search inputs and associations."""
from __future__ import annotations
import argparse
import copy
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from src.commons_files import commons_file_page, commons_file_title
from src.facility_data import _image_key, _read_json, _write_json, barrier_free_webpage, load_queries, new_uuid7, validate_jsonld_document, validate_published_document, validate_search_document
from src.resolve_osm_candidates import apply_decisions, current_id, evidence_hash, hold_entry, osm_candidate, validate_hold
from src.osm_maintenance import verified_snapshot
from src import facility_categories
from src.env_utils import load_dotenv

def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, document: dict[str, Any]) -> None:
    issues=validate_search_document(document)
    if issues: raise ValueError("; ".join(issues))
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _retained_osm_snapshot(root: Path) -> tuple[set[str] | None, str | None, str | None]:
    """Return retained OSM element ids, the snapshot version, and why it is unreadable."""
    try:
        snapshot = verified_snapshot(root)
    except FileNotFoundError:
        return None, None, "保持スナップショットが無い"
    except (OSError, ValueError, KeyError):
        return None, None, "保持スナップショットが取得メタと一致しない"
    ids = {f"{element.get('type')}/{element.get('id')}" for element in snapshot.get("elements", [])}
    return ids, snapshot.get("version"), None


def _hold(root: Path, query_id: str, reason: str | None, editor: str | None, previous: str | None = None) -> None:
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason is required: pass --reason with --hold")
    if not any(query["id"] == query_id for query in load_queries(root)):
        raise ValueError(f"search input not found: {query_id}")
    document = _read_json(root / "data/places.jsonld")
    place = next((p for p in document["@graph"] if p["@id"] == f"urn:uuid:{query_id}"), None)
    if place is None:
        raise ValueError(f"place not found: {query_id}")
    editor = editor or subprocess.run(["git", "config", "--get", "user.name"], cwd=root, capture_output=True, text=True).stdout.strip()
    if not editor:
        raise ValueError("editor is required: pass --editor or set git user.name")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    entry = hold_entry(previous or current_id(place), reason.strip(), editor, now)
    issues = validate_hold(entry)
    if issues:
        raise ValueError("; ".join(issues))
    ledger = _read_json(root / "data/osm-decisions.json")
    if ledger.get("version") != 1 or not isinstance(ledger.get("facilities"), dict):
        raise ValueError("invalid OSM decision ledger")
    ledger = copy.deepcopy(ledger)
    ledger["facilities"][query_id] = entry
    place.pop("rdfs:seeAlso", None)
    categories_path = root / "data/categories.json"
    if categories_path.exists() and (root / "data/category-vocabulary.jsonld").exists():
        codes = facility_categories.load_vocabulary(root)
        categories = _read_json(categories_path)
        issues = facility_categories.validate_decisions(categories, codes)
        if issues:
            raise ValueError("; ".join(issues))
        categories["facilities"].pop(query_id, None)
        _write_json(categories_path, categories)
    validate_jsonld_document(document)
    _write_json(root / "data/osm-decisions.json", ledger)
    _write_json(root / "data/places.jsonld", document)


def _image_place(root: Path, query_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    document = _read_json(root / "data/places.jsonld")
    place = next((p for p in document["@graph"] if p.get("@id") == f"urn:uuid:{query_id}"), None)
    if place is None:
        raise ValueError(f"place not found: {query_id}")
    return document, place


def _image_set(root: Path, query_id: str, value: str) -> None:
    page = commons_file_page(value)
    document, place = _image_place(root, query_id)
    place["schema:image"] = {"@id": page}
    validate_jsonld_document(document)
    _write_json(root / "data/places.jsonld", document)
    print(f"image={page}")


def _image_clear(root: Path, query_id: str) -> None:
    document, place = _image_place(root, query_id)
    if "schema:image" not in place:
        raise ValueError(f"image not recorded: {query_id}")
    del place["schema:image"]
    validate_jsonld_document(document)
    _write_json(root / "data/places.jsonld", document)


def _image_review(root: Path) -> None:
    document = _read_json(root / "data/places.jsonld")
    validate_jsonld_document(document)
    names = {q["id"]: q["name"] for q in load_queries(root)} if (root / "inputs/facilities.json").exists() else {}
    metadata = {}
    commons_path = root / "imports/commons/raw.json"
    if commons_path.exists():
        metadata = {_image_key(key): value for key, value in (_read_json(commons_path).get("files") or {}).items()}
    for place in document["@graph"]:
        image = place.get("schema:image")
        if not isinstance(image, dict) or set(image) != {"@id"} or not isinstance(image.get("@id"), str):
            continue
        title = commons_file_title(image["@id"])
        identifier = place["@id"].removeprefix("urn:uuid:")
        name = names.get(identifier, identifier)
        meta = metadata.get(_image_key(title))
        if not isinstance(meta, dict) or not meta.get("url") or not meta.get("license"):
            print(f"unresolved {name}\n  id={identifier}\n  file={title}")
            continue
        print(f"resolved {name}\n  id={identifier}\n  file={title}\n  license={meta.get('licenseUrl') or meta['license']}")
        if meta.get("artist"):
            print(f"  artist={meta['artist']}")


def _documents(root:Path) -> list[tuple[Path,dict[str,Any]]]:
    result=[]
    path = root / "inputs/facilities.json"
    document = _read(path)
    if validate_search_document(document): raise ValueError(f"invalid search input: {path}")
    result.append((path, document))
    return result

def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(prog="fac",description="Maintain canonical JSON-LD facility data")
    subs=parser.add_subparsers(dest="command",required=True)
    validate=subs.add_parser("jsonld-validate"); validate.add_argument("path"); validate.add_argument("--published",action="store_true",help="validate the published dataset graph, which may carry derived schema:image, categories and shapes"); validate.add_argument("--vocabulary",action="store_true",help="validate the non-public category vocabulary source")
    inp=subs.add_parser("in",help="maintain OSM search inputs"); commands=inp.add_subparsers(dest="input",required=True)
    for name in ("ls","get","add","set","rm"):
        p=commands.add_parser(name); p.add_argument("root",nargs="?",default=".")
        if name in {"get","set","rm"}: p.add_argument("query_id")
        if name=="add": p.add_argument("name")
        if name in {"add","set"}:
            p.add_argument("--name",dest="new_name"); p.add_argument("--lon",type=float); p.add_argument("--lat",type=float); p.add_argument("--qid")
    assoc=subs.add_parser("assoc",help="record a survey-confirmed OSM association as a human decision")
    assoc.add_argument("root",nargs="?",default=".")
    assoc.add_argument("query_id")
    exclusive=assoc.add_mutually_exclusive_group(required=True)
    exclusive.add_argument("--osm-id")
    exclusive.add_argument("--choice",choices=("none",))
    exclusive.add_argument("--hold",action="store_true",help="defer the association until a field survey")
    assoc.add_argument("--reason",help="why the association is deferred; required with --hold")
    assoc.add_argument("--editor")
    category=subs.add_parser("category",help="maintain facility category decisions")
    commands=category.add_subparsers(dest="action",required=True)
    review=commands.add_parser("review")
    review.add_argument("root",nargs="?",default=".")
    assign=commands.add_parser("assign")
    assign.add_argument("root",nargs="?",default=".")
    assign.add_argument("query_id")
    assign.add_argument("poi_code")
    assign.add_argument("--editor")
    clear=commands.add_parser("clear")
    clear.add_argument("root",nargs="?",default=".")
    clear.add_argument("query_id")
    refresh=commands.add_parser("refresh")
    refresh.add_argument("root",nargs="?",default=".")
    refresh.add_argument("--present",action="store_true",help="present unresolved facilities as a GitHub Issue")
    link=subs.add_parser("link",help="maintain barrier-free guide webpage links of a place")
    commands=link.add_subparsers(dest="action",required=True)
    for name in ("add","rm"):
        p=commands.add_parser(name)
        p.add_argument("root",nargs="?",default=".")
        p.add_argument("place_id")
        p.add_argument("url")
    image=subs.add_parser("image",help="maintain the curated Commons image reference of a place")
    commands=image.add_subparsers(dest="action",required=True)
    image_set=commands.add_parser("set")
    image_set.add_argument("root",nargs="?",default=".")
    image_set.add_argument("query_id")
    image_set.add_argument("file")
    image_clear=commands.add_parser("clear")
    image_clear.add_argument("root",nargs="?",default=".")
    image_clear.add_argument("query_id")
    image_review=commands.add_parser("review")
    image_review.add_argument("root",nargs="?",default=".")
    args=parser.parse_args(argv)
    load_dotenv(getattr(args, "root", "."))
    try:
        if args.command=="jsonld-validate":
            document=_read(Path(args.path))
            if args.vocabulary:
                from src.facility_categories import validate_vocabulary
                validate_vocabulary(document)
                return 0
            (validate_published_document if args.published else validate_jsonld_document)(document)
            return 0
        if args.command=="category":
            root=Path(args.root)
            if args.action=="review":
                report=facility_categories.review(root)
                for entry in report["decided"]:
                    print(f"decided {entry['method']} {entry['category']} {entry['name']}\n  id={entry['id']}")
                for entry in report["divergent"]:
                    print(f"divergent stored={entry['stored']} proposal={entry['proposal']} {entry['name']}\n  id={entry['id']}")
                for uuid in report["stale"]:
                    print(f"stale id={uuid}")
                for entry in report["uncategorized"]:
                    proposal=f" proposal={entry['proposal']}" if entry["proposal"] else ""
                    print(f"unresolved{proposal} {entry['name']}\n  id={entry['id']}")
                for entry in report["held"]:
                    print(f"held {entry['name']}\n  id={entry['id']}\n  reason={entry['reason']}")
                return 0
            if args.action=="assign":
                editor=args.editor or subprocess.run(["git","config","--get","user.name"],cwd=root,capture_output=True,text=True).stdout.strip()
                facility_categories.assign(root,args.query_id,args.poi_code,editor)
                return 0
            if args.action=="clear":
                facility_categories.clear(root,args.query_id)
                return 0
            if args.action=="refresh":
                judge=facility_categories._request_category if os.environ.get("TYPESAFE_API_KEY") else None
                document,report=facility_categories.refresh(root,judge=judge)
                if judge is None and report["pending"]:
                    print("NOTICE: TYPESAFE_API_KEY is not set; Jev judging skipped")
                for uuid,result in report["unresolved"].items():
                    print(f"unresolved confidence={result['confidence']:.4f} id={uuid}")
                for uuid in report["stale"]:
                    print(f"re-evaluated id={uuid}")
                if args.present:
                    from src.github_osm_review import GitHub
                    GitHub().save_category_review(facility_categories.unresolved_facilities(root, document))
                return 0
        if args.command=="link":
            root=Path(args.root)
            places_path=root/"data/places.jsonld"
            document=_read_json(places_path)
            place=next((p for p in document["@graph"] if p["@id"].removeprefix("urn:uuid:")==args.place_id),None)
            if place is None: raise ValueError(f"place not found: {args.place_id}")
            existing=place.get("schema:subjectOf",[])
            pages=[page for page in existing if page["schema:url"]!=args.url]
            if args.action=="add":
                if len(pages)!=len(existing): raise ValueError(f"link already recorded: {args.url}")
                pages.append(barrier_free_webpage(args.url))
            if len(pages)==len(existing) and args.action=="rm": raise ValueError(f"link not recorded: {args.url}")
            if pages: place["schema:subjectOf"]=pages
            else: place.pop("schema:subjectOf",None)
            validate_jsonld_document(document)
            _write_json(places_path,document)
            return 0
        if args.command=="image":
            root=Path(args.root)
            if args.action=="set": _image_set(root,args.query_id,args.file); return 0
            if args.action=="clear": _image_clear(root,args.query_id); return 0
            if args.action=="review": _image_review(root); return 0
        if args.command=="assoc":
            root=Path(args.root)
            queries=load_queries(root)
            query=next((q for q in queries if q["id"]==args.query_id), None)
            if query is None: raise ValueError(f"search input not found: {args.query_id}")
            if args.reason is not None and not args.hold: raise ValueError("--reason is only valid with --hold")
            if args.hold:
                _hold(root,args.query_id,args.reason,args.editor); return 0
            choice=args.choice if args.choice=="none" else args.osm_id
            if choice=="none":
                candidate=None
            else:
                candidate=osm_candidate(choice)
            if candidate is not None:
                retained,version,problem=_retained_osm_snapshot(root)
                if problem is not None:
                    print(f"WARNING: {problem}ため、{choice} の収録を確認していません")
                elif choice not in retained:
                    reason=f"OSMミラー（{version}）に要素未収録のため自動保留。ミラー更新後に assoc --osm-id で再確認"
                    print(f"WARNING: {choice} は保持スナップショットに未収録のため、保留として記録しました。ミラー更新後に同じ --osm-id で再実行すると確定します")
                    _hold(root,args.query_id,reason,args.editor,previous=choice); return 0
            evidence={"target":{k:query[k] for k in ("id","name","coordinates","qid") if k in query},
                      "candidates":[] if candidate is None else [candidate]}
            editor=args.editor or subprocess.run(["git","config","--get","user.name"],cwd=root,capture_output=True,text=True).stdout.strip()
            if not editor: raise ValueError("editor is required: pass --editor or set git user.name")
            now=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
            entry={"evidence":evidence,"evidenceHash":evidence_hash(evidence),
                   "current":None if candidate is None else choice,"status":"decided",
                   "choice":choice,"method":"human",
                   "human":{"choice":choice,"editor":editor,"editedAt":now}}
            ledger=_read_json(root/"data/osm-decisions.json")
            if ledger.get("version")!=1 or not isinstance(ledger.get("facilities"),dict): raise ValueError("invalid OSM decision ledger")
            ledger=copy.deepcopy(ledger)
            ledger["facilities"][args.query_id]=entry
            updated=apply_decisions(_read_json(root/"data/places.jsonld"),queries,{args.query_id:entry})
            _write_json(root/"data/osm-decisions.json",ledger)
            _write_json(root/"data/places.jsonld",updated)
            return 0
        root=Path(args.root); documents=_documents(root)
        if args.input=="ls":
            for _,doc in documents:
                for query in doc["queries"]: print(f"{query['name']}\n  id={query['id']}")
            return 0
        selected=[(path,doc,q) for path,doc in documents for q in doc["queries"] if str(q.get("id"))==getattr(args,"query_id",None)]
        if args.input=="get":
            if len(selected)!=1: raise ValueError(f"search input not found: {args.query_id}")
            print(json.dumps(selected[0][2],ensure_ascii=False,indent=2)); return 0
        if args.input=="add":
            if (args.lon is None) != (args.lat is None) or ((args.lon is not None)==(args.qid is not None)): raise ValueError("use exactly one of --lon/--lat or --qid")
            path=root/"inputs/facilities.json"; doc=copy.deepcopy(_read(path)) if path.exists() else {"queries":[]}
            query={"id":new_uuid7(),"name":args.name}; query.update({"qid":args.qid} if args.qid is not None else {"coordinates":[args.lon,args.lat]}); doc["queries"].append(query); _write(path,doc); print(f"id={query['id']}"); return 0
        if len(selected)!=1: raise ValueError(f"search input not found: {args.query_id}")
        path,doc,query=selected[0]
        if args.input=="rm":
            doc["queries"].remove(query); _write(path,doc)
            identifier=f"urn:uuid:{query['id']}"
            places=_read_json(root/"data/places.jsonld")
            places["@graph"]=[p for p in places["@graph"] if p["@id"]!=identifier]
            validate_jsonld_document(places)
            _write_json(root/"data/places.jsonld",places)
            ledger=_read_json(root/"data/osm-decisions.json")
            if ledger.get("version")!=1 or not isinstance(ledger.get("facilities"),dict): raise ValueError("invalid OSM decision ledger")
            ledger["facilities"].pop(query["id"],None)
            _write_json(root/"data/osm-decisions.json",ledger)
            if (root/"data/categories.json").exists() and (root/"data/category-vocabulary.jsonld").exists():
                codes=facility_categories.load_vocabulary(root)
                categories=_read_json(root/"data/categories.json")
                issues=facility_categories.validate_decisions(categories,codes)
                if issues: raise ValueError("; ".join(issues))
                if query["id"] in categories["facilities"]:
                    del categories["facilities"][query["id"]]
                    _write_json(root/"data/categories.json",categories)
            print(f"removed {query['id']}"); return 0
        if (args.lon is None)!=(args.lat is None) or (args.lon is not None and args.qid is not None) or (args.new_name is None and args.lon is None and args.qid is None): raise ValueError("set requires --name, --lon/--lat, or --qid")
        if args.new_name is not None: query["name"]=args.new_name
        if args.lon is not None: query.update({"coordinates":[args.lon,args.lat]}); query.pop("qid",None)
        if args.qid is not None: query.update({"qid":args.qid}); query.pop("coordinates",None)
        _write(path,doc); return 0
    except (OSError,ValueError,json.JSONDecodeError) as error:
        print(f"ERROR: {error}"); return 1
    return 0
