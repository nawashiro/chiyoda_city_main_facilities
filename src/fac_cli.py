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
from src.facility_data import _read_json, _write_json, barrier_free_webpage, load_queries, new_uuid7, validate_jsonld_document, validate_published_document, validate_search_document
from src.resolve_osm_candidates import apply_decisions, evidence_hash, osm_candidate
from src import facility_categories
from src.env_utils import load_dotenv

def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, document: dict[str, Any]) -> None:
    issues=validate_search_document(document)
    if issues: raise ValueError("; ".join(issues))
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
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
    validate=subs.add_parser("jsonld-validate"); validate.add_argument("path"); validate.add_argument("--published",action="store_true",help="validate the published distribution, which may carry derived schema:image")
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
    args=parser.parse_args(argv)
    load_dotenv(getattr(args, "root", "."))
    try:
        if args.command=="jsonld-validate":
            document=_read(Path(args.path))
            if document.get("@type")=="schema:DefinedTermSet":
                from src.facility_categories import validate_vocabulary
                validate_vocabulary(document)
                return 0
            codes=None
            for parent in [Path(args.path).resolve(), *Path(args.path).resolve().parents]:
                candidate=parent/"data/categories.jsonld"
                if candidate.exists():
                    from src.facility_categories import load_vocabulary
                    codes=set(load_vocabulary(parent))
                    break
            (validate_published_document if args.published else validate_jsonld_document)(document, category_codes=codes)
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
            published=root/"site/places.jsonld"
            if published.is_file(): _write_json(published,document)
            return 0
        if args.command=="assoc":
            root=Path(args.root)
            queries=load_queries(root)
            query=next((q for q in queries if q["id"]==args.query_id), None)
            if query is None: raise ValueError(f"search input not found: {args.query_id}")
            choice=args.choice if args.choice=="none" else args.osm_id
            if choice=="none":
                candidate=None
            else:
                candidate=osm_candidate(choice)
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
            published=root/"site/places.jsonld"
            if published.is_file(): _write_json(published,places)
            ledger=_read_json(root/"data/osm-decisions.json")
            if ledger.get("version")!=1 or not isinstance(ledger.get("facilities"),dict): raise ValueError("invalid OSM decision ledger")
            ledger["facilities"].pop(query["id"],None)
            _write_json(root/"data/osm-decisions.json",ledger)
            print(f"removed {query['id']}"); return 0
        if (args.lon is None)!=(args.lat is None) or (args.lon is not None and args.qid is not None) or (args.new_name is None and args.lon is None and args.qid is None): raise ValueError("set requires --name, --lon/--lat, or --qid")
        if args.new_name is not None: query["name"]=args.new_name
        if args.lon is not None: query.update({"coordinates":[args.lon,args.lat]}); query.pop("qid",None)
        if args.qid is not None: query.update({"qid":args.qid}); query.pop("coordinates",None)
        _write(path,doc); return 0
    except (OSError,ValueError,json.JSONDecodeError) as error:
        print(f"ERROR: {error}"); return 1
    return 0
