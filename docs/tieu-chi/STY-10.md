# STY-10 — Gradient/shadow/blur lỗi render

> **Nhóm:** Color, Contrast & Visual Style — màu, tương phản, style (`STY`)
> **Severity nền:** `low` (range `trivial→medium`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
pixel/crop

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

## ❌ Không đạt (fail) khi
banding / viền cứng / bóng lệch

## ✅ Đạt (pass) khi
render mượt

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
