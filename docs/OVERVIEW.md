# Tổng quan dự án — Phát hiện lỗi UI bằng AI

> **TL;DR:** API service nhận **1 ảnh chụp màn hình** (mobile/web) → trả **danh sách lỗi UI/UX**
> có `severity` + `confidence` + `evidence`. Hướng **zero-reference**: không cần design mẫu,
> không object detection (YOLO). Đọc file này là nắm toàn cảnh; cần chi tiết thì theo link.

## 1. Làm gì & nguyên tắc

- **Input:** chỉ 1 ảnh PNG (+ metadata tùy chọn). Không nhận DOM/XML.
- **Output:** danh sách lỗi có cấu trúc, mỗi lỗi kèm mức nghiêm trọng, độ tin cậy, bằng chứng (bbox/crop).
- **4 nguyên tắc cốt lõi:**
  1. **Tách tất định khỏi phán đoán** — cái gì code tính được (overlap, contrast, off-screen…) → **rule engine**; LLM chỉ xác nhận/bác + bắt lỗi cần ngữ cảnh + gán severity.
  2. **Reasoning chỉ nhận TEXT** — ảnh chỉ dùng ở tầng CV; pixel cần thiết (contrast, méo, font tofu) được CV tính thành số đưa vào JSON.
  3. **Vision-only** — element/geometry/style suy từ ảnh qua OCR + CV.
  4. **Precision-first** — false-positive là thứ giết hệ thống → ưu tiên đúng hơn nhiều.

## 2. Pipeline

```
Ảnh PNG
  → Vision Adapter (OCR + CV)  → schema chung (elements/relations…)   [ảnh CHỈ dùng ở đây]
  → Rule Engine (tất định)     → candidate_issues
  → Agent reasoning (Codex/Cline, TEXT-only) → confirm/reject + lỗi cần ngữ cảnh + severity
  → Verify/Critic (dedup + lọc) → API trả kết quả
```

| Tầng | Code | Tài liệu |
|---|---|---|
| Vision Adapter (A0, A3–A13) | `src/ui_defect/analyzers/` | [analyzers/](analyzers/) |
| Rule Engine (R1–R5) | `src/ui_defect/rules/` | [rules/](rules/README.md) |
| Agent reasoning | `src/ui_defect/agents/` (+ `skills/*.md`) | [F1.1](F1.1-codex-cli-architecture.md), [agents/](agents/S1-summary.md) |
| API + Web UI | `src/ui_defect/api/`, `web/` | [api-contract.md](api-contract.md), [F2.0](F2.0-web-ui.md) |

## 3. Bộ tiêu chí (121 / 9 nhóm)

Đầy đủ: [catalog-tieu-chi-loi-ui.md](catalog-tieu-chi-loi-ui.md) · từng tiêu chí: [tieu-chi/](tieu-chi/README.md).

| Mức phủ | Nghĩa | Số |
|---|---|---:|
| 🟦 rule | Tất định từ ảnh (CV/OCR/pixel) | 43 |
| 🟥 agent | Kiểm được từ ảnh nhưng cần agent lý luận | 52 |
| ⏳ chưa | Không kết luận được từ 1 ảnh tĩnh (cần nhiều màn/thiết bị/tương tác) | 26 |

→ **95/121 kiểm được từ 1 ảnh chụp**; 26 còn lại cần thứ ngoài 1 ảnh (consistency đa màn, responsive, animation, mẫu tham chiếu).

## 4. Trạng thái

- ✅ Vision adapter, rule engine, agent backend (Codex + Cline), API, Web UI, bộ chuẩn `standard_v1` ([F4.0](F4.0-standard-set.md)).
- ✅ Audit & vá false-positive rule engine ([F4.1](F4.1-fp-audit.md)) — ~730→68 FP/8 ảnh normal.
- ⏳ Đang dang dở: fix Cline `issue_type` mismatch (Windows); standard Tier-2 (ảnh thật).
- Checklist chi tiết & cập nhật mới nhất: **[../CLAUDE.md](../CLAUDE.md) §7**.

## 5. Đọc tiếp gì?

- **Mới vào / muốn chạy thử:** [../SETUP.md](../SETUP.md) → [huong-dan-su-dung.md](huong-dan-su-dung.md).
- **Hiểu schema dữ liệu / ngưỡng:** [F0.2](F0.2-canonical-schema.md), [F0.4](F0.4-thresholds.md).
- **Hiểu cách chấm precision/recall:** [F4.0](F4.0-standard-set.md).
- **Mục lục toàn bộ docs:** [README.md](README.md).
