# A11 — Face / Text-in-image Detector (trong vùng ảnh: khuôn mặt + text embedded)

> **TL;DR:** Chạy bên trong vùng ảnh-photo (A7): (1) detect khuôn mặt + cờ bị cắt biên (IMG-04); (2) tag text-segment (A5) nằm trong vùng ảnh là `in_image` để downstream không nhầm là text UI.

> Phase 1, nhóm "đo diện mạo". Tech: **Python + pretrained model nhẹ**.
> ⚠ **Ưu tiên thấp** — có thể để sau standard set nếu cần tiết kiệm effort Phase 1.
> Liên quan: [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A7-image-region-meta-reader.md`](A7-image-region-meta-reader.md) · [`A6-icon-graphic-detector.md`](A6-icon-graphic-detector.md)

## 1. Trách nhiệm
Chạy **BÊN TRONG vùng ảnh-photo** đã được A7 xác định. Hai nhiệm vụ độc lập:

### 1a. Face Detector — bắt lỗi crop cắt mặt (IMG-04)
- Phát hiện **khuôn mặt** trong vùng ảnh.
- Xác định mặt có bị **cắt bởi boundary vùng ảnh** không (bbox mặt chạm/vượt edge).
- Tín hiệu: candidate IMG-04 "Crop sai — cắt mất phần quan trọng".
- KHÔNG nhận dạng danh tính.

### 1b. Text-in-image Tagger — phân biệt text UI vs text trong ảnh
- Đánh dấu text segment (A5 OCR) nằm **trong vùng ảnh** là `"in_image"` → downstream (Rule R4, Agent G1) KHÔNG nhầm là text UI thiếu/không-render.
- Text trên banner, logo có chữ, text sản phẩm trên ảnh → hợp lệ.
- A11 KHÔNG check nội dung text đúng/sai — chỉ đánh dấu nguồn gốc.

KHÔNG phân tích nội dung ảnh, KHÔNG nhận dạng người, KHÔNG check text ngoài vùng ảnh.

## 2. Input / Output
- **Input:** crop vùng ảnh (từ A7, `role=image`) + `text_segments[]` từ A5 (có bbox) + `elements[]` `role=image` + bbox.
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
      "crop_direction": ["top", "left"]
    }
  ],
  "source": "vision",
  "face_detector": "mediapipe | opencv_dnn | haarcascade"
}
```

**1b. Text-in-image tagging** — annotate vào `text_segments[]`:
```jsonc
{
  "segment_id": 42,
  "in_image_region": true,       // bbox segment nằm trong bbox vùng ảnh (IoU check)
  "image_element_id": "e25",
  "note": "text embedded in image — not UI text"
}
```

## 3. Hai bài toán con
- a. **Face detection** trong crop ảnh → bbox mặt + check boundary clip.
- b. **Text-in-image overlap** → IoU giữa text_segment bbox (A5) và image element bbox (A7).

> b) **thuần hình học** (IoU), không cần ML. a) cần pretrained model.

## 4. Kỹ thuật / lib (Python)
| Việc | Lib/tool | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Face — **MediaPipe** | `mediapipe` (`FaceDetector`) | nhẹ (~3MB), nhanh CPU, pretrained, không train lại, API gọn | cần cài mediapipe; face cắt góc → miss | ✅ **primary** |
| Face — **OpenCV DNN** | `cv2.dnn` + `res10_300x300_ssd` (Caffe, ~10MB) | nhẹ, built-in, không dep ngoài | kém hơn MediaPipe với face nhỏ/nghiêng | ✅ fallback nhẹ |
| Face — **Haar Cascade** | `cv2.CascadeClassifier` (`haarcascade_frontalface`) | cực nhẹ, offline | nhiều FP, chỉ mặt thẳng | ⚠ fallback cuối |
| Face — **RetinaFace** | `retinaface` (InsightFace) | chính xác nhất (profile/góc) | nặng hơn, dep phức tạp | ⏭ tùy chọn nếu recall MediaPipe kém |
| Text-in-image | **thuần numpy** — IoU bbox text_segment (A5) ∩ bbox ảnh (A7) | deterministic, không ML | — | ✅ **không cần ML** |
| Face bị cắt | thuần Python: `face_bbox` vs `image_region_bbox` → edge overlap | deterministic | — | ✅ |

> ✅ **Pretrained ≠ train lại:** MediaPipe FaceDetector, OpenCV DNN SSD đều là **general pretrained**, KHÔNG train lại per app → hợp zero-reference ("no YOLO" = không gán nhãn / train lại, KHÔNG cấm pretrained).

## 5. Pipeline A11 (đề xuất)
### Bước 1 — Text-in-image tagging (thuần hình học, nhanh, làm trước):
1. Mỗi `text_segment` (A5): tính IoU với mỗi `image element bbox` (A7).
2. IoU > ngưỡng (đề xuất `0.5`) → `in_image_region = true`.
3. Emit text segments annotated.

### Bước 2 — Face detection (chạy sau, tốn hơn):
1. Nhận crop vùng ảnh (`crops/e25.png`).
2. Chạy face detector (MediaPipe).
3. Mỗi face bbox: kiểm có **chạm/vượt** boundary crop không (`face.x < margin` / `face.x + face.w > region.w - margin` / ...) → `is_cropped = true`.
4. Emit `faces_detected[]` per image element.
5. `is_cropped = true` → emit candidate IMG-04.

## 6. Phạm vi và confidence
Crop vùng ảnh đến từ A7 (bbox từ A3 — có thể sai ranh giới):
- **Text-in-image:** thuần IoU, không phụ thuộc độ chính xác bbox → vẫn đáng tin.
- **Face detection:** crop từ A3 bbox có thể sai → confidence thấp hơn; đánh dấu `"bbox_uncertain": true`.
- Tất cả: `source=vision`, `confidence` phản ánh độ chắc bbox đầu vào.

## 7. Tiêu chí phục vụ
| Tiêu chí | Cách A11 đóng góp |
|---|---|
| **IMG-04** Crop sai (cắt mặt / nội dung quan trọng) | Face detect → `is_cropped=true` → candidate R3 → Agent G5 xác nhận |
| **CNT-xx / Rule R4** Text UI vs text trong ảnh | `in_image_region=true` → R4 KHÔNG check là i18n-key/placeholder/mojibake |
| **TYP-03** Text bị cắt | Loại "text trong ảnh" khỏi FP cắt cụt |
| **CMP-02** Nút icon-only không nhãn | Text trong ảnh logo không tính label nút → loại FN |
| **IMG-06** Icon/ảnh sai ngữ nghĩa | "ảnh có mặt người" → Agent G5 tham khảo context |

## 8. Open decisions (cần anh chốt)
- [ ] **Face detector: MediaPipe vs OpenCV DNN?** Đề xuất **MediaPipe primary** (nhẹ, nhanh, chính xác face thẳng/nghiêng nhẹ). OpenCV DNN fallback.
- [ ] **Có thêm object/subject saliency (ngoài mặt)?** IMG-04 nói "cắt mất phần quan trọng" — mặt phổ biến nhất. Đề xuất **Phase 1 chỉ face**; subject saliency (SAM/CLIP) để Phase 2.
- [ ] **Ngưỡng IoU "text in image":** đề xuất `0.5`. Tune GS.
- [ ] **Ưu tiên triển khai:** A11 ưu tiên thấp — **implement sau** khi có standard set để biết IMG-04 phổ biến không. Nếu < 5% issue → Phase 2.

## 9. Edge cases (BẮT BUỘC xử lý)
- **Mặt rất nhỏ (< 20px):** MediaPipe có thể miss → confidence thấp; không báo FN.
- **Mặt bị che (kính đen, mask):** detector có thể miss — limitation pretrained; không handle.
- **Illustration / avatar (mặt cartoon):** MediaPipe detect hoặc không — FP nguy hiểm hơn FN → ngưỡng confidence cao (`> 0.7`).
- **Nhiều mặt trong 1 ảnh:** emit tất cả `faces_detected[]`; check từng cái bị cắt không.
- **Text logo nằm đúng rìa ảnh:** IoU check đủ bắt — case quan trọng (logo bị cắt = có thể IMG-04).
- **Vùng ảnh rất nhỏ (< 32×32):** bỏ qua face detection; vẫn chạy text-in-image check.
- **Crop vùng ảnh sai (A7 nhầm boundary):** face detect trên crop sai → confidence thấp → `"bbox_uncertain": true`.
- **IoU ≈ 0.3 (partial overlap):** không đủ kết luận → giữ ngưỡng `0.5`; đánh dấu `"ambiguous"`.

## 10. TDD outline
- Text-in-image: segment hoàn toàn trong image bbox → `in_image_region=true`.
- Text-in-image: segment ngoài hoàn toàn → `in_image_region=false`.
- Text-in-image: IoU = 0.3 → `in_image_region=false` (ngưỡng 0.5).
- Face: ảnh có mặt rõ → `faces_detected` không rỗng, confidence > 0.7.
- Face crop: bbox chạm top edge → `is_cropped=true`, `crop_direction=["top"]`.
- Face crop: bbox giữa không chạm edge → `is_cropped=false`, không emit IMG-04.
- ảnh < 32×32 → không chạy face detect, không crash.
- ảnh không có mặt → `faces_detected=[]`, không crash.
- IoU utility: bbox A hoàn toàn trong B → IoU đúng.
- `source=vision` trên tất cả output.

## Trạng thái: spec ✅ — ưu tiên thấp; chờ chốt mục 8 (lib face, scope IMG-04, timing triển khai) trước khi code.
