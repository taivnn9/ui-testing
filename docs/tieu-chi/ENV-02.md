# ENV-02 — Status/nav bar đè hoặc lẫn màu

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** mob
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`safe_area`, color

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1 + agent.

## ❌ Không đạt (fail) khi
nội dung đè status bar / lẫn màu

## ✅ Đạt (pass) khi
không đè

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
