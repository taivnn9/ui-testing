# LAY-04 — Lệch grid (không theo 8pt)

> **Nhóm:** Layout & Spatial Geometry — bố cục, hình học (`LAY`)
> **Severity nền:** `low` (range `trivial→medium`) · **Tags:** —
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
bbox

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1-LAY04 (`r1_geometry.check_grid_alignment`): bbox lệch lưới 8×dpr > GRID_TOLERANCE.

## ❌ Không đạt (fail) khi
cạnh trái/trên lệch lưới 8pt > 2px (rõ ràng)

## ✅ Đạt (pass) khi
bám lưới 8pt

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
