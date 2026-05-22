# A6 — Icon/Graphic Detector (icon · đồ hoạ nhỏ → phát hiện, phân loại, khoanh vùng)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". **Mode A · B.** Tech: **Python + CV**.
> Phân biệt icon/đồ hoạ nhỏ (non-text, ít màu) khỏi ảnh-photo (nhiều màu) và text (A5).
> Là **feed** cho A3 Box Detector (A3 gọi A6 để classify vùng icon) + cấp crop cho A8 (emoji/glyph).
> Liên quan: [`A1-tree-parser.md`](A1-tree-parser.md) · [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A7-image-region-meta-reader.md`](A7-image-region-meta-reader.md) · [`A8`](#) · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm

Tìm và khoanh vùng tất cả **icon / đồ hoạ nhỏ non-text** trên màn hình:
- **Phân loại**: icon-glyph / icon-vector / logo nhỏ / badge / decorative-graphic; phân biệt rõ với:
  - **Ảnh-photo** (`image` role → A7): vùng lớn, nhiều màu, gradient phức tạp.
  - **Text glyph** (→ A5/A8): ký tự đơn lẻ nhìn giống icon (vd: ❌ ✓ →).
- **Mode A (có cây):** trích từ DOM/XML do A1 cấp (`<svg>`, icon-font class, `<img>` kích thước nhỏ). Kết quả độ tin cậy cao — ground truth.
- **Mode B (chỉ ảnh):** phát hiện bằng CV từ pixel — **độ tin cậy thấp hơn**, cần đánh dấu `source=vision`.
- **Cấp output** cho A3 (fuse vào `elements[]` với `role=icon`), cho A8 (crop icon để kiểm tra render/emoji-box), và cho Rule Engine (IMG-07 lệch tâm, IMG-08 placeholder, STY-13 contrast đồ hoạ).

**KHÔNG** đọc text, KHÔNG tính màu/contrast (A4/A8), KHÔNG quyết lỗi — chỉ phát hiện & phân loại vùng icon.

## 2. Input / Output

- **Input:**
  - PNG (full hoặc crop region từ A3).
  - *Mode A:* `elements[]` từ A1 (có `role`, `bbox`, `attrs.src/class`, tag).
  - *Mode B:* `elements[]` thô từ A3 (non-text regions) + meta `viewport{w,h,dpr}`.
- **Output:** danh sách `icon_regions[]` bổ sung vào `elements[]` (hoặc annotate vào element đã có):
```jsonc
{
  "id": "e42",
  "role": "icon",
  "subtype": "svg_inline | icon_font | img_small | bitmap_icon | decorative",
  "source": "dom | vision",
  "confidence": 0.85,
  "bbox": { "x": 0, "y": 0, "w": 24, "h": 24 },
  "bbox_norm": {},
  "color_count_approx": 3,       // ≤5 → đặc trưng icon; >20 → có thể ảnh photo
  "edge_density": 0.42,          // cao → icon rõ nét (vector/glyph-style)
  "template_match": "arrow_right | hamburger | close_x | search | null",
  "crop": "crops/e42.png",
  "parent": "e15"
}
```

## 3. Bốn bài toán con

a. **Mode A — trích từ cây:** duyệt `elements[]` A1, lọc icon theo tag/role/size.
b. **Mode B — phát hiện từ pixel:** tìm region nhỏ, ít màu, edge density cao.
c. **Phân loại subtype:** svg / icon-font / img nhỏ / bitmap / decorative.
d. **Template matching** icon phổ biến (tùy chọn): tăng recall cho placeholder-detect (IMG-08).

## 4. Kỹ thuật / lib (Python) — list + đề xuất

| Hướng | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| **Mode A — parse SVG inline** | `lxml` / `xml.etree` (A1 đã dùng) + regex class icon-font (`fa-*`, `material-icons`, `bi-*`) | chính xác, không cần CV | chỉ Mode A | ✅ **bắt buộc Mode A** |
| **Mode A — img nhỏ** | filter `elements[]` A1: `role=image` + `bbox.w ≤ 64px && h ≤ 64px` (ngưỡng tune) | đơn giản, deterministic | ngưỡng cứng dễ miss | ✅ heuristic đơn giản |
| **Mode B — contour + lọc size** | **OpenCV** `findContours` → lọc area nhỏ (e.g. 16×16–80×80px), aspect ≈ 1:1, edge density | không train, nhanh | miss icon nằm trong container flat | ✅ **core Mode B** |
| **Mode B — đếm màu** | **numpy** `np.unique` trên crop resize nhỏ (vd 32×32) → count màu khác biệt | đặc trưng mạnh (icon ≤ ~5 màu, photo >> 20) | ảnh bitonal cũng ít màu → cần kết hợp edge | ✅ đặc trưng phụ |
| **Mode B — edge density** | **OpenCV** Canny → tỉ lệ edge-pixel / tổng-pixel vùng | icon vector → edge density cao + đều; ảnh → thấp/loang | phụ thuộc ngưỡng Canny | ✅ đặc trưng phụ |
| **Template matching icon phổ biến** | **OpenCV** `matchTemplate` với bộ template (arrow, hamburger, X, search, ☰, ✕...) | recall tốt cho icon hay gặp, deterministic | chỉ match được icon biết trước; scale/rotation sensitive | ✅ tùy chọn — bật cho `template_match` field |
| **ML pretrained (open-vocab)** | **OmniParser** (icon segment) / **GroundingDINO** (`icon`, `button icon`, `logo`) | recall cao, nhận icon bất kỳ | ⚠ động tới nguyên tắc "no-YOLO" — xem mục 8 | tùy chọn — **anh quyết** (mục 8) |
| **Icon classification pretrained** | **CLIP** (zero-shot: `"arrow icon"` vs `"photo"`) | zero-shot, không label | inference chậm hơn CV thuần | tùy chọn nhẹ hơn OmniParser |

> ⚠ **Làm rõ nguyên tắc "no-YOLO":** cấm YOLO là để tránh **train lại per app / per icon set**.
> Dùng **general pretrained** (OmniParser, GroundingDINO, CLIP) → không train lại → vẫn hợp
> zero-reference. Nhưng nếu muốn **thuần CV** (không ML), OpenCV contour + màu + edge + template
> matching vẫn chạy được — recall thấp hơn với icon lạ. Quyết định để anh chốt ở mục 8.

## 5. Pipeline A6 (đề xuất)

### Mode A (có cây — nhanh, chính xác):
1. Duyệt `elements[]` A1; lọc: `tag=svg` / `tag=img` với `w≤64 && h≤64` / class khớp regex icon-font (`fa-*|material-icons|bi-*|icon-*|ico-*`) / `role=img` + `aria-label` ngắn.
2. Gán `role=icon`, `subtype` theo nguồn (`svg_inline | icon_font | img_small`).
3. Crop vùng → emit. `source=dom`, `confidence=0.95`.

### Mode B (chỉ ảnh — CV pipeline):
1. Nhận non-text regions từ A3 (hoặc quét toàn ảnh nếu A3 chưa xong).
2. **Lọc theo size:** bbox trong range icon (16–80px cạnh ngắn; aspect 0.5–2.0). Loại bỏ text-box (từ A5).
3. **Đặc trưng mỗi vùng:**
   - `color_count`: resize crop → 32×32 → `np.unique` → đếm màu khác biệt.
   - `edge_density`: Canny trên crop → % pixel edge.
4. **Classify sơ bộ:**
   - `color_count ≤ 8` **và** `edge_density ≥ 0.15` → **candidate icon**.
   - `color_count > 20` → không phải icon → chuyển sang A7 (ảnh photo).
5. **Template match** (tùy chọn): nếu bật, chạy `matchTemplate` trên candidate icon với bộ template chuẩn (multi-scale).
6. **ML add-on** (tùy chọn): nếu bật OmniParser/GroundingDINO → overlay kết quả, boost confidence.
7. Crop → emit `icon_regions[]` với `source=vision`, `confidence` theo độ chắc.

## 6. Ranh giới với các analyzer khác (BẮT BUỘC giữ đúng)

| Analyzer | Ranh giới với A6 |
|---|---|
| **A3 Box/Layout Detector** | A3 gọi A6 để **classify** vùng non-text nhỏ thành `icon` vs `image` vs `container`. A6 KHÔNG tự chạy contour từ đầu nếu A3 đã cấp region. |
| **A7 Image Region Reader** | **A6 = icon/đồ hoạ nhỏ, ít màu (≤ ~8 màu khác biệt).** **A7 = ảnh-photo, vùng lớn, nhiều màu.** Phần phân loại "icon vs photo" do A6 quyết; A7 chỉ nhận vùng đã được đánh dấu `role=image`. |
| **A5 OCR / Text Extractor** | A5 trả text-box; A6 nhận danh sách text-box để **loại trừ** (không classify text thành icon). |
| **A8 Pixel/Glyph Inspector** | A6 cấp **crop icon** cho A8 để kiểm tra render emoji-box / icon-font sai glyph (TYP-14). |
| **A12 Interactivity Classifier** | A12 dùng vùng icon (từ A6) để suy luận "nút icon-only" (CMP-02). |

## 7. Tiêu chí phục vụ

| Tiêu chí | Cách A6 đóng góp |
|---|---|
| **IMG-07** Icon lệch tâm trong nút | A6 cấp `bbox` icon → Rule R1 tính offset so tâm nút (A3 bbox) |
| **IMG-08** Icon placeholder / chưa load | A6 phát hiện vùng nhỏ có pattern placeholder (màu đồng nhất + outline / dấu `?`) → candidate cho Rule R3 + A9 |
| **STY-04** Icon tàng hình dark mode | A6 cấp crop icon → A4 đo contrast icon vs nền → Rule R2 |
| **STY-13** Tương phản icon/đồ hoạ chức năng < 3:1 | A6 định danh vùng icon → A4 đo contrast → Rule R2 |
| **CMP-02** Nút icon-only không nhãn | A6 cấp icon + A12 suy luận interactive → Rule R1 bắt thiếu label |
| **TYP-14** Emoji/icon-font render sai | A6 crop vùng icon → A8 soi pixel emoji-box |
| **IMG-06** Icon sai ngữ nghĩa | A6 cấp `template_match` → Agent G5 xác nhận ngữ cảnh |
| **CONS-04** Phong cách icon không nhất quán (outline vs filled) | A6 `subtype` + A10 perceptual hash → Agent G6 |

## 8. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Phase 1 dùng ML pretrained cho icon detect (OmniParser/GroundingDINO) hay thuần CV?**
  Đề xuất: **core CV thuần** (contour + màu + edge + template) cho Phase 1; **thêm ML nếu golden set cho thấy recall icon < 70%**. Lý do: CV đủ bắt được icon phổ biến, tránh dependency nặng; ML add-on dễ bật sau.
- [ ] **Ngưỡng size icon (min/max px):** đề xuất 16–80px cạnh ngắn, aspect 0.5–2.0. Tune bằng golden set.
- [ ] **Bộ template matching:** có dựng sẵn bộ template icon phổ biến (arrow, hamburger, X, search, back, share...) không? Khoảng 20–30 template đủ bắt IMG-08 placeholder phổ biến.
- [ ] **CLIP zero-shot** như lớp giữa (rẻ hơn OmniParser): query `"icon"` vs `"photo"` vs `"text"` → có muốn thử không, hay đủ CV thuần?

## 9. Edge cases (BẮT BUỘC xử lý)

- **Icon-font render thành glyph Unicode:** A5 OCR có thể đọc ký tự → A6 nhận cờ `text_region` từ A5 và **không re-classify thành icon**. Phân biệt bằng font-family (Mode A) hoặc bằng kích thước + isolation (Mode B).
- **SVG inline nhiều màu (illustration):** kích thước lớn → không phải icon → A7. Dùng `color_count` + `bbox area` để lọc.
- **Icon badge (số nổi trên icon):** A6 nên giữ cả icon chính + badge là 2 element riêng (containment qua A3).
- **Icon placeholder (ô vuông xám, dấu ?):** đây là lỗi IMG-08 — A6 vẫn phải detect như icon region, gắn thêm cờ `possible_placeholder=true` để Rule R3 xử lý.
- **Flat design / monochrome UI:** icon màu trắng/đen trên nền trắng/đen — edge density thấp → confidence thấp; đánh dấu, không bỏ qua.
- **Icon trong ảnh (logo trên banner):** A7 đã crop vùng ảnh → A6 KHÔNG chạy lại trên toàn ảnh mà chỉ nhận vùng ngoài ảnh. A11 lo icon/text trong ảnh.

## 10. TDD outline (khi vào code)

- test Mode A: element `<img w=24 h=24>` → classify `role=icon`, `subtype=img_small`, `source=dom`.
- test Mode A: element có class `fa-arrow-right` → classify `role=icon`, `subtype=icon_font`.
- test Mode B: crop icon 24×24 ít màu (3 màu) + edge cao → candidate icon, confidence ≥ 0.7.
- test Mode B: crop ảnh photo 100×100 nhiều màu → **không** classify icon (`color_count > 20`).
- test Mode B: crop text glyph từ A5 → không double-classify thành icon.
- test template match: ảnh mũi tên phải → `template_match = "arrow_right"`.
- test icon placeholder (ô vuông xám) → `possible_placeholder=true`.
- test ranh giới A6/A7: vùng 200×200px nhiều màu → đẩy sang A7, không giữ lại A6.
- test tất cả output `source=vision` ở Mode B, `confidence < 1`.
- test không crash khi không tìm thấy icon nào → trả `[]`.

## Trạng thái: spec ✅ — chờ chốt mục 8 (CV thuần vs +ML pretrained, bộ template, ngưỡng size).
