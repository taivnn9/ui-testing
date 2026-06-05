---
name: ui-images
description: Detect image and asset quality bugs in UI screen data including distorted aspect ratios, broken images, placeholder icons, and duplicate images. Use when analyzing UI screenshot data for image rendering issues.
---

# Skill: Images & Assets

Dựa trên `image_meta` (intrinsic_w/h, displayed_w/h, scale_mode) + candidate R3/A7/A9. Bắt:
- **Ảnh méo tỉ lệ**: tỉ lệ `displayed_w/displayed_h` lệch nhiều so với `intrinsic_w/intrinsic_h`.
- **Ảnh vỡ/trống**: candidate A9/A7 báo blank/broken (vùng đơn sắc bất thường, icon ảnh vỡ).
- **Icon placeholder/chưa tải**: role=icon nhưng trống/ô xám (theo flag CV).
- **Ảnh trùng lặp**: candidate A10 (perceptual hash) báo 2 ảnh giống nhau xuất hiện bất thường.

Lưu ý: KHÔNG nhìn được nội dung ảnh → **không phán đoán "sai ảnh/sai nội dung"** trừ khi có
bằng chứng dữ liệu. Blur chủ đích (frosted glass) không phải lỗi. Thiếu chắc chắn → confidence < 0.5.
