# A10 — Perceptual Hashing (phát hiện ảnh/phần tử trùng trong màn)

> **TL;DR:** Tính perceptual hash (pHash) cho mọi element `image|icon|avatar` trong cùng màn, so từng cặp theo Hamming → phát hiện duplicate / near-duplicate; đưa vào `candidate_issues` cho agent reasoning (Codex/Cline) xác nhận chủ ý vs lỗi.

> Phase 1 (in-screen only). Tech: **Python + imagehash/OpenCV**.
> Cross-screen (so nhiều màn) → **Phase 2** (cần nhóm ảnh, A14 Cross-screen Matcher).
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A7`](#) Image Region Meta Reader

## 1. Trách nhiệm
Từ crop của **mọi element role `image | icon | avatar`** trong cùng màn → pHash → so cặp theo **Hamming distance** → 2 trường hợp:
1. **Trùng hoàn toàn (duplicate):** hash giống hệt / Hamming ≤ ngưỡng thấp → nghi "dùng ảnh mặc định cho nhiều slot" hoặc item list lặp sai.
2. **Gần trùng (near-duplicate):** Hamming dải trung → nghi icon nhầm chỗ, ảnh thiếu đa dạng, item pagination nhân đôi.

KHÔNG quyết "trùng là lỗi" — đưa vào `candidate_issues` để agent reasoning (Codex/Cline) xác nhận ngữ cảnh (chủ ý vs lỗi). KHÔNG so xuyên màn Phase 1.

> ⚠ **Phạm vi Phase 1 — in-screen:** chỉ so element trong **cùng request** (1 ảnh). Cross-screen (CONS) → **Phase 2**, cần nhóm ảnh + A14.

## 2. Input / Output
- **Input:** PNG full + `elements[]` có `bbox` + `crop` path (từ A3). Crop chưa có → A10 tự cắt từ bbox.
- **Output:** `hash_results[]` + `candidate_issues[]` kiểu `img_duplicate` / `img_near_dup`:
```jsonc
{
  "element_id": "e12",
  "hash": "f9a3c5...",      // hex pHash 64-bit
  "hash_type": "phash",
  "crop": "crops/e12.png",
  "pairs": [
    {
      "element_id_b": "e27",
      "hamming": 3,
      "similarity": 0.95,
      "verdict": "duplicate",    // "duplicate" | "near_dup" | "different"
      "confidence": 0.9,
      "source": "vision"         // luôn "vision" — hash từ pixel
    }
  ]
}
```
Candidate issue mẫu:
```jsonc
{
  "rule": "img_duplicate",
  "elements": ["e12", "e27"],
  "severity": "low",
  "confidence": 0.9,
  "detail": "pHash Hamming=3 (ngưỡng dup=6); nghi 2 avatar/placeholder dùng cùng ảnh"
}
```

## 3. Hai bài toán con
- a. **Hash generation** — crop element → pHash.
- b. **Pair comparison** — so từng cặp; phân loại theo ngưỡng Hamming.

## 4. Kỹ thuật / lib (Python)
| Hướng | Lib/tool | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Perceptual hash | **`imagehash`** (`phash`, `dhash`, `ahash`, `whash`) | nhẹ, thuần Python, 4 loại sẵn | không tự scale-invariant | ✅ **primary** |
| Hash nhanh/robust | **`imagehash.phash`** (DCT-based) | ổn với resize/nén nhẹ, ít FP | nhạy rotate 90° | ✅ **mặc định** |
| Diff-hash (gradient) | **`imagehash.dhash`** | nhanh, phân biệt cạnh tốt | kém màu | ✅ đối chiếu chéo khi phash FP cao |
| Structural similarity | **`skimage.metrics.ssim`** (OpenCV) | metric liên tục 0–1, hiểu vùng | chậm hơn, yêu cầu cùng size | tùy chọn cho near-dup tinh tế |
| Feature matching | **OpenCV ORB** + BFMatcher | tốt với icon/logo chi tiết | phức tạp, nhiễu với flat icon | tùy chọn nếu hash không đủ |
| Crop từ bbox | **Pillow** (`Image.crop`) | đơn giản | — | ✅ |
| Scale trước hash | **Pillow resize** (8×8 / 16×16) | chuẩn hoá kích thước | — | ✅ |

> **Đề xuất Phase 1:** **`imagehash.phash` (hash_size=16)** primary. Hamming ≤ `T_dup` → duplicate; `T_dup < Hamming ≤ T_near` → near-dup; còn lại → khác. Ngưỡng mặc định: **T_dup=6, T_near=15** — tune bằng standard set (GS).

## 5. Pipeline A10 (đề xuất)
1. **Thu crop:** lấy `element.crop`; rỗng → cắt Pillow từ `bbox` + ảnh full.
2. **Lọc role:** chỉ hash `role ∈ {image, icon, avatar}` + `visible=true` + area ≥ min_area (loại divider/pixel cực nhỏ).
3. **Resize & hash:** scale về `hash_size×hash_size` (grayscale) → `phash`.
4. **So cặp:** O(n²) với n nhỏ (≤ vài trăm element/màn); Hamming mọi cặp `(i,j)` với `i<j`.
5. **Phân loại:** theo ngưỡng → `duplicate | near_dup | different`.
6. **Emit candidate:** mỗi cặp `duplicate`/`near_dup` → `candidate_issue`; `confidence` cao hơn khi Hamming thấp; gắn `scope: "in-screen"`.
7. **Hash cache:** lưu hash theo `element_id` cho A0 tái dùng (tránh re-hash).

## 6. Edge cases (BẮT BUỘC xử lý)
- **Trùng chủ ý:** avatar mặc định, icon placeholder, icon tab bar cùng loại → agent reasoning (Codex/Cline) phân biệt. A10 **không tự loại** — chỉ hạ confidence khi role+vị trí gợi ý "chủ ý" (vd icon tab bar).
- **Ảnh nhỏ / icon 16×16:** hash kém ổn định → `confidence` thấp + cờ `small_crop`.
- **Ảnh nén mạnh / JPEG artifact:** phash ổn với nén nhẹ; nén nặng hạ confidence.
- **Crop rỗng (bbox lỗi):** bỏ qua + log cảnh báo, không crash.
- **n² lớn (list dài):** giới hạn max_elements (đề xuất 200); vượt → lấy mẫu ngẫu nhiên + cờ `sampled`.
- **Source luôn vision:** hash từ pixel, element id từ A3 (suy đoán) — confidence thấp hơn nếu có DOM reference.

## 7. Tiêu chí phục vụ
| Tiêu chí | Cách A10 đóng góp |
|---|---|
| **IMG-12** Ảnh trùng lặp ngoài ý muốn | candidate chính; agent xác nhận chủ ý vs lỗi |
| **STATE-08** Pull-refresh nhân đôi item | hash list item → duplicate cặp kề → nghi nhân đôi |
| **LAY-14** Phần tử chồng vị trí | phối hợp Rule geometry (IoU) xác nhận "trùng nội dung" |
| **IMG-10** Lộn ảnh brand/phiên bản | hash so reference brand — yếu ở zero-ref |
| **CONS** (Phase 2) | A10 cấp hash cache → A14 so xuyên màn |

## 8. Open decisions (cần anh chốt)
- [ ] **Hash mặc định pHash hay dHash?** Đề xuất `phash` (ổn hơn với nén nhẹ/resize); `dhash` nhanh hơn, phân biệt cạnh tốt. Cân nhắc chạy cả hai rồi AND.
- [ ] **Ngưỡng Hamming (T_dup, T_near):** T_dup=6, T_near=15 khởi điểm → bắt buộc tune bằng standard set. Anh chốt giá trị bắt đầu?
- [ ] **"Trùng chủ ý":** (a) blacklist role/pattern tĩnh; (b) hạ confidence theo heuristic vị trí; (c) để nguyên cho agent reasoning. Đề xuất **(b)+(c)**.
- [ ] **Thêm SSIM / ORB?** Đề xuất Phase 1 chỉ `imagehash`; thêm SSIM/ORB nếu standard set FP/FN cao.

## 9. TDD outline
- 2 crop y hệt → Hamming=0, verdict=`duplicate`.
- crop gốc vs resize 50% → Hamming ≤ T_dup (phash ổn với resize).
- 2 crop khác rõ → Hamming > T_near, verdict=`different`.
- crop quá nhỏ (< 8px) → skip + cờ `small_crop`, không crash.
- crop rỗng / không tồn tại → bỏ qua + log.
- n element > 200 → giới hạn + cờ `sampled`.
- tất cả hash `source=vision`.
- candidate_issue emit đúng cặp duplicate với severity + confidence.

## Trạng thái: spec ✅ — chờ chốt mục 8 (loại hash + ngưỡng Hamming + xử lý trùng chủ ý).
