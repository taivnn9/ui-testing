# ENV-04 — Bàn phím che input/submit

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** mob
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
(cần state bàn phím)

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

## ❌ Không đạt (fail) khi
input/submit bị bàn phím che

## ✅ Đạt (pass) khi
không che

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
