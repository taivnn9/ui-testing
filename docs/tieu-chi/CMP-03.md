# CMP-03 — Không tap được do bị đè

> **Nhóm:** UI Components & Controls — thành phần điều khiển (`CMP`)
> **Severity nền:** `critical` (range `high→critical`) · **Tags:** —
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
overlap + interactive

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: R1.

## ❌ Không đạt (fail) khi
element trên che control interactive

## ✅ Đạt (pass) khi
không bị che

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
