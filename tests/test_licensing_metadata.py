import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
OSM_ODBL_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
WAM_TERMS_URL = "https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/"
OLD_PROJECT_LICENSE = "Creative Commons Attribution-ShareAlike 4.0 International"
OLD_PROJECT_LICENSE_URL_RE = re.compile(
    r"https?://creativecommons\.org/licenses/by-sa/4\.0/?",
    re.IGNORECASE,
)
CC0_MARKER_RE = re.compile(
    r"(?:\bcc0\b|creative\s+commons\s+zero)",
    re.IGNORECASE,
)
REPOSITORY_ASSETS_RE = re.compile(
    r"(?:"
    r"(?:repository|project)(?:[-\s]+specific)?['’]?s?[-\s]+assets?"
    r"|独自(?:著作物|資産)"
    r")",
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

SOURCE_HEADING_PATTERNS = {
    "repository": re.compile(
        r"(?:"
        r"(?:repository|project)(?:[-\s]+specific)?[-\s]+assets?"
        r"|独自(?:著作物|資産)"
        r")",
        re.IGNORECASE,
    ),
    "openstreetmap": re.compile(r"\b(?:openstreetmap|osm)\b", re.IGNORECASE),
    "wikidata": re.compile(r"\bwikidata\b", re.IGNORECASE),
    "wam": re.compile(r"\bwam(?:net)?\b", re.IGNORECASE),
}

SOURCE_SECTION_CONDITIONS = {
    "repository": CC0_MARKER_RE,
    "openstreetmap": re.compile(
        r"©\s*OpenStreetMap contributors",
        re.IGNORECASE,
    ),
    "wikidata": CC0_MARKER_RE,
    "wam": re.compile(
        r"(?:distribution|terms|license|配布ページ|利用条件|規約)",
        re.IGNORECASE,
    ),
}

# Keep this statement local to one paragraph so unrelated words spread over
# the document cannot accidentally satisfy the non-uniformity requirement.
NON_UNIFORM_DATASET_PATTERNS = (
    re.compile(
        r"combined\s+dataset.{0,180}"
        r"(?:is\s+not|isn't|does\s+not|doesn't|not).{0,100}"
        r"(?:one|a\s+single|single|uniform).{0,80}"
        r"(?:cc0|creative\s+commons\s+zero|license)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:one|a\s+single|single|uniform).{0,80}"
        r"(?:cc0|creative\s+commons\s+zero|license).{0,180}"
        r"(?:does\s+not|doesn't|not|isn't).{0,80}"
        r"combined\s+dataset",
        re.IGNORECASE,
    ),
    re.compile(
        r"combined\s+dataset.{0,180}"
        r"(?:source[-\s]+specific|different|non[-\s]+uniform|each\s+source)"
        r".{0,80}licenses?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:統合(?:された)?|結合|複合)?データセット.{0,100}"
        r"(?:単一|一つ|ひとつ).{0,100}"
        r"(?:cc0|creative\s+commons\s+zero|ライセンス).{0,100}"
        r"(?:ではありません|ではない|表現しません|表現しない|ありません|ない)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:cc0|creative\s+commons\s+zero|ライセンス).{0,100}"
        r"(?:単一|一つ|ひとつ).{0,100}"
        r"(?:統合(?:された)?|結合|複合)?データセット.{0,100}"
        r"(?:ではありません|ではない|表現しません|表現しない|ありません|ない)",
        re.IGNORECASE,
    ),
)

_MARKDOWN_HEADING_RE = re.compile(
    r"^(?P<marks>#{1,6})[ \t]+(?P<title>[^\n]+?)\s*$",
    re.MULTILINE,
)


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

    @staticmethod
    def _markdown_sections(text):
        matches = list(_MARKDOWN_HEADING_RE.finditer(text))
        sections = []
        for index, match in enumerate(matches):
            level = len(match.group("marks"))
            end = len(text)
            for next_match in matches[index + 1 :]:
                if len(next_match.group("marks")) <= level:
                    end = next_match.start()
                    break
            title = match.group("title").strip().rstrip("#").strip()
            sections.append((title, text[match.start() : end]))
        return sections

    @staticmethod
    def _has_non_uniform_dataset_statement(document):
        paragraphs = re.split(r"\n\s*\n", document)
        for paragraph in paragraphs:
            candidate = re.sub(r"\s+", " ", paragraph)
            if any(pattern.search(candidate) for pattern in NON_UNIFORM_DATASET_PATTERNS):
                return True
        return False

    @classmethod
    def _has_local_association(
        cls,
        text,
        subject_pattern,
        condition_pattern,
        required_url=None,
    ):
        """Require subject and condition/URL in one local document window."""
        windows = []
        for match in subject_pattern.finditer(text):
            start = max(0, match.start() - 320)
            end = min(len(text), match.end() + 320)
            windows.append(text[start:end])

        for paragraph in re.split(r"\n\s*\n", text):
            if subject_pattern.search(paragraph):
                windows.append(paragraph)

        for heading, section in cls._markdown_sections(text):
            if subject_pattern.search(heading):
                windows.append(section)

        for window in windows:
            if not condition_pattern.search(window):
                continue
            if required_url is not None and required_url.casefold() not in window.casefold():
                continue
            return True
        return False

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

    def test_sources_and_licenses_documents_each_condition_and_non_uniform_scope(self):
        document_path = ROOT / "SOURCES_AND_LICENSES.md"
        self.assertTrue(
            document_path.is_file(),
            f"missing source and license document: {document_path}",
        )
        document = document_path.read_text(encoding="utf-8")
        sections = self._markdown_sections(document)
        self.assertTrue(
            sections,
            "SOURCES_AND_LICENSES.md must organize source license details under headings",
        )

        for source_id, expected_license_url in EXPECTED_PART_LICENSES.items():
            with self.subTest(source=source_id):
                source_sections = [
                    section
                    for heading, section in sections
                    if {
                        candidate
                        for candidate, pattern in SOURCE_HEADING_PATTERNS.items()
                        if pattern.search(heading)
                    }
                    == {source_id}
                ]
                self.assertTrue(
                    source_sections,
                    f"SOURCES_AND_LICENSES.md must have a dedicated {source_id} heading",
                )
                self.assertTrue(
                    any(
                        expected_license_url in section
                        and SOURCE_SECTION_CONDITIONS[source_id].search(section)
                        for section in source_sections
                    ),
                    f"{source_id} heading/section must contain its URL and license condition",
                )

        self.assertTrue(
            self._has_non_uniform_dataset_statement(document),
            "SOURCES_AND_LICENSES.md must explicitly say the combined Dataset has "
            "non-uniform, source-specific licensing",
        )

    def test_readme_and_license_identify_repository_assets_as_cc0(self):
        readme_path = ROOT / "README.md"
        license_path = ROOT / "LICENSE"
        self.assertTrue(readme_path.is_file(), f"missing README: {readme_path}")
        self.assertTrue(license_path.is_file(), f"missing LICENSE: {license_path}")

        readme = readme_path.read_text(encoding="utf-8")
        license_text = license_path.read_text(encoding="utf-8")

        self.assertTrue(
            self._has_local_association(
                readme,
                REPOSITORY_ASSETS_RE,
                CC0_MARKER_RE,
                required_url=CC0_URL,
            ),
            "README.md must associate repository-specific assets with the CC0 URL",
        )

        self.assertTrue(
            self._has_local_association(
                license_text,
                REPOSITORY_ASSETS_RE,
                CC0_MARKER_RE,
            ),
            "LICENSE must identify repository-specific assets as CC0, not merely "
            "contain a generic CC0 phrase",
        )

        for path, text in ((readme_path, readme), (license_path, license_text)):
            with self.subTest(path=path.name):
                self.assertNotIn(
                    OLD_PROJECT_LICENSE.casefold(),
                    text.casefold(),
                    f"{path} must not retain the old project license title",
                )
                self.assertNotIn(
                    "cc by-sa 4.0",
                    text.casefold(),
                    f"{path} must not retain the old CC BY-SA 4.0 marker",
                )
                self.assertNotRegex(
                    text,
                    OLD_PROJECT_LICENSE_URL_RE,
                    f"{path} must not retain the old project license URL",
                )


if __name__ == "__main__":
    unittest.main()
