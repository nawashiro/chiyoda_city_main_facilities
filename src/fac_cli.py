"""Maintainer CLI for canonical JSON-LD validation and OSM search inputs."""
from __future__ import annotations
import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from src.facility_data import new_uuid7, source_refresh_due, validate_jsonld_document, validate_search_document

def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, document: dict[str, Any]) -> None:
    issues=validate_search_document(document)
    if issues: raise ValueError("; ".join(issues))
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _documents(root:Path) -> list[tuple[Path,dict[str,Any]]]:
    result=[]
    for path in sorted((root/"inputs/osm-search").rglob("*.json")):
        document=_read(path)
        if validate_search_document(document): raise ValueError(f"invalid search input: {path}")
        result.append((path,document))
    return result

def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(prog="fac",description="Maintain canonical JSON-LD facility data")
    subs=parser.add_subparsers(dest="command",required=True)
    validate=subs.add_parser("jsonld-validate"); validate.add_argument("path")
    inp=subs.add_parser("in",help="maintain OSM search inputs"); commands=inp.add_subparsers(dest="input",required=True)
    for name in ("ls","get","add","set"):
        p=commands.add_parser(name); p.add_argument("root",nargs="?",default=".")
        if name in {"get","set"}: p.add_argument("query_id")
        if name=="add": p.add_argument("name")
        if name in {"add","set"}:
            p.add_argument("--name",dest="new_name"); p.add_argument("--lon",type=float); p.add_argument("--lat",type=float); p.add_argument("--qid"); p.add_argument("--at")
    args=parser.parse_args(argv)
    try:
        if args.command=="jsonld-validate": validate_jsonld_document(_read(Path(args.path))); return 0
        root=Path(args.root); documents=_documents(root)
        if args.input=="ls":
            for _,doc in documents:
                for query in doc["queries"]: print(f"{query['name']}\n  id={query['id']}")
            return 0
        selected=[(path,doc,q) for path,doc in documents for q in doc["queries"] if str(q.get("id"))==args.query_id]
        if args.input=="get":
            if len(selected)!=1: raise ValueError(f"search input not found: {args.query_id}")
            print(json.dumps(selected[0][2],ensure_ascii=False,indent=2)); return 0
        at=args.at or datetime.now(timezone.utc).isoformat(timespec="seconds"); source_refresh_due(None,at)
        if args.input=="add":
            if (args.lon is None) != (args.lat is None) or ((args.lon is not None)==(args.qid is not None)): raise ValueError("use exactly one of --lon/--lat or --qid")
            moment=datetime.fromisoformat(at.replace("Z","+00:00")); path=root/"inputs/osm-search/human"/f"{moment:%Y%m}.json"; doc=copy.deepcopy(_read(path)) if path.exists() else {"source":{"kind":"human","sourceId":None,"retrievedAt":None},"queries":[]}
            query={"id":new_uuid7(),"name":args.name}; query.update({"qid":args.qid} if args.qid is not None else {"coordinates":[args.lon,args.lat]}); doc["queries"].append(query); _write(path,doc); print(f"id={query['id']}"); return 0
        if len(selected)!=1: raise ValueError(f"search input not found: {args.query_id}")
        path,doc,query=selected[0]
        if (args.lon is None)!=(args.lat is None) or (args.lon is not None and args.qid is not None) or (args.new_name is None and args.lon is None and args.qid is None): raise ValueError("set requires --name, --lon/--lat, or --qid")
        if args.new_name is not None: query["name"]=args.new_name
        if args.lon is not None: query.update({"coordinates":[args.lon,args.lat]}); query.pop("qid",None)
        if args.qid is not None: query.update({"qid":args.qid}); query.pop("coordinates",None)
        _write(path,doc); return 0
    except (OSError,ValueError,json.JSONDecodeError) as error:
        print(f"ERROR: {error}"); return 1
    return 0
