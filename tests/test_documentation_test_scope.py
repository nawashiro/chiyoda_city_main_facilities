import ast
from pathlib import Path
import unittest


class DocumentationTestScopeTests(unittest.TestCase):
    def test_facility_data_has_no_broad_documentation_structure_test(self):
        repository = Path(__file__).resolve().parents[1]
        source = (repository / "tests/test_facility_data.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        method_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn(
            "test_documentation_uses_the_diataxis_directory_structure",
            method_names,
        )


if __name__ == "__main__":
    unittest.main()
