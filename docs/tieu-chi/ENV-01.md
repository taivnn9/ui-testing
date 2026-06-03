# ENV-01 — Safe-area / notch che nội dung

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** mob
> **Trạng thái:** ✅ Có rule tất định
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`safe_area` (A13), bbox

## Kỹ thuật & ai đánh giá
🟦 Rule tất định (code tính từ số/box/pixel) — R1 (F0.4 §8)

## ❌ Không đạt (fail) khi
bbox trong vùng notch/status/home indicator

## ✅ Đạt (pass) khi
ngoài vùng safe-area

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
