"""
Chọn backend cho tầng reasoning qua env AGENT_BACKEND.

  codex  (mặc định) → Codex CLI headless (codex_client.run_codex)        — máy dev
  cline             → Cline headless (cline_client.run_cline)             — máy công ty
  none              → không gọi agent (tương đương rule-only)

Mọi backend cùng giao diện: (prompt, schema) -> dict. Cấu hình chi tiết qua env riêng
(CODEX_* / CLINE_*). Xem codex_client.py, cline_client.py, docs/F1.1.
"""
from __future__ import annotations

import os
from typing import Any


def active_backend() -> str:
    return os.environ.get("AGENT_BACKEND", "codex").strip().lower()


def run_backend(prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Gọi backend đang chọn. Raise RuntimeError nếu backend lỗi (driver tự gói chi tiết)."""
    backend = active_backend()
    if backend == "codex":
        from .codex_client import run_codex
        return run_codex(prompt, schema)
    if backend == "cline":
        from .cline_client import run_cline
        return run_cline(prompt, schema)
    if backend in ("none", "off", ""):
        return {"findings": [], "summary": "agent_backend=none"}
    raise RuntimeError(f"AGENT_BACKEND không hỗ trợ: {backend!r} (dùng: codex | cline | none)")
