"""Minimal ComfyUI REST client used by the styling bridge."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import requests


@dataclass(frozen=True, slots=True)
class ComfyUIClient:
    """Client for ComfyUI prompt submission, history polling, and image download."""

    base_url: str = "http://127.0.0.1:8188"
    request_timeout: float = 30.0
    poll_interval: float = 1.0

    def submit_prompt(self, workflow_json: dict[str, Any]) -> str:
        """Submit a workflow JSON payload and return the ComfyUI prompt id."""
        response = requests.post(
            self._url("/prompt"),
            json={"prompt": workflow_json},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        prompt_id = payload.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ValueError(f"missing prompt_id in ComfyUI response: {payload!r}")
        return prompt_id

    def wait_for_completion(self, prompt_id: str, timeout: float = 120) -> list[str]:
        """Poll ComfyUI history until the prompt produces output paths or times out."""
        deadline = time.monotonic() + timeout
        while True:
            response = requests.get(
                self._url(f"/history/{prompt_id}"),
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            outputs = self._extract_output_paths(prompt_id, response.json())
            if outputs is not None:
                return outputs
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for ComfyUI prompt {prompt_id}")
            time.sleep(self.poll_interval)

    def download_image(self, path: str, dest: Path) -> None:
        """Download a ComfyUI image reference to a local path."""
        image_type, subfolder, filename = self._parse_output_path(path)
        response = requests.get(
            self._url("/view"),
            params={
                "filename": filename,
                "subfolder": subfolder,
                "type": image_type,
            },
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)

    def _url(self, suffix: str) -> str:
        return f"{self.base_url.rstrip('/')}{suffix}"

    @staticmethod
    def _extract_output_paths(prompt_id: str, payload: dict[str, Any]) -> list[str] | None:
        history = payload.get(prompt_id, payload)
        if not isinstance(history, dict) or not history:
            return None

        status = history.get("status")
        if isinstance(status, dict) and status.get("status_str") == "error":
            raise RuntimeError(f"ComfyUI prompt {prompt_id} failed: {history!r}")

        outputs = history.get("outputs")
        if not isinstance(outputs, dict):
            return None

        image_paths: list[str] = []
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            images = node_output.get("images", [])
            if not isinstance(images, list):
                continue
            for image in images:
                if isinstance(image, dict):
                    image_paths.append(ComfyUIClient._build_output_path(image))
        return image_paths

    @staticmethod
    def _build_output_path(image: dict[str, Any]) -> str:
        image_type = image.get("type", "output")
        filename = image.get("filename")
        if not isinstance(image_type, str) or not image_type:
            raise ValueError(f"invalid ComfyUI image type: {image!r}")
        if not isinstance(filename, str) or not filename:
            raise ValueError(f"invalid ComfyUI image filename: {image!r}")
        subfolder = image.get("subfolder", "")
        if subfolder and not isinstance(subfolder, str):
            raise ValueError(f"invalid ComfyUI image subfolder: {image!r}")
        parts = [image_type]
        if subfolder:
            parts.extend(PurePosixPath(subfolder).parts)
        parts.append(filename)
        return str(PurePosixPath(*parts))

    @staticmethod
    def _parse_output_path(path: str) -> tuple[str, str, str]:
        parts = PurePosixPath(path).parts
        if len(parts) < 2:
            raise ValueError(f"invalid ComfyUI output path: {path!r}")
        image_type = parts[0]
        filename = parts[-1]
        subfolder = str(PurePosixPath(*parts[1:-1])) if len(parts) > 2 else ""
        return image_type, subfolder, filename
