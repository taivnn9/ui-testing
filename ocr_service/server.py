"""
OCR sidecar — chạy TRÊN MÁY có PaddleOCR. App chính (ui_defect) gọi qua HTTP.

Mục đích: tách PaddleOCR (nặng ~1GB) sang máy riêng. App không cần cài paddle,
chỉ set env OCR_BASE_URL trỏ tới server này.

Chạy:
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8081

Contract (khớp với ui_defect/analyzers/a5_ocr.py::_run_ocr_remote):
    POST /ocr   { "image": "<base64 PNG/JPEG>", "lang": "en" }
            →   { "engine": "paddle", "segments": [
                    { "text": str,
                      "bbox": { "x":float, "y":float, "w":float, "h":float },
                      "confidence": float } ] }
    GET  /health → { "status": "ok" }

Toạ độ bbox: pixel trong hệ ảnh gốc app gửi lên (full image).
"""
from __future__ import annotations

import base64
import io

import numpy as np
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

app = FastAPI(title="UI-Defect OCR sidecar", version="0.1.0")

# Cache PaddleOCR theo lang (khởi tạo nặng → tái dùng giữa các request).
_ocr_cache: dict[str, object] = {}


def _get_ocr(lang: str):
    from paddleocr import PaddleOCR  # import lười — chỉ máy này cần paddle

    if lang not in _ocr_cache:
        _ocr_cache[lang] = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _ocr_cache[lang]


class OcrRequest(BaseModel):
    image: str          # base64 (PNG hoặc JPEG)
    lang: str = "en"    # mã lang PaddleOCR: en, vi, ch, japan, korean, ...


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ocr-sidecar"}


@app.post("/ocr")
def ocr(req: OcrRequest) -> dict:
    try:
        raw = base64.b64decode(req.image)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, detail=f"ảnh base64 không hợp lệ: {exc}") from exc

    arr = np.array(img)
    try:
        result = _get_ocr(req.lang).ocr(arr, cls=True)
    except Exception as exc:
        raise HTTPException(500, detail=f"paddle_ocr_failed: {exc}") from exc

    segments: list[dict] = []
    if result and result[0]:
        for line in result[0]:
            if line is None:
                continue
            points, (text, conf) = line
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            segments.append({
                "text": text,
                "bbox": {
                    "x": float(min(xs)), "y": float(min(ys)),
                    "w": float(max(xs) - min(xs)),
                    "h": float(max(ys) - min(ys)),
                },
                "confidence": float(conf),
            })

    return {"engine": "paddle", "segments": segments}
