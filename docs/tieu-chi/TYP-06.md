# TYP-06 — Ngắt dòng xấu

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `low` (range `trivial→medium`) · **Tags:** —
> **Trạng thái:** 🟥 Agent đánh giá (chưa có rule)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`text`, bbox dòng

## Kỹ thuật & ai đánh giá
🟥 Agent Codex (phán đoán text-only) — (yếu)

## ❌ Không đạt (fail) khi
gãy giữa từ / 1 từ mồ côi / hyphenation lỗi

## ✅ Đạt (pass) khi
ngắt dòng ổn

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
