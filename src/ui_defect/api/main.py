"""FastAPI application — POST /analyze endpoint."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from .pipeline import run_pipeline
from .schemas import AnalyzeResponse, IssueOut, SummaryOut

app = FastAPI(
    title="UI Defect Analyzer",
    description="Phát hiện lỗi UI tự động từ ảnh chụp màn hình.",
    version="0.1.0",
)

_MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_SIZE_MB", "10")) * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    screenshot: UploadFile = File(..., description="Ảnh PNG/JPG màn hình"),
    platform: str = Form(..., description="android | ios | web"),
    viewport_w: int = Form(...),
    viewport_h: int = Form(...),
    dpr: float = Form(2.0),
    locale: str = Form("en-US"),
    theme: str = Form("light"),
    font_scale: float = Form(1.0),
    route: Optional[str] = Form(None),
    safe_area_top: Optional[int] = Form(None),
    safe_area_bottom: Optional[int] = Form(None),
    min_severity: str = Form("low"),
    min_confidence: float = Form(0.4),
    run_vlm: bool = Form(True, description="False để chỉ chạy rule engine, bỏ qua VLM"),
):
    # Validate platform
    if platform not in ("android", "ios", "web"):
        raise HTTPException(400, detail="platform phải là android, ios hoặc web")
    if theme not in ("light", "dark", "system"):
        raise HTTPException(400, detail="theme phải là light, dark hoặc system")

    # Đọc file
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

    # Chạy pipeline
    try:
        output = run_pipeline(
            img=img,
            platform=platform,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            dpr=dpr,
            locale=locale,
            theme=theme,
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

    # Build response
    now = datetime.now(timezone.utc).isoformat()
    return AnalyzeResponse(
        screen_id=output.screen_id,
        analyzed_at=now,
        screen={
            "platform": platform,
            "viewport": {"w": viewport_w, "h": viewport_h, "dpr": dpr},
            "locale": locale,
            "theme": theme,
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
