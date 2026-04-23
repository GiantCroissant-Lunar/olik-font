"""DDL for the olik SurrealDB schema + `ensure_schema`."""

from __future__ import annotations

from surrealdb import Surreal

DDL = """
-- glyph: one row per character, embedded stroke/layout data
DEFINE TABLE IF NOT EXISTS glyph SCHEMALESS;
DEFINE INDEX IF NOT EXISTS glyph_char_uniq ON TABLE glyph FIELDS char UNIQUE;
DEFINE INDEX IF NOT EXISTS glyph_stroke_ct ON TABLE glyph FIELDS stroke_count;
DEFINE INDEX IF NOT EXISTS glyph_radical   ON TABLE glyph FIELDS radical;
DEFINE INDEX IF NOT EXISTS glyph_iou_mean  ON TABLE glyph FIELDS iou_mean;
DEFINE INDEX IF NOT EXISTS glyph_status    ON TABLE glyph FIELDS status;
DEFINE FIELD IF NOT EXISTS etymology ON TABLE glyph TYPE option<string>
    ASSERT $value IS NONE OR $value IN ["pictographic", "ideographic", "pictophonetic"];

-- prototype
DEFINE TABLE IF NOT EXISTS prototype SCHEMALESS;
DEFINE INDEX IF NOT EXISTS proto_id_uniq ON TABLE prototype FIELDS id UNIQUE;
DEFINE INDEX IF NOT EXISTS proto_name    ON TABLE prototype FIELDS name;
DEFINE FIELD IF NOT EXISTS role ON TABLE prototype TYPE option<string>
    ASSERT $value IS NONE OR $value IN ["meaning", "sound", "iconic", "distinguishing", "unknown"];
DEFINE FIELD IF NOT EXISTS etymology ON TABLE prototype TYPE option<string>
    ASSERT $value IS NONE OR $value IN ["pictographic", "ideographic", "pictophonetic"];
DEFINE FIELD IF NOT EXISTS productive_count ON TABLE prototype TYPE int DEFAULT 0;

-- rule
DEFINE TABLE IF NOT EXISTS rule SCHEMALESS;
DEFINE INDEX IF NOT EXISTS rule_id_uniq ON TABLE rule FIELDS id UNIQUE;
DEFINE INDEX IF NOT EXISTS rule_bucket  ON TABLE rule FIELDS bucket;

DEFINE TABLE IF NOT EXISTS rule_trace SCHEMALESS;
DEFINE INDEX IF NOT EXISTS rt_glyph_order ON TABLE rule_trace FIELDS glyph, order;

DEFINE TABLE IF NOT EXISTS extraction_run SCHEMALESS;

DEFINE TABLE IF NOT EXISTS style_variant SCHEMALESS;
DEFINE INDEX IF NOT EXISTS sv_char_style ON TABLE style_variant FIELDS char, style_name UNIQUE;

DEFINE TABLE IF NOT EXISTS comfyui_job SCHEMALESS;
DEFINE INDEX IF NOT EXISTS cj_id_uniq ON TABLE comfyui_job FIELDS id UNIQUE;

-- Edges
DEFINE TABLE IF NOT EXISTS uses SCHEMALESS;
DEFINE TABLE IF NOT EXISTS cites SCHEMALESS;
DEFINE TABLE IF NOT EXISTS variant_of SCHEMALESS;
DEFINE INDEX IF NOT EXISTS variant_of_in_out ON TABLE variant_of FIELDS in, out UNIQUE;

DEFINE TABLE IF NOT EXISTS decomposes_into TYPE RELATION FROM prototype TO prototype SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS ordinal ON TABLE decomposes_into TYPE int;
DEFINE FIELD IF NOT EXISTS source ON TABLE decomposes_into TYPE string;
DEFINE INDEX IF NOT EXISTS decomposes_into_in_out ON TABLE decomposes_into FIELDS in, out UNIQUE;

DEFINE TABLE IF NOT EXISTS appears_in TYPE RELATION FROM prototype TO glyph SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS instance_count ON TABLE appears_in TYPE int;
DEFINE INDEX IF NOT EXISTS appears_in_in_out ON TABLE appears_in FIELDS in, out UNIQUE;

DEFINE TABLE IF NOT EXISTS has_kangxi TYPE RELATION FROM glyph TO prototype SCHEMAFULL;
DEFINE INDEX IF NOT EXISTS has_kangxi_in ON TABLE has_kangxi FIELDS in UNIQUE;
"""


def ensure_schema(db: Surreal) -> None:
    """Apply DDL. IF NOT EXISTS keeps the migration idempotent."""
    db.query(DDL)
