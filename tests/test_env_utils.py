import os
import tempfile
import unittest
from pathlib import Path

from src.env_utils import load_dotenv


class LoadDotenvTests(unittest.TestCase):
    def test_fills_missing_values_and_keeps_environment(self):
        os.environ.pop("TEST_DOTENV_KEY", None)
        os.environ["TEST_DOTENV_SET"] = "already"
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text(
                "# comment\nTEST_DOTENV_KEY = 'from-file'\nTEST_DOTENV_SET=from-file\nMALFORMED LINE\n",
                encoding="utf-8",
            )
            load_dotenv(directory)
        try:
            self.assertEqual("from-file", os.environ["TEST_DOTENV_KEY"])
            self.assertEqual("already", os.environ["TEST_DOTENV_SET"])
        finally:
            os.environ.pop("TEST_DOTENV_KEY", None)
            os.environ.pop("TEST_DOTENV_SET", None)

    def test_missing_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            load_dotenv(directory)


if __name__ == "__main__":
    unittest.main()
