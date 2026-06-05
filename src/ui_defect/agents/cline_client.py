"""
Driver gọi Cline ở chế độ headless làm tầng reasoning text-only (máy công ty).

Cùng giao diện với codex_client.run_codex: `run_cline(prompt, schema) -> dict`.
KHÔNG gửi ảnh — chỉ prompt text (JSON map + candidates + skill).

KHÁC codex: KHÔNG giả định Cline hỗ trợ `--output-schema`. Thay vào đó schema được
NHÚNG vào prompt (yêu cầu trả JSON đúng shape), rồi trích object JSON cuối trong stdout.

Lệnh mặc định: `cline -y "<prompt>"` (CLINE_ARGS="-y", CLINE_PROMPT_MODE="arg").
Tuỳ chỉnh qua env để khớp cách gọi Cline headless ở từng máy.

⚠️  Chưa chạy thực tế (máy dev không có Cline binary). Khi triển khai: đặt env cho khớp
    CLI Cline thật rồi `AGENT_BACKEND=cline`. Logic adapter đã có unit test (mock subprocess).

Cấu hình qua env:
  CLINE_BIN         = binary/đường dẫn (mặc định "cline")
  CLINE_ARGS        = args phụ, cách nhau bởi khoảng trắng (mặc định "-y")
  CLINE_PROMPT_MODE = "stdin" (mặc định) | "arg"  — đưa prompt qua stdin hay tham số cuối
                      stdin an toàn hơn trên Windows (arg có thể vỡ khi prompt dài >8KB)
  CLINE_TIMEOUT_SEC = timeout giây (mặc định 300)
  CLINE_CD          = thư mục làm việc (mặc định = repo root)
"""
from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# repo root: agents → ui_defect → src → root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _env(name: str, default: str) -> str:
    val = os.environ.get(name, default)
    return val if val not in (None, "") else default


def _build_prompt(prompt: str, schema: dict[str, Any] | None) -> str:
    """Nhúng schema vào prompt (Cline không có --output-schema)."""
    if schema is None:
        return prompt
    return (
        f"{prompt}\n\n"
        "---\n"
        "CHỈ trả về DUY NHẤT một object JSON hợp lệ khớp JSON Schema sau "
        "(không kèm giải thích, không markdown fence):\n"
        f"{json.dumps(schema, ensure_ascii=False)}\n"
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Trích object JSON từ output. Thử parse cả chuỗi; nếu không, lấy {...} cân bằng cuối cùng."""
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Quét object {...} cân bằng cuối cùng (bỏ qua log/text bao quanh)
    depth = 0
    start = -1
    candidate = ""
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    candidate = text[start : i + 1]  # giữ cái cuối cùng
    if candidate:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Cline output có {{...}} nhưng không parse được JSON: {exc}. "
                f"Đoạn: {candidate[:500]}"
            ) from exc
    raise RuntimeError(f"Cline output không chứa JSON object. Output: {text[:500]}")


def run_cline(
    prompt: str,
    schema: dict[str, Any] | None = None,
    *,
    timeout: int | None = None,
    cwd: str | None = None,
    log_callback=None,
) -> dict[str, Any]:
    """
    Chạy Cline headless với prompt, trả dict JSON đã parse.

    Raise RuntimeError (kèm cmd + stderr) nếu: không thấy binary, timeout, exit≠0,
    hoặc output không chứa JSON hợp lệ.
    """
    cline_bin = _env("CLINE_BIN", "cline")
    extra_args = shlex.split(_env("CLINE_ARGS", "-y"))
    prompt_mode = _env("CLINE_PROMPT_MODE", "stdin")
    _timeout = timeout or int(_env("CLINE_TIMEOUT_SEC", "300"))
    _cwd = cwd or _env("CLINE_CD", str(_REPO_ROOT))

    full_prompt = _build_prompt(prompt, schema)
    cmd = [cline_bin, *extra_args]
    stdin_data: str | None = full_prompt
    if prompt_mode == "arg":
        cmd.append(full_prompt)
        stdin_data = None

    verbose = _env("CLINE_VERBOSE", "1") not in ("0", "false", "no")

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=_cwd,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Không tìm thấy Cline CLI '{cline_bin}'. Cài Cline hoặc đặt env CLINE_BIN/CLINE_ARGS. ({exc})"
        ) from exc

    # Stream stderr ra terminal trong khi chờ (để thấy progress)
    stderr_lines: list[str] = []

    def _drain_stderr() -> None:
        for line in proc.stderr:  # type: ignore[union-attr]
            stderr_lines.append(line)
            stripped = line.rstrip()
            if stripped:
                logger.debug("[cline] %s", stripped)  # → terminal + file
            if verbose:
                sys.stderr.write("[cline] " + line)
                sys.stderr.flush()
            if log_callback and stripped:
                log_callback("[cline] " + stripped)    # → SSE

    t = threading.Thread(target=_drain_stderr, daemon=True)
    t.start()

    try:
        stdout, _ = proc.communicate(input=stdin_data, timeout=_timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(f"Cline quá {_timeout}s (timeout). cmd={' '.join(cmd)}")
    finally:
        t.join(timeout=5)

    if proc.returncode != 0:
        tail = ("".join(stderr_lines) or stdout or "")[-600:]
        raise RuntimeError(
            f"Cline exit={proc.returncode}. cmd={' '.join(cmd[:4])}… stderr: {tail}"
        )

    return _extract_json(stdout or "")
