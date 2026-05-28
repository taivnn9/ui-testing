from ui_defect.schema.thresholds import (
    CONTRAST_TEXT_NORMAL,
    FONT_MIN_PX,
    HASH_NEAR_DUP,
    touch_gap_px,
    touch_min_px,
)


def test_touch_min_android_3x() -> None:
    assert touch_min_px(3.0, "android") == 144.0  # 48dp × 3


def test_touch_min_ios_2x() -> None:
    assert touch_min_px(2.0, "ios") == 88.0  # 44pt × 2


def test_touch_gap() -> None:
    assert touch_gap_px(3.0) == 24.0  # 8dp × 3


def test_contrast_aa() -> None:
    assert CONTRAST_TEXT_NORMAL == 4.5


def test_font_min() -> None:
    assert FONT_MIN_PX == 11


def test_hash_near_dup() -> None:
    assert HASH_NEAR_DUP == 10
