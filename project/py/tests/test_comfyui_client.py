from __future__ import annotations

from pathlib import Path

import pytest

from olik_font.styling import ComfyUIClient


class _FakeResponse:
    def __init__(self, *, json_data=None, content: bytes = b"", status_code: int = 200):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code

    def json(self):
        if self._json_data is None:
            raise AssertionError("json() not expected for this response")
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


def test_submit_prompt_posts_workflow_and_returns_prompt_id(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], timeout: float):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse(json_data={"prompt_id": "prompt-123"})

    monkeypatch.setattr("olik_font.styling.comfyui.requests.post", fake_post)

    workflow = {"prompt": {"3": {"class_type": "KSampler"}}}
    client = ComfyUIClient(base_url="http://127.0.0.1:8188")

    prompt_id = client.submit_prompt(workflow)

    assert prompt_id == "prompt-123"
    assert captured == {
        "url": "http://127.0.0.1:8188/prompt",
        "json": {"prompt": workflow},
        "timeout": 30.0,
    }


def test_wait_for_completion_polls_history_until_outputs(monkeypatch):
    responses = iter(
        [
            _FakeResponse(json_data={}),
            _FakeResponse(
                json_data={
                    "prompt-123": {
                        "status": {"status_str": "success"},
                        "outputs": {
                            "9": {
                                "images": [
                                    {
                                        "filename": "styled.png",
                                        "subfolder": "ink-brush/seed-1",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                    }
                }
            ),
        ]
    )
    calls: list[tuple[str, float]] = []

    def fake_get(url: str, *, params=None, timeout: float):
        assert params is None
        calls.append((url, timeout))
        return next(responses)

    monkeypatch.setattr("olik_font.styling.comfyui.requests.get", fake_get)
    monkeypatch.setattr("olik_font.styling.comfyui.time.sleep", lambda _seconds: None)

    client = ComfyUIClient(base_url="http://127.0.0.1:8188", poll_interval=0.0)

    outputs = client.wait_for_completion("prompt-123", timeout=5)

    assert outputs == ["output/ink-brush/seed-1/styled.png"]
    assert calls == [
        ("http://127.0.0.1:8188/history/prompt-123", 30.0),
        ("http://127.0.0.1:8188/history/prompt-123", 30.0),
    ]


def test_download_image_fetches_view_and_writes_file(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    def fake_get(url: str, *, params: dict[str, str], timeout: float):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return _FakeResponse(content=b"png-bytes")

    monkeypatch.setattr("olik_font.styling.comfyui.requests.get", fake_get)

    client = ComfyUIClient(base_url="http://127.0.0.1:8188")
    dest = tmp_path / "styled.png"

    client.download_image("output/ink-brush/seed-1/styled.png", dest)

    assert dest.read_bytes() == b"png-bytes"
    assert captured == {
        "url": "http://127.0.0.1:8188/view",
        "params": {
            "filename": "styled.png",
            "subfolder": "ink-brush/seed-1",
            "type": "output",
        },
        "timeout": 30.0,
    }


def test_wait_for_completion_times_out_when_history_never_finishes(monkeypatch):
    def fake_get(url: str, *, params=None, timeout: float):
        assert params is None
        return _FakeResponse(json_data={})

    clock = iter([100.0, 100.0, 101.5])

    monkeypatch.setattr("olik_font.styling.comfyui.requests.get", fake_get)
    monkeypatch.setattr("olik_font.styling.comfyui.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("olik_font.styling.comfyui.time.sleep", lambda _seconds: None)

    client = ComfyUIClient(base_url="http://127.0.0.1:8188", poll_interval=0.0)

    with pytest.raises(TimeoutError, match="prompt-123"):
        client.wait_for_completion("prompt-123", timeout=1)
