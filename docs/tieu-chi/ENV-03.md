# ENV-03 — Home indicator (iOS) đè nút

> **Nhóm:** Platform & Environment — nền tảng, môi trường (`ENV`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** mob
> **Trạng thái triển khai:** ✅ Đã implement (rule/analyzer tất định + agent xác nhận)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
`safe_area.bottom`

## Kỹ thuật & ai đánh giá
🟦 **Rule tất định** (code emit candidate) → 🟥 agent Codex xác nhận/bác

Chi tiết kỹ thuật: R1.

## ❌ Không đạt (fail) khi
nút chạm vùng home indicator

## ✅ Đạt (pass) khi
trên vùng

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
