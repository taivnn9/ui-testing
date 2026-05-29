"""Tiện ích hình học: IoU, containment, bbox helpers."""
from __future__ import annotations

from typing import NamedTuple

from ..schema.models import BBox


def bbox_area(b: BBox) -> float:
    return b.w * b.h


def iou(a: BBox, b: BBox) -> float:
    """Intersection-over-Union giữa 2 bbox."""
    ix = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    inter = ix * iy
    if inter == 0:
        return 0.0
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def intersection_area(a: BBox, b: BBox) -> float:
    ix = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    return ix * iy


def contains(outer: BBox, inner: BBox, threshold: float = 0.8) -> bool:
    """True nếu ít nhất `threshold` diện tích của inner nằm trong outer."""
    inter = intersection_area(outer, inner)
    inner_area = inner.w * inner.h
    if inner_area == 0:
        return False
    return inter / inner_area >= threshold


def normalize_bbox(bbox: BBox, img_w: int, img_h: int) -> BBox:
    return BBox(
        x=bbox.x / img_w,
        y=bbox.y / img_h,
        w=bbox.w / img_w,
        h=bbox.h / img_h,
    )


def gap_between(a: BBox, b: BBox) -> float:
    """Khoảng cách nhỏ nhất giữa 2 cạnh của 2 bbox (âm = chồng lấp)."""
    dx = max(0.0, max(a.x, b.x) - min(a.x + a.w, b.x + b.w))
    dy = max(0.0, max(a.y, b.y) - min(a.y + a.h, b.y + b.h))
    return max(dx, dy)


class AlignGroup(NamedTuple):
    """Nhóm element thẳng hàng."""
    axis: str       # "row" | "col"
    indices: list[int]
    center: float   # trung tâm trục vuông góc (y cho row, x cho col)


def group_aligned(
    bboxes: list[BBox],
    axis: str = "row",
    tolerance: float = 8.0,
) -> list[AlignGroup]:
    """
    Gom element thành nhóm thẳng hàng.
    axis="row": xếp ngang (cùng y-center), axis="col": xếp dọc (cùng x-center).
    """
    if not bboxes:
        return []
    centers = [
        (b.y + b.h / 2) if axis == "row" else (b.x + b.w / 2)
        for b in bboxes
    ]
    sorted_idx = sorted(range(len(bboxes)), key=lambda i: centers[i])
    groups: list[AlignGroup] = []
    current: list[int] = [sorted_idx[0]]
    current_center = centers[sorted_idx[0]]

    for idx in sorted_idx[1:]:
        if abs(centers[idx] - current_center) <= tolerance:
            current.append(idx)
            current_center = sum(centers[i] for i in current) / len(current)
        else:
            if len(current) >= 2:
                groups.append(AlignGroup(axis=axis, indices=current, center=current_center))
            current = [idx]
            current_center = centers[idx]

    if len(current) >= 2:
        groups.append(AlignGroup(axis=axis, indices=current, center=current_center))
    return groups
