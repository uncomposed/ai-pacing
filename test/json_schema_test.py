import json
import pathlib
import subprocess
import unittest

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]


class JsonSchemaTest(unittest.TestCase):
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
