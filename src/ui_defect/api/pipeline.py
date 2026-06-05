"""
Pipeline orchestrator: nhận PIL Image + params → chạy toàn bộ analyzers,
rule engine, agents, critic, summary → trả AnalyzeOutput.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from PIL import Image

from ..analyzers.a0_normalize import normalize
from ..analyzers.a13_device_meta import resolve_metadata
from ..analyzers.a3_box_layout import detect_layout
from ..analyzers.a4_pixel_color import enrich_elements, sample_colors
from ..analyzers.a5_ocr import extract_text
from ..analyzers.a6_icon_detector import detect_icons, icon_regions_to_elements
from ..analyzers.a7_image_meta import analyze_images
from ..analyzers.a8_glyph_inspector import glyph_issues_to_candidates, inspect_batch
from ..analyzers.a9_pixel_pattern import detect_patterns, patterns_to_candidates
from ..analyzers.a10_perceptual_hash import (
    compute_hashes,
    find_duplicates,
)
from ..analyzers.a12_interactivity import classify_interactivity
from ..schema.models import CandidateIssue, SafeArea, Screen, Viewport
from ..rules import run_rule_engine
from ..agents.summary import AnalyzeOutput, build_summary


def run_pipeline(
    img: Image.Image,
    platform: str,
    viewport_w: int,
    viewport_h: int,
    dpr: float = 1.0,   # khớp default API; A13 (resolve_metadata) có thể override
    locale: str = "en-US",
    theme: str = "light",
    font_scale: float = 1.0,
    route: Optional[str] = None,
    safe_area_top: Optional[int] = None,
    safe_area_bottom: Optional[int] = None,
    min_confidence: float = 0.4,
    agent_ids: Optional[list[str]] = None,
    run_agents: bool = True,
    agent_backend: Optional[str] = None,
    vlm_model: Optional[str] = None,
    screen_id: Optional[str] = None,
    log_callback=None,
) -> AnalyzeOutput:
    _log = log_callback or (lambda _: None)
    t0 = time.monotonic()
    _screen_id = screen_id or ("scr_" + uuid.uuid4().hex[:8])
    analyzers_ran: list[str] = []

    # ── Build Screen object ──────────────────────────────────────────────────
    screen = Screen(
        id=_screen_id,
        platform=platform,
        route=route,
        viewport=Viewport(w=viewport_w, h=viewport_h, dpr=dpr),
        safe_area=SafeArea(
            top=safe_area_top or 0,
            bottom=safe_area_bottom or 0,
        ),
        theme=theme,
        locale=locale,
        font_scale=font_scale,
    )

    # ── A13 — Device metadata ────────────────────────────────────────────────
    _log("[A13] Xác định metadata thiết bị (DPR, safe area)...")
    tester_meta = {}
    if safe_area_top is not None:
        tester_meta["safe_area"] = {"top": safe_area_top, "bottom": safe_area_bottom or 0}
    meta = resolve_metadata(img, screen, tester_meta or None)
    screen = Screen(
        id=_screen_id,
        platform=platform,
        route=route,
        viewport=Viewport(w=viewport_w, h=viewport_h, dpr=meta.viewport.dpr),
        safe_area=meta.safe_area,
        theme=theme,
        locale=locale,
        font_scale=font_scale,
        status_bar_h=float(meta.status_bar_h),   # R1-ENV02
        nav_bar_h=float(meta.nav_bar_h),          # R1-ENV03
    )
    analyzers_ran.append("A13")
    _log(f"[A13] DPR={screen.viewport.dpr}, safe_area top={screen.safe_area.top} bottom={screen.safe_area.bottom}")

    # dpr sau khi A13 resolve (có thể khác với dpr user cấp)
    _dpr = screen.viewport.dpr

    # ── A5 — OCR ─────────────────────────────────────────────────────────────
    _log("[A5] OCR trích xuất văn bản...")
    text_segments = extract_text(img, screen.viewport, lang=locale[:2].lower())
    analyzers_ran.append("A5")
    _log(f"[A5] Tìm thấy {len(text_segments)} text segment")

    # ── A3 — Box/Layout Detector ─────────────────────────────────────────────
    _log("[A3] Phát hiện bố cục (box layout)...")
    elements = detect_layout(img, screen.viewport, text_segments=text_segments)
    analyzers_ran.append("A3")
    _log(f"[A3] Tìm thấy {len(elements)} element")

    # ── A6 — Icon Detector ────────────────────────────────────────────────────
    _log("[A6] Phát hiện icon...")
    text_bboxes = [s.bbox for s in text_segments if s.level == "line"]
    icon_regions = detect_icons(img, screen.viewport, elements=elements, text_bboxes=text_bboxes)
    icon_elems = icon_regions_to_elements(icon_regions, img.width, img.height)
    elements = elements + icon_elems
    analyzers_ran.append("A6")
    _log(f"[A6] Tìm thấy {len(icon_regions)} icon region")

    # ── A12 — Interactivity Classifier ────────────────────────────────────────
    _log("[A12] Phân loại element tương tác...")
    icon_ids = {r.id for r in icon_regions}
    elements = classify_interactivity(
        img, elements, text_segments=text_segments,
        icon_region_ids=icon_ids, viewport_h=screen.viewport.h,
    )
    analyzers_ran.append("A12")

    # ── A4 — Pixel Color Sampler ─────────────────────────────────────────────
    _log("[A4] Phân tích màu pixel...")
    color_results, color_issues = sample_colors(img, elements, theme=screen.theme)
    elements = enrich_elements(elements, color_results)
    analyzers_ran.append("A4")
    _log(f"[A4] {len(color_issues)} color issue candidate")

    # ── A7 — Image Meta Reader ────────────────────────────────────────────────
    _log("[A7] Phân tích metadata ảnh (tỉ lệ, scale mode)...")
    elements, img_issues = analyze_images(img, elements, dpr=_dpr)
    analyzers_ran.append("A7")
    _log(f"[A7] {len(img_issues)} image issue candidate")

    # ── A8 — Glyph Inspector ─────────────────────────────────────────────────
    _log("[A8] Kiểm tra glyph / replacement character...")
    from ..utils.image_io import crop_bbox
    glyph_crops = []
    for seg in text_segments:
        if seg.level == "line" and seg.has_replacement:
            crop = crop_bbox(img, seg.bbox)
            glyph_crops.append((
                f"seg_{id(seg)}", crop, "text",
                _dpr, seg.has_replacement, seg.script,
            ))
    glyph_issues_raw = []
    if glyph_crops:
        from ..analyzers.a8_glyph_inspector import inspect_batch
        glyph_issues_raw = inspect_batch(glyph_crops)
    glyph_candidates = glyph_issues_to_candidates(glyph_issues_raw)
    analyzers_ran.append("A8")
    _log(f"[A8] {len(glyph_candidates)} glyph issue candidate")

    # ── A9 — Pixel Pattern Detector ───────────────────────────────────────────
    _log("[A9] Phát hiện pattern pixel (loading skeleton, broken image)...")
    pattern_detections = detect_patterns(img, screen.viewport)
    pattern_issues = patterns_to_candidates(pattern_detections)
    analyzers_ran.append("A9")
    _log(f"[A9] {len(pattern_issues)} pattern issue candidate")

    # ── A10 — Perceptual Hash ─────────────────────────────────────────────────
    _log("[A10] Tính perceptual hash, phát hiện element trùng lặp...")
    hash_results = compute_hashes(img, elements)
    dup_pairs = find_duplicates(hash_results)
    duplicate_pairs_data = [
        {"a": p.id_a, "b": p.id_b, "hamming": p.hamming_distance} for p in dup_pairs
    ]
    analyzers_ran.append("A10")
    _log(f"[A10] {len(dup_pairs)} cặp element trùng lặp")

    # ── A0 — Normalize ────────────────────────────────────────────────────────
    _log("[A0] Chuẩn hóa canonical doc...")
    all_issues: list[CandidateIssue] = (
        color_issues + img_issues + glyph_candidates + pattern_issues
    )
    doc = normalize(
        screen=screen,
        image_path=f"screens/{_screen_id}.png",
        img_w=img.width,
        img_h=img.height,
        elements=elements,
        candidate_issues=all_issues,
    )
    doc.duplicate_pairs = duplicate_pairs_data   # R3-IMG12 đọc trong rule engine
    analyzers_ran.append("A0")

    # ── Rule Engine R1–R4 ────────────────────────────────────────────────────
    _log(f"[R1-R4] Chạy rule engine trên {len(doc.elements)} element, {len(doc.candidate_issues)} candidate...")
    doc = run_rule_engine(doc)
    rules_ran = ["R1", "R2", "R3", "R4"]
    _log(f"[R1-R4] Rule engine xong: {len(doc.candidate_issues)} candidate issue")

    # ── Reasoning: coding-agent CLI headless (Codex/Cline), text-only — xem F1.1 ──
    agents_ran: list[str] = []
    agent_errors: list[dict] = []
    findings = []
    _backend = "none"
    if run_agents:
        from ..agents.backends import active_backend
        from ..agents.critic import run_critic
        from ..agents.runner import run_review
        _backend = agent_backend or active_backend()
        _log(f"[Agent] Gọi {_backend} reasoning ({len(doc.candidate_issues)} candidate)...")
        results = run_review(doc, model=vlm_model, backend=agent_backend, log_callback=log_callback)
        agents_ran = [r.agent_id for r in results if r.error is None]
        agent_errors = [
            {"agent_id": r.agent_id, "error": r.error}
            for r in results if r.error is not None
        ]
        findings = run_critic(results, min_confidence=min_confidence)
        _log(f"[Agent] Xong: {len(findings)} finding sau critic/filter")

    # ── S1 — Summary ──────────────────────────────────────────────────────────
    t1 = time.monotonic()
    duration_ms = round((t1 - t0) * 1000)
    output = build_summary(
        findings=findings,
        doc=doc,
        screen_id=_screen_id,
        rule_only_fallback=not run_agents,
        pipeline_meta={
            "analyzers_ran": analyzers_ran,
            "rules_ran": rules_ran,
            "agents_ran": agents_ran,
            "agent_errors": agent_errors,
            "total_candidates_pre_filter": len(doc.candidate_issues),
            "final_issues": len(findings) if run_agents else len(doc.candidate_issues),
            "mode": _backend if run_agents else "rule-only",
            "pipeline_duration_ms": duration_ms,
        },
    )
    n_issues = len(findings) if run_agents else len(doc.candidate_issues)
    _log(f"[Done] Pipeline xong {duration_ms}ms — {n_issues} issue")
    return output
