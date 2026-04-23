import json

import pytest

from olik_font.sources.authored import DEFAULT_ROOT, AuthoredDecomposition, load_authored

SAMPLE_CHAR = "丁"
SAMPLE_PATH = DEFAULT_ROOT / f"{SAMPLE_CHAR}.json"


def test_load_authored_round_trips_sample() -> None:
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))

    authored = load_authored(SAMPLE_CHAR)

    assert isinstance(authored, AuthoredDecomposition)
    assert authored is not None
    assert authored.char == raw["char"]
    assert authored.supersedes == raw["supersedes"]
    assert authored.model_dump(mode="json")["partition"] == [
        {
            "prototype_ref": "proto:ding_top_stroke",
            "mode": "keep",
            "source_stroke_indices": [0],
            "children": [],
            "replacement_proto_ref": None,
        },
        {
            "prototype_ref": "proto:ding_hook_stroke",
            "mode": "keep",
            "source_stroke_indices": [1],
            "children": [],
            "replacement_proto_ref": None,
        },
    ]


def test_load_authored_rejects_malformed_schema(tmp_path) -> None:
    bad_path = tmp_path / f"{SAMPLE_CHAR}.json"
    bad_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "char": SAMPLE_CHAR,
                "supersedes": "mmh",
                "rationale": "missing prototype ref should fail",
                "authored_by": "codex",
                "authored_at": "2026-04-23T02:10:00Z",
                "partition": [{"mode": "keep", "source_stroke_indices": [0]}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="failed to validate"):
        load_authored(SAMPLE_CHAR, root=tmp_path)


def test_load_authored_returns_none_when_file_missing(tmp_path) -> None:
    assert load_authored("無", root=tmp_path) is None
