"""
Ngưỡng chuẩn dùng chung cho Rule Engine và Analyzer.
Nguồn gốc: docs/F0.4-thresholds.md
Ngưỡng đánh dấu TUNE = cần điều chỉnh sau khi có Standard Set.
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


# Tương phản (WCAG 2.1 AA)
CONTRAST_TEXT_NORMAL: float = 4.5
CONTRAST_TEXT_LARGE: float = 3.0
CONTRAST_UI: float = 3.0
CONTRAST_INVISIBLE: float = 1.5  # thấp hơn = STY-02 critical

# Cỡ chữ (device px)
FONT_MIN_PX: int = 11   # thấp hơn = TYP-05 high
FONT_WARN_PX: int = 13  # thấp hơn = TYP-05 medium

# Méo ảnh
ASPECT_WARN: float = 0.05   # > 5%  sai lệch → medium
ASPECT_ERROR: float = 0.15  # > 15% sai lệch → high
UPSCALE_RATIO: float = 1.5  # displayed > intrinsic × 1.5 → cảnh báo

# Nhòe — Laplacian variance (TUNE)
BLUR_CLEAR: float = 100.0
BLUR_WARN: float = 50.0

# Perceptual hash — Hamming distance 64-bit (TUNE)
HASH_IDENTICAL: int = 4
HASH_NEAR_DUP: int = 10

# Lưới (TUNE)
GRID_UNIT_LOGICAL: int = 8  # pt/dp/px (đơn vị logic)
GRID_TOLERANCE_PX: int = 2  # ± device px sau khi chuẩn hóa dpr

# Khoảng cách / chồng lấp
GAP_MIN_PX: int = 4       # gap < 4 device px → ứng viên chồng lấp (TUNE)
OVERLAP_IOU_MIN: float = 0.05  # iou > 0.05 → đánh dấu chồng lấp (TUNE)

# Overflow container (TUNE)
OVERFLOW_THRESHOLD: float = 4.0  # element vượt ra ngoài parent > 4px → fire R1-LAY03
