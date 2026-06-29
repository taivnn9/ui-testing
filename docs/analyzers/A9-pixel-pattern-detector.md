# A9 — Pixel Pattern Detector (skeleton/spinner/overlay/keyboard/blank/broken)

> **TL;DR:** Phát hiện trạng thái macro của màn/vùng từ pixel (skeleton, spinner, overlay, keyboard, splash, broken-image, blank) — những thứ DOM không encode; output `pattern_detections[]`. Chỉ 1 frame → kết luận "kẹt" cần ≥2 frame (Phase 2).

> Phase 1, nhóm "đo diện mạo". Pixel là nguồn duy nhất.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (cấp vùng candidate) · [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) (xác nhận text thật vs placeholder) · [`A4-pixel-color-sampler.md`](A4-pixel-color-sampler.md) (màu/contrast) · [`A6`](A6-icon-graphic-detector.md) (icon broken)

## 1. Trách nhiệm
Phát hiện **trạng thái toàn màn hoặc từng vùng** chỉ từ pixel (DOM/XML không encode tường minh):

| Pattern | Biểu hiện pixel đặc trưng |
|---|---|
| **Skeleton loader** | Nhiều khối chữ nhật bo góc xám lặp lại, cùng màu, cách đều |
| **Spinner / loading** | Vùng tròn / cung tròn đối xứng — animation dừng 1 frame |
| **Loading overlay** | Lớp bán trong suốt lớn phủ toàn màn — giảm contrast toàn cục |
| **Bàn phím ảo** | Khối lưới nút chiếm phần lớn nửa dưới màn |
| **Splash screen kẹt** | Màn logo/loading bar chiếm toàn viewport |
| **Broken-image placeholder** | Icon ô vuông rách / dấu ? / icon ảnh lỗi |
| **Blank / empty screen** | Vùng lớn entropy/variance cực thấp |

> ⚠ **Giới hạn 1-frame:** một số STATE mang tính **thời gian** (skeleton kẹt bao lâu? overlay không tắt?). A9 chỉ phát hiện **sự hiện diện** pattern — kết luận "kẹt" cần ≥2 frame (Phase 2+). A9 đánh dấu `temporal=true` + `confidence` thấp hơn.

KHÔNG phân loại element thường (A3); KHÔNG đọc text (A5); KHÔNG đo contrast chữ (A4). A9 chuyên **macro-pattern của vùng**.

## 2. Input / Output
**Input:** PNG full + meta `viewport{w,h,dpr}`, `theme`. `elements[]` từ A3 (tùy chọn — lọc FP; A9 chạy độc lập được).

**Output:** `pattern_detections[]`:
```jsonc
{
  "pattern_type": "skeleton",       // skeleton | spinner | overlay | keyboard | splash | broken_image | blank
  "bbox": {"x":0,"y":0,"w":0,"h":0}, // null nếu toàn màn
  "confidence": 0.82,
  "temporal": false,                 // true nếu kết luận "kẹt" cần ≥2 frame
  "evidence": {
    "method": "rect_cluster",
    "block_count": 5,                // vd số skeleton block
    "mean_luminance": 0.18,          // cho blank/overlay
    "aspect_ratio": 1.0,             // cho spinner
    "coverage_ratio": 0.72           // tỉ lệ diện tích vùng/màn
  },
  "severity": "high",
  "rule_id": "A9-skeleton",
  "note": "skeleton detected — 'stuck' requires >=2 frames to confirm"
}
```
Cũng thêm `candidate_issues[]` liên kết `STATE-*` / `IMG-01`.

## 3. Bảy bài toán con
- a. Skeleton — nhóm rect xám lặp lại.
- b. Spinner — vùng tròn/cung tròn.
- c. Overlay — lớp mờ phủ rộng.
- d. Bàn phím — lưới phím nửa dưới.
- e. Splash — toàn màn logo/loading.
- f. Ảnh vỡ — icon placeholder ảnh vỡ.
- g. Màn trống — vùng entropy thấp.

## 4. Kỹ thuật / lib (Python)
| Việc | Lib / cách | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Đọc ảnh, crop, ops | **OpenCV + numpy + Pillow** | chuẩn, nhanh | — | ✅ core |
| Tìm rect bo góc | **OpenCV** `findContours` + `approxPolyDP` + `arc_length` vs `perimeter` (roundness) | không train | nhiễu design phức | ✅ skeleton/broken-image |
| Phân cụm vùng đều | **scipy `linkage` / sklearn `DBSCAN`** theo màu + vị trí + kích thước | detect nhóm skeleton | cần chọn epsilon | ✅ skeleton clustering |
| Tìm hình tròn / cung | **OpenCV `HoughCircles`** | spinner, progress | hay FP | ✅ spinner — + symmetry check |
| Đo entropy vùng | **numpy entropy** từ histogram (`-sum(p*log(p))`) | blank/overlay | — | ✅ |
| Variance luminance | **numpy var** trên L-channel | đơn giản, nhanh | — | ✅ |
| Bố cục bàn phím | Heuristic: vùng dưới nhiều `rect` nhỏ đều (lưới phím) + màu hệ thống | hợp keyboard iOS/Android | không bắt custom lạ | ✅ |
| Broken image icon | Template / **ORB/SIFT** match với vài icon broken chuẩn | detect icon hệ thống | cần template; không bắt custom | ✅ + heuristic shape |
| Shimmer/gradient lặp | **scipy `fft`** trục x — shimmer tần số đều → peak FFT | phát hiện animation frame | chỉ tốt khi shimmer rõ | ⚠ tùy chọn |

> ⚠ **`cv2.matchTemplate`** cho broken-image icon: nhanh, deterministic, không train. Cần tập template nhỏ (~5–10 icon broken Android/iOS/browser). KHÔNG phải YOLO/neural — template matching là CV tất định.

### 4.1 Skeleton detect
```
1. grayscale + blur nhẹ
2. threshold (Otsu) → binary
3. findContours → rect (approxPolyDP 4 điểm)
4. Lọc: aspect ratio 0.1–10, area > min_area
5. Roundness: 4π·area/perimeter² → > 0.7 = bo góc (skeleton-like)
6. Nhóm rect màu tương tự (Lab ΔE < 10), kích thước gần nhau
7. Nếu ≥ 3 rect đủ điều kiện, xếp hàng/cột → skeleton candidate
8. confidence = f(count, uniformity, layout_regularity)
```

### 4.2 Overlay detect
```
1. Tính luminance_mean + contrast_std
2. So baseline bình thường (luminance 0.3–0.7)
3. Vùng lớn (> 60% màn) luminance thấp + contrast giảm đột ngột → overlay candidate
4. Phía dưới overlay có nội dung (A3 elements)? → tăng confidence
```

### 4.3 Blank detect
```
1. Chia grid 8×8
2. Entropy từng ô = -sum(p * log2(p))
3. Blank vùng: entropy < ngưỡng (tune GS, đề xuất < 1.5 bit)
4. Blank toàn màn: >80% ô blank
```

## 5. Pipeline A9 (đề xuất)
1. **Tiền xử lý:** grayscale + bản Lab song song; resize max 1080px nếu lớn.
2. **Blank/Overlay toàn màn:** kiểm entropy + luminance trước (blank thì bỏ các bước sau).
3. **Skeleton:** nhóm rect đều (4.1).
4. **Spinner:** `HoughCircles` vùng trung tâm + symmetry check.
5. **Overlay:** luminance drop + contrast analysis (4.2).
6. **Keyboard:** vùng dưới (bottom 30–60%) → lưới rect đều + màu hệ thống.
7. **Broken-image:** vùng ảnh (A3 hoặc aspect ratio ảnh) → template match icon broken / heuristic "box trống nơi đáng có ảnh".
8. **Splash:** không có element thường + 1 ảnh lớn + logo centered.
9. **Tổng hợp:** dedup vùng chồng (merge bbox IoU > 0.5) → emit `pattern_detections[]`.
10. **`temporal=true`** cho skeleton/spinner/overlay.

## 6. Tiêu chí phục vụ
| Mã | Tiêu chí | Vai trò A9 |
|---|---|---|
| **STATE-01** | Skeleton / loading kẹt | ✅ detect skeleton; ⚠ `temporal=true` cho "kẹt" |
| **STATE-02** | Empty state trống trơn | ✅ blank region + thiếu text/ảnh |
| **STATE-03** | Error state (stack trace) | ⚠ phụ — regex là R4; A9 detect "text dày bất thường" |
| **STATE-04** | Render dở dang | ✅ skeleton + content mix bất thường |
| **STATE-06** | Spinner/overlay đè nội dung | ✅ overlay + spinner detect |
| **STATE-07** | Modal/toast kẹt | ⚠ overlay + bbox (A3) |
| **STATE-11** | Offline — màn trắng | ✅ blank screen detect |
| **IMG-01** | Ảnh vỡ / broken | ✅ broken-image placeholder detect |
| **IMG-05** | Thiếu ảnh (slot trống) | ✅ vùng ảnh rỗng (low-entropy) |
| **IMG-08** | Icon placeholder chưa load | ✅ hộp/dấu ? detect |
| **ENV-** | Bàn phím che input | ✅ keyboard detect nửa dưới |

## 7. Edge cases (BẮT BUỘC xử lý)
- **Skeleton CỐ Ý vs KẸT:** A9 chỉ báo "có skeleton" — KHÔNG phán "kẹt". `temporal=true` + `note="skeleton present — 'stuck' requires >=2 frames"`. Người dùng/agent định nghĩa test mới kết luận.
- **Dark-mode skeleton:** màu tối trên nền tối → Otsu fail. → adaptive threshold / normalize contrast trước.
- **List items thường nhầm skeleton:** card list đều nhau → nhầm. → Nếu có text OCR bên trong từng rect → KHÔNG skeleton. Cần A5 để lọc.
- **Custom keyboard (third-party):** bố cục khác → heuristic fail. → Confidence thấp hơn; `"keyboard_type": "custom?"`.
- **Spinner 1 frame vs progress bar:** progress bar là rect dài. → HoughCircles filter aspect tròn (~1.0 ±0.15); progress bar loại.
- **Ảnh product nền trắng hợp lệ:** dễ nhầm blank. → Blank chỉ kích hoạt khi TẤT CẢ vùng entropy thấp; có elements khác (text, nút) → không blank.
- **Shimmer 1 frame:** dừng frame tối → trông skeleton mờ; frame sáng → trông bình thường. → Confidence điều chỉnh theo brightness vùng.
- **Broken image theo browser/OS:** mỗi platform icon khác. Cần **template set** cho Chrome, Firefox, Safari, Android WebView, Android native, iOS (mục 8).

## 8. Open decisions (cần anh chốt)
- [ ] **Template set broken-image icon:** cần hỗ trợ platform nào? Đề xuất bắt đầu Chrome + Android + iOS (3 bộ), mở rộng sau.
- [ ] **Ngưỡng entropy blank:** đề xuất `< 1.5 bit` — tune GS (nền trắng hợp lệ vs blank thật).
- [ ] **Ngưỡng skeleton:** `≥ 3 rect đều` — có thể quá ít cho màn phức. Tune GS.
- [ ] **A9 có gate sau A3?** Đề xuất A9 **độc lập** (detect cả khi A3 fail); có A3 → lọc FP. Required-after-A3 hay song song?
- [ ] **Temporal context:** Phase 1 (1 ảnh) báo "pattern present"; Phase 2 (≥2 frame) nâng verdict "stuck/kẹt". Confirm thiết kế.

## 9. TDD outline
- 4 skeleton block (rect xám đều) → `pattern_type=skeleton`, `confidence > 0.7`.
- list cards thật (có text trong) → KHÔNG skeleton (loại FP).
- spinner (cung tròn) → `pattern_type=spinner`.
- màn trắng (entropy thấp) → `pattern_type=blank`.
- overlay mờ phủ toàn màn → `pattern_type=overlay`, `coverage_ratio > 0.8`.
- bàn phím Android/iOS nửa dưới → `pattern_type=keyboard`.
- broken-image icon (Chrome style) → `pattern_type=broken_image`.
- màn bình thường → `pattern_detections=[]`, không crash.
- skeleton → `temporal=true` + note "requires >=2 frames".
- dark-mode skeleton (màu tối) → detect được (không phụ thuộc absolute threshold).
- nền trắng product hợp lệ + có text/button → KHÔNG blank.
- mọi detection có `evidence` đầy đủ (method, bbox, confidence).

## Trạng thái: spec ✅ — chờ chốt mục 8 (template set platform + ngưỡng tune GS + scope A3 gate).
