# Phase 5 — API Contract

> **Mục đích:** định nghĩa request/response schema cho tester gọi service.
> Input: ảnh PNG. Output: danh sách lỗi UI có cấu trúc.
>
> Tech: **FastAPI** + Pydantic v2. Endpoint tester dùng thực tế.

---

## 1. Endpoint

```
POST /analyze
Content-Type: multipart/form-data
```

---

## 2. Request

### 2.1 Form fields

| Field | Type | Required | Default | Mô tả |
|---|---|---|---|---|
| `screenshot` | `file` (PNG/JPG) | ✅ | — | Ảnh chụp màn hình — **trường duy nhất bắt buộc** |
| `platform` | `string` | ❌ | `android` | `android` \| `ios` \| `web` |
| `viewport_w` | `int` | ❌ | `img.width` | Tự lấy từ kích thước ảnh |
| `viewport_h` | `int` | ❌ | `img.height` | Tự lấy từ kích thước ảnh |
| `dpr` | `float` | ❌ | `1.0` | Để 1.0 nếu ảnh đã ở device px; 2.0/3.0 nếu retina |
| `theme` | `string` | ❌ | auto | Tự detect từ mean luminance; override: `light`\|`dark` |
| `locale` | `string` | ❌ | `en-US` | vd `vi-VN` — ảnh hưởng G1 text agent |
| `font_scale` | `float` | ❌ | `1.0` | Trợ năng font scale |
| `route` | `string` | ❌ | `null` | Tên màn / route để tracking |
| `safe_area_top` | `int` | ❌ | A13 auto | Device px — override A13 device inference |
| `safe_area_bottom` | `int` | ❌ | A13 auto | Device px |
| `min_severity` | `string` | ❌ | `low` | Filter output: `critical`\|`high`\|`medium`\|`low`\|`trivial` |
| `min_confidence` | `float` | ❌ | `0.4` | Filter output: chỉ trả issue ≥ ngưỡng này |
| `run_vlm` | `bool` | ❌ | `true` | `false` = chỉ rule engine, bỏ qua VLM agents (nhanh hơn) |

### 2.2 Ví dụ curl

```bash
# Tối giản — chỉ cần ảnh
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen.png"

# Đầy đủ — cho iOS với safe_area cụ thể
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen_checkout.png" \
  -F "platform=ios" \
  -F "dpr=3" \
  -F "locale=vi-VN" \
  -F "safe_area_top=59" \
  -F "safe_area_bottom=34" \
  -F "route=checkout"

# Rule-only (không gọi VLM — nhanh, dùng để debug)
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen.png" \
  -F "run_vlm=false"
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
    "locale": "vi-VN",
    "theme": "light",
    "route": "checkout"
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
      "element_id":   "e7",
      "element_role": "button",
      "element_bbox": {"x": 16, "y": 780, "w": 358, "h": 48},
      "element_text": "Thanh toán",
      "evidence": {
        "measured_value": "contrast_ratio=2.8",
        "expected_value": ">= 4.5 (WCAG AA)",
        "description": "Nút 'Thanh toán' có contrast 2.8:1 — thấp hơn WCAG AA 4.5:1"
      },
      "description": "Nút CTA chính 'Thanh toán' có contrast màu chữ/nền 2.8:1.",
      "sources": ["R2-STY01", "G3-confirmed"]
    }
  ],
  "pipeline_meta": {
    "analyzers_ran": ["A13","A5","A3","A6","A12","A4","A7","A8","A9","A10","A0"],
    "rules_ran": ["R1","R2","R3","R4"],
    "agents_ran": ["G1","G3","G4","G6"],
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
| `400` | Giá trị platform/theme sai | `{"detail": "platform phải là android, ios hoặc web"}` |
| `413` | Ảnh quá lớn (> 10MB) | `{"error": "file_too_large"}` |
| `422` | Giá trị field không hợp lệ | Pydantic validation error |
| `500` | Pipeline lỗi nội bộ | `{"error": "pipeline_failed", "detail": "..."}` |
| `503` | VLM API không khả dụng | `{"error": "vlm_unavailable"}` |

---

## 5. Endpoint phụ

### GET /health
```json
{"status": "ok", "version": "0.1.0"}
```

### GET /crops/{screen_id}/{element_id}.png
Trả crop ảnh của element (PNG). Dùng để tester verify evidence.
TTL: 1 giờ sau khi analyze.

### GET /debug/{screen_id}/marked.png
Ảnh SoM đầy đủ (tất cả element có label). Chỉ enable khi `DEBUG=true`.

---

## 6. Pipeline orchestration

Xem `src/ui_defect/api/pipeline.py` — `run_pipeline()`.

Thứ tự: A13 → A5 → A3 → A6 → A12 → A4 → A7 → A8 → A9 → A10 → A0 → R1–R4 → G1–G6 → V1 → S1.

---

## 7. Performance targets (SLO đề xuất)

| Phần | Target | Ghi chú |
|---|---|---|
| Analyzers (A3–A13) | < 2s | CPU-only, không GPU |
| Rule Engine (R1–R5) | < 200ms | Pure Python, no ML |
| VLM Agents (G1–G6 parallel) | < 8s | llama.cpp endpoint, 6 parallel calls |
| V1 + S1 | < 1s | Mostly code |
| **Total E2E** | **< 12s** | Cho ảnh 390×844 |
| Concurrent requests | 5 | Giới hạn bởi throughput llama.cpp server |

---

## 8. Cấu hình môi trường

```bash
# .env — VLM gọi qua llama.cpp OpenAI-compatible endpoint (xem .env.example)
LLM_BASE_URL=http://localhost:8080   # URL server llama.cpp
LLM_MODEL=gemma-4                     # tên model đang serve
LLM_API_KEY=none                      # api key nếu server yêu cầu, không thì "none"
LLM_TIMEOUT_SEC=120
MAX_IMAGE_SIZE_MB=10
DEBUG=false
```

---

## Trạng thái: ✅ implemented — `src/ui_defect/api/` (main.py + pipeline.py + schemas.py).
