# G3 — Color/Style Agent

> ⚠️ **Lỗi thời:** VLM agent đã thay bằng **Codex CLI text-only** (xem [`../F1.1`](../F1.1-codex-cli-architecture.md)).
> Tiêu chí vẫn dùng, nay ở `src/ui_defect/agents/skills/30-color-style.md`.

> **Nhiệm vụ:** xác nhận và phát hiện lỗi **màu sắc, tương phản, visual style**.
>
> **Tiêu chí:** STY-01–13
>
> Nguồn định lượng: A4 Pixel Color Sampler (contrast_ratio_px, dark_mode_ok, opacity_px).
> G3 **xác nhận ngữ cảnh** phán đoán thêm những gì A4+R2 không tính được.

---

## 1. Input

```json
{
  "marked_image": "temp/marked_<id>_G3.png",
  "screen": { "theme", "platform", "locale" },
  "elements": [/* role=text|button|icon|input|toggle|nav */],
  "pixel_color_results": [/* từ A4: color_px, bg_color_px, contrast_ratio_px, dark_mode_ok, opacity_px, dominant_colors */],
  "candidate_issues": [/* prefix R2-STY*, STY-* */]
}
```

---

## 2. Nhiệm vụ chi tiết

### 2.1 Xác nhận / bác bỏ R2 candidates

| Candidate | G3 làm gì |
|---|---|
| R2-STY01 (contrast thấp) | Xác nhận: nhìn ảnh thấy chữ khó đọc không? Nền có phức tạp không? |
| R2-STY02 (invisible text) | Thường confirm; reject nếu là watermark/background decor |
| R2-STY03 (dark-mode hardcode) | Xác nhận: trong màn dark, element có rõ ràng dùng màu sáng cứng không? |
| R2-STY04 (icon tàng hình dark) | Xác nhận: icon có nhìn thấy không trong theme hiện tại? |
| R2-STY05 (opacity thấp) | Xác nhận: element trông mờ bất thường không? Hay là chủ ý (disabled/hint)? |
| R2-STY13 (icon contrast < 3:1) | Xác nhận: icon chức năng có nhìn thấy rõ không? |

### 2.2 Phát hiện mới (A4+R2 không bắt được)

| Tiêu chí | G3 cần phán đoán |
|---|---|
| **STY-06** Lệch bảng màu / sai màu brand | Màu trông lạ so với style guide (confident khi rõ ràng sai) |
| **STY-07** Disabled không phân biệt enabled | 2 state trông giống nhau — disabled không mờ đi |
| **STY-08** Focus/selected không rõ | Tab/radio/checkbox đang chọn — có highlight rõ không? |
| **STY-09** Màu là thông tin duy nhất | Error state chỉ đổi màu đỏ, không có icon/text — color-only |
| **STY-10** Gradient/shadow lỗi | Banding, viền cứng trong gradient, bóng đổ lệch |
| **STY-11** Viền/divider thiếu/thừa/nhân đôi | Thấy 2 đường kẻ sát nhau, hoặc thiếu separator rõ ràng |
| **STY-12** Nền sai vùng | Vùng đáng trong suốt lại nền đặc (nền thừa) |

---

## 3. System Prompt G3

```
You are a color and visual style expert reviewing a UI screenshot.
Your task: identify COLOR, CONTRAST, and VISUAL STYLE defects.

Focus areas:
1. Contrast issues:
   - Text/background contrast below WCAG AA (4.5:1 normal text, 3:1 large text)
   - Invisible text (same or nearly same color as background)
   - Icon/graphic contrast below 3:1
   
2. Dark mode issues (if theme=dark):
   - Elements with hardcoded light colors that don't adapt to dark mode
   - Icons/text invisible in dark theme
   
3. Opacity and visibility:
   - Elements unexpectedly transparent or nearly invisible
   - Disabled vs enabled states indistinguishable
   - Focus/selected states not visually distinct
   
4. Color-only information:
   - Error/warning states conveyed only by color change (no icon or text change)
   
5. Style inconsistencies:
   - Gradients with visible banding or hard edges
   - Duplicate or missing dividers/borders
   - Unexpected solid backgrounds where transparency expected

Pixel contrast measurements are provided — use them as ground truth for numbers,
but use your visual judgment to determine context (decorative vs functional, intentional design).

Theme: [THEME] | Platform: [PLATFORM]
```

---

## 4. User Prompt G3

```
Review for color and visual style defects.

Color measurements per element (from pixel analysis):
[JSON: {element_id, role, contrast_ratio_px, color_px, bg_color_px, opacity_px, dark_mode_ok, dominant_colors, bg_is_solid_px}]

Candidate issues from automated rules:
[JSON: R2-STY* candidates]

Instructions:
1. Confirm/reject each contrast candidate — use the measurements but verify visually.
2. For elements with bg_is_solid_px=false: note that contrast measurement may be unreliable.
3. Look for style issues NOT in candidates (STY-06 through STY-13).
4. For dark theme: focus on elements where dark_mode_ok=false.
5. Remember: low contrast on decorative elements is not a defect.
```

---

## 5. Few-shot examples

### Example 1 — Contrast confirmed

```
[Ảnh: e3 label "Giỏ hàng" xám nhạt #aaa trên nền trắng]
Pixel: contrast_ratio_px=2.3, bg_is_solid_px=true
Candidate: R2-STY01, element=e3

Expected:
{
  "findings": [{
    "issue_type": "STY-01",
    "element_id": "e3",
    "severity": "high",
    "confidence": 0.93,
    "verdict": "confirmed",
    "original_candidate_rule": "R2-STY01",
    "evidence": {
      "measured_value": "contrast_ratio=2.3:1",
      "expected_value": ">= 4.5:1 (WCAG AA)",
      "description": "Navigation tab label với contrast thấp"
    },
    "reasoning": "2.3:1 thấp hơn WCAG AA 4.5:1 và đây là nav label chức năng, không phải decor.",
    "severity_justification": "High — nav label ảnh hưởng toàn flow navigation."
  }]
}
```

### Example 2 — STY-07 phát hiện mới (disabled không phân biệt)

```
[Ảnh: 2 nút e5 (enabled) và e6 (disabled) trông giống hệt nhau về màu]
Pixel: e5.opacity_px=1.0, e6.opacity_px=0.95 (gần như bằng nhau)
Candidates: []

Expected:
{
  "findings": [{
    "issue_type": "STY-07",
    "element_id": "e6",
    "severity": "medium",
    "confidence": 0.75,
    "verdict": "new_finding",
    "evidence": {
      "element_ids": ["e5", "e6"],
      "description": "Button e6 (disabled) và e5 (enabled) trông gần như giống hệt — opacity khác biệt không đủ"
    },
    "reasoning": "Disabled state phải rõ ràng phân biệt (thường opacity < 0.5 hoặc màu khác). Tương đồng cao gây nhầm lẫn.",
    "severity_justification": "Medium — user có thể tap nhầm disabled button."
  }]
}
```

---

## 6. Ranh giới

| Kiểm tra | G3 | G2 | G4 |
|---|---|---|---|
| Contrast text/nền | ✅ | — | — |
| Màu brand lệch | ✅ (medium conf) | — | — |
| Blur/glyph render | ❌ | ✅ | — |
| Padding/spacing | ❌ | — | ✅ |

---

## 7. Calibration notes

- **STY-06 (brand color):** confidence tối đa 0.6 khi không có spec chuẩn → VLM xét định tính.
- **STY-09 (color-only):** chỉ fire khi thấy state change rõ ràng nhưng không có non-color indicator.
- **bg_is_solid_px=false:** hạ confidence xuống 0.5 cho mọi contrast issue trên nền phức tạp.

## Trạng thái: spec ✅
