"""
A12 — Interactivity Classifier
Đoán phần tử tương tác được từ pixel — precision-first, không có DOM.
Spec: docs/analyzers/A12-interactivity-classifier.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import BBox, Element
from ..utils.geometry import normalize_bbox


# ── Từ điển hành động (vi + en) ───────────────────────────────────────────────

_ACTION_WORDS_VI = {
    "đăng nhập", "đăng ký", "tiếp tục", "xác nhận", "đồng ý",
    "hủy", "lưu", "gửi", "mua", "thanh toán", "tìm kiếm",
    "thêm", "xóa", "chỉnh sửa", "xem thêm", "tải về",
}

_ACTION_WORDS_EN = {
    "login", "sign in", "sign up", "continue", "confirm", "cancel",
    "save", "submit", "buy", "checkout", "search", "add", "delete",
    "edit", "more", "download", "ok", "next", "back", "apply",
}

_ACTION_WORDS = _ACTION_WORDS_VI | _ACTION_WORDS_EN


# ── Cấu hình ─────────────────────────────────────────────────────────────────

@dataclass
class A12Config:
    interactive_threshold: float = 0.65   # score ≥ này → interactive=True (precision)
    ambiguous_threshold: float = 0.40     # score ≥ này nhưng < interactive → ambiguous

    # Signal weights (tổng tối đa không được > 1 một cách cứng nhắc; scoring cộng dồn)
    w_rounded_rect: float = 0.20
    w_bordered_box: float = 0.18
    w_action_label: float = 0.25
    w_short_centered_text: float = 0.12
    w_icon_only_box: float = 0.18
    w_bottom_tab_bar: float = 0.30
    w_fab_position: float = 0.28
    w_elevated_bg: float = 0.15
    w_form_field: float = 0.20

    # Hình dạng
    rounded_arc_ratio_min: float = 0.15   # arc_len / perimeter → bo góc
    border_edge_density_min: float = 0.25 # Canny density trên perimeter region

    # Text
    short_text_max_chars: int = 30
    center_tolerance_ratio: float = 0.25  # text offset/box_w < này → centered

    # Tab bar
    tab_bar_bottom_ratio: float = 0.20    # nằm trong 20% dưới viewport
    tab_bar_min_icons: int = 3
    tab_bar_max_icons: int = 5

    # FAB
    fab_min_size_px: int = 40
    fab_corner_ratio: float = 0.15        # phần tử nằm trong 15% bottom-right

    # Elevated bg
    elevated_bg_sample_pad: int = 6       # padding lấy mẫu pixel ngoài bbox
    elevated_contrast_min: float = 15.0   # ΔL tối thiểu


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crop_element(
    arr_rgb: np.ndarray,
    bbox: BBox,
    img_h: int,
    img_w: int,
) -> Optional[tuple[np.ndarray, np.ndarray]]:
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(img_w, int(bbox.x + bbox.w))
    y2 = min(img_h, int(bbox.y + bbox.h))
    if x2 <= x1 + 2 or y2 <= y1 + 2:
        return None
    crop_rgb = arr_rgb[y1:y2, x1:x2]
    crop_gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    return crop_rgb, crop_gray


def _signal_rounded_rect(crop_gray: np.ndarray, cfg: A12Config) -> bool:
    """
    approxPolyDP: nếu số đỉnh xấp xỉ > 8 hoặc contour phức tạp → bo góc.
    Đơn giản hơn: so sánh diện tích contour vs diện tích bbox → nếu chênh ít → không bo.
    """
    if crop_gray.size == 0:
        return False
    h, w = crop_gray.shape[:2]
    edges = cv2.Canny(crop_gray, 30, 100)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    largest = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(largest, True)
    if perimeter == 0:
        return False
    approx = cv2.approxPolyDP(largest, 0.04 * perimeter, True)
    # Bo góc → nhiều đỉnh (>= 8) hoặc contour area vs bbox area ratio không cao
    contour_area = cv2.contourArea(largest)
    bbox_area = float(h * w)
    fill_ratio = contour_area / bbox_area if bbox_area > 0 else 0.0
    n_vertices = len(approx)
    return n_vertices >= 8 or (n_vertices >= 6 and fill_ratio > 0.5)


def _signal_bordered_box(crop_gray: np.ndarray, cfg: A12Config) -> bool:
    """Canny edge density trên dải perimeter trong → có viền rõ."""
    h, w = crop_gray.shape[:2]
    if h < 8 or w < 8:
        return False
    thickness = max(2, min(h, w) // 8)
    edges = cv2.Canny(crop_gray, 30, 100)

    perimeter_mask = np.zeros_like(edges, dtype=bool)
    perimeter_mask[:thickness, :] = True
    perimeter_mask[-thickness:, :] = True
    perimeter_mask[:, :thickness] = True
    perimeter_mask[:, -thickness:] = True

    perimeter_pixels = edges[perimeter_mask]
    if perimeter_pixels.size == 0:
        return False
    density = float(perimeter_pixels.sum() / 255) / perimeter_pixels.size
    return density >= cfg.border_edge_density_min


def _signal_action_label(text: Optional[str]) -> bool:
    if not text:
        return False
    normalized = text.strip().lower()
    if normalized in _ACTION_WORDS:
        return True
    for word in _ACTION_WORDS:
        if word in normalized:
            return True
    return False


def _signal_short_centered_text(
    elem: Element,
    text: Optional[str],
    cfg: A12Config,
) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) > cfg.short_text_max_chars or len(stripped) == 0:
        return False
    return True


def _signal_icon_only_box(elem_id: str, icon_region_ids: set[str]) -> bool:
    return elem_id in icon_region_ids


def _signal_bottom_tab_bar(
    elem: Element,
    all_elements: list[Element],
    viewport_h: int,
    cfg: A12Config,
) -> bool:
    """
    Phát hiện tab bar: row 3-5 elements nằm trong 20% dưới viewport, cách đều nhau.
    Cách kiểm tra: đếm elements có y_center > viewport_h*(1-tab_bar_bottom_ratio)
    và xấp xỉ cùng y-range.
    """
    threshold_y = viewport_h * (1.0 - cfg.tab_bar_bottom_ratio)
    elem_cy = elem.bbox.y + elem.bbox.h / 2
    if elem_cy < threshold_y:
        return False

    bottom_elems = [
        e for e in all_elements
        if (e.bbox.y + e.bbox.h / 2) >= threshold_y
        and abs((e.bbox.y + e.bbox.h / 2) - elem_cy) < elem.bbox.h * 1.5
    ]
    return cfg.tab_bar_min_icons <= len(bottom_elems) <= cfg.tab_bar_max_icons


def _signal_fab_position(
    elem: Element,
    img_w: int,
    img_h: int,
    cfg: A12Config,
) -> bool:
    """FAB: element tròn/lớn nằm góc dưới phải."""
    w, h = elem.bbox.w, elem.bbox.h
    if w < cfg.fab_min_size_px or h < cfg.fab_min_size_px:
        return False
    aspect = max(w, h) / (min(w, h) + 1e-6)
    if aspect > 1.4:
        return False
    cx = elem.bbox.x + w / 2
    cy = elem.bbox.y + h / 2
    in_bottom_right = (
        cx > img_w * (1.0 - cfg.fab_corner_ratio * 2)
        and cy > img_h * (1.0 - cfg.fab_corner_ratio * 2)
    )
    return in_bottom_right


def _signal_elevated_bg(
    arr_rgb: np.ndarray,
    bbox: BBox,
    img_h: int,
    img_w: int,
    cfg: A12Config,
) -> bool:
    """
    Nền box khác màu nền ngoài: lấy mẫu pixel trong bbox vs pixel ngay ngoài bbox.
    Dùng luminance đơn giản (không cần Lab).
    """
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(img_w, int(bbox.x + bbox.w))
    y2 = min(img_h, int(bbox.y + bbox.h))
    if x2 <= x1 or y2 <= y1:
        return False

    inner = arr_rgb[y1:y2, x1:x2]
    if inner.size == 0:
        return False

    pad = cfg.elevated_bg_sample_pad
    ox1 = max(0, x1 - pad)
    oy1 = max(0, y1 - pad)
    ox2 = min(img_w, x2 + pad)
    oy2 = min(img_h, y2 + pad)

    outer_full = arr_rgb[oy1:oy2, ox1:ox2]
    outer_mask = np.ones(outer_full.shape[:2], dtype=bool)
    iy1 = y1 - oy1
    iy2 = y2 - oy1
    ix1 = x1 - ox1
    ix2 = x2 - ox1
    outer_mask[iy1:iy2, ix1:ix2] = False

    outer_pixels = outer_full[outer_mask]
    if outer_pixels.size == 0:
        return False

    def _lum(pixels: np.ndarray) -> float:
        p = pixels.astype(np.float32)
        return float((0.299 * p[:, 0] + 0.587 * p[:, 1] + 0.114 * p[:, 2]).mean())

    inner_lum = _lum(inner.reshape(-1, 3))
    outer_lum = _lum(outer_pixels.reshape(-1, 3))
    return abs(inner_lum - outer_lum) >= cfg.elevated_contrast_min


def _signal_form_field(
    elem: Element,
    all_elements: list[Element],
) -> bool:
    """
    Heuristic: box dài (aspect ratio w/h > 3), có text element ngay bên trên trong ~30px.
    """
    w, h = elem.bbox.w, elem.bbox.h
    if h == 0:
        return False
    if w / h < 3.0:
        return False
    threshold_above = 30.0
    for other in all_elements:
        if other.id == elem.id:
            continue
        if other.role != "text":
            continue
        other_bottom = other.bbox.y + other.bbox.h
        gap = elem.bbox.y - other_bottom
        if 0 <= gap <= threshold_above:
            overlap_x = min(elem.bbox.x + w, other.bbox.x + other.bbox.w) - max(elem.bbox.x, other.bbox.x)
            if overlap_x > w * 0.3:
                return True
    return False


# ── Public API ────────────────────────────────────────────────────────────────

def classify_interactivity(
    img: Image.Image,
    elements: list[Element],
    text_segments=None,
    icon_region_ids: set[str] | None = None,
    viewport_h: int = 844,
    cfg: A12Config | None = None,
) -> list[Element]:
    """
    Enrich mỗi element với interactive, interactive_confidence, interactive_signals.
    Precision-first: ngưỡng ≥ 0.65 để gán interactive=True.
    Trả elements đã cập nhật (in-place).
    """
    if cfg is None:
        cfg = A12Config()
    if icon_region_ids is None:
        icon_region_ids = set()

    arr_rgb = np.array(img.convert("RGB"))
    img_h, img_w = arr_rgb.shape[:2]

    # Build text lookup: element_id → text (từ element.text hoặc text_segments)
    text_map: dict[str, str] = {}
    for elem in elements:
        if elem.text:
            text_map[elem.id] = elem.text

    if text_segments:
        from ..utils.geometry import contains as _contains
        for seg in text_segments:
            if not hasattr(seg, "text") or not seg.text:
                continue
            if not hasattr(seg, "level") or seg.level != "line":
                continue
            for elem in elements:
                if elem.id not in text_map and _contains(elem.bbox, seg.bbox, 0.5):
                    text_map[elem.id] = seg.text
                    break

    non_interactive_roles = {"divider", "skeleton", "spinner", "modal"}

    for elem in elements:
        if elem.role in non_interactive_roles:
            elem.interactive = False
            elem.confidence = min(elem.confidence, 0.95)
            continue

        crops = _crop_element(arr_rgb, elem.bbox, img_h, img_w)
        crop_rgb = crops[0] if crops else None
        crop_gray = crops[1] if crops else None

        text = text_map.get(elem.id) or elem.text

        signals: list[str] = []
        score: float = 0.0

        # Nếu role đã là button/input/toggle/tab/nav → có baseline signal
        if elem.role in ("button", "input", "toggle", "tab", "nav"):
            score += 0.25
            signals.append("role_hint")

        if crop_gray is not None:
            if _signal_rounded_rect(crop_gray, cfg):
                score += cfg.w_rounded_rect
                signals.append("rounded_rect")

            if _signal_bordered_box(crop_gray, cfg):
                score += cfg.w_bordered_box
                signals.append("bordered_box")

        if _signal_action_label(text):
            score += cfg.w_action_label
            signals.append("action_label")

        if _signal_short_centered_text(elem, text, cfg):
            score += cfg.w_short_centered_text
            signals.append("short_centered_text")

        if _signal_icon_only_box(elem.id, icon_region_ids):
            score += cfg.w_icon_only_box
            signals.append("icon_only_box")

        if _signal_bottom_tab_bar(elem, elements, viewport_h, cfg):
            score += cfg.w_bottom_tab_bar
            signals.append("bottom_tab_bar")

        if _signal_fab_position(elem, img_w, img_h, cfg):
            score += cfg.w_fab_position
            signals.append("fab_position")

        if crop_rgb is not None and _signal_elevated_bg(arr_rgb, elem.bbox, img_h, img_w, cfg):
            score += cfg.w_elevated_bg
            signals.append("elevated_bg")

        if _signal_form_field(elem, elements):
            score += cfg.w_form_field
            signals.append("form_field")

        score = min(score, 0.95)

        elem.interactive = score >= cfg.interactive_threshold
        elem.source = "vision"
        if elem.confidence >= 1.0:
            elem.confidence = min(score, 0.9)

    return elements
