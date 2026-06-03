# STY-03 — Dark-mode không đổi màu

> **Nhóm:** Color, Contrast & Visual Style — màu, tương phản, style (`STY`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** dark
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`color`, `screen.theme`

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R2 + agent

## ❌ Không đạt (fail) khi
theme=dark mà element màu sáng / không adapt

## ✅ Đạt (pass) khi
màu adapt theme

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
