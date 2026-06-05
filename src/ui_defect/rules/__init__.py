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

import logging

from ..schema.models import CandidateIssue, CanonicalDoc

logger = logging.getLogger(__name__)


def _apply(issues: list[CandidateIssue], fn, doc: CanonicalDoc) -> list[CandidateIssue]:
    """Chạy 1 rule, log kết quả nếu có issue."""
    found = fn(doc)
    if found:
        logger.debug("  %-30s → %d candidate", fn.__name__, len(found))
    issues.extend(found)
    return issues
from .r1_geometry import (
    check_grid_alignment,
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
    check_distortion,
    check_hash_duplicates,
    check_icon_centering,
    check_placeholder_icon,
    check_scale_mode,
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
    n = len(doc.elements)
    logger.info("Rule engine: %d element, %d candidate trước đó", n, len(doc.candidate_issues))

    # R1 — Geometry
    logger.debug("R1 Geometry...")
    _apply(new_issues, check_offscreen, doc)
    _apply(new_issues, check_safe_area, doc)
    _apply(new_issues, check_overlap, doc)
    _apply(new_issues, check_near_duplicate_position, doc)
    _apply(new_issues, check_overflow, doc)
    _apply(new_issues, check_touch_target, doc)
    _apply(new_issues, check_tap_gap, doc)
    _apply(new_issues, check_grid_alignment, doc)
    logger.info("R1-Geometry: %d issue mới", len(new_issues))

    # R2 — Color/contrast
    before = len(new_issues)
    logger.debug("R2 Color/contrast...")
    _apply(new_issues, check_contrast, doc)
    _apply(new_issues, check_dark_mode, doc)
    _apply(new_issues, check_opacity, doc)
    logger.info("R2-Color: %d issue mới", len(new_issues) - before)

    # R3 — Image
    before = len(new_issues)
    logger.debug("R3 Image...")
    _apply(new_issues, check_blur, doc)
    _apply(new_issues, check_distortion, doc)
    _apply(new_issues, check_scale_mode, doc)
    _apply(new_issues, check_icon_centering, doc)
    _apply(new_issues, check_placeholder_icon, doc)
    _apply(new_issues, check_hash_duplicates, doc)
    logger.info("R3-Image: %d issue mới", len(new_issues) - before)

    # R4 — Text
    before = len(new_issues)
    logger.debug("R4 Text...")
    _apply(new_issues, check_placeholders, doc)
    _apply(new_issues, check_i18n_keys, doc)
    _apply(new_issues, check_lorem_ipsum, doc)
    _apply(new_issues, check_debug_text, doc)
    _apply(new_issues, check_mojibake, doc)
    _apply(new_issues, check_escape_literals, doc)
    _apply(new_issues, check_epoch, doc)
    _apply(new_issues, check_stacktrace, doc)
    _apply(new_issues, check_truncation, doc)
    _apply(new_issues, check_font_size, doc)
    logger.info("R4-Text: %d issue mới", len(new_issues) - before)

    # Gộp với existing issues (từ analyzers A4, A9, A10, ...)
    all_issues = list(doc.candidate_issues) + new_issues

    # Dedup toàn bộ
    deduped = _deduplicate(all_issues)
    logger.info("Rule engine xong: %d issue sau dedup (trước: %d)", len(deduped), len(all_issues))

    return doc.model_copy(update={"candidate_issues": deduped})
