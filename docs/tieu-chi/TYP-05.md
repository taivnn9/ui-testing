# TYP-05 — Cỡ chữ quá nhỏ

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** a11y
> **Trạng thái:** ✅ Có rule tất định
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`style.font_size`, `font_scale`

## Kỹ thuật & ai đánh giá
🟦 Rule tất định (code tính từ số/box/pixel) — ngưỡng F0.4 §4

## ❌ Không đạt (fail) khi
font_size < FONT_MIN_PX (11px device)

## ✅ Đạt (pass) khi
≥ 14px

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
