# CNT-08 — Số/ngày/tiền sai định dạng locale

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái:** 🟥 Agent đánh giá (chưa có rule)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`, `locale`

## Kỹ thuật & ai đánh giá
🟥 Agent Codex (phán đoán text-only)

## ❌ Không đạt (fail) khi
epoch thô / `1234567.89` không format theo locale

## ✅ Đạt (pass) khi
đúng định dạng locale

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
