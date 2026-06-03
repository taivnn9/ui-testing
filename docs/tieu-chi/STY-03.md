# STY-03 — Dark-mode không đổi màu

> **Nhóm:** Color, Contrast & Visual Style — màu, tương phản, style (`STY`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** dark
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`color`, `screen.theme`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R2 + agent.

## ❌ Không đạt (fail) khi
theme=dark mà element màu sáng / không adapt

## ✅ Đạt (pass) khi
màu adapt theme

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
