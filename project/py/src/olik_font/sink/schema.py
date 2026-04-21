"""DDL for the olik SurrealDB schema + `ensure_schema`."""

from __future__ import annotations

from surrealdb import Surreal

DDL = """
-- glyph: one row per character, embedded stroke/layout data
DEFINE TABLE glyph SCHEMALESS;
DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;
DEFINE INDEX glyph_stroke_ct ON glyph FIELDS stroke_count;
DEFINE INDEX glyph_radical   ON glyph FIELDS radical;
DEFINE INDEX glyph_iou_mean  ON glyph FIELDS iou_mean;
DEFINE INDEX glyph_status    ON glyph FIELDS status;

-- prototype
DEFINE TABLE prototype SCHEMALESS;
DEFINE INDEX proto_id_uniq ON prototype FIELDS id UNIQUE;
DEFINE INDEX proto_name    ON prototype FIELDS name;

-- rule
DEFINE TABLE rule SCHEMALESS;
DEFINE INDEX rule_id_uniq ON rule FIELDS id UNIQUE;
DEFINE INDEX rule_bucket  ON rule FIELDS bucket;

DEFINE TABLE rule_trace SCHEMALESS;
DEFINE INDEX rt_glyph_order ON rule_trace FIELDS glyph, order;

DEFINE TABLE extraction_run SCHEMALESS;

DEFINE TABLE style_variant SCHEMALESS;
DEFINE INDEX sv_char_style ON style_variant FIELDS char, style_name UNIQUE;

DEFINE TABLE comfyui_job SCHEMALESS;
DEFINE INDEX cj_id_uniq ON comfyui_job FIELDS id UNIQUE;

-- Edges
DEFINE TABLE uses       SCHEMALESS;
DEFINE TABLE cites      SCHEMALESS;
DEFINE TABLE variant_of SCHEMALESS;
DEFINE INDEX variant_of_in_out ON variant_of FIELDS in, out UNIQUE;
"""


def ensure_schema(db: Surreal) -> None:
    """Apply DDL. DEFINE statements are overwrite-safe so this is idempotent."""
    db.query(DDL)
