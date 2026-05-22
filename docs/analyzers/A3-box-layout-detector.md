# A3 — Box/Layout Detector (ảnh → elements/bbox/hierarchy)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". **Mode B (không cây).** Tech: **Python + CV**.
> Đây là **xương sống của Mode B** — quyết định Mode B có chạy được nhóm LAY hay không.
> Liên quan: [`A1-tree-parser.md`](A1-tree-parser.md) · [`A5`](#) OCR · [`A6`](#) Icon · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm
Khi **không có cây**, từ screenshot dựng `elements[]`: **bbox + role thô + containment
(parent/child) + visible** — làm nền cho rule layout + crop cho analyzer pixel. **Fuse** với
text-box (A5 OCR) và icon (A6). **KHÔNG** đọc text/màu (analyzer khác). `z`-order & `interactive`
là **suy đoán** → confidence thấp.

## 2. Input / Output
- **Input:** PNG + meta `viewport{w,h,dpr}`.
- **Output:** `elements[]` (`source=vision`, `confidence<1`): `bbox`, `bbox_norm`, `role` thô
  (`container|text|image|icon|button?|divider`), `parent/children` (containment hình học),
  `visible`. + dữ liệu để A0 tiền tính `relations`.

## 3. Bốn bài toán con
a. **Region proposal** — tìm vùng/box ứng viên.
b. **Text vs non-text** — text từ A5; non-text từ CV.
c. **Classify role thô**.
d. **Hierarchy** — containment + grouping (list/row/col).

## 4. Kỹ thuật / lib (Python) — list + đề xuất
**Hướng đề xuất Phase 1: HYBRID classical-CV + OCR fusion (kiểu UIED)** — KHÔNG cần train,
hợp tinh thần zero-reference.

| Hướng | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Classical CV (non-text) | **OpenCV** (Canny · `findContours` · morphology · `connectedComponents` · Hough lines) | không train, nhanh, deterministic | nhiễu với flat design/gradient, over/under-segment | ✅ **core** |
| Bộ detect screenshot→elements sẵn | **UIED** (CV+OCR fusion, mã nguồn mở) | đúng bài này, không train | repo cũ → cần port/adapt | ✅ tham khảo/port logic |
| Text regions | **PaddleOCR (det)** / EAST | box text chính xác | (đã làm ở A5) | dùng output **A5** |
| GUI detector ML **pretrained** | **OmniParser** (icon/element) / **GroundingDINO** (open-vocab) | recall component/icon cao | ⚠ nền YOLO/transformer — *động tới nguyên tắc "no YOLO"* | tùy chọn — **anh quyết** (mục 8) |
| Segmentation | **SAM / FastSAM** | segment không train | nặng, over-segment, không gán role | fallback tùy chọn |
| Clustering/hierarchy | **numpy/scipy** (IoU, containment, alignment-cluster) | deterministic | — | ✅ |

> ⚠ **Làm rõ nguyên tắc:** "KHÔNG object detection kiểu YOLO" trong dự án là để tránh **gán
> nhãn / train lại per app**. Một **detector general PRETRAINED** (OmniParser/GroundingDINO)
> KHÔNG đòi train lại → có thể dùng mà vẫn zero-reference. Nhưng nếu anh muốn thuần CV (không
> ML), core OpenCV+OCR vẫn chạy — chỉ **recall component thấp hơn**.

## 5. Pipeline A3 (đề xuất)
1. **Tiền xử lý:** grayscale + denoise (giữ bản màu cho A4).
2. **Non-text regions:** Canny → dilate → `findContours` → lọc theo area/aspect → bbox ứng viên
   (card/container/divider); `connectedComponents` cho khối đặc.
3. **Text boxes:** lấy từ **A5 OCR**.
4. **Fuse:** merge/loại trùng theo IoU; text nằm trong box → đánh `child`.
5. **Classify role thô (heuristic):** text→`text`; box bo góc chứa text→`button?`/`card`;
   vùng ảnh→`image` (chuyển A6/A7); line mảnh dài→`divider`.
6. **Hierarchy:** containment (box-in-box) → `parent/children`; grouping theo
   alignment/proximity (clustering) → suy list/row/col.
7. **Emit** `elements[]` + `confidence` theo độ chắc của từng bước.

## 6. Hạn chế Mode B (BẮT BUỘC đánh dấu confidence thấp)
- `parent/child` = suy từ hình học, KHÔNG phải DOM thật.
- `z`-order/occlusion = đoán (vùng bị cắt ⇒ có thể bị che).
- `role` thô, dễ nhầm button/card/text-label.
- `interactive` = KHÔNG biết → để **A12** đoán.
- over/under-segmentation là nguồn nhiễu chính.
→ Toàn bộ `source=vision`; rule engine chỉ chạy **tập con** tính được từ box+pixel.

## 7. Tiêu chí phục vụ
Cấp `bbox`/containment cho gần như mọi **LAY-*** (overlap/align/overflow/occlusion/scroll),
nền cho **CMP** (cùng A12/A6) và **crop theo element** cho A4/A8. → Là **điều kiện để Mode B
chạy được nhóm LAY** (nhóm "vàng").

## 8. Open decisions (cần anh chốt — lựa chọn lớn)
- [ ] **Phase 1 dùng pretrained ML detector (OmniParser/GroundingDINO) như add-on, hay thuần
  CV+OCR?** Đề xuất: **core CV+OCR trước**; chỉ thêm ML-detector nếu golden set cho thấy recall
  component quá thấp. (Quyết định này động tới nguyên tắc "no YOLO" — nên hỏi anh.)
- [ ] Ngưỡng lọc region (min area, aspect ratio) → **tune bằng golden set (GS)**.

## 9. TDD outline
- test contour detect trên ảnh card đơn giản → đúng số box.
- test fuse OCR text-box vào container (containment đúng).
- test role thô: divider (line mảnh), text, image-region.
- test hierarchy containment + alignment grouping (list 3 item thẳng hàng).
- test mọi element `source=vision`, `confidence<1`.
- test ảnh flat-design khó → không crash; recall đo bằng GS (không hard-assert).

## Trạng thái: spec ✅ — chờ chốt mục 8 (CV thuần vs +ML detector).
