# CMP-01 — Touch target nhỏ

> **Nhóm:** UI Components & Controls — thành phần điều khiển (`CMP`)
> **Severity nền:** `high` (range `medium→high`) · **Tags:** a11y,mob
> **Trạng thái:** ✅ Có rule tất định
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`touch_target`, `interactive` (A12)

## Kỹ thuật & ai đánh giá
🟦 Rule tất định (code tính từ số/box/pixel) — R1 (F0.4 §2)

## ❌ Không đạt (fail) khi
interactive & target < 44pt iOS / 48dp Android

## ✅ Đạt (pass) khi
≥ ngưỡng

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
