"""Connection factory - reads OLIK_DB_* env vars with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass

from surrealdb import Surreal


@dataclass(frozen=True)
class DbConfig:
    url: str
    namespace: str
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> DbConfig:
        return cls(
            url=os.environ.get("OLIK_DB_URL", "http://127.0.0.1:6480"),
            namespace=os.environ.get("OLIK_DB_NS", "hanfont"),
            database=os.environ.get("OLIK_DB_NAME", "olik"),
            user=os.environ.get("OLIK_DB_USER", "root"),
            password=os.environ.get("OLIK_DB_PASS", "root"),
        )


def connect(config: DbConfig | None = None) -> Surreal:
    """Open a SurrealDB connection, sign in, select NS/DB."""
    cfg = config or DbConfig.from_env()
    db = Surreal(cfg.url)
    db.signin({"username": cfg.user, "password": cfg.password})
    db.use(cfg.namespace, cfg.database)
    return db
