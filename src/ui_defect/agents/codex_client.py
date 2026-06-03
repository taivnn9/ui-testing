"""
Driver gọi Codex CLI ở chế độ headless (`codex exec`) làm tầng reasoning text-only.

Thay cho llm_client (VLM). KHÔNG gửi ảnh — chỉ gửi prompt text (JSON map + candidates + skill).
Khóa shape output bằng `--output-schema`, đọc message cuối từ `-o <file>`.

Cấu hình qua env (xem docs/F1.1):
  CODEX_BIN        = đường dẫn binary (mặc định "codex")
  CODEX_MODEL      = model (bỏ trống = mặc định của codex)
  CODEX_SANDBOX    = read-only | workspace-write | danger-full-access  (mặc định workspace-write)
  CODEX_TIMEOUT_SEC= timeout giây (mặc định 180)
  CODEX_CD         = thư mục làm việc (mặc định = repo root)
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# repo root = .../ui-testing (parents[3] tính từ file này: agents → ui_defect → src → root)
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _env(name: str, default: str) -> str:
    val = os.environ.get(name, default)
    return val if val not in (None, "") else default


def run_codex(
    prompt: str,
    schema: dict[str, Any] | None = None,
    *,
    timeout: int | None = None,
    sandbox: str | None = None,
    model: str | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    """
    Chạy `codex exec` với prompt (qua stdin), trả về dict đã parse từ JSON message cuối.

    Raise RuntimeError (kèm cmd + stderr) nếu: không thấy binary, timeout, exit≠0,
    không có output, hoặc output không phải JSON hợp lệ.
    """
    codex_bin = _env("CODEX_BIN", "codex")
    _sandbox = sandbox or _env("CODEX_SANDBOX", "workspace-write")
    _timeout = timeout or int(_env("CODEX_TIMEOUT_SEC", "180"))
    _model = model if model is not None else os.environ.get("CODEX_MODEL", "")
    _cwd = cwd or _env("CODEX_CD", str(_REPO_ROOT))

    with tempfile.TemporaryDirectory(prefix="codex_") as tmp:
        out_path = Path(tmp) / "out.json"
        cmd = [
            codex_bin, "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "-s", _sandbox,
            "-C", _cwd,
            "-o", str(out_path),
        ]
        if _model:
            cmd += ["-m", _model]
        if schema is not None:
            schema_path = Path(tmp) / "schema.json"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            cmd += ["--output-schema", str(schema_path)]
        cmd += ["-"]  # đọc prompt từ stdin

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=_timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Không tìm thấy Codex CLI '{codex_bin}'. Cài Codex hoặc đặt env CODEX_BIN. ({exc})"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Codex exec quá {_timeout}s (timeout). cmd={' '.join(cmd)}"
            ) from exc

        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-600:]
            raise RuntimeError(
                f"Codex exec exit={proc.returncode} (sandbox={_sandbox}, model={_model or 'default'}). "
                f"stderr: {tail}"
            )

        if not out_path.is_file():
            tail = (proc.stdout or proc.stderr or "")[-600:]
            raise RuntimeError(f"Codex exec không tạo output file. stdout/stderr: {tail}")

        raw = out_path.read_text(encoding="utf-8").strip()

    if not raw:
        raise RuntimeError("Codex exec trả output rỗng.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Codex exec output không phải JSON hợp lệ: {exc}. Output: {raw[:500]}"
        ) from exc
