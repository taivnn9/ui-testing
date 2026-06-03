# IMG-03 — Mờ / pixel hoá

> **Nhóm:** Images, Icons & Media — ảnh, icon, media (`IMG`)
> **Severity nền:** `medium` (range `low→medium`) · **Tags:** resp
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
A8 Laplacian + A7 upscale

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R3/A8.

## ❌ Không đạt (fail) khi
upscale (>1.5×) + blur dưới ngưỡng

## ✅ Đạt (pass) khi
nét

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
