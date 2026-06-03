# CMP-08 — Text nút / label bị cắt cụt

> **Nhóm:** UI Components & Controls — thành phần điều khiển (`CMP`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** i18n
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`text_truncated`

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R4 + agent

## ❌ Không đạt (fail) khi
label nút bị cắt

## ✅ Đạt (pass) khi
đủ chữ

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
