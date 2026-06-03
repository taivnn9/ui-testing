# IMG-02 — Méo / sai tỉ lệ

> **Nhóm:** Images, Icons & Media — ảnh, icon, media (`IMG`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`image_meta` (A7)

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R3-IMG02 (`r3_image.check_distortion`): |disp_ratio−intr_ratio|/intr_ratio.

## ❌ Không đạt (fail) khi
lệch ratio > 5% (warn) / > 15% (error)

## ✅ Đạt (pass) khi
trong ngưỡng

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
