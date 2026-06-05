"""Test adapter Cline (cline_client) + routing backends — mock subprocess (không cần Cline thật)."""
from __future__ import annotations

import json
import subprocess

import pytest

from ui_defect.agents import backends, cline_client


class _FakeProc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def test_extract_json_plain():
    assert cline_client._extract_json('{"findings": [], "summary": "ok"}') == {
        "findings": [], "summary": "ok"
    }


def test_extract_json_surrounded_by_log():
    # Cline có thể in log trước/sau JSON → lấy object {...} cân bằng cuối cùng
    out = 'INFO booting\n{"a": 1}\n{"findings": [1], "summary": "x"}\nDONE'
    assert cline_client._extract_json(out) == {"findings": [1], "summary": "x"}


def test_extract_json_raises_when_absent():
    with pytest.raises(RuntimeError, match="không chứa JSON"):
        cline_client._extract_json("no json here")


def test_build_prompt_embeds_schema():
    p = cline_client._build_prompt("ANALYZE", {"type": "object"})
    assert "ANALYZE" in p and "JSON Schema" in p and '"type": "object"' in p


def test_run_cline_parses_stdout(monkeypatch):
    """Default: cline -y "<prompt>" (CLINE_ARGS="-y", CLINE_PROMPT_MODE="arg")."""
    captured = {}

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, cwd=None):
        captured["cmd"] = cmd
        captured["input"] = input
        return _FakeProc(stdout='log line\n{"findings": [], "summary": "done"}')

    monkeypatch.setenv("CLINE_BIN", "cline-x")
    monkeypatch.delenv("CLINE_ARGS", raising=False)
    monkeypatch.delenv("CLINE_PROMPT_MODE", raising=False)
    monkeypatch.setattr(subprocess, "run", fake_run)

    out = cline_client.run_cline("PROMPT", {"type": "object"})
    assert out == {"findings": [], "summary": "done"}
    assert captured["cmd"][:2] == ["cline-x", "-y"]    # default -y flag
    assert "PROMPT" in captured["cmd"][-1]              # prompt là arg cuối
    assert captured["input"] is None                    # KHÔNG qua stdin


def test_run_cline_stdin_mode(monkeypatch):
    """Override: CLINE_PROMPT_MODE=stdin → prompt qua stdin."""
    captured = {}

    def fake_run(cmd, input=None, **kw):
        captured["cmd"] = cmd
        captured["input"] = input
        return _FakeProc(stdout='{"findings": [], "summary": "ok"}')

    monkeypatch.setenv("CLINE_BIN", "cline-x")
    monkeypatch.setenv("CLINE_ARGS", "task --headless")
    monkeypatch.setenv("CLINE_PROMPT_MODE", "stdin")
    monkeypatch.setattr(subprocess, "run", fake_run)

    cline_client.run_cline("PROMPT", None)
    assert captured["cmd"][:3] == ["cline-x", "task", "--headless"]
    assert "PROMPT" in captured["input"]


def test_run_cline_nonzero_exit_raises(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _FakeProc(stderr="boom", returncode=2))
    with pytest.raises(RuntimeError, match="exit=2"):
        cline_client.run_cline("p", None)


def test_run_cline_missing_binary_raises(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("nope")
    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(RuntimeError, match="Không tìm thấy Cline"):
        cline_client.run_cline("p", None)


def test_backend_routes_to_cline(monkeypatch):
    monkeypatch.setenv("AGENT_BACKEND", "cline")
    monkeypatch.setattr(cline_client, "run_cline",
                        lambda prompt, schema: {"routed": "cline"})
    assert backends.active_backend() == "cline"
    assert backends.run_backend("p", None) == {"routed": "cline"}


def test_backend_none_short_circuits(monkeypatch):
    monkeypatch.setenv("AGENT_BACKEND", "none")
    assert backends.run_backend("p", None)["findings"] == []
