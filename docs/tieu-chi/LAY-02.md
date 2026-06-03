# LAY-02 — Off-screen / cắt mép viewport

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** resp
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
bbox vs `viewport`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1 (F0.4 §8).

## ❌ Không đạt (fail) khi
bbox nằm ngoài viewport bất kỳ phía

## ✅ Đạt (pass) khi
nằm trong viewport

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
