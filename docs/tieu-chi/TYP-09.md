# TYP-09 — Chữ mờ / vỡ / răng cưa

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `medium` (range `low→medium`) · **Tags:** resp
> **Trạng thái:** ✅ Có rule tất định
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
A8 Laplacian variance (F0.4 §5.3)

## Kỹ thuật & ai đánh giá
🟦 Rule tất định (code tính từ số/box/pixel) — A8

## ❌ Không đạt (fail) khi
Laplacian var < BLUR_WARN (50) trên crop text

## ✅ Đạt (pass) khi
> 100 (rõ)

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
