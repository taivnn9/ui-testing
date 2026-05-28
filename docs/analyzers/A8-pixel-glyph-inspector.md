# A8 — Pixel/Glyph Inspector (tofu □ / mờ / emoji-box / banding)

> Bóc tách chi tiết. Phase 1, nhóm "đo diện mạo". **Mode B** chính + **Mode A bổ sung** (chốt
> cờ nghi từ A5). Đây là **bộ CHỐT tofu/glyph** — A5 OCR chỉ NGHI, A8 dùng pixel để KHẲNG ĐỊNH.
> Liên quan: [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) (cờ `has_replacement`) ·
> [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (cấp crop) ·
> [`A4-pixel-color-sampler.md`](A4-pixel-color-sampler.md) · [`A1-tree-parser.md`](A1-tree-parser.md) ·
> [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm

Phân tích **chất lượng render chữ ở mức pixel** để phát hiện:

| Loại lỗi | Biểu hiện pixel |
|---|---|
| **Tofu / glyph thiếu** | Hình chữ nhật đặc đều (□ ▯) với biên cứng, không có chi tiết nét |
| **Missing-glyph box** | Hộp viền (outline box) không màu fill bên trong — font trả `.notdef` |
| **Emoji thành ô vuông** | Vùng nhỏ đơn sắc nơi đáng có emoji màu sắc |
| **Chữ mờ / răng cưa** | Laplacian variance thấp / edge không đều — render scale lẻ |
| **Banding / gradient vỡ** | Sọc ngang/dọc đột ngột trong vùng tô màu trơn |
| **Chữ đè chữ (partial)** | Edge density bất thường + OCR conf thấp |

**Vai trò phân định rõ với A5:**

| | A5 OCR | A8 Glyph Inspector |
|---|---|---|
| Phương pháp | Đọc ký tự (pattern recognition) | Phân tích hình học/pixel của nét |
| Khi thấy □/`�` | Set `has_replacement=true` → **NGHI** | Xác nhận box là tofu thật hay nét chữ hợp lệ → **CHỐT** |
| Không tin cậy | Tofu = OCR trả rỗng nhưng có pixel → A8 sẽ phân loại | Nhận dạng ký tự / nội dung text |
| Output | `text_segments[]` + cờ | `glyph_issues[]` + confidence |

**KHÔNG** đọc nội dung text (A5); **KHÔNG** đo màu/contrast (A4); **KHÔNG** phát hiện placeholder
text kiểu "undefined" (Rule R4).

## 2. Input / Output

**Input:**
- **Crop chữ** từ A5 (text segment crop) hoặc A3 (element crop có `role=text`).
  Mode A: crop theo bbox của element từ A1.
  Mode B: crop theo text-box từ A5.
- `has_replacement` flag từ A5 (ưu tiên crop này — Mode B).
- `dom_text` từ A1 (Mode A) — để biết script loại nào đáng render.
- Meta: `dpr` (để tính px/pt), `font_family` nếu có (Mode A).

**Output:** `glyph_issues[]` per crop:

```jsonc
{
  "element_id": "e12",          // hoặc text_segment_id
  "crop": "crops/e12.png",      // crop đã dùng
  "issue_type": "tofu_box",     // tofu_box | outline_box | emoji_square | blur_jagged | banding | overlap_glyph
  "confidence": 0.88,           // 0–1
  "evidence": {
    "laplacian_var": 12.4,      // đo độ nét (thấp = mờ)
    "box_uniformity": 0.97,     // 1.0 = ô đặc tuyệt đối (tofu điển hình)
    "edge_regularity": 0.32,    // cạnh đều (tofu) vs chi tiết nét
    "color_variance": 3.1,      // variance màu trong crop (thấp = đơn sắc = tofu/emoji-box)
    "expected_script": "latin", // từ dom_text hoặc A5 lang_hint
    "bbox": {"x":0,"y":0,"w":0,"h":0}
  },
  "verdict": "confirmed",       // confirmed | likely | uncertain | rejected
  "rule_id": "A8-tofu"
}
```

Ghi vào `candidate_issues[]` khi `verdict = confirmed | likely`.

## 3. Ba bài toán con

a. **Phát hiện tofu/glyph box** — hình chữ nhật đặc đều hoặc outline box không detail.
b. **Đo độ nét / răng cưa** — chữ mờ do scale lẻ hoặc anti-aliasing sai.
c. **Phát hiện emoji-box / banding** — vùng đáng màu lại đơn sắc; vùng gradient có sọc.

## 4. Kỹ thuật / lib (Python) — list + đề xuất

| Việc | Lib / cách (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Đọc ảnh, crop | **Pillow + numpy** | chuẩn, nhanh | — | ✅ core |
| Laplacian variance (đo nét) | **OpenCV `Laplacian`** → `cv2.Laplacian(img, cv2.CV_64F).var()` | 1 dòng, chuẩn công nghiệp | ngưỡng cần tune theo dpr | ✅ **primary blur detect** |
| Connected components (hình học nét) | **OpenCV `connectedComponentsWithStats`** | phân tách từng glyph riêng | cần threshold trước | ✅ |
| Phát hiện tofu box | **numpy**: sau threshold → `shape_uniformity` = `filled_area / bbox_area` → gần 1 = đặc đều | deterministic, nhanh | nhầm với ô checked, icon solid | ✅ đề xuất primary |
| Độ đều cạnh (edge regularity) | **OpenCV Canny** → đếm pixel cạnh theo tỉ lệ bbox → tofu có cạnh ngoài đều, không có nét bên trong | — | cần tinh chỉnh kernel | ✅ bổ sung |
| Histogram màu | **numpy `np.histogram`** trên grayscale → variance thấp = đơn sắc | xác nhận tofu/emoji-box | — | ✅ |
| Phát hiện banding | **numpy** row/col mean → gradient dự kiến mịn → nếu có sọc đột ngột (std cục bộ cao) → banding | — | cần biết vùng đáng gradient | ✅ |
| Outline box (`.notdef`) | Morphological operations: erode → dilate → nếu "lõi" biến mất → rỗng bên trong = outline box | — | cần threshold sạch | ✅ |
| Emoji-box | Vùng square nhỏ đơn sắc (< 3 màu trong 10×10px) nơi OCR trả `□`/`🟥` rỗng | — | nhầm với icon đặc | ⚠ kết hợp với A5 `has_replacement` |

> ⚠ A8 **KHÔNG dùng ML recognition** (đó là A5). Toàn bộ là CV tất định + heuristic hình học.
> Mục tiêu: bắt tofu bằng **hình dạng pixel**, không cần biết ký tự gì.

### 4.1 Thuật toán tofu detection (đề xuất)

```
crop_gray = grayscale(crop)
_, thresh = cv2.threshold(crop_gray, 128, 255, OTSU)
components = connectedComponentsWithStats(thresh)
for each component cc (lọc theo min_area > 9px²):
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
# dpr=2: blur nếu lap_var < 100  (pixel dày hơn, nét phải sắc hơn)
# dpr=3: blur nếu lap_var < 200
```

Kết hợp: cạnh chữ (Canny) có `edge_irregularity` cao → răng cưa (jagged); thấp + lap_var thấp → mờ.

## 5. Pipeline A8 (đề xuất)

1. **Nhận danh sách crop** từ A5 (text_segment, ưu tiên `has_replacement=true`) + A3 (element text).
2. **Tiền xử lý:** grayscale + normalize contrast (CLAHE nhẹ nếu ảnh tối); giữ bản màu cho bộ banding/emoji.
3. **Bước 1 — Tofu box:** chạy pipeline mục 4.1 cho mỗi connected component đủ lớn.
4. **Bước 2 — Blur/jagged:** Laplacian variance theo mục 4.2; Canny edge irregularity.
5. **Bước 3 — Emoji-box:** nếu `has_replacement=true` và crop nhỏ (≤ 20×20px) → kiểm tra đơn sắc + outline.
6. **Bước 4 — Banding:** phân tích row/col mean của vùng gradient (nếu A4 đánh dấu vùng gradient).
7. **Gán `verdict`:** tổng hợp tín hiệu → `confirmed / likely / uncertain / rejected`; confidence tổng hợp.
8. **Emit** `glyph_issues[]` + cập nhật `candidate_issues[]`.

## 6. Ranh giới Mode A / Mode B

| | Mode A (có cây) | Mode B (chỉ ảnh) |
|---|---|---|
| Mục đích chính | **Chốt cờ nghi** từ A5 (`has_replacement`) + xác nhận render thực | Phát hiện tofu **độc lập** (không có DOM để đối chiếu) |
| Ưu điểm Mode A | Biết `dom_text` + `font_family` → biết script đáng render → loại false positive | — |
| Ưu điểm Mode B | Chạy trên mọi text → không miss | Không có context → nhiều false positive hơn |
| `source` | `"vision"` (pixel analysis) | `"vision"` |
| Confidence | Cao hơn (có DOM làm reference) | Thấp hơn — ghi rõ |

> ✅ **Luôn ghi `source="vision"`** vì A8 dùng pixel, kể cả Mode A.
> Mode A chỉ làm tăng confidence của verdict, không thay đổi nguồn.

## 7. Tiêu chí phục vụ

| Mã | Tiêu chí | Vai trò A8 |
|---|---|---|
| **TYP-01** | Tofu / glyph thiếu (□ ▯) | ✅ **CHỐT** — A5 nghi, A8 khẳng định |
| **TYP-02** | Font fallback sai | ⚠ tín hiệu phụ — nếu script sai với expected (dom_text Latin nhưng pixel ra CJK-box) |
| **TYP-09** | Chữ mờ / vỡ / răng cưa | ✅ Laplacian variance + edge irregularity |
| **TYP-14** | Emoji/icon-font render sai | ✅ emoji-box detect (đơn sắc nơi đáng màu) |
| **STY-10** | Banding/gradient lỗi | ⚠ tín hiệu phụ từ row/col mean analysis |

## 8. Edge cases (BẮT BUỘC xử lý)

- **Icon đặc (solid icon) nhầm tofu:** icon solid là hợp lệ — cũng là hình chữ nhật/tròn đặc.
  → Kiểm tra `role` element: nếu `role=icon` + `source=dom` → loại khỏi tofu check; nếu `role=text` → tofu.
  → Mode B không có role → dùng `has_replacement` từ A5 làm gate (chỉ check khi A5 đã nghi).
- **Chữ nét mảnh (thin stroke):** Laplacian variance thấp dù nét đẹp — chữ light-weight hợp lệ.
  → Kết hợp với `font_weight` (Mode A) hoặc chiều cao glyph: nếu box cao và uniformity thấp → không tofu.
- **Ảnh chất lượng thấp (JPEG artifact):** nhiễu ảnh nâng Laplacian giả → `lap_var` cao nhưng chữ vẫn mờ về ngữ nghĩa.
  → Pre-filter nhẹ (Gaussian blur σ=0.5) trước khi Laplacian → triệt artifact tần số cao.
- **Chữ rất nhỏ (< 8px chiều cao):** component quá nhỏ → unreliable. Đặt `min_height_px = 8 * dpr`;
  nhỏ hơn → skip A8, set confidence thấp.
- **Mixed script trên 1 dòng** (Latin + CJK): component checker chạy per-glyph → CJK box có thể
  nhầm tofu. → Dùng `expected_script` từ A5 để loại false positive.
- **Anti-aliasing subpixel (LCD rendering):** pixel viền có màu RGB offset (fringe) → không phải banding.
  → Phát hiện mẫu fringe (màu viền lệch kênh RGB) → loại trừ khỏi banding check.

## 9. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Ngưỡng Laplacian variance** theo từng dpr — đề xuất 50/100/200 cho dpr 1/2/3 — **tune bằng
  golden set (GS)** trước khi lock.
- [ ] **Ngưỡng `box_uniformity`** cho tofu detect: đề xuất `> 0.92` — cần test trên ảnh icon đặc
  hợp lệ vs tofu thật để chọn ngưỡng phân định.
- [ ] **Mode B: có chạy A8 trên tất cả text-box hay chỉ khi A5 set `has_replacement=true`?**
  Đề xuất: **chạy tất cả** — tofu không nhất thiết A5 phải nhận ra (OCR fail silent). Trade-off:
  nhiều crop hơn → chậm hơn. Anh quyết.
- [ ] **Banding detection:** cần A4 đánh dấu vùng "đáng gradient" trước hay A8 tự tìm? Đề xuất:
  A8 tự phân tích bất kỳ vùng nào có std row/col cao bất thường (không cần A4 gate).

## 10. TDD outline

- test: ảnh chứa ô vuông đặc đồng nhất (U+25A1 rendered tofu) → `issue_type=tofu_box`, `verdict=confirmed`.
- test: ảnh icon solid hình vuông (hợp lệ) với `role=icon` → không tạo issue.
- test: ảnh chữ sắc nét thường → `laplacian_var > 100`, không issue blur.
- test: ảnh chữ mờ (Gaussian blur σ=3 thêm vào) → `issue_type=blur_jagged`, verdict confirmed.
- test: crop nhỏ < 8px chiều cao → không crash, confidence thấp, không verdict.
- test: emoji thành ô vuông đơn sắc (A5 `has_replacement=true`) → `issue_type=emoji_square`.
- test: outline box (`.notdef` rendering) → `issue_type=outline_box`.
- test: JPEG artifact crop → không false positive blur (sau Gaussian pre-filter).
- test: Mode A — dom_text = "abc" (latin), pixel = CJK box → tofu confirmed với confidence cao.
- test: mọi glyph_issue đều có `evidence` đầy đủ (laplacian_var, box_uniformity, bbox).

## Trạng thái: spec ✅ — chờ chốt mục 9 (ngưỡng Laplacian + scope chạy Mode B).
