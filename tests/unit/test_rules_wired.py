"""Test 3 rule mới wire theo F0.4: R3-IMG02 (méo tỉ lệ), R3-IMG09 (scale-mode), R1-LAY04 (lệch grid)."""
from __future__ import annotations

from ui_defect.rules.r1_geometry import check_grid_alignment
from ui_defect.rules.r3_image import check_distortion, check_scale_mode
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
    # x=20 → 20 % 16 = 4 (> tol 2, < 16-2=14) → lệch
    el = Element(id="e1", role="button", source="vision", confidence=1.0,
                 bbox=BBox(x=20, y=32, w=48, h=48), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    out = check_grid_alignment(_doc([el], dpr=2.0))
    assert len(out) == 1 and out[0].rule == "R1-LAY04"


def test_grid_passes_when_on_grid():
    # x=32, y=48 đều bội số 16 → bám lưới
    el = Element(id="e1", role="button", source="vision", confidence=1.0,
                 bbox=BBox(x=32, y=48, w=48, h=48), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    assert check_grid_alignment(_doc([el], dpr=2.0)) == []


def test_grid_skips_container_role():
    el = Element(id="e1", role="container", source="vision", confidence=1.0,
                 bbox=BBox(x=20, y=20, w=100, h=100), bbox_norm=BBox(x=0, y=0, w=0, h=0))
    assert check_grid_alignment(_doc([el], dpr=2.0)) == []
