# A7 — Image Region + Meta Reader (ảnh-photo → vùng + intrinsic vs displayed)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". **Mode A · B.** Tech: **Python + CV**.
> ⚠ **Mode A mạnh hơn hẳn Mode B** — lý do: `intrinsic` chỉ có trong DOM (naturalWidth/Height).
> Mode B chỉ thấy `displayed`; không tính được tỉ lệ méo tuyệt đối → confidence thấp.
> Liên quan: [`A1-tree-parser.md`](A1-tree-parser.md) · [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A6-icon-graphic-detector.md`](A6-icon-graphic-detector.md) · [`A8`](#) · [`A9`](#) · [`A11-face-text-in-image-detector.md`](A11-face-text-in-image-detector.md) · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm

Nhận diện vùng **ảnh-photo** (lớn, nhiều màu) trên màn hình, đọc / ước lượng kích thước **intrinsic (gốc)** và **displayed (hiển thị thực)** để phát hiện:
- **Méo tỉ lệ** (IMG-09): `intrinsic_aspect ≠ displayed_aspect` → scale-mode sai.
- **Upscale / vỡ / mờ** (IMG-03): displayed >> intrinsic → ảnh bị phóng to quá.
- **Ảnh vỡ / placeholder** (IMG-01, IMG-08): vùng ảnh trống hoặc broken-image indicator.
- **Load dở** (IMG-14): vùng ảnh chỉ hiện một phần.

Điền vào `element.image_meta`: `intrinsic_w/h`, `displayed_w/h`, `scale_mode`, `aspect_ratio_error`, `blur_score`.

**KHÔNG** phân tích nội dung ảnh (mặt/text trong ảnh → A11), KHÔNG tính màu/contrast (A4).

## 2. Tại sao Mode A mạnh hơn hẳn Mode B

| Thông tin | Mode A (có DOM) | Mode B (chỉ ảnh) |
|---|---|---|
| **`intrinsic_w/h`** (kích thước gốc file ảnh) | ✅ DOM cấp thẳng: `imageMeta.naturalWidth/Height` từ A1 | ❌ KHÔNG biết — pixel chỉ thấy `displayed`; muốn biết phải **fetch URL ảnh** (chậm, không luôn dùng được) |
| **`displayed_w/h`** | ✅ `bbox` từ A1 | ✅ `bbox` từ A3 (vision) |
| **`scale_mode`** (`object-fit`) | ✅ computed-style từ A2 | ❌ chỉ suy đoán từ pixel |
| **Méo tỉ lệ tuyệt đối** | ✅ tính được: `intrinsic_aspect vs displayed_aspect` | ⚠ không tính được tuyệt đối — chỉ ước lượng từ pixel (xem dưới) |
| **Upscale/blur** | ✅ tính được: `displayed > intrinsic × dpr` | ✅ đo được: Laplacian sharpness từ pixel |
| **Ảnh vỡ** | ✅ `naturalWidth == 0` / `src` lỗi (A1) | ✅ detect pattern broken-image (A9) |

> ⚠ **Hệ quả quan trọng cho tester:** nếu cần bắt **méo tỉ lệ (IMG-02/IMG-09) chính xác** → phải
> gửi DOM. Mode B chỉ bắt được **mờ/blur (IMG-03)** và **pattern broken** (IMG-01/IMG-14) từ pixel.
> Đây là ví dụ điển hình **"Mode A mạnh hơn hẳn Mode B"** — nêu rõ trong API contract.

## 3. Input / Output

- **Input:**
  - PNG (full).
  - *Mode A:* `elements[]` từ A1 với `role=image`, `image_meta.naturalWidth/Height`, `bbox`, `attrs.src`, style `object-fit` từ A2.
  - *Mode B:* `elements[]` thô từ A3 đã loại icon (A6), meta `viewport{w,h,dpr}`.
- **Output:** annotate `image_meta` trong `elements[]` + `candidate_issues` sơ bộ:
```jsonc
{
  "id": "e25",
  "role": "image",
  "source": "dom | vision",
  "confidence": 0.9,             // Mode A: cao; Mode B: thấp hơn
  "image_meta": {
    "intrinsic_w": 800, "intrinsic_h": 600,    // Mode A: từ DOM; Mode B: null
    "displayed_w": 375, "displayed_h": 200,    // từ bbox
    "scale_mode": "cover | contain | fill | none | unknown",
    "intrinsic_aspect": 1.333,                 // Mode A: tính được
    "displayed_aspect": 1.875,                 // tính được cả 2 mode
    "aspect_ratio_error": 0.54,               // |intrinsic - displayed| aspect diff; Mode B: null
    "upscale_factor": null,                    // displayed/intrinsic nếu biết intrinsic
    "blur_score": 82.4,                       // Laplacian variance — cả 2 mode
    "is_broken": false,                        // pattern broken-img
    "is_partial_load": false,                  // load dở
    "source_url": "https://..."               // Mode A nếu có attrs.src
  },
  "crop": "crops/e25.png"
}
```
+ `candidate_issues[]` sơ bộ (R3) cho Rule Engine xử lý tiếp.

## 4. Kỹ thuật / lib (Python) — list + đề xuất

| Việc | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| **Mode A — đọc meta từ DOM** | A1 đã parse → A7 chỉ nhận field `image_meta` + `bbox` + `style.object-fit` từ A2 | zero-cost, chính xác, deterministic | chỉ Mode A | ✅ **bắt buộc Mode A** |
| **Tính méo tỉ lệ** | thuần Python (`abs(iw/ih - dw/dh) / (iw/ih)`) | deterministic, không lib | — | ✅ Rule R3 dùng ngưỡng `aspect_ratio_error` |
| **Mode B — detect vùng ảnh-photo** | **OpenCV** `calcHist` trên vùng + `np.var(gray)` (variance cao → nhiều chi tiết → photo), kết hợp `color_count` từ A6 | không train | flat-color banner có thể nhầm | ✅ đặc trưng phụ |
| **Đo độ nét / blur score** | **OpenCV** `Laplacian` variance (`cv2.Laplacian(gray, cv2.CV_64F).var()`) | nhanh, deterministic | nhạy cảm với nội dung ảnh mờ chủ ý | ✅ cả Mode A & B |
| **Detect broken-image pattern** | **OpenCV** detect icon broken-image (vùng nhỏ top-left + border) + histogram entropy thấp | không train | nhiều dạng broken → miss một số | ✅ kết hợp A9 Pattern Detector |
| **Ước lượng aspect từ pixel (Mode B — hạn chế)** | chỉ có `displayed_aspect`; không thể biết `intrinsic_aspect` nếu không fetch URL | — | Mode B KHÔNG tính được tỉ lệ méo | ⚠ đánh dấu rõ `confidence thấp` |
| **Fetch ảnh gốc để lấy intrinsic (tùy chọn)** | `httpx`/`requests` + `Pillow.open` (`image.size`) | biết được intrinsic → Mode B mạnh hơn | chậm (network), ảnh có thể auth-gated, không luôn dùng được | ⏭ tùy chọn Phase 2 — **anh quyết** (mục 8) |
| **Crop vùng ảnh** | **Pillow** (`Image.crop`) | cấp crop cho A11, A8 | — | ✅ |

## 5. Pipeline A7 (đề xuất)

### Mode A (có DOM):
1. Nhận `elements[]` từ A1, lọc `role=image`.
2. Đọc `imageMeta.naturalWidth/Height` → `intrinsic_w/h`; `bbox` → `displayed_w/h`.
3. Tính: `intrinsic_aspect`, `displayed_aspect`, `aspect_ratio_error`; phân loại `scale_mode` từ `style.object-fit` (A2).
4. Tính `upscale_factor` = `displayed_w / intrinsic_w` nếu intrinsic > 0.
5. Crop vùng ảnh từ PNG → tính `blur_score` (Laplacian variance).
6. Check `naturalWidth == 0` hoặc `src` rỗng/lỗi → `is_broken = true`.
7. Emit `image_meta` + candidate_issues sơ bộ. `source=dom`, `confidence=0.95`.

### Mode B (chỉ ảnh — hạn chế rõ):
1. Nhận regions từ A3 đã lọc icon (A6): giữ lại vùng `color_count > 8` + area lớn.
2. **Đặc trưng:** histogram entropy + variance → classify `photo vs illustration vs flat`.
3. `intrinsic_w/h = null` (không có); `displayed_w/h` = bbox A3.
4. `displayed_aspect` tính được; `aspect_ratio_error = null` (⚠ KHÔNG biết intrinsic).
5. Crop → `blur_score` Laplacian.
6. Check pattern broken-image (kết hợp A9): vùng nhỏ có icon broken + border.
7. Emit với `source=vision`, `confidence=0.6` (thấp hơn Mode A rõ ràng).

## 6. Ranh giới Mode A vs Mode B (BẮT BUỘC tôn trọng)

| Check | Mode A | Mode B |
|---|---|---|
| Méo tỉ lệ (IMG-09/IMG-02) | ✅ Tính chính xác từ `intrinsic vs displayed` | ❌ Không có intrinsic → KHÔNG check; đánh dấu `"intrinsic_unavailable"` |
| Upscale / @1x trên @3x (IMG-03/ENV-10) | ✅ `displayed / intrinsic > dpr` | ⚠ Chỉ đo blur_score (Laplacian) → nghi ngờ, confidence thấp |
| Ảnh vỡ (IMG-01) | ✅ `naturalWidth == 0` / src lỗi | ✅ Pattern broken từ A9 |
| Ảnh load dở (IMG-14) | ✅ Kết hợp A9 | ✅ A9 Pattern Detector |
| Blur / mờ (IMG-03) | ✅ Laplacian | ✅ Laplacian |
| `scale_mode` chính xác | ✅ `object-fit` từ A2 | ❌ `unknown` |

> Rule Engine phải kiểm tra `image_meta.intrinsic_w` trước khi chạy rule IMG-09/IMG-02.
> Nếu `intrinsic_w == null` → skip rule đó, không báo false positive.

## 7. Tiêu chí phục vụ

| Tiêu chí | Cách A7 đóng góp | Mode |
|---|---|---|
| **IMG-02** Méo tỉ lệ (intrinsic vs displayed) | `aspect_ratio_error > ngưỡng` → candidate R3 | A only |
| **IMG-09** Scale-mode sai (cover ↔ contain → méo/cắt) | `scale_mode` + `aspect_ratio_error` | A (chính xác), B yếu |
| **IMG-03** Mờ / pixel hoá (upscale, thiếu @2x/@3x) | `blur_score` thấp + `upscale_factor` cao | A & B |
| **ENV-10** Asset sai mật độ (@1x trên @3x) | `upscale_factor > dpr` | A only |
| **IMG-01** Ảnh vỡ / broken | `is_broken` + pattern A9 | A & B |
| **IMG-14** Ảnh load dở | `is_partial_load` từ A9 | A & B |
| **IMG-11** Logo mờ / sai tỉ lệ | `blur_score` + `aspect_ratio_error` | A & B |
| **IMG-04** Crop cắt mặt (nội dung quan trọng) | A7 cấp **crop vùng ảnh** → A11 detect face/text | A & B |
| **IMG-05** Slot ảnh trống | `intrinsic_w == 0` / vùng placeholder | A & B |

## 8. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Mode B có fetch URL ảnh gốc để lấy intrinsic không?** Đây là cách duy nhất Mode B tính được méo tỉ lệ. Trade-off: **chậm** (network), ảnh auth-gated không fetch được, phức tạp pipeline. Đề xuất: **Phase 1 bỏ qua** (Mode B không check IMG-09); Phase 2 thêm optional URL-fetch. (Anh quyết.)
- [ ] **Ngưỡng `aspect_ratio_error`** để báo lỗi IMG-09: đề xuất `> 0.1` (~10% sai lệch). Tune bằng golden set.
- [ ] **Ngưỡng `blur_score`** (Laplacian variance) cho IMG-03: phụ thuộc loại ảnh (portrait vs icon vs illustration). Tune bằng golden set — đừng hard-code.
- [ ] **Ngưỡng `upscale_factor`**: `displayed_w / intrinsic_w > dpr × 1.5` → nghi upscale? Cần golden set để xác nhận.

## 9. Edge cases (BẮT BUỘC xử lý)

- **`naturalWidth == 0`** (broken img chưa load): Mode A bắt được ngay; Mode B cần A9 Pattern Detector bổ trợ.
- **SVG co giãn tự do:** SVG không có intrinsic pixel size theo nghĩa bitmap → `intrinsic_w/h = null`, `scale_mode = "svg_scalable"`, không check upscale-blur.
- **Ảnh background CSS** (`background-image`): A1 có thể không cấp `naturalWidth` → cần xử lý riêng (Phase 2 nếu cần).
- **Ảnh rất nhỏ (< 32px cạnh):** Laplacian variance không đáng tin → không check blur; đẩy sang A6 (có thể là icon).
- **Video poster/thumbnail (IMG-13):** xử lý giống ảnh; `tag = video` → đặc biệt check `poster` attribute.
- **Progressive JPEG load dở (IMG-14):** ảnh hiện được một phần — Pillow có thể đọc được phần trên, A9 Pattern Detector bổ trợ nhận biết.
- **Ảnh nhiều tỉ lệ (srcset):** Mode A có thể lấy sai naturalSize nếu browser chọn src khác → ghi chú trong Web Capture Contract (cần tester capture đúng `currentSrc`).

## 10. TDD outline (khi vào code)

- test Mode A: element `img naturalWidth=800 naturalHeight=600` + bbox `375×200` → `aspect_ratio_error ≈ 0.54`, candidate IMG-09.
- test Mode A: `upscale_factor = displayed_w / intrinsic_w` tính đúng; vượt `dpr×1.5` → candidate IMG-03.
- test Mode A: `naturalWidth == 0` → `is_broken = true`, candidate IMG-01.
- test Mode A: `object-fit: cover` từ A2 → `scale_mode = "cover"`.
- test Mode B: không có intrinsic → `aspect_ratio_error = null`, `intrinsic_w = null`; không báo IMG-09.
- test Mode B: `source=vision`, `confidence < 0.7`.
- test blur_score: crop sắc nét (Laplacian cao) vs crop mờ (Laplacian thấp) → phân biệt đúng chiều.
- test SVG: `scale_mode = "svg_scalable"`, không check upscale.
- test ảnh < 32px → không check blur, không crash.
- test Rule Engine không bắn IMG-09 khi `intrinsic_w == null` (Mode B).

## Trạng thái: spec ✅ — chờ chốt mục 8 (URL-fetch intrinsic Mode B + ngưỡng aspect/blur/upscale tune golden set).
