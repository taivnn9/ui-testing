# CMP-16 — Khoảng tap chồng nhau

> **Nhóm:** UI Components & Controls — thành phần điều khiển (`CMP`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** a11y,mob
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`relations.gap` interactive

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1 (TOUCH_GAP_MIN).

## ❌ Không đạt (fail) khi
2 control interactive < 8pt gap

## ✅ Đạt (pass) khi
≥ 8pt

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
