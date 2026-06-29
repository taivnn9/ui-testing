"""
A9 — Pixel Pattern Detector
Phát hiện skeleton / spinner / overlay / keyboard / splash / broken-image / blank.
Chỉ từ 1 frame ảnh — "kẹt" cần ≥2 frame → đánh dấu temporal=True.
Spec: docs/analyzers/A9-pixel-pattern-detector.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import BBox, CandidateIssue, SeverityRange, Viewport


# ── Cấu hình ─────────────────────────────────────────────────────────────────

@dataclass
class A9Config:
    # Skeleton
    skeleton_min_blocks: int = 3
    skeleton_color_std_max: float = 15.0    # màu skeleton đồng đều
    skeleton_min_fill: float = 0.03         # block chiếm ≥ 3% diện tích màn
    # Spinner
    spinner_hough_min_radius_ratio: float = 0.03  # tỉ lệ với min(W,H)
    spinner_hough_max_radius_ratio: float = 0.15
    # Overlay
    overlay_min_coverage: float = 0.6
    overlay_max_luminance: float = 0.6      # mean lum < 0.6 + coverage → overlay
    overlay_variance_max: float = 0.04
    # Keyboard
    keyboard_min_coverage_h: float = 0.25  # chiếm ≥ 25% chiều cao màn
    keyboard_grid_rows_min: int = 3
    # Blank
    blank_entropy_max: float = 1.0          # bits
    blank_min_coverage: float = 0.4
    # Broken image
    broken_min_area_ratio: float = 0.005


# ── Kiểu output ───────────────────────────────────────────────────────────────

@dataclass
class PatternDetection:
    pattern_type: str  # skeleton|spinner|overlay|keyboard|splash|broken_image|blank
    bbox: Optional[BBox]
    confidence: float
    temporal: bool = False
    evidence: dict = field(default_factory=dict)
    severity: str = "medium"
    rule_id: str = "A9"
    note: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _image_entropy(img_gray: np.ndarray) -> float:
    """Entropy của histogram grayscale (bits)."""
    hist, _ = np.histogram(img_gray.flatten(), bins=256, range=(0, 256))
    hist = hist[hist > 0].astype(float)
    p = hist / hist.sum()
    return float(-np.sum(p * np.log2(p)))


def _mean_luminance_norm(img_gray: np.ndarray) -> float:
    """Mean luminance normalize về [0,1]."""
    return float(img_gray.mean()) / 255.0


def _variance_norm(img_gray: np.ndarray) -> float:
    return float(img_gray.var()) / (255 ** 2)


# ── Sub-detectors ─────────────────────────────────────────────────────────────

def _detect_skeleton(
    img_rgb: np.ndarray,
    img_gray: np.ndarray,
    cfg: A9Config,
) -> Optional[PatternDetection]:
    """
    Skeleton loader: nhiều khối chữ nhật bo góc xám đồng đều, lặp lại theo grid.
    """
    # Tìm rect có màu xám đồng nhất (đặc trưng skeleton)
    _, thresh = cv2.threshold(img_gray, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = img_gray.shape[:2]
    img_area = h * w
    skeleton_candidates = []

    for c in contours:
        area = cv2.contourArea(c)
        if area < img_area * cfg.skeleton_min_fill:
            continue
        cx, cy, cw, ch = cv2.boundingRect(c)
        crop = img_rgb[cy:cy+ch, cx:cx+cw]
        if crop.size == 0:
            continue
        # Kiểm tra màu đồng đều (skeleton thường xám nhạt)
        std = float(crop.std())
        mean_gray = float(cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY).mean())
        if std <= cfg.skeleton_color_std_max and 150 <= mean_gray <= 230:
            skeleton_candidates.append((cx, cy, cw, ch, std))

    if len(skeleton_candidates) >= cfg.skeleton_min_blocks:
        xs = [c[0] for c in skeleton_candidates]
        ys = [c[1] for c in skeleton_candidates]
        x2s = [c[0] + c[2] for c in skeleton_candidates]
        y2s = [c[1] + c[3] for c in skeleton_candidates]
        bbox = BBox(x=float(min(xs)), y=float(min(ys)),
                    w=float(max(x2s) - min(xs)), h=float(max(y2s) - min(ys)))
        conf = min(0.9, 0.5 + len(skeleton_candidates) * 0.08)
        return PatternDetection(
            pattern_type="skeleton",
            bbox=bbox,
            confidence=round(conf, 2),
            temporal=True,  # "kẹt" cần ≥2 frame
            evidence={"block_count": len(skeleton_candidates)},
            severity="high",
            rule_id="A9-skeleton",
            note="skeleton detected — 'stuck' requires >=2 frames to confirm",
        )
    return None


def _detect_spinner(
    img_gray: np.ndarray,
    viewport: Viewport,
    cfg: A9Config,
) -> Optional[PatternDetection]:
    """Phát hiện spinner/loading circle bằng HoughCircles."""
    min_dim = min(img_gray.shape[0], img_gray.shape[1])
    min_r = int(min_dim * cfg.spinner_hough_min_radius_ratio)
    max_r = int(min_dim * cfg.spinner_hough_max_radius_ratio)
    if min_r < 3 or max_r < min_r:
        return None

    blurred = cv2.GaussianBlur(img_gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2,
        minDist=min_r * 2,
        param1=50, param2=30,
        minRadius=min_r, maxRadius=max_r,
    )
    if circles is None:
        return None

    circles = np.round(circles[0, :]).astype(int)
    best = circles[0]
    cx, cy, r = int(best[0]), int(best[1]), int(best[2])
    bbox = BBox(x=float(cx - r), y=float(cy - r), w=float(2 * r), h=float(2 * r))
    return PatternDetection(
        pattern_type="spinner",
        bbox=bbox,
        confidence=0.65,
        temporal=True,
        evidence={"center": (cx, cy), "radius": r, "aspect_ratio": 1.0},
        severity="high",
        rule_id="A9-spinner",
        note="spinner detected — 'stuck' requires >=2 frames to confirm",
    )


def _detect_overlay(
    img_gray: np.ndarray,
    img_rgb: np.ndarray,
    cfg: A9Config,
) -> Optional[PatternDetection]:
    """
    Loading overlay: lớp bán trong suốt lớp phủ phần lớn màn.
    Đặc trưng: variance thấp + luminance trung bình thấp hoặc cao đồng nhất.
    """
    h, w = img_gray.shape[:2]
    lum = _mean_luminance_norm(img_gray)
    var = _variance_norm(img_gray)

    # Overlay tối: lum thấp + variance thấp trên vùng lớn
    if lum < cfg.overlay_max_luminance and var < cfg.overlay_variance_max:
        conf = round(1.0 - lum - var, 2)
        conf = max(0.3, min(0.85, conf))
        return PatternDetection(
            pattern_type="overlay",
            bbox=None,
            confidence=conf,
            temporal=True,
            evidence={"mean_luminance": round(lum, 3), "variance": round(var, 4),
                      "coverage_ratio": 1.0},
            severity="high",
            rule_id="A9-overlay",
        )
    return None


def _detect_keyboard(
    img_gray: np.ndarray,
    img_rgb: np.ndarray,
    cfg: A9Config,
) -> Optional[PatternDetection]:
    """
    Bàn phím ảo: lưới nút đồng đều chiếm phần lớn nửa dưới màn.
    """
    h, w = img_gray.shape[:2]
    # Chỉ xét nửa dưới
    lower_half = img_gray[h // 2:, :]
    # Tìm lưới horizontal lines
    edges = cv2.Canny(lower_half, 30, 100)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                             minLineLength=w // 4, maxLineGap=20)
    if lines is None:
        return None

    h_lines = [l for l in lines[:, 0] if abs(l[3] - l[1]) < 5]  # gần ngang
    if len(h_lines) < cfg.keyboard_grid_rows_min:
        return None

    # Tính coverage
    y_coords = sorted(set(l[1] for l in h_lines))
    span = y_coords[-1] - y_coords[0] if len(y_coords) > 1 else 0
    coverage = span / h if h > 0 else 0
    if coverage < cfg.keyboard_min_coverage_h:
        return None

    bbox = BBox(x=0.0, y=float(h // 2), w=float(w), h=float(h // 2))
    conf = min(0.85, 0.5 + len(h_lines) * 0.05)
    return PatternDetection(
        pattern_type="keyboard",
        bbox=bbox,
        confidence=round(conf, 2),
        evidence={"hline_count": len(h_lines), "coverage_ratio": round(coverage, 2)},
        severity="medium",
        rule_id="A9-keyboard",
    )


def _detect_blank(
    img_gray: np.ndarray,
    cfg: A9Config,
) -> Optional[PatternDetection]:
    """Màn trống: entropy thấp trên vùng lớn."""
    entropy = _image_entropy(img_gray)
    if entropy <= cfg.blank_entropy_max:
        h, w = img_gray.shape[:2]
        conf = max(0.5, 1.0 - entropy / cfg.blank_entropy_max)
        return PatternDetection(
            pattern_type="blank",
            bbox=None,
            confidence=round(conf, 2),
            evidence={"entropy": round(entropy, 3), "mean_luminance": round(_mean_luminance_norm(img_gray), 3)},
            severity="medium",
            rule_id="A9-blank",
        )
    return None


def _detect_broken_image(
    img_rgb: np.ndarray,
    img_gray: np.ndarray,
    cfg: A9Config,
) -> list[PatternDetection]:
    """
    Ảnh vỡ: vùng có icon broken-image placeholder đặc trưng.
    Dấu hiệu: vùng xám nhạt có outline + ký hiệu đơn giản bên trong.
    """
    h, w = img_gray.shape[:2]
    img_area = h * w
    _, thresh = cv2.threshold(img_gray, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for c in contours:
        area = cv2.contourArea(c)
        if area / img_area < cfg.broken_min_area_ratio:
            continue
        cx, cy, cw, ch = cv2.boundingRect(c)
        aspect = max(cw, ch) / max(min(cw, ch), 1)
        if aspect > 3:
            continue
        # Kiểm tra bên trong có ít nội dung (vùng gần trống)
        crop = img_gray[cy:cy+ch, cx:cx+cw]
        if crop.size == 0:
            continue
        inner_entropy = _image_entropy(crop)
        if inner_entropy < 3.0:
            bbox = BBox(x=float(cx), y=float(cy), w=float(cw), h=float(ch))
            detections.append(PatternDetection(
                pattern_type="broken_image",
                bbox=bbox,
                confidence=0.55,
                evidence={"inner_entropy": round(inner_entropy, 2), "area_ratio": round(area/img_area, 3)},
                severity="high",
                rule_id="A9-broken",
            ))
    return detections


# ── Public API ────────────────────────────────────────────────────────────────

def detect_patterns(
    img: Image.Image,
    viewport: Viewport,
    cfg: A9Config | None = None,
) -> list[PatternDetection]:
    """
    Phát hiện tất cả pattern đặc biệt trong ảnh.
    """
    if cfg is None:
        cfg = A9Config()

    arr_rgb = np.array(img.convert("RGB"))
    arr_gray = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY)
    detections: list[PatternDetection] = []

    # Blank screen — check trước để short-circuit
    blank = _detect_blank(arr_gray, cfg)
    if blank:
        detections.append(blank)
        return detections  # Nếu blank thì skip các check khác

    for detect_fn in [
        lambda: _detect_overlay(arr_gray, arr_rgb, cfg),
        lambda: _detect_skeleton(arr_rgb, arr_gray, cfg),
        lambda: _detect_spinner(arr_gray, viewport, cfg),
        lambda: _detect_keyboard(arr_gray, arr_rgb, cfg),
    ]:
        result = detect_fn()
        if result:
            detections.append(result)

    # Broken image (có thể nhiều vùng)
    broken = _detect_broken_image(arr_rgb, arr_gray, cfg)
    detections.extend(broken)

    return detections


def patterns_to_candidates(detections: list[PatternDetection]) -> list[CandidateIssue]:
    """Chuyển PatternDetection thành CandidateIssue cho Rule Engine."""
    severity_map = {
        "skeleton": ("high", SeverityRange(min="medium", max="critical")),
        "spinner": ("high", SeverityRange(min="medium", max="critical")),
        "overlay": ("high", SeverityRange(min="medium", max="critical")),
        "keyboard": ("medium", SeverityRange(min="low", max="high")),
        "broken_image": ("high", SeverityRange(min="medium", max="critical")),
        "blank": ("medium", SeverityRange(min="low", max="high")),
        "splash": ("high", SeverityRange(min="medium", max="critical")),
    }
    result = []
    for d in detections:
        sev, sev_range = severity_map.get(d.pattern_type, ("medium", SeverityRange(min="low", max="high")))
        # Pattern "kẹt" (spinner/skeleton/overlay) cần ≥2 frame mới xác nhận được; từ 1
        # ảnh tĩnh KHÔNG thể chắc → hạ severity xuống low (giữ confidence ≥0.4 để agent
        # còn xác nhận). Tránh báo HIGH nhầm cho avatar/nút tròn = spinner. (FP audit.)
        if d.temporal:
            sev = "low"
            sev_range = SeverityRange(min="trivial", max="medium")
        result.append(CandidateIssue(
            rule=d.rule_id,
            element=None,
            severity=sev,
            severity_range=sev_range,
            confidence=d.confidence,
            detail=f"{d.pattern_type}: {d.note or ''} evidence={d.evidence}",
        ))
    return result
