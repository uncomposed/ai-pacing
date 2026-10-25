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

    def test_id_registry_matches_schema(self):
        # PyYAML is not a CI dependency, so Ruby's YAML loader converts the registry.
        converted = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e", "puts JSON.generate(YAML.safe_load(File.read(ARGV[0])))", "spec/id-registry.yaml"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        instance = json.loads(converted.stdout)
        schema = json.loads((ROOT / "schema/id-registry.schema.json").read_text())
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])

    def test_proposed_node_without_proposal_fails_schema(self):
        subprocess.run(
            ["ruby", "tools/spec_tool.rb", "generate"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        instance = json.loads((ROOT / "generated/canonical.json").read_text())
        schema = json.loads((ROOT / "schema/ai-pacing.schema.json").read_text())
        node = next(item for item in instance["nodes"] if item["provenance"]["author_status"] == "proposed")
        del node["proposal"]
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        self.assertTrue(any("'proposal' is a required property" in error.message for error in validator.iter_errors(instance)))


if __name__ == "__main__":
    unittest.main()
