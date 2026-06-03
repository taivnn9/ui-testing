# CNT-06 — Mojibake / entity thô

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R4 regex.

## ❌ Không đạt (fail) khi
chứa `Ã©|â€™|&amp;|&#39;` …

## ✅ Đạt (pass) khi
text mã hoá đúng

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
