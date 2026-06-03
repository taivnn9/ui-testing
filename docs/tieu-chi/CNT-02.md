# CNT-02 — i18n key lòi ra chưa dịch

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** i18n
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R4 regex.

## ❌ Không đạt (fail) khi
text là key dot-notation (`home.title`, `btn_submit`) không phải từ thật

## ✅ Đạt (pass) khi
text là câu/từ tự nhiên

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
