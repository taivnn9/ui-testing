"""
Ngưỡng chuẩn dùng chung cho Rule Engine và Analyzer.
Nguồn gốc: docs/F0.4-thresholds.md
Ngưỡng đánh dấu TUNE = cần điều chỉnh sau khi có Golden Set.
"""


def touch_min_px(dpr: float, platform: str) -> float:
    """Kích thước touch target tối thiểu (device px)."""
    if platform == "ios":
        return 44.0 * dpr
    if platform == "android":
        return 48.0 * dpr
    return 44.0 * dpr  # web


def touch_gap_px(dpr: float) -> float:
    return 8.0 * dpr


# Contrast (WCAG 2.1 AA)
CONTRAST_TEXT_NORMAL: float = 4.5
CONTRAST_TEXT_LARGE: float = 3.0
CONTRAST_UI: float = 3.0
CONTRAST_INVISIBLE: float = 1.5  # below = STY-02 critical

# Font size (device px)
FONT_MIN_PX: int = 11   # below = TYP-05 high
FONT_WARN_PX: int = 13  # below = TYP-05 medium

# Image distortion
ASPECT_WARN: float = 0.05   # > 5%  deviation → medium
ASPECT_ERROR: float = 0.15  # > 15% deviation → high
UPSCALE_RATIO: float = 1.5  # displayed > intrinsic × 1.5 → flag

# Blur — Laplacian variance (TUNE)
BLUR_CLEAR: float = 100.0
BLUR_WARN: float = 50.0

# Perceptual hash — Hamming distance 64-bit (TUNE)
HASH_IDENTICAL: int = 4
HASH_NEAR_DUP: int = 10

# Grid (TUNE)
GRID_UNIT_LOGICAL: int = 8  # pt/dp/px (logical units)
GRID_TOLERANCE_PX: int = 2  # ± device px after dpr normalization

# Spacing / overlap
GAP_MIN_PX: int = 4       # gap < 4 device px → overlap candidate (TUNE)
OVERLAP_IOU_MIN: float = 0.05  # iou > 0.05 → flag overlaps (TUNE)
