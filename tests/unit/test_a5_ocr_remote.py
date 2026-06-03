"""
Test backend OCR remote (A5 _run_ocr_remote) + sidecar server.
Không cần paddle thật — mock httpx (client) và mock PaddleOCR (server).
"""
import base64
import io

import httpx
import pytest
from PIL import Image

from src.ui_defect.analyzers import a5_ocr
from src.ui_defect.schema.models import Viewport


def _png_b64(w=40, h=20) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (255, 255, 255)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


# ── Client (A5) ──────────────────────────────────────────────────────────────

def test_run_ocr_remote_parses_segments(monkeypatch):
    payload = {"engine": "paddle", "segments": [
        {"text": "Đăng nhập", "bbox": {"x": 10, "y": 5, "w": 80, "h": 18},
         "confidence": 0.97},
    ]}

    def fake_post(url, json, timeout):
        assert url.endswith("/ocr")
        assert "image" in json and json["lang"] == "vi"
        return _FakeResp(payload)

    monkeypatch.setattr(httpx, "post", fake_post)
    img = Image.new("RGB", (390, 844), (255, 255, 255))
    segs = a5_ocr._run_ocr_remote(img, Viewport(w=390, h=844), "vi", "http://x:8081")

    assert len(segs) == 1
    assert segs[0].text == "Đăng nhập"
    assert segs[0].bbox.w == 80
    assert segs[0].confidence == pytest.approx(0.97)
    assert segs[0].script == "latin"


def test_extract_text_uses_remote_when_env_set(monkeypatch):
    payload = {"segments": [
        {"text": "Hello", "bbox": {"x": 0, "y": 0, "w": 50, "h": 12}, "confidence": 0.9},
    ]}
    monkeypatch.setenv("OCR_BASE_URL", "http://remote:8081")
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: _FakeResp(payload))
    img = Image.new("RGB", (390, 844), (255, 255, 255))
    segs = a5_ocr.extract_text(img, Viewport(w=390, h=844), lang="en")
    assert len(segs) == 1 and segs[0].text == "Hello"
    # bbox_norm phải được điền
    assert segs[0].bbox_norm.w == pytest.approx(50 / 390)


def test_extract_text_remote_failure_falls_back(monkeypatch):
    """Remote lỗi + không có paddle/tesseract local → trả [] (graceful)."""
    monkeypatch.setenv("OCR_BASE_URL", "http://remote:8081")

    def boom(url, json, timeout):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(httpx, "post", boom)
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    segs = a5_ocr.extract_text(img, Viewport(w=100, h=100), lang="en")
    assert segs == []


# ── Sidecar server ────────────────────────────────────────────────────────────

def test_sidecar_health_and_ocr(monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ocr_service"))
    import server

    from fastapi.testclient import TestClient
    client = TestClient(server.app)

    assert client.get("/health").json()["status"] == "ok"

    # Mock PaddleOCR: trả 1 dòng
    class _FakeOCR:
        def ocr(self, arr, cls=True):
            return [[
                [[[10, 5], [90, 5], [90, 23], [10, 23]], ("Xin chào", 0.95)],
            ]]

    monkeypatch.setattr(server, "_get_ocr", lambda lang: _FakeOCR())

    r = client.post("/ocr", json={"image": _png_b64(), "lang": "vi"})
    assert r.status_code == 200
    j = r.json()
    assert j["engine"] == "paddle"
    assert len(j["segments"]) == 1
    seg = j["segments"][0]
    assert seg["text"] == "Xin chào"
    assert seg["bbox"] == {"x": 10.0, "y": 5.0, "w": 80.0, "h": 18.0}
