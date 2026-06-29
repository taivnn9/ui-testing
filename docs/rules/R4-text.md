# R4 — Text Rules (placeholder + typography tất định)

> **TL;DR:** Rule regex/pattern tất định trên `elements[].text` (A5 OCR): bắt placeholder chưa render, i18n key lòi, lorem ipsum, debug text, mojibake, escape, epoch, stack trace, text cắt cụt, cỡ chữ nhỏ. "Nội dung sai ngữ cảnh" (CNT-09/10/11) để agent reasoning Text xử lý.

> **Nguồn dữ liệu:** `elements[].text` (A5), `style.font_size`, `text_truncated` (A5).

## Danh sách rules

| Rule ID | Tiêu chí | Pattern / Điều kiện | Severity nền (range) |
|---|---|---|---|
| `R4-CNT01` | Placeholder/biến chưa render | `undefined`,`null`,`NaN`,`%s`,`{{…}}`,`${…}`,`%@` | high (medium→critical) |
| `R4-CNT02` | i18n key lòi ra | key-path `[a-z_]+\.[a-z_]+`, không space | high (medium→critical) |
| `R4-CNT04` | Lorem ipsum | dict: `lorem ipsum`, `your text here`, `placeholder text` | high (medium→high) |
| `R4-CNT05` | Debug/nội bộ | dict: `asdf`,`TODO`,`TEST`,`DO NOT SHIP`,`FIXME`,`[test]`,`dummy` | high (medium→critical) |
| `R4-CNT06` | Mojibake / HTML entity | `Ã©`,`â€™`,`&amp;`,`&#\d+;`,`&[a-z]+;` | medium (low→high) |
| `R4-CNT07` | Escape literal | `\n`,`\t`,`<br>`,`&lt;`,`&gt;` như text | medium (low→high) |
| `R4-CNT08` | Epoch / số thô | epoch 10–13 digit, ISO date sai format | medium (low→high) |
| `R4-STATE03` | Stack trace / raw error | exception/stack trace patterns | high (medium→critical) |
| `R4-TYP03` | Text cắt cụt (unintended) | `text_truncated=true` + không có "…" chủ ý | medium (trivial→critical) |
| `R4-TYP05` | Cỡ chữ quá nhỏ | `font_size_px < FONT_MIN_PX` (11px) | medium (low→high) |

---

## Chi tiết từng rule

### R4-CNT01 — Placeholder / biến chưa render
- **Fire:** role có text (text/button/input/tab/nav/container); một pattern khớp; KHÔNG fire nếu role=code/monospace.
- **Patterns:** literal `undefined/null/NaN/None` (`n/a` chỉ standalone; `N/A` hoa toàn bộ = hợp lệ); template `{{…}}`,`${…}`,`%s %d %@ %1$s`,`{0} {name}`,`__PLACEHOLDER__`,`[[var]]`; framework `@string/…`,`NSLocalizedString`,`UNTRANSLATED_…`.
- **Confidence:** `elem.conf × 0.92`
- **Modifier:** ↑ button/CTA / label chính → high–critical · ↓ input placeholder hợp lệ → medium (value thật → high)

```python
PLACEHOLDER_PATTERNS = [
    r'\bundefined\b', r'\bnull\b', r'\bNaN\b', r'\bNone\b',
    r'\{\{[^}]+\}\}', r'\$\{[^}]+\}', r'%[@sdf]|\%\d+\$[@sdf]',
    r'\{[a-zA-Z_]\w*\}', r'%s|%d|%i|%f|%@', r'__\w+__',
    r'\[\[\w+\]\]', r'@string/\w+',
]
```

### R4-CNT02 — i18n key lòi ra
- **Patterns:** dot-notation `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,4}$`; SCREAMING_SNAKE `^[A-Z][A-Z0-9_]{3,}$` (**require underscore** — `SKIP`/`DONE` thuần không phải key); underscore `^[a-z][a-z_]{3,}$` (nếu không phải English word).
- **Fire:** pattern khớp VÀ text ngắn (<40 ký tự), không space, không URL/email/code.
- **FP loại:** `sign_in` là text hợp lệ → loại theo từ điển · URL path `home/profile` (có "/") → loại.
- **Confidence:** `elem.conf × 0.75` (FP cao — agent reasoning Text confirm).

### R4-CNT04 — Lorem ipsum / placeholder copy
- **Dict (case-insensitive, partial):** `lorem ipsum`, `your text here`, `text placeholder`, `sample text`, `dummy text`, `placeholder`, `enter text`, `[placeholder]`, `[text]`…
- **Confidence:** `elem.conf × 0.95` (ít FP) · **Modifier:** ↑ text đơn độc trên màn → high

### R4-CNT05 — Debug / nội bộ
- **Dict (standalone):** `asdf`,`qwerty`,`foobar`,`foo/bar/baz`,`TODO`,`FIXME`,`HACK`,`XXX`,`TEMP`,`TEST`,`DO NOT SHIP`,`DEBUG`,`DEV ONLY`,`[test]`,`DUMMY`,`STUB`,`MOCK`,`[WIP]`…
- **Patterns:** `\btest\d+\b`, `\b(admin|password|123456)\b`.
- **Confidence:** `elem.conf × 0.85` · **Modifier:** ↑ hero area / form submit → critical

### R4-CNT06 — Mojibake / HTML entity thô
- **Patterns:** mojibake `[ÃÂ]{2,}|â€[^\s]{1,3}` (é→`Ã©`, '→`â€™`…); HTML entity `&(?:[a-z]{2,7}|#\d{1,5});`; BOM/invisible `U+FEFF/200B/200C/200D/FFFD`.
- **Fire:** trong text thật (không code block) · **Confidence:** `elem.conf × 0.9`
- **Modifier:** ↑ tiêu đề/CTA dính → high · **Tags:** i18n

### R4-CNT07 — Escape literal
- **Patterns:** `\\n|\\t|\\r`; `<br\s*/?>|<p>|</p>|<b>|</b>`; `&lt;|&gt;|&amp;`.
- **Fire:** không phải context code/monospace · **Confidence:** `elem.conf × 0.88`

### R4-CNT08 — Epoch / format số sai
- **Patterns:** UNIX ts `\b1[3-9]\d{8}\b` (s) / `\b[12]\d{12}\b` (ms); ISO `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}` (UI); số dài `\b\d{7,}\b` không phân cách.
- **Fire:** role không phải code / input type=number · **Confidence:** `elem.conf × 0.7` (nhiều FP)
- **Modifier:** ↑ giá tiền/ngày lòi thô → high

### R4-STATE03 — Stack trace / raw error
- **Patterns:** Java `at \w+\.\w+\(`; Python `Traceback \(most recent call last\)`; JS `TypeError:|ReferenceError:|SyntaxError:|Error:`; iOS `Thread \d+.*crash`; generic `Exception in thread|java\.lang\.|NullPointerException`; HTTP `\b[45]\d{2}\b` (standalone).
- **Confidence:** `elem.conf × 0.9` · **Modifier:** ↑ foreground (không phải debug panel) → critical

### R4-TYP03 — Text cắt cụt (unintended)
- **Fire:** `text_truncated=true`:
  - KHÔNG kết thúc "…"/"..."/"more" → lỗi · **conf** `elem.conf × 0.8`
  - CÓ "…" → có thể chủ ý · **conf** `elem.conf × 0.4` (agent xác nhận)
- **Modifier:** ↑ button/CTA bị cắt → high–critical · ↑ chứa số/tiền/phủ định ("không") → critical · ↓ body có ellipsis rõ → low–trivial · **Tags:** i18n

### R4-TYP05 — Cỡ chữ quá nhỏ
- **Fire:** `font_size_px < FONT_MIN_PX` (11px) → HIGH · `< FONT_WARN_PX` (13px) → MEDIUM. (device px, từ A5/A4)
- **Confidence:** `elem.conf × 0.75` · **Tags:** a11y
- **Modifier:** ↑ body chính/tên sản phẩm → high · ↓ copyright/legal nhỏ → low
- **Ghi chú:** `font_scale > 1` → tính trước scale `font_size_px / font_scale`.

---

## Tổng hợp regex module

Đóng gói trong `src/ui_defect/rules/patterns.py`: `r4_placeholder_patterns[]`, `r4_i18n_key_patterns[]`, `r4_lorem_ipsum_dict[]`, `r4_debug_dict[]`, `r4_mojibake_patterns[]`, `r4_escape_patterns[]`, `r4_epoch_patterns[]`, `r4_stacktrace_patterns[]`. Dùng `re.compile` + cache; `match_any(text, patterns) → list[match]`.

## Phân chia R4 vs agent reasoning

| Kiểm tra | R4 (regex) | Agent reasoning Text |
|---|---|---|
| Placeholder `undefined` | ✅ R4-CNT01 | xác nhận context |
| i18n key lòi | ✅ R4-CNT02 (conf thấp) | key hay từ thật |
| Lỗi chính tả | ❌ | ✅ |
| Nội dung sai ngữ cảnh | ❌ | ✅ |
| Text trùng/mâu thuẫn | ❌ | ✅ cross-element |

## Trạng thái: spec ✅ — implement ngay (chỉ regex + dict, không heavy deps).
