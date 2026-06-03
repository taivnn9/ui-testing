# TYP-14 — Emoji/icon-font render sai

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `low` (range `trivial→medium`) · **Tags:** i18n
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`has_replacement`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: A8 + agent.

## ❌ Không đạt (fail) khi
emoji thành box / mất màu (has_replacement)

## ✅ Đạt (pass) khi
emoji render đúng

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
