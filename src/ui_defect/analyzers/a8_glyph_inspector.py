"""
A8 — Pixel/Glyph Inspector
Phân tích pixel để CHỐT tofu/glyph thiếu / chữ mờ / emoji-box / banding.
A5 chỉ NGHI, A8 KHẲNG ĐỊNH.
Spec: docs/analyzers/A8-pixel-glyph-inspector.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import BBox, CandidateIssue, Evidence, SeverityRange
from ..schema.thresholds import BLUR_CLEAR, BLUR_WARN


# ── Cấu hình ngưỡng ──────────────────────────────────────────────────────────

@dataclass
class A8Config:
    # Tofu detection
    tofu_uniformity_threshold: float = 0.92  # filled_area / bbox_area
    min_component_area: int = 9              # px² tối thiểu cho connected component
    min_height_px: int = 8                   # chiều cao tối thiểu (device px; scale với dpr)
    # Blur detection
    blur_threshold_per_dpr: dict = field(default_factory=lambda: {1: 50.0, 2: 100.0, 3: 200.0})
    # Banding
    banding_std_threshold: float = 15.0     # std(row mean) > 15 → nghi banding
    banding_step_ratio: float = 0.3         # bước nhảy > 30% range → banding cứng
    # Outline box
    outline_erode_iter: int = 2


# ── Kiểu output ───────────────────────────────────────────────────────────────

@dataclass
class GlyphIssue:
    element_id: str
    issue_type: str      # tofu_box | outline_box | emoji_square | blur_jagged | banding | overlap_glyph
    confidence: float
    verdict: str         # confirmed | likely | uncertain | rejected
    rule_id: str
    evidence: dict = field(default_factory=dict)
    crop: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _laplacian_variance(crop_gray: np.ndarray) -> float:
    """Đo độ nét. Thấp → mờ/jagged."""
    return float(cv2.Laplacian(crop_gray.astype(np.float64), cv2.CV_64F).var())


def _detect_tofu_components(
    crop_gray: np.ndarray,
    cfg: A8Config,
) -> list[dict]:
    """
    Tìm connected component hình chữ nhật đặc đều → tofu candidate.
    Trả list dict với uniformity, bbox, edge_internal.
    """
    # Threshold Otsu
    _, thresh = cv2.threshold(crop_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(thresh, connectivity=8)

    results = []
    for i in range(1, n):  # bỏ background (0)
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < cfg.min_component_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        if h < cfg.min_height_px or w < 2:
            continue
        bbox_area = w * h
        uniformity = area / bbox_area if bbox_area > 0 else 0.0

        # Đếm edge nội bộ (bên trong component)
        component_mask = (labels[y:y+h, x:x+w] == i).astype(np.uint8) * 255
        edges = cv2.Canny(component_mask, 30, 100)
        edge_internal = int(edges.sum() / 255)

        results.append({
            "x": x, "y": y, "w": w, "h": h,
            "area": area,
            "bbox_area": bbox_area,
            "uniformity": round(uniformity, 3),
            "edge_internal": edge_internal,
        })
    return results


def _is_outline_box(crop_gray: np.ndarray, cfg: A8Config) -> bool:
    """
    Kiểm tra outline box (.notdef): erode → dilate → nếu lõi biến mất → rỗng bên trong.
    """
    _, thresh = cv2.threshold(crop_gray, 128, 255, cv2.THRESH_BINARY_INV)
    if thresh.sum() == 0:
        return False
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    eroded = cv2.erode(thresh, kernel, iterations=cfg.outline_erode_iter)
    # Nếu sau erode gần hết pixel → là outline mỏng
    original_fill = float(thresh.sum())
    eroded_fill = float(eroded.sum())
    if original_fill == 0:
        return False
    return eroded_fill / original_fill < 0.15


def _detect_banding(crop_gray: np.ndarray, cfg: A8Config) -> tuple[bool, float]:
    """
    Phát hiện banding: row mean có bước nhảy đột ngột.
    Trả (is_banding, confidence).
    """
    if crop_gray.shape[0] < 4:
        return False, 0.0
    row_means = crop_gray.mean(axis=1).astype(float)
    diffs = np.abs(np.diff(row_means))
    value_range = row_means.max() - row_means.min()
    if value_range < 10:
        return False, 0.0
    max_step = diffs.max()
    step_ratio = max_step / value_range if value_range > 0 else 0.0
    is_banding = step_ratio >= cfg.banding_step_ratio
    conf = min(0.9, step_ratio)
    return is_banding, round(conf, 2)


def _blur_threshold(dpr: float, cfg: A8Config) -> float:
    dpr_i = max(1, min(3, int(round(dpr))))
    return cfg.blur_threshold_per_dpr.get(dpr_i, BLUR_WARN)


# ── Public API ────────────────────────────────────────────────────────────────

def inspect_glyph(
    element_id: str,
    crop_img: Image.Image,
    role: str = "text",
    dpr: float = 2.0,
    has_replacement: bool = False,
    expected_script: str = "unknown",
    cfg: A8Config | None = None,
) -> list[GlyphIssue]:
    """
    Phân tích 1 crop ảnh (element/text segment) → list GlyphIssue.
    """
    if cfg is None:
        cfg = A8Config()

    issues: list[GlyphIssue] = []

    crop_np = np.array(crop_img.convert("RGB"))
    h, w = crop_np.shape[:2]

    if h < cfg.min_height_px or w < 2:
        return []  # quá nhỏ → skip, không crash

    # Tiền xử lý: Gaussian nhẹ để triệt JPEG artifact (σ=0.5)
    crop_gray = cv2.cvtColor(crop_np, cv2.COLOR_RGB2GRAY)
    crop_gray_smooth = cv2.GaussianBlur(crop_gray, (0, 0), sigmaX=0.5)

    # 1. Tofu box (chỉ check với role=text hoặc khi has_replacement)
    if role == "text" or has_replacement:
        components = _detect_tofu_components(crop_gray_smooth, cfg)
        for comp in components:
            if comp["uniformity"] >= cfg.tofu_uniformity_threshold and comp["edge_internal"] < 3:
                conf = round(comp["uniformity"] * 0.95, 2)
                verdict = "confirmed" if conf >= 0.90 else "likely"
                issues.append(GlyphIssue(
                    element_id=element_id,
                    issue_type="tofu_box",
                    confidence=conf,
                    verdict=verdict,
                    rule_id="A8-tofu",
                    evidence={
                        "box_uniformity": comp["uniformity"],
                        "edge_internal": comp["edge_internal"],
                        "component_area": comp["area"],
                        "bbox": {"x": comp["x"], "y": comp["y"],
                                 "w": comp["w"], "h": comp["h"]},
                    },
                ))

    # 2. Outline box (.notdef)
    if role == "text" and _is_outline_box(crop_gray_smooth, cfg):
        issues.append(GlyphIssue(
            element_id=element_id,
            issue_type="outline_box",
            confidence=0.75,
            verdict="likely",
            rule_id="A8-outline",
            evidence={"method": "erode_dilate"},
        ))

    # 3. Blur / jagged
    lap_var = _laplacian_variance(crop_gray_smooth)
    blur_thresh = _blur_threshold(dpr, cfg)
    if lap_var < blur_thresh:
        conf = round(1.0 - (lap_var / blur_thresh), 2) if blur_thresh > 0 else 0.5
        verdict = "confirmed" if conf >= 0.7 else "likely"
        issues.append(GlyphIssue(
            element_id=element_id,
            issue_type="blur_jagged",
            confidence=conf,
            verdict=verdict,
            rule_id="A8-blur",
            evidence={
                "laplacian_var": round(lap_var, 2),
                "threshold": blur_thresh,
                "dpr": dpr,
            },
        ))

    # 4. Emoji-box: vùng nhỏ đơn sắc khi has_replacement=true
    if has_replacement and h <= int(20 * dpr) and w <= int(20 * dpr):
        std = float(crop_gray_smooth.std())
        n_colors = len(np.unique(crop_np.reshape(-1, 3), axis=0))
        if std < 20 and n_colors <= 5:
            issues.append(GlyphIssue(
                element_id=element_id,
                issue_type="emoji_square",
                confidence=0.80,
                verdict="confirmed",
                rule_id="A8-emoji",
                evidence={"color_variance": round(std, 2), "color_count": n_colors},
            ))

    # 5. Banding
    is_banding, band_conf = _detect_banding(crop_gray, cfg)
    if is_banding:
        issues.append(GlyphIssue(
            element_id=element_id,
            issue_type="banding",
            confidence=band_conf,
            verdict="likely" if band_conf >= 0.5 else "uncertain",
            rule_id="A8-banding",
            evidence={"banding_conf": band_conf},
        ))

    return issues


def inspect_batch(
    crops: list[tuple[str, Image.Image, str, float, bool, str]],
    cfg: A8Config | None = None,
) -> list[GlyphIssue]:
    """
    Chạy A8 trên nhiều crop.
    crops: list[(element_id, crop_img, role, dpr, has_replacement, expected_script)]
    """
    all_issues: list[GlyphIssue] = []
    for eid, crop_img, role, dpr, has_repl, script in crops:
        issues = inspect_glyph(eid, crop_img, role, dpr, has_repl, script, cfg)
        all_issues.extend(issues)
    return all_issues


def glyph_issues_to_candidates(
    issues: list[GlyphIssue],
) -> list[CandidateIssue]:
    severity_map = {
        "tofu_box": ("high", SeverityRange(min="medium", max="critical")),
        "outline_box": ("medium", SeverityRange(min="low", max="high")),
        "blur_jagged": ("medium", SeverityRange(min="low", max="high")),
        "emoji_square": ("high", SeverityRange(min="medium", max="critical")),
        "banding": ("low", SeverityRange(min="trivial", max="medium")),
        "overlap_glyph": ("medium", SeverityRange(min="low", max="high")),
    }
    candidates = []
    for issue in issues:
        if issue.verdict not in ("confirmed", "likely"):
            continue
        sev, sev_range = severity_map.get(issue.issue_type, ("medium", SeverityRange(min="low", max="high")))
        candidates.append(CandidateIssue(
            rule=issue.rule_id,
            element=issue.element_id,
            severity=sev,
            severity_range=sev_range,
            confidence=issue.confidence,
            detail=f"{issue.issue_type}: {issue.evidence}",
        ))
    return candidates
