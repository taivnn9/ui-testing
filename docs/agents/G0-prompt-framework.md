# G0 — Prompt Framework chung

> Đây là **nền tảng kỹ thuật** cho mọi agent G1–G6. Không phải agent riêng —
> là bộ công cụ dùng chung: SoM renderer, output schema, few-shot format, call wrapper.

---

## 1. Set-of-Marks (SoM) Renderer

### 1.1 Mục đích
Vẽ **label số/chữ lên ảnh** tại bbox mỗi element → model trỏ element theo ID, không mô tả toạ độ.

### 1.2 Thiết kế visual label

```
Mỗi element → 1 label hình chữ nhật nhỏ (badge) đặt tại góc trên-trái bbox.
Badge: nền màu theo role, chữ trắng, font nhỏ (8–10px), border-radius 2px.

Màu badge theo role:
  text/button    → xanh đậm  (#1a56db)
  image          → cam       (#f05252)
  icon           → tím       (#7e3af2)
  input          → xanh lá   (#057a55)
  container/card → xám       (#6b7280)
  nav/tab        → nâu       (#92400e)
  skeleton/spinner → vàng    (#c27803)
  unknown        → đen       (#111827)

Label text: element.id  (vd "e7")
Vị trí: (bbox.x + 2, bbox.y + 2)  — góc trên-trái, không đè lên content
Kích thước badge: auto-fit text
Opacity: 0.85 (nhìn thấy nhưng không che hoàn toàn content)
```

### 1.3 Pseudo-code renderer

```python
def render_som(
    img: Image.Image,
    elements: list[Element],
    show_bbox: bool = True,
    show_label: bool = True,
) -> Image.Image:
    """Vẽ SoM lên ảnh. Trả ảnh mới (không modify original)."""
    ROLE_COLORS = {
        "text": "#1a56db", "button": "#1a56db",
        "image": "#f05252", "icon": "#7e3af2",
        "input": "#057a55", "container": "#6b7280",
        "nav": "#92400e", "tab": "#92400e",
        "skeleton": "#c27803", "spinner": "#c27803",
    }
    out = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for elem in elements:
        color = ROLE_COLORS.get(elem.role, "#111827")
        x, y, w, h = elem.bbox.x, elem.bbox.y, elem.bbox.w, elem.bbox.h
        
        if show_bbox:
            # Vẽ viền bbox
            draw.rectangle([x, y, x+w, y+h], outline=color + "cc", width=1)
        
        if show_label:
            # Badge label
            label = elem.id
            label_w, label_h = 8 * len(label) + 4, 12
            bx, by = x + 2, y + 2
            draw.rectangle([bx, by, bx+label_w, by+label_h],
                           fill=color + "d9")  # 85% opacity
            draw.text((bx+2, by+1), label, fill="white")
    
    return Image.alpha_composite(out, overlay).convert("RGB")
```

### 1.4 Lưu ý
- Với màn nhiều element (> 50): chỉ vẽ elements **liên quan** đến agent đang chạy
  (filtered subset) → tránh ảnh quá lộn xộn.
- Ảnh SoM lưu tạm tại `temp/marked_<screen_id>_<agent_id>.png`, xóa sau call.

---

## 2. Output Schema (JSON tool_use)

### 2.1 Tool definition (Anthropic API format)

```json
{
  "name": "report_ui_defects",
  "description": "Báo cáo các lỗi UI phát hiện được trong ảnh.",
  "input_schema": {
    "type": "object",
    "properties": {
      "findings": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["issue_type", "element_id", "severity", "confidence", "evidence", "reasoning"],
          "properties": {
            "issue_type": {
              "type": "string",
              "description": "Mã lỗi từ catalog: CNT-01, LAY-02, STY-01, v.v."
            },
            "element_id": {
              "type": "string",
              "description": "ID element trên ảnh SoM (vd 'e7'). Null nếu lỗi toàn màn."
            },
            "severity": {
              "type": "string",
              "enum": ["critical", "high", "medium", "low", "trivial"]
            },
            "confidence": {
              "type": "number",
              "minimum": 0,
              "maximum": 1,
              "description": "Độ chắc chắn 0–1. Thấp nếu cần thêm context."
            },
            "verdict": {
              "type": "string",
              "enum": ["confirmed", "new_finding", "rejected", "uncertain"],
              "description": "confirmed=xác nhận candidate từ Rule Engine; new_finding=phát hiện mới; rejected=bác bỏ candidate sai"
            },
            "original_candidate_rule": {
              "type": "string",
              "description": "Rule ID từ Rule Engine nếu verdict=confirmed/rejected (vd 'R1-LAY01')"
            },
            "evidence": {
              "type": "object",
              "description": "Bằng chứng cụ thể: giá trị đo, element_id liên quan, mô tả pixel.",
              "properties": {
                "element_ids": { "type": "array", "items": { "type": "string" } },
                "measured_value": { "type": "string" },
                "expected_value": { "type": "string" },
                "description": { "type": "string" }
              }
            },
            "reasoning": {
              "type": "string",
              "description": "1–2 câu: tại sao đây là lỗi (không phải thiết kế chủ ý)."
            },
            "severity_justification": {
              "type": "string",
              "description": "Tại sao chọn mức severity này (không phải mức khác)."
            }
          }
        }
      },
      "self_critique": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "issue_index": { "type": "integer" },
            "concern": { "type": "string" },
            "decision": { "type": "string", "enum": ["keep", "downgrade", "remove"] },
            "new_confidence": { "type": "number" }
          }
        },
        "description": "Self-review: issues nào có thể là false positive?"
      },
      "summary": {
        "type": "string",
        "description": "1–2 câu tóm tắt findings của agent."
      }
    },
    "required": ["findings", "self_critique", "summary"]
  }
}
```

### 2.2 Ghi chú về verdict

| verdict | Ý nghĩa |
|---|---|
| `confirmed` | Rule Engine đã fire candidate này → VLM xác nhận là lỗi thật |
| `new_finding` | VLM phát hiện thêm (Rule Engine chưa bắt được) |
| `rejected` | Rule Engine fire nhưng VLM thấy là thiết kế chủ ý → không phải lỗi |
| `uncertain` | VLM không đủ context để quyết → ghi `confidence < 0.4` |

---

## 3. System Prompt chung (template)

```
You are a senior UI/UX QA engineer reviewing a mobile/web app screenshot for visual defects.

You are given:
1. A screenshot with element IDs overlaid (Set-of-Marks format) — numbered badges at each element's top-left corner.
2. A JSON schema describing detected elements (role, bbox, text, style).
3. A list of candidate issues flagged by automated rules — you must confirm, reject, or adjust each.
4. Your specific task: check for [CRITERIA GROUP] defects only.

CRITICAL RULES:
- Always refer to elements by their ID (e.g. "e7"), never by coordinates or vague positions.
- Do NOT invent defects you cannot see in the image.
- Do NOT reject candidates without clear justification.
- Confidence < 0.5 = "uncertain but possible"; DO NOT omit uncertain findings — mark them.
- Intentional design choices are NOT defects (e.g. a decorative low-opacity element is fine).

SEVERITY GUIDE:
- critical: blocks task completion or hides essential content
- high: significantly impacts usability/readability
- medium: noticeable quality issue, doesn't block tasks
- low: minor, noticeable only on close inspection
- trivial: aesthetic only, negligible impact

[FEW-SHOT EXAMPLES — see agent-specific file]

Now review the following screen and report findings using the report_ui_defects tool.
```

---

## 4. Few-Shot Format

### 4.1 Cấu trúc một example

```
<example>
<image>[base64 hoặc path ảnh mẫu đã SoM]</image>
<elements>[JSON subset elements liên quan]</elements>
<candidates>[JSON candidate_issues từ Rule Engine]</candidates>

Expected output:
{
  "findings": [
    {
      "issue_type": "STY-01",
      "element_id": "e3",
      "severity": "high",
      "confidence": 0.92,
      "verdict": "confirmed",
      "original_candidate_rule": "R2-STY01",
      "evidence": {
        "element_ids": ["e3"],
        "measured_value": "contrast_ratio=2.8",
        "expected_value": ">= 4.5",
        "description": "Text 'Giỏ hàng' màu xám nhạt #999 trên nền trắng"
      },
      "reasoning": "Contrast ratio 2.8:1 thấp hơn WCAG AA (4.5:1) cho text thường. User khó đọc trong điều kiện ánh sáng mạnh.",
      "severity_justification": "High vì đây là label navigation chính, ảnh hưởng nhiều user."
    }
  ],
  "self_critique": [],
  "summary": "1 contrast issue confirmed trên nav label."
}
</example>
```

### 4.2 Yêu cầu few-shot cho mỗi agent

| Agent | Số example đề xuất | Loại lỗi cần cover |
|---|---|---|
| G1 Text | 2 | 1 placeholder (`undefined`), 1 i18n key lòi |
| G2 Typography | 2 | 1 tofu box, 1 text truncated |
| G3 Color | 2 | 1 low contrast, 1 invisible text |
| G4 Layout | 2 | 1 overlap, 1 off-screen |
| G5 Image | 2 | 1 distorted aspect, 1 broken image |
| G6 Component | 2 | 1 small touch target, 1 skeleton stuck |

→ **Tạo few-shot từ mutation testing** (Phase 6 GS): inject lỗi biết trước vào ảnh thật → có nhãn chính xác.

---

## 5. Call wrapper (API pattern)

```python
def call_agent(
    agent_id: str,
    marked_image: Image.Image,
    system_prompt: str,
    user_payload: dict,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1024,
) -> dict:
    """
    Gọi Claude API với vision + tool_use.
    Trả dict findings từ tool_use input.
    """
    import anthropic
    import base64
    from io import BytesIO
    
    # Encode ảnh
    buf = BytesIO()
    marked_image.save(buf, format="PNG")
    img_b64 = base64.standard_b64encode(buf.getvalue()).decode()
    
    client = anthropic.Anthropic()
    
    # Turn 1: main analysis
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        tools=[REPORT_TOOL_SCHEMA],
        tool_choice={"type": "any"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
                },
                {
                    "type": "text",
                    "text": f"Schema và candidates:\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}"
                }
            ]
        }]
    )
    
    # Extract tool_use result
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    
    return {"findings": [], "self_critique": [], "summary": "no tool use"}
```

---

## 6. Context trimming per agent

Để giảm token, mỗi agent nhận **filtered** elements và issues:

```python
AGENT_ROLE_FILTER = {
    "G1": ["text", "button", "input", "nav", "tab"],  # text-bearing elements
    "G2": ["text", "button", "input"],
    "G3": ["text", "button", "icon", "input", "toggle", "nav"],
    "G4": None,   # tất cả (layout cần toàn cảnh)
    "G5": ["image", "icon"],
    "G6": ["button", "input", "toggle", "tab", "nav", "container", "skeleton", "spinner"],
}

AGENT_ISSUE_FILTER = {
    "G1": ["CNT", "TYP-03", "TYP-06", "TYP-07", "TYP-10", "TYP-11", "R4"],
    "G2": ["TYP-01", "TYP-02", "TYP-04", "TYP-05", "TYP-09", "TYP-12", "TYP-13", "TYP-14", "A8"],
    "G3": ["STY", "R2"],
    "G4": ["LAY", "ENV-04", "ENV-05", "ENV-06", "R1-LAY"],
    "G5": ["IMG", "R3"],
    "G6": ["CMP", "STATE", "ENV-01", "ENV-02", "ENV-03", "R1-CMP", "R1-ENV", "A9"],
}
```

---

## 7. Prompt caching (Anthropic API)

System prompt + few-shot examples dài → **cache với `cache_control: ephemeral`** để tiết kiệm chi phí khi gọi nhiều ảnh liên tiếp:

```python
# System prompt và few-shot: đặt cache_control trên block cuối của static content
messages=[{
    "role": "user",
    "content": [
        {"type": "text", "text": FEW_SHOT_EXAMPLES, "cache_control": {"type": "ephemeral"}},
        {"type": "image", ...},  # dynamic — không cache
        {"type": "text", "text": dynamic_payload}
    ]
}]
```

→ Static: system + few-shot (~1500 token) → cache hit sau lần đầu.
→ Dynamic: ảnh + schema mỗi call (~800 token).

---

## Trạng thái: spec ✅ — cần implement SoM renderer và call wrapper khi bắt đầu code Phase 3.
