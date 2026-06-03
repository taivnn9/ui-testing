# LAY-01 — Overlap / va chạm phần tử vô lý

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`relations` iou

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1 + agent.

## ❌ Không đạt (fail) khi
iou > OVERLAP_IOU_MIN (0.05) không chủ ý

## ✅ Đạt (pass) khi
không chồng / chủ ý

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
