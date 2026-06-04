# A7 — Image Region + Meta Reader (ảnh-photo → vùng + displayed + blur)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". Tech: **Python + CV**.
> ⚠ **Giới hạn quan trọng:** không có DOM → không biết `intrinsic_w/h` (kích thước file gốc).
> Chỉ thấy `displayed` (bbox từ A3). Méo tỉ lệ tuyệt đối KHÔNG tính được — chỉ đo blur/sharpness.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A6-icon-graphic-detector.md`](A6-icon-graphic-detector.md) · [`A8`](#) · [`A9`](#) · [`A11-face-text-in-image-detector.md`](A11-face-text-in-image-detector.md) · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm

Nhận diện vùng **ảnh-photo** (lớn, nhiều màu) trên màn hình, đo kích thước **displayed (hiển thị thực)** và các chỉ số pixel để phát hiện:
- **Mờ / pixel hoá** (IMG-03): đo Laplacian sharpness từ pixel.
- **Ảnh vỡ / placeholder** (IMG-01, IMG-08): vùng ảnh trống hoặc broken-image indicator — kết hợp A9.
- **Load dở** (IMG-14): vùng ảnh chỉ hiện một phần.

> ⚠ **Không có intrinsic:** hệ thống chỉ nhận ảnh, không có DOM → `intrinsic_w/h` luôn `null`.
> Các tiêu chí cần intrinsic (IMG-09 méo tỉ lệ, ENV-10 sai mật độ asset) **không check được**
> ở Phase 1. Đánh dấu `"intrinsic_unavailable"` trong output. Nếu cần check méo tỉ lệ → Phase 2
> với optional URL-fetch.

Điền vào `element.image_meta`: `displayed_w/h`, `scale_mode="unknown"`, `blur_score`.

**KHÔNG** phân tích nội dung ảnh (mặt/text trong ảnh → A11), KHÔNG tính màu/contrast (A4).

## 2. Input / Output

- **Input:**
  - PNG (full).
  - `elements[]` thô từ A3 đã loại icon (A6), meta `viewport{w,h,dpr}`.
- **Output:** annotate `image_meta` trong `elements[]` + `candidate_issues` sơ bộ:
```jsonc
{
  "id": "e25",
  "role": "image",
  "source": "vision",
  "confidence": 0.6,
  "image_meta": {
    "intrinsic_w": null, "intrinsic_h": null,    // không có — hệ thống chỉ nhận ảnh
    "displayed_w": 375, "displayed_h": 200,       // từ bbox A3
    "scale_mode": "unknown",                      // không có object-fit từ CSS
    "intrinsic_aspect": null,
    "displayed_aspect": 1.875,                    // tính được từ displayed
    "aspect_ratio_error": null,                   // KHÔNG tính được (không có intrinsic)
    "upscale_factor": null,
    "blur_score": 82.4,                           // Laplacian variance — đo được từ pixel
    "is_broken": false,                           // pattern broken-img
    "is_partial_load": false,                     // load dở
    "intrinsic_unavailable": true                 // cờ: không có DOM để lấy kích thước gốc
  },
  "crop": "crops/e25.png"
}
```
+ `candidate_issues[]` sơ bộ (R3) cho Rule Engine xử lý tiếp.

## 3. Kỹ thuật / lib (Python) — list + đề xuất

| Việc | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| **Detect vùng ảnh-photo** | **OpenCV** `calcHist` trên vùng + `np.var(gray)` (variance cao → nhiều chi tiết → photo), kết hợp `color_count` từ A6 | không train | flat-color banner có thể nhầm | ✅ đặc trưng phụ |
| **Đo độ nét / blur score** | **OpenCV** `Laplacian` variance (`cv2.Laplacian(gray, cv2.CV_64F).var()`) | nhanh, deterministic | nhạy cảm với nội dung ảnh mờ chủ ý | ✅ cả Mode A & B |
| **Phát hiện pattern ảnh vỡ** | **OpenCV** phát hiện icon broken-image (vùng nhỏ top-left + border) + histogram entropy thấp | không train | nhiều dạng broken → miss một số | ✅ kết hợp A9 Pattern Detector |
| **Crop vùng ảnh** | **Pillow** (`Image.crop`) | cấp crop cho A11, A8 | — | ✅ |

> ⚠ **URL-fetch để lấy intrinsic:** cách duy nhất biết `intrinsic_w/h` khi không có DOM. Trade-off:
> chậm (network), ảnh có thể auth-gated. → Phase 2 nếu cần bắt IMG-09 ở vision-only. Mục 8.

## 4. Pipeline A7 (đề xuất)

1. Nhận regions từ A3 đã lọc icon (A6): giữ lại vùng `color_count > 8` + area lớn.
2. **Đặc trưng:** histogram entropy + variance → classify `photo vs illustration vs flat`.
3. `intrinsic_w/h = null` (không có); `displayed_w/h` = bbox A3.
4. `displayed_aspect` tính được; `aspect_ratio_error = null` (KHÔNG biết intrinsic).
5. Crop → `blur_score` Laplacian.
6. Check pattern broken-image (kết hợp A9): vùng nhỏ có icon broken + border.
7. Emit với `source=vision`, `confidence=0.6`, `intrinsic_unavailable=true`.

## 5. Khả năng check theo tiêu chí

| Check | Có check được không? | Lý do |
|---|---|---|
| Méo tỉ lệ (IMG-09/IMG-02) | ❌ Không | Không có intrinsic → `"intrinsic_unavailable"` |
| Upscale / @1x trên @3x (IMG-03/ENV-10) | ⚠ Chỉ gián tiếp | Chỉ đo blur_score (Laplacian) → nghi ngờ, confidence thấp |
| Ảnh vỡ (IMG-01) | ✅ | Pattern broken từ A9 |
| Ảnh load dở (IMG-14) | ✅ | A9 Pattern Detector |
| Blur / mờ (IMG-03) | ✅ | Laplacian |
| `scale_mode` chính xác | ❌ | `unknown` — không có object-fit từ CSS |

> Rule Engine **bắt buộc** kiểm tra `image_meta.intrinsic_unavailable` trước khi chạy rule
> IMG-09/IMG-02. Nếu `true` → bỏ qua rule đó, không báo false positive.

## 6. Tiêu chí phục vụ

| Tiêu chí | Cách A7 đóng góp |
|---|---|
| **IMG-03** Mờ / pixel hoá (blur, thiếu @2x/@3x) | `blur_score` thấp → candidate nghi |
| **IMG-01** Ảnh vỡ / broken | `is_broken` + pattern A9 |
| **IMG-14** Ảnh load dở | `is_partial_load` từ A9 |
| **IMG-11** Logo mờ / sai tỉ lệ | `blur_score` |
| **IMG-04** Crop cắt mặt (nội dung quan trọng) | A7 cấp **crop vùng ảnh** → A11 detect face/text |
| **IMG-05** Slot ảnh trống | vùng placeholder (low-entropy) |
| **IMG-09, IMG-02, ENV-10** | ❌ Không check — cần intrinsic (Phase 2) |

## 7. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Phase 2 có fetch URL ảnh gốc để lấy intrinsic không?** Đây là cách duy nhất tính được méo tỉ lệ. Trade-off: chậm (network), ảnh auth-gated, phức tạp pipeline. Đề xuất: Phase 1 bỏ qua IMG-09; Phase 2 optional URL-fetch. (Anh quyết.)
- [ ] **Ngưỡng `blur_score`** (Laplacian variance) cho IMG-03: phụ thuộc loại ảnh (portrait vs icon vs illustration). Tune bằng standard set — đừng hard-code.

## 8. Edge cases (BẮT BUỘC xử lý)

- **SVG co giãn tự do:** SVG không có intrinsic pixel size theo nghĩa bitmap → `intrinsic_w/h = null`, `scale_mode = "svg_scalable"`, không check upscale-blur.
- **Ảnh rất nhỏ (< 32px cạnh):** Laplacian variance không đáng tin → không check blur; đẩy sang A6 (có thể là icon).
- **Video poster/thumbnail (IMG-13):** xử lý giống ảnh.
- **Progressive JPEG load dở (IMG-14):** ảnh hiện được một phần — Pillow có thể đọc được phần trên, A9 Pattern Detector bổ trợ nhận biết.

## 9. TDD outline (khi vào code)

- test: không có intrinsic → `aspect_ratio_error = null`, `intrinsic_w = null`, `intrinsic_unavailable=true`; không báo IMG-09.
- test: `source=vision`, `confidence < 0.7`.
- test blur_score: crop sắc nét (Laplacian cao) vs crop mờ (Laplacian thấp) → phân biệt đúng chiều.
- test SVG: `scale_mode = "svg_scalable"`, không check upscale.
- test ảnh < 32px → không check blur, không crash.
- test Rule Engine không bắn IMG-09 khi `intrinsic_unavailable=true`.

## Trạng thái: spec ✅ — chờ chốt mục 7 (URL-fetch intrinsic Phase 2 + ngưỡng blur tune standard set).
