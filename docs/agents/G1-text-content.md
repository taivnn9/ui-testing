# G1 — Text/Content Agent

> **Nhiệm vụ:** phát hiện và xác nhận lỗi **nội dung text** — những gì chữ *nói gì*
> và text *trông thế nào ở mức bố cục*.
>
> **Tiêu chí phụ trách:** CNT-01–14, TYP-03/06/07/10/11
>
> **Khó nhất với zero-reference:** CNT-09/10/11/13 cần ngữ cảnh màn — VLM làm tốt
> hơn rule (không có design spec để so).

---

## 1. Input

```json
{
  "marked_image": "temp/marked_<id>_G1.png",
  "screen": { "platform", "locale", "font_scale", "theme" },
  "elements": [/* role=text|button|input|nav|tab|container có text */],
  "text_segments": [/* từ A5 — có text, confidence, script, lang_hint, has_replacement */],
  "candidate_issues": [/* prefix R4-CNT*, R4-TYP03, R4-TYP05 */]
}
```

**Elements nhận:** chỉ elements có `text != null`.
**Context trimming:** bỏ elements không có text (image, icon thuần).

---

## 2. Nhiệm vụ chi tiết

### 2.1 Xác nhận / bác bỏ candidates từ R4

| Candidate từ R4 | G1 làm gì |
|---|---|
| R4-CNT01 (`undefined`, `%s`, `{{var}}`) | Xác nhận: nhìn ảnh thấy text đó không? context hợp lệ không? |
| R4-CNT02 (i18n key lòi) | **Cần xác nhận nhiều nhất**: `home.title` có thể là tên hợp lệ → VLM phán |
| R4-CNT04 (lorem ipsum) | Thường confirm; reject nếu là tên thật tình cờ giống |
| R4-CNT05 (debug text) | Xác nhận context — `TODO` trong label thật khác `TODO` trong debug |
| R4-CNT06 (mojibake) | Xác nhận trực quan — nhìn thấy ký tự vỡ không? |
| R4-CNT07 (escape literal) | Xác nhận `\n` thật sự lòi ra ảnh không |
| R4-CNT08 (epoch thô) | Xác nhận số dài có đang hiển thị như timestamp không |
| R4-TYP03 (text bị cắt) | Xác nhận cắt là lỗi hay chủ ý (ellipsis design) |

### 2.2 Phát hiện mới (R4 không bắt được)

| Tiêu chí | G1 cần làm gì |
|---|---|
| **CNT-03** Sai/lẫn ngôn ngữ | Screen locale=vi nhưng thấy text Anh → phát hiện; kết hợp `lang_hint` từ A5 |
| **CNT-08** Số sai format locale | "1234567" không có dấu phân cách → số tài chính? Epoch? |
| **CNT-09** Lỗi chính tả | Visible text — VLM nhận ra rõ ràng (typo, sai dấu) |
| **CNT-10** Nội dung sai ngữ cảnh | "Thêm vào giỏ" trên màn login → sai intent (confidence thấp) |
| **CNT-11** Text trùng lặp / mâu thuẫn | Cùng giá hiển thị 2 con số khác nhau |
| **CNT-12** Đơn vị / ký hiệu thiếu | Giá không có ký hiệu tiền tệ |
| **CNT-13** Giá trị vô lý | "0 sản phẩm" nhưng có item trong list |
| **TYP-06** Ngắt dòng xấu | Từ bị ngắt giữa, orphan word 1 chữ cuối dòng |
| **TYP-07** Line-height sai | Dòng dính nhau hoặc cách quá xa bất thường |
| **TYP-10** Căn lề text sai | Justify tạo river of whitespace rõ ràng |
| **TYP-11** Casing sai | ALL CAPS nơi không phải style intentional |

---

## 3. System Prompt G1

```
You are a senior UI/UX QA engineer. Your task: review TEXT CONTENT and TEXT LAYOUT defects only.

Focus areas:
A. Content errors (what the text says):
   - Unrendered variables: {{var}}, ${x}, undefined, null, NaN, %s, %@
   - Untranslated i18n keys: home.title, btn_submit (dot-notation keys not real words)
   - Wrong language: screen locale is [LOCALE] — flag text in a different language
   - Lorem ipsum, placeholder copy, debug text (TODO, asdf, TEST)
   - Mojibake: garbled characters like "Ã©" instead of "é"
   - Escaped HTML/text: literal "\n", "<br>", "&amp;" appearing as text
   - Unreasonable values: "0 items" but list shows items; prices missing currency symbols
   - Logical contradictions: same price shown differently in 2 places

B. Text layout issues:
   - Truncated text without ellipsis (cut mid-word or mid-sentence — NOT intentional "...")
   - Bad line breaks: single orphan word, hyphenation mid-word
   - Wrong text alignment: justify creating large whitespace rivers
   - Inappropriate ALL CAPS on body text (not intentional design)

DO NOT check: colors, contrast, spacing/layout geometry, image quality — those are handled by other agents.

Screen locale: [LOCALE]
Platform: [PLATFORM]
```

---

## 4. User Prompt template G1

```
Review the screenshot for text content and layout defects.

Elements with text (by ID shown in image):
[JSON list: {id, role, text, confidence, lang_hint}]

Candidate issues from automated rules:
[JSON list: candidate_issues filtered for CNT/TYP]

Instructions:
1. For each candidate issue: confirm (verdict="confirmed"), reject (verdict="rejected"), or mark uncertain.
2. Look for additional text defects NOT in the candidate list (verdict="new_finding").
3. For locale mismatch: screen is [LOCALE] — flag any text that appears to be in a different language.
4. Report using the report_ui_defects tool. Be specific about element IDs from the image.
```

---

## 5. Few-shot examples

### Example 1 — Placeholder biến chưa render

```
[Ảnh: màn hình có element e3 hiển thị text "Xin chào, {{user.name}}!"]
Candidates: [{rule:"R4-CNT01", element:"e3", detail:"found {{user.name}}"}]

Expected output:
{
  "findings": [{
    "issue_type": "CNT-01",
    "element_id": "e3",
    "severity": "high",
    "confidence": 0.97,
    "verdict": "confirmed",
    "original_candidate_rule": "R4-CNT01",
    "evidence": {
      "element_ids": ["e3"],
      "measured_value": "text='Xin chào, {{user.name}}!'",
      "description": "Template variable {{user.name}} chưa được interpolate — tên user không hiển thị"
    },
    "reasoning": "{{user.name}} là template syntax chưa render, user thấy text thô.",
    "severity_justification": "High — ảnh hưởng trải nghiệm cá nhân hoá, không phải critical vì màn vẫn dùng được."
  }],
  "self_critique": [],
  "summary": "1 unrendered variable confirmed."
}
```

### Example 2 — Phát hiện mới: sai ngôn ngữ

```
[Ảnh: màn hình app Việt, element e11 có text "Add to Cart" (tiếng Anh)]
Candidates: []  (R4 không bắt được — không có regex sai ngôn ngữ)
screen.locale: "vi-VN"

Expected output:
{
  "findings": [{
    "issue_type": "CNT-03",
    "element_id": "e11",
    "severity": "medium",
    "confidence": 0.85,
    "verdict": "new_finding",
    "evidence": {
      "element_ids": ["e11"],
      "measured_value": "text='Add to Cart', lang_hint='en'",
      "expected_value": "Vietnamese text for locale vi-VN",
      "description": "Nút 'Add to Cart' chưa dịch sang tiếng Việt trong app locale vi-VN"
    },
    "reasoning": "Screen locale là vi-VN nhưng button text là tiếng Anh — bỏ sót dịch.",
    "severity_justification": "Medium — có thể đọc hiểu được nhưng không nhất quán với locale."
  }],
  "self_critique": [{
    "issue_index": 0,
    "concern": "App có thể intentionally dùng tiếng Anh cho thuật ngữ kỹ thuật/ecommerce.",
    "decision": "keep",
    "new_confidence": 0.75
  }],
  "summary": "1 untranslated text found, confidence adjusted for possible intentional design."
}
```

---

## 6. Ranh giới với agent khác

| Kiểm tra | G1 làm | Agent khác |
|---|---|---|
| Text nói gì (nội dung) | ✅ | — |
| Text bị cắt cụt (cắt thấy trong ảnh) | ✅ | — |
| Tofu □ / glyph thiếu (render pixel) | ❌ | **G2** |
| Contrast text/nền | ❌ | **G3** |
| Text overflow container (hình học) | ❌ | **G4** |
| Căn lề text sai (chỉ visual, không phải nội dung) | ✅ TYP-10 | — |

---

## 7. Calibration notes

**CNT-10/13 (nội dung sai ngữ cảnh):**
- Luôn ghi `confidence < 0.6` vì không có design spec để so.
- Ghi `verdict="uncertain"` nếu G1 không chắc intent màn.

**CNT-02 (i18n key):**
- R4 đã flag với confidence 0.75 — G1 nhìn ảnh để quyết.
- Nếu text trông tự nhiên (vd "sign.in" nhìn như "sign in") → `verdict="rejected"`.
- Nếu text rõ là key (`auth.login.title.v2`) → `verdict="confirmed"`.

**CNT-11 (mâu thuẫn):**
- Cần 2 element cùng hiển thị giá trị cho cùng 1 thứ → compare.
- Confidence thấp nếu không chắc 2 số là cho cùng đối tượng.

---

## Trạng thái: spec ✅
