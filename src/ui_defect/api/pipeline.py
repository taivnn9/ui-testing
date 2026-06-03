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
    duplicates_to_candidates,
    find_duplicates,
)
from ..analyzers.a12_interactivity import classify_interactivity
from ..schema.models import CandidateIssue, SafeArea, Screen, Viewport
from ..rules import run_rule_engine
from ..agents.runner import run_all_agents
from ..agents.critic import run_critic
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
    vlm_model: Optional[str] = None,
    screen_id: Optional[str] = None,
) -> AnalyzeOutput:
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
    )
    analyzers_ran.append("A13")

    # dpr sau khi A13 resolve (có thể khác với dpr user cấp)
    _dpr = screen.viewport.dpr

    # ── A5 — OCR ─────────────────────────────────────────────────────────────
    text_segments = extract_text(img, screen.viewport, lang=locale[:2].lower())
    analyzers_ran.append("A5")

    # ── A3 — Box/Layout Detector ─────────────────────────────────────────────
    elements = detect_layout(img, screen.viewport, text_segments=text_segments)
    analyzers_ran.append("A3")

    # ── A6 — Icon Detector ────────────────────────────────────────────────────
    text_bboxes = [s.bbox for s in text_segments if s.level == "line"]
    icon_regions = detect_icons(img, screen.viewport, elements=elements, text_bboxes=text_bboxes)
    icon_elems = icon_regions_to_elements(icon_regions, img.width, img.height)
    elements = elements + icon_elems
    analyzers_ran.append("A6")

    # ── A12 — Interactivity Classifier ────────────────────────────────────────
    icon_ids = {r.id for r in icon_regions}
    elements = classify_interactivity(
        img, elements, text_segments=text_segments,
        icon_region_ids=icon_ids, viewport_h=screen.viewport.h,
    )
    analyzers_ran.append("A12")

    # ── A4 — Pixel Color Sampler ─────────────────────────────────────────────
    color_results, color_issues = sample_colors(img, elements, theme=screen.theme)
    elements = enrich_elements(elements, color_results)
    analyzers_ran.append("A4")

    # ── A7 — Image Meta Reader ────────────────────────────────────────────────
    elements, img_issues = analyze_images(img, elements, dpr=_dpr)
    analyzers_ran.append("A7")

    # ── A8 — Glyph Inspector ─────────────────────────────────────────────────
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

    # ── A9 — Pixel Pattern Detector ───────────────────────────────────────────
    pattern_detections = detect_patterns(img, screen.viewport)
    pattern_issues = patterns_to_candidates(pattern_detections)
    analyzers_ran.append("A9")

    # ── A10 — Perceptual Hash ─────────────────────────────────────────────────
    hash_results = compute_hashes(img, elements)
    dup_pairs = find_duplicates(hash_results)
    dup_issues = duplicates_to_candidates(dup_pairs)
    analyzers_ran.append("A10")

    # ── A0 — Normalize ────────────────────────────────────────────────────────
    all_issues: list[CandidateIssue] = (
        color_issues + img_issues + glyph_candidates + pattern_issues + dup_issues
    )
    doc = normalize(
        screen=screen,
        image_path=f"screens/{_screen_id}.png",
        img_w=img.width,
        img_h=img.height,
        elements=elements,
        candidate_issues=all_issues,
    )
    analyzers_ran.append("A0")

    # ── Rule Engine R1–R4 ────────────────────────────────────────────────────
    doc = run_rule_engine(doc)
    rules_ran = ["R1", "R2", "R3", "R4"]

    # ── Judgment Agents G1–G6 ─────────────────────────────────────────────────
    agents_ran: list[str] = []
    findings = []
    if run_agents:
        from ..agents.runner import run_all_agents
        from ..agents.critic import run_critic
        results = run_all_agents(doc, img, agent_ids=agent_ids, model=vlm_model)
        agents_ran = [r.agent_id for r in results if r.error is None]
        findings = run_critic(results, min_confidence=min_confidence)

    # ── S1 — Summary ──────────────────────────────────────────────────────────
    t1 = time.monotonic()
    output = build_summary(
        findings=findings,
        doc=doc,
        screen_id=_screen_id,
        rule_only_fallback=not run_agents,
        pipeline_meta={
            "analyzers_ran": analyzers_ran,
            "rules_ran": rules_ran,
            "agents_ran": agents_ran,
            "total_candidates_pre_filter": len(doc.candidate_issues),
            "final_issues": len(findings) if run_agents else len(doc.candidate_issues),
            "mode": "vlm" if run_agents else "rule-only",
            "pipeline_duration_ms": round((t1 - t0) * 1000),
        },
    )
    return output
