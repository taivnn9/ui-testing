"""Test rule mới wire theo F0.4: R3-IMG02 (méo tỉ lệ), R3-IMG09 (scale-mode), R1-LAY04 (lệch grid),
và (2026-06-04) R1-ENV02/03, R3-IMG08, R3-IMG12 — sau khi nối field analyzer A13/A6/A10 vào schema."""
from __future__ import annotations

from ui_defect.analyzers.a6_icon_detector import IconRegion, icon_regions_to_elements
from ui_defect.rules.r1_geometry import check_grid_alignment, check_safe_area
from ui_defect.rules.r3_image import (
    check_distortion,
    check_hash_duplicates,
    check_placeholder_icon,
    check_scale_mode,
)
from ui_defect.schema.models import (
    BBox,
    CanonicalDoc,
    Element,
    Image,
    ImageMeta,
    SafeArea,
    Screen,
    Viewport,
)


def _doc(elements, dpr=2.0):
    screen = Screen(
        id="scr", platform="android",
        viewport=Viewport(w=800, h=1600, dpr=dpr),
        safe_area=SafeArea(top=0, bottom=0),
    )
    return CanonicalDoc(screen=screen, image=Image(full="x.png", w=800, h=1600), elements=elements)


def _img_elem(eid, x, y, w, h, *, iw=None, ih=None, dw=None, dh=None, scale=None):
    return Element(
        id=eid, role="image", source="vision", confidence=1.0,
        bbox=BBox(x=x, y=y, w=w, h=h), bbox_norm=BBox(x=0, y=0, w=0, h=0),
        image_meta=ImageMeta(intrinsic_w=iw, intrinsic_h=ih,
                             displayed_w=dw, displayed_h=dh, scale_mode=scale),
    )


# ── R3-IMG02 méo tỉ lệ ────────────────────────────────────────────────────────
def test_distortion_fires_when_ratio_off():
    # gốc 100x100 (1.0) hiển thị 200x100 (2.0) → lệch 100% > 15%
    el = _img_elem("e1", 10, 10, 200, 100, iw=100, ih=100, dw=200, dh=100)
    out = check_distortion(_doc([el]))
    assert len(out) == 1
    assert out[0].rule == "R3-IMG02"
    assert out[0].severity == "high"  # >= ASPECT_ERROR


def test_distortion_passes_when_ratio_ok():
    # gốc 100x100, hiển thị 50x50 (cùng ratio) → không méo
    el = _img_elem("e1", 10, 10, 50, 50, iw=100, ih=100, dw=50, dh=50)
    assert check_distortion(_doc([el])) == []


def test_distortion_skips_when_meta_missing():
    el = _img_elem("e1", 10, 10, 50, 50)  # không có intrinsic/displayed
    assert check_distortion(_doc([el])) == []


# ── R3-IMG09 scale-mode ───────────────────────────────────────────────────────
def test_scale_mode_fires_on_stretch():
    el = _img_elem("e1", 0, 0, 50, 50, scale="stretch")
    out = check_scale_mode(_doc([el]))
    assert len(out) == 1 and out[0].rule == "R3-IMG09"


def test_scale_mode_ignores_fit_fill():
    els = [_img_elem("e1", 0, 0, 50, 50, scale="fit"),
           _img_elem("e2", 0, 0, 50, 50, scale="fill")]
    assert check_scale_mode(_doc(els)) == []


# ── R1-LAY04 lệch grid (unit = 8 × dpr = 16px ở dpr=2) ────────────────────────
def test_grid_fires_when_off_grid():
    # x=20 → 20 % 16 = 4 (> tol 2, < 16-2=14) → lệch. Chỉ chạy trên toạ độ pixel-exact.
    el = Element(id="e1", role="button", source="pixel", confidence=1.0,
                 bbox=BBox(x=20, y=32, w=48, h=48), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    out = check_grid_alignment(_doc([el], dpr=2.0))
    assert len(out) == 1 and out[0].rule == "R1-LAY04"


def test_grid_skips_vision_source():
    # Toạ độ vision (CV) quá nhiễu → LAY-04 BỎ QUA dù lệch lưới (tránh FP hàng loạt).
    el = Element(id="e1", role="button", source="vision", confidence=1.0,
                 bbox=BBox(x=20, y=32, w=48, h=48), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    assert check_grid_alignment(_doc([el], dpr=2.0)) == []


def test_grid_passes_when_on_grid():
    # x=32, y=48 đều bội số 16 → bám lưới
    el = Element(id="e1", role="button", source="pixel", confidence=1.0,
                 bbox=BBox(x=32, y=48, w=48, h=48), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    assert check_grid_alignment(_doc([el], dpr=2.0)) == []


def test_grid_skips_container_role():
    el = Element(id="e1", role="container", source="pixel", confidence=1.0,
                 bbox=BBox(x=20, y=20, w=100, h=100), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    assert check_grid_alignment(_doc([el], dpr=2.0)) == []


# ── R1-ENV02 status bar overlap (Screen.status_bar_h từ A13) ──────────────────
def _text_elem(eid, x, y, w, h, role="text"):
    return Element(id=eid, role=role, source="vision", confidence=1.0,
                   bbox=BBox(x=x, y=y, w=w, h=h), bbox_norm=BBox(x=0, y=0, w=0, h=0))


def test_env02_fires_when_content_crosses_status_bar():
    # Nội dung app vắt qua status bar (đáy 200 >> bar 72 → chỉ phần nhỏ bị che) → lỗi thật.
    el = _text_elem("e1", 0, 0, 200, 200)  # overlap 72/200=0.36 < 0.6 → KHÔNG phải system strip
    d = _doc([el])
    d.screen.status_bar_h = 72.0
    out = [i for i in check_safe_area(d) if i.rule == "R1-ENV02"]
    assert len(out) == 1 and out[0].element == "e1"


def test_env02_fires_for_interactive_in_status_bar():
    # Button app nằm gọn trong status bar → vẫn lỗi (interactive không bị coi là system strip).
    el = _text_elem("e1", 0, 0, 200, 40, role="button")
    el.interactive = True
    d = _doc([el])
    d.screen.status_bar_h = 72.0
    out = [i for i in check_safe_area(d) if i.rule == "R1-ENV02"]
    assert len(out) == 1 and out[0].element == "e1"


def test_env02_skips_system_status_bar_icon():
    # Icon hệ thống (giờ/sóng/pin) nằm gọn trong status bar, không tương tác → BỎ (tránh FP).
    el = _text_elem("e1", 980, 4, 40, 40, role="icon")  # overlap ~1.0 >= 0.6
    d = _doc([el])
    d.screen.status_bar_h = 72.0
    out = [i for i in check_safe_area(d) if i.rule == "R1-ENV02"]
    assert out == []


def test_env02_silent_when_status_bar_h_zero():
    el = _text_elem("e1", 0, 0, 200, 40)
    assert [i for i in check_safe_area(_doc([el])) if i.rule == "R1-ENV02"] == []


# ── R1-ENV03 home indicator overlap (iOS, Screen.nav_bar_h từ A13) ────────────
def test_env03_fires_on_ios_home_indicator():
    screen = Screen(id="scr", platform="ios",
                    viewport=Viewport(w=390, h=844, dpr=1.0),
                    safe_area=SafeArea(top=0, bottom=0), nav_bar_h=34.0)
    el = _text_elem("e1", 48, 784, 296, 56, role="button")  # bottom=840 > (844-34)+4
    d = CanonicalDoc(screen=screen, image=Image(full="x.png", w=390, h=844), elements=[el])
    out = [i for i in check_safe_area(d) if i.rule == "R1-ENV03"]
    assert len(out) == 1 and out[0].element == "e1"


# ── R3-IMG08 placeholder (ImageMeta.possible_placeholder từ A6) ───────────────
def test_img08_fires_when_possible_placeholder():
    el = _img_elem("e1", 10, 10, 80, 80)
    el.image_meta.possible_placeholder = True
    out = check_placeholder_icon(_doc([el]))
    assert len(out) == 1 and out[0].rule == "R3-IMG08" and out[0].element == "e1"


def test_a6_conversion_propagates_placeholder_to_image_meta():
    region = IconRegion(id="i1", bbox=BBox(x=0, y=0, w=40, h=40),
                        bbox_norm=BBox(x=0, y=0, w=0, h=0), subtype="icon",
                        confidence=0.8, color_count_approx=2, edge_density=0.1,
                        template_match=None, possible_placeholder=True)
    [el] = icon_regions_to_elements([region], 800, 1600)
    assert el.image_meta is not None and el.image_meta.possible_placeholder is True


# ── R3-IMG12 duplicate images (CanonicalDoc.duplicate_pairs từ A10) ───────────
def test_img12_fires_from_duplicate_pairs():
    # Ảnh nội dung đủ lớn (>= 56*dpr) → trùng nhau là lỗi copy nhầm thật.
    a = _img_elem("e1", 16, 72, 160, 160)
    b = _img_elem("e2", 16, 320, 160, 160)
    d = _doc([a, b])
    d.duplicate_pairs = [{"a": "e1", "b": "e2", "hamming": 2}]
    out = check_hash_duplicates(d)
    assert len(out) == 1 and out[0].rule == "R3-IMG12" and out[0].element == "e1"


def test_img12_skips_small_duplicate_graphics():
    # Đồ hoạ nhỏ trùng nhau (< 56*dpr) = trang trí chủ ý → KHÔNG fire (tránh FP).
    a = _img_elem("e1", 16, 72, 40, 40)
    b = _img_elem("e2", 16, 320, 40, 40)
    d = _doc([a, b])
    d.duplicate_pairs = [{"a": "e1", "b": "e2", "hamming": 2}]
    assert check_hash_duplicates(d) == []


def test_img12_skips_icon_pairs():
    # Icon trùng icon = tái sử dụng chủ ý → KHÔNG fire.
    a = _img_elem("e1", 16, 72, 160, 160); a.role = "icon"
    b = _img_elem("e2", 16, 320, 160, 160); b.role = "icon"
    d = _doc([a, b])
    d.duplicate_pairs = [{"a": "e1", "b": "e2", "hamming": 0}]
    assert check_hash_duplicates(d) == []
