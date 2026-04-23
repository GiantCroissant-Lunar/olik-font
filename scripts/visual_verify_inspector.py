#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
TS_ROOT = ROOT / "project" / "ts"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5176
DEFAULT_CHARS = ("明", "清", "國", "森")
DEFAULT_OUT_DIR = ROOT / "vault" / "references" / "plan-14-kimi-verdicts" / "task-07-screens"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url = args.base_url or f"http://{args.host}:{args.port}"
    server = start_server(args.host, args.port)
    try:
        wait_for_server(base_url, timeout_s=90)
        capture_screenshots(base_url, out_dir, list(args.chars))
    finally:
        stop_server(server)

    for char in args.chars:
        print(out_dir / f"{char}.png")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--base-url")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--chars", nargs="+", default=list(DEFAULT_CHARS))
    return parser.parse_args(argv)


def start_server(host: str, port: int) -> subprocess.Popen[str]:
    subprocess.run(
        ["pnpm", "--filter", "@olik/inspector", "prepare-data"],
        cwd=TS_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return subprocess.Popen(
        [
            "pnpm",
            "--filter",
            "@olik/inspector",
            "exec",
            "vite",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=TS_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_server(base_url: str, *, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(base_url, timeout=2) as response:  # noqa: S310
                if response.status < 500:
                    return
        except URLError:
            time.sleep(1)
    raise TimeoutError(f"inspector server did not start at {base_url}")


def capture_screenshots(base_url: str, out_dir: Path, chars: list[str]) -> None:
    if shutil.which("npx") is None:
        raise FileNotFoundError("npx not found on PATH")

    for char in chars:
        subprocess.run(
            [
                "npx",
                "playwright",
                "screenshot",
                "--browser",
                "chromium",
                "--viewport-size",
                "1600,1200",
                "--wait-for-selector",
                "[data-testid=\"decomposition-explorer\"] .react-flow__node",
                "--wait-for-timeout",
                "500",
                f"{base_url}/glyph/{quote(char)}",
                str(out_dir / f"{char}.png"),
            ],
            cwd=ROOT,
            check=True,
        )


def stop_server(server: subprocess.Popen[str]) -> None:
    if server.poll() is not None:
        output = ""
        if server.stdout is not None:
            output = server.stdout.read()
        if server.returncode != 0:
            raise RuntimeError(f"inspector server exited early:\n{output[-4000:]}")
        return
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:  # noqa: BLE001
    print(str(exc), file=sys.stderr)
    raise
