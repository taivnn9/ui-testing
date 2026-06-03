# Tài liệu dự án — Phân tích lỗi UI bằng AI

Thư mục `docs/` lưu lại toàn bộ phân tích & trao đổi của dự án (theo thứ tự thời gian).
Bản **quyết định kiến trúc gọn** dùng để tham chiếu nhanh: `../CLAUDE.md`.

> ⚠️ **Lưu ý thuật ngữ (2026-06-03):** tầng reasoning đã đổi từ **VLM** sang
> **coding-agent CLI headless (Codex), text-only** — xem [`F1.1-codex-cli-architecture.md`](F1.1-codex-cli-architecture.md).
> Trong các tài liệu cũ (rules/analyzers/agents), chữ **"VLM"** = **tầng agent reasoning** hiện tại;
> mọi đề cập "gửi ảnh cho model / llama.cpp / LLM_BASE_URL" đã **lỗi thời**.

| File | Nội dung |
|---|---|
| [`phan-tich-ban-dau.md`](phan-tich-ban-dau.md) | Phân tích mở đầu: tiêu chí đủ chưa, lấy dữ liệu gì & thế nào, tổ chức dữ liệu, cách prompt/Skill/Rule/workflow cho Agent. |
| [`../CLAUDE.md`](../CLAUDE.md) | Bản quyết định kiến trúc gọn (đọc tự động mỗi phiên): mục tiêu, schema chung, pipeline, bộ tiêu chí, checklist việc tiếp theo. |

**Hướng dẫn người dùng:**

| File | Nội dung |
|---|---|
| [`../SETUP.md`](../SETUP.md) | Cài đặt & chạy (file đọc đầu tiên). |
| [`cai-tesseract-windows.md`](cai-tesseract-windows.md) | Cài Tesseract OCR trên Windows (PATH, language data). |
| [`huong-dan-web-ui.md`](huong-dan-web-ui.md) | Cách dùng giao diện web: upload → phân tích → đọc overlay lỗi. |
| [`go-loi.md`](go-loi.md) | Đọc lỗi & phân biệt lỗi cấu hình vs lỗi code (DEBUG_ERRORS, agent_errors). |
| [`F2.0-web-ui.md`](F2.0-web-ui.md) | Thiết kế & kiến trúc Web UI (spec). |
| [`catalog-tieu-chi-loi-ui.md`](catalog-tieu-chi-loi-ui.md) | Liệt kê đầy đủ 121 tiêu chí lỗi UI (9 nhóm) + severity. |
| [`tieu-chi/`](tieu-chi/README.md) | **Tổng hợp + 1 file/tiêu chí: dữ liệu · kỹ thuật · đạt/không đạt · ai đánh giá** (sinh bởi `scripts/gen_criteria.py`). |
| [`F0.4-thresholds.md`](F0.4-thresholds.md) | Đơn vị & ngưỡng số chuẩn (touch target, contrast, blur, pHash...). |

> Phiên 2026-05-21. Trao đổi bằng tiếng Việt.
