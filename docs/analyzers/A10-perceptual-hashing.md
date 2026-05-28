# A10 — Perceptual Hashing (phát hiện ảnh/phần tử trùng trong màn)

> Bóc tách chi tiết. Phase 1 (in-screen only). **Mode A · B.** Tech: **Python + imagehash/OpenCV**.
> Phase 1: **chỉ so trong cùng một màn**. Cross-screen (so nhiều màn) → **Phase 2** (cần nhóm ảnh, A14 Cross-screen Matcher).
> Liên quan: [`A1-tree-parser.md`](A1-tree-parser.md) · [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A7`](#) Image Region Meta Reader · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm
Từ crop của **mọi element có role `image | icon | avatar`** trong cùng một màn,
tính **perceptual hash** → so từng cặp theo **Hamming distance** → phát hiện hai trường hợp:

1. **Trùng hoàn toàn (duplicate):** hash giống hệt hoặc Hamming ≤ ngưỡng thấp → nghi lỗi
   "dùng ảnh mặc định cho nhiều slot" hoặc item list lặp sai.
2. **Gần trùng (near-duplicate):** Hamming trong dải trung → nghi icon nhầm chỗ, ảnh thiếu
   đa dạng, item pagination nhân đôi.

**KHÔNG** quyết định "trùng là lỗi" — đưa vào `candidate_issues` để VLM xác nhận ngữ cảnh
(trùng chủ ý vs lỗi). **KHÔNG** so xuyên màn ở Phase 1 — nêu rõ trong output.

> ⚠ **Phạm vi Phase 1 — in-screen:** chỉ so các element trong **cùng một request** (1 ảnh).
> Cross-screen matching (CONS) → **Phase 2**, yêu cầu nhóm ảnh + A14.

## 2. Input / Output
- **Input:** PNG full + `elements[]` đã có `bbox` + `crop` path (từ A1 Mode A hoặc A3 Mode B).
  Nếu crop chưa có → A10 tự cắt từ bbox.
- **Output:** `hash_results[]` + các `candidate_issues[]` kiểu `img_duplicate` / `img_near_dup`:
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
      "source": "vision"         // "vision" cả 2 mode (hash từ pixel)
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
a. **Hash generation** — crop element theo bbox → tính perceptual hash.
b. **Pair comparison** — so từng cặp trong tập; phân loại theo ngưỡng Hamming.

## 4. Kỹ thuật / lib (Python)

| Hướng | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Perceptual hash | **`imagehash`** (`phash`, `dhash`, `ahash`, `whash`) | nhẹ, thuần Python, 4 loại hash sẵn | không tự scale-invariant | ✅ **primary** |
| Hash nhanh/robust | **`imagehash.phash`** (DCT-based) | ổn với resize/nén nhẹ, ít FP | nhạy rotate 90° | ✅ **mặc định** |
| Diff-hash (gradient) | **`imagehash.dhash`** | nhanh, phân biệt cấu trúc cạnh tốt | kém màu | ✅ đối chiếu chéo khi phash FP cao |
| Structural similarity | **`skimage.metrics.ssim`** (OpenCV) | metric liên tục 0–1, hiểu vùng | chậm hơn hash, yêu cầu cùng size | tùy chọn cho near-dup tinh tế |
| Feature matching | **OpenCV ORB** + BFMatcher | tốt với icon/logo chi tiết | phức tạp hơn, nhiễu với flat icon | tùy chọn nếu hash không đủ |
| Crop từ bbox | **Pillow** (`Image.crop`) | đơn giản | — | ✅ |
| Scale ảnh trước hash | **Pillow resize** (8×8 / 16×16) | chuẩn hoá kích thước | — | ✅ |

> **Đề xuất Phase 1:** dùng **`imagehash.phash` (hash_size=16)** làm primary. Khi
> Hamming ≤ `T_dup` → duplicate; `T_dup < Hamming ≤ T_near` → near-dup; còn lại → khác.
> Ngưỡng T mặc định: T_dup=6, T_near=15 — **tune bằng golden set (GS)**.

## 5. Pipeline A10 (đề xuất)
1. **Thu thập crop:** lấy path `element.crop` từ schema; nếu rỗng → cắt bằng Pillow từ `bbox` + ảnh full.
2. **Lọc role:** chỉ hash element có `role ∈ {image, icon, avatar}` + `visible=true` +
   area ≥ min_area (loại divider/pixel cực nhỏ).
3. **Resize & hash:** scale crop về `hash_size×hash_size` (grayscale) → `phash`.
4. **So cặp:** O(n²) với n nhỏ (≤ vài trăm element/màn); tính Hamming cho mọi cặp `(i,j)` với `i<j`.
5. **Phân loại:** theo ngưỡng → verdict `duplicate | near_dup | different`.
6. **Emit candidate:** với mỗi cặp `duplicate`/`near_dup` → tạo `candidate_issue`; gắn
   `confidence` (cao hơn khi Hamming thấp hơn); đánh dấu phạm vi `scope: "in-screen"`.
7. **Ghi hash cache:** lưu hash theo `element_id` để A0 tái dùng (tránh re-hash).

## 6. Edge cases (BẮT BUỘC xử lý)
- **Trùng chủ ý:** avatar mặc định, icon placeholder, icon tab bar cùng loại → VLM phân biệt.
  A10 **không tự loại** — chỉ hạ confidence khi role+vị trí gợi ý "chủ ý" (vd: icon tab bar).
- **Ảnh rất nhỏ / icon 16×16:** hash kém ổn định → gắn `confidence` thấp + cờ `small_crop`.
- **Ảnh bị nén mạnh / JPEG artifact:** phash vẫn ổn với nén nhẹ; nén nặng hạ confidence.
- **Crop rỗng (bbox lỗi):** bỏ qua + ghi log cảnh báo, không crash pipeline.
- **n²  lớn (màn list dài):** giới hạn max_elements (đề xuất 200); nếu vượt → lấy mẫu ngẫu nhiên + đánh dấu `sampled`.
- **Mode A vs B:** hash luôn từ pixel (`source=vision`) — không phân biệt mode. Mode A có thêm `element.id` chính xác, Mode B id từ A3 (suy đoán).

## 7. Tiêu chí phục vụ
| Tiêu chí | Cách A10 đóng góp |
|---|---|
| **IMG-12** Ảnh trùng lặp ngoài ý muốn | candidate chính; V xác nhận chủ ý vs lỗi |
| **STATE-08** Pull-refresh nhân đôi item | hash list item → duplicate cặp kề → nghi nhân đôi |
| **LAY-14** Phần tử chồng vị trí | phối hợp với Rule geometry (IoU) để xác nhận thêm "trùng nội dung" |
| **IMG-10** Lộn ảnh brand/phiên bản | hash so reference brand (Mode A, nếu có ref sẵn) — yếu ở zero-ref |
| **CONS** (Phase 2) | A10 cấp hash cache → A14 tái dùng để so xuyên màn |

## 8. Open decisions (cần anh chốt — lựa chọn lớn)
- [ ] **Loại hash mặc định: pHash hay dHash?** Đề xuất `phash` vì ổn hơn với nén nhẹ/resize;
  nhưng `dhash` nhanh hơn và phân biệt cấu trúc cạnh tốt. Cân nhắc chạy cả hai rồi AND kết quả.
- [ ] **Ngưỡng Hamming (T_dup, T_near):** T_dup=6, T_near=15 là khởi điểm → **bắt buộc tune
  bằng golden set** (ảnh placeholder giống nhau hợp lệ vs duplicate thật). Anh chốt giá trị nào để bắt đầu test?
- [ ] **Xử lý "trùng chủ ý" (placeholder mặc định, icon tab):** (a) blacklist role/pattern tĩnh;
  (b) hạ confidence tự động theo heuristic vị trí; (c) để nguyên cho VLM phân biệt tất.
  Đề xuất: (b)+(c) — heuristic giảm FP, VLM xác nhận cuối.
- [ ] **Có thêm SSIM / ORB không?** Đề xuất Phase 1 chỉ dùng `imagehash` cho đơn giản; thêm
  SSIM/ORB nếu golden set cho thấy FP/FN cao.

## 9. TDD outline (khi vào code)
- test: 2 crop ảnh y hệt → Hamming=0, verdict=`duplicate`.
- test: crop gốc vs crop resize 50% → Hamming ≤ T_dup (phash ổn với resize).
- test: 2 crop khác rõ → Hamming > T_near, verdict=`different`.
- test: crop quá nhỏ (< 8px) → skip + cờ `small_crop`, không crash.
- test: crop rỗng / không tồn tại → bỏ qua + ghi log cảnh báo.
- test: n element lớn (>200) → giới hạn + cờ `sampled`.
- test: tất cả hash `source=vision` bất kể mode.
- test: candidate_issue emit đúng cặp duplicate với severity + confidence.

## Trạng thái: spec ✅ — chờ chốt mục 8 (loại hash + ngưỡng Hamming + xử lý trùng chủ ý).
