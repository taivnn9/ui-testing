# A9 — Pixel Pattern Detector (skeleton/spinner/overlay/keyboard/blank/broken)

> Bóc tách chi tiết. Phase 1, nhóm "đo diện mạo". Pixel là nguồn duy nhất.
> Phát hiện **trạng thái đặc biệt của màn/vùng từ mẫu pixel** — không cần DOM.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (cấp vùng candidate) ·
> [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) (xác nhận/loại text thật vs placeholder) ·
> [`A4-pixel-color-sampler.md`](A4-pixel-color-sampler.md) (màu/contrast vùng) ·
> [`A6`](A6-icon-graphic-detector.md) (icon broken)

## 1. Trách nhiệm

Phát hiện **trạng thái toàn màn hoặc từng vùng** chỉ từ pixel — những trạng thái mà DOM/XML
KHÔNG encode tường minh:

| Pattern | Biểu hiện pixel đặc trưng |
|---|---|
| **Skeleton loader** | Nhiều khối chữ nhật bo góc xám lặp lại, cùng màu, cách đều |
| **Spinner / loading** | Vùng tròn hoặc cung tròn đối xứng — animation dừng ở 1 frame |
| **Loading overlay** | Lớp bán trong suốt lớn phủ toàn màn — giảm độ tương phản toàn cục |
| **Bàn phím ảo** | Khối lưới nút chiếm phần lớn nửa dưới màn — nhìn thấy từ ảnh |
| **Splash screen kẹt** | Màn logo/loading bar chiếm toàn bộ viewport |
| **Broken-image placeholder** | Icon ô vuông rách / dấu ? / icon ảnh lỗi đặc trưng |
| **Blank / empty screen** | Vùng lớn entropy/variance cực thấp, không có nội dung |

> ⚠ **Giới hạn 1-frame:** Một số STATE mang tính **thời gian** (skeleton kẹt bao lâu? overlay
> không tắt?). A9 chỉ phát hiện **sự hiện diện** của pattern — kết luận "kẹt" cần ≥2 frame
> (Phase 2+). A9 đánh dấu `temporal=true` và `confidence` thấp hơn cho các trường hợp này.

**KHÔNG** phân loại element thông thường (A3); **KHÔNG** đọc text (A5); **KHÔNG** đo màu
contrast của chữ (A4). A9 chuyên về **macro-pattern của vùng**.

## 2. Input / Output

**Input:**
- PNG full màn + meta `viewport{w,h,dpr}`, `theme`.
- `elements[]` từ A3 (tùy chọn — dùng để loại false positive; A9 hoạt động độc lập nếu cần).

**Output:** `pattern_detections[]`:

```jsonc
{
  "pattern_type": "skeleton",       // skeleton | spinner | overlay | keyboard | splash | broken_image | blank
  "bbox": {"x":0,"y":0,"w":0,"h":0}, // vùng phát hiện (null nếu toàn màn)
  "confidence": 0.82,
  "temporal": false,                 // true nếu kết luận "kẹt" cần ≥2 frame
  "evidence": {
    "method": "rect_cluster",        // method dùng để detect
    "block_count": 5,                // vd: số skeleton block
    "mean_luminance": 0.18,          // cho blank/overlay
    "aspect_ratio": 1.0,             // cho spinner
    "coverage_ratio": 0.72           // tỉ lệ diện tích vùng/màn
  },
  "severity": "high",               // nền rule: STATE severity
  "rule_id": "A9-skeleton",
  "note": "skeleton detected — 'stuck' requires >=2 frames to confirm"
}
```

Cũng thêm `candidate_issues[]` liên kết tới `STATE-*` / `IMG-01` tương ứng.

## 3. Bảy bài toán con

a. **Phát hiện skeleton** — nhóm rect xám lặp lại.
b. **Phát hiện spinner** — vùng tròn/cung tròn.
c. **Phát hiện overlay** — lớp mờ phủ rộng.
d. **Phát hiện bàn phím** — lưới phím nửa dưới.
e. **Phát hiện splash** — toàn màn logo/loading.
f. **Phát hiện ảnh vỡ** — icon placeholder ảnh vỡ.
g. **Phát hiện màn trống** — vùng entropy thấp.

## 4. Kỹ thuật / lib (Python) — list + đề xuất

| Việc | Lib / cách (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Đọc ảnh, crop, ops cơ bản | **OpenCV + numpy + Pillow** | chuẩn, nhanh | — | ✅ core |
| Tìm vùng hình chữ nhật bo góc | **OpenCV** `findContours` + `approxPolyDP` + check `arc_length` vs `perimeter` (roundness metric) | không train | nhiễu với design phức | ✅ skeleton/broken-image |
| Phân cụm vùng đều nhau | **scipy `linkage` / sklearn `DBSCAN`** theo màu + vị trí + kích thước | detect nhóm skeleton | cần chọn epsilon | ✅ skeleton clustering |
| Phát hiện hình tròn / cung tròn | **OpenCV `HoughCircles`** | phát hiện spinner, progress | hay false positive | ✅ spinner — kết hợp với symmetry check |
| Đo entropy vùng | **numpy entropy** từ histogram (`-sum(p*log(p))`) | blank / overlay detect | — | ✅ blank + overlay |
| Variance luminance | **numpy var** trên L-channel (PIL → grayscale) | đơn giản, nhanh | — | ✅ |
| Phát hiện bố cục bàn phím | Heuristic: vùng dưới màn có nhiều `rect` nhỏ đều nhau (lưới phím) + màu hệ thống (trắng/xám) | phù hợp keyboard iOS/Android | không bắt custom keyboard lạ | ✅ |
| Broken image icon | Template-based hoặc **ORB/SIFT feature match** với vài icon broken tiêu chuẩn | detect icon hệ thống | cần template nhỏ; không bắt custom | ✅ kết hợp với heuristic shape |
| Shimmer/gradient lặp | **scipy `fft`** theo trục x — skeleton shimmer có tần số đều → peak trong FFT | phát hiện animation frame | chỉ tốt khi shimmer rõ | ⚠ tùy chọn |

> ⚠ **Template matching `cv2.matchTemplate`** cho broken-image icon: nhanh, deterministic, không
> train. Cần duy trì tập template nhỏ (~5–10 icon broken tiêu chuẩn Android/iOS/browser).
> Đây KHÔNG phải YOLO/neural — template matching là CV tất định.

### 4.1 Skeleton detect — thuật toán đề xuất

```
1. Chuyển sang grayscale + blur nhẹ
2. threshold (Otsu) → binary
3. findContours → lấy hình chữ nhật (approxPolyDP 4 điểm)
4. Lọc theo: aspect ratio hợp lệ (0.1–10), area > min_area
5. Tính roundness: 4π·area/perimeter² → nếu > 0.7 = bo góc (skeleton-like)
6. Nhóm các rect có màu tương tự (Lab ΔE < 10), kích thước gần nhau
7. Nếu ≥ 3 rect đủ điều kiện, xếp thành hàng/cột → skeleton candidate
8. confidence = f(count, uniformity, layout_regularity)
```

### 4.2 Overlay detect — thuật toán đề xuất

```
1. Tính luminance_mean và contrast_std của ảnh
2. So sánh với baseline bình thường (luminance 0.3–0.7)
3. Nếu có vùng lớn (> 60% màn) có luminance thấp + độ tương phản giảm đột ngột
   → overlay candidate
4. Kiểm tra: phía dưới overlay có nội dung (A3 elements) không? → tăng confidence
```

### 4.3 Blank detect — thuật toán đề xuất

```
1. Chia ảnh thành grid (vd 8×8)
2. Tính entropy từng ô = -sum(p * log2(p)) với p = histogram normalize
3. Blank vùng: entropy < ngưỡng thấp (tune GS, đề xuất < 1.5 bit)
4. Blank toàn màn: >80% ô blank
```

## 5. Pipeline A9 (đề xuất)

1. **Tiền xử lý:** grayscale + bản màu Lab giữ song song; resize về max 1080px nếu ảnh lớn.
2. **Bước 1 — Blank/Overlay toàn màn:** kiểm tra entropy + luminance toàn ảnh trước (nếu blank thì
   các bước sau không cần chạy).
3. **Bước 2 — Skeleton detect:** tìm nhóm rect đều nhau (mục 4.1) → phát hiện vùng skeleton.
4. **Bước 3 — Spinner detect:** `HoughCircles` vùng trung tâm + symmetry check → spinner/progress.
5. **Bước 4 — Overlay detect:** luminance drop + contrast analysis (mục 4.2) → overlay region.
6. **Bước 5 — Keyboard detect:** vùng dưới màn (bottom 30–60%) → lưới rect đều + màu hệ thống.
7. **Bước 6 — Broken-image detect:** tìm vùng ảnh (từ A3 hoặc area có aspect ratio ảnh) →
   template match icon broken / heuristic "box trống nơi đáng có ảnh".
8. **Bước 7 — Splash detect:** không có element thông thường + 1 ảnh lớn + logo centered.
9. **Tổng hợp:** dedup vùng chồng lấn (merge bbox IoU > 0.5) → emit `pattern_detections[]`.
10. **Đánh dấu `temporal=true`** cho skeleton/spinner/overlay (cần ≥2 frame để kết luận "kẹt").

## 6. Tiêu chí phục vụ

| Mã | Tiêu chí | Vai trò A9 |
|---|---|---|
| **STATE-01** | Skeleton / loading kẹt | ✅ detect skeleton pattern; ⚠ `temporal=true` cho "kẹt" |
| **STATE-02** | Empty state trống trơn | ✅ blank region detect + thiếu text/ảnh |
| **STATE-03** | Error state (stack trace) | ⚠ tín hiệu phụ — text regex là R4; A9 detect "screen có nhiều text dày không bình thường" |
| **STATE-04** | Render dở dang | ✅ tín hiệu từ skeleton + content mix bất thường |
| **STATE-06** | Spinner/overlay đè nội dung | ✅ overlay detect + spinner detect |
| **STATE-07** | Modal/toast kẹt | ⚠ tín hiệu từ overlay + bbox (A3) |
| **STATE-11** | Offline — màn trắng | ✅ blank screen detect |
| **IMG-01** | Ảnh vỡ / broken | ✅ broken-image placeholder detect |
| **IMG-05** | Thiếu ảnh (slot trống) | ✅ vùng ảnh rỗng (low-entropy) nơi đáng có ảnh |
| **IMG-08** | Icon placeholder chưa load | ✅ hộp/dấu ? detect |
| **ENV-** | Bàn phím che input | ✅ keyboard detect nửa dưới màn |

## 7. Edge cases (BẮT BUỘC xử lý)

- **Skeleton CỐ Ý vs KẸT:** A9 chỉ báo "có skeleton" — KHÔNG phán "kẹt". Đánh dấu
  `temporal=true` + `note="skeleton present — 'stuck' requires >=2 frames"`. Người dùng / agent
  định nghĩa test (có timeout hay không) mới kết luận kẹt.
- **Dark-mode skeleton:** màu skeleton tối (dark gray) trên nền tối → threshold Otsu có thể fail.
  → Dùng adaptive threshold hoặc normalize contrast trước khi detect.
- **List items bình thường nhầm skeleton:** card list đều nhau (cùng kích thước, cùng màu) →
  nhầm skeleton. → Kiểm tra: nếu có text OCR bên trong từng rect → KHÔNG phải skeleton
  (nội dung thật). Cần gọi A5 kết quả để lọc.
- **Custom keyboard (third-party):** bàn phím bố cục khác hệ thống → heuristic keyboard fail.
  → Confidence thấp hơn; đánh dấu `"keyboard_type": "custom?"`.
- **Spinner 1 frame vs progress bar:** progress bar cũng là hình chữ nhật dài — không phải spinner.
  → HoughCircles filter aspect ratio tròn (aspect ~1.0 ±0.15); progress bar loại.
- **Ảnh product toàn trắng / nền trắng hợp lệ:** product photography trên nền trắng → nhầm blank.
  → Blank detect chỉ kích hoạt khi TẤT CẢ vùng ảnh entropy thấp; nếu có elements khác (text, nút) xung quanh → không blank.
- **Shimmer chỉ có ở 1 frame:** skeleton shimmer animation dừng ở frame tối → trông như skeleton mờ.
  Dừng ở frame sáng → trông bình thường. → Confidence skeleton được điều chỉnh theo brightness của vùng.
- **Broken image phụ thuộc browser/OS:** mỗi platform có icon broken khác nhau. Cần **template set** cho: Chrome, Firefox, Safari, Android WebView, Android native, iOS. → Mục open decision (mục 8).

## 8. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Template set broken-image icon:** cần anh xác nhận cần hỗ trợ platform nào (Chrome/Firefox/Android/iOS native) để chuẩn bị đúng template. Đề xuất: bắt đầu với Chrome + Android + iOS (3 bộ), mở rộng sau.
- [ ] **Ngưỡng entropy blank:** đề xuất `< 1.5 bit` — **tune bằng standard set (GS)** (ảnh nền trắng hợp lệ vs màn thật blank).
- [ ] **Ngưỡng skeleton:** `≥ 3 rect đều` — có thể quá ít cho màn phức tạp. Tune GS.
- [ ] **A9 có gate sau A3 không?** Đề xuất: A9 **độc lập** (không cần A3) để detect ngay cả khi A3 fail. Nhưng nếu có A3 → dùng để lọc false positive. Anh muốn A9 required-after-A3 hay song song?
- [ ] **Temporal context:** Phase 1 chỉ 1 ảnh → A9 báo "pattern present". Phase 2 nhận ≥2 frame → A9 nâng cấp verdict "stuck/kẹt". Confirm thiết kế này.

## 9. TDD outline

- test: ảnh có 4 skeleton block (rect xám đều) → `pattern_type=skeleton`, `confidence > 0.7`.
- test: ảnh list cards thật (có text bên trong) → KHÔNG là skeleton (loại false positive).
- test: ảnh spinner (hình tròn cung) → `pattern_type=spinner`.
- test: ảnh màn trắng (entropy thấp) → `pattern_type=blank`.
- test: ảnh có overlay mờ phủ toàn màn → `pattern_type=overlay`, `coverage_ratio > 0.8`.
- test: ảnh bàn phím Android/iOS nửa dưới màn → `pattern_type=keyboard`.
- test: ảnh có broken-image icon (Chrome style) → `pattern_type=broken_image`.
- test: ảnh màn bình thường (không có pattern) → `pattern_detections=[]`, không crash.
- test: skeleton pattern → `temporal=true` + note "requires >=2 frames".
- test: dark-mode skeleton (màu tối) → detect được (không phụ thuộc absolute threshold).
- test: ảnh nền trắng product hợp lệ + có text/button → KHÔNG phải blank.
- test: mọi detection có `evidence` đầy đủ (method, bbox, confidence).

## Trạng thái: spec ✅ — chờ chốt mục 8 (template set platform + ngưỡng tune GS + scope A3 gate).
