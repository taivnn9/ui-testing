# A8 — Pixel/Glyph Inspector (tofu □ / mờ / emoji-box / banding)

> **TL;DR:** Phân tích pixel chữ (Laplacian, connected-components, uniformity) để **chốt** tofu/glyph thiếu/mờ/emoji-box/banding — A5 chỉ NGHI (`has_replacement`), A8 KHẲNG ĐỊNH; output `glyph_issues[]` + verdict.

> Phase 1, nhóm "đo diện mạo".
> Liên quan: [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) (cờ `has_replacement`) · [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (cấp crop) · [`A4-pixel-color-sampler.md`](A4-pixel-color-sampler.md)

## 1. Trách nhiệm
Phân tích **chất lượng render chữ ở mức pixel**:

| Loại lỗi | Biểu hiện pixel |
|---|---|
| **Tofu / glyph thiếu** | Hình chữ nhật đặc đều (□ ▯), biên cứng, không chi tiết nét |
| **Missing-glyph box** | Hộp viền (outline box) không fill — font trả `.notdef` |
| **Emoji thành ô vuông** | Vùng nhỏ đơn sắc nơi đáng có emoji màu |
| **Chữ mờ / răng cưa** | Laplacian variance thấp / edge không đều — render scale lẻ |
| **Banding / gradient vỡ** | Sọc ngang/dọc đột ngột trong vùng tô màu trơn |
| **Chữ đè chữ (partial)** | Edge density bất thường + OCR conf thấp |

**Phân định với A5:**

| | A5 OCR | A8 Glyph Inspector |
|---|---|---|
| Phương pháp | Đọc ký tự (pattern recognition) | Phân tích hình học/pixel của nét |
| Khi thấy □/`�` | Set `has_replacement=true` → **NGHI** | Xác nhận box tofu thật hay nét hợp lệ → **CHỐT** |
| Không tin | Tofu = OCR rỗng nhưng có pixel → A8 phân loại | Nhận dạng ký tự / nội dung |
| Output | `text_segments[]` + cờ | `glyph_issues[]` + confidence |

KHÔNG đọc nội dung text (A5); KHÔNG đo màu/contrast (A4); KHÔNG phát hiện placeholder text "undefined" (Rule R4).

## 2. Input / Output
**Input:**
- **Crop chữ** từ A5 (text segment) hoặc A3 (element `role=text`).
- `has_replacement` từ A5 (ưu tiên crop này).
- Meta: `dpr` (tính px/pt); `lang_hint` từ A5 nếu có.

**Output:** `glyph_issues[]` per crop:
```jsonc
{
  "element_id": "e12",          // hoặc text_segment_id
  "crop": "crops/e12.png",
  "issue_type": "tofu_box",     // tofu_box | outline_box | emoji_square | blur_jagged | banding | overlap_glyph
  "confidence": 0.88,
  "evidence": {
    "laplacian_var": 12.4,      // độ nét (thấp = mờ)
    "box_uniformity": 0.97,     // 1.0 = ô đặc tuyệt đối (tofu)
    "edge_regularity": 0.32,    // cạnh đều (tofu) vs chi tiết nét
    "color_variance": 3.1,      // thấp = đơn sắc = tofu/emoji-box
    "expected_script": "latin", // từ A5 lang_hint
    "bbox": {"x":0,"y":0,"w":0,"h":0}
  },
  "verdict": "confirmed",       // confirmed | likely | uncertain | rejected
  "rule_id": "A8-tofu"
}
```
Ghi vào `candidate_issues[]` khi `verdict = confirmed | likely`.

## 3. Ba bài toán con
- a. **Phát hiện tofu/glyph box** — hình chữ nhật đặc đều hoặc outline box không detail.
- b. **Đo độ nét / răng cưa** — chữ mờ do scale lẻ / anti-aliasing sai.
- c. **Phát hiện emoji-box / banding** — vùng đáng màu lại đơn sắc; vùng gradient có sọc.

## 4. Kỹ thuật / lib (Python)
| Việc | Lib / cách | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Đọc ảnh, crop | **Pillow + numpy** | chuẩn, nhanh | — | ✅ core |
| Laplacian variance (đo nét) | **OpenCV `Laplacian`** → `cv2.Laplacian(img, cv2.CV_64F).var()` | 1 dòng, chuẩn | ngưỡng tune theo dpr | ✅ **primary blur** |
| Connected components | **OpenCV `connectedComponentsWithStats`** | tách từng glyph | cần threshold trước | ✅ |
| Phát hiện tofu box | **numpy**: sau threshold → `shape_uniformity = filled_area/bbox_area` (gần 1 = đặc đều) | deterministic, nhanh | nhầm ô checked, icon solid | ✅ primary |
| Độ đều cạnh (edge regularity) | **OpenCV Canny** → đếm pixel cạnh / bbox (tofu cạnh ngoài đều, không nét trong) | — | cần tinh chỉnh kernel | ✅ bổ sung |
| Histogram màu | **numpy `np.histogram`** grayscale → variance thấp = đơn sắc | xác nhận tofu/emoji-box | — | ✅ |
| Phát hiện banding | **numpy** row/col mean → sọc đột ngột (std cục bộ cao) → banding | — | cần biết vùng đáng gradient | ✅ |
| Outline box (`.notdef`) | Morphological: erode → dilate → "lõi" biến mất → rỗng trong = outline box | — | cần threshold sạch | ✅ |
| Emoji-box | Vùng square nhỏ đơn sắc (< 3 màu trong 10×10px) nơi OCR trả `□`/`🟥` rỗng | — | nhầm icon đặc | ⚠ kết hợp A5 `has_replacement` |

> ⚠ A8 **KHÔNG dùng ML recognition** (đó là A5). Toàn bộ là CV tất định + heuristic hình học — bắt tofu bằng **hình dạng pixel**, không cần biết ký tự gì.

### 4.1 Thuật toán tofu detection
```
crop_gray = grayscale(crop)
_, thresh = cv2.threshold(crop_gray, 128, 255, OTSU)
components = connectedComponentsWithStats(thresh)
for each component cc (lọc min_area > 9px²):
    uniformity = cc.filled_area / cc.bbox_area
    edge_internal = count(Canny(crop=cc.bbox, low, high)) nội bộ cc
    if uniformity > 0.92 AND edge_internal < 3:
        → tofu box candidate (confidence tỉ lệ uniformity)
    elif is_outline_box(cc):  # erode–dilate check
        → outline_box candidate
```

### 4.2 Blur/jagged detection
```
lap_var = cv2.Laplacian(crop_gray, cv2.CV_64F).var()
# Ngưỡng tham khảo (tune theo dpr):
# dpr=1: blur nếu lap_var < 50
# dpr=2: blur nếu lap_var < 100
# dpr=3: blur nếu lap_var < 200
```
Kết hợp: cạnh chữ (Canny) `edge_irregularity` cao → răng cưa (jagged); thấp + lap_var thấp → mờ.

## 5. Pipeline A8 (đề xuất)
1. **Nhận crop** từ A5 (ưu tiên `has_replacement=true`) + A3 (element text).
2. **Tiền xử lý:** grayscale + normalize contrast (CLAHE nhẹ nếu tối); giữ bản màu cho banding/emoji.
3. **Tofu box:** pipeline mục 4.1 cho mỗi connected component đủ lớn.
4. **Blur/jagged:** Laplacian variance (4.2); Canny edge irregularity.
5. **Emoji-box:** nếu `has_replacement=true` và crop nhỏ (≤ 20×20px) → kiểm đơn sắc + outline.
6. **Banding:** phân tích row/col mean vùng gradient (nếu A4 đánh dấu).
7. **Gán `verdict`:** tổng hợp tín hiệu → `confirmed/likely/uncertain/rejected`; confidence tổng hợp.
8. **Emit** `glyph_issues[]` + cập nhật `candidate_issues[]`.

## 6. Tiêu chí phục vụ
| Mã | Tiêu chí | Vai trò A8 |
|---|---|---|
| **TYP-01** | Tofu / glyph thiếu (□ ▯) | ✅ **CHỐT** — A5 nghi, A8 khẳng định |
| **TYP-02** | Font fallback sai | ⚠ tín hiệu phụ — script sai với expected (lang_hint Latin nhưng pixel ra CJK-box) |
| **TYP-09** | Chữ mờ / vỡ / răng cưa | ✅ Laplacian variance + edge irregularity |
| **TYP-14** | Emoji/icon-font render sai | ✅ emoji-box detect (đơn sắc nơi đáng màu) |
| **STY-10** | Banding/gradient lỗi | ⚠ tín hiệu phụ từ row/col mean |

## 7. Edge cases (BẮT BUỘC xử lý)
- **Icon đặc nhầm tofu:** icon solid hợp lệ cũng là hình đặc. → Kiểm `role`: `role=icon` (A3/A6) → loại; `role=text` → tofu. Dùng `has_replacement` từ A5 làm gate.
- **Chữ nét mảnh (thin stroke):** Laplacian thấp dù nét đẹp. → Kết hợp chiều cao glyph: box cao + uniformity thấp → không tofu.
- **JPEG artifact:** nhiễu nâng Laplacian giả. → Pre-filter nhẹ (Gaussian blur σ=0.5) trước Laplacian → triệt artifact tần số cao.
- **Chữ rất nhỏ (< 8px cao):** component quá nhỏ → unreliable. Đặt `min_height_px = 8 * dpr`; nhỏ hơn → skip, confidence thấp.
- **Mixed script (Latin + CJK):** CJK box dễ nhầm tofu. → Dùng `expected_script` từ A5 `lang_hint` để loại FP.
- **Anti-aliasing subpixel (LCD):** pixel viền có fringe RGB → không phải banding. → Phát hiện mẫu fringe (màu viền lệch kênh) → loại khỏi banding check.

## 8. Open decisions (cần anh chốt)
- [ ] **Ngưỡng Laplacian variance** theo dpr — đề xuất 50/100/200 cho dpr 1/2/3 — tune GS trước khi lock.
- [ ] **Ngưỡng `box_uniformity`** tofu: đề xuất `> 0.92` — test ảnh icon đặc hợp lệ vs tofu thật để chọn.
- [ ] **Chạy A8 trên tất cả text-box hay chỉ khi `has_replacement=true`?** Đề xuất **chạy tất cả** (OCR fail silent). Trade-off: nhiều crop hơn → chậm hơn.
- [ ] **Banding detection:** cần A4 đánh dấu vùng "đáng gradient" hay A8 tự tìm? Đề xuất: A8 tự phân tích vùng có std row/col cao bất thường (không cần A4 gate).

## 9. TDD outline
- ô vuông đặc đồng nhất (U+25A1 rendered tofu) → `issue_type=tofu_box`, `verdict=confirmed`.
- icon solid hình vuông (hợp lệ) `role=icon` → không tạo issue.
- chữ sắc nét thường → `laplacian_var > 100`, không issue blur.
- chữ mờ (Gaussian blur σ=3) → `issue_type=blur_jagged`, verdict confirmed.
- crop nhỏ < 8px cao → không crash, confidence thấp, không verdict.
- emoji thành ô vuông đơn sắc (`has_replacement=true`) → `issue_type=emoji_square`.
- outline box (`.notdef`) → `issue_type=outline_box`.
- JPEG artifact crop → không FP blur (sau Gaussian pre-filter).
- `lang_hint="latin"`, pixel = CJK box → tofu confirmed confidence cao.
- mọi glyph_issue có `evidence` đầy đủ (laplacian_var, box_uniformity, bbox).

## Trạng thái: spec ✅ — chờ chốt mục 8 (ngưỡng Laplacian + scope chạy).
