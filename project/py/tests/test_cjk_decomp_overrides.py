from __future__ import annotations

import json
from pathlib import Path

from olik_font.bulk.batch import _load_cjk_entries


def _write_cjk_snapshot(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "source": {
                    "upstream": "https://github.com/amake/cjk-decomp",
                    "commit": "0000000000000000000000000000000000000000",
                    "license": "Apache-2.0",
                },
                "entries": {
                    "國": {"operator": "s", "components": ["囗", "或"]},
                    "或": {"operator": "c", "components": ["戈", "口"]},
                    "囗": {"operator": None, "components": []},
                    "戈": {"operator": None, "components": []},
                    "口": {"operator": None, "components": []},
                    "玉": {"operator": None, "components": []},
                    "一": {"operator": None, "components": []},
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_load_cjk_entries_applies_override_replacement_and_logs(tmp_path, capsys) -> None:
    cjk_path = tmp_path / "cjk-decomp.json"
    overrides_path = tmp_path / "cjk_decomp_overrides.yaml"
    _write_cjk_snapshot(cjk_path)
    overrides_path.write_text(
        "國:\n  operator: c\n  components: [囗, 玉]\n",
        encoding="utf-8",
    )

    entries = _load_cjk_entries(cjk_path, overrides_path=overrides_path)

    assert entries["國"]["operator"] == "c"
    assert entries["國"]["components"] == ["囗", "玉"]
    assert [node["char"] for node in entries["國"]["component_tree"]] == ["囗", "玉"]
    assert "cjk-decomp override: 國" in capsys.readouterr().err


def test_load_cjk_entries_builds_component_tree_from_overridden_children(tmp_path) -> None:
    cjk_path = tmp_path / "cjk-decomp.json"
    overrides_path = tmp_path / "cjk_decomp_overrides.yaml"
    _write_cjk_snapshot(cjk_path)
    overrides_path.write_text(
        "或:\n  operator: c\n  components: [一, 口]\n",
        encoding="utf-8",
    )

    entries = _load_cjk_entries(cjk_path, overrides_path=overrides_path)

    tree = entries["國"]["component_tree"]
    assert tree[1]["char"] == "或"
    assert [node["char"] for node in tree[1]["components"]] == ["一", "口"]
