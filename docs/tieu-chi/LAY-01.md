# LAY-01 — Overlap / va chạm phần tử vô lý

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`relations` iou

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R1 + agent

## ❌ Không đạt (fail) khi
iou > OVERLAP_IOU_MIN (0.05) không chủ ý

## ✅ Đạt (pass) khi
không chồng / chủ ý

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
