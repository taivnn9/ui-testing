# TYP-03 — Chữ tràn/cắt cụt khỏi container

> **Nhóm:** Typography & Text Rendering — text trông thế nào (`TYP`)
> **Severity nền:** `medium` (range `trivial→critical`) · **Tags:** i18n,ctx
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`text_truncated`, bbox vs parent

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R4 + agent

## ❌ Không đạt (fail) khi
`text_truncated=true` không có '…' hoặc text cụt nghĩa

## ✅ Đạt (pass) khi
đủ chữ / ellipsis chủ ý

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
