# CNT-05 — Text debug/nội bộ lòi

> **Nhóm:** Content & Semantics — nội dung text nói gì (`CNT`)
> **Severity nền:** `high` (range `medium→critical`) · **Tags:** —
> **Trạng thái:** ✅ Rule + agent xác nhận
>
> _Sinh tự động bởi `scripts/gen_criteria.py` — đừng sửa tay; sửa ở DATA rồi chạy lại._

## Dữ liệu dùng để đánh giá
`element.text`

## Kỹ thuật & ai đánh giá
🟦🟥 Rule fire candidate → Agent Codex xác nhận/bác — R4 regex + agent

## ❌ Không đạt (fail) khi
chứa `TODO|asdf|TEST|DO NOT SHIP` …

## ✅ Đạt (pass) khi
không có text debug

---
↩ [Về bảng tổng hợp](README.md) · Tiêu chí đầy đủ: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) · Ngưỡng: [`../F0.4-thresholds.md`](../F0.4-thresholds.md)
