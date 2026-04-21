# project/py/tests/test_schema_record.py
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schema" / "glyph-record.schema.json"
EXAMPLE = ROOT / "schema" / "examples" / "hello-record.json"


def test_hello_record_validates():
    schema = json.loads(SCHEMA.read_text())
    example = json.loads(EXAMPLE.read_text())
    jsonschema.Draft202012Validator(schema).validate(example)


def test_rejects_missing_glyph_id():
    schema = json.loads(SCHEMA.read_text())
    example = json.loads(EXAMPLE.read_text())
    del example["glyph_id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(example)


def test_rejects_invalid_render_layer_z_range():
    schema = json.loads(SCHEMA.read_text())
    example = json.loads(EXAMPLE.read_text())
    example["render_layers"][0]["z_max"] = -1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(example)
