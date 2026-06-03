# CNT-03 — Sai/lẫn ngôn ngữ

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`, `screen.locale`

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

## ❌ Không đạt (fail) khi
ngôn ngữ của text ≠ `locale` màn hình

## ✅ Đạt (pass) khi
text đúng ngôn ngữ locale

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
