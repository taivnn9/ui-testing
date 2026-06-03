# ENV-06 — Font-scale lớn làm vỡ layout

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** a11y,mob
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`font_scale` + overflow

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R1 + agent

## ❌ Không đạt (fail) khi
font_scale lớn gây tràn/cắt

## ✅ Đạt (pass) khi
ổn khi scale

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
