"""
A4 — Pixel Color Sampler
Đo contrast/màu/opacity từ pixel thực cho từng element.
Spec: docs/analyzers/A4-pixel-color-sampler.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import (
    BBox, CandidateIssue, Element, Evidence, SeverityRange, SeverityType,
)
from ..schema.thresholds import (
    CONTRAST_TEXT_NORMAL, CONTRAST_TEXT_LARGE, CONTRAST_UI, CONTRAST_INVISIBLE,
)
from ..utils.color import contrast_ratio, dominant_colors_kmeans, rgb_to_lab
from ..utils.geometry import normalize_bbox


# ── Kiểu dữ liệu kết quả ─────────────────────────────────────────────────────

@dataclass
class PixelColorResult:
    element_id: str
    color_px: Optional[tuple[int, int, int]] = None     # foreground RGB
    bg_color_px: Optional[tuple[int, int, int]] = None  # background RGB
    contrast_ratio_px: Optional[float] = None
    bg_is_solid_px: bool = True
    dominant_colors: list[tuple[tuple[int, int, int], float]] = field(default_factory=list)
    opacity_px: float = 1.0
    dark_mode_ok: Optional[bool] = None
    disabled_color_similar: Optional[bool] = None
    crop_confidence: float = 1.0    # confidence từ A3 bbox


# ── Thresholds cụ thể A4 ─────────────────────────────────────────────────────

BG_SOLID_STD_THRESHOLD = 20.0   # std(L) > 20 → gradient/image  (TUNE)
ANTIALIASING_BLEND_PCT = 0.2    # loại pixel "pha" 20–80% giữa 2 cluster
MIN_CROP_SIZE_PX = 4
DARK_MODE_BG_THRESHOLD = 80     # L < 80/255 → dark bg  (TUNE)


# ── Helpers ──────────────────────────────────────────────────────────────────

_A4_MAX_CROP_DIM = 80  # max chiều crop trước K-means (giữ latency thấp)


def _crop_from_array(arr_rgb: np.ndarray, bbox: BBox, img_w: int, img_h: int) -> Optional[np.ndarray]:
    """Crop element bbox từ numpy array đã có sẵn (không convert lại). None nếu quá nhỏ.
    Resize về tối đa _A4_MAX_CROP_DIM×_A4_MAX_CROP_DIM để K-means nhanh.
    """
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(img_w, int(bbox.x + bbox.w))
    y2 = min(img_h, int(bbox.y + bbox.h))
    if (x2 - x1) < MIN_CROP_SIZE_PX or (y2 - y1) < MIN_CROP_SIZE_PX:
        return None
    crop = arr_rgb[y1:y2, x1:x2]
    h, w = crop.shape[:2]
    if h > _A4_MAX_CROP_DIM or w > _A4_MAX_CROP_DIM:
        scale = _A4_MAX_CROP_DIM / max(h, w)
        new_h = max(MIN_CROP_SIZE_PX, int(h * scale))
        new_w = max(MIN_CROP_SIZE_PX, int(w * scale))
        crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return crop


def _crop_element(img: Image.Image, bbox: BBox) -> Optional[np.ndarray]:
    """Legacy: convert image → array rồi crop (dùng nếu gọi độc lập ngoài sample_colors)."""
    arr = np.array(img.convert("RGB"))
    return _crop_from_array(arr, bbox, img.width, img.height)


def _bg_is_solid(crop_rgb: np.ndarray, bg_pixels: np.ndarray) -> bool:
    """True nếu background đặc (không phải gradient/ảnh)."""
    if len(bg_pixels) == 0:
        return True
    # Chuyển sang Lab, đo std của L
    lab = rgb_to_lab(bg_pixels)
    return float(lab[:, 0].std()) <= BG_SOLID_STD_THRESHOLD


def _estimate_opacity(img: Image.Image, bbox: BBox) -> float:
    """Ước lượng opacity từ alpha channel (nếu RGBA). Else trả 1.0."""
    if img.mode != "RGBA":
        return 1.0
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(img.width, int(bbox.x + bbox.w))
    y2 = min(img.height, int(bbox.y + bbox.h))
    arr = np.array(img)
    alpha = arr[y1:y2, x1:x2, 3]
    if alpha.size == 0:
        return 1.0
    return float(alpha.mean() / 255.0)


def _separate_fg_bg_text(crop_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Tách fg/bg cho element chứa text bằng K-means k=2 trong Lab.
    Cluster nhỏ hơn = foreground (chữ thường ít pixel hơn nền).
    Bỏ pixel "pha" (antialiasing) trước khi tính màu trội.
    """
    pixels = crop_rgb.reshape(-1, 3)
    if len(pixels) < 4:
        return pixels, pixels

    colors, weights, labels = dominant_colors_kmeans(pixels, k=2)
    if len(colors) < 2:
        return pixels, pixels

    # Xác định fg = cluster có ít pixel hơn
    fg_idx = 0 if weights[0] <= weights[1] else 1
    bg_idx = 1 - fg_idx
    fg_pixels = pixels[labels == fg_idx]
    bg_pixels = pixels[labels == bg_idx]

    # Loại pixel antialiasing: trong khoảng 20–80% giữa 2 cluster trong Lab
    fg_lab = rgb_to_lab(np.array([colors[fg_idx]], dtype=np.uint8))[0]
    bg_lab = rgb_to_lab(np.array([colors[bg_idx]], dtype=np.uint8))[0]
    all_lab = rgb_to_lab(pixels)

    # Tính t (projection onto fg-bg axis)
    axis = fg_lab - bg_lab
    axis_norm = np.linalg.norm(axis)
    if axis_norm > 0:
        t = (all_lab - bg_lab) @ axis / (axis_norm ** 2)
        blended_mask = (t > ANTIALIASING_BLEND_PCT) & (t < 1 - ANTIALIASING_BLEND_PCT)
        fg_pixels = pixels[(labels == fg_idx) & ~blended_mask]
        bg_pixels = pixels[(labels == bg_idx) & ~blended_mask]

    if len(fg_pixels) == 0:
        fg_pixels = pixels[labels == fg_idx]
    if len(bg_pixels) == 0:
        bg_pixels = pixels[labels == bg_idx]
    return fg_pixels, bg_pixels


def _severity_for_contrast(
    cr: float, is_text: bool, is_large_text: bool
) -> tuple[SeverityType, SeverityRange]:
    threshold = CONTRAST_TEXT_LARGE if is_large_text else (
        CONTRAST_TEXT_NORMAL if is_text else CONTRAST_UI
    )
    if cr <= CONTRAST_INVISIBLE:
        return "critical", SeverityRange(min="high", max="critical")
    if cr < threshold * 0.5:
        return "high", SeverityRange(min="medium", max="critical")
    if cr < threshold:
        return "medium", SeverityRange(min="low", max="high")
    return "low", SeverityRange(min="trivial", max="medium")  # unreachable nhưng fallback


# ── Public API ────────────────────────────────────────────────────────────────

import os as _os
_A4_MAX_ELEMENTS = int(_os.environ.get("A4_MAX_ELEMENTS", "20"))  # set 0 để skip A4
_A4_MIN_AREA_PX2 = 100    # bỏ element quá nhỏ (<10×10 px)
_A4_MAX_AREA_PX2 = 150_000  # bỏ background full-screen (không cần contrast)


def sample_colors(
    img: Image.Image,
    elements: list[Element],
    theme: str = "light",
    img_w: Optional[int] = None,
    img_h: Optional[int] = None,
) -> tuple[list[PixelColorResult], list[CandidateIssue]]:
    """
    Đo màu/contrast cho mọi element có role text/button/icon/toggle.
    Giới hạn MAX_ELEMENTS để giữ latency thấp — ưu tiên element lớn nhất
    (most visible) và bỏ background full-screen.
    Trả về: (results[], candidate_issues[]).
    """
    _img_w = img_w or img.width
    _img_h = img_h or img.height
    results: list[PixelColorResult] = []
    issues: list[CandidateIssue] = []

    _TARGET_ROLES = ("text", "button", "icon", "input", "toggle", "nav", "tab")

    # Convert ảnh 1 lần duy nhất (tránh bottleneck convert × N element)
    arr_rgb = np.array(img.convert("RGB"))
    img_w_px, img_h_px = img.width, img.height

    # Lọc và sắp xếp: chỉ lấy element đủ lớn, ưu tiên element diện tích lớn nhất
    eligible = [
        e for e in elements
        if e.visible
        and e.role in _TARGET_ROLES
        and _A4_MIN_AREA_PX2 <= (e.bbox.w * e.bbox.h) <= _A4_MAX_AREA_PX2
    ]
    eligible.sort(key=lambda e: e.bbox.w * e.bbox.h, reverse=True)
    eligible = eligible[:_A4_MAX_ELEMENTS]

    for elem in eligible:
        crop_rgb = _crop_from_array(arr_rgb, elem.bbox, img_w_px, img_h_px)
        res = PixelColorResult(
            element_id=elem.id,
            crop_confidence=elem.confidence,
            opacity_px=_estimate_opacity(img, elem.bbox),
        )

        if crop_rgb is None:
            # Quá nhỏ
            results.append(res)
            continue

        # Tách fg/bg
        is_text_role = elem.role in ("text", "button", "input")
        if is_text_role:
            fg_pixels, bg_pixels = _separate_fg_bg_text(crop_rgb)
        else:
            # icon/toggle: lấy dominant colors tổng thể
            pixels = crop_rgb.reshape(-1, 3)
            colors, weights, _ = dominant_colors_kmeans(pixels, k=3)
            res.dominant_colors = list(zip(colors, weights))
            # Contrast: giữa sáng nhất và tối nhất trong dominant
            if len(colors) >= 2:
                lums = [sum([0.2126*(c[0]/255)**2.2, 0.7152*(c[1]/255)**2.2, 0.0722*(c[2]/255)**2.2]) for c in colors]
                lightest = colors[lums.index(max(lums))]
                darkest = colors[lums.index(min(lums))]
                res.color_px = darkest
                res.bg_color_px = lightest
                cr = contrast_ratio(darkest, lightest)
                res.contrast_ratio_px = round(cr, 2)
            results.append(res)
            continue

        if len(fg_pixels) > 0:
            res.color_px = tuple(int(v) for v in fg_pixels.mean(axis=0))  # type: ignore[assignment]
        if len(bg_pixels) > 0:
            res.bg_color_px = tuple(int(v) for v in bg_pixels.mean(axis=0))  # type: ignore[assignment]
            res.bg_is_solid_px = _bg_is_solid(crop_rgb, bg_pixels)

        # Dominant colors
        pixels_all = crop_rgb.reshape(-1, 3)
        dom_colors, dom_weights, _ = dominant_colors_kmeans(pixels_all, k=3)
        res.dominant_colors = list(zip(dom_colors, dom_weights))

        # Contrast WCAG
        if res.color_px and res.bg_color_px and elem.confidence >= 0.4:
            cr = contrast_ratio(res.color_px, res.bg_color_px)
            res.contrast_ratio_px = round(cr, 2)

            # Dark mode check
            if theme == "dark":
                bg_l = res.bg_color_px[0] * 0.299 + res.bg_color_px[1] * 0.587 + res.bg_color_px[2] * 0.114
                res.dark_mode_ok = bg_l < DARK_MODE_BG_THRESHOLD

            # Phát sinh candidate issue nếu fail contrast
            is_large = elem.style and elem.style.font_size and elem.style.font_size >= 18
            threshold = CONTRAST_TEXT_LARGE if is_large else CONTRAST_TEXT_NORMAL
            if cr < threshold:
                sev, sev_range = _severity_for_contrast(cr, True, bool(is_large))
                issues.append(CandidateIssue(
                    rule="STY-01_contrast",
                    element=elem.id,
                    severity=sev,
                    severity_range=sev_range,
                    confidence=elem.confidence * 0.9,
                    detail=f"contrast_ratio={cr:.2f} < {threshold} (fg={res.color_px} bg={res.bg_color_px})",
                    evidence=Evidence(bbox=elem.bbox),
                ))

        results.append(res)

    return results, issues


def enrich_elements(
    elements: list[Element],
    color_results: list[PixelColorResult],
) -> list[Element]:
    """
    Ghi kết quả A4 vào elements[].style.* để downstream dùng.
    """
    result_map = {r.element_id: r for r in color_results}
    from ..schema.models import Style, StyleSources
    for elem in elements:
        r = result_map.get(elem.id)
        if r is None:
            continue
        color_str = "#{:02x}{:02x}{:02x}".format(*r.color_px) if r.color_px else None
        bg_str = "#{:02x}{:02x}{:02x}".format(*r.bg_color_px) if r.bg_color_px else None
        if elem.style is None:
            elem.style = Style(
                color=color_str,
                bg_color=bg_str,
                contrast_ratio=r.contrast_ratio_px,
                opacity=r.opacity_px,
                dark_mode_ok=r.dark_mode_ok,
                sources=StyleSources(
                    color="pixel" if color_str else None,
                    bg_color="pixel" if bg_str else None,
                    contrast_ratio="pixel" if r.contrast_ratio_px is not None else None,
                    opacity="pixel",
                ),
            )
        else:
            if color_str and elem.style.color is None:
                elem.style.color = color_str
            if bg_str and elem.style.bg_color is None:
                elem.style.bg_color = bg_str
            if r.contrast_ratio_px is not None and elem.style.contrast_ratio is None:
                elem.style.contrast_ratio = r.contrast_ratio_px
            if r.dark_mode_ok is not None and elem.style.dark_mode_ok is None:
                elem.style.dark_mode_ok = r.dark_mode_ok
    return elements
