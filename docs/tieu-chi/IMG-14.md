# IMG-14 — Ảnh load dở (progressive kẹt)

> **Nhóm:** Images, Icons & Media — ảnh, icon, media (`IMG`)
> **Severity nền:** `medium` (range `low→medium`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
A9 (vùng dở)

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

## ❌ Không đạt (fail) khi
ảnh chỉ load 1 phần / progressive kẹt

## ✅ Đạt (pass) khi
load đủ

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
