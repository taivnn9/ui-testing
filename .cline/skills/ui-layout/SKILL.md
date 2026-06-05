---
name: ui-layout
description: Detect spatial layout and geometry bugs in UI screen data including overlapping elements, off-screen content, safe area violations, small touch targets, and misalignment. Use when analyzing UI screenshot data for layout issues.
---

# Skill: Layout & Spatial geometry

Dựa trên `bbox`, `relations` (overlaps/iou/gap), `viewport`, `safe_area`. Bắt:
- **Chồng lấp/che khuất**: hai element `overlaps` với `iou` đáng kể mà không phải chủ đích
  (badge-trên-icon là chủ đích). Candidate R1 thường nêu.
- **Tràn màn hình / off-screen**: bbox vượt `viewport` (x<0, hoặc x+w>vp_w, y+h>vp_h).
- **Vi phạm safe-area**: element nằm trong vùng notch/status bar/home indicator (`safe_area`).
- **Touch target nhỏ**: element `interactive=true` có `touch_target` < 44pt iOS / 48dp Android.
- **Khoảng cách bất thường**: `gap` quá lớn/không nhất quán; lệch canh lề (optical alignment).
- **Z-order**: nội dung quan trọng bị che (suy từ overlap + z nếu có).

Đây là phần rule R1 mạnh nhất — chủ yếu xác nhận candidate theo số, bác cái rõ ràng là chủ đích.
