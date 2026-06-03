# CMP-08 — Text nút / label bị cắt cụt

> **Nhóm:** UI Components & Controls — thành phần điều khiển (`CMP`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`text_truncated`

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: R4 + agent.

## ❌ Không đạt (fail) khi
label nút bị cắt

## ✅ Đạt (pass) khi
đủ chữ

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
