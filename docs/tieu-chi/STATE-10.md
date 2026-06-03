# STATE-10 — Trạng thái không khớp dữ liệu

> **Nhóm:** State & Lifecycle — trạng thái màn (`STATE`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** ctx,multi
> **Trạng thái:** 🟥 Agent đánh giá (chưa có rule)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
badge vs list

## Kỹ thuật & ai đánh giá
🟥 Agent Codex (phán đoán text-only)

## ❌ Không đạt (fail) khi
badge '3' nhưng list rỗng

## ✅ Đạt (pass) khi
khớp dữ liệu

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
