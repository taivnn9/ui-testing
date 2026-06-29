"""
R3 — Image Rules (ảnh + icon)

Tất định hoàn toàn (số học ratio + hash Hamming).
Nguồn: elements[].image_meta (từ A7), elements[] role=image/icon,
       output A6 (possible_placeholder), output A10 (hash duplicates).
"""
from __future__ import annotations

from ..schema.models import (
    CandidateIssue,
    CanonicalDoc,
    Evidence,
    SeverityRange,
)
from ..schema.thresholds import (
    ASPECT_ERROR,
    ASPECT_WARN,
    BLUR_CLEAR,
    BLUR_WARN,
    HASH_IDENTICAL,
)
from .r5_severity import apply_modifiers, clamp_confidence, get_position_modifier

_MIN_ELEM_CONFIDENCE: float = 0.35

# Roles cần check ảnh
_IMAGE_ROLES = {"image"}
_ICON_ROLES = {"icon"}
_PARENT_BUTTON_ROLES = {"button", "tab", "nav"}


def _visible(elem) -> bool:  # type: ignore[return]
    return elem.visible and elem.confidence >= _MIN_ELEM_CONFIDENCE


def _elem_map(doc: CanonicalDoc) -> dict:
    return {e.id: e for e in doc.elements}


# ---------------------------------------------------------------------------
# R3-IMG03 — Mờ / pixel hoá (Laplacian blur)
# ---------------------------------------------------------------------------

def check_blur(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R3-IMG03: blur_score < BLUR_WARN × dpr → ảnh mờ.
    Laplacian variance từ A7.image_meta.blur_score.
    """
    issues: list[CandidateIssue] = []
    dpr = doc.screen.viewport.dpr
    effective_thresh = BLUR_WARN * dpr
    high_thresh = BLUR_CLEAR * dpr / 2  # rất mờ → high

    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.role not in _IMAGE_ROLES | _ICON_ROLES:
            continue
        if elem.image_meta is None:
            continue

        blur_score = getattr(elem.image_meta, "blur_score", None)
        if blur_score is None:
            continue

        if blur_score >= effective_thresh:
            continue  # không mờ

        confidence = clamp_confidence(elem.confidence * 0.75)
        sev_range = SeverityRange(min="low", max="medium")
        modifiers: list[int] = []

        if blur_score < high_thresh:
            # Rất mờ → fire HIGH (vượt range max → clamp = medium)
            baseline = "medium"
            modifiers.append(+1)
        else:
            baseline = "medium"

        # Modifier theo vị trí
        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        # Ảnh sản phẩm / ảnh người → medium–high; background decorative → low–trivial
        if not elem.interactive and elem.z <= 1:
            modifiers.append(-1)

        sev = apply_modifiers(baseline, modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R3-IMG03",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=(
                    f"Ảnh mờ/pixel hoá: blur_score={blur_score:.1f} "
                    f"< {effective_thresh:.1f} (BLUR_WARN={BLUR_WARN}×dpr={dpr})"
                ),
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R3-IMG07 — Icon lệch tâm trong nút
# ---------------------------------------------------------------------------

def check_icon_centering(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R3-IMG07: icon center offset > 5% parent width (tối thiểu 3px).
    """
    issues: list[CandidateIssue] = []
    elems = _elem_map(doc)

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.role not in _ICON_ROLES:
            continue
        if not elem.parent:
            continue

        parent = elems.get(elem.parent)
        if parent is None or not _visible(parent):
            continue
        if parent.role not in _PARENT_BUTTON_ROLES:
            continue

        icon_cx = elem.bbox.x + elem.bbox.w / 2
        icon_cy = elem.bbox.y + elem.bbox.h / 2
        parent_cx = parent.bbox.x + parent.bbox.w / 2
        parent_cy = parent.bbox.y + parent.bbox.h / 2

        h_offset = abs(icon_cx - parent_cx)
        v_offset = abs(icon_cy - parent_cy)

        threshold = max(3.0, parent.bbox.w * 0.05)

        if h_offset <= threshold and v_offset <= threshold:
            continue

        confidence = clamp_confidence(
            min(elem.confidence, parent.confidence) * 0.7
        )

        sev_range = SeverityRange(min="trivial", max="medium")
        issues.append(
            CandidateIssue(
                rule="R3-IMG07",
                element=elem.id,
                severity="low",
                severity_range=sev_range,
                confidence=confidence,
                detail=(
                    f"Icon lệch tâm: h_offset={h_offset:.1f}px v_offset={v_offset:.1f}px "
                    f"> threshold={threshold:.1f}px (5% parent_w={parent.bbox.w:.1f})"
                ),
                evidence=Evidence(bbox=elem.bbox),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R3-IMG08 — Icon placeholder / chưa load
# ---------------------------------------------------------------------------

def check_placeholder_icon(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R3-IMG08: elements với possible_placeholder hint từ A6.
    Field: element.image_meta hay custom attribute possible_placeholder.
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem):
            continue

        # possible_placeholder có thể được A6 gắn vào image_meta hoặc extra attrs
        possible_placeholder: bool = False

        if elem.image_meta is not None:
            possible_placeholder = getattr(elem.image_meta, "possible_placeholder", False) or False

        # Fallback: check extra attributes nếu có
        if not possible_placeholder:
            possible_placeholder = getattr(elem, "possible_placeholder", False) or False

        if not possible_placeholder:
            continue

        confidence = clamp_confidence(elem.confidence * 0.7)

        sev_range = SeverityRange(min="low", max="high")
        modifiers: list[int] = []

        # Top-fold + ảnh sản phẩm/avatar → high
        pos_mod = get_position_modifier(elem.bbox, vp_h)
        modifiers.append(pos_mod)

        # Icon nhỏ, decorative → low
        if elem.role == "icon" and not elem.interactive:
            modifiers.append(-2)

        sev = apply_modifiers("medium", modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R3-IMG08",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail="Icon/ảnh placeholder chưa load (possible_placeholder=True từ A6)",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R3-IMG12 — Ảnh trùng lặp (hash duplicates)
# ---------------------------------------------------------------------------

def check_hash_duplicates(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R3-IMG12: Đọc candidate_issues đã emit bởi A10 (R3-IMG12 hoặc IMG-12),
    bổ sung context và severity nếu chưa có.
    Cũng xử lý trực tiếp nếu A10 ghi duplicate_pairs vào doc extras.
    """
    issues: list[CandidateIssue] = []

    # Kiểm tra nếu doc có duplicate_pairs từ A10 (có thể là attr extra)
    duplicate_pairs = getattr(doc, "duplicate_pairs", None) or []
    elems = _elem_map(doc)

    # Chỉ soi ảnh NỘI DUNG đủ lớn (banner/hero/thumbnail). Đồ hoạ nhỏ lặp lại là trang
    # trí chủ ý → FP. Ngưỡng cạnh tối thiểu scale theo dpr. (FP audit: dup thật ~38px.)
    _dpr = doc.screen.viewport.dpr or 1.0
    _dup_min_side = 56.0 * _dpr

    for pair in duplicate_pairs:
        # Pair expected: {"a": id_a, "b": id_b, "hamming": int}
        id_a = pair.get("a") or pair.get("elem_a")
        id_b = pair.get("b") or pair.get("elem_b")
        hamming = pair.get("hamming", 0)

        if not id_a or not id_b:
            continue

        elem_a = elems.get(id_a)
        elem_b = elems.get(id_b)
        if elem_a is None or elem_b is None:
            continue
        if not _visible(elem_a) or not _visible(elem_b):
            continue

        # Icon trùng icon = tái sử dụng CHỦ Ý (chevron, sao, nút lặp trong list…) →
        # gần như luôn là false-positive trên UI thật. Chỉ soi ảnh nội dung trùng
        # (banner/hero/thumbnail) — đó mới là lỗi copy nhầm. (FP audit: 66 FP/8 ảnh.)
        if elem_a.role == "icon" and elem_b.role == "icon":
            continue

        # Bỏ qua đồ hoạ nhỏ trùng nhau (cạnh < ngưỡng) — trang trí lặp chủ ý, không phải
        # lỗi copy nhầm. Chỉ giữ ảnh nội dung đủ lớn.
        a_small = min(elem_a.bbox.w, elem_a.bbox.h) < _dup_min_side
        b_small = min(elem_b.bbox.w, elem_b.bbox.h) < _dup_min_side
        if a_small or b_small:
            continue

        # Loại trừ trường hợp chủ ý: cùng parent list-row
        if elem_a.parent and elem_a.parent == elem_b.parent:
            # Có thể list thumbnail → confidence thấp
            list_confidence_factor = 0.3
            confidence = clamp_confidence(
                min(elem_a.confidence, elem_b.confidence) * (1 - hamming / 64) * list_confidence_factor
            )
        else:
            confidence = clamp_confidence(
                min(elem_a.confidence, elem_b.confidence) * (1 - hamming / 64)
            )

        is_identical = hamming <= HASH_IDENTICAL
        sev_range = SeverityRange(min="trivial", max="medium")

        modifiers: list[int] = []
        # Cả 2 là hero image / banner → medium
        if elem_a.role == "image" and elem_b.role == "image":
            modifiers.append(+1)
        # Icon trong list → trivial
        if elem_a.role == "icon" and elem_b.role == "icon":
            modifiers.append(-2)

        baseline = "low" if is_identical else "trivial"
        # hamming <= HASH_IDENTICAL → fire MEDIUM
        if is_identical:
            baseline = "low"
            modifiers.append(+1)

        sev = apply_modifiers(baseline, modifiers, sev_range)  # type: ignore[arg-type]

        issues.append(
            CandidateIssue(
                rule="R3-IMG12",
                element=id_a,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=(
                    f"Ảnh trùng lặp: {id_a} ↔ {id_b} hamming={hamming} "
                    f"({'identical' if is_identical else 'near-dup'})"
                ),
                evidence=Evidence(bbox=elem_a.bbox, crop=elem_a.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R3-IMG02 — Méo / sai tỉ lệ (displayed ratio ≠ intrinsic ratio)
# ---------------------------------------------------------------------------

def check_distortion(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R3-IMG02: lệch tỉ lệ render so với gốc > ASPECT_WARN → medium, > ASPECT_ERROR → high.
    deviation = |disp_ratio − intr_ratio| / intr_ratio   (F0.4 §5.1, tất định).
    """
    issues: list[CandidateIssue] = []
    vp_h = doc.screen.viewport.h

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.role not in _IMAGE_ROLES:
            continue
        im = elem.image_meta
        if im is None:
            continue
        iw, ih, dw, dh = im.intrinsic_w, im.intrinsic_h, im.displayed_w, im.displayed_h
        if not all(isinstance(v, (int, float)) and v for v in (iw, ih, dw, dh)):
            continue

        intr_ratio = iw / ih
        disp_ratio = dw / dh
        if intr_ratio <= 0:
            continue
        deviation = abs(disp_ratio - intr_ratio) / intr_ratio
        if deviation < ASPECT_WARN:
            continue

        sev_range = SeverityRange(min="low", max="high")
        baseline = "high" if deviation >= ASPECT_ERROR else "medium"
        modifiers: list[int] = [get_position_modifier(elem.bbox, vp_h)]
        if not elem.interactive and elem.z <= 1:
            modifiers.append(-1)
        sev = apply_modifiers(baseline, modifiers, sev_range)  # type: ignore[arg-type]
        confidence = clamp_confidence(
            elem.confidence * (0.85 if deviation >= ASPECT_ERROR else 0.7)
        )

        issues.append(
            CandidateIssue(
                rule="R3-IMG02",
                element=elem.id,
                severity=sev,
                severity_range=sev_range,
                confidence=confidence,
                detail=(
                    f"Méo tỉ lệ: hiển thị {dw}×{dh} (ratio {disp_ratio:.2f}) ≠ gốc "
                    f"{iw}×{ih} (ratio {intr_ratio:.2f}), lệch {deviation * 100:.0f}% "
                    f"> {ASPECT_WARN * 100:.0f}%"
                ),
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# R3-IMG09 — Scale-mode sai (stretch → méo)
# ---------------------------------------------------------------------------

def check_scale_mode(doc: CanonicalDoc) -> list[CandidateIssue]:
    """
    R3-IMG09: scale_mode='stretch' → ảnh không giữ tỉ lệ (signal-based, confidence thấp,
    agent xác nhận). Các mode fit/fill/none giữ tỉ lệ nên bỏ qua.
    """
    issues: list[CandidateIssue] = []

    for elem in doc.elements:
        if not _visible(elem):
            continue
        if elem.role not in _IMAGE_ROLES:
            continue
        im = elem.image_meta
        if im is None or im.scale_mode != "stretch":
            continue

        sev_range = SeverityRange(min="low", max="high")
        confidence = clamp_confidence(elem.confidence * 0.6)
        issues.append(
            CandidateIssue(
                rule="R3-IMG09",
                element=elem.id,
                severity="medium",
                severity_range=sev_range,
                confidence=confidence,
                detail="scale_mode='stretch' → ảnh có thể bị méo (nên dùng fit/fill để giữ tỉ lệ)",
                evidence=Evidence(bbox=elem.bbox, crop=elem.crop),
            )
        )

    return issues
