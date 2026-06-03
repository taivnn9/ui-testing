# STY-01 — Contrast chữ/nền < WCAG

> **Nhóm:** Color, Contrast & Visual Style — màu, tương phản, style (`STY`)
> **Severity nền:** `high` (range `medium→high`) · **Tags:** a11y
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`style.contrast_ratio` (A4)

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R2 (F0.4 §3).

## ❌ Không đạt (fail) khi
< 4.5 (text thường) hoặc < 3.0 (text lớn)

## ✅ Đạt (pass) khi
≥ ngưỡng WCAG

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
