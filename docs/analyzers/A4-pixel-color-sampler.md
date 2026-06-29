# A4 — Pixel Color Sampler (contrast/dark/opacity từ pixel thực)

> **TL;DR:** Đo màu/contrast/opacity THỰC TẾ từ pixel (tách fg/bg, k-means, WCAG) — nguồn màu duy nhất vì hệ thống không có computed-style; ghi vào `element.style.*` + candidate STY.

> Phase 1, nhóm "đo diện mạo".
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (cấp crop) · [`A8-pixel-glyph-inspector.md`](A8-pixel-glyph-inspector.md)

## 1. Trách nhiệm
Đo màu/contrast/opacity từ pixel — nguồn duy nhất cho màu (không có computed-style):
- Lấy **crop element** (A3) → tách **foreground** (chữ/icon) vs **background**.
- Trích **màu trội** mỗi vùng → tính **WCAG contrast_ratio** từ pixel.
- Phát hiện **dark-mode render** đúng/sai (cả màn hay chỉ một vùng không đổi).
- Đo **opacity hiệu dụng** từ alpha / blend.
- Bắt **màu disabled** (so với sibling enabled tương tự).

KHÔNG đọc text/content (A5); KHÔNG phân loại element (A3/A6).

## 2. Input / Output
**Input:**
- PNG full + meta `viewport{w,h,dpr}`, `theme` (`light|dark`).
- `elements[]` từ A3 (`bbox`, `role`, `text` nếu biết) — để crop.
- *Tùy chọn:* `bg_layer_crop` (lớp nền dưới nếu element trong suốt — A0 cấp).

**Output:** thêm field `style.*` vào `elements[]` (`source="vision"`):
```jsonc
"style": {
  "color_px":       [17, 24, 39],       // RGB màu trội foreground
  "bg_color_px":    [255, 255, 255],    // RGB màu trội background
  "contrast_ratio_px": 12.4,            // WCAG từ pixel (null nếu không tách được)
  "color_px_source": "vision",
  "bg_is_solid_px": true,               // bg đặc hay ảnh/gradient?
  "dominant_colors": [[17,24,39,0.65],[200,210,220,0.35]], // [(RGB, weight)]
  "opacity_px": 0.9,                    // opacity hiệu dụng từ pixel
  "dark_mode_ok": true,                 // null nếu theme không rõ
  "disabled_color_similar": false       // so với sibling enabled (null nếu không có)
}
```
Thêm `pixel_color_result` vào `candidate_issues[]` (rule A4-R2) nếu `contrast_ratio_px < 4.5` (text thường) hoặc `< 3.0` (đồ hoạ/chữ lớn).

## 3. Bốn bài toán con
- a. **Crop & tách fg/bg** — cắt vùng, tách pixel foreground vs background.
- b. **Trích màu trội** — từ tập pixel fg và bg.
- c. **Tính contrast WCAG** — relative luminance → ratio.
- d. **Suy dark-mode, opacity, disabled** — từ phân tích màu vùng.

## 4. Kỹ thuật / lib (Python)

| Việc | Lib / cách | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Đọc/crop/resize ảnh | **Pillow** + **numpy** | gọn, nhanh | — | ✅ **core** |
| Tách fg/bg theo màu | **K-means** (`sklearn.cluster.KMeans` k=2–4) trên pixel | tổng quát, không train | chậm nếu vùng lớn; cần seed ổn định | ✅ **primary** |
| Tách fg/bg thay thế | **Histogram median-cut** (Pillow `quantize`) | nhanh, không dep | kém với gradient phức tạp | ✅ fallback nhanh |
| Tách fg theo stroke chữ | **OpenCV Canny + dilate** (cạnh chữ = fg) | hợp text rõ nét | cần crop chữ nguyên vẹn | ✅ cho `role=text` |
| Màu trội từ cluster | **numpy weighted mean** theo label | deterministic | — | ✅ |
| Luminance & contrast WCAG | **tự code** (`L = 0.2126R+0.7152G+0.0722B` linearised) | tái dùng R2 | — | ✅ **bắt buộc tự code** |
| Alpha/opacity từ RGBA | **numpy** (channel A / blend) | chính xác | cần alpha hoặc lớp nền | ✅ |
| Dark mode toàn màn | **numpy mean(L channel)** (thấp → dark) | đơn giản | không bắt vùng cục bộ sai | ✅ đủ dùng |
| So màu disabled vs sibling | **Euclidean RGB / ΔE CIE76** (numpy) | tường minh | cần sibling rõ | ✅ |

> ⚠ **Không dùng ML/neural** cho màu — đây là bài tính tất định từ pixel. K-means là phân cụm không giám sát, không train lại per app → đúng zero-reference.

### 4.1 Tách fg/bg — chi tiết
**`role=text/button` (chứa chữ):**
1. Crop → **Lab** (perceptual) để phân cụm đều hơn RGB.
2. K-means k=2: cluster 1 = fg (chữ), cluster 2 = bg.
3. Chọn cluster nhỏ hơn = fg (chữ ít pixel hơn nền); kiểm bằng edge density.
4. Dự phòng: Canny → pixel cạnh → fg; còn lại → bg.

**`role=image/icon`:**
- Không có "chữ" → màu trội tổng thể bằng k-means k=3–5 → `dominant_colors`.
- Contrast tính giữa màu sáng nhất và tối nhất trong tập trội → proxy đồ hoạ.

**Nền ảnh sau text (khó nhất):**
- Lấy crop lớp dưới (A0 cấp nếu có z-order) → trung vị màu → bg.
- Dự phòng: blur crop → màu trung vị góc (ít chữ nhất).

## 5. Pipeline A4 (đề xuất)
1. **Nhận element** cần đo màu (ưu tiên `role=text|button|icon|toggle`, `visible=true`).
2. **Crop** theo `bbox`; resize max 200×200 nếu cần.
3. **Tách fg/bg** (mục 4.1) → pixel sets.
4. **Màu trội fg/bg:** weighted mean trong cluster → `color_px`, `bg_color_px`; ghi `dominant_colors`.
5. **`bg_is_solid_px`:** variance pixel bg > ngưỡng (tune GS) → `false` + note "gradient/image".
6. **`contrast_ratio_px`** (WCAG): relative luminance → ratio; `null` nếu không tách được.
7. **Dark mode:** nếu `screen.theme=dark`, kiểm `bg_color_px` vùng tối vs màu sáng hard-coded → cờ nghi STY-03.
8. **`opacity_px`:** ảnh có alpha (RGBA) → mean alpha vùng; else ước lượng từ blend.
9. **Disabled:** nếu A12 đoán element disabled → so màu sibling nearest enabled → `disabled_color_similar`.
10. **Emit** vào `elements[].style.*` + `candidate_issues[]` nếu vượt ngưỡng.

## 6. Tiêu chí phục vụ
| Mã | Tiêu chí | Vai trò A4 |
|---|---|---|
| **STY-01** | Contrast chữ/nền < WCAG 4.5:1 | ✅ **chính** — nguồn duy nhất cho màu |
| **STY-02** | Chữ tàng hình (trắng/trắng) | ✅ contrast_ratio_px ~ 1.0 → candidate |
| **STY-03** | Dark-mode không đổi màu | ✅ `dark_mode_ok` + bắt màu sáng hard-code trong theme tối |
| **STY-04** | Icon/viền tàng hình trong theme | ✅ contrast đồ hoạ (ngưỡng 3:1) |
| **STY-05** | Opacity sai | ✅ `opacity_px` |
| **STY-07** | Disabled không phân biệt enabled | ✅ `disabled_color_similar` |
| **STY-13** | Contrast icon/đồ hoạ chức năng < 3:1 | ✅ contrast từ dominant_colors icon |
| **STY-10** | Gradient/banding lỗi render | ⚠ tín hiệu phụ từ variance bg |

## 7. Edge cases (BẮT BUỘC xử lý)
- **Text antialiasing:** pixel viền pha màu fg/bg → bỏ pixel "pha" (màu trung gian 20–80% giữa 2 cluster) trước khi tính màu trội.
- **Nền nhiều màu:** bg_color_px trung vị → contrast "trung bình", dễ miss. → Tính contrast **worst-case**: bg màu gần fg nhất (nhỏ nhất trong dominant_colors bg) → báo conservative.
- **Crop lệch:** bbox A3 sai → màu vô nghĩa. → Thêm `crop_confidence` (= confidence bbox A3); nếu < ngưỡng → `contrast_ratio_px=null`.
- **Transparent/RGBA:** channel A = opacity thực. → Blend với nền trắng/đen theo quy ước trước khi đo.
- **Text màu gradient:** fg không đồng nhất → k-means >2 cluster chữ. → Lấy màu trội nhất fg; ghi `color_px_quality="gradient"`.
- **Emoji/icon nhiều sắc:** không có fg/bg rõ → skip contrast; chỉ ghi dominant_colors.
- **Element < 4×4 px:** không đủ pixel phân cụm → `contrast_ratio_px=null`, confidence thấp.

## 8. Open decisions (cần anh chốt)
- [ ] **Thuật toán tách fg/bg:** đề xuất **K-means k=2 + dự phòng Canny** (mục 4.1). Test trên standard set trước khi lock.
- [ ] **Ngưỡng `bg_is_solid_px`** (variance bg) → tune GS. Đề xuất: `std(L) > 15` (thang 0–255) → không đặc.
- [ ] **Ngưỡng contrast candidate:** `< 4.5` text thường, `< 3.0` chữ lớn/đồ hoạ (WCAG 2.1). Chốt cùng **F0.4**.
- [ ] **Lab vs RGB cho K-means:** Lab chuẩn perceptual hơn (cần `scikit-image` hoặc tự code chuyển), RGB+numpy đơn giản hơn. Đề xuất **Lab**.

## 9. TDD outline
- text trắng nền đen → `contrast_ratio_px` = 21.0 (±0.5).
- text xám nhạt nền trắng (WCAG fail) → candidate STY-01.
- k-means tách fg/bg ảnh chữ đen nền trắng → 2 cluster đúng.
- element RGBA → `opacity_px` < 1.0.
- nền gradient → `bg_is_solid_px=false`, `contrast_ratio_px=null`.
- element < 4px → `contrast_ratio_px=null`, không crash.
- `dark_mode_ok=false` khi màn dark nhưng element bg sáng hardcode.
- mọi field ghi `color_px_source="vision"`.
- `disabled_color_similar=true` khi 2 element disabled/enabled màu gần (ΔE < 5).
- antialiasing không lệch màu trội quá 10 ΔE so màu thực.

## Trạng thái: spec ✅ — chờ chốt mục 8 (thuật toán fg/bg, ngưỡng) + F0.4 (đơn vị/ngưỡng contrast).
