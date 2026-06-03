# TYP-04 — Chữ đè lên chữ / phần tử khác

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái:** ✅ Có rule tất định
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`relations` (overlaps text-text)

## Kỹ thuật & ai đánh giá
🟦 Rule tất định (code tính từ số/box/pixel) — R1 overlap

## ❌ Không đạt (fail) khi
2 element text `overlaps`, iou > OVERLAP_IOU_MIN (0.05)

## ✅ Đạt (pass) khi
không chồng

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
