# STATE-02 — Empty state trống trơn

> **Nhóm:** State & Lifecycle — trạng thái màn (`STATE`)
> **Severity nền:** `medium` (range `low→high`) · **Tags:** ctx
> **Trạng thái triển khai:** 🟥 Chỉ agent Codex (CHƯA có rule tất định)
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA/sets rồi chạy lại._

## Dữ liệu dùng để đánh giá
text + vùng trống

## Kỹ thuật & ai đánh giá
🟥 **Agent Codex** (text-only) — chưa có rule riêng, phán đoán từ JSON

## ❌ Không đạt (fail) khi
vùng trống không có thông báo empty

## ✅ Đạt (pass) khi
có empty message

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
