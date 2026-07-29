import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import src.retrieve_wam as retrieve_wam
from src.facility_data import update_repository, validate_search_document
from src.retrieve_wam import (
    WAM_INCLUDED_SERVICE_CODES,
    fetch_wam_release,
    parse_wam_zip,
    prepare_wam_release,
    run_wam_retrieval,
)
from src.wam_contract import WAM_PUBLIC_ATTRIBUTE_HEADERS


WAM_HEADERS = list(WAM_PUBLIC_ATTRIBUTE_HEADERS)


def wam_zip(rows):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=WAM_HEADERS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("data.csv", "\ufeff" + text.getvalue())
    return payload.getvalue()


class WamRetrievalTests(unittest.TestCase):
    def test_rejects_oversized_archive_and_zip_member(self):
        with patch.object(retrieve_wam, "MAX_ARCHIVE_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "too large"):
                fetch_wam_release("202603", lambda url: (b"x" * 11, {}))

        payload = wam_zip(
            [
                {
                    "NO（※システム内の固有の番号、連番）": "A0001",
                    "サービス種別": "計画相談支援",
                    "事業所の名称": "施設A",
                    "事業所番号": "1330100001",
                    "事業所住所（市区町村）": "東京都千代田区",
                    "事業所緯度": "35.69",
                    "事業所経度": "139.75",
                }
            ]
        )
        with patch.object(retrieve_wam, "MAX_CSV_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "expanded CSV"):
                parse_wam_zip(payload, "52")

    def test_keeps_consultation_rows_without_available_hours(self):
        payload = wam_zip(
            [
                {
                    "NO（※システム内の固有の番号、連番）": "A0001",
                    "サービス種別": "計画相談支援",
                    "事業所の名称": "時間記載あり",
                    "事業所番号": "1330100001",
                    "事業所住所（市区町村）": "東京都千代田区",
                    "事業所緯度": "35.69",
                    "事業所経度": "139.75",
                    "利用可能な時間帯（平日）": "10:00-16:00",
                },
                {
                    "NO（※システム内の固有の番号、連番）": "A0002",
                    "サービス種別": "計画相談支援",
                    "事業所の名称": "時間記載なし",
                    "事業所番号": "1330100002",
                    "事業所住所（市区町村）": "東京都千代田区",
                    "事業所緯度": "35.70",
                    "事業所経度": "139.76",
                    "利用可能な時間帯（平日）": "",
                },
            ]
        )

        rows = parse_wam_zip(payload, "52")

        self.assertEqual(["時間記載あり", "時間記載なし"], [row["name"] for row in rows])

    def test_run_wam_retrieval_writes_operational_inputs(self):
        payload = wam_zip(
            [
                {
                    "都道府県コード又は市区町村コード": "13000",
                    "NO（※システム内の固有の番号、連番）": "A0001",
                    "サービス種別": "対象サービス",
                    "事業所の名称": "施設A",
                    "事業所番号": "1310100001",
                    "事業所住所（市区町村）": "東京都千代田区",
                    "事業所緯度": "35.69",
                    "事業所経度": "139.75",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs/osm-search").mkdir(parents=True)
            (root / "imports/wam").mkdir(parents=True)
            (root / "imports/wam/retrieval.json").write_text(
                json.dumps({"retrievedAt": None, "rawVersion": None}), encoding="utf-8"
            )

            run_wam_retrieval(
                root,
                "202603",
                "2026-04-16T00:00:00Z",
                lambda url: (payload, {"ETag": '"fixture"'}),
            )

            search = json.loads(
                (root / "inputs/osm-search/wam/202603.json").read_text(encoding="utf-8")
            )
            normalized = json.loads(
                (root / "imports/wam/normalized.json").read_text(encoding="utf-8")
            )
            retrieval = json.loads(
                (root / "imports/wam/retrieval.json").read_text(encoding="utf-8")
            )
            raw = json.loads((root / "imports/wam/raw.json").read_text(encoding="utf-8"))
            raw_bytes = (root / "imports/wam/raw.json").read_bytes()
            downloads_path = root / "imports/wam/downloads"

        self.assertEqual(1, len(search["queries"]))
        self.assertEqual(1, len(normalized["records"]))
        self.assertEqual("202603", retrieval["rawVersion"])
        self.assertEqual(len(WAM_INCLUDED_SERVICE_CODES), len(retrieval["artifacts"]))
        self.assertEqual("202603", raw["version"])
        self.assertFalse(downloads_path.exists())
        self.assertEqual(retrieval["rawSha256"], hashlib.sha256(raw_bytes).hexdigest())

    def test_fetches_only_consultation_archives_with_provenance(self):
        payload = wam_zip(
            [
                {
                    "都道府県コード又は市区町村コード": "13000",
                    "NO（※システム内の固有の番号、連番）": "A0001",
                    "サービス種別": "対象サービス",
                    "事業所の名称": "施設A",
                    "事業所番号": "1310100001",
                    "事業所住所（市区町村）": "東京都千代田区",
                    "事業所緯度": "35.69",
                    "事業所経度": "139.75",
                }
            ]
        )
        calls = []

        def fetch(url):
            calls.append(url)
            return payload, {"ETag": '"fixture"', "Last-Modified": "Wed, 01 Apr 2026 00:00:00 GMT"}

        rows, artifacts, downloads = fetch_wam_release("202603", fetch)

        self.assertEqual(("52", "53", "54", "70"), WAM_INCLUDED_SERVICE_CODES)
        self.assertEqual(len(WAM_INCLUDED_SERVICE_CODES), len(calls))
        self.assertTrue(all(f"_202603_{code}.zip" in url for code, url in zip(WAM_INCLUDED_SERVICE_CODES, calls)))
        self.assertTrue({"11", "12", "13", "14", "15", "66", "67"}.isdisjoint(WAM_INCLUDED_SERVICE_CODES))
        self.assertEqual(len(WAM_INCLUDED_SERVICE_CODES), len(rows))
        self.assertEqual('"fixture"', artifacts[0]["etag"])
        self.assertEqual(64, len(artifacts[0]["sha256"]))
        self.assertEqual(set(WAM_INCLUDED_SERVICE_CODES), set(downloads))

    def test_parses_official_zip_and_filters_to_chiyoda(self):
        payload = wam_zip(
            [
                {
                    "都道府県コード又は市区町村コード": "13000",
                    "NO（※システム内の固有の番号、連番）": "A0001",
                    "法人の名称": "法人A",
                    "法人URL": "https://example.com/corporation",
                    "サービス種別": "生活介護",
                    "事業所の名称": "施設A",
                    "事業所番号": "1310100001",
                    "事業所住所（市区町村）": "東京都千代田区",
                    "事業所住所（番地以降）": "神田一丁目1-1",
                    "事業所電話番号": "03-1234-5678",
                    "事業所緯度": "35.69",
                    "事業所経度": "139.75",
                },
                {
                    "都道府県コード又は市区町村コード": "13000",
                    "NO（※システム内の固有の番号、連番）": "A0002",
                    "サービス種別": "生活介護",
                    "事業所の名称": "区外施設",
                    "事業所番号": "1310200001",
                    "事業所住所（市区町村）": "東京都中央区",
                    "事業所緯度": "35.68",
                    "事業所経度": "139.77",
                },
            ]
        )

        rows = parse_wam_zip(payload, "22")

        self.assertEqual(1, len(rows))
        self.assertEqual("A0001", rows[0]["sourceRecordId"])
        self.assertEqual("1310100001", rows[0]["officeId"])
        self.assertEqual("22", rows[0]["serviceCode"])
        self.assertEqual("生活介護", rows[0]["serviceType"])
        self.assertEqual("施設A", rows[0]["name"])
        self.assertEqual([139.75, 35.69], rows[0]["coordinates"])
        self.assertEqual(set(WAM_HEADERS), set(rows[0]["attributes"]))
        self.assertEqual("03-1234-5678", rows[0]["attributes"]["事業所電話番号"])
        self.assertEqual("神田一丁目1-1", rows[0]["attributes"]["事業所住所（番地以降）"])
        self.assertEqual("法人A", rows[0]["attributes"]["法人の名称"])
        self.assertEqual(
            "https://example.com/corporation", rows[0]["attributes"]["法人URL"]
        )

    def test_groups_services_and_reuses_existing_alias_query(self):
        rows = [
            {
                "sourceRecordId": "A0001",
                "officeId": "1310100001",
                "serviceCode": "22",
                "serviceType": "生活介護",
                "name": "千代田区立障害者福祉センター",
                "coordinates": [139.76083554, 35.70039345],
            },
            {
                "sourceRecordId": "A0002",
                "officeId": "1310100002",
                "serviceCode": "52",
                "serviceType": "計画相談支援",
                "name": "千代田区立障害者福祉センター",
                "coordinates": [139.76083553, 35.70039345],
            },
        ]
        existing_id = "019c0000-0000-7000-8000-000000000099"
        existing = [
            {
                "schemaVersion": 1,
                "source": {"kind": "human"},
                "queries": [
                    {
                        "id": existing_id,
                        "name": "えみふる（障害者福祉センター）",
                        "coordinates": [139.760849, 35.700506],
                    }
                ],
            }
        ]

        search, normalized = prepare_wam_release(
            rows, existing, "202603", "2026-04-16T00:00:00Z"
        )

        self.assertEqual([], search["queries"])
        self.assertEqual(
            {
                "kind": "source",
                "sourceId": "wam",
                "retrievedAt": "2026-04-16T00:00:00Z",
            },
            search["source"],
        )
        self.assertNotIn("schemaVersion", search)
        self.assertEqual([], validate_search_document(search))
        self.assertEqual(existing_id, normalized["records"][0]["queryId"])
        self.assertEqual(["A0001", "A0002"], normalized["records"][0]["sourceRecordIds"])

    def test_generates_stable_uuid7_search_input_and_promotes_new_place(self):
        row = {
            "sourceRecordId": "A1000",
            "officeId": "1310101000",
            "serviceCode": "60",
            "serviceType": "就労移行支援",
            "name": "新しい支援施設",
            "coordinates": [139.75, 35.69],
            "attributes": {name: "" for name in WAM_HEADERS},
        }
        search, normalized = prepare_wam_release(
            [row], [], "202603", "2026-04-16T00:00:00Z"
        )
        repeated, _ = prepare_wam_release(
            [row], [], "202603", "2026-04-16T00:00:00Z"
        )
        query = search["queries"][0]

        self.assertEqual(query["id"], repeated["queries"][0]["id"])
        self.assertEqual("7", query["id"][14])
        self.assertEqual(query["id"], normalized["records"][0]["queryId"])

        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs/osm-search/wam").mkdir(parents=True)
            (root / "imports/wam").mkdir(parents=True)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "data").mkdir()
            (root / "config").mkdir()
            (root / "dist/public").mkdir(parents=True)
            (root / "inputs/osm-search/wam/202603.json").write_text(
                json.dumps(search), encoding="utf-8"
            )
            (root / "imports/wam/normalized.json").write_text(
                json.dumps(normalized), encoding="utf-8"
            )
            raw_payload = (
                json.dumps({"version": "202603", "rows": [row]}, ensure_ascii=False, indent=2)
                + "\n"
            ).encode()
            (root / "imports/wam/raw.json").write_bytes(raw_payload)
            (root / "imports/wam/retrieval.json").write_text(
                json.dumps(
                    {
                        "rawVersion": "202603",
                        "retrievedAt": "2026-04-16T00:00:00Z",
                        "rawSha256": hashlib.sha256(raw_payload).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            (root / "data/registry.json").write_text(
                json.dumps({"schemaVersion": 1, "places": []}), encoding="utf-8"
            )
            (root / "config/sources.json").write_text(
                (repository / "config/sources.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            update_repository(root, "2026-04-16T00:00:00Z", "wam")
            registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))

        self.assertEqual(1, len(registry["places"]))
        self.assertEqual(query["id"], registry["places"][0]["id"])
        self.assertEqual(["disability-support"], registry["places"][0]["categoryIds"])
        self.assertEqual("wam", registry["places"][0]["geometrySource"]["sourceId"])


if __name__ == "__main__":
    unittest.main()
