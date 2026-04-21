"""Shared test fixtures."""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Generator

import pytest

from olik_font.sink.connection import DbConfig, connect


def _pick_port() -> int:
    """Reserve a free TCP port by binding then closing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def surreal_ephemeral() -> Generator[DbConfig, None, None]:
    """Start an in-memory SurrealDB on a random port for the test session."""
    port = _pick_port()
    proc = subprocess.Popen(
        [
            "surreal",
            "start",
            "--user",
            "root",
            "--pass",
            "root",
            "--bind",
            f"127.0.0.1:{port}",
            "memory",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cfg = DbConfig(
        url=f"http://127.0.0.1:{port}",
        namespace="hanfont",
        database="olik_test",
        user="root",
        password="root",
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            connect(cfg)
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("ephemeral surrealdb did not become reachable")

    try:
        yield cfg
    finally:
        proc.terminate()
        proc.wait(timeout=5)
