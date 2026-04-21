# project/py/tests/test_schema_library.py
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schema" / "prototype-library.schema.json"
EXAMPLE = ROOT / "schema" / "examples" / "hello-library.json"


def test_hello_library_validates():
    schema = json.loads(SCHEMA.read_text())
    example = json.loads(EXAMPLE.read_text())
    jsonschema.Draft202012Validator(schema).validate(example)


def test_rejects_missing_coord_space():
    schema = json.loads(SCHEMA.read_text())
    example = json.loads(EXAMPLE.read_text())
    del example["coord_space"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(example)


def test_rejects_prototype_without_canonical_bbox():
    schema = json.loads(SCHEMA.read_text())
    example = json.loads(EXAMPLE.read_text())
    proto_id = next(iter(example["prototypes"]))
    del example["prototypes"][proto_id]["canonical_bbox"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(example)
