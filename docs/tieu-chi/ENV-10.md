# ENV-10 — Asset không đúng mật độ (@1x)

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `low` (range `trivial→medium`) · **Tags:** mob
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`image_meta` + dpr

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: R3 (upscale).

## ❌ Không đạt (fail) khi
@1x trên màn @3x → mờ

## ✅ Đạt (pass) khi
đúng @Nx

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
