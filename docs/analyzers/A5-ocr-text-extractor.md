# A5 — OCR / Text Extractor (ảnh → text + box + script)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". **Chạy CẢ hai mode.** Tech: **Python + OCR**.
> Là **nguồn `text` cho Mode B** và là **bộ đối chiếu render cho Mode A** (DOM-text vs ảnh-text).
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) (fuse text-box) ·
> [`A1-tree-parser.md`](A1-tree-parser.md) (text ground truth) · [`A8`](#) glyph inspector ·
> [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm
Trích **mọi cụm text nhìn thấy trên ảnh** thành segment có `text + bbox + confidence + script`,
gom thành dòng/khối theo **reading order**. Hai vai trò:
- **Mode B (không cây):** là **nguồn `text` duy nhất** → đổ vào element của A3, nuôi Rule R4.
- **Mode A (có cây):** chạy song song để **đối chiếu DOM/XML-text ⟷ text-thực-render** — bắt
  lỗi mà cây KHÔNG thấy: tofu/glyph thiếu, chữ bị che/cắt, font fallback đổi hình (DOM nói
  "Đăng nhập" nhưng ảnh đọc ra "Ð□ng nh□p"). **Đây là tín hiệu zero-ref rất mạnh.**

**KHÔNG** phân loại nội dung (regex `undefined`/i18n-key/mojibake là việc **Rule R4**); A5 chỉ
trả text **đã chuẩn hoá unicode** + độ tin cậy. **KHÔNG** quyết "tofu thật/giả" (A8 pixel chốt).

## 2. Input / Output
- **Input:** PNG (full) + meta `viewport{w,h,dpr}`. *Tùy chọn:* danh sách bbox vùng (từ A1/A3)
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
+ (Mode A) bảng **đối chiếu** `tree_text_match[]`: `{element_id, dom_text, ocr_text, similarity, verdict}`.

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
| So chuỗi (Mode A đối chiếu) | **`rapidfuzz`** | nhanh, ratio/Levenshtein | — | ✅ cho `similarity` |
| Upscale text bé | **OpenCV** (resize Lanczos / super-res nhẹ) | tăng recall text nhỏ | thêm thời gian | ✅ có điều kiện |

> **Đa ngôn ngữ là bắt buộc** (dự án test i18n). Đề xuất mặc định bật bộ: `latin + vi + cjk`
> (+`arabic` khi cần RTL). PaddleOCR cho phép chọn `lang`; cân nhắc auto theo `screen.locale`
> nếu có.

## 5. Pipeline A5 (đề xuất)
1. **Chọn vùng:** có bbox từ A1/A3 → OCR theo từng vùng/crop; không có → quét full ảnh.
2. **Tiền xử lý có điều kiện:** ước lượng cỡ chữ; nếu < ngưỡng px → **upscale** crop (giữ bản
   gốc cho A8). Giữ ảnh màu (không ép nhị phân — UI nhiều nền).
3. **Phát hiện + Nhận dạng** (PaddleOCR): box + text + conf + angle, theo bộ ngôn ngữ đã chọn.
4. **Normalize:** NFC, strip, gộp khoảng trắng; cờ `has_replacement` nếu thấy `�`/chuỗi `□`.
5. **Grouping:** word→line (cluster theo overlap trục y + gần trục x) → block; gán
   `parent/level`; suy **reading order** (LTR mặc định; RTL nếu script=arabic/hebrew).
6. **Script/lang:** phân loại theo bảng Unicode block + `lang_hint` từ langdetect.
7. **(Mode A) Đối chiếu:** map segment ↔ element A1 theo IoU bbox; tính `similarity`
   (rapidfuzz) giữa `dom_text` và `ocr_text` → verdict (`match | render_mismatch | missing_on_screen`).
8. **Emit** `text_segments[]` (+ `tree_text_match[]` ở Mode A) cho A0 / A3 / Rule R4 / A8.

## 6. Mode A vs Mode B (ranh giới rõ)
- **Mode B:** A5 = nguồn `text` chính → `element.text` lấy từ segment fuse vào box (A3).
  Confidence = OCR conf. Text sai/thiếu là rủi ro chính → đánh dấu.
- **Mode A:** `element.text` vẫn là **DOM/XML (ground truth)**; A5 **không ghi đè**, chỉ thêm
  `tree_text_match` để Rule/Agent bắt **lỗi render**:
  - `dom_text` có, `ocr_text` rỗng/khác xa ⇒ nghi **tofu / bị che / cắt / màu trùng nền**
    (TYP-01/03/04, STY invisible-text).
  - `dom_text` rỗng nhưng ảnh có chữ ⇒ text vẽ trong ảnh (→ A11) hoặc DOM thiếu.

## 7. Tiêu chí được A5 cấp data nền
- **Toàn bộ CNT** (text là input): CNT-01 placeholder, CNT-02 i18n-key, CNT-03 sai ngôn ngữ
  (qua `script`/`lang_hint`), CNT-04 lorem, CNT-05 debug, CNT-06 mojibake, CNT-07 escape,
  CNT-08/12 số/đơn vị, CNT-09 chính tả, CNT-10/11/13/14 (text cho agent).
- **TYP:** TYP-01 tofu (cờ `has_replacement` → A8 chốt), TYP-03 cắt cụt (đối chiếu Mode A),
  TYP-06 ngắt dòng (line grouping), TYP-11 casing, TYP-12 RTL (`script`+reading order).
- **CMP-07** placeholder-vs-value, **CMP-08** label nút bị cắt, **STATE-05** stale placeholder.
- **CONS-07** định dạng số/ngày xuyên màn → **Phase 2** (đa ảnh).
- Cấp **text-box** để A3 fuse (containment) và **crop** cho A8 soi glyph.

## 8. Edge cases (BẮT BUỘC xử lý)
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

## 9. Open decisions (cần anh chốt — lựa chọn lớn)
- [ ] **OCR engine chính:** đề xuất **PaddleOCR chính + Tesseract dự phòng/đối chiếu chéo**.
  Chốt vì ảnh hưởng dependency (paddle nặng) & GPU. (Anh quyết: Paddle-only cho gọn, hay giữ
  cả 2 để đối chiếu?)
- [ ] **Mode A có luôn chạy OCR để đối chiếu không?** Đề xuất **CÓ** — rẻ tương đối mà bắt được
  lỗi render (tofu/che/cắt) cây không thấy. (Trade-off: thêm thời gian mỗi request.)
- [ ] **Bộ ngôn ngữ mặc định** + auto chọn theo `screen.locale` nếu có. Đề xuất `latin+vi+cjk`,
  thêm `arabic` khi locale RTL.
- [ ] Ngưỡng upscale text-bé & ngưỡng conf để gắn cờ → **tune bằng golden set (GS)**.

## 10. TDD outline (khi vào code)
- test: ảnh 1 dòng text sạch → đúng `text` + bbox + conf cao.
- test: NFC normalize dấu tiếng Việt (tổ hợp → dựng sẵn) giống nhau.
- test: grouping word→line đúng (3 từ 1 dòng → 1 line, đúng thứ tự).
- test: script detect (latin / cjk / arabic) đúng nhãn.
- test: `has_replacement` bật khi có `�`/`□`.
- test (Mode A): `dom_text`="Đăng nhập" vs `ocr_text`="Ð□ng nh□p" → verdict `render_mismatch`.
- test (Mode A): map segment↔element theo IoU đúng cặp.
- test: RTL → reading order đảo.
- test: ảnh không có text → trả `[]`, không crash.
- test: recall text-nhỏ đo bằng GS (không hard-assert).

## Trạng thái: spec ✅ — chờ chốt mục 9 (engine + chạy-OCR-ở-Mode-A + bộ ngôn ngữ).
