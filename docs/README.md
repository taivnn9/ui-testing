# Tài liệu dự án — Phát hiện lỗi UI bằng AI

> **Bắt đầu ở đây:** [OVERVIEW.md](OVERVIEW.md) — 1 trang nắm toàn cảnh (dự án là gì · pipeline · tiêu chí · trạng thái).
> Quyết định kiến trúc gọn (đọc tự động mỗi phiên): [../CLAUDE.md](../CLAUDE.md).

`docs/` là **nguồn sự thật chi tiết** (tài liệu sống). Mục lục theo mục đích:

## 🚀 Bắt đầu & sử dụng
| File | Nội dung |
|---|---|
| [OVERVIEW.md](OVERVIEW.md) | Tổng quan toàn dự án — đọc đầu tiên. |
| [../SETUP.md](../SETUP.md) | Cài đặt & chạy. |
| [huong-dan-su-dung.md](huong-dan-su-dung.md) | Dùng web UI + API · cài Tesseract (Windows) · đọc & gỡ lỗi. |

## 🧱 Kiến trúc & thiết kế
| File | Nội dung |
|---|---|
| [F0.2-canonical-schema.md](F0.2-canonical-schema.md) | Schema dữ liệu chung (screen/elements/relations/candidate_issues). |
| [F0.4-thresholds.md](F0.4-thresholds.md) | Đơn vị & ngưỡng chuẩn (touch target, contrast, blur, pHash, grid…). |
| [F1.1-codex-cli-architecture.md](F1.1-codex-cli-architecture.md) | Tầng reasoning = coding-agent CLI (Codex/Cline), text-only. |
| [F2.0-web-ui.md](F2.0-web-ui.md) | Thiết kế & kiến trúc Web UI. |
| [api-contract.md](api-contract.md) | Hợp đồng API: request/response, error codes. |

## 🔍 Thành phần xử lý
| Thư mục | Nội dung |
|---|---|
| [analyzers/](analyzers/A3-box-layout-detector.md) | Vision adapter A0, A3–A13 (CV + OCR + pixel). |
| [rules/](rules/README.md) | Rule engine R1–R5 (geometry, color, image, text, severity). |
| [agents/](agents/S1-summary.md) | Tầng agent: S1 summary, V1 critic. |

## 📋 Bộ tiêu chí lỗi UI (121 / 9 nhóm)
| File | Nội dung |
|---|---|
| [catalog-tieu-chi-loi-ui.md](catalog-tieu-chi-loi-ui.md) | Danh sách đầy đủ 121 tiêu chí + severity. |
| [tieu-chi/](tieu-chi/README.md) | 1 file/tiêu chí: dữ liệu · kỹ thuật · đạt/không đạt · ai đánh giá (sinh bởi `scripts/gen_criteria.py`). |

## ✅ Đo lường & chất lượng
| File | Nội dung |
|---|---|
| [F4.0-standard-set.md](F4.0-standard-set.md) | Bộ chuẩn `standard_v1` + đo precision/recall (kiểm thử đột biến). |
| [F4.1-fp-audit.md](F4.1-fp-audit.md) | Audit & xử lý false-positive rule engine trên ảnh thật. |

## 🗄️ Lịch sử
| File | Nội dung |
|---|---|
| [phan-tich-ban-dau.md](phan-tich-ban-dau.md) | Phân tích mở đầu (tài liệu lịch sử). |

> Trao đổi bằng tiếng Việt. Thuật ngữ "VLM" trong tài liệu cũ = tầng **agent reasoning (Codex/Cline)** hiện tại.
