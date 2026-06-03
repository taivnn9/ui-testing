# ENV-02 — Status/nav bar đè hoặc lẫn màu

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** mob
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`safe_area`, color

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R1 + agent

## ❌ Không đạt (fail) khi
nội dung đè status bar / lẫn màu

## ✅ Đạt (pass) khi
không đè

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
