# IMG-09 — Scale-mode sai

> **Nhóm:** Images, Icons & Media — ảnh, icon, media (`IMG`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** —
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`image_meta.scale_mode`

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: R3.

## ❌ Không đạt (fail) khi
cover↔contain gây méo/cắt

## ✅ Đạt (pass) khi
đúng scale mode

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
