# CNT-10 — Nội dung sai ngữ cảnh / nhầm dữ liệu user

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** ctx,multi
> **Trạng thái:** 🟥 Agent đánh giá (chưa có rule)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text` + ngữ cảnh màn

## Kỹ thuật & ai đánh giá
🟥 Agent Codex (phán đoán text-only) — (confidence thấp — cần intent)

## ❌ Không đạt (fail) khi
nội dung vô lý so với màn/intent

## ✅ Đạt (pass) khi
nội dung hợp lý

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
