"""
A13 — Device/Env Metadata Provider
Điền safe_area / dpr / bars vào schema. Chạy trước mọi analyzer khác.
Spec: docs/analyzers/A13-device-env-metadata.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PIL import Image

from ..schema.models import SafeArea, Screen, Viewport


# ── Bảng device profile tĩnh ─────────────────────────────────────────────────
# Key: (platform, px_width, px_height) hoặc (platform, pt_width, pt_height, dpr)
# Các màn hình phổ biến (thêm dần khi golden set mở rộng).

@dataclass
class DeviceProfile:
    name: str
    platform: str
    pt_w: int        # logical point width
    pt_h: int        # logical point height
    dpr: float
    safe_top: int    # pt (sau khi nhân dpr = px)
    safe_bottom: int # pt
    status_bar_h: int # pt
    nav_bar_h: int   # pt
    notch_type: str  # none | notch | dynamic_island | punch_hole | unknown


# Bảng device phổ biến (pt units — nhân dpr để ra device px)
_DEVICE_TABLE: list[DeviceProfile] = [
    # iOS
    DeviceProfile("iPhone SE 3rd", "ios", 375, 667, 2.0, 20, 0, 20, 0, "none"),
    DeviceProfile("iPhone 13/14", "ios", 390, 844, 3.0, 47, 34, 47, 34, "notch"),
    DeviceProfile("iPhone 14 Pro/15", "ios", 393, 852, 3.0, 59, 34, 59, 34, "dynamic_island"),
    DeviceProfile("iPhone 15 Pro Max", "ios", 430, 932, 3.0, 59, 34, 59, 34, "dynamic_island"),
    DeviceProfile("iPad Air", "ios", 820, 1180, 2.0, 24, 20, 24, 0, "none"),
    # Android (common)
    DeviceProfile("Pixel 6", "android", 411, 891, 2.625, 24, 16, 24, 48, "punch_hole"),
    DeviceProfile("Pixel 7", "android", 412, 892, 2.625, 24, 16, 24, 48, "punch_hole"),
    DeviceProfile("Samsung S23", "android", 360, 780, 3.0, 24, 20, 24, 48, "punch_hole"),
    DeviceProfile("Generic Android", "android", 360, 800, 3.0, 24, 16, 24, 48, "unknown"),
    # Web / Desktop (safe_area = 0)
    DeviceProfile("Web 1920", "web", 1920, 1080, 1.0, 0, 0, 0, 0, "none"),
    DeviceProfile("Web 1440", "web", 1440, 900, 1.0, 0, 0, 0, 0, "none"),
    DeviceProfile("Web 390", "web", 390, 844, 1.0, 0, 0, 0, 0, "none"),
]


def _find_device_profile(
    platform: str,
    pt_w: int,
    pt_h: int,
    dpr: Optional[float] = None,
) -> Optional[DeviceProfile]:
    """Tra bảng device theo platform + kích thước. Trả profile gần nhất hoặc None."""
    exact = [
        p for p in _DEVICE_TABLE
        if p.platform == platform and abs(p.pt_w - pt_w) <= 5 and abs(p.pt_h - pt_h) <= 10
    ]
    if exact:
        if dpr:
            by_dpr = [p for p in exact if abs(p.dpr - dpr) < 0.1]
            return by_dpr[0] if by_dpr else exact[0]
        return exact[0]
    # Fallback: chỉ match platform
    by_platform = [p for p in _DEVICE_TABLE if p.platform == platform]
    if by_platform:
        return min(by_platform, key=lambda p: abs(p.pt_w - pt_w) + abs(p.pt_h - pt_h))
    return None


def _infer_from_pixel(
    img: Image.Image,
    platform: str,
) -> tuple[SafeArea, str, str, float]:
    """
    Dự phòng: suy safe_area từ pixel.
    Trả: (safe_area, orientation, notch_type, confidence).
    Confidence thấp khi pixel-inferred.
    """
    import cv2
    import numpy as np

    w, h = img.width, img.height
    orientation = "portrait" if h > w else "landscape"
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Ước lượng status bar: dải trên cùng có ít text/icon + màu đồng nhất
    top_band = gray[:max(1, h // 15), :]
    top_var = float(top_band.std())

    if top_var < 20:
        # Dải trên đồng nhất (có thể status bar)
        status_h = h // 15
    elif platform == "ios":
        status_h = int(h * 0.056)  # ~47pt/844pt ≈ 5.6%
    elif platform == "android":
        status_h = int(h * 0.03)
    else:
        status_h = 0

    # Home indicator: dải dưới cùng
    if platform == "ios":
        nav_h = int(h * 0.04)     # ~34pt/844pt ≈ 4%
    elif platform == "android":
        nav_h = int(h * 0.055)    # gesture bar
    else:
        nav_h = 0

    # Notch phát hiện sơ bộ: dải trên có vùng tối ở giữa
    top_strip = gray[:status_h, w//3:2*w//3] if status_h > 0 else np.array([[]])
    notch = "none"
    if platform == "ios" and top_strip.size > 0:
        if top_strip.mean() < 50:
            notch = "dynamic_island"
        elif top_strip.mean() < 100:
            notch = "notch"

    safe = SafeArea(top=status_h, bottom=nav_h, left=0, right=0)
    return safe, orientation, notch, 0.55


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class MetaResult:
    safe_area: SafeArea
    viewport: Viewport
    orientation: str
    notch_type: str
    meta_source: str
    meta_confidence: float
    status_bar_h: int = 0
    nav_bar_h: int = 0


def detect_platform(img: Image.Image) -> tuple[str, float]:
    """
    Đoán platform từ ảnh: "android" | "ios" | "web".
    Trả (platform, confidence).

    Heuristic theo thứ tự độ tin cậy:
    1. Kích thước khớp bảng device profile → confidence cao
    2. Aspect ratio + orientation → phân biệt web vs mobile
    3. Bottom strip: iOS home indicator (thanh mảnh giữa) vs Android nav buttons
    4. Top strip: status bar layout
    """
    import cv2
    import numpy as np

    w, h = img.width, img.height
    aspect = h / w if w > 0 else 1.0

    # 1. Tra bảng device profile theo kích thước
    for platform in ("ios", "android"):
        profile = _find_device_profile(platform, w, h, dpr=None)
        if profile and abs(profile.pt_w - w) <= 10 and abs(profile.pt_h - h) <= 20:
            return platform, 0.88

    # 2. Aspect ratio: web/desktop thường rộng hoặc gần vuông
    if aspect < 1.2:
        return "web", 0.75
    if aspect > 2.2:
        # Rất cao → likely mobile
        pass

    # 3. Bottom strip: detect iOS home indicator (đường kẻ mảnh nằm giữa)
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    bottom_strip_h = max(4, h // 20)
    bottom = gray[h - bottom_strip_h:, :]

    # iOS home indicator: dải nằm giữa, sẫm hơn nền, chiều rộng ~30% màn
    mid_start = w // 3
    mid_end = 2 * w // 3
    mid_col_mean = bottom[:, mid_start:mid_end].mean()
    side_col_mean = (bottom[:, :mid_start].mean() + bottom[:, mid_end:].mean()) / 2
    ios_indicator_score = side_col_mean - mid_col_mean  # dương = giữa tối hơn

    # Android nav bar: 3 vùng đối xứng (back/home/recent buttons)
    third = w // 3
    left_mean = bottom[:, :third].mean()
    center_mean = bottom[:, third:2*third].mean()
    right_mean = bottom[:, 2*third:].mean()
    symmetry = 1.0 - abs(left_mean - right_mean) / (max(left_mean, right_mean, 1))
    android_nav_score = symmetry * (1.0 - abs(center_mean - (left_mean + right_mean) / 2) / 255)

    # 4. Top strip: status bar height heuristic
    top_h = max(4, h // 18)
    top_strip = gray[:top_h, :]
    top_var = float(top_strip.std())
    # iOS status bar: ít biến động, iOS thường có giờ ở giữa
    # Android: notification icons trái → variance cao hơn

    # Quyết định
    if ios_indicator_score > 10:
        return "ios", 0.72
    if android_nav_score > 0.7 and top_var > 15:
        return "android", 0.68

    # Fallback theo aspect ratio
    if aspect >= 1.8:
        return "android", 0.55  # mobile, default android
    return "web", 0.60


def resolve_metadata(
    img: Image.Image,
    screen: Screen,
    tester_meta: Optional[dict] = None,
) -> MetaResult:
    """
    Điền metadata. Thứ tự ưu tiên:
    1. tester_meta (JSON từ tester) → confidence 1.0
    2. Device profile table → confidence 0.85–0.9
    3. Pixel-inferred → confidence 0.55
    """
    # 1. Tester meta
    if tester_meta:
        sa_raw = tester_meta.get("safe_area", {})
        sa = SafeArea(
            top=int(sa_raw.get("top", 0)),
            bottom=int(sa_raw.get("bottom", 0)),
            left=int(sa_raw.get("left", 0)),
            right=int(sa_raw.get("right", 0)),
        )
        vp_raw = tester_meta.get("viewport", {})
        vp = Viewport(
            w=int(vp_raw.get("w", screen.viewport.w)),
            h=int(vp_raw.get("h", screen.viewport.h)),
            dpr=float(vp_raw.get("dpr", screen.viewport.dpr)),
        )
        return MetaResult(
            safe_area=sa,
            viewport=vp,
            orientation=tester_meta.get("orientation", "portrait"),
            notch_type=tester_meta.get("notch_type", "unknown"),
            meta_source="tester_meta",
            meta_confidence=1.0,
            status_bar_h=int(tester_meta.get("status_bar_h", sa.top)),
            nav_bar_h=int(tester_meta.get("nav_bar_h", sa.bottom)),
        )

    # 2. Device profile
    dpr = screen.viewport.dpr
    vp_w = screen.viewport.w
    vp_h = screen.viewport.h
    # Nếu viewport đã là device px (dpr ≠ 1), chuyển về pt
    pt_w = int(vp_w / dpr) if dpr > 1 else vp_w
    pt_h = int(vp_h / dpr) if dpr > 1 else vp_h

    profile = _find_device_profile(screen.platform, pt_w, pt_h, dpr)
    if profile:
        safe = SafeArea(
            top=int(profile.safe_top * dpr),
            bottom=int(profile.safe_bottom * dpr),
        )
        h_land = img.height
        orientation = "portrait" if img.height >= img.width else "landscape"
        return MetaResult(
            safe_area=safe,
            viewport=screen.viewport,
            orientation=orientation,
            notch_type=profile.notch_type,
            meta_source="device_profile",
            meta_confidence=0.85,
            status_bar_h=int(profile.status_bar_h * dpr),
            nav_bar_h=int(profile.nav_bar_h * dpr),
        )

    # 3. Pixel inference fallback
    safe, orientation, notch, conf = _infer_from_pixel(img, screen.platform)
    return MetaResult(
        safe_area=safe,
        viewport=screen.viewport,
        orientation=orientation,
        notch_type=notch,
        meta_source="pixel_inferred",
        meta_confidence=conf,
    )
