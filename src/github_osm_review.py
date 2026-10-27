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
    canonical = entry.get("issueBody") or render_issue(query_id, entry)
    normalize = lambda s: re.sub(r"(?m)^- \[[xX ]\]", "- [ ]", s).strip()
    if normalize(body) != normalize(canonical):
        raise ValueError("候補や根拠が更新・変更されています。最新の本文で選び直してください。")
    selected = re.findall(r"^- \[[xX]\] `([^`]+)` ", body, re.M)
    if len(selected) != 1:
        raise ValueError("候補または「該当なし」を一つだけ選び、確定欄をチェックしてください。")
    allowed = {c["recordId"] for c in entry["evidence"]["candidates"]} | {"none"}
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
        response = self.api("/graphql", {"query": "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){issue(number:$number){body state lastEditedAt url timelineItems(last: 10, itemTypes: [ISSUE_EDITED]){... on IssueEditedEvent{createdAt editor{login}}}}}}", "variables": {"owner": owner, "name": name, "number": number}})
        if response.get("errors"):
            raise ValueError("GitHub could not read Issue edit provenance: " + json.dumps(response["errors"], ensure_ascii=False))
        issue = response["data"]["repository"]["issue"]
        edited = [event for event in issue.pop("timelineItems") or [] if event and event.get("editor", {}).get("login")]
        latest = max(edited, key=lambda event: event["createdAt"], default=None)
        issue["lastEditedBy"] = latest["editor"] if latest else None
        return issue

    def may_write(self, login):
        permission = self.api(f"/repos/{self.repository}/collaborators/{quote(login, safe='')}/permission")
        return permission["permission"] in {"admin", "maintain", "write"}

    def find_issue(self, query_id):
        for page in range(1, 100):
            issues = self.api(f"/repos/{self.repository}/issues?state=all&per_page=100&page={page}")
            found = [i for i in issues if not i.get("pull_request") and i["user"]["login"] == "github-actions[bot]" and f"<!-- osm-review:{query_id}:" in (i.get("body") or "")]
            if found:
                return max(found, key=lambda i: i["number"])["number"]
            if len(issues) < 100:
                return None
        raise ValueError("Issue search exceeds pagination budget")

    def save_issue(self, query_id, entry):
        body = render_issue(query_id, entry)
        number = entry.get("issue") or self.find_issue(query_id)
        if number:
            issue = self.issue(number)
            if entry.get("issueEvidenceHash") == entry["evidenceHash"] or (issue and MARKER.search(issue["body"]) and MARKER.search(issue["body"]).groups() == (query_id, entry["evidenceHash"])):
                entry.update(issue=number, issueEvidenceHash=entry["evidenceHash"], issueBody=entry.get("issueBody", body))
                if issue["state"] != "OPEN":
                    self.api(f"/repos/{self.repository}/issues/{number}", {"state": "open"}, "PATCH")
                return
            self.api(f"/repos/{self.repository}/issues/{number}", {"body": body, "state": "open"}, "PATCH")
        else:
            created = self.api(f"/repos/{self.repository}/issues", {"title": f"[bot] OSM確認: {escape(entry['evidence']['target']['name'])}", "body": body})
            number = created["number"]
        entry.update(issue=number, issueEvidenceHash=entry["evidenceHash"], issueBody=body)

    def corrective_comment(self, number, message):
        body = "[bot] " + message
        comments = self.api(f"/repos/{self.repository}/issues/{number}/comments?per_page=100")
        if any(c["user"]["login"] == "github-actions[bot]" and c["body"] == body for c in comments):
            return
        self.api(f"/repos/{self.repository}/issues/{number}/comments", {"body": body})


def read_confirmations(ledger, github, current_hashes=None):
    confirmations = {}
    for query_id, entry in ledger["facilities"].items():
        if not entry.get("issue") or entry.get("status") != "needs_review":
            continue
        issue = github.issue(entry["issue"])
        if not issue or issue["state"] != "OPEN":
            continue
        try:
            choice = parse_issue(issue["body"], query_id, entry)
            if choice is None:
                continue
            if current_hashes is not None and current_hashes.get(query_id) != entry["evidenceHash"]:
                raise ValueError("検索入力か候補が変更されています。Update OpenStreetMap dataを再実行し、更新後の本文で選び直してください。")
            editor = issue.get("lastEditedBy")
            if not editor or not github.may_write(editor["login"]):
                raise ValueError("確定には、このリポジトリへの書き込み権限を持つ人の本文編集が必要です。")
            confirmations[query_id] = {"choice": choice, "editor": editor["login"], "editedAt": issue["lastEditedAt"], "url": issue["url"]}
        except ValueError as error:
            github.corrective_comment(entry["issue"], str(error))
    return confirmations


def apply_confirmations(ledger, confirmations):
    for query_id, human in confirmations.items():
        entry = ledger["facilities"][query_id]
        entry.update(choice=human["choice"], method="human", human=human, status="decided")


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
