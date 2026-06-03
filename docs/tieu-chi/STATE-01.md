# STATE-01 — Skeleton / loading kẹt

> **Nhóm:** State & Lifecycle — trạng thái màn (`STATE`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái:** 🟥 Agent đánh giá (chưa có rule)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
role skeleton

## Kỹ thuật & ai đánh giá
🟥 Agent Codex (phán đoán text-only) — (temporal=true)

## ❌ Không đạt (fail) khi
có skeleton/shimmer (báo, đánh temporal)

## ✅ Đạt (pass) khi
không có skeleton

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
