"""
R5 — Severity Baseline + Modifier System

Chuẩn hoá gán severity + severity_range cho mọi rule,
bao gồm modifier ngữ cảnh để chốt mức cuối trong range.
"""
from __future__ import annotations

from ..schema.models import BBox, SeverityRange, SeverityType

SEVERITY_ORDER: list[str] = ["trivial", "low", "medium", "high", "critical"]


def _clamp(idx: int) -> int:
    return max(0, min(len(SEVERITY_ORDER) - 1, idx))


def apply_modifiers(
    severity: SeverityType,
    modifiers: list[int],
    severity_range: SeverityRange,
) -> SeverityType:
    """
    Áp dụng list modifier (+/-1) lên severity baseline, clamp vào severity_range.

    severity: mức baseline ("critical"|"high"|"medium"|"low"|"trivial")
    modifiers: list of int (+1 = lên 1 mức, -1 = xuống 1 mức)
    severity_range: giới hạn output vào [min, max]
    Returns: SeverityType sau khi điều chỉnh.
    """
    idx = SEVERITY_ORDER.index(severity)
    delta = sum(modifiers)
    new_idx = _clamp(idx + delta)

    min_idx = SEVERITY_ORDER.index(severity_range.min)
    max_idx = SEVERITY_ORDER.index(severity_range.max)

    result_idx = max(min_idx, min(max_idx, new_idx))
    return SEVERITY_ORDER[result_idx]  # type: ignore[return-value]


def get_role_modifier(role: str, interactive: bool = False) -> int:
    """
    Modifier ngữ cảnh theo role của element (theo R5 spec §2.1).

    Trả về int modifier (+1 lên, -1 xuống, -2 xuống mạnh).
    """
    if role == "button":
        return +1
    if role == "input":
        return +1
    if role == "nav":
        return +1
    if role == "icon":
        # Icon decorative (interactive=false) → -2; icon chức năng → 0
        return 0 if interactive else -2
    if role == "image":
        # image hero/product → +1; background/decorative không có interactive cờ
        # Dùng interactive như proxy: image tương tác = hero
        return +1 if interactive else -2
    if role == "container":
        return -1
    if role in ("skeleton", "spinner"):
        return -2
    # text label phụ/caption không phân biệt được ở đây → baseline 0
    return 0


def get_position_modifier(bbox: BBox, viewport_h: int) -> int:
    """
    Modifier theo vị trí trên màn hình (theo R5 spec §2.2).

    Top-fold (y < viewport_h × 0.4) → +1, còn lại → 0.
    Below-fold (y > viewport_h) → -1 (element cần scroll để thấy).
    """
    top_fold_threshold = viewport_h * 0.4
    if bbox.y < top_fold_threshold:
        return +1
    if bbox.y > viewport_h:
        return -1
    return 0


def clamp_confidence(value: float) -> float:
    """Clamp confidence vào [0.1, 0.99]."""
    return max(0.1, min(0.99, value))
