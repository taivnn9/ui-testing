"""
LLM client — gọi llama.cpp OpenAI-compatible endpoint.
Thay thế anthropic SDK. Hỗ trợ vision + JSON output.

Cấu hình qua env:
  LLM_BASE_URL  = http://host:port  (mặc định: http://localhost:8080)
  LLM_MODEL     = tên model (mặc định: gemma-4)
  LLM_API_KEY   = api key nếu server yêu cầu (mặc định: "none")
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from PIL import Image

from .g0_framework import image_to_base64


_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8080").rstrip("/")
_MODEL = os.environ.get("LLM_MODEL", "gemma-4")
_API_KEY = os.environ.get("LLM_API_KEY", "none")
_TIMEOUT = int(os.environ.get("LLM_TIMEOUT_SEC", "120"))


def _parse_json_from_text(text: str) -> dict[str, Any]:
    """
    Trích JSON từ text response — fallback khi model không dùng json_object mode.
    Tìm block ```json ... ``` hoặc { ... } đầu tiên.
    """
    # Thử ```json ... ```
    m = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1).strip())
    # Thử block JSON trần
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"Không tìm thấy JSON trong response: {text[:200]}")


def call_llm(
    system_prompt: str,
    user_text: str,
    image: Image.Image | None = None,
    max_tokens: int = 1500,
    temperature: float = 0.1,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Gọi llama.cpp /v1/chat/completions.
    Trả về dict parsed từ JSON response.
    Raise httpx.HTTPError hoặc ValueError nếu lỗi.
    """
    _model = model or _MODEL

    # Build user content
    user_content: list[dict] | str
    if image is not None:
        img_b64 = image_to_base64(image)
        user_content = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            },
            {"type": "text", "text": user_text},
        ]
    else:
        user_content = user_text

    payload: dict[str, Any] = {
        "model": _model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_API_KEY}",
    }

    url = f"{_BASE_URL}/v1/chat/completions"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.RequestError as exc:
        # Lỗi mạng/timeout/DNS/connect refused — kèm URL + model để debug
        raise RuntimeError(
            f"Không gọi được LLM tại {url} (model={_model}, timeout={_TIMEOUT}s): "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise httpx.HTTPStatusError(
            f"LLM server tại {url} trả về {resp.status_code}: {resp.text[:500]}",
            request=resp.request,
            response=resp,
        )

    try:
        data = resp.json()
        raw_text: str = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise RuntimeError(
            f"Response LLM từ {url} không đúng định dạng OpenAI chat: "
            f"{type(exc).__name__}: {exc}. Body: {resp.text[:500]}"
        ) from exc

    # Parse JSON từ response
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: model có thể không dùng json_object mode
        return _parse_json_from_text(raw_text)
