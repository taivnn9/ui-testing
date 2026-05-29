"""
A0 — Normalize + Relation Pre-computer
Gộp output các analyzer → schema chung; tiền tính relations[].
"""
from __future__ import annotations

from dataclasses import dataclass

from ..schema.models import (
    BBox, CandidateIssue, CanonicalDoc, Element, Image as ImageSchema,
    Relation, RelType, Screen,
)
from ..utils.geometry import gap_between, iou, normalize_bbox


# ── Tiền tính relations ───────────────────────────────────────────────────────

def _rel_type(a: BBox, b: BBox) -> list[tuple[RelType, float]]:
    """
    Trả list (rel_type, iou/gap) giữa 2 bbox.
    Một cặp có thể có nhiều loại quan hệ.
    """
    from ..utils.geometry import contains, intersection_area
    rels = []
    iou_val = iou(a, b)
    gap_val = gap_between(a, b)

    if iou_val > 0.05:
        rels.append(("overlaps", iou_val))
    if contains(a, b, threshold=0.8):
        rels.append(("contains", iou_val))
    elif contains(b, a, threshold=0.8):
        rels.append(("contains", iou_val))
    else:
        # Vị trí tương đối
        a_cx = a.x + a.w / 2
        b_cx = b.x + b.w / 2
        a_cy = a.y + a.h / 2
        b_cy = b.y + b.h / 2
        if abs(a_cx - b_cx) >= abs(a_cy - b_cy):
            if a_cx < b_cx:
                rels.append(("left_of", gap_val))
            else:
                rels.append(("right_of", gap_val))
        else:
            if a_cy < b_cy:
                rels.append(("above", gap_val))
            else:
                rels.append(("below", gap_val))
    return rels


def compute_relations(
    elements: list[Element],
    img_w: int,
    img_h: int,
    max_gap_px: float = 200.0,
) -> list[Relation]:
    """
    Tiền tính relations[] giữa mọi cặp element.
    Chỉ tính cặp có gap < max_gap_px (tránh O(n²) trên màn dày đặc).
    """
    relations: list[Relation] = []
    n = len(elements)
    for i in range(n):
        for j in range(i + 1, n):
            a = elements[i]
            b = elements[j]
            gap = gap_between(a.bbox, b.bbox)
            if gap > max_gap_px:
                continue
            rels = _rel_type(a.bbox, b.bbox)
            for rel_type, val in rels:
                iou_val = iou(a.bbox, b.bbox)
                relations.append(Relation(
                    a=a.id, rel=rel_type, b=b.id,
                    gap=round(gap, 1),
                    iou=round(iou_val, 3),
                ))
    return relations


# ── Deduplicate elements ──────────────────────────────────────────────────────

def deduplicate_elements(elements: list[Element], iou_threshold: float = 0.8) -> list[Element]:
    """
    Loại element trùng lặp (cùng bbox, khác nguồn) — giữ lại cái có confidence cao hơn.
    """
    kept: list[Element] = []
    for elem in elements:
        duplicate = False
        for k in kept:
            if iou(elem.bbox, k.bbox) >= iou_threshold:
                # Giữ cái confidence cao hơn
                if elem.confidence > k.confidence:
                    kept.remove(k)
                    kept.append(elem)
                duplicate = True
                break
        if not duplicate:
            kept.append(elem)
    return kept


# ── Fill bbox_norm ─────────────────────────────────────────────────────────────

def fill_bbox_norm(elements: list[Element], img_w: int, img_h: int) -> list[Element]:
    for e in elements:
        if e.bbox_norm.w == 0 and e.bbox_norm.h == 0:
            e.bbox_norm = normalize_bbox(e.bbox, img_w, img_h)
    return elements


# ── Public API ────────────────────────────────────────────────────────────────

def normalize(
    screen: Screen,
    image_path: str,
    img_w: int,
    img_h: int,
    elements: list[Element],
    candidate_issues: list[CandidateIssue] | None = None,
    max_relation_gap_px: float = 200.0,
) -> CanonicalDoc:
    """
    Tạo CanonicalDoc hoàn chỉnh từ output các analyzer.
    """
    # Deduplicate
    elems = deduplicate_elements(elements)
    # Fill bbox_norm
    elems = fill_bbox_norm(elems, img_w, img_h)
    # Tiền tính relations
    relations = compute_relations(elems, img_w, img_h, max_relation_gap_px)

    return CanonicalDoc(
        screen=screen,
        image=ImageSchema(full=image_path, w=img_w, h=img_h),
        elements=elems,
        relations=relations,
        candidate_issues=candidate_issues or [],
    )
