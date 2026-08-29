import json
import pathlib
import subprocess
import unittest

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]


class JsonSchemaTest(unittest.TestCase):
    def test_all_json_schemas_are_valid_draft_2020_12(self):
        schema_paths = sorted((ROOT / "schema").glob("*.json"))
        schema_paths += sorted((ROOT / "eval" / "clean-room").glob("*.schema.json"))
        self.assertGreaterEqual(len(schema_paths), 3)
        for path in schema_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))

    def test_generated_canonical_json_matches_schema(self):
        subprocess.run(
            ["ruby", "tools/spec_tool.rb", "generate"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        instance = json.loads((ROOT / "generated/canonical.json").read_text())
        schema = json.loads((ROOT / "schema/ai-pacing.schema.json").read_text())
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()
