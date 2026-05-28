# A11 — Face / Text-in-image Detector (trong vùng ảnh: khuôn mặt + text embedded)

> Bóc tách chi tiết. Phase 1, nhóm "đo diện mạo". **Mode B (vision-only — thực tế cả 2 mode dùng
> được, nhưng chỉ phát huy ở Mode B).** Tech: **Python + pretrained model nhẹ**.
> ⚠ **Ưu tiên thấp** — có thể để sau golden set nếu cần tiết kiệm effort Phase 1.
> Liên quan: [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A7-image-region-meta-reader.md`](A7-image-region-meta-reader.md) · [`A6-icon-graphic-detector.md`](A6-icon-graphic-detector.md) · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm

**Chạy BÊN TRONG vùng ảnh-photo** đã được A7 xác định. Hai nhiệm vụ độc lập:

### 1a. Face Detector — bắt lỗi crop cắt mặt (IMG-04)
Phát hiện **khuôn mặt** trong vùng ảnh:
- Xác định xem mặt có bị **cắt bởi boundary vùng ảnh** không (bbox mặt chạm/vượt edge của vùng).
- Tín hiệu: candidate lỗi IMG-04 "Crop sai — cắt mất phần quan trọng".
- **KHÔNG** nhận dạng danh tính người.

### 1b. Text-in-image Tagger — phân biệt text UI vs text nằm trong ảnh
Đánh dấu các text segment (từ A5 OCR) nằm **bên trong vùng ảnh** là `"in_image"` → downstream (Rule R4, Agent G1) KHÔNG nhầm là text UI bị thiếu/không-render:
- Text trên banner ảnh, logo có chữ, text sản phẩm trên ảnh → hợp lệ, KHÔNG phải lỗi text UI.
- Làm rõ phạm vi: A11 KHÔNG check nội dung text đó đúng/sai — chỉ đánh dấu nguồn gốc.

**KHÔNG** phân tích nội dung ảnh, KHÔNG nhận dạng người, KHÔNG check text ngoài vùng ảnh.

## 2. Input / Output

- **Input:**
  - Crop vùng ảnh (từ A7) — PNG từng vùng `role=image`.
  - Danh sách `text_segments[]` từ A5 (có bbox) để đối chiếu.
  - `elements[]` với `role=image` + bbox vùng (để biết boundary).
- **Output:**

**1a. Face results** — annotate vào element ảnh:
```jsonc
{
  "element_id": "e25",
  "faces_detected": [
    {
      "bbox": { "x": 10, "y": 5, "w": 80, "h": 90 },   // relative trong crop vùng ảnh
      "confidence": 0.91,
      "is_cropped": true,         // bbox mặt chạm/vượt edge vùng ảnh → nghi IMG-04
      "crop_direction": ["top", "left"]   // phía nào bị cắt
    }
  ],
  "source": "vision",
  "face_detector": "mediapipe | opencv_dnn | haarcascade"
}
```

**1b. Text-in-image tagging** — annotate vào `text_segments[]` của A5:
```jsonc
{
  "segment_id": 42,
  "in_image_region": true,       // bbox segment nằm trong bbox vùng ảnh (IoU check)
  "image_element_id": "e25",
  "note": "text embedded in image — not UI text"
}
```

## 3. Hai bài toán con

a. **Face detection** trong crop ảnh → bbox mặt + check boundary clip.
b. **Text-in-image overlap** → IoU giữa text_segment bbox (A5) và image element bbox (A7).

> Bài toán b) **thuần hình học** (IoU) — không cần ML. Bài toán a) cần pretrained model.

## 4. Kỹ thuật / lib (Python) — list + đề xuất

| Việc | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| **Phát hiện mặt — MediaPipe** | `mediapipe` (`FaceDetector`) | nhẹ (~3MB model), nhanh (CPU), pretrained, không train lại, API Python đơn giản | cần cài mediapipe; iOS/Android face có thể bị cắt góc → miss | ✅ **khuyến nghị primary** |
| **Phát hiện mặt — OpenCV DNN** | `cv2.dnn` + model `res10_300x300_ssd` (Caffe, ~10MB) | nhẹ, built-in OpenCV, không cần dep ngoài | kém hơn MediaPipe với face nhỏ/nghiêng | ✅ fallback nhẹ |
| **Phát hiện mặt — Haar Cascade** | `cv2.CascadeClassifier` (`haarcascade_frontalface`) | cực nhẹ, offline | nhiều false positive, chỉ mặt thẳng | ⚠ fallback cuối nếu không có DNN |
| **Phát hiện mặt — RetinaFace** | `retinaface` (InsightFace) | chính xác nhất (kể cả profile/góc) | nặng hơn MediaPipe, dep phức tạp | ⏭ tùy chọn nếu recall MediaPipe kém |
| **Kiểm tra text-in-image** | **thuần numpy** — IoU bbox text_segment (A5) ∩ bbox ảnh (A7) | deterministic, không ML | — | ✅ **không cần ML** |
| **Kiểm tra face bị cắt** | thuần Python: so `face_bbox` vs `image_region_bbox` → edge overlap | deterministic | — | ✅ |

> ✅ **Pretrained ≠ train lại:** MediaPipe FaceDetector, OpenCV DNN SSD — đều là **general
> pretrained model**, KHÔNG train lại per app / per dataset. Vẫn hoàn toàn hợp nguyên tắc
> zero-reference của dự án ("no YOLO" = không gán nhãn / train lại, KHÔNG cấm dùng pretrained).

## 5. Pipeline A11 (đề xuất)

### Bước 1 — Text-in-image tagging (thuần hình học, nhanh, làm trước):
1. Với mỗi `text_segment` từ A5: tính IoU với mỗi `image element bbox` từ A7.
2. Nếu IoU > ngưỡng (đề xuất `0.5` — segment nằm chủ yếu trong vùng ảnh) → set `in_image_region = true`.
3. Emit danh sách annotated text segments.

### Bước 2 — Face detection (chạy sau, tốn hơn):
1. Nhận crop vùng ảnh từ A7 (`crops/e25.png`).
2. Chạy face detector (MediaPipe FaceDetector) trên crop.
3. Với mỗi face bbox:
   - Tính xem face bbox có **chạm/vượt** boundary crop không (xét theo `image_region bbox`): `face.x < margin` / `face.x + face.w > region.w - margin` / v.v. → `is_cropped = true`.
4. Emit `faces_detected[]` per image element.
5. Nếu `is_cropped = true` → emit `candidate_issue IMG-04`.

## 6. Ranh giới Mode A vs Mode B

| | Mode A (có DOM) | Mode B (chỉ ảnh) |
|---|---|---|
| **Vùng ảnh input** | A7 cấp bbox chính xác từ DOM | A7 cấp bbox từ CV (A3) — kém chính xác hơn |
| **Text-in-image check** | ✅ Giống nhau — thuần IoU, không phụ thuộc mode | ✅ |
| **Face detection** | ✅ Crop chính xác từ DOM bbox → detect tốt hơn | ✅ Crop từ A3 bbox — đủ dùng |
| **Confidence** | Cao hơn (crop chính xác) | Thấp hơn (crop có thể sai ranh giới) |

> A11 chủ yếu phát huy ở **Mode B** (khi không có DOM để nói "ảnh có gì bên trong").
> Ở Mode A, DOM không nói về nội dung ảnh → A11 vẫn cần.

## 7. Tiêu chí phục vụ

| Tiêu chí | Cách A11 đóng góp |
|---|---|
| **IMG-04** Crop sai (cắt mặt / nội dung quan trọng) | Face detect → `is_cropped=true` → candidate R3 → Agent G5 xác nhận |
| **CNT-xx / Rule R4** Text UI vs text trong ảnh | `in_image_region=true` → Rule R4 KHÔNG check text này là i18n-key/placeholder/mojibake |
| **TYP-03** Text bị cắt | Loại trừ "text trong ảnh" khỏi false positive cắt cụt |
| **CMP-02** Nút icon-only không nhãn | Text trong ảnh logo không tính là label của nút → loại false negative |
| **IMG-06** Icon/ảnh sai ngữ nghĩa | A11 face detect cung cấp "ảnh này có mặt người" → Agent G5 tham khảo context |

## 8. Open decisions (cần anh chốt — lựa chọn lớn)

- [ ] **Face detector library: MediaPipe vs OpenCV DNN?** Đề xuất **MediaPipe primary** (nhẹ, nhanh, chính xác với face thẳng/nghiêng nhẹ — phổ biến trên UI). OpenCV DNN fallback. Anh quyết nếu có ràng buộc runtime.
- [ ] **Có thêm object/subject saliency (ngoài mặt) không?** IMG-04 nói "cắt mất phần quan trọng" — mặt là case phổ biến nhất, nhưng cũng có thể là text, sản phẩm, icon chính. Phase 1 chỉ detect mặt là đủ? (Đề xuất: **Phase 1 chỉ face**; subject saliency (SAM/CLIP saliency) để Phase 2.)
- [ ] **Ngưỡng IoU "text in image":** đề xuất `0.5` (segment nằm > 50% trong vùng ảnh). Tune bằng golden set.
- [ ] **Ưu tiên triển khai:** A11 ưu tiên thấp — nên **implement sau** khi golden set hình thành để biết IMG-04 có phổ biến trong data thực không. Nếu < 5% issue thì để Phase 2. Anh quyết có build Phase 1 không.

## 9. Edge cases (BẮT BUỘC xử lý)

- **Mặt rất nhỏ (< 20px):** MediaPipe có thể miss → confidence thấp; không báo false negative.
- **Mặt bị che (kính đen, mask):** detector có thể miss — đây là limitation pretrained model; không cần handle.
- **Ảnh illustration / avatar (mặt cartoon):** MediaPipe có thể detect hoặc không — false positive nguy hiểm hơn false negative ở đây → chọn ngưỡng confidence cao (`> 0.7`).
- **Nhiều mặt trong 1 ảnh:** emit tất cả `faces_detected[]`; check từng cái có bị cắt không.
- **Text logo nằm đúng rìa ảnh:** IoU check đủ bắt — đây là case quan trọng (logo bị cắt = có thể IMG-04).
- **Vùng ảnh rất nhỏ (< 32×32):** bỏ qua face detection (không đủ pixel); vẫn chạy text-in-image check.
- **Crop vùng ảnh sai (A7 Mode B nhầm boundary):** A11 face detect trên crop sai → confidence thấp → đánh dấu `"bbox_uncertain": true` khi `source=vision` từ A7.
- **A5 text segment bbox và A7 image bbox chồng nhau một phần (IoU ≈ 0.3):** không đủ để kết luận "text trong ảnh" → giữ ngưỡng `0.5`; đánh dấu `"ambiguous"`.

## 10. TDD outline (khi vào code)

- test Text-in-image: text_segment bbox nằm hoàn toàn trong image_element bbox → `in_image_region=true`.
- test Text-in-image: text_segment nằm ngoài hoàn toàn → `in_image_region=false`.
- test Text-in-image: IoU = 0.3 (partial overlap) → `in_image_region=false` với ngưỡng 0.5.
- test Face detect: ảnh có mặt rõ → trả `faces_detected` không rỗng, confidence > 0.7.
- test Face crop: face bbox chạm top edge → `is_cropped=true`, `crop_direction=["top"]`.
- test Face crop: face bbox nằm giữa không chạm edge → `is_cropped=false`, không emit IMG-04.
- test ảnh nhỏ < 32×32 → không chạy face detect, không crash.
- test ảnh không có mặt → `faces_detected=[]`, không crash.
- test IoU utility function: bbox A hoàn toàn trong B → IoU tính đúng.
- test `source=vision` trên tất cả output A11.

## Trạng thái: spec ✅ — ưu tiên thấp; chờ chốt mục 8 (lib face, scope IMG-04, timing triển khai) trước khi code.
