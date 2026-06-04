# A4 — Pixel Color Sampler (contrast/dark/opacity từ pixel thực)

> Bóc tách chi tiết. Phase 1, nhóm "đo diện mạo".
> Đây là **analyzer màu/contrast chủ lực** — nguồn duy nhất cho màu/contrast vì hệ thống
> chỉ nhận ảnh, không có computed-style.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (cấp crop element) ·
> [`A8-pixel-glyph-inspector.md`](A8-pixel-glyph-inspector.md) · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm

Đo **màu/contrast/opacity THỰC TẾ từ pixel ảnh** — nguồn duy nhất cho thông tin màu vì
không có computed-style:

Cụ thể A4 làm:
- Lấy **crop element** (từ A3) → tách vùng **foreground** (chữ/icon) vs **background**.
- Trích **màu trội** mỗi vùng → tính **WCAG contrast_ratio** từ pixel.
- Phát hiện **dark-mode render** đúng/sai (cả màn tối hay chỉ một vùng không đổi).
- Đo **opacity hiệu dụng** từ alpha-channel / blend với lớp dưới.
- Bắt **màu disabled** (so sánh với sibling enabled tương tự).

**KHÔNG** đọc text/content (việc A5); **KHÔNG** phân loại element (việc A3/A6).

## 2. Input / Output

**Input:**
- PNG full màn + meta `viewport{w,h,dpr}`, `theme` (`light|dark`).
- `elements[]` từ A3 (có `bbox`, `role`, `text` nếu biết) — để crop từng element.
- *Tùy chọn:* `bg_layer_crop` (crop lớp nền phía dưới nếu element trong suốt — A0 cấp).

**Output:** bổ sung vào `elements[]` các field `style.*` sau (gán `source="vision"`):

```jsonc
"style": {
  "color_px":       [17, 24, 39],       // RGB màu trội foreground (từ pixel)
  "bg_color_px":    [255, 255, 255],    // RGB màu trội background (từ pixel)
  "contrast_ratio_px": 12.4,            // WCAG contrast tính từ pixel (null nếu không tách được)
  "color_px_source": "vision",
  "bg_is_solid_px": true,               // background đặc hay ảnh/gradient?
  "dominant_colors": [[17,24,39,0.65],[200,210,220,0.35]], // [(RGB, weight)]
  "opacity_px": 0.9,                    // ước lượng opacity hiệu dụng từ pixel
  "dark_mode_ok": true,                 // null nếu theme không rõ
  "disabled_color_similar": false       // so với sibling enabled (null nếu không có sibling)
}
```

Thêm `pixel_color_result` vào `candidate_issues[]` (rule A4-R2) nếu `contrast_ratio_px < 4.5`
(text thường) hoặc `< 3.0` (đồ hoạ/chữ lớn).

## 3. Bốn bài toán con

a. **Crop & tách fg/bg** — cắt vùng element, tách pixel foreground (chữ/icon) vs background.
b. **Trích màu trội** — từ tập pixel foreground và background.
c. **Tính contrast WCAG** — relative luminance → ratio.
d. **Suy diễn dark-mode, opacity, disabled** — từ phân tích màu toàn vùng.

## 4. Kỹ thuật / lib (Python) — list + đề xuất

| Việc | Lib / cách (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Đọc ảnh, crop, resize | **Pillow (`PIL.Image`)** + **numpy** | API gọn, nhanh, stdlib-like | — | ✅ **core** |
| Tách fg/bg theo màu | **K-means (`sklearn.cluster.KMeans` k=2–4)** trên pixel vùng | tổng quát, không train | chậm nếu vùng lớn; cần seed ổn định | ✅ đề xuất **primary** |
| Tách fg/bg thay thế | **Histogram median-cut (Pillow `quantize`)** | nhanh, không dep ngoài | kém với gradient phức tạp | ✅ fallback nhanh |
| Tách fg theo stroke chữ | **OpenCV Canny + dilate** — vùng cạnh chữ = foreground | phù hợp text rõ nét | cần crop chữ nguyên vẹn | ✅ bổ sung cho element `role=text` |
| Màu trội từ cluster | **numpy weighted mean** theo cluster label | deterministic | — | ✅ |
| Luminance & contrast WCAG | **tự code** (`L = 0.2126R+0.7152G+0.0722B` linearised) | tái dùng R2, không dep | — | ✅ **bắt buộc tự code** |
| Alpha/opacity từ RGBA | **numpy** (channel A / blend công thức) | chính xác | cần ảnh có alpha hoặc lớp nền | ✅ |
| Dark mode detect toàn màn | **numpy mean(L channel)** — nếu trung bình thấp → dark | đơn giản, nhanh | không phát hiện vùng cục bộ sai | ✅ đủ dùng |
| So màu disabled vs sibling | **Euclidean distance RGB / ΔE CIE76** (numpy) | tường minh | cần có sibling rõ ràng | ✅ |

> ⚠ **Không dùng ML/neural** cho bài toán màu — đây là bài tính toán tất định từ pixel.
> K-means là giải thuật **phân cụm không giám sát**, không train lại per app → đúng tinh thần zero-reference.

### 4.1 Tách fg/bg — kỹ thuật chi tiết đề xuất

**Element `role=text/button` (chứa chữ):**
1. Chuyển crop sang **Lab** (perceptual) để phân cụm đều hơn RGB.
2. K-means k=2: cluster 1 = foreground (chữ), cluster 2 = background.
3. Chọn cluster nhỏ hơn = fg (chữ thường ít pixel hơn nền); kiểm tra bằng edge density.
4. Dự phòng: Canny → pixel cạnh → fg; phần còn lại → bg.

**Element `role=image/icon`:**
- Không có "chữ" để tách → lấy màu trội tổng thể bằng k-means k=3–5 → `dominant_colors`.
- Contrast tính giữa màu sáng nhất và tối nhất trong tập trội → proxy cho đồ hoạ.

**Nền ảnh sau text (trường hợp khó nhất):**
- Lấy crop nền (lớp dưới element text — A0 cấp nếu có z-order) → trung vị màu → bg.
- Dự phòng: blur crop → lấy màu trung vị góc (thường ít chữ nhất).

## 5. Pipeline A4 (đề xuất)

1. **Nhận danh sách element** cần đo màu (ưu tiên: `role=text|button|icon|toggle`, có `visible=true`).
2. **Crop element** từ ảnh full theo `bbox`; resize về max 200×200 nếu cần (tốc độ).
3. **Tách fg/bg** (mục 4.1) → pixel sets.
4. **Màu trội fg / bg:** weighted mean trong cluster → `color_px`, `bg_color_px`; ghi `dominant_colors`.
5. **Kiểm tra bg_is_solid_px:** nếu variance pixel bg > ngưỡng (tune GS) → `false` + note "gradient/image".
6. **Tính contrast_ratio_px** (WCAG): relative luminance → ratio; ghi `null` nếu không tách được.
7. **Dark mode check:** nếu `screen.theme=dark`, kiểm tra `bg_color_px` vùng tối vs màu sáng cứng-coded → cờ nghi STY-03.
8. **Opacity px:** nếu ảnh có alpha channel (RGBA) → mean alpha vùng element → `opacity_px`; else ước lượng từ blend.
9. **Disabled so sánh:** nếu agent đoán element là disabled (từ A12) → so màu với sibling nearest enabled → `disabled_color_similar`.
10. **Emit** kết quả vào `elements[].style.*` + `candidate_issues[]` nếu vượt ngưỡng.

## 6. Tiêu chí phục vụ

| Mã | Tiêu chí | Vai trò A4 |
|---|---|---|
| **STY-01** | Contrast chữ/nền < WCAG 4.5:1 | ✅ **chính** — nguồn duy nhất cho màu |
| **STY-02** | Chữ tàng hình (trắng/trắng) | ✅ contrast_ratio_px ~ 1.0 → candidate STY-02 |
| **STY-03** | Dark-mode không đổi màu | ✅ `dark_mode_ok` + phát hiện vùng màu cứng sáng trong theme tối |
| **STY-04** | Icon/viền tàng hình trong theme | ✅ tính contrast đồ hoạ (ngưỡng 3:1) |
| **STY-05** | Opacity sai | ✅ `opacity_px` — ước lượng từ pixel |
| **STY-07** | Disabled không phân biệt enabled | ✅ `disabled_color_similar` — so màu sibling |
| **STY-13** | Tương phản icon/đồ hoạ chức năng < 3:1 | ✅ contrast từ dominant_colors của icon |
| **STY-10** | Gradient/banding lỗi render | ⚠ tín hiệu phụ từ variance bg |

## 7. Edge cases (BẮT BUỘC xử lý)

- **Text antialiasing:** pixel viền chữ pha màu giữa fg và bg → lấy nguyên sẽ sai cluster.
  → Bỏ pixel "pha" (màu trung gian trong khoảng 20–80% giữa 2 cluster) trước khi tính màu trội.
- **Nền nhiều màu (ảnh nền phức tạp):** bg_color_px là trung vị → contrast "trung bình", có thể
  miss vùng text contrast thấp trên 1 nền. → Tính contrast **worst-case**: lấy bg màu gần fg nhất
  (nhỏ nhất trong dominant_colors vùng bg) → báo conservative.
- **Element crop lệch:** bbox A3 sai → crop nhầm nền/phần tử khác → màu vô nghĩa.
  → Thêm `crop_confidence` (= confidence của bbox từ A3); nếu < ngưỡng thì `contrast_ratio_px=null`.
- **Transparent/RGBA ảnh:** ảnh UI xuất PNG có alpha → channel A thể hiện opacity thực.
  → Trộn (blend) với nền trắng/đen theo quy ước trước khi đo màu.
- **Text màu gradient:** foreground không đồng nhất → k-means cho >2 cluster chữ.
  → Lấy màu trội nhất của fg; ghi `color_px_quality="gradient"`.
- **Emoji / icon màu nhiều sắc:** không có fg/bg rõ ràng → skip contrast; chỉ ghi dominant_colors.
- **Element quá nhỏ (< 4×4 px):** không đủ pixel để phân cụm → `contrast_ratio_px=null`,
  confidence thấp.

## 8. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Thuật toán tách fg/bg:** đề xuất **K-means k=2 + dự phòng Canny** (trình bày ở mục 4.1).
  Chốt vì ảnh hưởng toàn bộ precision — nên test trên standard set trước khi lock.
- [ ] **Ngưỡng `bg_is_solid_px`** (variance pixel bg) → **tune bằng standard set (GS)**. Đề xuất
  ban đầu: `std(L) > 15` (trên thang 0–255) → không đặc.
- [ ] **Ngưỡng contrast candidate:** đề xuất `< 4.5` text thường, `< 3.0` chữ lớn/đồ hoạ — theo
  WCAG 2.1. Chốt cùng **bảng ngưỡng F0.4**.
- [ ] **Lab vs RGB cho K-means:** Lab chuẩn hơn perceptual nhưng cần `scikit-image` hoặc tự code
  chuyển đổi. RGB + numpy đủ đơn giản. Đề xuất: **Lab** để tách màu chính xác hơn — anh quyết.

## 9. TDD outline

- test: crop text trắng nền đen → `contrast_ratio_px` = 21.0 (±0.5).
- test: text xám nhạt nền trắng (WCAG fail) → candidate STY-01 được tạo.
- test: k-means tách fg/bg trên ảnh chữ đen nền trắng → 2 cluster đúng.
- test: element trong suốt (RGBA) → `opacity_px` < 1.0.
- test: nền gradient → `bg_is_solid_px=false`, `contrast_ratio_px=null`.
- test: element quá nhỏ (< 4px) → `contrast_ratio_px=null`, không crash.
- test: `dark_mode_ok` = false khi màn dark nhưng element có bg sáng hardcode.
- test: tất cả field ghi `color_px_source="vision"`.
- test: `disabled_color_similar=true` khi 2 element (disabled/enabled) màu gần nhau (ΔE < 5).
- test: antialiasing không làm lệch màu trội quá 10 ΔE so với màu thực.

## Trạng thái: spec ✅ — chờ chốt mục 8 (thuật toán fg/bg, ngưỡng) + F0.4 (đơn vị/ngưỡng contrast).
