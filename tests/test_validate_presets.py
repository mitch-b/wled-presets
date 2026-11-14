import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_presets.py"


class ValidatePresetsTests(unittest.TestCase):
    def run_validator(self, *paths):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), *map(str, paths)],
            capture_output=True,
            text=True,
            check=False,
        )

    def validate_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "presets.json"
            path.write_text(text, encoding="utf-8")
            return self.run_validator(path)

    def test_existing_backups(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("office-shelves.json", "roof-line.json"):
            self.assertIn(f"{name}: OK", result.stdout)

    def test_partial_states_layering_and_playlist_forms(self):
        data = {
            "0": {},
            "1": {"seg": [{"bm": 16, "bri": 0}, {"stop": 0}]},
            "2": {"on": "t", "seg": {"col": [[0, 255, 0, 128], "FFA000", "r"]}},
            "3": {"playlist": {"ps": [1, 2], "dur": [100], "transition": 7}},
            "4": {"playlist": {"ps": [1], "dur": 100, "transition": [7], "end": 255}},
        }
        result = self.validate_text(json.dumps(data))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_json_lint_failures(self):
        for text, message in (
            ('{"1": {},}', "line 1 column"),
            ('{"1": {}, "1": {}}', "duplicate object key"),
            ('{"1": {"bri": 1, "bri": 2}}', "duplicate object key"),
            ('{"1": {"bri": NaN}}', "non-JSON numeric constant"),
            ('{"1": {"bri": Infinity}}', "non-JSON numeric constant"),
        ):
            with self.subTest(text=text):
                result = self.validate_text(text)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_invalid_schema_values(self):
        for data in (
            [],
            {"251": {"on": True}},
            {"01": {"on": True}},
            {"0": {"on": True}},
            {"1": {"brightness": 102}},
            {"1": {"bri": 256}},
            {"1": {"bri": -1}},
            {"1": {"bri": True}},
            {"1": {"on": 1}},
            {"1": {"seg": [{"c3": 32}]}},
            {"1": {"seg": [{"bm": 17}]}},
            {"1": {"seg": [{"col": [[256, 0, 0]]}]}},
            {"1": {"seg": [{"col": [[0, 0]]}]}},
            {"1": {"seg": [{"typo": 0}]}},
            {"1": {"playlist": {"ps": []}}},
            {"1": {"playlist": {"ps": [251]}}},
            {"1": {"playlist": {"ps": [1], "dur": -1}}},
        ):
            with self.subTest(data=data):
                result = self.validate_text(json.dumps(data))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("presets.json:$", result.stderr)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_validator(Path(directory) / "missing.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No such file", result.stderr)

    def test_failure_is_not_hidden_by_valid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text('{"1": {"bri": 256}}', encoding="utf-8")
            result = self.run_validator(path, ROOT / "office-shelves.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("office-shelves.json: OK", result.stdout)
        self.assertIn("invalid.json:$.1.bri", result.stderr)


if __name__ == "__main__":
    unittest.main()
