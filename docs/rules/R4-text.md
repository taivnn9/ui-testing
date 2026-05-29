# R4 — Text Rules (placeholder + typography tất định)

> **Nguồn dữ liệu:** `elements[].text` (từ A5 OCR), `elements[].style.font_size`,
> `elements[].text_truncated` (từ A5).
> Phần R4 là **regex/pattern matching tất định** — không cần LLM.
> Phần "nội dung sai ngữ cảnh" (CNT-09/10/11) → để VLM G1 agent xử lý.

## Danh sách rules

| Rule ID | Tiêu chí | Pattern / Điều kiện |
|---|---|---|
| `R4-CNT01` | CNT-01 Placeholder/biến chưa render | regex: `undefined`,`null`,`NaN`,`%s`,`{{…}}`,`${…}`,`%@` |
| `R4-CNT02` | CNT-02 i18n key lòi ra | regex: `[a-z_]+\.[a-z_]+` dạng key-path, không chứa space |
| `R4-CNT04` | CNT-04 Lorem ipsum | dictionary: `lorem ipsum`, `your text here`, `placeholder text` |
| `R4-CNT05` | CNT-05 Text debug nội bộ | dictionary: `asdf`,`TODO`,`TEST`,`DO NOT SHIP`,`FIXME`,`[test]`,`dummy` |
| `R4-CNT06` | CNT-06 Mojibake / HTML entity | regex: `Ã©`,`â€™`,`&amp;`,`&#[0-9]+;`,`&[a-z]+;` ngoài nội dung HTML |
| `R4-CNT07` | CNT-07 Escape literal | regex: `\\n`,`\\t`,`<br>`,`<br/>`,`&lt;`,`&gt;` như text thật |
| `R4-CNT08` | CNT-08 Epoch / số thô | regex: epoch 10-13 digit, UNIX ts, ISO date trong format sai |
| `R4-TYP03` | TYP-03 Text cắt cụt (unintended) | elem.text_truncated=true + không có "…" chủ ý |
| `R4-TYP05` | TYP-05 Cỡ chữ quá nhỏ | style.font_size_px < FONT_MIN_PX (11px) |
| `R4-STATE03`| STATE-03 Stack trace / raw error | regex: exception patterns, stack trace |

---

## Chi tiết từng rule

### R4-CNT01 — Placeholder / biến chưa render

```
Input:  elem.text  (từ A5, đã NFC-normalize)
        elem.role: text|button|input|tab|nav|container (có text)
Patterns (case-insensitive, whole-word hoặc standalone):
  LITERAL:
    "undefined", "null", "NaN", "None"
    "n/a" (chỉ khi standalone, viết hoa toàn bộ: "N/A" — hợp lệ)
  TEMPLATE ENGINE:
    {{…}}  →  regex: \{\{[^}]+\}\}
    ${…}   →  regex: \$\{[^}]+\}
    %s, %d, %@, %1$s, %2$d  →  regex: %[@sdf\d$]+
    {0}, {name}  →  regex: \{[a-zA-Z0-9_]+\}
    __PLACEHOLDER__, [[var]]
  FRAMEWORK-SPECIFIC:
    @string/…  (Android XML leak)
    NSLocalizedString  (iOS leak hiếm gặp)
    UNTRANSLATED_…

Điều kiện:
  Một trong các pattern khớp trong elem.text
  Không fire nếu: text là code block (role=code hoặc trong monospace context)
  
Confidence: elem.confidence × 0.92
Severity nền: high; range: medium→critical
Modifier ↑: role=button|CTA | text là label chính → high–critical
Modifier ↓: role=input (placeholder attribute hợp lệ) → medium (nhưng value thật thì high)
```

**Regex cụ thể (Python):**
```python
PLACEHOLDER_PATTERNS = [
    r'\bundefined\b',
    r'\bnull\b',
    r'\bNaN\b',
    r'\bNone\b',
    r'\{\{[^}]+\}\}',
    r'\$\{[^}]+\}',
    r'%[@sdf]|\%\d+\$[@sdf]',
    r'\{[a-zA-Z_]\w*\}',
    r'%s|%d|%i|%f|%@',
    r'__\w+__',
    r'\[\[\w+\]\]',
    r'@string/\w+',
]
```

---

### R4-CNT02 — i18n key lòi ra chưa dịch

```
Patterns:
  Dạng dot-notation: "home.title", "btn.submit", "error.network.timeout"
    → regex: ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,4}$
  Dạng SCREAMING_SNAKE: "BTN_SUBMIT", "HOME_TITLE"  
    → regex: ^[A-Z][A-Z0-9_]{3,}$
  Dạng underscore chỉ: "home_title", "btn_submit" (không có space, không phải tên)
    → regex: ^[a-z][a-z_]{3,}$ (nếu không phải English word)

Điều kiện:
  Pattern khớp VÀ:
    - text ngắn (< 40 ký tự) — key thường ngắn
    - Không có space giữa các từ (hoặc rất ít)
    - Không phải URL / email / snake_case trong code block

False positive phổ biến:
  - "sign_in" thực ra là text hợp lệ → loại nếu text hợp lệ theo từ điển cơ bản
  - URL path: "home/profile" → loại nếu có "/"

Confidence: elem.confidence × 0.75  (false positive cao — cần VLM G1 confirm)
Severity nền: high; range: medium→critical  (CNT-02)
```

---

### R4-CNT04 — Lorem ipsum / placeholder copy

```
Dictionary (case-insensitive, partial match):
  "lorem ipsum", "lorem ipsum dolor",
  "your text here", "text placeholder",
  "sample text", "dummy text",
  "placeholder", "enter text", "write something here"
  "[placeholder]", "(text)", "[text]"
  
Điều kiện: bất kỳ phrase trên xuất hiện trong elem.text
Confidence: elem.confidence × 0.95  (ít false positive)
Severity nền: high; range: medium→high
Modifier ↑: text đơn độc trên màn → high
```

---

### R4-CNT05 — Text debug / nội bộ

```
Dictionary (case-insensitive, standalone):
  "asdf", "qwerty", "foobar", "foo", "bar", "baz",
  "TODO", "FIXME", "HACK", "XXX", "TEMP",
  "TEST", "DO NOT SHIP", "DEBUG", "DEV ONLY",
  "[test]", "[debug]", "[todo]",
  "DUMMY", "STUB", "MOCK",
  "[WIP]", "work in progress"
  
Patterns (regex):
  r'\btest\d+\b'  ("test1", "test123")
  r'\b(admin|password|123456)\b'  (credential debug)

Confidence: elem.confidence × 0.85
Severity nền: high; range: medium→critical
Modifier ↑: nằm ở hero area / form submit → critical
```

---

### R4-CNT06 — Mojibake / HTML entity thô

```
Patterns:
  MOJIBAKE (encoding sai UTF-8 → Latin-1):
    "Ã©" = é, "Ã " = à, "â€™" = ', "â€œ" = ", "Ã¨" = è
    Heuristic: nhiều ký tự Ã / â€ liên tiếp → mojibake
    → regex: r'[ÃÂ]{2,}|â€[^\s]{1,3}'
    
  HTML ENTITY THỰC SỰ (không trong HTML context):
    "&amp;", "&lt;", "&gt;", "&nbsp;",
    "&#\d+;", "&[a-z]{2,7};"
    → regex: r'&(?:[a-z]{2,7}|#\d{1,5});'
    
  BOM / invisible chars:
    U+FEFF, U+200B, U+200C, U+200D, U+FFFD (replacement char)
    → check trong raw text
    
Điều kiện: pattern xuất hiện trong text thật (không phải code block)
Confidence: elem.confidence × 0.9
Severity nền: medium; range: low→high
Modifier ↑: tiêu đề, CTA bị dính → high
Tags: i18n
```

---

### R4-CNT07 — Escape literal

```
Patterns:
  r'\\n|\\t|\\r'   → escape sequence thô
  r'<br\s*/?>|<p>|<\/p>|<b>|<\/b>'   → HTML tag thô
  r'&lt;|&gt;|&amp;'   → double-escaped HTML
  
Điều kiện:
  Pattern xuất hiện trong text và không phải context code/monospace
Confidence: elem.confidence × 0.88
Severity nền: medium; range: low→high
```

---

### R4-CNT08 — Epoch / format số sai

```
Patterns:
  UNIX Timestamp (10-digit: seconds since epoch, ~2001–2286):
    regex: r'\b1[3-9]\d{8}\b'   [1300000000 – 1999999999]
    regex: r'\b[12]\d{12}\b'     [ms epoch]
    
  ISO Date render sai locale:
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}'  (ISO full trong UI)
    Ngoại lệ: không fire trong context kỹ thuật (log, debug panel)
    
  Số lớn không định dạng (tài chính):
    r'\b\d{7,}\b'  không có dấu phân cách → có thể epoch hoặc số tài chính sai
    
Điều kiện:
  Pattern khớp trong elem.text
  elem.role không phải "code", không phải input có type=number
Confidence: elem.confidence × 0.7  (nhiều false positive — số hợp lệ cũng dài)
Severity nền: medium; range: low→high
Modifier ↑: giá tiền / ngày tháng rõ ràng bị lòi thô → high
```

---

### R4-STATE03 — Stack trace / raw error

```
Patterns:
  Java/Kotlin: r'at \w+\.\w+\('
  Python: r'Traceback \(most recent call last\)'
  JS: r'TypeError:|ReferenceError:|SyntaxError:|Error:'
  iOS: r'Thread \d+.*crash'
  Generic: r'Exception in thread|java\.lang\.|NullPointerException'
  HTTP error code: r'\b[45]\d{2}\b' (400–599) nếu xuất hiện đơn độc
  
Điều kiện:
  Pattern khớp trong elem.text (thường là container text block)
Confidence: elem.confidence × 0.9
Severity nền: high; range: medium→critical  (STATE-03)
Modifier ↑: nằm ở foreground (không phải hidden/debug panel) → critical
```

---

### R4-TYP03 — Text cắt cụt (unintended)

```
Input:  elem.text_truncated (bool từ A5 OCR)
        elem.text (để kiểm tra "…" chủ ý)
Điều kiện:
  elem.text_truncated == True
  VÀ text KHÔNG kết thúc bằng "…" hoặc "..." hoặc "more"
    → tức là bị cắt mà không có ellipsis → lỗi
  
  elem.text_truncated == True VÀ kết thúc bằng "…"
    → có thể chủ ý (ellipsis) → confidence thấp, VLM xác nhận

Confidence:
  Không có ellipsis: elem.confidence × 0.8
  Có ellipsis: elem.confidence × 0.4 (thấp — VLM xác nhận)
  
Severity nền: medium; range: trivial→critical
Modifier ↑: role=button|CTA (text nút bị cắt) → high–critical
Modifier ↑: text chứa số/tiền/phủ định ("không") → critical
Modifier ↓: role=body-text, có ellipsis rõ → low–trivial
Tags: i18n (thường do text dài sau dịch)
```

---

### R4-TYP05 — Cỡ chữ quá nhỏ

```
Input:  elem.style.font_size  (px — từ A5 hoặc A4 ước lượng)
        screen.viewport.dpr
Điều kiện:
  font_size_px = elem.style.font_size  (trong device px)
  if font_size_px < FONT_MIN_PX (11px): fire HIGH
  if font_size_px < FONT_WARN_PX (13px): fire MEDIUM

Confidence: elem.confidence × 0.75
  (A5 ước lượng font_size từ bbox height — không chắc 100%)
Severity nền: medium; range: low→high
Modifier ↑: body text chính, tên sản phẩm → high
Modifier ↓: copyright/legal text nhỏ (bình thường) → low
Tags: a11y
Ghi chú: Nếu screen.font_scale > 1 (trợ năng), ngưỡng thực tế lớn hơn →
  font đã scale lên rồi; rule nên tính font_size trước scale: font_size_px / font_scale.
```

---

## Tổng hợp regex module

Tất cả patterns trên sẽ được đóng gói trong `src/ui_defect/rules/patterns.py`:
```
r4_placeholder_patterns[]
r4_i18n_key_patterns[]
r4_lorem_ipsum_dict[]
r4_debug_dict[]
r4_mojibake_patterns[]
r4_escape_patterns[]
r4_epoch_patterns[]
r4_stacktrace_patterns[]
```

→ Dùng `re.compile` + cache; function `match_any(text, patterns) → list[match]`.

## Phân chia trách nhiệm R4 vs VLM

| Kiểm tra | R4 (regex tất định) | VLM G1 (xác nhận / bổ sung) |
|---|---|---|
| Placeholder = `undefined` | ✅ R4-CNT01 | Xác nhận context |
| i18n key lòi | ✅ R4-CNT02 (confidence thấp) | Xác nhận là key hay từ thật |
| Lỗi chính tả | ❌ VLM | G1 Text agent |
| Nội dung sai ngữ cảnh | ❌ VLM | G1 Text agent |
| Text trùng lặp / mâu thuẫn | ❌ VLM multi | G1 cross-element |

## Trạng thái: spec ✅ — có thể implement ngay (chỉ cần regex + dict, không cần heavy deps).
