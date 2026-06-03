# TYP-12 — RTL/bidi hỏng

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** i18n
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`script` (A5), `text`, bbox

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

## ❌ Không đạt (fail) khi
Ả Rập/Do Thái chạy sai chiều, dấu câu lệch

## ✅ Đạt (pass) khi
đúng chiều RTL

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
