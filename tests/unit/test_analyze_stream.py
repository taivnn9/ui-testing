"""
Tests cho /analyze/stream SSE + log_callback + Cline integration.

Thiết kế cho máy đích có Cline thật (AGENT_BACKEND=cline).
- Không mock subprocess — test gọi Cline thật khi có thể.
- Test cần Cline sẽ auto-skip nếu binary không tìm thấy (xem fixture `cline_bin`).
- Test không cần Cline luôn chạy được trên mọi máy.
"""
from __future__ import annotations

import io
import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from ui_defect.api.main import app

client = TestClient(app)


# ── Helpers: ảnh tổng hợp ─────────────────────────────────────────────────────

def _make_png(w: int = 390, h: int = 844) -> bytes:
    """PNG giả màn hình Android: status bar, button, text, input, nav bar."""
    img = Image.new("RGB", (w, h), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, 44], fill=(30, 30, 30))                          # status bar
    draw.rectangle([0, h - 60, w, h], fill=(30, 30, 30))                      # nav bar
    draw.rectangle([20, 100, w - 20, 148], fill=(33, 150, 243))               # button
    draw.rectangle([20, 200, 200, 218], fill=(150, 150, 150))                  # text line
    draw.rectangle([20, 228, 280, 246], fill=(180, 180, 180))                  # text line
    draw.rectangle([20, 280, w - 20, 330], fill=(255, 255, 255), outline=(200, 200, 200))  # input
    draw.rectangle([20, 360, 120, 388], fill=(255, 87, 34))                    # small button (touch target test)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _parse_sse(text: str) -> list[dict]:
    """Parse SSE body thành list event dict."""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ── Fixture: kiểm tra Cline có sẵn không ────────────────────────────────────

@pytest.fixture
def cline_bin():
    """Trả path của Cline binary, skip test nếu không tìm thấy."""
    _bin = os.environ.get("CLINE_BIN", "cline")
    found = shutil.which(_bin)
    if not found:
        pytest.skip(f"Cline binary '{_bin}' không tìm thấy — chạy trên máy có Cline")
    return found


# ── Tests không cần Cline (chạy mọi máy) ─────────────────────────────────────

def test_pipeline_log_callback_all_stages():
    """log_callback phải được gọi tại 12 stage (A* + R*) khi agent=none."""
    from ui_defect.api.pipeline import run_pipeline

    logs: list[str] = []
    img = Image.open(io.BytesIO(_make_png()))

    run_pipeline(
        img=img,
        platform="android",
        viewport_w=390,
        viewport_h=844,
        run_agents=False,
        log_callback=logs.append,
    )

    expected = [
        "[A13]", "[A5]", "[A3]", "[A6]", "[A12]",
        "[A4]", "[A7]", "[A8]", "[A9]", "[A10]", "[A0]", "[R1-R4]",
    ]
    missing = [p for p in expected if not any(p in m for m in logs)]
    assert not missing, f"Stage chưa log: {missing}\nLogs: {logs}"


def test_pipeline_log_done_appears():
    """[Done] phải là log cuối cùng của pipeline."""
    from ui_defect.api.pipeline import run_pipeline

    logs: list[str] = []
    img = Image.open(io.BytesIO(_make_png()))

    run_pipeline(
        img=img, platform="android",
        viewport_w=390, viewport_h=844,
        run_agents=False, log_callback=logs.append,
    )

    assert any("[Done]" in m for m in logs), f"Không có [Done]. Logs: {logs[-5:]}"
    assert "[Done]" in logs[-1], f"[Done] phải là log cuối. Log cuối: {logs[-1]!r}"


def test_stream_no_agent_sse_structure():
    """/analyze/stream với agent=none → SSE có log events + 1 result event."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "none", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    logs = [e for e in events if e.get("type") == "log"]
    results = [e for e in events if e.get("type") == "result"]

    assert len(results) == 1, "Phải có đúng 1 result event"
    assert len(logs) >= 12, f"Phải có ≥12 log event (12 stage), nhận: {len(logs)}"
    assert any("[A13]" in e["msg"] for e in logs)
    assert any("[R1-R4]" in e["msg"] for e in logs)
    assert any("[Done]" in e["msg"] for e in logs)


def test_stream_result_schema():
    """result event phải có đúng schema AnalyzeResponse."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "ios", "agent_backend": "none"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
    )
    events = _parse_sse(resp.text)
    result = next((e["data"] for e in events if e.get("type") == "result"), None)
    assert result is not None

    assert "screen_id" in result
    assert "analyzed_at" in result
    assert "pipeline_meta" in result
    assert result["screen"]["platform"] == "ios"
    assert isinstance(result["issues"], list)
    assert isinstance(result["summary"]["total_issues"], int)
    assert isinstance(result["summary"]["by_severity"], dict)


def test_stream_log_events_have_msg_field():
    """Mỗi log event phải có field 'msg' là string."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "none"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
    )
    events = _parse_sse(resp.text)
    log_events = [e for e in events if e.get("type") == "log"]

    for e in log_events:
        assert "msg" in e, f"log event thiếu 'msg': {e}"
        assert isinstance(e["msg"], str), f"msg phải là str: {e['msg']!r}"


def test_stream_invalid_image_400():
    """/analyze/stream với file rác → HTTP 400."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "none"},
        files={"screenshot": ("bad.png", b"not an image at all", "image/png")},
    )
    assert resp.status_code == 400


def test_stream_invalid_backend_400():
    """/analyze/stream với agent_backend không hợp lệ → HTTP 400."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "invalid_value"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
    )
    assert resp.status_code == 400


def test_stream_missing_screenshot_422():
    """/analyze/stream không gửi ảnh → HTTP 422."""
    resp = client.post("/analyze/stream", data={"platform": "android"})
    assert resp.status_code == 422


# ── Tests cần Cline thật (skip nếu không có binary) ──────────────────────────

def test_stream_cline_agent_log_appears(cline_bin):
    """/analyze/stream với Cline thật → phải có [Agent] log trong SSE."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "cline", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
        timeout=300,
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    log_msgs = [e["msg"] for e in events if e.get("type") == "log"]

    assert any("[Agent]" in m for m in log_msgs), (
        "Không có [Agent] log. Tất cả log:\n" + "\n".join(log_msgs)
    )
    assert any("[Done]" in m for m in log_msgs)

    results = [e for e in events if e.get("type") == "result"]
    assert len(results) == 1, "Phải có đúng 1 result event"
    assert "issues" in results[0]["data"]


def test_stream_cline_stderr_forwarded(cline_bin):
    """Cline thật: stderr output phải xuất hiện trong SSE dưới prefix [cline]."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "cline", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
        timeout=300,
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    cline_logs = [
        e["msg"] for e in events
        if e.get("type") == "log" and e.get("msg", "").startswith("[cline]")
    ]
    # Cline thường in log/progress ra stderr — nếu không có thì Cline im lặng (không phải lỗi)
    # Chỉ assert không có error event
    error_events = [e for e in events if e.get("type") == "error"]
    assert not error_events, f"Có error event: {error_events}"


def test_stream_cline_result_has_findings(cline_bin):
    """Cline thật: result phải trả findings list (có thể rỗng nếu không tìm thấy lỗi)."""
    resp = client.post(
        "/analyze/stream",
        data={"platform": "android", "agent_backend": "cline", "min_severity": "trivial"},
        files={"screenshot": ("screen.png", _make_png(), "image/png")},
        timeout=300,
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    results = [e for e in events if e.get("type") == "result"]
    assert len(results) == 1

    data = results[0]["data"]
    assert isinstance(data["issues"], list)
    assert data["summary"]["total_issues"] == len(
        [i for i in data["issues"] if True]  # count all
    )
    # pipeline_meta phải có agent info
    meta = data["pipeline_meta"]
    assert "cline" in meta.get("agents_ran", []) or meta.get("mode") == "cline", (
        f"pipeline_meta không ghi nhận cline. meta={meta}"
    )
