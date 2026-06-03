# ENV-06 — Font-scale lớn làm vỡ layout

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** a11y,mob
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`font_scale` + overflow

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: R1 + agent.

## ❌ Không đạt (fail) khi
font_scale lớn gây tràn/cắt

## ✅ Đạt (pass) khi
ổn khi scale

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
