---
name: ui-color-style
description: Detect color, contrast, and visual style bugs in UI screen data including low contrast ratios, invisible text, hardcoded colors in dark mode, and indistinguishable states. Use when analyzing UI screenshot data for color accessibility issues.
---

# Skill: Color, Contrast & Visual style

`contrast_ratio` đã được CV tính (WCAG) — dùng làm ground truth. Bắt:
- **Tương phản thấp**: `contrast_ratio` < 4.5 (text thường) hoặc < 3.0 (text lớn/icon) → lỗi.
  Candidate R2 thường đã nêu; xác nhận theo số.
- **Text vô hình**: `color` ≈ `bg_color` (contrast_ratio rất thấp, ~1.x).
- **Dark mode hardcode**: nếu `theme=dark` mà element có màu sáng không đổi.
- **Trạng thái không phân biệt**: disabled/enabled, focus/selected giống nhau (suy từ style nếu có).

Dùng số `contrast_ratio` là chính; phần "ý đồ thiết kế" (decorative vs functional) thì phán đoán
thận trọng. Mâu thuẫn giữa số và rule → tin số.
