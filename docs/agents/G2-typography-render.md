# G2 — Typography/Render Agent

> ⚠️ **Lỗi thời:** VLM agent đã thay bằng **Codex CLI text-only** (xem [`../F1.1`](../F1.1-codex-cli-architecture.md)).
> Tiêu chí vẫn dùng, nay ở `src/ui_defect/agents/skills/20-typography.md`.

> **Nhiệm vụ:** xác nhận lỗi **render chữ ở mức pixel** — tofu, glyph thiếu, mờ,
> font fallback, RTL hỏng. Nhận output từ A8 để confirm/reject.
>
> **Tiêu chí:** TYP-01/02/04/05/09/12/13/14
>
> Quan hệ với G1: G1 lo *nội dung* text; G2 lo *render pixel* của chữ.

---

## 1. Input

```json
{
  "marked_image": "temp/marked_<id>_G2.png",
  "screen": { "platform", "locale", "dpr", "font_scale" },
  "elements": [/* role=text|button|input */],
  "text_segments": [/* từ A5: text, has_replacement, script, lang_hint, angle */],
  "glyph_issues": [/* từ A8: issue_type, confidence, verdict, evidence */],
  "candidate_issues": [/* prefix A8-*, TYP-01/02/04/05/09/12/14 */]
}
```

---

## 2. Nhiệm vụ chi tiết

### 2.1 Xác nhận A8 glyph detections

| A8 issue_type | G2 làm gì |
|---|---|
| `tofu_box` (verdict=confirmed) | Nhìn ảnh xác nhận có ô vuông □ không? Là lỗi font hay icon đặc? |
| `outline_box` | Xác nhận: thấy hộp viền mỏng (`.notdef`) hay icon outline hợp lệ? |
| `blur_jagged` | Nhìn: chữ thật sự mờ/vỡ không? Hay ảnh chất lượng thấp nói chung? |
| `emoji_square` | Xác nhận: vùng đó đáng có emoji màu nhưng hiện ô vuông đơn sắc? |
| `banding` | Xác nhận: có sọc ngang/dọc trong vùng text không? |

### 2.2 Phát hiện mới

| Tiêu chí | G2 cần làm gì |
|---|---|
| **TYP-02** Font fallback sai | Phát hiện font khác brand bất ngờ — chữ trông lạ so với phần còn lại |
| **TYP-04** Chữ đè lên chữ | 2 cụm text chồng nhau (khác với LAY-01: đây chỉ về text overlap) |
| **TYP-05** Cỡ chữ quá nhỏ | Nhìn ảnh: text có nhỏ đến mức khó đọc không? |
| **TYP-12** RTL/bidi hỏng | Text Arabic/Hebrew sai chiều; dấu câu lệch; mixed RTL-LTR xáo trộn |
| **TYP-13** Trộn font không chủ ý | Trong cùng đoạn, font thay đổi bất thường |
| **TYP-14** Emoji thành box | A8 đã detect; G2 confirm + mô tả context |

---

## 3. System Prompt G2

```
You are a typography and font-rendering expert reviewing a UI screenshot.
Your task: identify TEXT RENDERING defects at the pixel level.

Focus areas:
1. Tofu / missing glyphs: □ or ▯ boxes where a character should render
   (common with Vietnamese diacritics, CJK, special emoji on wrong font)
2. Outline boxes (.notdef): hollow rectangle outlines — font missing the glyph entirely
3. Blurry / jagged text: text rendered at wrong scale, antialiasing failure
4. Font fallback issues: text appears in a noticeably different font from the rest of the UI
5. Text overlapping text: two text elements visually colliding
6. RTL/bidi broken: Arabic/Hebrew text running left-to-right, punctuation misplaced
7. Mixed fonts: within one text block, font family changes unexpectedly
8. Emoji rendered as squares: colored emoji appearing as monochrome boxes

DO NOT check: text content/meaning (G1), colors/contrast (G3), layout spacing (G4).

Key signal: elements with has_replacement=true in text_segments are HIGH PRIORITY —
these are flagged by OCR as containing U+FFFD or □ replacement characters.
```

---

## 4. User Prompt template G2

```
Review the screenshot for text rendering defects.

Text segments from OCR (prioritize has_replacement=true):
[JSON: {segment_id, text, has_replacement, script, lang_hint, confidence}]

Glyph analysis from pixel inspector:
[JSON: glyph_issues từ A8]

Candidate issues:
[JSON: candidates từ A8 đã convert thành CandidateIssue]

Instructions:
1. For each A8 glyph issue: confirm or reject using visual evidence in the image.
2. Look for rendering defects NOT caught by A8 (especially RTL/bidi, font mixing).
3. Focus on elements with has_replacement=true — these are most likely to have tofu.
4. Report using report_ui_defects tool.
```

---

## 5. Few-shot examples

### Example 1 — Tofu box confirmed

```
[Ảnh: element e5 hiển thị "Xin chào □□□" — 3 ô vuông thay cho dấu tiếng Việt]
A8 glyph_issues: [{element_id:"e5", issue_type:"tofu_box", verdict:"confirmed", confidence:0.93}]

Expected:
{
  "findings": [{
    "issue_type": "TYP-01",
    "element_id": "e5",
    "severity": "high",
    "confidence": 0.95,
    "verdict": "confirmed",
    "original_candidate_rule": "A8-tofu",
    "evidence": {
      "element_ids": ["e5"],
      "measured_value": "3 replacement boxes at positions 9-11",
      "description": "Dấu tiếng Việt (ờ, ọ, ổ) render thành □ — font không hỗ trợ Vietnamese"
    },
    "reasoning": "Ký tự Unicode tiếng Việt không có glyph trong font đang dùng → hiển thị tofu box.",
    "severity_justification": "High — text chính không đọc được."
  }],
  "self_critique": [],
  "summary": "Tofu confirmed on e5 — Vietnamese glyphs missing from font."
}
```

### Example 2 — Blur rejected (false positive)

```
[Ảnh: element e9 có chữ nhỏ nhưng sắc nét — A8 báo blur do Laplacian thấp]
A8 glyph_issues: [{element_id:"e9", issue_type:"blur_jagged", verdict:"likely", confidence:0.6}]

Expected:
{
  "findings": [{
    "issue_type": "TYP-09",
    "element_id": "e9",
    "severity": "low",
    "confidence": 0.3,
    "verdict": "rejected",
    "original_candidate_rule": "A8-blur",
    "evidence": {
      "description": "Text appears clear in the image despite low Laplacian variance. Small font size (caption) but rendering is crisp."
    },
    "reasoning": "Text visually sharp — low Laplacian score likely due to thin strokes in small font, not actual blur.",
    "severity_justification": "Rejected — no visible rendering defect."
  }],
  "self_critique": [],
  "summary": "A8 blur candidate rejected on visual inspection."
}
```

---

## 6. Ranh giới

| Kiểm tra | G2 | G1 | G3 | G4 |
|---|---|---|---|---|
| Tofu / glyph hình học | ✅ | — | — | — |
| Text nói gì | ❌ | ✅ | — | — |
| Contrast chữ/nền | ❌ | — | ✅ | — |
| Text tràn container (hình học) | ❌ | — | — | ✅ |
| Cỡ chữ nhỏ (visual confirm) | ✅ | — | — | — |

---

## Trạng thái: spec ✅
