# STATE-11 — Offline / no-network không xử lý

> **Nhóm:** State & Lifecycle — trạng thái màn (`STATE`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** ctx
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
màn trắng / text

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

## ❌ Không đạt (fail) khi
màn trắng khi no-network

## ✅ Đạt (pass) khi
có xử lý offline

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
