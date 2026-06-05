"""
Unit tests cho /analyze/stream (SSE) + log_callback xuyên pipeline → Cline.

Không cần Cline binary thật: subprocess.Popen được mock.
Ảnh đầu vào là PNG tổng hợp tạo bằng PIL (có status bar, button, text block).
"""
from __future__ import annotations

import io
import json
import subprocess

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from ui_defect.api.main import app

client = TestClient(app)


# ── PNG tổng hợp ─────────────────────────────────────────────────────────────

def _make_png(w: int = 390, h: int = 844, *, with_ui: bool = True) -> bytes:
    """Tạo ảnh PNG giả màn hình Android: status bar, nút, text block."""
    img = Image.new("RGB", (w, h), color=(245, 245, 245))
    if with_ui:
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, 44], fill=(30, 30, 30))           # status bar
        draw.rectangle([0, h - 60, w, h], fill=(30, 30, 30))        # nav bar
        draw.rectangle([20, 100, w - 20, 148], fill=(33, 150, 243)) # button
        draw.rectangle([20, 200, 200, 220], fill=(180, 180, 180))   # text line
        draw.rectangle([20, 240, 280, 260], fill=(200, 200, 200))   # text line
        draw.rectangle([20, 300, w - 20, 360], fill=(255, 255, 255), outline=(200, 200, 200))  # input
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── SSE parser ───────────────────────────────────────────────────────────────

def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ── Popen mock ───────────────────────────────────────────────────────────────

class _FakePopen:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self._stdout = stdout
        self.stderr = iter(stderr.splitlines(keepends=True)) if stderr else iter([])
        self.returncode = returncode

    def communicate(self, input=None, timeout=None):
        return self._stdout, ""

    def kill(self):
        pass


_CLINE_OK_OUTPUT = json.dumps({
    "summary": "1 lỗi touch target nhỏ",
    "findings": [{
        "issue_type": "touch_target_min",
        "element_id": None,
        "verdict": "confirmed",
        "severity": "high",
        "confidence": 0.85,
        "reasoning": "Touch target 28x28 < 44dp",
        "original_candidate_rule": "R1-LAY01",
        "temporal": False,
    }],
})


# ── Test 1: log_callback gọi đủ stage (không cần agent) ─────────────────────

def test_pipeline_log_callback_all_stages():
    """Tất cả stage A*/R*/Agent phải gọi log_callback ít nhất 1 lần."""
    from ui_defect.api.pipeline import run_pipeline

    logs: list[str] = []
    img = Image.new("RGB", (390, 844), color=(245, 245, 245))

    run_pipeline(
        img=img,
        platform="android",
        viewport_w=390,
        viewport_h=844,
        run_agents=False,
        log_callback=logs.append,
    )

    expected_prefixes = ["[A13]", "[A5]", "[A3]", "[A6]", "[A12]",
                         "[A4]", "[A7]", "[A8]", "[A9]", "[A10]", "[A0]", "[R1-R4]"]
    missing = [p for p in expected_prefixes if not any(p in m for m in logs)]
    assert not missing, f"Stage chưa log: {missing}\nLogs nhận được: {logs}"


# ── Test 2: /analyze/stream không có agent ───────────────────────────────────

def test_stream_no_agent_returns_sse_log_and_result():
    """/analyze/stream với agent=none phải trả log events + 1 result event."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "none", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(with_ui=True), "image/png")},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    log_events = [e for e in events if e.get("type") == "log"]
    result_events = [e for e in events if e.get("type") == "result"]

    assert len(result_events) == 1, "Phải có đúng 1 result event"
    data = result_events[0]["data"]
    assert "issues" in data
    assert "summary" in data
    assert "pipeline_meta" in data

    assert len(log_events) > 0, "Phải có ít nhất 1 log event"
    assert any("[A13]" in e["msg"] for e in log_events), "[A13] không có trong log"
    assert any("[R1-R4]" in e["msg"] for e in log_events), "[R1-R4] không có trong log"


def test_stream_result_has_correct_structure():
    """result event phải có đủ field theo AnalyzeResponse schema."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "ios", "agent_backend": "none"},
        files={"screenshot": ("screen.png", _make_png(390, 844), "image/png")},
    )
    events = _parse_sse(resp.text)
    result = next(e["data"] for e in events if e.get("type") == "result")

    assert "screen_id" in result
    assert "analyzed_at" in result
    assert "screen" in result
    assert result["screen"]["platform"] == "ios"
    assert isinstance(result["issues"], list)
    assert isinstance(result["summary"]["total_issues"], int)


# ── Test 3: /analyze/stream với Cline mock ───────────────────────────────────

def test_stream_cline_mock_agent_log_appears(monkeypatch):
    """/analyze/stream với backend=cline (Popen mock) phải có log [Agent]."""
    monkeypatch.setenv("CLINE_VERBOSE", "0")
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **kw: _FakePopen(stdout=_CLINE_OK_OUTPUT),
    )

    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "cline", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(with_ui=True), "image/png")},
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    log_msgs = [e["msg"] for e in events if e.get("type") == "log"]

    assert any("[Agent]" in m for m in log_msgs), \
        f"Không có [Agent] log. Log nhận được:\n" + "\n".join(log_msgs[:10])
    assert any("[Done]" in m for m in log_msgs), "Không có [Done] log"

    result_events = [e for e in events if e.get("type") == "result"]
    assert len(result_events) == 1


# ── Test 4: Cline stderr → [cline] log trong SSE ─────────────────────────────

def test_stream_cline_stderr_forwarded_to_log(monkeypatch):
    """Stderr Cline phải xuất hiện trong SSE log events với prefix [cline]."""
    stderr_lines = "Loading model...\nRunning analysis...\nGenerating response...\n"
    monkeypatch.setenv("CLINE_VERBOSE", "0")
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **kw: _FakePopen(stdout=_CLINE_OK_OUTPUT, stderr=stderr_lines),
    )

    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "cline", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    cline_logs = [e["msg"] for e in events if e.get("type") == "log" and e["msg"].startswith("[cline]")]

    assert len(cline_logs) > 0, \
        "Không có [cline] log. Tất cả log:\n" + "\n".join(e.get("msg","") for e in events if e.get("type")=="log")
    assert any("Loading model" in m for m in cline_logs)
    assert any("Running analysis" in m for m in cline_logs)


# ── Test 5: error cases ───────────────────────────────────────────────────────

def test_stream_invalid_image_returns_400():
    """/analyze/stream với dữ liệu không phải ảnh → HTTP 400."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "none"},
        files={"screenshot": ("bad.png", b"this is not an image", "image/png")},
    )
    assert resp.status_code == 400


def test_stream_invalid_backend_returns_400():
    """/analyze/stream với agent_backend không hợp lệ → HTTP 400."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "unknown_backend"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
    )
    assert resp.status_code == 400


def test_stream_missing_screenshot_returns_422():
    """/analyze/stream không gửi file → HTTP 422 (FastAPI validation)."""
    resp = client.post("/analyze/stream", data={"platform": "android"})
    assert resp.status_code == 422
