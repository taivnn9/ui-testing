"""FastAPI application — POST /analyze endpoint."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .pipeline import run_pipeline
from .schemas import AnalyzeResponse, IssueOut, SummaryOut

app = FastAPI(
    title="UI Defect Analyzer",
    description="Phát hiện lỗi UI tự động từ ảnh chụp màn hình.",
    version="0.1.0",
)

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(_WEB_DIR / "index.html")


_MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_SIZE_MB", "10")) * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    screenshot: UploadFile = File(..., description="Ảnh PNG/JPG màn hình — trường duy nhất bắt buộc"),
    # Tất cả optional — hệ thống tự detect từ ảnh nếu không cấp
    platform: str = Form("android", description="android (default) | ios | web"),
    viewport_w: Optional[int] = Form(None, description="Tự lấy img.width nếu bỏ trống"),
    viewport_h: Optional[int] = Form(None, description="Tự lấy img.height nếu bỏ trống"),
    theme: Optional[str] = Form(None, description="light|dark — tự detect từ luminance"),
    dpr: float = Form(1.0),
    locale: Optional[str] = Form(None, description="vd vi-VN — tự detect từ OCR text"),
    safe_area_top: Optional[int] = Form(None, description="Override A13 nếu muốn chính xác"),
    safe_area_bottom: Optional[int] = Form(None),
    font_scale: float = Form(1.0),
    route: Optional[str] = Form(None),
    min_severity: str = Form("low"),
    min_confidence: float = Form(0.4),
    run_vlm: bool = Form(True),
):
    # Đọc ảnh
    raw = await screenshot.read()
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(413, detail="file_too_large")

    try:
        from io import BytesIO
        img = Image.open(BytesIO(raw))
        img.load()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
    except (UnidentifiedImageError, Exception) as exc:
        raise HTTPException(400, detail=f"invalid_image: {exc}") from exc

    if platform not in ("android", "ios", "web"):
        raise HTTPException(400, detail="platform phải là android, ios hoặc web")
    _platform = platform

    # Auto-derive từ ảnh
    import numpy as np
    _vp_w = viewport_w or img.width
    _vp_h = viewport_h or img.height
    _theme = theme or ("dark" if np.array(img.convert("L")).mean() / 255.0 < 0.35 else "light")
    _locale = locale or "en-US"

    # Chạy pipeline
    try:
        output = run_pipeline(
            img=img,
            platform=_platform,
            viewport_w=_vp_w,
            viewport_h=_vp_h,
            dpr=dpr,
            locale=_locale,
            theme=_theme,
            font_scale=font_scale,
            route=route,
            safe_area_top=safe_area_top,
            safe_area_bottom=safe_area_bottom,
            min_confidence=min_confidence,
            run_agents=run_vlm,
        )
    except Exception as exc:
        raise HTTPException(500, detail=f"pipeline_failed: {exc}") from exc

    # Filter theo min_severity
    _sev_order = ["trivial", "low", "medium", "high", "critical"]
    min_idx = _sev_order.index(min_severity) if min_severity in _sev_order else 0
    filtered = [i for i in output.issues if _sev_order.index(i.severity) >= min_idx]

    now = datetime.now(timezone.utc).isoformat()
    return AnalyzeResponse(
        screen_id=output.screen_id,
        analyzed_at=now,
        screen={
            "platform": _platform,  # android mặc định
            "viewport": {"w": _vp_w, "h": _vp_h, "dpr": dpr},
            "locale": _locale,
            "theme": _theme,
            "route": route,
        },
        summary=SummaryOut(
            total_issues=len(filtered),
            by_severity=output.summary.get("by_severity", {}),
            top_categories=output.summary.get("top_categories", []),
            confidence_avg=output.summary.get("confidence_avg", 0.0),
        ),
        issues=[
            IssueOut(
                id=i.id,
                issue_type=i.issue_type,
                title=i.title,
                severity=i.severity,
                confidence=i.confidence,
                tags=i.tags,
                temporal=i.temporal,
                element_id=i.element_id,
                element_role=i.element_role,
                element_bbox=i.element_bbox,
                element_text=i.element_text,
                evidence=i.evidence,
                description=i.description,
                sources=i.sources,
            )
            for i in filtered
        ],
        pipeline_meta=output.pipeline_meta,
    )
