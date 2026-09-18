import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
OSM_ODBL_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
WAM_TERMS_URL = "https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/"
CC0_MARKER_RE = re.compile(
    r"(?:\bcc0\b|creative\s+commons\s+zero)",
    re.IGNORECASE,
)

EXPECTED_PART_LICENSES = {
    "repository": CC0_URL,
    "openstreetmap": OSM_ODBL_URL,
    "wikidata": CC0_URL,
    "wam": WAM_TERMS_URL,
}

EXPECTED_LEDGER_LICENSES = {
    "openstreetmap": OSM_ODBL_URL,
    "wikidata": CC0_URL,
    "wam": WAM_TERMS_URL,
}

# These are exact, unambiguous identity/name forms.  Matching whole values
# prevents one broad name such as "repository/OpenStreetMap/Wikidata/WAM"
# from satisfying every required part.
SOURCE_IDENTITY_ALIASES = {
    "repository": (
        "repository",
        "repository assets",
        "repository-specific assets",
        "project assets",
        "project-specific assets",
        "独自著作物",
        "独自資産",
    ),
    "openstreetmap": ("openstreetmap", "openstreetmap data", "osm"),
    "wikidata": ("wikidata", "wikidata data"),
    "wam": ("wam", "wamnet", "wam data"),
}

class LicensingMetadataTests(unittest.TestCase):
    @staticmethod
    def _read_jsonld_from_landing_page():
        landing_page = ROOT / "site/index.html"
        if not landing_page.is_file():
            raise AssertionError(f"missing landing page: {landing_page}")

        html = landing_page.read_text(encoding="utf-8")
        match = re.search(
            r'<script\b[^>]*\s+type\s*=\s*["\']application/ld\+json["\'][^>]*>'
            r"(.*?)"
            r"</script>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match is None:
            raise AssertionError(
                "site/index.html must contain an application/ld+json script"
            )
        return json.loads(match.group(1).strip())

    @staticmethod
    def _string_values(value):
        """Yield string values from schema.org string/object/list forms."""
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for item in value:
                yield from LicensingMetadataTests._string_values(item)
        elif isinstance(value, dict):
            for key in ("@id", "@value", "id", "name", "value", "url"):
                if key in value:
                    yield from LicensingMetadataTests._string_values(value[key])

    @staticmethod
    def _normalize_identity(value):
        return re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]+", "", value.casefold())

    @classmethod
    def _source_ids_for_exact_values(cls, values):
        normalized_values = {
            cls._normalize_identity(value)
            for value in values
            if isinstance(value, str)
        }
        matches = set()
        for source_id, aliases in SOURCE_IDENTITY_ALIASES.items():
            normalized_aliases = {
                cls._normalize_identity(alias) for alias in aliases
            }
            if normalized_values & normalized_aliases:
                matches.add(source_id)
        return matches

    @classmethod
    def _entry_source_ids(cls, entry):
        explicit_values = []
        for field in ("identifier", "sourceId"):
            if field in entry:
                explicit_values.extend(cls._string_values(entry[field]))

        explicit_matches = cls._source_ids_for_exact_values(explicit_values)
        name_values = cls._string_values(entry.get("name"))
        name_matches = cls._source_ids_for_exact_values(name_values)
        return explicit_matches | name_matches

    @classmethod
    def _license_urls(cls, entry):
        values = []
        for field in ("license", "schema:license"):
            if field in entry:
                values.extend(cls._string_values(entry[field]))
        return set(values)


    def test_dataset_jsonld_has_source_specific_parts_and_no_uniform_cc0(self):
        metadata = self._read_jsonld_from_landing_page()
        self.assertIsInstance(metadata, dict)
        if not isinstance(metadata, dict):
            return

        has_part = metadata.get("hasPart")
        self.assertIsInstance(
            has_part,
            list,
            "Dataset JSON-LD must expose source-specific parts as a hasPart list",
        )
        if not isinstance(has_part, list):
            return

        self.assertEqual(
            len(EXPECTED_PART_LICENSES),
            len(has_part),
            "Dataset JSON-LD must contain exactly four source-specific hasPart entries",
        )

        matched_sources = []
        for index, entry in enumerate(has_part):
            with self.subTest(part=index):
                self.assertIsInstance(entry, dict)
                if not isinstance(entry, dict):
                    continue

                source_ids = self._entry_source_ids(entry)
                self.assertEqual(
                    1,
                    len(source_ids),
                    "each hasPart entry must identify exactly one required source",
                )
                if len(source_ids) != 1:
                    continue

                source_id = next(iter(source_ids))
                matched_sources.append(source_id)
                self.assertEqual(
                    {EXPECTED_PART_LICENSES[source_id]},
                    self._license_urls(entry),
                    f"hasPart entry for {source_id} must contain only its exact license URL",
                )

        self.assertEqual(
            set(EXPECTED_PART_LICENSES),
            set(matched_sources),
            "hasPart must contain one distinct entry for repository, OpenStreetMap, "
            "Wikidata, and WAM",
        )
        self.assertEqual(
            len(matched_sources),
            len(set(matched_sources)),
            "a source must not be represented by more than one hasPart entry",
        )

        top_level_license_values = []
        for field in ("license", "schema:license"):
            if field in metadata:
                top_level_license_values.extend(
                    self._string_values(metadata[field])
                )
        top_level_license_text = " ".join(top_level_license_values)
        self.assertFalse(
            CC0_URL.casefold() in top_level_license_text.casefold()
            or CC0_MARKER_RE.search(top_level_license_text),
            "the combined Dataset must not claim one top-level CC0 license",
        )

    def test_source_ledger_has_only_current_non_uniform_sources_and_licenses(self):
        ledger_path = ROOT / "config/sources.json"
        self.assertTrue(ledger_path.is_file(), f"missing source ledger: {ledger_path}")
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertIsInstance(ledger, dict)
        if not isinstance(ledger, dict):
            return

        sources = ledger.get("sources")
        self.assertIsInstance(sources, list)
        if not isinstance(sources, list):
            return

        self.assertEqual(
            len(EXPECTED_LEDGER_LICENSES),
            len(sources),
            "source ledger must contain exactly the three current source records",
        )
        source_ids = [
            source.get("id") if isinstance(source, dict) else None
            for source in sources
        ]
        self.assertEqual(
            len(source_ids),
            len(set(source_ids)),
            "source ledger IDs must be unique",
        )
        self.assertEqual(
            set(EXPECTED_LEDGER_LICENSES),
            set(source_ids),
            "source ledger must contain exactly openstreetmap, wikidata, and wam",
        )
        if (
            len(sources) != len(EXPECTED_LEDGER_LICENSES)
            or len(source_ids) != len(set(source_ids))
            or set(source_ids) != set(EXPECTED_LEDGER_LICENSES)
        ):
            return

        by_id = {source["id"]: source for source in sources}
        for source_id, expected_license_url in EXPECTED_LEDGER_LICENSES.items():
            with self.subTest(source=source_id):
                self.assertEqual(
                    expected_license_url,
                    by_id[source_id].get("license_url"),
                )

if __name__ == "__main__":
    unittest.main()
