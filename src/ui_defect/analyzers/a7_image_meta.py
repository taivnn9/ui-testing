"""
A7 — Image Region Meta Reader
Đo kích thước displayed, blur score, broken/partial-load cho vùng ảnh-photo.
Spec: docs/analyzers/A7-image-region-meta-reader.md
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import BBox, CandidateIssue, Element, Evidence, ImageMeta, SeverityRange
from ..schema.thresholds import BLUR_CLEAR, BLUR_WARN
from ..utils.geometry import normalize_bbox


# ── Cấu hình ─────────────────────────────────────────────────────────────────

@dataclass
class A7Config:
    min_crop_side: int = 32          # skip blur check nếu crop nhỏ hơn (px)
    photo_color_count: int = 12      # color_count > 12 AND variance > 500 → photo
    photo_variance: float = 500.0
    resize_for_color: int = 32
    broken_entropy_max: float = 0.8  # entropy thấp → ảnh trắng/đơn sắc → có thể broken
    partial_gradient_rows: int = 10  # số row đồng nhất liên tiếp ở đáy → partial load
    partial_uniform_std: float = 8.0 # std row nhỏ hơn → uniform (chưa load)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crop_to_numpy(img: Image.Image, bbox: BBox) -> Optional[tuple[np.ndarray, np.ndarray]]:
    """Crop bbox → (rgb_array, gray_array). None nếu crop không hợp lệ."""
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(img.width, int(bbox.x + bbox.w))
    y2 = min(img.height, int(bbox.y + bbox.h))
    if x2 <= x1 or y2 <= y1:
        return None
    arr_rgb = np.array(img.convert("RGB"))[y1:y2, x1:x2]
    arr_gray = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY)
    return arr_rgb, arr_gray


def _color_count(crop_rgb: np.ndarray, resize_to: int = 32) -> int:
    if crop_rgb.size == 0:
        return 0
    small = cv2.resize(crop_rgb, (resize_to, resize_to), interpolation=cv2.INTER_AREA)
    quantized = (small // 32) * 32
    return int(len(np.unique(quantized.reshape(-1, 3), axis=0)))


def _is_photo(crop_rgb: np.ndarray, crop_gray: np.ndarray, cfg: A7Config) -> bool:
    n_colors = _color_count(crop_rgb, cfg.resize_for_color)
    variance = float(crop_gray.var())
    return n_colors > cfg.photo_color_count and variance > cfg.photo_variance


def _blur_score(crop_gray: np.ndarray) -> float:
    return float(cv2.Laplacian(crop_gray.astype(np.float64), cv2.CV_64F).var())


def _histogram_entropy(crop_gray: np.ndarray) -> float:
    hist = cv2.calcHist([crop_gray], [0], None, [256], [0, 256]).flatten()
    total = hist.sum()
    if total == 0:
        return 0.0
    prob = hist[hist > 0] / total
    return float(-np.sum(prob * np.log2(prob)))


def _is_broken(crop_rgb: np.ndarray, crop_gray: np.ndarray, cfg: A7Config) -> bool:
    """
    Heuristic phát hiện broken image:
    - Entropy rất thấp (ảnh đơn sắc / trắng trơn).
    - Hoặc: có đường viền rõ + interior đồng nhất (placeholder frame).
    """
    entropy = _histogram_entropy(crop_gray)
    if entropy < cfg.broken_entropy_max:
        return True

    h, w = crop_gray.shape[:2]
    if h < 10 or w < 10:
        return False

    edges = cv2.Canny(crop_gray, 30, 100)
    border_mask = np.zeros_like(edges)
    thickness = max(2, min(h, w) // 10)
    border_mask[:thickness, :] = 1
    border_mask[-thickness:, :] = 1
    border_mask[:, :thickness] = 1
    border_mask[:, -thickness:] = 1

    interior_mask = np.ones_like(edges, dtype=bool)
    interior_mask[:thickness, :] = False
    interior_mask[-thickness:, :] = False
    interior_mask[:, :thickness] = False
    interior_mask[:, -thickness:] = False

    border_edge_density = float(edges[border_mask == 1].sum() / 255) / max(1, border_mask.sum())
    interior_std = float(crop_gray[interior_mask].std()) if interior_mask.any() else 0.0

    return border_edge_density > 0.3 and interior_std < 15.0


def _is_partial_load(crop_gray: np.ndarray, cfg: A7Config) -> bool:
    """
    Phát hiện ảnh load dở: nhiều row liên tiếp ở phần dưới crop có std thấp (đồng màu).
    """
    h = crop_gray.shape[0]
    if h < cfg.partial_gradient_rows * 2:
        return False

    bottom = crop_gray[-cfg.partial_gradient_rows:, :]
    row_stds = bottom.std(axis=1)
    uniform_rows = int((row_stds < cfg.partial_uniform_std).sum())
    return uniform_rows >= cfg.partial_gradient_rows // 2


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_images(
    img: Image.Image,
    elements: list[Element],
    dpr: float = 2.0,
    cfg: A7Config | None = None,
) -> tuple[list[Element], list[CandidateIssue]]:
    """
    Enrich elements có role="image" với image_meta (displayed_w/h, blur_score,
    is_broken, is_partial_load, intrinsic_unavailable=True, scale_mode="unknown").
    Trả (elements_updated, candidate_issues).
    """
    if cfg is None:
        cfg = A7Config()

    issues: list[CandidateIssue] = []

    for elem in elements:
        if elem.role != "image":
            continue

        displayed_w = int(elem.bbox.w)
        displayed_h = int(elem.bbox.h)

        crops = _crop_to_numpy(img, elem.bbox)

        blur = None
        broken = False
        partial = False

        if crops is not None:
            crop_rgb, crop_gray = crops
            ch, cw = crop_gray.shape[:2]

            if cw >= cfg.min_crop_side and ch >= cfg.min_crop_side:
                blur = round(_blur_score(crop_gray), 2)
                broken = _is_broken(crop_rgb, crop_gray, cfg)
                partial = _is_partial_load(crop_gray, cfg)

        elem.image_meta = ImageMeta(
            intrinsic_w=None,
            intrinsic_h=None,
            displayed_w=displayed_w,
            displayed_h=displayed_h,
            scale_mode=None,
            blur_score=blur,
            is_broken=broken,
            is_partial_load=partial,
            intrinsic_unavailable=True,
        )

        elem.source = "vision"
        if elem.confidence >= 1.0:
            elem.confidence = 0.6

        if blur is not None and blur < BLUR_WARN:
            confidence = round(1.0 - blur / BLUR_WARN, 2) if BLUR_WARN > 0 else 0.5
            confidence = min(0.9, max(0.3, confidence))
            severity: str
            sev_range: SeverityRange
            if blur < BLUR_WARN * 0.4:
                severity = "high"
                sev_range = SeverityRange(min="medium", max="high")
            else:
                severity = "medium"
                sev_range = SeverityRange(min="low", max="high")
            issues.append(CandidateIssue(
                rule="IMG-03_blur",
                element=elem.id,
                severity=severity,  # type: ignore[arg-type]
                severity_range=sev_range,
                confidence=confidence,
                detail=f"blur_score={blur:.2f} < BLUR_WARN={BLUR_WARN} (displayed={displayed_w}×{displayed_h})",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            ))

        if broken:
            issues.append(CandidateIssue(
                rule="IMG-01_broken",
                element=elem.id,
                severity="high",  # type: ignore[arg-type]
                severity_range=SeverityRange(min="medium", max="critical"),
                confidence=0.65,
                detail=f"Broken or placeholder image detected (displayed={displayed_w}×{displayed_h})",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            ))

        if partial:
            issues.append(CandidateIssue(
                rule="IMG-14_partial_load",
                element=elem.id,
                severity="medium",  # type: ignore[arg-type]
                severity_range=SeverityRange(min="low", max="high"),
                confidence=0.6,
                detail=f"Partial image load detected (bottom rows uniform, displayed={displayed_w}×{displayed_h})",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            ))

    return elements, issues
