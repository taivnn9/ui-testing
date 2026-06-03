# Bước 2: Kiến trúc xử lý + mapping input / xử-lý / output theo tiêu chí

> **Mục đích bước 2** (kế hoạch của chủ dự án): với mỗi tiêu chí trong
> [`catalog-tieu-chi-loi-ui.md`](catalog-tieu-chi-loi-ui.md), xác định:
> cần **input** gì → **xử lý** thế nào (analyzer nào / rule hay AI) → **output** ra sao.
>
> Tài liệu sống. Trạng thái: **đang thảo luận kiến trúc** (chưa chốt hết).
> Phiên: 2026-05-22. Bằng tiếng Việt.

> ⚠️ **LỖI THỜI MỘT PHẦN (giữ làm lịch sử).** Tài liệu này còn mô tả **Mode A/B** và
> input **DOM/XML** (Tree Parser A1, Style Reader A2, `source=dom/xml`, routing có/không cây).
> Kiến trúc **đã chốt lại** sau đó: **MỘT CHẾ ĐỘ vision-only**, input ảnh duy nhất
> (xem `../CLAUDE.md` §2.1). Mọi đoạn nói Mode A / DOM / XML / A1 / A2 **không còn áp dụng** —
> đọc để hiểu lý do thiết kế, không phải spec hiện hành.

---

## 1. Kiến trúc xử lý

### 1.1. Đề xuất gốc của chủ dự án (3 lớp)
1. **Analyzer** — mỗi analyzer trích các data khác nhau từ ảnh/xml/html (OCR, object
   detection, phân cụm, segmentation, bounding...). Số lượng analyzer phụ thuộc **nhu cầu
   data đầu vào của các tiêu chí**.
2. **Agents** — đánh giá dựa trên data + định nghĩa tiêu chí (dùng AI, prompt engineering,
   skill, rule). Output mỗi agent = kết quả 1 tiêu chí: có lỗi không, ở đâu, toạ độ/vùng,
   độ nghiêm trọng...
3. **Summary agent** — tổng hợp các lỗi để trả cho tester.

→ **Khung này đúng hướng**, khớp pipeline đã chốt (Analyzer↔Normalize, Agents↔VLM,
Summary↔Aggregate).

### 1.2. Bốn điều chỉnh (để không phạm nguyên tắc #3: "tách tất định khỏi phán đoán")

**① Lớp 2 KHÔNG phải toàn AI.** Rất nhiều tiêu chí là thuần toán học (contrast, touch-target,
overlap/IoU, off-screen, méo ảnh) → phải để **Rule Engine bằng code** tính, KHÔNG hỏi LLM
(LLM dở số học toạ độ + hay bịa). → Tách Lớp 2 = **2a Rule Engine (code)** + **2b Judgment
Agents (VLM)**. Agent chỉ: (a) confirm/reject candidate của rule (↓ false-positive),
(b) bắt lỗi thẩm mỹ/ngữ cảnh, (c) gán/chỉnh severity trong range.

**② Chèn "Normalize → 1 schema chung" giữa analyzer và lớp 2.** Analyzer đổ data vào **một**
đồ thị `elements[] + relations[] + features` (schema CLAUDE.md mục 5); rule & agent đọc chung,
không tự trích lại. Analyzer **chạy có điều kiện theo Mode**: có DOM/XML → đọc thẳng cây
(khỏi OCR); chỉ ảnh → bật OCR/detect/segment/đo-pixel.

**③ Đừng làm 121 agent.** Gom **theo nhóm tiêu chí + cùng loại input** (tốn token/chậm/khó
dedupe nếu mỗi tiêu chí 1 agent; nhưng cũng đừng "hỏi tìm hết bug 1 phát" → nông).
*(Quyết định granularity: đang chốt — xem mục 3.)*

**④ Bổ sung 2 thứ thiếu:** (1) **Verify/Critic pass** trước Summary để lọc false-positive;
(2) xử lý đặc biệt cho tag **`multi`** (CONS — cần nhiều ảnh để so) và **`ctx`** (cần
tên màn/intent; thiếu thì hạ confidence / đánh dấu).

### 1.3. Pipeline tinh chỉnh

```
Input: ảnh [+ DOM/XML] [+ ngữ cảnh: tên màn/intent] [+ nhiều ảnh nếu cần CONS]
  │
 (1) ANALYZERS — chạy CÓ ĐIỀU KIỆN theo mode + nhu cầu tiêu chí
 │     Mode A: DOM/XML parser (đọc thẳng cây = ground truth)
 │     Mode B: OCR · detect element/icon · segmentation · đo pixel (contrast/clip/blur/ratio)
 │
 (1.5) NORMALIZE → 1 SCHEMA CHUNG (elements[] + relations[] + features, kèm `source`)
  │
 (2a) RULE ENGINE (code, tất định) ❗không hỏi AI
 │      overlap · touch-target · contrast · off-screen · distortion · safe-area...
 │      → candidate_issues (severity nền + bbox)
 │
 (2b) JUDGMENT AGENTS (VLM, theo NHÓM) — nhận: ảnh + schema + candidate_issues
 │      • confirm/reject candidate của rule (↓ false-positive)
 │      • bắt lỗi thẩm mỹ/ngữ cảnh (ctx)
 │      • chỉnh severity trong range (theo modifier)
 │      • Set-of-Marks (trỏ theo ID) + structured output
 │
 (3) VERIFY / CRITIC pass — tự phản biện, lọc confidence thấp
 │
 (4) SUMMARY AGENT — dedupe + gộp + xếp theo severity → trả tester
```

---

### 1.4. Xử lý theo sự hiện diện của cây (routing Mode A / B / mixed) — QUAN TRỌNG

DOM/XML **không phải lúc nào cũng có**. Hệ thống KHÔNG được giả định luôn có cây.
Stage Normalize tự **dò input** và định tuyến — đầu ra LUÔN về cùng schema, kèm `source`
và `confidence` ở cấp element/field để downstream biết độ tin cậy.

| Trường hợp | Analyzer chạy | Ghi chú |
|---|---|---|
| **Có cây đầy đủ** (Mode A) | Tree Parser + Style Reader dựng `elements/style`. Box/Layout, OCR, Interactivity-Classifier **KHÔNG cần** (cây đã cho). | `source=dom/xml`, confidence cao. **Nhưng vẫn BẮT BUỘC chạy analyzer pixel** (Color Sampler, Glyph/Pixel Inspector, Pattern Detector, Image fetch) — vì contrast-thực, tofu, mờ, méo, ảnh vỡ KHÔNG đọc được từ cây. |
| **Không có cây** (Mode B) | OCR + Box/Layout Detector + Interactivity-Classifier + Icon Detector **dựng** `elements`; toàn bộ analyzer pixel chạy. | `source=vision`, confidence thấp hơn. Một số tiêu chí **tắt/yếu**: intrinsic-ratio (IMG-02), tính tương tác (CMP-01/03), font fallback (TYP-02). |
| **Có cây một phần** (mixed) | Lấy field nào cây có (vd bbox/role/text từ XML); **pixel bù** field cây thiếu (vd XML thiếu computed-style → contrast đo từ pixel). | Ghi `source` **theo từng field**, không theo cả element. Vd: bbox `source=xml`, contrast `source=vision`. |

**Quy tắc vàng:** cây lo *hình học + role + text + style chính xác*; pixel lo *diện mạo*
(contrast thực, tofu, mờ, méo, vỡ). Hai cái **luôn bù nhau** — kể cả Mode A vẫn cần pixel.
→ Phần lớn analyzer pixel (Color Sampler, Glyph Inspector, Pattern Detector) **chạy ở CẢ hai
mode**; chỉ nhóm "dựng cấu trúc" (OCR, Box/Layout, Interactivity) là **chỉ bật khi thiếu cây**.

```
Normalize: input có cây?
  ├─ có đầy đủ  → Tree Parser + Style Reader  ─┐
  ├─ một phần   → Tree (field có) + Vision (bù)─┤→ elements[] (mỗi field có `source`)
  └─ không có   → OCR + Box + Interactivity ────┘   + LUÔN: analyzer pixel cho diện mạo
```

---

## 2. Phân loại tiêu chí theo "ai xử lý" (sẽ điền chi tiết)

Mỗi tiêu chí sẽ được gán 1 trong các nhãn xử lý:
- **R** — Rule (code tất định, không cần AI).
- **R→V** — Rule tính candidate, VLM xác nhận/bác bỏ.
- **V** — VLM/judgment (cần phán đoán thị giác/thẩm mỹ).
- **V+ctx** — VLM nhưng cần ngữ cảnh/intent màn hình.
- **multi** — cần nhiều ảnh (so xuyên màn).

→ Việc gán nhãn này (bước 2) sẽ cho ra: (a) danh sách **analyzer cần xây**, (b) danh sách
**rule cần code**, (c) các **nhóm agent** cần prompt. (Granularity agent = hệ quả của mapping,
chốt sau.)

### 2.1. Output chuẩn (mọi tiêu chí, mọi nhãn — chỉ khác phần `evidence`)
```jsonc
{ "criterion":"CNT-01", "element_ids":["e12"], "bbox":{...},
  "severity":"high", "confidence":0.0,
  "evidence":{ "crop":"...", "matched":"{{user.name}}", "measured":null },
  "explanation":"...", "source":"rule|vlm", "mode":"A|B" }
```
→ "Output như nào" đã chốt ở mức khung. Mapping mỗi tiêu chí chỉ cần làm rõ **INPUT**
(data/analyzer) + **XỬ LÝ** (rule/AI + cách phát hiện).

### 2.2. Mapping nhóm A — Content & Semantics (`CNT`)  ✅

| ID | Data cần · analyzer | Nhãn | Phát hiện & evidence riêng |
|---|---|---|---|
| CNT-01 | text (A: cây · B: OCR) | R→V | regex token `undefined/NaN/%s/{0}/{{x}}/${x}`; V xác nhận không phải nội dung thật |
| CNT-02 | text | R→V | regex key i18n (`a.b.c`, snake_case, không dấu cách); V loại FP (url, version) |
| CNT-03 | text + `locale` | R→V (ctx) | lang-detect lib vs `screen.locale`; V xác nhận |
| CNT-04 | text | R | dictionary: "lorem ipsum / your text here / sample" |
| CNT-05 | text | R→V | dict debug + heuristic gibberish ("asdf","qwerty"); V vì FP cao |
| CNT-06 | text / HTML thô | R | regex mojibake `Ã.|â€` + entity `&amp;`,`&#39;`. ⚠ A bắt entity tốt hơn B/OCR |
| CNT-07 | text | R | regex literal `\n` `\t` `<br>` hiện như chữ |
| CNT-08 | text + `locale` | R→V (ctx) | regex epoch/ISO/số chưa format; V phán "đáng lẽ format" |
| CNT-09 | text + lang | V (R hỗ trợ) | spellcheck lib gợi ý → V quyết theo ngữ cảnh |
| CNT-10 | text + intent màn | V+ctx | cần intent/nhiều ảnh; zero-ref yếu → confidence thấp |
| CNT-11 | toàn bộ text + số | R→V | code dò chuỗi trùng / số mâu thuẫn; V phán chủ ý |
| CNT-12 | text + ngữ cảnh field | V+ctx | thiếu ký hiệu tiền tệ — cần biết field là "giá" |
| CNT-13 | text + quan hệ/đếm | R→V (ctx) | code đối chiếu "0 sản phẩm" vs số item thực; else V |
| CNT-14 | text + intent màn | V+ctx | cần biết disclaimer nào bắt buộc — domain knowledge |

**Analyzer nhóm A:** 1 chính = **Text Extractor** (A: đọc cây; B: OCR). Rule libs dùng chung:
regex token, heuristic i18n-key, dictionary (lorem/debug), language-detection, spellcheck,
regex mojibake/entity. Đa số R/R→V (hợp zero-ref); 3 cái ctx (CNT-10/12/14) yếu.

### 2.3. Nhóm B — Typography (`TYP`)  ✅
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| TYP-01 | pixel chữ (B: Glyph Inspector) | R→V | dò glyph hộp □/▯ lặp; V xác nhận. A: heuristic font thiếu dấu |
| TYP-02 | font-family (A) / pixel (B) | V | "trông như font hệ thống/sai font" — cần ref → yếu, conf thấp |
| TYP-03 | text bbox + container (A: cây · B: Box+OCR) | R→V | box text vượt/clip parent, không "…" → candidate; V chủ ý vs lỗi + severity theo nội dung |
| TYP-04 | bbox text & phần tử | R→V | IoU text–text / text–element; V loại watermark chủ ý |
| TYP-05 | font_size (A) / cao px+dpr (B) | R | ngưỡng (<12pt body); R→V vì có text nhỏ hợp lệ (legal) |
| TYP-06 | text + line boxes | R→V | gãy giữa từ / từ dài tràn / mồ côi; V thẩm mỹ |
| TYP-07 | line-height (A) / khoảng cách dòng px (B) | R→V | ngưỡng tỉ lệ; V thẩm mỹ |
| TYP-08 | letter-spacing (A) / px (B, khó) | V | thẩm mỹ; B yếu |
| TYP-09 | pixel sharpness chữ | R→V | metric mờ/răng cưa trên crop; V xác nhận |
| TYP-10 | text-align (A) / căn lề px (B) | V (ctx) | "đáng lẽ căn trái" — cần ngữ cảnh |
| TYP-11 | text | R→V | dò ALL-CAPS dài; V phán sai chỗ |
| TYP-12 | text + locale RTL | V+ctx | script RTL + chiều dấu/số; cần visual; khó |
| TYP-13 | font-family/cụm (A) / phân loại font px (B) | R→V | A: đếm font khác nhau trong cụm; B yếu |
| TYP-14 | pixel emoji | R→V | dò emoji thành hộp/mất màu |

**Analyzer B:** Glyph/Pixel-Text Inspector (tofu/mờ/emoji), Box/Layout (container), Style Reader (A: font_size/family/line-height/align — miễn phí). ⚠ Mode B yếu: 02/08/10/13.

### 2.4. Nhóm C — Color/Style (`STY`)  ✅
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| STY-01 | màu chữ+nền (A: style; nền ảnh→Pixel Sampler) | R | công thức WCAG, ngưỡng 4.5/3; R→V khi nền ảnh/gradient |
| STY-02 | contrast ~1 | R | ratio <1.1 (cực của 01) |
| STY-03 | theme=dark + màu (Pixel Sampler) | R→V | vùng sáng/tương phản bất thường trong dark; V xác nhận |
| STY-04 | màu icon vs nền (Pixel + Icon Detector) | R→V | tương phản đồ hoạ <3:1 |
| STY-05 | opacity (A) / alpha px (B) | R / R→V | A: opacity<1 bất ngờ; B: ước lượng px |
| STY-06 | palette + brand ref | V / multi | cần ref bảng màu → yếu; so xuyên màn |
| STY-07 | disabled attr+style (A) / px (B) | R→V (ctx) | A: disabled nhưng màu == sibling enabled |
| STY-08 | focus state | V | focus tạm thời, khó từ ảnh tĩnh → yếu |
| STY-09 | pixel màu ngữ nghĩa | V+ctx | thông tin chỉ bằng màu (đỏ/xanh) |
| STY-10 | pixel gradient/shadow | R→V | metric banding/viền cứng; V |
| STY-11 | border (A) / line px (B) | R→V | thiếu/thừa/nhân đôi divider |
| STY-12 | pixel vùng nền | V | nền sai vùng |
| STY-13 | màu đồ hoạ vs nền (Pixel) | R | ngưỡng 3:1 |

**Analyzer C:** Pixel Color Sampler (chìa khoá), Icon/Graphic Detector, Style Reader (A). Rule: WCAG. ⚠ yếu/aesthetic: 06/08/09/10/12.

### 2.5. Nhóm D — Layout (`LAY`)  ✅ — nhóm "vàng" của zero-ref (gần hết R/R→V)
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| LAY-01 | bbox+z (A: cây · B: Box Detector+segment) | R→V | IoU overlap phần tử không cha-con; V xác nhận |
| LAY-02 | bbox vs viewport | R | vượt/clip mép màn |
| LAY-03 | child vs parent bbox | R→V | A dễ; B cần dò container |
| LAY-04 | gap giữa siblings | R→V | gap không bội 8 / không đều; V thẩm mỹ |
| LAY-05 | mép/tâm canh | R→V | lệch mép nhỏ; V (optical tinh tế) |
| LAY-06 | overlap+z+visible | R→V | bị phần tử z cao che; V xác nhận che nhầm |
| LAY-07 | gap | V / R→V | ngưỡng cực; thẩm mỹ |
| LAY-08 | tâm phần tử vs tâm container | R→V | lệch tâm |
| LAY-09 | (cần nhiều kích thước) | R→V / V | reflow — lý tưởng cần đa kích thước; 1 ảnh chỉ bắt collapse rõ |
| LAY-10 | scrollW/H vs client (A) / cắt mép (B) | R | không cuộn được / double scrollbar |
| LAY-11 | bbox fixed vs content | R→V | header/footer dính đè |
| LAY-12 | size bất thường vs siblings | R→V (ctx) | khối phình/teo |
| LAY-13 | vùng trống (pixel/gap) | R→V (ctx) | metric vùng trống; V chủ ý |
| LAY-14 | bbox gần trùng | R | 2 phần tử cùng toạ độ |
| LAY-15 | thứ tự + expected | V+ctx | sắp xếp sai |

**Analyzer D:** Box/Layout Detector (THE chìa khoá; A: bounds+parent/child từ cây, B: detect+segment+cluster) + Relation pre-computer (overlap/gap/align). Rule: IoU, parent-overflow, viewport, grid-8pt, alignment, scroll, near-dup-pos. ctx: 12/13/15.

### 2.6. Nhóm E — Images/Media (`IMG`)  ✅
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| IMG-01 | vùng ảnh (A: naturalWidth/src; B: Image Inspector+OCR alt) | R→V | A: naturalWidth==0/src lỗi; B: pattern broken-img + alt text |
| IMG-02 | intrinsic vs displayed ratio | R | A: image_meta; ⚠ B yếu (không biết intrinsic nếu không fetch source) |
| IMG-03 | pixel sharpness ảnh | R→V | metric mờ + dò upscale |
| IMG-04 | pixel (face/text edge) | V+ctx | cắt mất phần quan trọng — cần biết "quan trọng" |
| IMG-05 | slot ảnh rỗng | R→V (ctx) | A: container img rỗng; B: vùng trống |
| IMG-06 | icon + ngữ nghĩa | V+ctx | icon sai nghĩa |
| IMG-07 | bbox icon vs nút | R→V | lệch tâm icon trong nút |
| IMG-08 | pixel placeholder | R→V | hộp/dấu ? chưa load |
| IMG-09 | object-fit+ratio (A) / méo-cắt (B) | R→V / V | scale-mode sai |
| IMG-10 | nội dung ảnh vs ref/brand | V+ctx / multi | sai phiên bản/lộn brand |
| IMG-11 | pixel logo | V / R→V | mờ/sai màu/tỉ lệ (reuse blur) |
| IMG-12 | perceptual hash | R→V | ảnh trùng; V chủ ý |
| IMG-13 | như IMG-01 cho poster | R→V | thumbnail/poster vỡ |
| IMG-14 | pixel ảnh dở | V / R→V | load nửa chừng |
| IMG-15 | nội dung ảnh vs context | V+ctx | sai ảnh sản phẩm |

**Analyzer E:** Image Region Detector, Image Meta Reader (mạnh A, ⚠ yếu B), Icon Detector, Pixel sharpness, Perceptual Hashing, Face/Text-in-image. ⚠ Nặng ctx + Mode B yếu (intrinsic ratio).

### 2.7. Nhóm F — Components/Controls (`CMP`)  ✅
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| CMP-01 | bbox tương tác + dpr (A: clickable; B: Interactivity classifier) | R | ngưỡng 44pt/48dp. ⚠ B phải SUY LUẬN tính tương tác |
| CMP-02 | A: thiếu text/aria/alt; B: icon-only không text gần | R→V / V | nút không nhãn |
| CMP-03 | overlap+z+interactive | R→V | không tap được do đè |
| CMP-04 | state control + expected | R→V / V+ctx | radio chọn >1 = R; còn lại ctx |
| CMP-05 | nút trùng (text+role) | R→V | trùng component |
| CMP-06 | control expected vắng | V+ctx | thiếu submit/back |
| CMP-07 | A: attrs input+label; B: px/OCR | R→V / V | focus/label/placeholder |
| CMP-08 | text box vs control box | R→V | label/nút cắt cụt |
| CMP-09 | disabled vs expected | V+ctx | disabled sai |
| CMP-10 | canh control trong nhóm | R→V | lệch hàng |
| CMP-11 | bbox popup vs viewport | R | dropdown lòi màn (reuse off-screen) |
| CMP-12 | spinner present | V | reuse STATE-01 |
| CMP-13 | bbox badge vs anchor + "99+" | R→V | badge lệch/tràn |
| CMP-14 | khác biệt visual tab chọn | R→V / V | không rõ tab đang chọn |
| CMP-15 | size cùng component | R→V / multi | không nhất quán cỡ |
| CMP-16 | gap giữa control tương tác | R | tap chồng |
| CMP-17 | content cắt không gợi ý cuộn | V+ctx | thiếu affordance |

**Analyzer F:** Box + Interactivity Classifier (A: role/clickable = ground truth; ⚠ B suy luận), Text Extractor (label), Component Detector (B). ⚠ Khác biệt A/B LỚN NHẤT: *biết phần tử có tương tác không*. ctx: 04/06/09/17.

### 2.8. Nhóm G — State/Lifecycle (`STATE`)  ✅ — ⚠ nhiều cái cần THỜI GIAN (≥2 frame)
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| STATE-01 | pixel skeleton/shimmer | R→V | dò khối skeleton; ⚠ "kẹt" cần ≥2 frame mới chắc |
| STATE-02 | vùng trống + thiếu msg | R→V (ctx) | empty state |
| STATE-03 | text (stack/err) | R→V | regex exception/HTTP code/"Error:" |
| STATE-04 | nội dung thiếu khối | V / R→V | render dở |
| STATE-05 | placeholder sót (reuse CNT-04) | V+ctx | stale data |
| STATE-06 | spinner+overlay | R→V | overlay đè; ⚠ temporal |
| STATE-07 | modal/toast present | V | ⚠ temporal (kẹt) |
| STATE-08 | item trùng / loading cuối list | R→V | pull-refresh/pagination |
| STATE-09 | (đa frame) | V / multi-frame | animation kẹt — 1 ảnh bất lực |
| STATE-10 | badge count vs số item | R→V (ctx) | trạng thái lệch dữ liệu |
| STATE-11 | màn trắng/không content | R→V (ctx) | offline không xử lý |

**Analyzer G:** Text Extractor (regex lỗi), Pixel Pattern Detector (skeleton/spinner/overlay/blank), Box (vùng trống/item trùng), Perceptual Hash. ⚠⚠ **PHÁT HIỆN:** "kẹt/stuck/animation" mang tính **thời gian** → lý tưởng cần **≥2 frame**. Từ 1 ảnh chỉ suy "có dấu hiệu".

### 2.9. Nhóm H — Platform/Environment (`ENV`)  ✅ — ⚠ nhiều cái cần CAPTURE đặc biệt
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| ENV-01 | content bbox vs safe_area | R | xâm phạm safe-area; cần safe_area (device profile) |
| ENV-02 | content dưới system bar + màu | R→V | bar đè/lẫn màu |
| ENV-03 | control đáy vs vùng home-indicator | R | iOS home đè |
| ENV-04 | keyboard present + input focus | R→V | ⚠ cần ảnh "bàn phím đang mở" |
| ENV-05 | (cần ảnh landscape) | R→V / V | ⚠ cần capture xoay |
| ENV-06 | (cần ảnh font-scale lớn) | R→V | ⚠ reuse overflow/overlap trên capture cỡ chữ lớn |
| ENV-07 | (đa thiết bị) | R→V | ⚠ cần capture nhiều device |
| ENV-08 | (đa width) | R→V | ⚠ cần capture nhiều breakpoint |
| ENV-09 | content cắt đáy mobile browser | R→V | 100vh/viewport-unit |
| ENV-10 | dpr + ratio (reuse IMG-03) | R | asset sai mật độ |
| ENV-11 | (capture foldable/cutout) | R→V | ⚠ device đặc thù |
| ENV-12 | tương tác cần hover | V | ⚠ khó từ ảnh tĩnh |
| ENV-13 | pixel splash | R→V | splash kẹt/méo |

**Analyzer H:** Box + Device/Env Metadata (safe_area/dpr/bar/orientation — từ device profile, KHÔNG từ ảnh), Pixel Detector (keyboard/splash/bars). ⚠⚠ **PHÁT HIỆN:** nhiều ENV cần **điều kiện capture cụ thể** (keyboard-open, landscape, font lớn, nhiều width/device) — **harness test phải chủ động chụp**; từ 1 ảnh mặc định KHÔNG bắt được. Đây là yêu cầu *thu thập input*.

### 2.10. Nhóm I — Consistency (`CONS`)  ✅ — toàn bộ cần NHIỀU ẢNH
| ID | Data · analyzer | Nhãn | Phát hiện & evidence |
|---|---|---|---|
| CONS-01 | cùng component qua màn (match role/text) | R→V | so kích cỡ |
| CONS-02 | font same-role qua màn | R→V | lệch font |
| CONS-03 | palette qua màn | R→V | theme drift |
| CONS-04 | phong cách icon | V | outline vs filled |
| CONS-05 | label cùng hành động | R→V (ctx) | thuật ngữ không nhất quán |
| CONS-06 | hệ gap qua màn | R→V | spacing không nhất quán |
| CONS-07 | format số/ngày/tiền | R→V | reuse CNT-08 |
| CONS-08 | vị trí phần tử chung (back) | R→V | lệch vị trí |
| CONS-09 | phong cách ảnh | V | tỉ lệ/bo góc/filter khác |

**Analyzer I:** reuse toàn bộ analyzer per-screen + Cross-screen Matcher (gióng phần tử giữa màn) + Consistency Agent. ⚠⚠ **PHÁT HIỆN:** cần API nhận **một TẬP ảnh** (1 flow), không chỉ 1 ảnh.

### 2.11. TỔNG HỢP: analyzer · rule · agent (dẫn xuất từ mapping)

**A. Analyzers cần xây** (số nhóm tiêu chí dùng → ưu tiên):
| # | Analyzer | Mode | Phục vụ |
|---|---|---|---|
| 1 | **Tree Parser** (DOM/XML → schema) | A | tất cả (ground truth) |
| 2 | **OCR / Text Extractor** | B | CNT, TYP, STATE(err), CMP(label) |
| 3 | **Box/Layout Detector** (+segment/cluster) | B | LAY, TYP(container), CMP — *chìa khoá Mode B* |
| 4 | **Interactivity Classifier** | B | CMP, LAY(tap) — ⚠ khó |
| 5 | **Icon/Graphic Detector** | A·B | IMG, STY(graphic), CMP |
| 6 | **Image Region + Meta Reader** | A·B | IMG, ENV-10 — ⚠ intrinsic yếu ở B |
| 7 | **Pixel Color Sampler** | A·B | STY (contrast/dark/opacity) |
| 8 | **Pixel/Glyph Inspector** | B | TYP (tofu/mờ/emoji), STY(banding) |
| 9 | **Pixel Pattern Detector** | B | STATE, ENV (skeleton/spinner/keyboard/splash/blank/broken) |
| 10 | **Perceptual Hashing** | A·B | IMG/STATE (trùng) |
| 11 | **Face/Text-in-image Detector** | B | IMG-04 (crop) |
| 12 | **Style Reader** (computed-style) | A | TYP, STY, CMP — *miễn phí, mạnh* |
| 13 | **Device/Env Metadata provider** | — | ENV (safe_area/dpr/bar/orientation) |
| 14 | **Cross-screen Matcher** | — | CONS, một số ENV/CMP `multi` |
| + | **Normalize + Relation pre-computer** | — | gộp về schema chung, tiền tính relations |

**B. Rule libs (code tất định):**
- *Geometry:* IoU/overlap · parent-overflow · viewport/off-screen · grid-8pt/gap · alignment · near-dup-pos · scroll-overflow · touch-target · tap-gap · safe-area · icon-centering · badge-geom.
- *Color:* WCAG (text 4.5/3, graphic 3:1) · invisible-text · opacity.
- *Image:* distortion-ratio · broken-image · upscale · hash-dup.
- *Text:* token/placeholder regex · i18n-key · mojibake/entity · escape-literal · lorem/debug dict · epoch/format · all-caps · stack-trace.
- *Cross-screen:* attribute-variance.

**C. Agent groups (VLM — gom theo CỤM, KHÔNG 121 agent):** đề xuất ~6–7 nhóm
(mỗi nhóm = 1 lượt VLM nhận ảnh + schema + candidate liên quan):
Text/Content · Typography-Render · Color/Style · Layout · Image · Component+State ·
Consistency(đa ảnh) [+ Context/intent agent khi có input intent].
→ Granularity chính xác chốt sau — nhưng chắc chắn **theo cụm chức năng**, không per-criterion.

---

## 3. Quyết định đang mở (cần chủ dự án chốt)

**Về INPUT của API — ĐÃ CHỐT (2026-05-22):**
- ✅ **Phase 1 (target trước):** chỉ **1 ảnh + DOM/XML (tùy chọn)**. Mode A & B đều có.
- ⏭ **Phase 2:** **nhóm ảnh / screen-group** (mở khoá toàn bộ CONS + `multi` xuyên màn).
- ⏭ **Phase 2+:** ngữ cảnh/intent màn (nâng `ctx`), đa frame (STATE temporal), capture variants (ENV).

### 3.1. Phạm vi Phase 1 (chốt theo input "1 ảnh + cây")
**Analyzer Phase 1:** 13/14 cái (TẤT CẢ trừ #14 Cross-screen Matcher → Phase 2).
*Ưu tiên xây trước (mở khoá nhiều + chuẩn zero-ref):* Tree Parser · Style Reader (A) ·
Box/Layout · Pixel Color Sampler · OCR → bật ngay **LAY + STY + CNT/TYP**.

**Coverage Phase 1 theo nhóm:**
| Nhóm | Phase 1 | Ghi chú |
|---|---|---|
| CNT | ✅ phần lớn | trừ ctx (CNT-10/12/14): chạy nhưng confidence thấp (thiếu intent) |
| TYP | ✅ phần lớn | B yếu: 02/08/10/13 |
| STY | ✅ gần hết | aesthetic yếu: 06/08/09/10/12 |
| LAY | ✅ toàn bộ per-screen | nhóm "vàng" — làm trước |
| IMG | ✅ phần lớn | B yếu intrinsic ratio (02); ctx (04/06/10/15) confidence thấp |
| CMP | ✅ phần lớn | B yếu "tính tương tác"; ctx (04/06/09/17) thấp |
| STATE | ⚠ một phần | chỉ tín hiệu 1-frame (01/03/04/06/07/08); "kẹt/animation" (09) cần đa frame → Phase 2+ |
| ENV | ⚠ subset 1-ảnh | bật: 01/02/03/09/10/13. Hoãn: 04/05/06/07/08/11/12 (cần capture variant) → Phase 2+ |
| CONS | ⏭ Phase 2 | toàn bộ cần nhóm ảnh |

**Nguyên tắc Phase 1:** tiêu chí `ctx`/temporal/variant vẫn để trong schema nhưng **đánh dấu
confidence thấp / "cần input Phase 2"**, KHÔNG xoá — để xuống cấp mượt và không vỡ schema.

**Về XỬ LÝ:**
- [ ] Granularity Judgment Agents: xác nhận **~6–7 nhóm theo cụm** (mục 2.11.C)?
- [ ] Xác nhận tách **Rule Engine (code)** riêng khỏi AI? *(đề xuất: có — nguyên tắc #3)*

**Giới hạn Mode B cần chấp nhận** (confidence thấp, đánh dấu rõ):
- [ ] Font fallback (TYP-02), intrinsic ratio/distortion (IMG-02), tính tương tác (CMP-01/03) — Mode B suy luận, không chắc như Mode A.

---

## 4. Tiến độ bước 2
- [x] Nhận đề xuất kiến trúc 3 lớp của chủ dự án.
- [x] Phản biện + đề xuất kiến trúc tinh chỉnh (4 điều chỉnh).
- [x] Output chuẩn thống nhất.
- [x] Mapping input/xử-lý cho **121 tiêu chí / 9 nhóm** (A→I).
- [x] Suy ra **14 analyzer + bộ rule libs + ~6–7 nhóm agent** (mục 2.11).
- [ ] Chốt các quyết định mục 3 (input dạng nào, granularity agent).
- [ ] (Bước 3 tương lai) Bóc tách chi tiết từng analyzer + spec từng agent (prompt/skill/rule cụ thể).
