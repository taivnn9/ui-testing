# CNT-11 — Text trùng lặp / mâu thuẫn

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** ctx
> **Trạng thái:** 🟥 Agent đánh giá (chưa có rule)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
toàn bộ `text` các element

## Kỹ thuật & ai đánh giá
🟥 Agent Codex (phán đoán text-only)

## ❌ Không đạt (fail) khi
cùng giá trị hiển thị khác nhau ở 2 chỗ

## ✅ Đạt (pass) khi
nhất quán

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
