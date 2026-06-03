"""ui_defect — nạp .env sớm để config (AGENT_BACKEND, CODEX_*, OCR_BASE_URL, ...) áp dụng tự động.

Nạp ngay khi import package, trước khi bất kỳ submodule nào đọc os.environ.
"""
from __future__ import annotations

try:
    from pathlib import Path

    from dotenv import load_dotenv

    # .env ở repo root (parents[2] = .../ui-testing) — đúng cả khi cài editable `pip install -e .`
    _repo_env = Path(__file__).resolve().parents[2] / ".env"
    if _repo_env.is_file():
        load_dotenv(_repo_env)
    load_dotenv()  # fallback: .env theo thư mục hiện tại (không override cái đã nạp)
except ImportError:
    # python-dotenv chưa cài → bỏ qua, vẫn đọc được biến môi trường export sẵn
    pass
