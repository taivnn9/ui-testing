from fastapi.testclient import TestClient

from ui_defect.api.main import app

client = TestClient(app)


def test_index_served_at_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "UI Defect Analyzer" in resp.text


def test_static_mount_exists():
    # /static được mount; file không tồn tại trả 404 (không phải route thiếu)
    resp = client.get("/static/does-not-exist.js")
    assert resp.status_code == 404


def test_health_still_works():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
