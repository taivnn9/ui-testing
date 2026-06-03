# CNT-12 — Đơn vị/ký hiệu sai hoặc thiếu

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

## ❌ Không đạt (fail) khi
thiếu ký hiệu tiền tệ / sai đơn vị

## ✅ Đạt (pass) khi
đủ & đúng đơn vị

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
