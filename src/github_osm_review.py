"""GitHub Issue decisions bound to committed facility evidence."""
from __future__ import annotations

import json
import os
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.facility_data import _distance_metres
from src.http_utils import read_limited_response
from src.resolve_osm_candidates import OSM

CONFIRM = "判断を確定する"
MARKER = re.compile(r"<!-- osm-review:([^: ]+):([0-9a-f]{64}) -->")


def escape(text):
    return str(text).replace("\n", " ").replace("\r", " ").replace("|", "&#124;").replace("<", "&lt;").replace(">", "&gt;").replace("[", "&#91;").replace("]", "&#93;")


def render_issue(query_id, entry):
    evidence = entry["evidence"]
    target = evidence["target"]
    lines = [f"[bot] {escape(target['name'])}のOSM参照を確認してください。", "",
             f"対象UUID: `{query_id}`", f"現在の参照: {OSM + entry['current'] if entry.get('current') else 'なし'}", "",
             f"確認理由: {escape(entry.get('reason', '自動判定できませんでした。'))}"]
    if entry.get("jev"):
        result = entry["jev"]
        lines.append(f"Jev: `{result['choice']}` / confidence `{result['confidence']:.4f}`（正答率ではありません）")
    else:
        lines.append("Jev: 未実行（" + ("既存ID・QIDでの照合に競合があるため" if evidence["candidates"] else "候補が見つからなかったため") + "）")
    lines.extend(["", "候補または「該当なし」を一つ選び、最後に確定欄をチェックしてください。", ""])
    for candidate in evidence["candidates"]:
        lon, lat = candidate["coordinates"]
        distance = f"{_distance_metres(target['coordinates'], candidate['coordinates']):.1f} m" if "coordinates" in target else "QID検索（距離なし）"
        record_id = candidate["recordId"]
        lines.append(f"- [ ] `{record_id}` {escape(candidate['name'])} / {distance} / [OSM]({OSM}{record_id}) / [地図](https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=19/{lat}/{lon})")
    lines.extend(["- [ ] `none` 該当なし（OSMとそれに伴うWikidataの参照を解除）", "", f"- [ ] {CONFIRM}", "", f"<!-- osm-review:{query_id}:{entry['evidenceHash']} -->"])
    return "\n".join(lines) + "\n"


def parse_issue(body, query_id, entry):
    if not re.search(rf"^- \[[xX]\] {CONFIRM}$", body, re.M):
        return None
    selected = re.findall(r"^- \[[xX]\] `([^`]+)` ", body, re.M)
    if len(selected) != 1:
        raise ValueError("候補または「該当なし」を一つだけ選び、確定欄をチェックしてください。")
    allowed = {c["recordId"] for c in entry["evidence"]["candidates"]} | {"none"}
    marker = MARKER.search(body)
    if not marker or marker.group(1) != query_id:
        raise ValueError("対象施設のIDを確認してください。")
    if selected[0] not in allowed:
        raise ValueError("保存済みの候補にない選択です。")
    return selected[0]


class GitHub:
    def __init__(self, repository=None, token=None):
        self.repository = repository or os.environ["GITHUB_REPOSITORY"]
        self.token = token or os.environ["GH_TOKEN"]
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", self.repository):
            raise ValueError("invalid GitHub repository")

    def api(self, path, data=None, method=None):
        request = Request("https://api.github.com" + path, data=json.dumps(data).encode() if data is not None else None,
                          method=method, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
        with urlopen(request, timeout=60) as response:
            return json.loads(read_limited_response(response, 4 * 1024 * 1024, "GitHub"))

    def issue(self, number):
        owner, name = self.repository.split("/")
        response = self.api("/graphql", {"query": "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){issue(number:$number){body state lastEditedAt url userContentEdits(first: 50){nodes{editedAt editor{login}}}}}}", "variables": {"owner": owner, "name": name, "number": number}})
        if response.get("errors"):
            raise ValueError("GitHub could not read Issue edit provenance: " + json.dumps(response["errors"], ensure_ascii=False))
        issue = response["data"]["repository"]["issue"]
        edits = [edit for edit in (issue.pop("userContentEdits") or {}).get("nodes") or [] if edit and edit.get("editor", {}).get("login")]
        latest = max(edits, key=lambda edit: edit["editedAt"], default=None)
        issue["lastEditedBy"] = {"login": latest["editor"]["login"]} if latest else None
        return issue

    def may_write(self, login):
        permission = self.api(f"/repos/{self.repository}/collaborators/{quote(login, safe='')}/permission")
        return permission["permission"] in {"admin", "maintain", "write"}

    def find_issue(self, query_id):
        marker = f"<!-- osm-review:{query_id}:" if query_id else "<!-- osm-unmatched -->"
        for page in range(1, 100):
            issues = self.api(f"/repos/{self.repository}/issues?state=all&per_page=100&page={page}")
            found = [i for i in issues if not i.get("pull_request")
                     and i["user"]["login"] == "github-actions[bot]" and marker in (i.get("body") or "")]
            if found:
                return max(found, key=lambda i: i["number"])["number"]
            if len(issues) < 100:
                return None
        raise ValueError("Issue search exceeds pagination budget")

    def save_issue(self, query_id, entry):
        body = render_issue(query_id, entry)
        number = self.find_issue(query_id)
        if number:
            issue = self.issue(number)
            marker = MARKER.search(issue["body"])
            if marker and marker.groups() == (query_id, entry["evidenceHash"]):
                return
            self.api(f"/repos/{self.repository}/issues/{number}", {"body": body, "state": "open"}, "PATCH")
        else:
            self.api(f"/repos/{self.repository}/issues", {"title": f"[bot] OSM確認: {escape(entry['evidence']['target']['name'])}", "body": body})

    def save_unmatched(self, entries):
        missing = [(key, entry) for key, entry in sorted(entries.items())
                   if entry.get("status") in {"decided", "no_candidates"} and entry.get("choice") == "none"]
        number = self.find_issue(None)
        if not missing:
            if number and self.issue(number)["state"] == "OPEN":
                self.api(f"/repos/{self.repository}/issues/{number}", {"state": "closed"}, "PATCH")
            return
        lines = ["[bot] 接続先が見つからなかった検索対象です。", "",
                 "実在を確認し、検索入力の除去またはOSMへの収録を検討してください。", ""]
        lines.extend(f"- {escape(entry['evidence']['target']['name'])} — `{key}`" for key, entry in missing)
        lines.extend(["", "<!-- osm-unmatched -->"])
        body = "\n".join(lines) + "\n"
        if number:
            issue = self.issue(number)
            if issue["body"] != body:
                self.api(f"/repos/{self.repository}/issues/{number}", {"body": body, "state": "open"}, "PATCH")
        else:
            self.api(f"/repos/{self.repository}/issues", {"title": "[bot] OSM接続先なし", "body": body})

    def corrective_comment(self, number, message):
        body = "[bot] " + message
        comments = self.api(f"/repos/{self.repository}/issues/{number}/comments?per_page=100")
        if any(c["user"]["login"] == "github-actions[bot]" and c["body"] == body for c in comments):
            return
        self.api(f"/repos/{self.repository}/issues/{number}/comments", {"body": body})


def read_confirmations(ledger, github):
    confirmations = {}
    for query_id, entry in ledger["facilities"].items():
        if entry.get("status") != "needs_review":
            continue
        number = github.find_issue(query_id)
        if not number:
            continue
        issue = github.issue(number)
        if not issue or issue["state"] != "OPEN":
            continue
        try:
            choice = parse_issue(issue["body"], query_id, entry)
            if choice is None:
                continue
            editor = issue.get("lastEditedBy")
            if not editor or not github.may_write(editor["login"]):
                raise ValueError("確定には、このリポジトリへの書き込み権限を持つ人の本文編集が必要です。")
            confirmations[query_id] = {"choice": choice, "editor": editor["login"], "editedAt": issue["lastEditedAt"], "url": issue["url"], "issue": number}
        except ValueError as error:
            github.corrective_comment(number, str(error))
    return confirmations


def apply_confirmations(ledger, confirmations):
    for query_id, human in confirmations.items():
        entry = ledger["facilities"][query_id]
        entry.update(choice=human["choice"], method="human", human=human, issue=human["issue"], status="decided")


def close_published(ledger, github):
    for query_id, entry in ledger["facilities"].items():
        if entry.get("method") != "human" or entry.get("status") != "decided" or not entry.get("issue"):
            continue
        issue = github.issue(entry["issue"])
        if issue["state"] != "OPEN":
            continue
        if parse_issue(issue["body"], query_id, entry) != entry["choice"]:
            continue
        github.api(f"/repos/{github.repository}/issues/{entry['issue']}", {"state": "closed", "state_reason": "completed"}, "PATCH")
