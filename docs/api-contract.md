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

| Field | Type | Required | Mô tả |
|---|---|---|---|
| `screenshot` | `file` (PNG/JPG) | ✅ | Ảnh chụp màn hình |
| `platform` | `string` | ✅ | `android` \| `ios` \| `web` |
| `viewport_w` | `int` | ✅ | Chiều rộng viewport (device px) |
| `viewport_h` | `int` | ✅ | Chiều cao viewport (device px) |
| `dpr` | `float` | ❌ | Device pixel ratio (mặc định: 2.0) |
| `locale` | `string` | ❌ | vd `vi-VN`, `en-US` (mặc định: `en-US`) |
| `theme` | `string` | ❌ | `light` \| `dark` \| `system` (mặc định: `light`) |
| `font_scale` | `float` | ❌ | Trợ năng font scale (mặc định: 1.0) |
| `route` | `string` | ❌ | Tên màn / route để track (vd `checkout`) |
| `safe_area_top` | `int` | ❌ | Device px — override A13 (khuyến khích cấp) |
| `safe_area_bottom` | `int` | ❌ | Device px |
| `analyzers` | `string` (JSON array) | ❌ | Subset analyzers muốn chạy (mặc định: tất cả) |
| `agents` | `string` (JSON array) | ❌ | Subset agents muốn chạy (mặc định: tất cả) |
| `min_severity` | `string` | ❌ | Chỉ trả issue từ mức này trở lên (mặc định: `low`) |
| `min_confidence` | `float` | ❌ | Chỉ trả issue có confidence ≥ này (mặc định: 0.4) |

### 2.2 Ví dụ curl

```bash
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen_checkout.png" \
  -F "platform=ios" \
  -F "viewport_w=390" \
  -F "viewport_h=844" \
  -F "dpr=3" \
  -F "locale=vi-VN" \
  -F "theme=light" \
  -F "safe_area_top=59" \
  -F "safe_area_bottom=34" \
  -F "route=checkout"
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
    "by_severity": {
      "critical": 0, "high": 2, "medium": 2, "low": 1, "trivial": 0
    },
    "top_categories": ["STY", "LAY", "CNT"],
    "confidence_avg": 0.84,
    "analyzers_ran": ["A3", "A4", "A5", "A6", "A8", "A9", "A10", "A13"],
    "agents_ran": ["G1", "G3", "G4", "G6"],
    "pipeline_duration_ms": 4200
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
      "element": {
        "id": "e7",
        "role": "button",
        "bbox": {"x": 16, "y": 780, "w": 358, "h": 48},
        "text": "Thanh toán"
      },
      "evidence": {
        "measured_value": "contrast_ratio=2.8",
        "expected_value": ">= 4.5 (WCAG AA)",
        "crop": "http://localhost:8000/crops/scr_a1b2c3d4/e7.png",
        "description": "Nút 'Thanh toán' có contrast 2.8:1 — thấp hơn WCAG AA 4.5:1"
      },
      "description": "Nút CTA chính 'Thanh toán' có contrast màu chữ/nền 2.8:1, thấp hơn ngưỡng WCAG AA 4.5:1. User khó đọc trong điều kiện ánh sáng mạnh.",
      "sources": ["R2-STY01", "G3-confirmed"]
    },
    {
      "id": "iss_9e4c7f2a",
      "issue_type": "LAY-02",
      "title": "Nội dung bị cắt khỏi viewport",
      "severity": "high",
      "confidence": 0.88,
      "tags": [],
      "temporal": false,
      "element": {
        "id": "e12",
        "role": "button",
        "bbox": {"x": 300, "y": 400, "w": 120, "h": 44},
        "text": "Xem thêm"
      },
      "evidence": {
        "measured_value": "bbox.x+w=420 > viewport.w=390",
        "description": "Nút 'Xem thêm' bị cắt 30px ở mép phải viewport"
      },
      "description": "Nút 'Xem thêm' bị cắt 30px ở phía phải viewport — không nhìn thấy hoàn toàn.",
      "sources": ["R1-LAY02", "G4-confirmed"]
    }
  ],
  "marked_image_url": "http://localhost:8000/debug/scr_a1b2c3d4/marked.png"
}
```

---

## 4. Error responses

| HTTP | Khi nào | Body |
|---|---|---|
| `400` | File không phải ảnh hợp lệ | `{"error": "invalid_image", "detail": "..."}` |
| `400` | Thiếu field bắt buộc | `{"error": "missing_field", "detail": "platform required"}` |
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

## 6. Pipeline orchestration (FastAPI endpoint)

```python
@app.post("/analyze")
async def analyze(
    screenshot: UploadFile,
    platform: str = Form(...),
    viewport_w: int = Form(...),
    viewport_h: int = Form(...),
    dpr: float = Form(2.0),
    locale: str = Form("en-US"),
    theme: str = Form("light"),
    # ... other params
) -> AnalyzeResponse:
    
    # 1. Load ảnh
    img = load_image(screenshot.file)
    screen = build_screen(platform, viewport_w, viewport_h, dpr, locale, theme)
    
    # 2. A13 — Device metadata
    meta = resolve_metadata(img, screen, tester_meta)
    screen = apply_meta(screen, meta)
    
    # 3. Analyzers (parallel nếu có thể)
    a5_result = extract_text(img, screen.viewport)
    a3_result = detect_layout(img, screen.viewport, a5_result)
    # ... A4, A6, A8, A9, A10
    
    # 4. A0 — Normalize
    doc = normalize(screen, img_path, img.width, img.height, elements, issues)
    
    # 5. Rule Engine
    doc = run_rule_engine(doc)  # R1–R5
    
    # 6. Judgment Agents (parallel)
    findings = await run_agents_parallel(doc, img)  # G1–G6
    
    # 7. V1 Critic
    findings = run_critic(findings, doc)
    
    # 8. S1 Summary
    response = build_summary(findings, doc)
    
    return response
```

---

## 7. Performance targets (SLO đề xuất)

| Phần | Target | Ghi chú |
|---|---|---|
| Analyzers (A3–A13) | < 2s | CPU-only, không GPU |
| Rule Engine (R1–R5) | < 200ms | Pure Python, no ML |
| VLM Agents (G1–G6 parallel) | < 8s | Claude API, 6 parallel calls |
| V1 + S1 | < 1s | Mostly code |
| **Total E2E** | **< 12s** | Cho ảnh 390×844 |
| Concurrent requests | 5 | Giới hạn bởi VLM API rate limit |

---

## 8. Cấu hình môi trường

```bash
# .env
ANTHROPIC_API_KEY=sk-...
VLM_MODEL=claude-sonnet-4-6
MAX_IMAGE_SIZE_MB=10
CROPS_DIR=/tmp/ui_defect_crops
CROPS_TTL_HOURS=1
MIN_ELEMENT_CONFIDENCE=0.35
DEBUG=false
```

---

## Trạng thái: spec ✅ — chờ implement Phase 5 sau khi analyzer + rule + agent xong.
