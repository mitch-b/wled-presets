"""Lint strict JSON and validate root-level WLED preset backups."""

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "wled-presets.schema.json"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"non-JSON numeric constant: {value}")


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Defaults to all root *.json files")
    args = parser.parse_args()
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    paths = args.files or sorted(ROOT.glob("*.json"))
    if not paths:
        parser.error("no preset JSON files found")

    failed = False
    for path in paths:
        try:
            data = load_json(path)
        except (OSError, ValueError) as error:
            print(f"{path}: {error}", file=sys.stderr)
            failed = True
            continue
        errors = list(validator.iter_errors(data))
        for error in errors:
            print(f"{path}:{error.json_path}: {error.message}", file=sys.stderr)
        if errors:
            failed = True
        else:
            print(f"{path}: OK")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
