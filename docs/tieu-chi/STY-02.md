# STY-02 — Chữ tàng hình (cùng màu nền)

> **Nhóm:** Color, Contrast & Visual Style — màu, tương phản, style (`STY`)
> **Severity nền:** `critical` (range `high→critical`) · **Tags:** a11y,dark
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`contrast_ratio`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R2.

## ❌ Không đạt (fail) khi
< CONTRAST_INVISIBLE (1.5)

## ✅ Đạt (pass) khi
contrast đủ thấy

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
