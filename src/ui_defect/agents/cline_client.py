"""
Driver gọi Cline ở chế độ headless làm tầng reasoning text-only (máy công ty).

Cùng giao diện với codex_client.run_codex: `run_cline(prompt, schema) -> dict`.
KHÔNG gửi ảnh — chỉ prompt text (JSON map + candidates + skill).

KHÁC codex: KHÔNG giả định Cline hỗ trợ `--output-schema`. Thay vào đó schema được
NHÚNG vào prompt (yêu cầu trả JSON đúng shape), rồi trích object JSON cuối trong stdout.
Lệnh chạy CẤU HÌNH HOÀN TOÀN qua env để khớp cách gọi Cline headless ở máy công ty.

⚠️  Chưa chạy thực tế (máy dev không có Cline binary). Khi triển khai: đặt env cho khớp
    CLI Cline thật rồi `AGENT_BACKEND=cline`. Logic adapter đã có unit test (mock subprocess).

Cấu hình qua env:
  CLINE_BIN         = binary/đường dẫn (mặc định "cline")
  CLINE_ARGS        = args phụ, cách nhau bởi khoảng trắng (vd "task --headless --json")
  CLINE_PROMPT_MODE = "stdin" (mặc định) | "arg"  — đưa prompt qua stdin hay tham số cuối
  CLINE_TIMEOUT_SEC = timeout giây (mặc định 300)
  CLINE_CD          = thư mục làm việc (mặc định = repo root)
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

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
) -> dict[str, Any]:
    """
    Chạy Cline headless với prompt, trả dict JSON đã parse.

    Raise RuntimeError (kèm cmd + stderr) nếu: không thấy binary, timeout, exit≠0,
    hoặc output không chứa JSON hợp lệ.
    """
    cline_bin = _env("CLINE_BIN", "cline")
    extra_args = shlex.split(_env("CLINE_ARGS", ""))
    prompt_mode = _env("CLINE_PROMPT_MODE", "stdin")
    _timeout = timeout or int(_env("CLINE_TIMEOUT_SEC", "300"))
    _cwd = cwd or _env("CLINE_CD", str(_REPO_ROOT))

    full_prompt = _build_prompt(prompt, schema)
    cmd = [cline_bin, *extra_args]
    stdin_data: str | None = full_prompt
    if prompt_mode == "arg":
        cmd.append(full_prompt)
        stdin_data = None

    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=_timeout,
            cwd=_cwd,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Không tìm thấy Cline CLI '{cline_bin}'. Cài Cline hoặc đặt env CLINE_BIN/CLINE_ARGS. ({exc})"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Cline quá {_timeout}s (timeout). cmd={' '.join(cmd)}"
        ) from exc

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-600:]
        raise RuntimeError(
            f"Cline exit={proc.returncode}. cmd={' '.join(cmd[:4])}… stderr: {tail}"
        )

    return _extract_json(proc.stdout or "")
