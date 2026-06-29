# Phase 5 — API Contract

> **TL;DR:** Request/response schema cho tester gọi service. Input: ảnh PNG (trường duy nhất bắt buộc); output: danh sách lỗi UI có cấu trúc. Tech: **FastAPI** + Pydantic v2.
>
> Trạng thái: ✅ implemented — `src/ui_defect/api/` (main.py + pipeline.py + schemas.py).

---

## 1. Endpoint

```
POST /analyze
Content-Type: multipart/form-data
```

## 2. Request — Form fields

| Field | Type | Required | Default | Mô tả |
|---|---|---|---|---|
| `screenshot` | file (PNG/JPG) | ✅ | — | Ảnh chụp màn hình — **trường duy nhất bắt buộc** |
| `platform` | string | ❌ | `android` | `android` \| `ios` \| `web` |
| `viewport_w` | int | ❌ | `img.width` | Tự lấy từ kích thước ảnh |
| `viewport_h` | int | ❌ | `img.height` | Tự lấy từ kích thước ảnh |
| `dpr` | float | ❌ | `1.0` | 1.0 nếu ảnh đã ở device px; 2.0/3.0 nếu retina |
| `theme` | string | ❌ | auto | Auto từ mean luminance; override: `light`\|`dark` |
| `locale` | string | ❌ | `en-US` | vd `vi-VN` — ảnh hưởng agent reasoning text |
| `font_scale` | float | ❌ | `1.0` | Trợ năng font scale |
| `route` | string | ❌ | `null` | Tên màn / route để tracking |
| `safe_area_top` | int | ❌ | A13 auto | Device px — override A13 inference |
| `safe_area_bottom` | int | ❌ | A13 auto | Device px |
| `min_severity` | string | ❌ | `low` | Filter: `critical`\|`high`\|`medium`\|`low`\|`trivial` |
| `min_confidence` | float | ❌ | `0.4` | Filter: chỉ trả issue ≥ ngưỡng |
| `agent_backend` | string | ❌ | `""` (env `AGENT_BACKEND`) | `codex` \| `cline` \| `none`. `none` = chỉ rule engine (nhanh). Trống = lấy theo env. |

### Ví dụ curl

```bash
# Tối giản — chỉ cần ảnh
curl -X POST http://localhost:8000/analyze -F "screenshot=@screen.png"

# Đầy đủ — iOS với safe_area cụ thể
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen_checkout.png" \
  -F "platform=ios" -F "dpr=3" -F "locale=vi-VN" \
  -F "safe_area_top=59" -F "safe_area_bottom=34" -F "route=checkout"

# Rule-only (không gọi agent — nhanh, để debug)
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen.png" -F "agent_backend=none"
```

---

## 3. Response (200 OK)

```json
{
  "screen_id": "scr_a1b2c3d4",
  "analyzed_at": "2026-05-29T10:30:00Z",
  "screen": {
    "platform": "ios",
    "viewport": {"w": 390, "h": 844, "dpr": 3.0},
    "locale": "vi-VN", "theme": "light", "route": "checkout"
  },
  "summary": {
    "total_issues": 5,
    "by_severity": { "critical": 0, "high": 2, "medium": 2, "low": 1, "trivial": 0 },
    "top_categories": ["STY", "LAY", "CNT"],
    "confidence_avg": 0.84
  },
  "issues": [
    {
      "id": "iss_3f7a2b1c",
      "issue_type": "STY-01",
      "title": "Contrast chữ/nền dưới WCAG AA",
      "severity": "high",
      "confidence": 0.93,
      "tags": ["a11y"],
      "temporal": false,
      "element_id": "e7",
      "element_role": "button",
      "element_bbox": {"x": 16, "y": 780, "w": 358, "h": 48},
      "element_text": "Thanh toán",
      "evidence": {
        "measured_value": "contrast_ratio=2.8",
        "expected_value": ">= 4.5 (WCAG AA)",
        "description": "Nút 'Thanh toán' có contrast 2.8:1 — thấp hơn WCAG AA 4.5:1"
      },
      "description": "Nút CTA chính 'Thanh toán' có contrast màu chữ/nền 2.8:1.",
      "sources": ["R2-STY01", "agent-confirmed"]
    }
  ],
  "pipeline_meta": {
    "analyzers_ran": ["A13","A5","A3","A6","A12","A4","A7","A8","A9","A10","A0"],
    "rules_ran": ["R1","R2","R3","R4"],
    "agents_ran": ["codex"],
    "total_candidates_pre_filter": 18,
    "final_issues": 5,
    "pipeline_duration_ms": 4200
  }
}
```

---

## 4. Error responses

| HTTP | Khi nào | Body |
|---|---|---|
| `400` | File không phải ảnh hợp lệ | `{"error": "invalid_image", "detail": "..."}` |
| `400` | platform/theme sai | `{"detail": "platform phải là android, ios hoặc web"}` |
| `413` | Ảnh quá lớn (> 10MB) | `{"error": "file_too_large"}` |
| `422` | Field không hợp lệ | Pydantic validation error |
| `500` | Pipeline lỗi nội bộ | `{"detail": {"error":"pipeline_failed","stage","type","message","traceback"}}` (khi `DEBUG_ERRORS=1`) |

> Lỗi tầng agent reasoning (Codex/Cline) **không** trả mã lỗi: pipeline degrade graceful → **HTTP 200**, lý do ở `pipeline_meta.agent_errors`. Xem [huong-dan-su-dung.md](huong-dan-su-dung.md) (mục 4).

---

## 5. Endpoint phụ

**GET /health** → `{"status": "ok", "version": "0.1.0"}`

**GET / và /static/\*** → Giao diện web (upload → phân tích → visualize). Xem [huong-dan-su-dung.md](huong-dan-su-dung.md) (mục 1).

> Set-of-Marks (vẽ ID lên ảnh) đã **bỏ** — tầng reasoning là agent CLI text-only, không nhận ảnh (xem [F1.1](F1.1-codex-cli-architecture.md)).

---

## 6. Pipeline orchestration

Xem `src/ui_defect/api/pipeline.py` — `run_pipeline()`. Thứ tự:

```
A13 → A5 → A3 → A6 → A12 → A4 → A7 → A8 → A9 → A10 → A0
  → R1–R4 → agent reasoning (text-only, 1 call) → V1 (critic) → S1 (summary)
```

---

## 7. Performance targets (SLO đề xuất)

| Phần | Target | Ghi chú |
|---|---|---|
| Analyzers (A3–A13) | < 2s | CPU-only |
| Rule Engine (R1–R5) | < 200ms | Pure Python |
| Agent reasoning (1 call, text-only) | ~10–18s | `codex exec` headless; phụ thuộc model/quota |
| V1 + S1 | < 1s | Mostly code |
| **Total E2E** | **~12–20s** (có agent) / **< 3s** (rule-only) | Ảnh 390×844 |
| Concurrent requests | tùy | Giới hạn bởi throughput/quota agent backend |

---

## 8. Cấu hình môi trường

```bash
# .env — tầng reasoning dùng coding-agent CLI headless (xem .env.example, docs/F1.1)
AGENT_BACKEND=codex             # codex | none(=rule-only)
CODEX_SANDBOX=workspace-write   # quyền đọc/ghi file project
CODEX_TIMEOUT_SEC=180
# CODEX_MODEL=                  # bỏ trống = mặc định codex
# OCR_BASE_URL=http://localhost:8081   # OCR remote (tùy chọn, xem ocr_service/)
OCR_TIMEOUT_SEC=60
MAX_IMAGE_SIZE_MB=10
DEBUG_ERRORS=1                  # 1=dev (trả traceback), 0=prod
```

> Codex CLI chạy local (đã `codex login`). OCR có thể tách máy qua `OCR_BASE_URL`. Không còn phụ thuộc llama.cpp/VLM.
