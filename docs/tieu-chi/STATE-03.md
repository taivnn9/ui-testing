# STATE-03 — Error/stack trace lòi

> **Nhóm:** State & Lifecycle — trạng thái màn (`STATE`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R4 + agent

## ❌ Không đạt (fail) khi
text chứa stack trace / mã lỗi thô

## ✅ Đạt (pass) khi
không lộ lỗi thô

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
