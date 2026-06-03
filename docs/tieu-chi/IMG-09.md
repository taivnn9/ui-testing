# IMG-09 — Scale-mode sai

> **Nhóm:** Images, Icons & Media — ảnh, icon, media (`IMG`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`image_meta.scale_mode`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R3-IMG09 (`r3_image.check_scale_mode`): scale_mode='stretch'.

## ❌ Không đạt (fail) khi
scale_mode='stretch' (không giữ tỉ lệ)

## ✅ Đạt (pass) khi
fit/fill/none

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
