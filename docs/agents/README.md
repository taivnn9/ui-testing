# Phase 3 — Judgment Agents (VLM)

> **Mục đích:** nhận ảnh + schema + `candidate_issues[]` từ Rule Engine → VLM
> **xác nhận/bác bỏ** candidate + **phát hiện thêm** lỗi cần thẩm mỹ/ngữ cảnh.
>
> Model đề xuất: **Claude claude-sonnet-4-6** (vision + tool_use + structured output).
> Tất cả agent gọi qua Anthropic API (hoặc self-host VLM compatible API).

---

## Nguyên tắc thiết kế (BẮT BUỘC áp cho mọi agent)

### 1. Set-of-Marks (SoM) — vẽ ID lên ảnh
Trước khi gọi VLM, **render ID số lên ảnh** tại vị trí bbox của mỗi element.
Model trỏ element theo `element_id` (vd `e7`) — **không đoán toạ độ, không mô tả vị trí mơ hồ**.
→ Chi tiết kỹ thuật: [`G0-prompt-framework.md`](G0-prompt-framework.md#set-of-marks-renderer)

### 2. Structured output bắt buộc
Mọi agent đều dùng **tool_use / JSON schema** để nhận response có cấu trúc.
Không dùng free-form text → không parse lại, không mất dữ liệu.
→ Schema output: [`G0-prompt-framework.md`](G0-prompt-framework.md#output-schema)

### 3. Decompose theo nhóm tiêu chí
Mỗi agent phụ trách **1 nhóm** criteria — không gọi 1 agent "tìm hết lỗi".
Lý do: attention dilution → mỗi lần call có focus rõ hơn → precision cao hơn.
→ 6 agent nhóm + 1 framework: G0/G1/G2/G3/G4/G5/G6.

### 4. Few-shot calibration
Mỗi agent có **2–3 few-shot example** trong system prompt: ảnh có lỗi đã biết →
expected JSON output → calibrate severity.
→ Format: [`G0-prompt-framework.md`](G0-prompt-framework.md#few-shot-format)

### 5. Self-critique pass
Cuối mỗi agent call, **1 turn thêm** yêu cầu model review lại findings của chính nó:
*"Review your findings. For each issue, justify why it's a real defect vs. intentional design."*
→ Issues nào model tự hủy → không đưa vào output.

### 6. Precision-first
- Mỗi issue phải có `evidence` cụ thể (element_id, giá trị đo, crop).
- Nếu không chắc → ghi `confidence < 0.5`, không drop issue (để V1 lọc sau).
- Rule: **không bịa, không đoán toạ độ** — chỉ dùng element_id SoM.

---

## Danh sách agents

| File | Agent | Tiêu chí | Input chính |
|---|---|---|---|
| [`G0-prompt-framework.md`](G0-prompt-framework.md) | Prompt Framework | — | SoM renderer, output schema, few-shot |
| [`G1-text-content.md`](G1-text-content.md) | Text/Content | CNT-01–14, TYP-03/06–08/10/11 | A5 text, R4 candidates |
| [`G2-typography-render.md`](G2-typography-render.md) | Typography/Render | TYP-01/02/04/05/09/12/13/14 | A8 glyph issues, A5 segments |
| [`G3-color-style.md`](G3-color-style.md) | Color/Style | STY-01–13 | A4 color results, R2 candidates |
| [`G4-layout.md`](G4-layout.md) | Layout | LAY-01–15, ENV-04–13 | R1 candidates, relations[] |
| [`G5-image.md`](G5-image.md) | Image/Icon | IMG-01–15 | A6/A7/A10 results, R3 candidates |
| [`G6-component-state.md`](G6-component-state.md) | Component+State | CMP-01–17, STATE-01–11, ENV-01–03 | A9 patterns, R1 candidates |

---

## Thứ tự chạy

```
G0 (SoM render) → chạy trước mọi agent (1 lần cho mỗi ảnh)

Parallel (độc lập nhau):
  G1 Text/Content
  G2 Typography/Render
  G3 Color/Style  
  G4 Layout
  G5 Image
  G6 Component+State

→ Aggregate tất cả findings
→ V1 Critic self-critique tổng
→ S1 Summary + dedupe + severity cuối
```

Có thể chạy G1–G6 song song (n8n parallel nodes) vì độc lập nhau.

---

## Input package cho mỗi agent

Mỗi agent nhận:
```json
{
  "marked_image": "path/to/marked_image.png",  // SoM đã vẽ
  "screen": { "platform", "viewport", "theme", "locale" },
  "elements": [/* chỉ elements liên quan đến nhóm criteria */],
  "candidate_issues": [/* chỉ candidates thuộc nhóm criteria */],
  "text_segments": [/* từ A5 — G1/G2 dùng */],
  "pixel_results": [/* từ A4 — G3 dùng */]
}
```

**Context trimming:** mỗi agent chỉ nhận subset elements/issues liên quan → giảm token.

---

## Open decisions

- [ ] **Model**: Claude claude-sonnet-4-6 hay dùng hosted VLM self-serve? Đề xuất: Claude API trước (có vision + tool_use tốt), self-host sau khi validate pipeline.
- [ ] **Few-shot images**: lưu ở đâu? Đề xuất: `data/few_shot/<agent_id>/` — anh cần tạo ~3 ảnh mẫu/agent có lỗi đã biết.
- [ ] **Parallel hay sequential?** Đề xuất: parallel (n8n parallel execution) — tiết kiệm latency.
- [ ] **Token budget per agent**: ước tính ~2000 token prompt + ~500 response cho ảnh 390×844. Cần benchmark thực tế.
