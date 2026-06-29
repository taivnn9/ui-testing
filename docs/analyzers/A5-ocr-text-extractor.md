# A5 — OCR / Text Extractor (ảnh → text + box + script)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". Tech: **Python + OCR**.
> Là **nguồn `text` duy nhất** vì hệ thống chỉ nhận ảnh.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (fuse text-box) ·
> [`A8`](#) glyph inspector

## 1. Trách nhiệm
Trích **mọi cụm text nhìn thấy trên ảnh** thành segment có `text + bbox + confidence + script`,
gom thành dòng/khối theo **reading order**. A5 là **nguồn `text` duy nhất** — không có DOM/XML
để đối chiếu.

**KHÔNG** phân loại nội dung (regex `undefined`/i18n-key/mojibake là việc **Rule R4**); A5 chỉ
trả text **đã chuẩn hoá unicode** + độ tin cậy. **KHÔNG** quyết "tofu thật/giả" (A8 pixel chốt).

## 2. Input / Output
- **Input:** PNG (full) + meta `viewport{w,h,dpr}`. *Tùy chọn:* danh sách bbox vùng (từ A3)
  để OCR **theo vùng** (chính xác & nhanh hơn quét cả ảnh) + crop nhỏ cho text bé.
- **Output:** `text_segments[]` (`source=vision`):
```jsonc
{
  "text": "Đăng nhập",            // đã NFC-normalize, strip
  "bbox": { "x":0,"y":0,"w":0,"h":0 }, "bbox_norm": {},
  "confidence": 0.97,             // điểm recognizer — đẩy lên confidence element
  "level": "line",                // word | line | block (đa cấp, có parent)
  "parent": 12,                   // index segment cha (block chứa line…)
  "script": "latin",              // latin | cjk | arabic | cyrillic | digit | mixed | unknown
  "lang_hint": "vi",              // đoán ngôn ngữ (tùy chọn, conf riêng)
  "angle": 0,                     // độ nghiêng (≠0 ⇒ text xoay)
  "has_replacement": false        // chứa U+FFFD '�' / nhiều '□' ⇒ cờ nghi tofu → A8
}
```

## 3. Bốn bài toán con
a. **Detection** — tìm box chứa text (kể cả text nhỏ/đa cỡ trên UI).
b. **Recognition** — đọc ký tự + confidence; **đa ngôn ngữ** (i18n là trọng tâm dự án).
c. **Reading order / grouping** — gom word→line→block, sắp đúng thứ tự đọc (cả RTL).
d. **Nhận dạng script/ngôn ngữ** — phân loại chữ viết (phục vụ CNT-03 lẫn RTL TYP-12).

## 4. Kỹ thuật / lib (Python) — list + đề xuất
| Việc | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| OCR det+rec đa ngữ | **PaddleOCR (PP-OCRv4/v5)** | đa ngôn ngữ mạnh (vi/cjk/arabic), det+rec+angle sẵn, box tốt với UI | nặng, kéo paddle runtime; GPU tối ưu | ✅ **primary** |
| OCR fallback/đối chiếu | **Tesseract** (`pytesseract`) | nhẹ, ổn với text UI sạch nét, `tsv` cho box+conf+level | yếu text nhỏ/đa cỡ/nghiêng, cần `--psm` | ✅ **fallback** + cross-check |
| OCR thuần Python | **EasyOCR** | API gọn, đa ngữ | chậm hơn, box thô hơn Paddle | tùy chọn |
| Lang detect (trên text) | **`fast-langdetect`/`langid`** | nhẹ, offline | ngắn → kém chính xác | dùng làm `lang_hint`, conf thấp |
| Unicode normalize | **`unicodedata`** (NFC) + `regex` | chuẩn hoá dấu vi/CJK | — | ✅ |
| Group/đo box | **numpy** (sort y→x, cluster dòng theo overlap-y) | deterministic | — | ✅ |
| Upscale text bé | **OpenCV** (resize Lanczos / super-res nhẹ) | tăng recall text nhỏ | thêm thời gian | ✅ có điều kiện |

> **Đa ngôn ngữ là bắt buộc** (dự án test i18n). Đề xuất mặc định bật bộ: `latin + vi + cjk`
> (+`arabic` khi cần RTL). PaddleOCR cho phép chọn `lang`; cân nhắc auto theo `screen.locale`
> nếu có.

## 5. Pipeline A5 (đề xuất)
1. **Chọn vùng:** có bbox từ A3 → OCR theo từng vùng/crop; không có → quét full ảnh.
2. **Tiền xử lý có điều kiện:** ước lượng cỡ chữ; nếu < ngưỡng px → **upscale** crop (giữ bản
   gốc cho A8). Giữ ảnh màu (không ép nhị phân — UI nhiều nền).
3. **Phát hiện + Nhận dạng** (PaddleOCR): box + text + conf + angle, theo bộ ngôn ngữ đã chọn.
4. **Normalize:** NFC, strip, gộp khoảng trắng; cờ `has_replacement` nếu thấy `�`/chuỗi `□`.
5. **Grouping:** word→line (cluster theo overlap trục y + gần trục x) → block; gán
   `parent/level`; suy **reading order** (LTR mặc định; RTL nếu script=arabic/hebrew).
6. **Script/lang:** phân loại theo bảng Unicode block + `lang_hint` từ langdetect.
7. **Emit** `text_segments[]` cho A0 / A3 / Rule R4 / A8.

## 6. Tiêu chí được A5 cấp data nền
- **Toàn bộ CNT** (text là input): CNT-01 placeholder, CNT-02 i18n-key, CNT-03 sai ngôn ngữ
  (qua `script`/`lang_hint`), CNT-04 lorem, CNT-05 debug, CNT-06 mojibake, CNT-07 escape,
  CNT-08/12 số/đơn vị, CNT-09 chính tả, CNT-10/11/13/14 (text cho agent).
- **TYP:** TYP-01 tofu (cờ `has_replacement` → A8 chốt), TYP-03 cắt cụt (kiểm tra trực tiếp từ
  pixel + bbox), TYP-06 ngắt dòng (line grouping), TYP-11 casing, TYP-12 RTL (`script`+reading order).
- **CMP-07** placeholder-vs-value, **CMP-08** label nút bị cắt, **STATE-05** stale placeholder.
- **CONS-07** định dạng số/ngày xuyên màn → **Phase 2** (đa ảnh).
- Cấp **text-box** để A3 fuse (containment) và **crop** cho A8 soi glyph.

## 7. Edge cases (BẮT BUỘC xử lý)
- **Đa ngôn ngữ trên 1 màn** (i18n) → bật multi-lang; đừng ép 1 `lang`.
- **Tofu / glyph thiếu:** OCR có thể trả rỗng hoặc `�`/`□` → **không kết luận**, set
  `has_replacement` + để **A8** soi pixel chốt. (OCR một mình KHÔNG đủ tin.)
- **Chữ đè chữ (TYP-04)** → OCR ra chuỗi rác/giảm conf → chính nó là tín hiệu, đừng vứt.
- **Text rất nhỏ** → upscale crop; vẫn miss thì conf thấp, đánh dấu.
- **Text trên ảnh nền (low-contrast)** → có thể miss → không coi "không thấy text" là "không có".
- **Vertical CJK / text xoay** → dùng `angle`, model hỗ trợ dọc nếu cần.
- **Decor text trong ảnh** (logo, ảnh sản phẩm) vs **UI text** → A11 phân biệt; A5 vẫn trích,
  gắn cờ nằm-trong-vùng-ảnh để downstream lọc.
- **RTL/bidi** → reading order phải đảo; sai chiều là chính lỗi TYP-12.

## 8. Open decisions (cần anh chốt — lựa chọn lớn)
- [ ] **OCR engine chính:** đề xuất **PaddleOCR chính + Tesseract dự phòng/đối chiếu chéo**.
  Chốt vì ảnh hưởng dependency (paddle nặng) & GPU. (Anh quyết: Paddle-only cho gọn, hay giữ
  cả 2 để đối chiếu?)
- [ ] **Bộ ngôn ngữ mặc định** + auto chọn theo `screen.locale` nếu có. Đề xuất `latin+vi+cjk`,
  thêm `arabic` khi locale RTL.
- [ ] Ngưỡng upscale text-bé & ngưỡng conf để gắn cờ → **tune bằng standard set (GS)**.

## 9. TDD outline (khi vào code)
- test: ảnh 1 dòng text sạch → đúng `text` + bbox + conf cao.
- test: NFC normalize dấu tiếng Việt (tổ hợp → dựng sẵn) giống nhau.
- test: grouping word→line đúng (3 từ 1 dòng → 1 line, đúng thứ tự).
- test: script detect (latin / cjk / arabic) đúng nhãn.
- test: `has_replacement` bật khi có `�`/`□`.
- test: RTL → reading order đảo.
- test: ảnh không có text → trả `[]`, không crash.
- test: recall text-nhỏ đo bằng GS (không hard-assert).

## Trạng thái: spec ✅ — chờ chốt mục 8 (engine + bộ ngôn ngữ).
