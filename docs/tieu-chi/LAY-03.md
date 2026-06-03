# LAY-03 — Tràn ra ngoài container cha

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
bbox child vs parent

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1 (OVERFLOW 4px) + agent.

## ❌ Không đạt (fail) khi
child vượt parent > 4px

## ✅ Đạt (pass) khi
trong parent

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
