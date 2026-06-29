# A13 — Device/Env Metadata Provider (safe_area / dpr / bars / orientation)

> **TL;DR:** Điền metadata nền cho `screen{}` (safe_area, dpr, status/nav bar, notch, orientation) từ tester meta → bảng device profile → suy pixel; không báo lỗi trực tiếp nhưng là input bắt buộc cho ENV-01/02/03. Chạy trước mọi analyzer khác.

> Phase 1. **Chạy trước mọi analyzer khác.** Tech: **Python + OpenCV + bảng device profile tĩnh**.
> Liên quan: [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A9`](#) Pixel Pattern Detector

## 1. Trách nhiệm
Điền `screen.safe_area` (top/bottom/left/right), `screen.viewport.dpr`, vùng **status bar**, **navigation bar**, **home indicator** vào schema.

Hai nguồn, **ưu tiên theo thứ tự:**
1. **Tester gửi meta** (lý tưởng): JSON `device_meta` → parse + điền thẳng. `source=meta`, `confidence=1.0`.
2. **Suy từ pixel + bảng device profile** (khi thiếu meta): dùng `viewport{w,h}` + `dpr` tra bảng → ước lượng safe_area; OpenCV + OCR nhận dạng status bar / home indicator từ ảnh. `source=inferred`, confidence thấp hơn.

> ⚠ **Giới hạn khi không có meta:** nhiều thiết bị cùng viewport nhưng safe_area khác (vd iPhone 14 vs 14 Pro Dynamic Island). Không có meta → **`confidence<1`** + ưu tiên tra bảng phổ biến; không khớp → `safe_area` ước lượng + cờ `inferred_from_pixel`. Rule ENV-01/02/03 chỉ fire khi `confidence` đủ ngưỡng.

## 2. Input / Output
- **Input:** PNG full + `screen.viewport{w,h}` + `screen.platform` (android/ios/web) + *tùy chọn:* `device_meta` JSON.
- **Output:** điền vào `screen{}`:
```jsonc
"screen": {
  "viewport": { "w": 390, "h": 844, "dpr": 3 },
  "safe_area": {
    "top": 59,        // px — notch/Dynamic Island/status bar (cao nhất, bảo thủ nhất)
    "bottom": 34,     // px — home indicator / gesture area
    "left": 0, "right": 0
  },
  "status_bar": { "h": 59, "bbox": {"x":0,"y":0,"w":390,"h":59}, "source": "device_profile" },
  "nav_bar": { "h": 34, "bbox": {"x":0,"y":810,"w":390,"h":34}, "source": "device_profile" },
  "home_indicator": { "present": true, "h": 34, "source": "device_profile" },
  "orientation": "portrait",           // "portrait" | "landscape"
  "notch_type": "dynamic_island",     // "none" | "notch" | "dynamic_island" | "punch_hole" | "unknown"
  "meta_source": "device_profile",    // "tester_meta" | "device_profile" | "pixel_inferred" | "unknown"
  "meta_confidence": 0.85
}
```

## 3. Ba bài toán con
- a. **Parse tester meta** — validate + điền schema.
- b. **Tra bảng device profile** — key = `viewport{w,h,dpr}` + `platform`.
- c. **Suy từ pixel** (dự phòng khi bảng không khớp) — dò status bar, home indicator, notch/cutout bằng OpenCV + OCR.

## 4. Kỹ thuật / lib (Python)
| Việc | Lib/tool | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Parse / validate tester meta | **`pydantic` v2** | model hoá, validate sẵn | — | ✅ |
| Bảng device profile tĩnh | **dict Python / JSON tĩnh** | deterministic, không dep ngoài | cần bảo trì | ✅ **dự phòng chính** |
| Dò status bar (giờ/pin/sóng) | **OpenCV** + **A5 OCR** (đọc giờ dải trên cùng) | dò được dù không meta | FP khi app full-screen/immersive | ✅ |
| Nhận diện notch / Dynamic Island | **OpenCV** (dò vùng đen hình giọt nước / viên thuốc ở đỉnh giữa) | tự động | khó phân biệt notch vs status-bar custom, FP với splash | ✅ có điều kiện |
| Dò home indicator (iOS) | **OpenCV** (thanh mỏng căn giữa đáy, ≈134×5 px @3x) | tự động | FP nếu app có thanh tương tự | tùy chọn |
| Orientation | **numpy / Pillow** so `w` vs `h` | đơn giản | — | ✅ |
| Đọc giờ status bar (đối chiếu) | **A5 OCR** (crop dải trên → đọc HH:MM) | xác nhận status bar | OCR chậm nếu gọi riêng → tái dùng A5 | ✅ tái dùng A5 |

> **Bảng device profile** cần phủ ít nhất các model phổ biến (đề xuất top-20 theo thị phần VN/SEA: iPhone 14/15/16 series, Samsung Galaxy S/A series, Pixel series). Format: key = `(platform, w_pt, h_pt, dpr)` → `{safe_area, notch_type, status_bar_h, home_h}`. Nguồn: Apple HIG, Android docs, crowdsource (screensizes.es).

## 5. Pipeline A13 (đề xuất)
1. **Orientation:** so `viewport.w` vs `viewport.h` → `portrait/landscape`.
2. **Tester meta có không?**
   - Có → parse + validate (`pydantic`) → điền; `meta_source=tester_meta`, `confidence=1.0`. **Dừng**.
   - Không → bước 3.
3. **Tra bảng** bằng `(platform, w, h, dpr)`:
   - Khớp chính xác → `meta_source=device_profile`, `confidence=0.9`.
   - Khớp gần (±10px) → `confidence=0.75`.
   - Không khớp → bước 4.
4. **Suy từ pixel (dự phòng):**
   - a. **Status bar:** crop dải trên 5–8% → OCR tìm "HH:MM"; thấy → đo chiều cao.
   - b. **Notch/Dynamic Island:** crop vùng giữa đỉnh ~8% → dò vùng tối (threshold đen/xám đậm, aspect gần Dynamic Island / notch).
   - c. **Home indicator (iOS):** crop đáy ~3% → dò line ngang mỏng căn giữa sáng hơn nền.
   - d. Gộp → ước lượng `safe_area`; `meta_source=pixel_inferred`, `confidence=0.55`.
5. **Không suy được:** zero/unknown + cờ; Rule ENV-01/02/03 bỏ qua / confidence thấp.
6. **Emit** vào `screen{}` — chạy **trước** mọi analyzer (A0 Normalize gọi A13 đầu tiên).

## 6. Bảng device profile — phủ tối thiểu Phase 1
| Nhóm thiết bị | Nền tảng | Viewport (pt/dp) | DPR | Safe trên | Safe dưới | Kiểu notch |
|---|---|---|---|---|---|---|
| iPhone SE 3rd | ios | 375×667 | 2 | 20 | 0 | none |
| iPhone 12/13/14 | ios | 390×844 | 3 | 47 | 34 | notch |
| iPhone 14 Pro / 15 Pro | ios | 393×852 | 3 | 59 | 34 | dynamic_island |
| iPhone 15 / 16 | ios | 393×852 | 3 | 59 | 34 | dynamic_island |
| iPhone 15 Plus / 16 Plus | ios | 430×932 | 3 | 59 | 34 | dynamic_island |
| Samsung Galaxy S (2022+) | android | 360×800 | 3 | 24 | 0 | punch_hole |
| Samsung Galaxy A (tầm trung) | android | 360×800 | 2.75 | 24 | 0 | punch_hole |
| Google Pixel 7/8 | android | 411×914 | 2.625 | 24 | 16 | punch_hole |
| Android chung (không thanh điều hướng) | android | bất kỳ | bất kỳ | 24 | 0 | unknown |
| Android chung (thanh 3 nút) | android | bất kỳ | bất kỳ | 24 | 48 | unknown |
| Web (máy tính bàn) | web | bất kỳ | 1–2 | 0 | 0 | none |
| Web (trình duyệt di động) | web | 375–430 | 2–3 | 0 | 50 | none |

> Bảng là **khởi điểm** — review & mở rộng trước standard-set test (mục 9).

## 7. Edge cases (BẮT BUỘC xử lý)
- **Immersive / fullscreen app:** status bar ẩn → OCR không tìm được giờ; dự phòng bảng profile hoặc `confidence=0.4`.
- **Screenshot tool crop mất status bar:** chiều cao ảnh ≠ viewport thật → cờ `viewport_mismatch`, ước lượng dè dặt.
- **Landscape:** safe_area left/right quan trọng hơn; bảng cần dữ liệu riêng (nhiều device safe_area landscape ≠ portrait xoay).
- **Web:** không notch/home indicator; safe_area = 0 trừ khi mobile browser có URL bar đè (ENV-09 — 100vh lỗi).
- **Foldable:** Phase 2 (ENV-11).
- **Custom ROM Android** ẩn/thay status bar: dò pixel + `confidence=0.5`.
- **DPR thiếu:** tester không gửi → ước lượng từ `(viewport_w, image_w)` ratio.

## 8. Tiêu chí phục vụ
| Tiêu chí | Vai trò A13 |
|---|---|
| **ENV-01** Safe-area/notch che nội dung | `safe_area` là **input bắt buộc** |
| **ENV-02** Status bar đè / lẫn màu | `status_bar.bbox` → kiểm phần tử trong vùng này |
| **ENV-03** Home indicator đè nút | `home_indicator.bbox` |
| **ENV-04** Bàn phím che input | `safe_area.bottom` tham chiếu (bàn phím suy pixel → A9) |
| **ENV-09** 100vh lỗi mobile browser | `nav_bar.h` của browser = chiều cao bị cắt |
| **ENV-10** Asset sai mật độ | `screen.viewport.dpr` |
| **CMP-01** Touch target | `viewport.dpr` để chuyển pt/dp ↔ px khi check 44pt/48dp |
| **R (geometry rules)** | `safe_area`, `dpr` dùng trong toàn Rule Engine |

## 9. Open decisions (cần anh chốt)
- [ ] **Nguồn safe_area ưu tiên: bắt buộc tester gửi meta hay tự suy pixel?**
  - *Bắt buộc meta:* chính xác nhất. Nhược: tester thêm bước (friction).
  - *Tự suy pixel:* tester chỉ gửi ảnh. Nhược: không chính xác với model phức (Dynamic Island, foldable) → có thể báo sai ENV-01.
  - → **Đề xuất:** meta (nếu có) → profile → pixel. Anh xác nhận flow?
- [ ] **Bảng device profile phủ tới đâu?** Đề xuất top-20 model VN/SEA (mục 6 là khởi điểm). Anh có danh sách device thực tester hay dùng?
- [ ] **Khi không suy được safe_area (confidence quá thấp):** (a) bỏ qua hoàn toàn ENV-01/02/03 (FN); hay (b) chạy với safe_area=0 + cờ `unreliable_metadata`? Đề xuất **(b)** — tránh bỏ sót lỗi nặng, nhưng tester biết kết quả thiếu tin cậy.
- [ ] **DPR khi tester không gửi:** tự suy từ `image.w / viewport.w` ratio đủ chính xác không? (Chỉ đúng nếu screenshot không bị tool scale.)

## 10. TDD outline
- tester meta đầy đủ → đúng safe_area, `meta_source=tester_meta`, `confidence=1.0`.
- viewport (390, 844, dpr=3) + platform=ios → tra bảng → safe_area top=47, bot=34.
- viewport không khớp bảng → suy pixel + `meta_source=pixel_inferred`.
- ảnh có dải giờ "9:41" trên cùng → OCR nhận diện → ghi status_bar.h đúng.
- landscape (w > h) → orientation=landscape.
- web → safe_area top=0, bottom=0 (no notch).
- dpr thiếu → suy từ `image.w / viewport.w`, không crash.
- không suy được gì → safe_area=zero + cờ `meta_source=unknown`, không crash.
- ENV-01 nhận `safe_area.confidence < 0.5` → downgrade issue confidence.

## Trạng thái: spec ✅ — chờ chốt mục 9 (nguồn meta ưu tiên + phạm vi bảng device + xử lý khi thiếu dữ liệu).
