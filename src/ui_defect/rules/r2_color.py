"""
R2 — Color Rules (màu sắc + contrast)

Nguồn: elements[].style.* — đo từ pixel bởi A4.
Dedup logic: skip nếu (rule_prefix, element_id) đã tồn tại trong doc.candidate_issues.
"""
from __future__ import annotations

from ..schema.models import (
    CandidateIssue,
    CanonicalDoc,
    Evidence,
    SeverityRange,
)
from ..schema.thresholds import (
    CONTRAST_INVISIBLE,
    CONTRAST_TEXT_LARGE,
    CONTRAST_TEXT_NORMAL,
    CONTRAST_UI,
)
from .r5_severity import apply_modifiers, clamp_confidence

_MIN_ELEM_CONFIDENCE: float = 0.35

# Nhóm role có text cần kiểm tra contrast
_TEXT_ROLES = {"text", "button", "input", "tab", "nav"}
# Ngưỡng px font size "chữ lớn" (18pt ở dpr=1 = 18px; cần nhân với dpr ở thời điểm check)
_LARGE_FONT_PT = 18.0
_LARGE_FONT_BOLD_PT = 14.0


def _visible(elem) -> bool:  # type: ignore[return]
    return elem.visible and elem.confidence >= _MIN_ELEM_CONFIDENCE


def _existing_rules(doc: CanonicalDoc) -> set[tuple[str, str]]:
    """
    Trả về set (rule, element_id) đã có trong doc.candidate_issues.
    Dùng để dedup — bao gồm cả rule từ A4 (vd: 'STY-01_contrast').
    """
    result: set[tuple[str, str]] = set()
    for issue in doc.candidate_issues:
        if issue.element:
            result.add((issue.rule, issue.element))
    return result


def _rule_elem_exists(existing: set[tuple[str, str]], rule_prefix: str, elem_id: str) -> bool:
    """
    Kiểm tra element đã có issue với rule_prefix trong existing set.
    So khớp bằng startswith để bắt cả 'R2-STY01' lẫn 'STY-01_contrast' từ A4.
    """
    for r, e in existing:
        if e == elem_id and (r.startswith(rule_prefix) or r == rule_prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# R2-STY01 — Contrast chữ/nền thấp
# ---------------------------------------------------------------------------

def check_contrast(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R2-STY01: contrast < 4.5 (text thường) hoặc < 3.0 (chữ lớn).
    R2-STY02: contrast < 1.5 → chữ tàng hình (critical).
    R2-STY04: icon contrast < 3.0 trong dark mode.
    R2-STY13: icon/đồ hoạ chức năng contrast < 3.0.
    """
    issues: list[CandidateIssue] = []
    existing = _existing_rules(doc)
    dpr = doc.screen.viewport.dpr
    theme = doc.screen.theme
    font_scale = doc.screen.font_scale

    large_font_threshold_px = _LARGE_FONT_PT * dpr
    large_font_bold_px = _LARGE_FONT_BOLD_PT * dpr

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.style is None:
            continue

        cr = elem.style.contrast_ratio
        if cr is None:
            continue  # A4 không tách được fg/bg → skip, để VLM G3

        # --- R2-STY02: chữ tàng hình (invisible) ---
        if elem.role in _TEXT_ROLES and cr < CONTRAST_INVISIBLE:
            rule = "R2-STY02"
            if not _rule_elem_exists(existing, rule, elem.id):
                confidence = clamp_confidence(elem.confidence * 0.95)
                sev_range = SeverityRange(min="high", max="critical")
                modifiers = [+1] if elem.role in {"button", "nav"} else []
                sev = apply_modifiers("critical", modifiers, sev_range)  # type: ignore[arg-type]
                issues.append(
                    CandidateIssue(
                        rule=rule,
                        element=elem.id,
                        severity=sev,
                        severity_range=sev_range,
                        confidence=confidence,
                        detail=f"Chữ tàng hình: contrast_ratio={cr:.2f} < {CONTRAST_INVISIBLE}",
                        evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
                    )
                )
            continue  # STY-02 bao phủ STY-01 với cr cực thấp

        # --- R2-STY01: contrast thấp cho text ---
        if elem.role in _TEXT_ROLES:
            rule = "R2-STY01"
            if not _rule_elem_exists(existing, "STY-01", elem.id) and not _rule_elem_exists(existing, rule, elem.id):
                font_size = elem.style.font_size
                is_large = False
                if font_size is not None:
                    effective_size = font_size / font_scale if font_scale > 1.0 else font_size
                    is_large = (
                        effective_size >= large_font_threshold_px
                        or effective_size >= large_font_bold_px
                    )

                threshold = CONTRAST_TEXT_LARGE if is_large else CONTRAST_TEXT_NORMAL

                # font_scale trợ năng ≥ 1.3 → hạ ngưỡng xuống CONTRAST_TEXT_LARGE
                if font_scale >= 1.3:
                    threshold = min(threshold, CONTRAST_TEXT_LARGE)

                if cr < threshold:
                    confidence = clamp_confidence(elem.confidence * 0.9)
                    sev_range = SeverityRange(min="medium", max="high")
                    modifiers: list[int] = []
                    if elem.role in {"button", "nav"}:
                        modifiers.append(+1)
                    sev = apply_modifiers("high", modifiers, sev_range)  # type: ignore[arg-type]
                    detail = (
                        f"Contrast thấp: {cr:.2f} < {threshold} "
                        f"({'chữ lớn' if is_large else 'chữ thường'})"
                    )
                    issues.append(
                        CandidateIssue(
                            rule=rule,
                            element=elem.id,
                            severity=sev,
                            severity_range=sev_range,
                            confidence=confidence,
                            detail=detail,
                            evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
                        )
                    )

        # --- R2-STY04: icon tàng hình trong dark mode ---
        if elem.role == "icon" and theme == "dark":
            rule = "R2-STY04"
            if not _rule_elem_exists(existing, rule, elem.id):
                if cr < CONTRAST_UI:
                    confidence = clamp_confidence(elem.confidence * 0.8)
                    sev_range = SeverityRange(min="medium", max="critical")
                    sev = apply_modifiers("high", [], sev_range)  # type: ignore[arg-type]
                    issues.append(
                        CandidateIssue(
                            rule=rule,
                            element=elem.id,
                            severity=sev,
                            severity_range=sev_range,
                            confidence=confidence,
                            detail=f"Icon tàng hình dark mode: contrast={cr:.2f} < {CONTRAST_UI} (UI threshold)",
                            evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
                        )
                    )

        # --- R2-STY13: icon/đồ hoạ chức năng contrast < 3:1 ---
        if elem.role == "icon" and elem.interactive:
            rule = "R2-STY13"
            if not _rule_elem_exists(existing, rule, elem.id):
                if cr < CONTRAST_UI:
                    confidence = clamp_confidence(elem.confidence * 0.8)
                    sev_range = SeverityRange(min="low", max="high")
                    modifiers_icon: list[int] = []
                    # nav icon, primary action → high
                    # decorative (already skipped — interactive=True here)
                    sev = apply_modifiers("medium", modifiers_icon, sev_range)  # type: ignore[arg-type]
                    issues.append(
                        CandidateIssue(
                            rule=rule,
                            element=elem.id,
                            severity=sev,
                            severity_range=sev_range,
                            confidence=confidence,
                            detail=f"Icon chức năng contrast thấp: {cr:.2f} < {CONTRAST_UI}",
                            evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
                        )
                    )

    return issues


# ---------------------------------------------------------------------------
# R2-STY03 — Dark-mode không đổi màu
# ---------------------------------------------------------------------------

def check_dark_mode(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R2-STY03: dark_mode_ok=False khi theme=dark → element hardcode màu sáng.
    """
    issues: list[CandidateIssue] = []

    if doc.screen.theme != "dark":
        return issues

    existing = _existing_rules(doc)

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.style is None:
            continue

        # dark_mode_ok là field tùy chọn từ A4
        dark_mode_ok = getattr(elem.style, "dark_mode_ok", None)
        if dark_mode_ok is None:
            continue  # A4 chưa emit flag này
        if dark_mode_ok:
            continue  # OK

        rule = "R2-STY03"
        if _rule_elem_exists(existing, rule, elem.id):
            continue

        confidence = clamp_confidence(elem.confidence * 0.75)
        sev_range = SeverityRange(min="medium", max="critical")
        modifiers: list[int] = []
        if elem.role in {"button", "input", "nav"}:
            modifiers.append(+1)
        elif elem.role in {"image"} and not elem.interactive:
            modifiers.append(-1)

        sev = apply_modifiers("high", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule=rule,
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail="Dark-mode: element hardcode màu sáng (dark_mode_ok=False)",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R2-STY05 — Opacity sai (gần trong suốt)
# ---------------------------------------------------------------------------

def check_opacity(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R2-STY05: opacity_px < 0.15 → gần như vô hình; 0.15–0.35 → nghi mờ bất thường.
    """
    issues: list[CandidateIssue] = []
    existing = _existing_rules(doc)

    _OPACITY_CRITICAL = 0.15
    _OPACITY_WARN = 0.35

    _SKIP_ROLES = {"skeleton", "spinner"}
    _IMPORTANT_ROLES = {"button", "input"}

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.style is None:
            continue

        # opacity từ style — A4 đo từ pixel
        opacity = elem.style.opacity
        if opacity is None or opacity >= _OPACITY_WARN:
            continue

        # Skeleton/spinner mờ chủ ý → skip
        if elem.role in _SKIP_ROLES:
            continue

        rule = "R2-STY05"
        if _rule_elem_exists(existing, rule, elem.id):
            continue

        is_nearly_invisible = opacity < _OPACITY_CRITICAL
        rule_factor = 0.7

        confidence = clamp_confidence(elem.confidence * rule_factor)

        sev_range = SeverityRange(min="low", max="high")
        baseline = "medium"
        modifiers: list[int] = []

        if is_nearly_invisible:
            modifiers.append(+1)
        if elem.role in _IMPORTANT_ROLES:
            modifiers.append(+1)

        sev = apply_modifiers(baseline, modifiers, sev_range)  # type: ignore[arg-type]

        detail = (
            f"Opacity bất thường: {opacity:.2f} "
            f"({'< ' + str(_OPACITY_CRITICAL) + ' → gần như vô hình' if is_nearly_invisible else 'trong [0.15, 0.35] → nghi mờ'})"
        )

        issues.append(
            CandidateIssue(
                rule=rule,
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=detail,
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues
