# CNT-01 — Placeholder/biến chưa render

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text` (A5 OCR)

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R4 regex (`rules/patterns.py`).

## ❌ Không đạt (fail) khi
text khớp mẫu `undefined|null|NaN|%s|%@|{{...}}|${...}`

## ✅ Đạt (pass) khi
text không khớp mẫu biến chưa render

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
