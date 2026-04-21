"""SurrealDB sink for glyph records."""

from olik_font.sink.connection import connect
from olik_font.sink.schema import DDL, ensure_schema

__all__ = ["DDL", "connect", "ensure_schema"]
