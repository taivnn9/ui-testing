"""
Rule Engine — chạy tất cả R1–R4, deduplicate, trả về CanonicalDoc đã bổ sung issues.

Thứ tự chạy:
  1. R1-LAY02  (off-screen — nhanh, cần trước)
  2. R1-ENV01/02/03  (safe-area)
  3. R1-LAY01  (overlap siblings)
  4. R1-LAY14  (near-dup position)
  5. R1-LAY03  (overflow container)
  6. R1-CMP01  (touch target)
  7. R1-CMP16  (tap gap)
  8. R2  (color/contrast)
  9. R3  (image)
  10. R4  (text)
"""
from __future__ import annotations

from ..schema.models import CandidateIssue, CanonicalDoc
from .r1_geometry import (
    check_near_duplicate_position,
    check_offscreen,
    check_overflow,
    check_overlap,
    check_safe_area,
    check_tap_gap,
    check_touch_target,
)
from .r2_color import check_contrast, check_dark_mode, check_opacity
from .r3_image import (
    check_blur,
    check_hash_duplicates,
    check_icon_centering,
    check_placeholder_icon,
)
from .r4_text import (
    check_debug_text,
    check_epoch,
    check_escape_literals,
    check_font_size,
    check_i18n_keys,
    check_lorem_ipsum,
    check_mojibake,
    check_placeholders,
    check_stacktrace,
    check_truncation,
)


def _deduplicate(issues: list[CandidateIssue]) -> list[CandidateIssue]:
    """
    Loại bỏ duplicate issues: cùng (rule, element).
    Giữ issue có confidence cao nhất.
    """
    seen: dict[tuple[str, str | None], CandidateIssue] = {}
    for issue in issues:
        key = (issue.rule, issue.element)
        if key not in seen or issue.confidence > seen[key].confidence:
            seen[key] = issue
    return list(seen.values())


def run_rule_engine(doc: CanonicalDoc) -> CanonicalDoc:
    """
    Chạy tất cả rules R1–R4 trên CanonicalDoc.
    Bổ sung CandidateIssue[] vào doc.candidate_issues.
    Dedup trước khi trả về.

    Returns: CanonicalDoc mới với candidate_issues đầy đủ.
    """
    new_issues: list[CandidateIssue] = []

    # R1 — Geometry (thứ tự theo spec)
    new_issues.extend(check_offscreen(doc))
    new_issues.extend(check_safe_area(doc))
    new_issues.extend(check_overlap(doc))
    new_issues.extend(check_near_duplicate_position(doc))
    new_issues.extend(check_overflow(doc))
    new_issues.extend(check_touch_target(doc))
    new_issues.extend(check_tap_gap(doc))

    # R2 — Color/contrast
    new_issues.extend(check_contrast(doc))
    new_issues.extend(check_dark_mode(doc))
    new_issues.extend(check_opacity(doc))

    # R3 — Image
    new_issues.extend(check_blur(doc))
    new_issues.extend(check_icon_centering(doc))
    new_issues.extend(check_placeholder_icon(doc))
    new_issues.extend(check_hash_duplicates(doc))

    # R4 — Text
    new_issues.extend(check_placeholders(doc))
    new_issues.extend(check_i18n_keys(doc))
    new_issues.extend(check_lorem_ipsum(doc))
    new_issues.extend(check_debug_text(doc))
    new_issues.extend(check_mojibake(doc))
    new_issues.extend(check_escape_literals(doc))
    new_issues.extend(check_epoch(doc))
    new_issues.extend(check_stacktrace(doc))
    new_issues.extend(check_truncation(doc))
    new_issues.extend(check_font_size(doc))

    # Gộp với existing issues (từ analyzers A4, A9, A10, ...)
    all_issues = list(doc.candidate_issues) + new_issues

    # Dedup toàn bộ
    deduped = _deduplicate(all_issues)

    # Trả về doc mới (Pydantic v2: model_copy)
    return doc.model_copy(update={"candidate_issues": deduped})
