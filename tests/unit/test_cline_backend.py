"""Test adapter Cline (cline_client) + routing backends — mock subprocess (không cần Cline thật)."""
from __future__ import annotations

import json
import subprocess

import pytest

from ui_defect.agents import backends, cline_client


class _FakePopen:
    """Mock subprocess.Popen cho Popen-based cline_client."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self._stdout = stdout
        self.stderr = iter(stderr.splitlines(keepends=True)) if stderr else iter([])
        self.returncode = returncode

    def communicate(self, input=None, timeout=None):
        return self._stdout, ""

    def kill(self):
        pass


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

    def fake_popen(cmd, stdin=None, stdout=None, stderr=None, text=None, cwd=None):
        captured["cmd"] = cmd
        captured["stdin"] = stdin
        return _FakePopen(stdout='log line\n{"findings": [], "summary": "done"}')

    monkeypatch.setenv("CLINE_BIN", "cline-x")
    monkeypatch.setenv("CLINE_VERBOSE", "0")
    monkeypatch.delenv("CLINE_ARGS", raising=False)
    monkeypatch.delenv("CLINE_PROMPT_MODE", raising=False)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    out = cline_client.run_cline("PROMPT", {"type": "object"})
    assert out == {"findings": [], "summary": "done"}
    assert captured["cmd"][:2] == ["cline-x", "-y"]    # default -y flag
    assert "PROMPT" in captured["cmd"][-1]              # prompt là arg cuối
    assert captured["stdin"] is None                    # KHÔNG qua stdin


def test_run_cline_stdin_mode(monkeypatch):
    """Override: CLINE_PROMPT_MODE=stdin → prompt qua stdin."""
    captured = {}

    def fake_popen(cmd, stdin=None, **kw):
        captured["cmd"] = cmd
        captured["stdin"] = stdin
        return _FakePopen(stdout='{"findings": [], "summary": "ok"}')

    monkeypatch.setenv("CLINE_BIN", "cline-x")
    monkeypatch.setenv("CLINE_ARGS", "task --headless")
    monkeypatch.setenv("CLINE_PROMPT_MODE", "stdin")
    monkeypatch.setenv("CLINE_VERBOSE", "0")
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    cline_client.run_cline("PROMPT", None)
    assert captured["cmd"][:3] == ["cline-x", "task", "--headless"]
    assert captured["stdin"] == subprocess.PIPE


def test_run_cline_nonzero_exit_raises(monkeypatch):
    monkeypatch.setenv("CLINE_VERBOSE", "0")
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **k: _FakePopen(stderr="boom", returncode=2),
    )
    with pytest.raises(RuntimeError, match="exit=2"):
        cline_client.run_cline("p", None)


def test_run_cline_missing_binary_raises(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("nope")
    monkeypatch.setattr(subprocess, "Popen", boom)
    with pytest.raises(RuntimeError, match="Không tìm thấy Cline"):
        cline_client.run_cline("p", None)


def test_backend_routes_to_cline(monkeypatch):
    monkeypatch.setenv("AGENT_BACKEND", "cline")
    monkeypatch.setattr(cline_client, "run_cline",
                        lambda prompt, schema, **kw: {"routed": "cline"})
    assert backends.active_backend() == "cline"
    assert backends.run_backend("p", None) == {"routed": "cline"}


def test_backend_none_short_circuits(monkeypatch):
    monkeypatch.setenv("AGENT_BACKEND", "none")
    assert backends.run_backend("p", None)["findings"] == []
