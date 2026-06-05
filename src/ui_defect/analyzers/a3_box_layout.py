"""
A3 — Box/Layout Detector
Từ ảnh + A5 text segments → elements[] với bbox, role thô, hierarchy.
Spec: docs/analyzers/A3-box-layout-detector.md
"""
from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..schema.models import BBox, Element, RoleType, Viewport
from ..utils.geometry import contains, iou, normalize_bbox, group_aligned
from .a5_ocr import TextSegment


# ── Cấu hình (có thể tune) ───────────────────────────────────────────────────

@dataclass
class A3Config:
    # Lọc contour
    min_area_px: int = 100          # bỏ box quá nhỏ
    max_area_ratio: float = 0.85    # bỏ box gần bằng toàn ảnh
    # Morphology
    dilate_kernel: int = 3
    dilate_iter: int = 2
    # Fuse OCR
    text_contains_threshold: float = 0.6   # text box nằm trong container ≥ 60% → child
    iou_merge_threshold: float = 0.5       # 2 box gần như nhau → merge
    # Role heuristic
    divider_aspect_ratio: float = 5.0      # w/h > 5 (hoặc h/w > 5) → divider
    button_max_area_px: int = 40_000       # box nhỏ hơn ngưỡng này mới là button
    border_radius_proxy: float = 0.1       # (h / min_side) < này → bo góc
    # Hierarchy
    containment_threshold: float = 0.75


# ── Helpers ──────────────────────────────────────────────────────────────────

def _next_id() -> str:
    return "e" + uuid.uuid4().hex[:6]


def _contour_to_bbox(c: np.ndarray) -> BBox:
    x, y, w, h = cv2.boundingRect(c)
    return BBox(x=float(x), y=float(y), w=float(w), h=float(h))


def _has_rounded_corners(img_gray: np.ndarray, bbox: BBox, threshold: float = 0.1) -> bool:
    """
    Ước lượng bo góc bằng cách so sánh vùng góc với nền.
    Đơn giản: nếu corner pixels trung bình sáng (= nền) → bo góc.
    """
    x, y, w, h = int(bbox.x), int(bbox.y), int(bbox.w), int(bbox.h)
    r = max(3, min(w, h) // 5)
    corners = [
        img_gray[y:y+r, x:x+r],
        img_gray[y:y+r, x+w-r:x+w],
        img_gray[y+h-r:y+h, x:x+r],
        img_gray[y+h-r:y+h, x+w-r:x+w],
    ]
    corner_means = [c.mean() for c in corners if c.size > 0]
    if not corner_means:
        return False
    # Lấy mean của vùng giữa element để làm baseline màu nền
    cy1, cy2 = y + h//3, y + 2*h//3
    cx1, cx2 = x + w//3, x + 2*w//3
    center_region = img_gray[cy1:cy2, cx1:cx2]
    if center_region.size == 0:
        return False
    center_mean = center_region.mean()
    bg_mean = img_gray.mean()
    # Nếu corner gần màu nền hơn là gần màu element → có bo góc
    corner_avg = sum(corner_means) / len(corner_means)
    return abs(corner_avg - bg_mean) < abs(center_mean - bg_mean) * 0.5


# ── CV pipeline ──────────────────────────────────────────────────────────────

def _detect_non_text_regions(
    img: Image.Image,
    cfg: A3Config,
) -> list[BBox]:
    """
    Canny + morphology + findContours → bbox ứng viên cho non-text regions.
    """
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    # Denoise nhẹ
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    # Canny
    edges = cv2.Canny(blur, threshold1=30, threshold2=100)
    # Dilate để đóng khoảng trống nhỏ bên trong UI element
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (cfg.dilate_kernel, cfg.dilate_kernel)
    )
    dilated = cv2.dilate(edges, kernel, iterations=cfg.dilate_iter)
    # Contours
    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    img_area = img.width * img.height
    candidates: list[BBox] = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < cfg.min_area_px:
            continue
        if area / img_area > cfg.max_area_ratio:
            continue
        candidates.append(_contour_to_bbox(c))
    return candidates


def _classify_role(
    bbox: BBox,
    has_text_child: bool,
    cfg: A3Config,
    img_gray: Optional[np.ndarray] = None,
) -> tuple[RoleType, float]:
    """
    Heuristic phân loại role thô. Trả (role, confidence).
    """
    w, h = bbox.w, bbox.h
    area = w * h
    if w == 0 or h == 0:
        return "unknown", 0.3

    aspect = max(w, h) / min(w, h)
    if aspect >= cfg.divider_aspect_ratio:
        thickness = min(w, h)
        if thickness <= 4:
            return "divider", 0.85
        return "divider", 0.6

    if has_text_child and area <= cfg.button_max_area_px:
        # Kiểm tra bo góc → button vs text label
        if img_gray is not None and _has_rounded_corners(img_gray, bbox):
            return "button", 0.6
        return "container", 0.5  # có thể là card nhỏ

    if area > cfg.button_max_area_px and has_text_child:
        return "container", 0.6

    if not has_text_child and area > 1000:
        # Có thể là image/icon region
        return "image", 0.4  # confidence thấp — A6/A7 sẽ xác nhận

    return "container", 0.35


# ── Fuse OCR text boxes ──────────────────────────────────────────────────────

def _fuse_text_segments(
    candidates: list[BBox],
    text_segments: list[TextSegment],
    cfg: A3Config,
) -> tuple[list[BBox], list[TextSegment]]:
    """
    - Text box đã nằm trong candidate → đánh dấu là child (không thêm mới).
    - Text box orphan (không trong candidate nào) → thêm vào danh sách.
    Trả: (updated_candidates, orphan_texts).
    """
    orphans = []
    for i, seg in enumerate(text_segments):
        # Kiểm tra xem bbox seg có nằm trong candidate nào không
        in_container = any(
            contains(c, seg.bbox, cfg.text_contains_threshold) for c in candidates
        )
        if not in_container:
            orphans.append(seg)

    return candidates, orphans


# ── Merge trùng lặp ──────────────────────────────────────────────────────────

def _merge_overlapping(bboxes: list[BBox], threshold: float = 0.5) -> list[BBox]:
    """
    Gộp 2 bbox nếu IoU > threshold (lấy bounding box lớn hơn).
    """
    if not bboxes:
        return []
    merged = list(bboxes)
    changed = True
    while changed:
        changed = False
        result: list[BBox] = []
        used = [False] * len(merged)
        for i in range(len(merged)):
            if used[i]:
                continue
            current = merged[i]
            for j in range(i + 1, len(merged)):
                if used[j]:
                    continue
                if iou(current, merged[j]) >= threshold:
                    # Lấy bounding box bao ngoài cả 2
                    x = min(current.x, merged[j].x)
                    y = min(current.y, merged[j].y)
                    x2 = max(current.x + current.w, merged[j].x + merged[j].w)
                    y2 = max(current.y + current.h, merged[j].y + merged[j].h)
                    current = BBox(x=x, y=y, w=x2 - x, h=y2 - y)
                    used[j] = True
                    changed = True
            result.append(current)
            used[i] = True
        merged = result
    return merged


# ── Xây dựng hierarchy ────────────────────────────────────────────────────────

def _build_hierarchy(elements: list[Element], cfg: A3Config) -> list[Element]:
    """
    Gán parent/children dựa trên containment hình học.
    Element nhỏ nhất chứa trong element lớn hơn → parent = element lớn.
    """
    # Sắp theo diện tích tăng dần → element nhỏ được assign trước
    sorted_idx = sorted(range(len(elements)), key=lambda i: elements[i].bbox.w * elements[i].bbox.h)
    for i in sorted_idx:
        elem = elements[i]
        best_parent: Optional[str] = None
        best_area = float("inf")
        for j in sorted_idx:
            if i == j:
                continue
            candidate = elements[j]
            c_area = candidate.bbox.w * candidate.bbox.h
            e_area = elem.bbox.w * elem.bbox.h
            if c_area <= e_area:
                continue
            if contains(candidate.bbox, elem.bbox, cfg.containment_threshold):
                if c_area < best_area:
                    best_area = c_area
                    best_parent = candidate.id
        if best_parent:
            elem.parent = best_parent
            for e in elements:
                if e.id == best_parent:
                    if elem.id not in e.children:
                        e.children.append(elem.id)
                    break
    return elements


# ── Thêm grouping (list/row/col) ──────────────────────────────────────────────

def _add_grouping(elements: list[Element]) -> list[Element]:
    """
    Nhóm element thẳng hàng → tạo container ảo với role="list".
    Chỉ nhóm orphan (chưa có parent).
    """
    orphans = [e for e in elements if e.parent is None]
    bboxes = [e.bbox for e in orphans]

    new_containers: list[Element] = []
    for axis in ("row", "col"):
        groups = group_aligned(bboxes, axis=axis, tolerance=12.0)
        for grp in groups:
            if len(grp.indices) < 3:
                continue
            members = [orphans[i] for i in grp.indices]
            xs = [e.bbox.x for e in members]
            ys = [e.bbox.y for e in members]
            x2s = [e.bbox.x + e.bbox.w for e in members]
            y2s = [e.bbox.y + e.bbox.h for e in members]
            container_bbox = BBox(
                x=min(xs), y=min(ys),
                w=max(x2s) - min(xs),
                h=max(y2s) - min(ys),
            )
            container_id = _next_id()
            child_ids = [e.id for e in members]
            for e in members:
                e.parent = container_id
            img_w = max(x2s) or 1
            img_h = max(y2s) or 1
            new_containers.append(Element(
                id=container_id,
                role="list",
                source="vision",
                confidence=0.5,
                bbox=container_bbox,
                bbox_norm=normalize_bbox(container_bbox, int(img_w), int(img_h)),
                children=child_ids,
                visible=True,
            ))
    return elements + new_containers


# ── Public API ────────────────────────────────────────────────────────────────

def detect_layout(
    img: Image.Image,
    viewport: Viewport,
    text_segments: list[TextSegment] | None = None,
    cfg: A3Config | None = None,
) -> list[Element]:
    """
    Từ ảnh (+ optional text segments từ A5) → list Element với bbox, role, hierarchy.
    Tất cả elements có source="vision", confidence < 1.
    """
    if cfg is None:
        cfg = A3Config()
    if text_segments is None:
        text_segments = []

    img_w, img_h = img.width, img.height

    # 1. Detect non-text regions bằng CV
    cv_bboxes = _detect_non_text_regions(img, cfg)

    # 2. Fuse: lấy thêm orphan text box (text không nằm trong CV region nào)
    cv_bboxes, orphan_texts = _fuse_text_segments(cv_bboxes, text_segments, cfg)

    # 3. Merge overlapping CV boxes
    cv_bboxes = _merge_overlapping(cv_bboxes, threshold=cfg.iou_merge_threshold)

    # Chuẩn bị ảnh xám để heuristic role
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # 4. Tạo Element từ CV boxes
    elements: list[Element] = []
    text_bboxes = [s.bbox for s in text_segments]

    for bbox in cv_bboxes:
        has_text = any(contains(bbox, tb, cfg.text_contains_threshold) for tb in text_bboxes)
        role, conf = _classify_role(bbox, has_text, cfg, gray)
        eid = _next_id()
        elements.append(Element(
            id=eid,
            role=role,
            source="vision",
            confidence=conf,
            bbox=bbox,
            bbox_norm=normalize_bbox(bbox, img_w, img_h),
            visible=True,
        ))

    # 5. Thêm text-only elements từ orphan text segments
    for seg in orphan_texts:
        if seg.level != "line":
            continue
        eid = _next_id()
        elements.append(Element(
            id=eid,
            role="text",
            source="vision",
            confidence=seg.confidence * 0.8,
            bbox=seg.bbox,
            bbox_norm=normalize_bbox(seg.bbox, img_w, img_h),
            text=seg.text,
            visible=True,
        ))

    # 6. Gán text content từ text_segments vào elements có role text/button
    for elem in elements:
        if elem.text is not None:
            continue
        matching_texts = [
            s.text for s in text_segments
            if s.level == "line" and contains(elem.bbox, s.bbox, 0.5)
        ]
        if matching_texts:
            elem.text = " ".join(matching_texts)

    # 7. Hierarchy (containment)
    elements = _build_hierarchy(elements, cfg)

    # 8. Group alignment → list containers ảo
    elements = _add_grouping(elements)

    return elements
