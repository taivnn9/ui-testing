"""
A6 — Icon/Graphic Detector
Phát hiện và phân loại icon/đồ hoạ nhỏ từ pixel — không train.
Spec: docs/analyzers/A6-icon-graphic-detector.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import BBox, Element, ImageMeta, RoleType, Viewport
from ..utils.geometry import normalize_bbox

# ── Cấu hình ─────────────────────────────────────────────────────────────────

@dataclass
class A6Config:
    min_side_px: int = 14          # cạnh ngắn tối thiểu của icon
    max_side_px: int = 120         # cạnh ngắn tối đa
    min_aspect: float = 0.33       # w/h hoặc h/w (sau flip)
    max_aspect: float = 3.0
    icon_max_colors: int = 12      # > 12 màu khác biệt → có thể ảnh
    photo_min_colors: int = 24     # > 24 → gần chắc ảnh
    edge_density_min: float = 0.10 # edge_density thấp → flat/đặc
    resize_for_color: int = 32     # resize về đây trước khi đếm màu
    template_match_threshold: float = 0.7  # threshold matchTemplate


# ── Helpers ──────────────────────────────────────────────────────────────────

def _edge_density(crop_gray: np.ndarray) -> float:
    if crop_gray.size == 0:
        return 0.0
    edges = cv2.Canny(crop_gray, 30, 100)
    return float(edges.sum() / 255) / crop_gray.size


def _color_count(crop_rgb: np.ndarray, resize_to: int = 32) -> int:
    """Số màu khác biệt sau khi quantize về resize_to×resize_to."""
    if crop_rgb.size == 0:
        return 0
    small = cv2.resize(crop_rgb, (resize_to, resize_to), interpolation=cv2.INTER_AREA)
    # Quantize: chia mỗi channel thành 8 mức (32-step)
    quantized = (small // 32) * 32
    flat = quantized.reshape(-1, 3)
    return int(len(np.unique(flat, axis=0)))


def _classify_icon_vs_photo(
    bbox: BBox,
    crop_rgb: np.ndarray,
    crop_gray: np.ndarray,
    cfg: A6Config,
) -> tuple[str, float]:
    """
    Phân loại: 'icon' | 'photo' | 'unknown'
    Trả (subtype, confidence).
    """
    w, h = int(bbox.w), int(bbox.h)
    if w == 0 or h == 0:
        return "unknown", 0.0

    short = min(w, h)
    long = max(w, h)
    aspect = long / short if short > 0 else 999

    if short < cfg.min_side_px or short > cfg.max_side_px:
        return "unknown", 0.1
    if aspect > cfg.max_aspect:
        return "unknown", 0.1

    n_colors = _color_count(crop_rgb, cfg.resize_for_color)
    edge_d = _edge_density(crop_gray)

    if n_colors > cfg.photo_min_colors:
        return "photo", 0.85
    if n_colors <= cfg.icon_max_colors and edge_d >= cfg.edge_density_min:
        conf = min(0.9, 0.5 + (cfg.icon_max_colors - n_colors) / cfg.icon_max_colors * 0.4
                   + edge_d * 0.3)
        return "icon", round(conf, 2)
    if n_colors <= cfg.icon_max_colors:
        # ít màu nhưng edge thấp → solid icon hoặc placeholder
        return "icon", 0.5
    return "unknown", 0.3


# ── Template matching (optional) ─────────────────────────────────────────────

# Các template icon phổ biến: sinh tổng hợp (không dùng file ngoài).
# Mỗi template là dict: name → numpy array gray (16×16 hoặc 24×24).
def _make_templates() -> dict[str, np.ndarray]:
    """Tạo bộ template icon đơn giản bằng code (không cần file ngoài)."""
    templates: dict[str, np.ndarray] = {}
    # Arrow right (→): dải diagonal giảm dần
    arr = np.zeros((24, 24), dtype=np.uint8)
    for i in range(24):
        arr[i, min(i, 23)] = 255
        if i > 0:
            arr[i - 1, min(i, 23)] = 200
    templates["arrow_right"] = arr
    # Close X: 2 đường chéo
    arr = np.zeros((24, 24), dtype=np.uint8)
    for i in range(24):
        arr[i, i] = 255
        arr[i, 23 - i] = 255
    templates["close_x"] = arr
    # Hamburger: 3 đường ngang
    arr = np.zeros((24, 24), dtype=np.uint8)
    for row in (5, 12, 19):
        arr[row, 2:22] = 255
    templates["hamburger"] = arr
    # Search: vòng tròn + cán
    arr = np.zeros((24, 24), dtype=np.uint8)
    cv2.circle(arr, (9, 9), 6, 255, 2)
    cv2.line(arr, (14, 14), (20, 20), 255, 2)
    templates["search"] = arr
    return templates


_TEMPLATES = _make_templates()


def _template_match(crop_gray: np.ndarray, threshold: float = 0.7) -> Optional[str]:
    """Tìm template match tốt nhất. None nếu không match."""
    best_name = None
    best_score = threshold
    h, w = crop_gray.shape[:2]
    for name, tmpl in _TEMPLATES.items():
        th, tw = tmpl.shape[:2]
        if h < th or w < tw:
            # Scale template xuống
            scale = min(h / th, w / tw) * 0.9
            if scale <= 0:
                continue
            tmpl_r = cv2.resize(tmpl, (max(1, int(tw * scale)), max(1, int(th * scale))))
        else:
            tmpl_r = tmpl
        th_r, tw_r = tmpl_r.shape[:2]
        if h < th_r or w < tw_r:
            continue
        result = cv2.matchTemplate(crop_gray, tmpl_r, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = max_val
            best_name = name
    return best_name


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class IconRegion:
    id: str
    bbox: BBox
    bbox_norm: BBox
    subtype: str        # "icon" | "photo" | "unknown"
    confidence: float
    color_count_approx: int
    edge_density: float
    template_match: Optional[str]
    possible_placeholder: bool
    source: str = "vision"
    parent: Optional[str] = None
    crop: Optional[str] = None


def detect_icons(
    img: Image.Image,
    viewport: Viewport,
    elements: list[Element] | None = None,
    text_bboxes: list[BBox] | None = None,
    cfg: A6Config | None = None,
    use_template_match: bool = True,
) -> list[IconRegion]:
    """
    Phát hiện icon/đồ hoạ nhỏ từ ảnh.
    Ưu tiên dùng elements từ A3; nếu không có thì quét toàn ảnh.
    Loại trừ text-box từ A5.
    """
    if cfg is None:
        cfg = A6Config()
    if text_bboxes is None:
        text_bboxes = []

    arr_rgb = np.array(img.convert("RGB"))
    arr_gray = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY)
    img_w, img_h = img.width, img.height

    # Danh sách vùng cần xét
    candidate_bboxes: list[tuple[BBox, Optional[str]]] = []  # (bbox, parent_id)

    if elements:
        for elem in elements:
            if elem.role in ("image", "unknown", "container", "icon"):
                candidate_bboxes.append((elem.bbox, elem.id))
    else:
        # Fallback: dùng contours
        edges = cv2.Canny(arr_gray, 30, 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            bbox = BBox(x=float(x), y=float(y), w=float(w), h=float(h))
            candidate_bboxes.append((bbox, None))

    results: list[IconRegion] = []

    for bbox, parent_id in candidate_bboxes:
        # Kiểm tra có phải text không
        from ..utils.geometry import iou
        is_text = any(iou(bbox, tb) > 0.4 for tb in text_bboxes)
        if is_text:
            continue

        x1 = max(0, int(bbox.x))
        y1 = max(0, int(bbox.y))
        x2 = min(img_w, int(bbox.x + bbox.w))
        y2 = min(img_h, int(bbox.y + bbox.h))
        if x2 <= x1 or y2 <= y1:
            continue

        crop_rgb = arr_rgb[y1:y2, x1:x2]
        crop_gray = arr_gray[y1:y2, x1:x2]

        subtype, conf = _classify_icon_vs_photo(bbox, crop_rgb, crop_gray, cfg)
        if subtype not in ("icon",):
            continue  # Chỉ giữ icon; photo → A7 xử lý

        n_colors = _color_count(crop_rgb, cfg.resize_for_color)
        edge_d = _edge_density(crop_gray)

        # Template match
        tmatch = None
        if use_template_match and conf >= 0.5:
            tmatch = _template_match(crop_gray, cfg.template_match_threshold)

        # Placeholder detection: màu đồng nhất + kích thước đủ lớn để là ảnh bị vỡ
        # Phải đủ lớn (≥50px) vì icon nav nhỏ cũng có ít màu nhưng không phải placeholder.
        placeholder = False
        min_dim = min(bbox.w, bbox.h)
        if n_colors <= 2 and edge_d < 0.12 and min_dim >= 50:
            placeholder = True

        import uuid
        eid = "ic" + uuid.uuid4().hex[:6]
        results.append(IconRegion(
            id=eid,
            bbox=bbox,
            bbox_norm=normalize_bbox(bbox, img_w, img_h),
            subtype=subtype,
            confidence=conf,
            color_count_approx=n_colors,
            edge_density=round(edge_d, 3),
            template_match=tmatch,
            possible_placeholder=placeholder,
            parent=parent_id,
        ))

    return results


def icon_regions_to_elements(regions: list[IconRegion], img_w: int, img_h: int) -> list[Element]:
    """Chuyển IconRegion thành Element để merge vào elements[]."""
    elements = []
    for r in regions:
        elements.append(Element(
            id=r.id,
            role="icon",
            source="vision",
            confidence=r.confidence,
            bbox=r.bbox,
            bbox_norm=normalize_bbox(r.bbox, img_w, img_h),
            parent=r.parent,
            visible=True,
            # R3-IMG08: chuyển cờ placeholder của A6 xuống image_meta để rule đọc
            image_meta=ImageMeta(possible_placeholder=True) if r.possible_placeholder else None,
        ))
    return elements
