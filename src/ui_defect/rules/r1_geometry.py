"""
R1 — Geometry Rules (hình học không gian)

Tất định hoàn toàn — không cần LLM.
Nguồn: elements[].bbox, relations[], screen.viewport, screen.safe_area, screen.platform.
"""
from __future__ import annotations

from ..schema.models import (
    BBox,
    CandidateIssue,
    CanonicalDoc,
    Evidence,
    SeverityRange,
)
from ..schema.thresholds import (
    GAP_MIN_PX,
    GRID_TOLERANCE_PX,
    GRID_UNIT_LOGICAL,
    OVERFLOW_THRESHOLD,
    OVERLAP_IOU_MIN,
    touch_gap_px,
    touch_min_px,
)
from ..utils.geometry import gap_between, iou
from .r5_severity import apply_modifiers, clamp_confidence, get_position_modifier

# Tolerance pixel cho offscreen check
_OFFSCREEN_TOL_SIDE: float = 2.0
_OFFSCREEN_TOL_BOTTOM: float = 5.0

# Minimum element confidence để rule fire
_MIN_ELEM_CONFIDENCE: float = 0.35


def _visible(elem) -> bool:  # type: ignore[return]
    return elem.visible and elem.confidence >= _MIN_ELEM_CONFIDENCE


def _elem_map(doc: CanonicalDoc) -> dict:
    return {e.id: e for e in doc.elements}


# ---------------------------------------------------------------------------
# R1-LAY01 — Overlap sibling (IoU > 0.05)
# ---------------------------------------------------------------------------

def check_overlap(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-LAY01: IoU > OVERLAP_IOU_MIN (0.05) giữa các sibling không phải parent-child.
    Bỏ qua cặp có role modal/tooltip/skeleton, hoặc badge nhỏ trên icon.
    """
    issues: list[CandidateIssue] = []
    elems = _elem_map(doc)

    _SKIP_ROLES = {"modal", "skeleton", "spinner"}
    _INTERACTIVE_ROLES = {"button", "input", "nav"}

    for rel in doc.relations:
        if rel.rel != "overlaps":
            continue
        if rel.iou <= OVERLAP_IOU_MIN:
            continue

        elem_a = elems.get(rel.a)
        elem_b = elems.get(rel.b)
        if elem_a is None or elem_b is None:
            continue
        if not _visible(elem_a) or not _visible(elem_b):
            continue

        # Bỏ qua parent-child
        if elem_a.parent == elem_b.id or elem_b.parent == elem_a.id:
            continue

        # Bỏ qua nếu một trong 2 là modal/tooltip/skeleton
        if elem_a.role in _SKIP_ROLES or elem_b.role in _SKIP_ROLES:
            continue

        # Bỏ qua badge nhỏ (icon nhỏ đè lên icon khác là chủ ý)
        min_dim_a = min(elem_a.bbox.w, elem_a.bbox.h)
        min_dim_b = min(elem_b.bbox.w, elem_b.bbox.h)
        if (
            elem_a.role == "icon" and min_dim_a < 30
            and elem_b.role == "icon"
        ) or (
            elem_b.role == "icon" and min_dim_b < 30
            and elem_a.role == "icon"
        ):
            continue

        # Bỏ qua z-order rõ ràng (z cao hơn hẳn)
        if abs(elem_a.z - elem_b.z) >= 10:
            continue

        # Issue element = element nhỏ hơn (bị che nhiều hơn)
        area_a = elem_a.bbox.w * elem_a.bbox.h
        area_b = elem_b.bbox.w * elem_b.bbox.h
        issue_elem = elem_a if area_a <= area_b else elem_b

        confidence = clamp_confidence(
            min(elem_a.confidence, elem_b.confidence) * (0.5 + rel.iou * 0.5)
        )

        severity_range = SeverityRange(min="medium", max="critical")
        baseline = "high"
        modifiers: list[int] = []

        # Modifier: một trong 2 là interactive role → +1
        if elem_a.role in _INTERACTIVE_ROLES or elem_b.role in _INTERACTIVE_ROLES:
            modifiers.append(+1)
        # IoU thấp → giảm severity
        if rel.iou < 0.15:
            modifiers.append(-1)
        # Một element decorative → giảm severity
        if (
            (elem_a.role == "icon" and not elem_a.interactive)
            or (elem_b.role == "icon" and not elem_b.interactive)
        ):
            modifiers.append(-2)

        severity = apply_modifiers(baseline, modifiers, severity_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R1-LAY01",
                element=issue_elem.id,
                severity=severity,
                severity_range=severity_range,
                confidence=confidence,
                detail=(
                    f"Overlap giữa {rel.a} và {rel.b}: iou={rel.iou:.3f} > {OVERLAP_IOU_MIN}"
                ),
                evidence=Evidence(bbox=issue_elem.bbox),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R1-LAY02 — Off-screen / cắt mép viewport
# ---------------------------------------------------------------------------

def check_offscreen(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-LAY02: element bbox vượt ra ngoài viewport bounds (±2px tolerance).
    """
    issues: list[CandidateIssue] = []
    vp = doc.screen.viewport
    sa = doc.screen.safe_area

    _DECORATIVE_ROLES = {"image", "container"}
    _IMPORTANT_ROLES = {"button", "input", "text"}

    for elem in doc.elements:
        if not _visible(elem):
            continue

        b = elem.bbox
        violations: list[str] = []

        if b.x < -_OFFSCREEN_TOL_SIDE:
            violations.append("left")
        if b.y < -(sa.top + _OFFSCREEN_TOL_BOTTOM):
            violations.append("top")
        if b.x + b.w > vp.w + _OFFSCREEN_TOL_SIDE:
            violations.append("right")
        if b.y + b.h > vp.h + _OFFSCREEN_TOL_BOTTOM:
            violations.append("bottom")

        if not violations:
            continue

        # offscreen=true từ A3 → dùng confidence cao hơn
        rule_factor = 0.98 if elem.offscreen else 0.95
        confidence = clamp_confidence(elem.confidence * rule_factor)

        severity_range = SeverityRange(min="medium", max="critical")
        baseline = "high"
        modifiers: list[int] = []

        if elem.role in _IMPORTANT_ROLES:
            modifiers.append(+1)
        if elem.role in _DECORATIVE_ROLES and elem.z <= 1:
            modifiers.append(-2)

        # Ảnh nền parallax (role=image, z thấp) → giảm severity
        if elem.role == "image" and not elem.interactive and elem.z <= 1:
            modifiers.append(-1)

        # web platform thường scroll → giảm 1 mức
        if doc.screen.platform == "web":
            modifiers.append(-1)

        severity = apply_modifiers(baseline, modifiers, severity_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R1-LAY02",
                element=elem.id,
                severity=severity,
                severity_range=severity_range,
                confidence=confidence,
                detail=f"Off-screen: {', '.join(violations)}; bbox=({b.x},{b.y},{b.w},{b.h})",
                evidence=Evidence(bbox=b, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R1-LAY03 — Overflow container
# ---------------------------------------------------------------------------

def check_overflow(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-LAY03: element vượt ra ngoài parent bbox > OVERFLOW_THRESHOLD (4px).
    """
    issues: list[CandidateIssue] = []
    elems = _elem_map(doc)

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if not elem.parent:
            continue

        parent = elems.get(elem.parent)
        if parent is None or not _visible(parent):
            continue

        e, p = elem.bbox, parent.bbox

        overflow_right = max(0.0, (e.x + e.w) - (p.x + p.w))
        overflow_bottom = max(0.0, (e.y + e.h) - (p.y + p.h))
        overflow_left = max(0.0, p.x - e.x)
        overflow_top = max(0.0, p.y - e.y)

        max_overflow = max(overflow_right, overflow_bottom, overflow_left, overflow_top)
        if max_overflow <= OVERFLOW_THRESHOLD:
            continue

        # Card image bleed chủ ý: image overflow nhỏ < 10px → trivial, không fire
        if elem.role == "image" and max_overflow < 10.0:
            continue

        confidence = clamp_confidence(
            min(elem.confidence, parent.confidence) * 0.85
        )

        severity_range = SeverityRange(min="low", max="high")
        baseline = "medium"
        modifiers: list[int] = []

        if elem.text_truncated:
            modifiers.append(+1)

        severity = apply_modifiers(baseline, modifiers, severity_range)  # type: ignore[arg-type]

        detail = (
            f"Overflow: right={overflow_right:.1f}px bottom={overflow_bottom:.1f}px "
            f"left={overflow_left:.1f}px top={overflow_top:.1f}px "
            f"(threshold={OVERFLOW_THRESHOLD}px)"
        )
        issues.append(
            CandidateIssue(
                rule="R1-LAY03",
                element=elem.id,
                severity=severity,
                severity_range=severity_range,
                confidence=confidence,
                detail=detail,
                evidence=Evidence(bbox=e),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R1-LAY14 — Near-duplicate position (IoU > 0.9)
# ---------------------------------------------------------------------------

def check_near_duplicate_position(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-LAY14: IoU > 0.9 giữa 2 element không phải parent-child → gần trùng hoàn toàn.
    """
    issues: list[CandidateIssue] = []
    elems = _elem_map(doc)

    _NEAR_DUP_THRESHOLD = 0.9

    for rel in doc.relations:
        if rel.rel != "overlaps":
            continue
        if rel.iou <= _NEAR_DUP_THRESHOLD:
            continue

        elem_a = elems.get(rel.a)
        elem_b = elems.get(rel.b)
        if elem_a is None or elem_b is None:
            continue
        if not _visible(elem_a) or not _visible(elem_b):
            continue

        # Bỏ qua parent-child
        if elem_a.parent == elem_b.id or elem_b.parent == elem_a.id:
            continue

        confidence = clamp_confidence(
            min(elem_a.confidence, elem_b.confidence) * 0.9
        )

        severity_range = SeverityRange(min="low", max="high")
        baseline = "medium"

        issues.append(
            CandidateIssue(
                rule="R1-LAY14",
                element=rel.a,
                severity=baseline,  # type: ignore[arg-type]
                severity_range=severity_range,
                confidence=confidence,
                detail=(
                    f"Phần tử gần trùng vị trí: {rel.a} và {rel.b} iou={rel.iou:.3f}"
                ),
                evidence=Evidence(bbox=elem_a.bbox),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R1-CMP01 — Touch target nhỏ
# ---------------------------------------------------------------------------

def check_touch_target(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-CMP01: interactive elements có touch target < touch_min_px threshold.
    """
    issues: list[CandidateIssue] = []
    dpr = doc.screen.viewport.dpr
    platform = doc.screen.platform
    min_touch = touch_min_px(dpr, platform)

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if not elem.interactive:
            continue

        if elem.touch_target is not None:
            target_w = elem.touch_target.w
            target_h = elem.touch_target.h
        else:
            target_w = elem.bbox.w
            target_h = elem.bbox.h

        if target_w >= min_touch and target_h >= min_touch:
            continue

        confidence = clamp_confidence(elem.confidence * 0.9)

        severity_range = SeverityRange(min="medium", max="high")
        baseline = "high"
        modifiers: list[int] = []

        # Nav icon decorative → medium
        if elem.role == "icon" and not elem.interactive:
            modifiers.append(-1)

        severity = apply_modifiers(baseline, modifiers, severity_range)  # type: ignore[arg-type]

        small_dim = "w" if target_w < min_touch else "h"
        small_val = target_w if target_w < min_touch else target_h
        detail = (
            f"Touch target {small_dim}={small_val:.1f}px < {min_touch:.1f}px "
            f"({platform}; dpr={dpr})"
        )

        issues.append(
            CandidateIssue(
                rule="R1-CMP01",
                element=elem.id,
                severity=severity,
                severity_range=severity_range,
                confidence=confidence,
                detail=detail,
                evidence=Evidence(bbox=elem.bbox),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R1-CMP16 — Khoảng tap chồng nhau
# ---------------------------------------------------------------------------

def check_tap_gap(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-CMP16: gap giữa 2 interactive elements < touch_gap_px (8pt×dpr).
    """
    issues: list[CandidateIssue] = []
    dpr = doc.screen.viewport.dpr
    min_gap = touch_gap_px(dpr)

    # Lấy danh sách interactive elements đủ confidence
    interactive = [e for e in doc.elements if e.interactive and _visible(e)]

    seen_pairs: set[tuple[str, str]] = set()

    for i in range(len(interactive)):
        for j in range(i + 1, len(interactive)):
            ea = interactive[i]
            eb = interactive[j]

            key = (min(ea.id, eb.id), max(ea.id, eb.id))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            gap = gap_between(ea.bbox, eb.bbox)
            if gap >= min_gap:
                continue
            if gap < 0:
                # Đã chồng lấp — R1-LAY01 xử lý
                continue

            confidence = clamp_confidence(
                min(ea.confidence, eb.confidence) * 0.8
            )

            severity_range = SeverityRange(min="low", max="high")
            baseline = "medium"

            issues.append(
                CandidateIssue(
                    rule="R1-CMP16",
                    element=ea.id,
                    severity=baseline,  # type: ignore[arg-type]
                    severity_range=severity_range,
                    confidence=confidence,
                    detail=(
                        f"Khoảng tap quá hẹp: {ea.id} ↔ {eb.id} gap={gap:.1f}px "
                        f"< {min_gap:.1f}px (8pt×dpr={dpr})"
                    ),
                    evidence=Evidence(bbox=ea.bbox),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# R1-ENV01/02/03 — Safe-area, status bar, home indicator
# ---------------------------------------------------------------------------

def check_safe_area(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R1-ENV01: element trong vùng safe_area (notch/home indicator).
    R1-ENV02: element chồng lên status bar.
    R1-ENV03: element chồng lên home indicator (iOS only).
    """
    issues: list[CandidateIssue] = []
    screen = doc.screen
    vp = screen.viewport
    sa = screen.safe_area

    # meta_confidence: nếu screen không có thì mặc định 0.8
    meta_conf: float = getattr(screen, "meta_confidence", 0.8) or 0.8

    _SKIP_ROLES = {"background"}
    _INTERACTIVE_ROLES = {"button", "input"}
    _DECOR_ROLES = {"image"}

    # status_bar_h và nav_bar_h từ screen attrs (A13 device meta)
    status_bar_h: float = getattr(screen, "status_bar_h", 0) or 0
    nav_bar_h: float = getattr(screen, "nav_bar_h", 0) or 0

    _SAFE_OVERLAP_MIN = 10.0  # element phải overlap vùng > 10px để fire

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.role in _SKIP_ROLES:
            continue

        b = elem.bbox
        elem_conf = clamp_confidence(elem.confidence * meta_conf)
        modifiers: list[int] = []
        if elem.role in _INTERACTIVE_ROLES:
            modifiers.append(+1)
        elif elem.role in _DECOR_ROLES and not elem.interactive:
            modifiers.append(-1)

        # --- R1-ENV01: safe_area overlap ---
        sa_violations: list[str] = []

        # Top (notch / status bar)
        if sa.top > 0:
            overlap_top = max(0.0, min(b.y + b.h, sa.top) - b.y)
            if overlap_top > _SAFE_OVERLAP_MIN:
                sa_violations.append(f"top={overlap_top:.1f}px")

        # Bottom (home indicator)
        bottom_zone_start = vp.h - sa.bottom
        if sa.bottom > 0:
            overlap_bottom = max(0.0, (b.y + b.h) - bottom_zone_start)
            if overlap_bottom > _SAFE_OVERLAP_MIN:
                sa_violations.append(f"bottom={overlap_bottom:.1f}px")

        # Left
        if sa.left > 0:
            overlap_left = max(0.0, min(b.x + b.w, sa.left) - b.x)
            if overlap_left > _SAFE_OVERLAP_MIN:
                sa_violations.append(f"left={overlap_left:.1f}px")

        # Right
        right_zone_start = vp.w - sa.right
        if sa.right > 0:
            overlap_right = max(0.0, (b.x + b.w) - right_zone_start)
            if overlap_right > _SAFE_OVERLAP_MIN:
                sa_violations.append(f"right={overlap_right:.1f}px")

        if sa_violations:
            sev = apply_modifiers(  # type: ignore[arg-type]
                "high", modifiers, SeverityRange(min="medium", max="critical")
            )
            issues.append(
                CandidateIssue(
                    rule="R1-ENV01",
                    element=elem.id,
                    severity=sev,
                    severity_range=SeverityRange(min="medium", max="critical"),
                    confidence=elem_conf,
                    detail=f"Safe-area violation: {'; '.join(sa_violations)}",
                    evidence=Evidence(bbox=b),
                )
            )

        # --- R1-ENV02: status bar overlap ---
        if status_bar_h > 0 and b.y < status_bar_h + 4.0:
            overlap = status_bar_h + 4.0 - b.y
            if overlap > 0:
                sev2 = apply_modifiers(  # type: ignore[arg-type]
                    "medium", modifiers, SeverityRange(min="low", max="high")
                )
                issues.append(
                    CandidateIssue(
                        rule="R1-ENV02",
                        element=elem.id,
                        severity=sev2,
                        severity_range=SeverityRange(min="low", max="high"),
                        confidence=elem_conf,
                        detail=(
                            f"Chồng lên status bar: elem.y={b.y:.1f} "
                            f"< status_bar_h={status_bar_h:.1f}+4px"
                        ),
                        evidence=Evidence(bbox=b),
                    )
                )

        # --- R1-ENV03: home indicator overlap (iOS only) ---
        if screen.platform == "ios" and nav_bar_h > 0:
            home_start_y = vp.h - nav_bar_h
            if b.y + b.h > home_start_y + 4.0:
                overlap_hi = (b.y + b.h) - (home_start_y + 4.0)
                sev3 = apply_modifiers(  # type: ignore[arg-type]
                    "medium", modifiers, SeverityRange(min="low", max="high")
                )
                issues.append(
                    CandidateIssue(
                        rule="R1-ENV03",
                        element=elem.id,
                        severity=sev3,
                        severity_range=SeverityRange(min="low", max="high"),
                        confidence=elem_conf,
                        detail=(
                            f"Chồng lên home indicator: overlap={overlap_hi:.1f}px "
                            f"(home_start_y={home_start_y:.1f})"
                        ),
                        evidence=Evidence(bbox=b),
                    )
                )

    return issues
