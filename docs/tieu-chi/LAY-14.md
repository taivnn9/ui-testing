# LAY-14 — Phần tử chồng vị trí (cùng toạ độ)

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** —
> **Trạng thái:** ✅ Có rule tất định
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
bbox

## Kỹ thuật & ai đánh giá
🟦 Rule tất định (code tính từ số/box/pixel) — R1

## ❌ Không đạt (fail) khi
2 element gần trùng toạ độ

## ✅ Đạt (pass) khi
vị trí riêng biệt

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
