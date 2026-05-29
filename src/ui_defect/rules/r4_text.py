"""
R4 — Text Rules (placeholder + typography tất định)

Nguồn: elements[].text (từ A5 OCR), elements[].style.font_size, elements[].text_truncated.
Toàn bộ là regex/pattern matching tất định — không cần LLM.
"""
from __future__ import annotations

from ..schema.models import (
    CandidateIssue,
    CanonicalDoc,
    Evidence,
    SeverityRange,
)
from ..schema.thresholds import FONT_MIN_PX, FONT_WARN_PX
from .patterns import (
    DEBUG_WORDS,
    EPOCH_PATTERNS,
    ESCAPE_PATTERNS,
    I18N_KEY_PATTERNS,
    LOREM_IPSUM_PHRASES,
    MOJIBAKE_PATTERNS,
    PLACEHOLDER_PATTERNS,
    STACKTRACE_PATTERNS,
    match_any,
    match_debug_patterns,
    match_dict,
)
from .r5_severity import apply_modifiers, clamp_confidence, get_position_modifier

_MIN_ELEM_CONFIDENCE: float = 0.35

# Roles mang text nội dung
_TEXT_ROLES = {"text", "button", "input", "tab", "nav", "container"}
# Roles bỏ qua check text (code context)
_CODE_ROLES: set[str] = set()


def _visible(elem) -> bool:  # type: ignore[return]
    return elem.visible and elem.confidence >= _MIN_ELEM_CONFIDENCE


def _has_text(elem) -> bool:
    return elem.text is not None and elem.text.strip() != ""


# ---------------------------------------------------------------------------
# R4-CNT01 — Placeholder / biến chưa render
# ---------------------------------------------------------------------------

def check_placeholders(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT01: regex match placeholder patterns trong element.text.
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue
        if elem.role not in _TEXT_ROLES:
            continue

        text = elem.text  # type: ignore[union-attr]
        matches = match_any(text, PLACEHOLDER_PATTERNS)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.92)
        sev_range = SeverityRange(min="medium", max="critical")
        modifiers: list[int] = []

        if elem.role in {"button", "nav"}:
            modifiers.append(+1)
        elif elem.role == "input":
            # input placeholder attribute hợp lệ → giảm severity
            modifiers.append(-1)

        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        sev = apply_modifiers("high", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-CNT01",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Placeholder/biến chưa render: {matches[:3]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-CNT02 — i18n key lòi ra
# ---------------------------------------------------------------------------

def check_i18n_keys(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT02: i18n key patterns (dot-notation, SCREAMING_SNAKE).
    Confidence thấp — nhiều false positive, cần VLM G1 confirm.
    """
    issues: list[CandidateIssue] = []

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue
        if elem.role not in _TEXT_ROLES:
            continue

        text = elem.text.strip()  # type: ignore[union-attr]

        # Điều kiện: text ngắn (<40 ký tự), không có space nhiều, không phải URL/email
        if len(text) >= 40:
            continue
        if "/" in text or "@" in text:
            continue
        # Không fire nếu text có nhiều space (là câu văn thật)
        if text.count(" ") >= 2:
            continue

        matches = match_any(text, I18N_KEY_PATTERNS)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.75)
        sev_range = SeverityRange(min="medium", max="critical")

        issues.append(
            CandidateIssue(
                rule="R4-CNT02",
                element=elem.id,
                severity="high",
                severity_range=sev_range,
                confidence=confidence,
                detail=f"i18n key chưa dịch: '{text}' khớp pattern {matches[:2]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-CNT04 — Lorem ipsum / placeholder copy
# ---------------------------------------------------------------------------

def check_lorem_ipsum(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT04: dictionary match các lorem ipsum phrases.
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue

        text = elem.text  # type: ignore[union-attr]
        matches = match_dict(text, LOREM_IPSUM_PHRASES)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.95)
        sev_range = SeverityRange(min="medium", max="high")
        modifiers: list[int] = []

        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        sev = apply_modifiers("high", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-CNT04",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Lorem ipsum / placeholder copy: {matches[:2]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-CNT05 — Text debug / nội bộ
# ---------------------------------------------------------------------------

def check_debug_text(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT05: dictionary match + regex debug patterns.
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue

        text = elem.text  # type: ignore[union-attr]
        dict_matches = match_dict(text, DEBUG_WORDS)
        regex_matches = match_debug_patterns(text)
        matches = dict_matches + regex_matches

        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.85)
        sev_range = SeverityRange(min="medium", max="critical")
        modifiers: list[int] = []

        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        sev = apply_modifiers("high", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-CNT05",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Text debug/nội bộ: {matches[:3]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-CNT06 — Mojibake / HTML entity thô
# ---------------------------------------------------------------------------

def check_mojibake(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT06: mojibake patterns, HTML entities thô, invisible chars.
    """
    issues: list[CandidateIssue] = []

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue

        text = elem.text  # type: ignore[union-attr]
        matches = match_any(text, MOJIBAKE_PATTERNS)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.9)
        sev_range = SeverityRange(min="low", max="high")
        modifiers: list[int] = []

        if elem.role in {"button", "nav", "text"}:
            modifiers.append(+1)

        sev = apply_modifiers("medium", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-CNT06",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Mojibake / HTML entity thô: {matches[:3]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-CNT07 — Escape literal
# ---------------------------------------------------------------------------

def check_escape_literals(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT07: escape sequences thô (\\n, \\t, <br>, &lt;, &gt;) như text thật.
    """
    issues: list[CandidateIssue] = []

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue

        text = elem.text  # type: ignore[union-attr]
        matches = match_any(text, ESCAPE_PATTERNS)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.88)
        sev_range = SeverityRange(min="low", max="high")

        issues.append(
            CandidateIssue(
                rule="R4-CNT07",
                element=elem.id,
                severity="medium",
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Escape literal trong text: {matches[:3]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-CNT08 — Epoch / format số sai
# ---------------------------------------------------------------------------

def check_epoch(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-CNT08: epoch timestamp (10–13 digit), ISO date thô trong UI.
    """
    issues: list[CandidateIssue] = []

    _SKIP_ROLES = {"code"}

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue
        if elem.role in _SKIP_ROLES:
            continue

        text = elem.text  # type: ignore[union-attr]
        matches = match_any(text, EPOCH_PATTERNS)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.7)
        sev_range = SeverityRange(min="low", max="high")

        issues.append(
            CandidateIssue(
                rule="R4-CNT08",
                element=elem.id,
                severity="medium",
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Epoch/số thô không định dạng: {matches[:3]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-STATE03 — Stack trace / raw error
# ---------------------------------------------------------------------------

def check_stacktrace(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-STATE03: stack trace hoặc raw error message trong text.
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem) or not _has_text(elem):
            continue

        text = elem.text  # type: ignore[union-attr]
        matches = match_any(text, STACKTRACE_PATTERNS)
        if not matches:
            continue

        confidence = clamp_confidence(elem.confidence * 0.9)
        sev_range = SeverityRange(min="medium", max="critical")
        modifiers: list[int] = []

        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        sev = apply_modifiers("high", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-STATE03",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=f"Stack trace / raw error lộ ra UI: {matches[:3]}",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-TYP03 — Text cắt cụt (unintended truncation)
# ---------------------------------------------------------------------------

def check_truncation(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-TYP03: text_truncated=True mà không có ellipsis chủ ý.
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    _ELLIPSIS_INDICATORS = ("…", "...", " more", "more")

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if not elem.text_truncated:
            continue

        text = elem.text or ""

        has_ellipsis = any(text.rstrip().endswith(ind) for ind in _ELLIPSIS_INDICATORS)

        if has_ellipsis:
            # Có ellipsis → có thể chủ ý → confidence thấp
            confidence = clamp_confidence(elem.confidence * 0.4)
            detail = "Text bị cắt có ellipsis — có thể chủ ý; VLM xác nhận"
        else:
            # Bị cắt không có ellipsis → lỗi rõ
            confidence = clamp_confidence(elem.confidence * 0.8)
            detail = "Text bị cắt cụt không có ellipsis"

        sev_range = SeverityRange(min="trivial", max="critical")
        modifiers: list[int] = []

        if elem.role in {"button"}:
            modifiers.append(+2)
        elif not has_ellipsis:
            modifiers.append(+1)

        # Phủ định / số tiền trong text
        neg_words = ("không", "cancel", "từ chối", "hủy")
        if text and any(w in text.lower() for w in neg_words):
            modifiers.append(+2)

        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        # role body text có ellipsis → giảm
        if elem.role == "text" and has_ellipsis:
            modifiers.append(-2)

        sev = apply_modifiers("medium", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-TYP03",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=detail,
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R4-TYP05 — Cỡ chữ quá nhỏ
# ---------------------------------------------------------------------------

def check_font_size(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R4-TYP05: style.font_size_px < FONT_MIN_PX (11px) → high;
              < FONT_WARN_PX (13px) → medium.
    """
    issues: list[CandidateIssue] = []
    font_scale = doc.screen.font_scale

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.style is None:
            continue

        font_size = elem.style.font_size
        if font_size is None:
            continue

        # Nếu font_scale > 1 (trợ năng), tính font trước scale
        effective_size = font_size / font_scale if font_scale > 1.0 else font_size

        if effective_size >= FONT_WARN_PX:
            continue  # không nhỏ

        confidence = clamp_confidence(elem.confidence * 0.75)
        sev_range = SeverityRange(min="low", max="high")

        if effective_size < FONT_MIN_PX:
            baseline = "high"
            detail = f"Cỡ chữ quá nhỏ: {effective_size:.1f}px < {FONT_MIN_PX}px (critical threshold)"
        else:
            baseline = "medium"
            detail = f"Cỡ chữ nhỏ: {effective_size:.1f}px < {FONT_WARN_PX}px (warn threshold)"

        modifiers: list[int] = []
        if elem.role in {"text", "button"}:
            modifiers.append(+1)
        # copyright/footnote → low
        if elem.role == "text" and effective_size < FONT_MIN_PX and elem.z <= 0:
            modifiers.append(-1)

        # font_scale trợ năng → +1 cho tất cả TYP rule
        if font_scale >= 1.3:
            modifiers.append(+1)

        sev = apply_modifiers(baseline, modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R4-TYP05",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=detail,
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues
