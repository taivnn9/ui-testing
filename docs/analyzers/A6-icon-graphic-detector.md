# A6 — Icon/Graphic Detector (icon · đồ hoạ nhỏ → phát hiện, phân loại, khoanh vùng)

> **TL;DR:** Phát hiện & phân loại icon/đồ hoạ nhỏ non-text bằng CV (contour + đếm màu + edge + template match), phân biệt với ảnh-photo (A7) và text-glyph (A5); cấp `icon_regions[]` cho A3/A8 + candidate IMG/STY/CMP.

> Phase 1, nhóm "dựng cấu trúc". Tech: **Python + CV**.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A7-image-region-meta-reader.md`](A7-image-region-meta-reader.md) · [`A8`](#)

## 1. Trách nhiệm
Tìm & khoanh vùng mọi **icon / đồ hoạ nhỏ non-text**:
- **Phân loại:** icon-glyph / icon-vector / logo nhỏ / badge / decorative-graphic; phân biệt với:
  - **Ảnh-photo** (`image` role → A7): vùng lớn, nhiều màu, gradient phức tạp.
  - **Text glyph** (→ A5/A8): ký tự đơn nhìn giống icon (❌ ✓ →).
- **Phát hiện từ pixel** bằng CV — tin cậy thấp hơn cây, đánh dấu `source=vision`.
- **Cấp output** cho A3 (fuse `role=icon`), A8 (crop kiểm render/emoji-box), Rule Engine (IMG-07 lệch tâm, IMG-08 placeholder, STY-13 contrast đồ hoạ).

KHÔNG đọc text, KHÔNG tính màu/contrast (A4/A8), KHÔNG quyết lỗi.

## 2. Input / Output
- **Input:** PNG (full hoặc crop region từ A3) + `elements[]` thô từ A3 (non-text) + meta `viewport{w,h,dpr}`.
- **Output:** `icon_regions[]` bổ sung/annotate vào `elements[]`:
```jsonc
{
  "id": "e42",
  "role": "icon",
  "subtype": "img_small | bitmap_icon | decorative",
  "source": "vision",
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

## 3. Hai bài toán con
- a. **Phát hiện từ pixel:** region nhỏ, ít màu, edge density cao.
- b. **Template matching** icon phổ biến (tùy chọn): tăng recall placeholder (IMG-08).

## 4. Kỹ thuật / lib (Python)
| Hướng | Lib/tool | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Phát hiện — contour + lọc size | **OpenCV** `findContours` → lọc area nhỏ (~16×16–80×80px), aspect ≈ 1:1, edge density | không train, nhanh | miss icon trong container flat | ✅ **core** |
| Đếm màu | **numpy** `np.unique` trên crop resize 32×32 | đặc trưng mạnh (icon ≤ ~5 màu, photo >>20) | ảnh bitonal cũng ít màu → cần kết hợp edge | ✅ đặc trưng phụ |
| Edge density | **OpenCV** Canny → edge-pixel / tổng-pixel | icon vector → cao+đều; ảnh → thấp/loang | phụ thuộc ngưỡng Canny | ✅ đặc trưng phụ |
| Template matching | **OpenCV** `matchTemplate` (arrow, hamburger, X, search, ☰, ✕...) | recall tốt icon hay gặp, deterministic | chỉ match icon biết trước; scale/rotation sensitive | ✅ tùy chọn — field `template_match` |
| ML pretrained (open-vocab) | **OmniParser** / **GroundingDINO** (`icon`, `button icon`, `logo`) | recall cao, icon bất kỳ | ⚠ động "no-YOLO" — mục 8 | tùy chọn — **anh quyết** |
| Icon classification pretrained | **CLIP** (zero-shot `"arrow icon"` vs `"photo"`) | zero-shot, không label | chậm hơn CV thuần | tùy chọn nhẹ hơn OmniParser |

> ⚠ "No-YOLO" = tránh **train lại per app / per icon set**. Dùng **general pretrained** (OmniParser, GroundingDINO, CLIP) → không train lại → vẫn zero-reference. Thuần CV (OpenCV contour+màu+edge+template) cũng chạy, recall thấp hơn với icon lạ.

## 5. Pipeline A6 (đề xuất)
1. Nhận non-text regions từ A3 (hoặc quét toàn ảnh nếu A3 chưa xong).
2. **Lọc size:** bbox trong range icon (16–80px cạnh ngắn; aspect 0.5–2.0). Loại text-box (A5).
3. **Đặc trưng mỗi vùng:** `color_count` (resize 32×32 → `np.unique`); `edge_density` (Canny → % pixel edge).
4. **Classify sơ bộ:**
   - `color_count ≤ 8` **và** `edge_density ≥ 0.15` → **candidate icon**.
   - `color_count > 20` → không phải icon → A7 (ảnh photo).
5. **Template match** (tùy chọn): `matchTemplate` multi-scale trên candidate.
6. **ML add-on** (tùy chọn): OmniParser/GroundingDINO → overlay, boost confidence.
7. Crop → emit `icon_regions[]` (`source=vision`, `confidence` theo độ chắc).

## 6. Ranh giới với analyzer khác (BẮT BUỘC giữ đúng)
| Analyzer | Ranh giới với A6 |
|---|---|
| **A3 Box/Layout** | A3 gọi A6 để **classify** vùng non-text nhỏ thành `icon`/`image`/`container`. A6 KHÔNG tự chạy contour nếu A3 đã cấp region. |
| **A7 Image Region** | A6 = icon/đồ hoạ nhỏ (≤ ~8 màu). A7 = ảnh-photo lớn, nhiều màu. A6 quyết "icon vs photo"; A7 chỉ nhận vùng đã `role=image`. |
| **A5 OCR** | A5 trả text-box; A6 nhận để **loại trừ** (không classify text thành icon). |
| **A8 Glyph Inspector** | A6 cấp **crop icon** cho A8 kiểm emoji-box / icon-font sai glyph (TYP-14). |
| **A12 Interactivity** | A12 dùng vùng icon (A6) suy "nút icon-only" (CMP-02). |

## 7. Tiêu chí phục vụ
| Tiêu chí | Cách A6 đóng góp |
|---|---|
| **IMG-07** Icon lệch tâm trong nút | A6 cấp `bbox` icon → Rule R1 tính offset so tâm nút |
| **IMG-08** Icon placeholder / chưa load | A6 phát hiện vùng nhỏ pattern placeholder (màu đồng nhất + outline / dấu `?`) → candidate R3 + A9 |
| **STY-04** Icon tàng hình dark mode | A6 cấp crop icon → A4 đo contrast → Rule R2 |
| **STY-13** Contrast icon/đồ hoạ chức năng < 3:1 | A6 định danh vùng icon → A4 đo contrast → Rule R2 |
| **CMP-02** Nút icon-only không nhãn | A6 cấp icon + A12 suy interactive → Rule R1 bắt thiếu label |
| **TYP-14** Emoji/icon-font render sai | A6 crop vùng icon → A8 soi pixel emoji-box |
| **IMG-06** Icon sai ngữ nghĩa | A6 cấp `template_match` → Agent G5 xác nhận ngữ cảnh |
| **CONS-04** Phong cách icon không nhất quán (outline vs filled) | A6 `subtype` + A10 pHash → Agent G6 |

## 8. Open decisions (cần anh chốt)
- [ ] **Phase 1 ML pretrained (OmniParser/GroundingDINO) hay thuần CV?** Đề xuất **core CV thuần** (contour+màu+edge+template); thêm ML nếu standard set cho thấy recall icon < 70%.
- [ ] **Ngưỡng size icon:** đề xuất 16–80px cạnh ngắn, aspect 0.5–2.0. Tune GS.
- [ ] **Bộ template matching:** dựng sẵn ~20–30 template icon phổ biến (arrow, hamburger, X, search, back, share...) đủ bắt IMG-08?
- [ ] **CLIP zero-shot** như lớp giữa (rẻ hơn OmniParser): query `"icon"` vs `"photo"` vs `"text"` — có thử không?

## 9. Edge cases (BẮT BUỘC xử lý)
- **Icon-font render thành glyph Unicode:** A5 OCR đọc được ký tự → A6 nhận cờ `text_region` từ A5 và **không re-classify thành icon**. Phân biệt bằng kích thước + isolation.
- **SVG inline nhiều màu (illustration):** kích thước lớn → không phải icon → A7. Lọc bằng `color_count` + `bbox area`.
- **Icon badge (số nổi trên icon):** giữ icon chính + badge là 2 element riêng (containment qua A3).
- **Icon placeholder (ô vuông xám, dấu ?):** lỗi IMG-08 — vẫn phát hiện như icon region, gắn `possible_placeholder=true` cho Rule R3.
- **Flat design / monochrome:** icon trắng/đen trên nền trắng/đen → edge density thấp → confidence thấp; đánh dấu, không bỏ qua.
- **Icon trong ảnh (logo trên banner):** A7 đã crop vùng ảnh → A6 KHÔNG chạy lại toàn ảnh, chỉ nhận vùng ngoài ảnh. A11 lo icon/text trong ảnh.

## 10. TDD outline
- crop icon 24×24 ít màu (3 màu) + edge cao → candidate icon, confidence ≥ 0.7.
- crop ảnh photo 100×100 nhiều màu → **không** classify icon (`color_count > 20`).
- crop text glyph từ A5 → không double-classify thành icon.
- template match: ảnh mũi tên phải → `template_match = "arrow_right"`.
- icon placeholder (ô vuông xám) → `possible_placeholder=true`.
- ranh giới A6/A7: vùng 200×200px nhiều màu → đẩy sang A7.
- mọi output `source=vision`, `confidence < 1`.
- không tìm thấy icon → trả `[]`, không crash.

## Trạng thái: spec ✅ — chờ chốt mục 8 (CV thuần vs +ML pretrained, bộ template, ngưỡng size).
