"""Shared test fixtures."""

from __future__ import annotations

import socket
import subprocess
import time
import uuid
from collections.abc import Generator

import pytest

from olik_font.sink.connection import DbConfig, connect


def _pick_port() -> int:
    """Reserve a free TCP port by binding then closing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def _surreal_ephemeral_server() -> Generator[tuple[str, str, str], None, None]:
    """Start one in-memory SurrealDB process for the test session."""
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
    url = f"http://127.0.0.1:{port}"
    user = "root"
    password = "root"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            connect(
                DbConfig(
                    url=url,
                    namespace="hanfont",
                    database="bootstrap",
                    user=user,
                    password=password,
                )
            )
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("ephemeral surrealdb did not become reachable")

    try:
        yield (url, user, password)
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture
def surreal_ephemeral(_surreal_ephemeral_server: tuple[str, str, str]) -> DbConfig:
    """Provide an isolated namespace/database pair for each test."""
    url, user, password = _surreal_ephemeral_server
    return DbConfig(
        url=url,
        namespace="hanfont",
        database=f"olik_test_{uuid.uuid4().hex}",
        user=user,
        password=password,
    )
