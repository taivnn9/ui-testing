"""Test tầng reasoning mới (Codex CLI text-only): build prompt, parse, xử lý lỗi backend."""
from __future__ import annotations

import pytest

from ui_defect.agents import runner
from ui_defect.agents.codex_client import run_codex
from ui_defect.schema.models import (
    BBox,
    CandidateIssue,
    CanonicalDoc,
    Element,
    Evidence,
    Image,
    SafeArea,
    Screen,
    SeverityRange,
    Viewport,
)


def _doc() -> CanonicalDoc:
    screen = Screen(
        id="scr_t", platform="android",
        viewport=Viewport(w=1080, h=2400, dpr=3.0),
        safe_area=SafeArea(top=72, bottom=48), locale="vi-VN", theme="light",
    )
    el = Element(
        id="e5", role="button", source="vision",
        bbox=BBox(x=20, y=40, w=100, h=30),
        bbox_norm=BBox(x=0.02, y=0.017, w=0.09, h=0.012),
    )
    cand = CandidateIssue(
        rule="R1.touch_target_min", element="e5", severity="high",
        severity_range=SeverityRange(min="medium", max="critical"),
        confidence=1.0, detail="height 30 < 44",
        evidence=Evidence(bbox=BBox(x=20, y=40, w=100, h=30)),
    )
    return CanonicalDoc(
        screen=screen, image=Image(full="x.png", w=1080, h=2400),
        elements=[el], candidate_issues=[cand],
    )


def test_build_prompt_has_skills_and_data():
    prompt = runner.build_review_prompt(_doc())
    assert "R1.touch_target_min" in prompt          # candidate
    assert "e5" in prompt                            # element id
    assert "Vai trò" in prompt or "QA" in prompt     # skill 00-system nhúng vào
    assert "candidate_issues =" in prompt


def test_run_review_parses_stub_findings(monkeypatch):
    def fake_backend(prompt, schema=None, *, backend=None, log_callback=None):
        return {"summary": "ok", "findings": [
            {"issue_type": "R1.touch_target_min", "element_id": "e5",
             "verdict": "confirmed", "severity": "high", "confidence": 0.9,
             "reasoning": "30<44", "original_candidate_rule": "R1.touch_target_min",
             "temporal": False},
            {"issue_type": "x", "element_id": "e5", "verdict": "rejected",
             "severity": "low", "confidence": 0.1, "reasoning": "no",
             "original_candidate_rule": None, "temporal": False},
        ]}
    monkeypatch.setattr(runner, "run_backend", fake_backend)
    monkeypatch.setattr(runner, "active_backend", lambda: "codex")

    results = runner.run_review(_doc())
    assert len(results) == 1
    r = results[0]
    assert r.error is None
    assert r.agent_id == "codex"
    # rejected bị loại, chỉ còn 1 confirmed
    assert len(r.findings) == 1
    assert r.findings[0].issue_type == "R1.touch_target_min"


def test_run_review_backend_error_is_graceful(monkeypatch):
    def boom(prompt, schema=None, *, backend=None):
        raise RuntimeError("Codex exec exit=1: boom")
    monkeypatch.setattr(runner, "run_backend", boom)
    monkeypatch.setattr(runner, "active_backend", lambda: "codex")

    results = runner.run_review(_doc())
    assert len(results) == 1
    assert results[0].error is not None
    assert "boom" in results[0].error
    assert results[0].findings == []


def test_run_codex_missing_binary_raises(monkeypatch):
    monkeypatch.setenv("CODEX_BIN", "definitely-not-a-real-binary-xyz")
    with pytest.raises(RuntimeError, match="Không tìm thấy Codex CLI"):
        run_codex("hi", schema=None, timeout=5)
