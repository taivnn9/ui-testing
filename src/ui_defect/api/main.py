"""FastAPI application — POST /analyze endpoint."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .pipeline import run_pipeline
from .schemas import AnalyzeResponse, IssueOut, SummaryOut

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ui_defect")

# Verbose error detail trong HTTP response — BẬT ở giai đoạn dev (mặc định "1").
# Đặt DEBUG_ERRORS=0 khi lên production để giấu traceback.
DEBUG_ERRORS = os.environ.get("DEBUG_ERRORS", "1") not in ("0", "false", "False", "")


def _error_detail(exc: Exception, stage: str) -> dict:
    """Gói lỗi thành payload chi tiết để vừa log vừa trả cho client (khi DEBUG_ERRORS)."""
    detail: dict = {
        "error": f"{stage}_failed",
        "stage": stage,
        "type": type(exc).__name__,
        "message": str(exc) or repr(exc),
    }
    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        detail["cause"] = f"{type(cause).__name__}: {cause}"
    if DEBUG_ERRORS:
        detail["traceback"] = traceback.format_exc().splitlines()
    return detail


app = FastAPI(
    title="UI Defect Analyzer",
    description="Phát hiện lỗi UI tự động từ ảnh chụp màn hình.",
    version="0.1.0",
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Bắt mọi lỗi chưa được xử lý (ngoài các try cụ thể) → log full traceback + trả chi tiết."""
    logger.exception("Unhandled error tại %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": _error_detail(exc, "unhandled")})

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    path = _WEB_DIR / "index.html"
    if not path.is_file():
        raise HTTPException(500, detail="frontend_not_found")
    return FileResponse(path)


_MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_SIZE_MB", "10")) * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    screenshot: UploadFile = File(..., description="Ảnh PNG/JPG màn hình — trường duy nhất bắt buộc"),  # noqa: B008
    # Tất cả optional — hệ thống tự detect từ ảnh nếu không cấp
    platform: str = Form("android", description="android (default) | ios | web"),
    viewport_w: int | None = Form(None, description="Tự lấy img.width nếu bỏ trống"),
    viewport_h: int | None = Form(None, description="Tự lấy img.height nếu bỏ trống"),
    theme: str | None = Form(None, description="light|dark — tự detect từ luminance"),
    dpr: float = Form(1.0),
    locale: str | None = Form(None, description="vd vi-VN — tự detect từ OCR text"),
    safe_area_top: int | None = Form(None, description="Override A13 nếu muốn chính xác"),
    safe_area_bottom: int | None = Form(None),
    font_scale: float = Form(1.0),
    route: str | None = Form(None),
    min_severity: str = Form("low"),
    min_confidence: float = Form(0.4),
    agent_backend: str = Form("", description="codex | cline | none — trống = dùng env AGENT_BACKEND"),
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
    except UnidentifiedImageError as exc:
        logger.warning("Ảnh không hợp lệ: %s", exc)
        raise HTTPException(400, detail={"error": "invalid_image", "message": str(exc)}) from exc
    except Exception as exc:
        logger.exception("Lỗi khi đọc ảnh")
        raise HTTPException(400, detail=_error_detail(exc, "image_decode")) from exc

    if platform not in ("android", "ios", "web"):
        raise HTTPException(400, detail="platform phải là android, ios hoặc web")
    _agent_backend = agent_backend.strip().lower() if agent_backend.strip() else None
    if _agent_backend and _agent_backend not in ("codex", "cline", "none"):
        raise HTTPException(400, detail="agent_backend phải là codex, cline hoặc none")
    _platform = platform

    # Auto-derive từ ảnh
    import numpy as np
    _vp_w = viewport_w or img.width
    _vp_h = viewport_h or img.height
    _theme = theme or ("dark" if np.array(img.convert("L")).mean() / 255.0 < 0.35 else "light")
    _locale = locale or "en-US"

    # Chạy pipeline
    _run_agents = (_agent_backend or "codex") != "none"
    logger.info(
        "Bắt đầu phân tích screen platform=%s vp=%dx%d agent_backend=%s",
        _platform, _vp_w, _vp_h, _agent_backend or "env",
    )
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
            run_agents=_run_agents,
            agent_backend=_agent_backend,
        )
    except Exception as exc:
        logger.exception("Pipeline thất bại (platform=%s, run_agents=%s)", _platform, _run_agents)
        raise HTTPException(500, detail=_error_detail(exc, "pipeline")) from exc

    # Cảnh báo nếu agent VLM lỗi nhưng pipeline vẫn chạy (không 500) — để debug cấu hình LLM
    agent_errors = output.pipeline_meta.get("agent_errors", [])
    if agent_errors:
        logger.warning(
            "%d agent VLM lỗi: %s",
            len(agent_errors),
            "; ".join(f"{a['agent_id']}: {a['error']}" for a in agent_errors),
        )

    # Filter theo min_severity
    return _build_analyze_response(output, _platform, _vp_w, _vp_h, dpr, _locale, _theme, route, min_severity)


def _build_analyze_response(
    output: Any,
    platform: str, vp_w: int, vp_h: int, dpr: float,
    locale: str, theme: str, route: Any, min_severity: str,
) -> AnalyzeResponse:
    _sev_order = ["trivial", "low", "medium", "high", "critical"]
    min_idx = _sev_order.index(min_severity) if min_severity in _sev_order else 0
    filtered = [i for i in output.issues if _sev_order.index(i.severity) >= min_idx]
    now = datetime.now(UTC).isoformat()
    return AnalyzeResponse(
        screen_id=output.screen_id,
        analyzed_at=now,
        screen={
            "platform": platform,
            "viewport": {"w": vp_w, "h": vp_h, "dpr": dpr},
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


@app.post("/analyze/stream", include_in_schema=False)
async def analyze_stream(
    screenshot: UploadFile = File(...),  # noqa: B008
    platform: str = Form("android"),
    viewport_w: int | None = Form(None),
    viewport_h: int | None = Form(None),
    theme: str | None = Form(None),
    dpr: float = Form(1.0),
    locale: str | None = Form(None),
    safe_area_top: int | None = Form(None),
    safe_area_bottom: int | None = Form(None),
    font_scale: float = Form(1.0),
    route: str | None = Form(None),
    min_severity: str = Form("low"),
    min_confidence: float = Form(0.4),
    agent_backend: str = Form(""),
):
    """Giống /analyze nhưng trả text/event-stream, mỗi dòng là 1 SSE event log hoặc kết quả cuối."""
    raw = await screenshot.read()
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(413, detail="file_too_large")

    try:
        from io import BytesIO
        img = Image.open(BytesIO(raw))
        img.load()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(400, detail={"error": "invalid_image", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(400, detail=_error_detail(exc, "image_decode")) from exc

    _agent_backend = agent_backend.strip().lower() if agent_backend.strip() else None
    if _agent_backend and _agent_backend not in ("codex", "cline", "none"):
        raise HTTPException(400, detail="agent_backend phải là codex, cline hoặc none")

    import numpy as np
    _platform = platform
    _vp_w = viewport_w or img.width
    _vp_h = viewport_h or img.height
    _theme = theme or ("dark" if np.array(img.convert("L")).mean() / 255.0 < 0.35 else "light")
    _locale = locale or "en-US"
    _run_agents = (_agent_backend or "cline") != "none"

    loop = asyncio.get_event_loop()
    log_queue: asyncio.Queue = asyncio.Queue()

    def _log_cb(msg: str):
        loop.call_soon_threadsafe(log_queue.put_nowait, ("log", msg))

    def _run():
        try:
            out = run_pipeline(
                img=img, platform=_platform,
                viewport_w=_vp_w, viewport_h=_vp_h, dpr=dpr,
                locale=_locale, theme=_theme, font_scale=font_scale, route=route,
                safe_area_top=safe_area_top, safe_area_bottom=safe_area_bottom,
                min_confidence=min_confidence, run_agents=_run_agents,
                agent_backend=_agent_backend, log_callback=_log_cb,
            )
            loop.call_soon_threadsafe(log_queue.put_nowait, ("result", out))
        except Exception as exc:
            logger.exception("Stream pipeline lỗi")
            loop.call_soon_threadsafe(log_queue.put_nowait, ("error", exc))

    threading.Thread(target=_run, daemon=True).start()

    def _sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    async def _event_stream():
        while True:
            kind, payload = await log_queue.get()
            if kind == "log":
                yield _sse({"type": "log", "msg": payload})
            elif kind == "result":
                resp = _build_analyze_response(
                    payload, _platform, _vp_w, _vp_h, dpr,
                    _locale, _theme, route, min_severity,
                )
                yield _sse({"type": "result", "data": resp.model_dump()})
                break
            elif kind == "error":
                yield _sse({"type": "error", "detail": _error_detail(payload, "pipeline")})
                break

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
