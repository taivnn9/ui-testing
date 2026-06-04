#!/usr/bin/env python3
"""
Agent A — Generator cho Standard Set Tier-1 (schema-level mutation testing).

Sinh:
  data/standard_v1/schema/base/<base>.json    — CanonicalDoc SẠCH (0 issue)
  data/standard_v1/schema/cases/<case>.json    — CanonicalDoc đã mutate (input rule engine)
  data/standard_v1/schema/labels/<case>.json   — ground truth (kỳ vọng)
  data/standard_v1/images/README.md            — TODO Tier-2

Quy tắc:
  - KHÔNG gọi agent/LLM/OCR/ảnh. Thuần dựng JSON từ Pydantic models.
  - Idempotent: ghi đè sạch mỗi lần chạy.
  - Tự kiểm bằng run_rule_engine sau khi sinh: positive PHẢI fire đúng (rule, element),
    negative PHẢI sạch.

CLI: python scripts/gen_standard.py [--out data/standard_v1/schema]

Spec: docs/F4.0-standard-set.md (§3 schema khóa chặt, §4 việc của Agent A).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Callable

# Cho phép chạy trực tiếp: thêm src/ vào path
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from ui_defect.rules import run_rule_engine  # noqa: E402
from ui_defect.schema.models import (  # noqa: E402
    BBox,
    CanonicalDoc,
    Element,
    Image,
    ImageMeta,
    Relation,
    SafeArea,
    Screen,
    Style,
    StyleSources,
    TouchTarget,
    Viewport,
)

# ---------------------------------------------------------------------------
# Helpers dựng element/doc sạch
# ---------------------------------------------------------------------------

# Grid unit logic = 8. Dùng dpr=1 cho mobile/web để toạ độ là bội số của 8 → bám lưới.
# (R1-LAY04 chỉ fire khi cạnh trái/trên lệch lưới 8×dpr quá 2px.)


def _norm(bbox: BBox, w: int, h: int) -> BBox:
    return BBox(x=bbox.x / w, y=bbox.y / h, w=bbox.w / w, h=bbox.h / h)


def make_element(
    vp_w: int,
    vp_h: int,
    *,
    id: str,
    role: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str | None = None,
    interactive: bool = False,
    touch_target: tuple[float, float] | None = None,
    contrast_ratio: float | None = 7.0,
    font_size: float | None = 16.0,
    opacity: float = 1.0,
    parent: str | None = None,
    children: list[str] | None = None,
    z: int = 0,
    image_meta: ImageMeta | None = None,
    text_truncated: bool = False,
    confidence: float = 0.95,
    color: str = "#111111",
    bg_color: str = "#FFFFFF",
    dark_mode_ok: bool | None = None,
) -> Element:
    """Dựng 1 element. Mặc định cho ra element SẠCH (không trip rule nào)."""
    bbox = BBox(x=x, y=y, w=w, h=h)
    style = Style(
        font_size=font_size,
        font_family="System",
        color=color,
        bg_color=bg_color,
        contrast_ratio=contrast_ratio,
        opacity=opacity,
        border_radius=4.0,
        dark_mode_ok=dark_mode_ok,
        _sources=StyleSources(contrast_ratio="pixel"),
    )
    tt = None
    if interactive:
        if touch_target is not None:
            tt = TouchTarget(w=touch_target[0], h=touch_target[1])
        else:
            tt = TouchTarget(w=w, h=h)
    return Element(
        id=id,
        role=role,  # type: ignore[arg-type]
        source="vision",
        confidence=confidence,
        bbox=bbox,
        bbox_norm=_norm(bbox, vp_w, vp_h),
        parent=parent,
        children=children or [],
        z=z,
        text=text,
        text_truncated=text_truncated,
        style=style,
        image_meta=image_meta,
        interactive=interactive,
        interactive_confidence=0.9 if interactive else 0.0,
        touch_target=tt,
        visible=True,
    )


def make_doc(
    *,
    screen_id: str,
    platform: str,
    vp_w: int,
    vp_h: int,
    dpr: float,
    elements: list[Element],
    relations: list[Relation] | None = None,
    safe_area: SafeArea | None = None,
    theme: str = "light",
    font_scale: float = 1.0,
    route: str | None = None,
) -> CanonicalDoc:
    screen = Screen(
        id=screen_id,
        platform=platform,  # type: ignore[arg-type]
        route=route,
        viewport=Viewport(w=vp_w, h=vp_h, dpr=dpr),
        safe_area=safe_area or SafeArea(),
        theme=theme,  # type: ignore[arg-type]
        font_scale=font_scale,
    )
    return CanonicalDoc(
        screen=screen,
        image=Image(full=f"{screen_id}.png", w=vp_w, h=vp_h),
        elements=elements,
        relations=relations or [],
        candidate_issues=[],
    )


# ---------------------------------------------------------------------------
# 6 base doc SẠCH
# ---------------------------------------------------------------------------
# Tất cả toạ độ là bội số của 8 (dpr=1 → grid unit=8) để không trip R1-LAY04.
# Text tránh các pattern R4 (không lowercase-word đơn ≥4 ký tự, không số ≥7 chữ số,
# không null/undefined/NaN/None, không HTTP 4xx/5xx standalone).


def base_mobile_login() -> CanonicalDoc:
    vp_w, vp_h = 360, 800
    els = [
        make_element(vp_w, vp_h, id="e1", role="container", x=0, y=0, w=360, h=800,
                     text=None, contrast_ratio=None, font_size=None),
        make_element(vp_w, vp_h, id="e2", role="image", x=128, y=80, w=104, h=104,
                     contrast_ratio=None, font_size=None, parent="e1",
                     image_meta=ImageMeta(intrinsic_w=200, intrinsic_h=200,
                                          displayed_w=104, displayed_h=104,
                                          scale_mode="fit")),
        make_element(vp_w, vp_h, id="e3", role="text", x=96, y=216, w=168, h=32,
                     text="Welcome back", font_size=22.0, parent="e1"),
        make_element(vp_w, vp_h, id="e4", role="input", x=32, y=304, w=296, h=56,
                     text="Email address", interactive=True, parent="e1"),
        make_element(vp_w, vp_h, id="e5", role="input", x=32, y=376, w=296, h=56,
                     text="Secret code", interactive=True, parent="e1"),
        make_element(vp_w, vp_h, id="e6", role="button", x=32, y=456, w=296, h=56,
                     text="Sign in now", interactive=True, parent="e1",
                     color="#FFFFFF", bg_color="#1565C0"),
        make_element(vp_w, vp_h, id="e7", role="text", x=104, y=536, w=152, h=24,
                     text="Reset access?", font_size=14.0, parent="e1"),
    ]
    return make_doc(screen_id="mobile_login", platform="android",
                    vp_w=vp_w, vp_h=vp_h, dpr=1.0, elements=els, route="/login")


def base_mobile_feed() -> CanonicalDoc:
    vp_w, vp_h = 360, 800
    els = [
        make_element(vp_w, vp_h, id="e1", role="nav", x=0, y=0, w=360, h=56,
                     text="Your feed today", interactive=True,
                     touch_target=(360, 56), color="#FFFFFF", bg_color="#222222"),
        make_element(vp_w, vp_h, id="e2", role="container", x=0, y=64, w=360, h=200,
                     contrast_ratio=None, font_size=None),
        make_element(vp_w, vp_h, id="e3", role="image", x=16, y=72, w=80, h=80,
                     contrast_ratio=None, font_size=None, parent="e2",
                     image_meta=ImageMeta(intrinsic_w=160, intrinsic_h=160,
                                          displayed_w=80, displayed_h=80,
                                          scale_mode="fill")),
        make_element(vp_w, vp_h, id="e4", role="text", x=112, y=72, w=232, h=24,
                     text="A great article", font_size=18.0, parent="e2"),
        make_element(vp_w, vp_h, id="e5", role="text", x=112, y=104, w=232, h=48,
                     text="Read the full story inside", font_size=14.0, parent="e2"),
        make_element(vp_w, vp_h, id="e6", role="button", x=16, y=168, w=160, h=48,
                     text="Open story", interactive=True, parent="e2",
                     color="#FFFFFF", bg_color="#1565C0"),
        make_element(vp_w, vp_h, id="e7", role="button", x=192, y=168, w=152, h=48,
                     text="Save later", interactive=True, parent="e2",
                     color="#1565C0", bg_color="#FFFFFF"),
    ]
    return make_doc(screen_id="mobile_feed", platform="android",
                    vp_w=vp_w, vp_h=vp_h, dpr=1.0, elements=els, route="/feed")


def base_mobile_form() -> CanonicalDoc:
    vp_w, vp_h = 360, 800
    els = [
        make_element(vp_w, vp_h, id="e1", role="container", x=0, y=0, w=360, h=800,
                     contrast_ratio=None, font_size=None),
        make_element(vp_w, vp_h, id="e2", role="text", x=32, y=48, w=296, h=32,
                     text="Create account", font_size=24.0, parent="e1"),
        make_element(vp_w, vp_h, id="e3", role="input", x=32, y=120, w=296, h=56,
                     text="Full name", interactive=True, parent="e1"),
        make_element(vp_w, vp_h, id="e4", role="input", x=32, y=192, w=296, h=56,
                     text="Email address", interactive=True, parent="e1"),
        make_element(vp_w, vp_h, id="e5", role="input", x=32, y=264, w=296, h=56,
                     text="Phone number", interactive=True, parent="e1"),
        make_element(vp_w, vp_h, id="e6", role="toggle", x=32, y=344, w=56, h=32,
                     text=None, interactive=True, touch_target=(56, 48), parent="e1"),
        make_element(vp_w, vp_h, id="e7", role="text", x=96, y=344, w=232, h=32,
                     text="Accept the terms", font_size=14.0, parent="e1"),
        make_element(vp_w, vp_h, id="e8", role="button", x=32, y=416, w=296, h=56,
                     text="Submit form", interactive=True, parent="e1",
                     color="#FFFFFF", bg_color="#1565C0"),
    ]
    return make_doc(screen_id="mobile_form", platform="android",
                    vp_w=vp_w, vp_h=vp_h, dpr=1.0, elements=els, route="/signup")


def base_web_landing() -> CanonicalDoc:
    vp_w, vp_h = 1280, 800
    els = [
        make_element(vp_w, vp_h, id="e1", role="nav", x=0, y=0, w=1280, h=64,
                     text="Home about contact", interactive=True,
                     touch_target=(1280, 64), color="#111111", bg_color="#FFFFFF"),
        make_element(vp_w, vp_h, id="e2", role="image", x=0, y=64, w=1280, h=400,
                     contrast_ratio=None, font_size=None, z=0,
                     image_meta=ImageMeta(intrinsic_w=2560, intrinsic_h=800,
                                          displayed_w=1280, displayed_h=400,
                                          scale_mode="fill")),
        make_element(vp_w, vp_h, id="e3", role="text", x=96, y=160, w=600, h=56,
                     text="Build better apps", font_size=40.0, parent="e2"),
        make_element(vp_w, vp_h, id="e4", role="text", x=96, y=240, w=600, h=32,
                     text="Ship faster every week", font_size=18.0, parent="e2"),
        make_element(vp_w, vp_h, id="e5", role="button", x=96, y=304, w=200, h=56,
                     text="Get started", interactive=True, parent="e2",
                     color="#FFFFFF", bg_color="#1565C0"),
        make_element(vp_w, vp_h, id="e6", role="button", x=312, y=304, w=200, h=56,
                     text="Learn more", interactive=True, parent="e2",
                     color="#1565C0", bg_color="#FFFFFF"),
    ]
    return make_doc(screen_id="web_landing", platform="web",
                    vp_w=vp_w, vp_h=vp_h, dpr=1.0, elements=els, route="/")


def base_web_table() -> CanonicalDoc:
    vp_w, vp_h = 1280, 800
    els = [
        make_element(vp_w, vp_h, id="e1", role="nav", x=0, y=0, w=1280, h=64,
                     text="Dashboard reports", interactive=True,
                     touch_target=(1280, 64), color="#111111", bg_color="#FFFFFF"),
        make_element(vp_w, vp_h, id="e2", role="container", x=0, y=64, w=1280, h=600,
                     contrast_ratio=None, font_size=None),
        make_element(vp_w, vp_h, id="e3", role="text", x=32, y=96, w=200, h=32,
                     text="Total users", font_size=16.0, parent="e2"),
        make_element(vp_w, vp_h, id="e4", role="text", x=320, y=96, w=200, h=32,
                     text="Active sessions", font_size=16.0, parent="e2"),
        make_element(vp_w, vp_h, id="e5", role="text", x=608, y=96, w=200, h=32,
                     text="Revenue total", font_size=16.0, parent="e2"),
        make_element(vp_w, vp_h, id="e6", role="text", x=32, y=144, w=200, h=32,
                     text="Twelve thousand", font_size=16.0, parent="e2"),
        make_element(vp_w, vp_h, id="e7", role="text", x=320, y=144, w=200, h=32,
                     text="Eight hundred", font_size=16.0, parent="e2"),
        make_element(vp_w, vp_h, id="e8", role="button", x=1088, y=96, w=160, h=48,
                     text="Export data", interactive=True, parent="e2",
                     color="#FFFFFF", bg_color="#1565C0"),
    ]
    return make_doc(screen_id="web_table", platform="web",
                    vp_w=vp_w, vp_h=vp_h, dpr=1.0, elements=els, route="/dashboard")


def base_ios_safe_area() -> CanonicalDoc:
    vp_w, vp_h = 390, 844
    # safe_area top=48 (notch), bottom=32 (home indicator). Đặt nội dung TRONG vùng an toàn.
    els = [
        # Root container nằm TRONG safe-area (y=48 dưới notch, bottom=812 trên home indicator)
        make_element(vp_w, vp_h, id="e1", role="container", x=0, y=48, w=390, h=764,
                     contrast_ratio=None, font_size=None),
        make_element(vp_w, vp_h, id="e2", role="nav", x=0, y=48, w=390, h=48,
                     text="Profile page", interactive=True, touch_target=(390, 48),
                     parent="e1", color="#111111", bg_color="#FFFFFF"),
        make_element(vp_w, vp_h, id="e3", role="image", x=152, y=120, w=88, h=88,
                     contrast_ratio=None, font_size=None, parent="e1",
                     image_meta=ImageMeta(intrinsic_w=176, intrinsic_h=176,
                                          displayed_w=88, displayed_h=88,
                                          scale_mode="fit")),
        make_element(vp_w, vp_h, id="e4", role="text", x=96, y=224, w=200, h=32,
                     text="Jordan Avery", font_size=20.0, parent="e1"),
        make_element(vp_w, vp_h, id="e5", role="button", x=48, y=288, w=296, h=56,
                     text="Edit profile", interactive=True, parent="e1",
                     color="#FFFFFF", bg_color="#1565C0"),
        make_element(vp_w, vp_h, id="e6", role="button", x=48, y=720, w=296, h=56,
                     text="Sign out now", interactive=True, parent="e1",
                     color="#1565C0", bg_color="#FFFFFF"),
    ]
    return make_doc(screen_id="ios_safe_area", platform="ios",
                    vp_w=vp_w, vp_h=vp_h, dpr=1.0, elements=els,
                    safe_area=SafeArea(top=48, bottom=32), route="/profile")


BASES: dict[str, Callable[[], CanonicalDoc]] = {
    "mobile_login": base_mobile_login,
    "mobile_feed": base_mobile_feed,
    "mobile_form": base_mobile_form,
    "web_landing": base_web_landing,
    "web_table": base_web_table,
    "ios_safe_area": base_ios_safe_area,
}


# ---------------------------------------------------------------------------
# Mutator library — 1 hàm/rule. (clean_doc) -> (mutated_doc, expected_labels)
# expected_labels: list[dict(rule, element, severity_range{min,max})]
# ---------------------------------------------------------------------------

ExpLabel = dict
Mutator = Callable[[CanonicalDoc], tuple[CanonicalDoc, list[ExpLabel]]]


def _find(doc: CanonicalDoc, eid: str) -> Element:
    for e in doc.elements:
        if e.id == eid:
            return e
    raise KeyError(eid)


def _lbl(rule: str, element: str | None, smin: str, smax: str) -> ExpLabel:
    return {"rule": rule, "element": element,
            "severity_range": {"min": smin, "max": smax}}


def _renorm(doc: CanonicalDoc, e: Element) -> None:
    vp = doc.screen.viewport
    e.bbox_norm = _norm(e.bbox, vp.w, vp.h)


# --- R1 geometry ---

def mut_r1_cmp01_touch_target(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-CMP01: thu nhỏ touch target dưới ngưỡng (android 48)."""
    e = _find(doc, "e6")  # button mobile_login
    e.bbox = BBox(x=e.bbox.x, y=e.bbox.y, w=32, h=32)
    e.touch_target = TouchTarget(w=32, h=32)
    _renorm(doc, e)
    return doc, [_lbl("R1-CMP01", "e6", "medium", "high")]


def mut_r1_cmp16_tap_gap(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-CMP16: 2 button interactive cách nhau < 8px (gap dương)."""
    # mobile_feed: thu e6 còn w=156 (right=172), e7 đặt x=176 (bám lưới) → gap=4 < 8.
    # x của cả 2 đều bội số 8 → không trip R1-LAY04.
    e6 = _find(doc, "e6")
    e6.bbox = BBox(x=16, y=168, w=156, h=48)
    e6.touch_target = TouchTarget(w=156, h=48)
    _renorm(doc, e6)
    e7 = _find(doc, "e7")
    e7.bbox = BBox(x=176, y=168, w=152, h=48)
    e7.touch_target = TouchTarget(w=152, h=48)
    _renorm(doc, e7)
    return doc, [_lbl("R1-CMP16", "e6", "low", "high")]


def mut_r1_env01_safe_area(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-ENV01: button lấn vào safe_area.top (notch) > 10px (ios base)."""
    e = _find(doc, "e5")  # button ios
    # y=8,h=32 → bottom=40 (<48): lấn safe-area top 32px (>10), KHÔNG chạm nav e2(y=48)
    # → cô lập khỏi R1-CMP16 (gap với e2 = 8px, không < 8).
    e.bbox = BBox(x=48, y=8, w=296, h=32)
    e.parent = None  # tránh R1-LAY03 overflow (parent e1 bắt đầu y=48)
    _renorm(doc, e)
    return doc, [_lbl("R1-ENV01", "e5", "medium", "critical")]


def mut_r1_lay01_overlap(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-LAY01: 2 sibling text (KHÔNG interactive) overlap iou > 0.05.
    Dùng text để cô lập khỏi R1-CMP16 (chỉ áp interactive)."""
    from ui_defect.utils.geometry import iou as _iou
    # mobile_feed: e4 (text x112,y72,232x24), e5 (text x112,y104,232x48). Đẩy e5 đè e4.
    e5 = _find(doc, "e5")
    e5.bbox = BBox(x=112, y=80, w=232, h=48)  # đè lên e4 (y72..96)
    _renorm(doc, e5)
    e4 = _find(doc, "e4")
    iou_val = _iou(e4.bbox, e5.bbox)
    doc.relations.append(Relation(a="e4", b="e5", rel="overlaps", iou=iou_val))
    # element nhỏ hơn diện tích bị flag: e4 area=232*24 < e5 232*48 → e4
    return doc, [_lbl("R1-LAY01", "e4", "medium", "critical")]


def mut_r1_lay02_offscreen(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-LAY02: button vượt mép phải viewport."""
    e = _find(doc, "e6")  # button mobile_login, vp_w=360
    e.bbox = BBox(x=320, y=456, w=296, h=56)  # x+w=616 >> 360
    e.parent = None  # tránh R1-LAY03 overflow lan kèm (cô lập R1-LAY02)
    _renorm(doc, e)
    return doc, [_lbl("R1-LAY02", "e6", "medium", "critical")]


def mut_r1_lay03_overflow(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-LAY03: child text vượt parent container > 4px."""
    # mobile_feed e2 container (x0,y64,360x200 → bottom 264). e5 text con tràn ĐÁY parent
    # (giữ trong viewport để cô lập khỏi R1-LAY02 offscreen).
    e5 = _find(doc, "e5")
    e5.bbox = BBox(x=112, y=104, w=232, h=240)  # bottom=344 > parent bottom 264; trong vp
    _renorm(doc, e5)
    return doc, [_lbl("R1-LAY03", "e5", "low", "high")]


def mut_r1_lay04_grid(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-LAY04: lệch lưới 8px (x lệch ~4px khỏi mốc gần nhất)."""
    e = _find(doc, "e3")  # text mobile_login
    e.bbox = BBox(x=99, y=216, w=168, h=32)  # 99 % 8 = 3 → off=3 (>2, <6) → bad_x
    _renorm(doc, e)
    return doc, [_lbl("R1-LAY04", "e3", "trivial", "medium")]


def mut_r1_lay14_near_dup(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-LAY14: 2 element gần trùng vị trí iou > 0.9."""
    # mobile_feed: thêm element trùng e4 gần như khít.
    e4 = _find(doc, "e4")
    dup = make_element(doc.screen.viewport.w, doc.screen.viewport.h,
                       id="e99", role="text", x=e4.bbox.x, y=e4.bbox.y,
                       w=e4.bbox.w, h=e4.bbox.h, text="A great article",
                       font_size=18.0, parent="e2")
    doc.elements.append(dup)
    doc.relations.append(Relation(a="e4", b="e99", rel="overlaps", iou=1.0))
    # iou>0.9 LUÔN kéo theo R1-LAY01 (ngưỡng 0.05) — không tách được; cả 2 đều đúng.
    # element bị flag: LAY14 dùng rel.a (e4); LAY01 dùng element nhỏ hơn (e4==e99 cùng size → e4).
    return doc, [
        _lbl("R1-LAY14", "e4", "low", "high"),
        _lbl("R1-LAY01", "e4", "medium", "critical"),
    ]


# --- R2 color ---

def mut_r2_sty01_contrast(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R2-STY01: contrast text thường < 4.5 (nhưng >= 1.5)."""
    e = _find(doc, "e7")  # text mobile_login, font 14 (thường)
    e.style.contrast_ratio = 2.5  # type: ignore[union-attr]
    return doc, [_lbl("R2-STY01", "e7", "medium", "high")]


def mut_r2_sty02_invisible(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R2-STY02: contrast < 1.5 → chữ tàng hình (critical)."""
    e = _find(doc, "e3")  # text mobile_login
    e.style.contrast_ratio = 1.1  # type: ignore[union-attr]
    return doc, [_lbl("R2-STY02", "e3", "high", "critical")]


def mut_r2_sty03_dark_mode(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R2-STY03: theme dark + dark_mode_ok=False → hardcode màu sáng."""
    doc.screen.theme = "dark"  # type: ignore[assignment]
    e = _find(doc, "e6")  # button mobile_login
    e.style.dark_mode_ok = False  # type: ignore[union-attr]
    # giữ contrast cao để không trip STY01/04
    e.style.contrast_ratio = 7.0  # type: ignore[union-attr]
    return doc, [_lbl("R2-STY03", "e6", "medium", "critical")]


def mut_r2_sty04_dark_icon(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R2-STY04: icon contrast < 3.0 trong dark mode."""
    doc.screen.theme = "dark"  # type: ignore[assignment]
    e = _find(doc, "e2")  # image mobile_login → đổi thành icon
    e.role = "icon"  # type: ignore[assignment]
    e.image_meta = None
    e.style.contrast_ratio = 2.0  # type: ignore[union-attr]
    e.style.font_size = None  # type: ignore[union-attr]
    return doc, [_lbl("R2-STY04", "e2", "medium", "critical")]


def mut_r2_sty05_opacity(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R2-STY05: opacity < 0.35 (gần vô hình)."""
    e = _find(doc, "e6")  # button mobile_login
    e.style.opacity = 0.1  # type: ignore[union-attr]
    return doc, [_lbl("R2-STY05", "e6", "low", "high")]


def mut_r2_sty13_icon_contrast(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R2-STY13: icon chức năng (interactive) contrast < 3.0 (light mode)."""
    e = _find(doc, "e2")  # image mobile_login → icon interactive
    e.role = "icon"  # type: ignore[assignment]
    e.image_meta = None
    e.interactive = True
    e.touch_target = TouchTarget(w=104, h=104)
    e.style.contrast_ratio = 2.2  # type: ignore[union-attr]
    e.style.font_size = None  # type: ignore[union-attr]
    return doc, [_lbl("R2-STY13", "e2", "low", "high")]


# --- R3 image ---

def mut_r3_img02_distortion(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R3-IMG02: méo tỉ lệ render so với gốc > 15% (high)."""
    e = _find(doc, "e2")  # image mobile_login, intrinsic 200x200
    e.image_meta = ImageMeta(intrinsic_w=200, intrinsic_h=200,
                             displayed_w=104, displayed_h=52,  # ratio 2.0 vs 1.0 → lệch 100%
                             scale_mode="fill")
    return doc, [_lbl("R3-IMG02", "e2", "low", "high")]


def mut_r3_img03_blur(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R3-IMG03: blur_score < BLUR_WARN (50) → mờ."""
    e = _find(doc, "e2")  # image mobile_login
    im = e.image_meta or ImageMeta()
    im.blur_score = 20.0
    e.image_meta = im
    return doc, [_lbl("R3-IMG03", "e2", "low", "medium")]


def mut_r3_img07_icon_offcenter(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R3-IMG07: icon lệch tâm trong nút > 5% parent width."""
    # mobile_feed e6 button (x16,y168,160x48). Thêm icon con lệch tâm.
    parent = _find(doc, "e6")
    icon = make_element(doc.screen.viewport.w, doc.screen.viewport.h,
                        id="e98", role="icon", x=24, y=176,
                        w=24, h=24, contrast_ratio=5.0, font_size=None, parent="e6")
    # parent center x = 16+80=96; icon center x = 24+12=36 → h_offset 60 > 5%*160=8
    # x=24,y=176 đều bội số gần lưới (off<=2) → không trip R1-LAY04.
    parent.children = list(parent.children) + ["e98"]
    doc.elements.append(icon)
    return doc, [_lbl("R3-IMG07", "e98", "trivial", "medium")]


def mut_r3_img09_scale_mode(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R3-IMG09: scale_mode='stretch'."""
    e = _find(doc, "e2")  # image mobile_login
    im = e.image_meta or ImageMeta()
    im.scale_mode = "stretch"
    e.image_meta = im
    return doc, [_lbl("R3-IMG09", "e2", "low", "high")]


# --- R4 text ---

def mut_r4_cnt01_placeholder(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT01: placeholder/biến chưa render."""
    e = _find(doc, "e3")  # text mobile_login
    e.text = "Welcome {{user_name}}"
    return doc, [_lbl("R4-CNT01", "e3", "medium", "critical")]


def mut_r4_cnt02_i18n(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT02: i18n key lòi ra (dot-notation)."""
    e = _find(doc, "e3")
    e.text = "home.login.title"
    return doc, [_lbl("R4-CNT02", "e3", "medium", "critical")]


def mut_r4_cnt04_lorem(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT04: lorem ipsum."""
    e = _find(doc, "e3")
    e.text = "Lorem ipsum dolor sit amet"
    return doc, [_lbl("R4-CNT04", "e3", "medium", "high")]


def mut_r4_cnt05_debug(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT05: text debug/nội bộ."""
    e = _find(doc, "e3")
    e.text = "TODO fixme placeholder"
    return doc, [_lbl("R4-CNT05", "e3", "medium", "critical")]


def mut_r4_cnt06_mojibake(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT06: mojibake / HTML entity thô."""
    e = _find(doc, "e3")
    e.text = "Welcome &nbsp; back"
    return doc, [_lbl("R4-CNT06", "e3", "low", "high")]


def mut_r4_cnt07_escape(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT07: escape literal thô."""
    e = _find(doc, "e3")
    e.text = "Line one\\nLine two"
    return doc, [_lbl("R4-CNT07", "e3", "low", "high")]


def mut_r4_cnt08_epoch(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-CNT08: epoch/số thô."""
    e = _find(doc, "e3")
    e.text = "Updated 1700000000"
    return doc, [_lbl("R4-CNT08", "e3", "low", "high")]


def mut_r4_state03_stacktrace(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-STATE03: stack trace / raw error lộ UI."""
    e = _find(doc, "e3")
    e.text = "NullPointerException at com.app.Main"
    return doc, [_lbl("R4-STATE03", "e3", "medium", "critical")]


def mut_r4_typ03_truncation(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-TYP03: text bị cắt cụt không ellipsis trên button."""
    e = _find(doc, "e6")  # button mobile_login
    e.text = "Sign in to your accoun"
    e.text_truncated = True
    return doc, [_lbl("R4-TYP03", "e6", "trivial", "critical")]


def mut_r4_typ05_font(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R4-TYP05: font_size < 11 → high."""
    e = _find(doc, "e7")  # text mobile_login
    e.style.font_size = 9.0  # type: ignore[union-attr]
    return doc, [_lbl("R4-TYP05", "e7", "low", "high")]


# --- Rule cần field từ analyzer (đã nối vào schema 2026-06-04: A13/A6/A10 → doc) ---

def mut_r1_env02_status_bar(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-ENV02: phần tử chồng status bar (A13 đo status_bar_h → Screen.status_bar_h).
    Chỉ root container e1 (y=0) lọt dưới status_bar_h+4; element khác bắt đầu ≥80px → không co-fire."""
    doc.screen.status_bar_h = 72.0  # device px — pipeline thật lấy từ A13.resolve_metadata
    return doc, [_lbl("R1-ENV02", "e1", "low", "high")]


def mut_r1_env03_home_indicator(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R1-ENV03: phần tử chồng home indicator (iOS, A13 đo nav_bar_h). Tách e6 khỏi container
    + safe_area.bottom=0 để cô lập khỏi R1-LAY03 (overflow) và R1-ENV01 (safe-area)."""
    doc.screen.nav_bar_h = 34.0  # device px
    doc.screen.safe_area = SafeArea(top=48, bottom=0)
    e = _find(doc, "e6")  # button ios_safe_area
    e.parent = None
    e.bbox = BBox(x=48, y=784, w=296, h=56)  # bottom=840 > (vp_h 844 - nav_bar_h 34)+4 = 814
    _renorm(doc, e)
    return doc, [_lbl("R1-ENV03", "e6", "low", "high")]


def mut_r3_img08_placeholder(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R3-IMG08: ảnh/icon placeholder chưa load (A6 gắn image_meta.possible_placeholder)."""
    e = _find(doc, "e2")  # image mobile_login
    e.image_meta.possible_placeholder = True  # type: ignore[union-attr]
    return doc, [_lbl("R3-IMG08", "e2", "low", "high")]


def mut_r3_img12_duplicate(doc: CanonicalDoc) -> tuple[CanonicalDoc, list[ExpLabel]]:
    """R3-IMG12: 2 ảnh trùng lặp (A10 ghi doc.duplicate_pairs). Thêm ảnh e8 sao y bản chính e3,
    để top-level (parent=None) → khác parent e3 ⇒ confidence cao, không bị giảm như list-row."""
    vp = doc.screen.viewport
    e8 = make_element(vp.w, vp.h, id="e8", role="image", x=16, y=320, w=80, h=80,
                      contrast_ratio=None, font_size=None,
                      image_meta=ImageMeta(intrinsic_w=160, intrinsic_h=160,
                                           displayed_w=80, displayed_h=80,
                                           scale_mode="fill"))
    doc.elements.append(e8)
    doc.duplicate_pairs = [{"a": "e3", "b": "e8", "hamming": 2}]
    return doc, [_lbl("R3-IMG12", "e3", "trivial", "medium")]


# Mapping rule → (base, mutator). Mỗi mutator dùng base phù hợp.
POSITIVE_CASES: list[tuple[str, str, Mutator]] = [
    # rule_id (cho tên case)        base             mutator
    ("R1-CMP01", "mobile_login", mut_r1_cmp01_touch_target),
    ("R1-CMP16", "mobile_feed",  mut_r1_cmp16_tap_gap),
    ("R1-ENV01", "ios_safe_area", mut_r1_env01_safe_area),
    ("R1-ENV02", "mobile_login", mut_r1_env02_status_bar),
    ("R1-ENV03", "ios_safe_area", mut_r1_env03_home_indicator),
    ("R1-LAY01", "mobile_feed",  mut_r1_lay01_overlap),
    ("R1-LAY02", "mobile_login", mut_r1_lay02_offscreen),
    ("R1-LAY03", "mobile_feed",  mut_r1_lay03_overflow),
    ("R1-LAY04", "mobile_login", mut_r1_lay04_grid),
    ("R1-LAY14", "mobile_feed",  mut_r1_lay14_near_dup),
    ("R2-STY01", "mobile_login", mut_r2_sty01_contrast),
    ("R2-STY02", "mobile_login", mut_r2_sty02_invisible),
    ("R2-STY03", "mobile_login", mut_r2_sty03_dark_mode),
    ("R2-STY04", "mobile_login", mut_r2_sty04_dark_icon),
    ("R2-STY05", "mobile_login", mut_r2_sty05_opacity),
    ("R2-STY13", "mobile_login", mut_r2_sty13_icon_contrast),
    ("R3-IMG02", "mobile_login", mut_r3_img02_distortion),
    ("R3-IMG03", "mobile_login", mut_r3_img03_blur),
    ("R3-IMG07", "mobile_feed",  mut_r3_img07_icon_offcenter),
    ("R3-IMG09", "mobile_login", mut_r3_img09_scale_mode),
    ("R3-IMG08", "mobile_login", mut_r3_img08_placeholder),
    ("R3-IMG12", "mobile_feed",  mut_r3_img12_duplicate),
    ("R4-CNT01", "mobile_login", mut_r4_cnt01_placeholder),
    ("R4-CNT02", "mobile_login", mut_r4_cnt02_i18n),
    ("R4-CNT04", "mobile_login", mut_r4_cnt04_lorem),
    ("R4-CNT05", "mobile_login", mut_r4_cnt05_debug),
    ("R4-CNT06", "mobile_login", mut_r4_cnt06_mojibake),
    ("R4-CNT07", "mobile_login", mut_r4_cnt07_escape),
    ("R4-CNT08", "mobile_login", mut_r4_cnt08_epoch),
    ("R4-STATE03", "mobile_login", mut_r4_state03_stacktrace),
    ("R4-TYP03", "mobile_login", mut_r4_typ03_truncation),
    ("R4-TYP05", "mobile_login", mut_r4_typ05_font),
]


# Rule chưa phủ được ở Tier-1 schema. (2026-06-04: đã nối field analyzer A13/A6/A10 vào
# Screen.status_bar_h/nav_bar_h, ImageMeta.possible_placeholder, CanonicalDoc.duplicate_pairs
# → R1-ENV02/03, R3-IMG08, R3-IMG12 nay biểu diễn & phủ được ở Tier-1. Danh sách rỗng = 32/32.)
UNSUPPORTED_RULES: list[tuple[str, str]] = []


# Near-miss negatives: bản sạch ngay trên ngưỡng, để bắt FP biên.
def nm_touch_target_ok(doc: CanonicalDoc) -> CanonicalDoc:
    """Touch target = 48 (đúng ngưỡng android, không fire)."""
    e = _find(doc, "e6")
    e.bbox = BBox(x=e.bbox.x, y=e.bbox.y, w=48, h=48)
    e.touch_target = TouchTarget(w=48, h=48)
    _renorm(doc, e)
    return doc


def nm_contrast_ok(doc: CanonicalDoc) -> CanonicalDoc:
    """Contrast = 4.5 (đúng ngưỡng text thường, không fire)."""
    e = _find(doc, "e7")
    e.style.contrast_ratio = 4.5  # type: ignore[union-attr]
    return doc


def nm_font_ok(doc: CanonicalDoc) -> CanonicalDoc:
    """Font = 13 (đúng ngưỡng warn, không fire vì >= 13)."""
    e = _find(doc, "e7")
    e.style.font_size = 13.0  # type: ignore[union-attr]
    return doc


def nm_aspect_ok(doc: CanonicalDoc) -> CanonicalDoc:
    """Méo tỉ lệ ~4% (< 5% warn, không fire)."""
    e = _find(doc, "e2")
    e.image_meta = ImageMeta(intrinsic_w=200, intrinsic_h=200,
                             displayed_w=104, displayed_h=100,  # ratio 1.04 → lệch 4%
                             scale_mode="fill")
    return doc


NEARMISS_CASES: list[tuple[str, str, Callable[[CanonicalDoc], CanonicalDoc]]] = [
    ("nearmiss_touch_target_48", "mobile_login", nm_touch_target_ok),
    ("nearmiss_contrast_45", "mobile_login", nm_contrast_ok),
    ("nearmiss_font_13", "mobile_login", nm_font_ok),
    ("nearmiss_aspect_4pct", "mobile_login", nm_aspect_ok),
]


# ---------------------------------------------------------------------------
# Sinh + ghi file
# ---------------------------------------------------------------------------

def _dump(doc: CanonicalDoc) -> dict:
    return doc.model_dump(mode="json", exclude_none=True)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate(out_dir: Path) -> dict:
    base_dir = out_dir / "base"
    cases_dir = out_dir / "cases"
    labels_dir = out_dir / "labels"

    # Idempotent: xoá sạch trước khi ghi
    for d in (base_dir, cases_dir, labels_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    # 1. Ghi base + tự kiểm sạch
    base_docs: dict[str, CanonicalDoc] = {}
    base_dirty: list[str] = []
    for name, fn in BASES.items():
        doc = fn()
        base_docs[name] = doc
        _write_json(base_dir / f"{name}.json", _dump(doc))
        out = run_rule_engine(deepcopy(doc))
        if out.candidate_issues:
            base_dirty.append(
                f"{name}: " + ", ".join(f"{i.rule}/{i.element}" for i in out.candidate_issues)
            )

    n_positive = 0
    n_negative = 0

    # 2. Positive cases
    for rule_id, base_name, mutator in POSITIVE_CASES:
        case_id = f"{rule_id.lower().replace('-', '_')}_{base_name}"
        clean = deepcopy(base_docs[base_name])
        mutated, expected = mutator(clean)
        _write_json(cases_dir / f"{case_id}.json", _dump(mutated))
        label = {
            "case_id": case_id,
            "base": base_name,
            "mutation": mutator.__name__,
            "kind": "positive",
            "expected": expected,
        }
        _write_json(labels_dir / f"{case_id}.json", label)
        n_positive += 1

    # 3. Negative — mỗi base 1 bản sạch
    for base_name, doc in base_docs.items():
        case_id = f"negative_{base_name}"
        _write_json(cases_dir / f"{case_id}.json", _dump(doc))
        label = {
            "case_id": case_id,
            "base": base_name,
            "mutation": "none",
            "kind": "negative",
            "expected": [],
        }
        _write_json(labels_dir / f"{case_id}.json", label)
        n_negative += 1

    # 4. Near-miss negatives
    for case_id, base_name, nm_fn in NEARMISS_CASES:
        clean = deepcopy(base_docs[base_name])
        mutated = nm_fn(clean)
        _write_json(cases_dir / f"{case_id}.json", _dump(mutated))
        label = {
            "case_id": case_id,
            "base": base_name,
            "mutation": nm_fn.__name__,
            "kind": "negative",
            "expected": [],
        }
        _write_json(labels_dir / f"{case_id}.json", label)
        n_negative += 1

    return {
        "n_base": len(base_docs),
        "n_positive": n_positive,
        "n_negative": n_negative,
        "base_dirty": base_dirty,
        "out_dir": out_dir,
    }


# ---------------------------------------------------------------------------
# Tự kiểm: load lại cases, chạy rule engine, đối chiếu labels
# ---------------------------------------------------------------------------

def self_check(out_dir: Path) -> list[tuple[str, bool, str]]:
    cases_dir = out_dir / "cases"
    labels_dir = out_dir / "labels"
    results: list[tuple[str, bool, str]] = []

    for label_path in sorted(labels_dir.glob("*.json")):
        label = json.loads(label_path.read_text(encoding="utf-8"))
        case_id = label["case_id"]
        case_data = json.loads((cases_dir / f"{case_id}.json").read_text(encoding="utf-8"))
        doc = CanonicalDoc.model_validate(case_data)
        out = run_rule_engine(doc)
        fired = {(i.rule, i.element) for i in out.candidate_issues}
        fired_sev = {(i.rule, i.element): i.severity for i in out.candidate_issues}

        if label["kind"] == "negative":
            ok = len(out.candidate_issues) == 0
            note = "sạch" if ok else "FP: " + ", ".join(f"{r}/{e}" for r, e in sorted(fired))
            results.append((case_id, ok, note))
        else:
            ok = True
            missing = []
            expected_keys = {(e["rule"], e["element"]) for e in label["expected"]}
            sev_order = ["trivial", "low", "medium", "high", "critical"]
            for exp in label["expected"]:
                key = (exp["rule"], exp["element"])
                if key not in fired:
                    ok = False
                    missing.append(f"{exp['rule']}/{exp['element']}")
                else:
                    # severity fired phải nằm trong severity_range của label (scorer khớp điều này)
                    sev = fired_sev[key]
                    lo = sev_order.index(exp["severity_range"]["min"])
                    hi = sev_order.index(exp["severity_range"]["max"])
                    if not (lo <= sev_order.index(sev) <= hi):
                        ok = False
                        missing.append(
                            f"{exp['rule']}/{exp['element']} sev={sev} ngoài "
                            f"[{exp['severity_range']['min']},{exp['severity_range']['max']}]"
                        )
            extras = sorted(fired - expected_keys)
            notes = []
            if missing:
                ok = False
                notes.append("MISSING: " + ", ".join(missing))
            if extras:
                # Extra candidate trên positive case → FP khi Agent B chấm điểm.
                ok = False
                notes.append("EXTRA(FP): " + ", ".join(f"{r}/{e}" for r, e in extras))
            note = "OK" if ok else " | ".join(notes)
            results.append((case_id, ok, note))

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh Standard Set Tier-1 (schema mutation).")
    ap.add_argument("--out", default="data/standard_v1/schema",
                    help="Thư mục output (mặc định data/standard_v1/schema)")
    args = ap.parse_args()

    out_dir = (_REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)

    stats = generate(out_dir)

    # README Tier-2
    images_dir = out_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "README.md").write_text(
        "# Standard Set Tier-2 — ảnh thật (CHƯA BUILD)\n\n"
        "TODO (F4.1): render ảnh thật bằng Playwright + mutate CSS/DOM rồi chạy qua\n"
        "Vision Adapter (OCR + CV) → CanonicalDoc → so với label. Cần OCR backend local\n"
        "(xem F1.1/SETUP). Hiện chỉ có Tier-1 schema-level ở `../schema/`.\n",
        encoding="utf-8",
    )

    print(f"== Standard Set sinh tại: {out_dir}")
    print(f"   base     : {stats['n_base']}")
    print(f"   positive : {stats['n_positive']}")
    print(f"   negative : {stats['n_negative']}")
    print(f"   TỔNG case: {stats['n_positive'] + stats['n_negative']}")
    if stats["base_dirty"]:
        print("!! BASE KHÔNG SẠCH:")
        for d in stats["base_dirty"]:
            print(f"   - {d}")

    # Tự kiểm
    print("\n== Tự kiểm (load lại → rule engine → đối chiếu label):")
    results = self_check(out_dir)
    n_pass = sum(1 for _, ok, _ in results if ok)
    n_fail = len(results) - n_pass
    for case_id, ok, note in results:
        flag = "OK  " if ok else "FAIL"
        print(f"   [{flag}] {case_id:40s} {note}")
    print(f"\n   PASS {n_pass}/{len(results)}  (FAIL {n_fail})")

    print(f"\n== Rule KHÔNG phủ được ở Tier-1 ({len(UNSUPPORTED_RULES)}/32 — cần Tier-2):")
    for rule_id, reason in UNSUPPORTED_RULES:
        print(f"   - {rule_id}: {reason}")
    covered = len(POSITIVE_CASES)
    print(f"   Đã phủ {covered}/32 rule bằng positive case.")

    return 0 if (n_fail == 0 and not stats["base_dirty"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
