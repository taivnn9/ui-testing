# LAY-04 — Lệch grid (không theo 8pt)

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `low` (range `trivial→medium`) · **Tags:** —
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
bbox

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: R1 (GRID_TOLERANCE 2px).

## ❌ Không đạt (fail) khi
abs(pos mod 8) > 2px

## ✅ Đạt (pass) khi
đúng grid 8pt

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
