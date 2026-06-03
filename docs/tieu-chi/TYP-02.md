# TYP-02 — Font chưa load / fallback sai

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `medium` (range `low→medium`) · **Tags:** —
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`style.font_family`

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

Ghi chú: (yếu).

## ❌ Không đạt (fail) khi
font_family đổi bất thường / mất font brand

## ✅ Đạt (pass) khi
font nhất quán

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
