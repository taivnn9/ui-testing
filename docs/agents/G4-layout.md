# G4 — Layout Agent

> ⚠️ **Lỗi thời:** VLM agent đã thay bằng **Codex CLI text-only** (xem [`../F1.1`](../F1.1-codex-cli-architecture.md)).
> Tiêu chí vẫn dùng, nay ở `src/ui_defect/agents/skills/40-layout.md`.

> **Nhiệm vụ:** xác nhận và phát hiện lỗi **hình học không gian** — overlap,
> off-screen, overflow, spacing, z-order, responsive.
>
> **Tiêu chí:** LAY-01–15, ENV-04/05/06/08/09
>
> G4 nhận **toàn bộ elements** (không trim) vì layout cần toàn cảnh.
> R1 đã tính hầu hết — G4 xác nhận và phát hiện lỗi cần ngữ cảnh visual.

---

## 1. Input

```json
{
  "marked_image": "temp/marked_<id>_G4.png",
  "screen": { "platform", "viewport", "safe_area", "orientation" },
  "elements": [/* tất cả elements */],
  "relations": [/* relations[] đã tiền tính bởi A0 */],
  "candidate_issues": [/* prefix R1-LAY*, R1-ENV* */]
}
```

---

## 2. Nhiệm vụ chi tiết

### 2.1 Xác nhận / bác bỏ R1 candidates

| Candidate | G4 làm gì |
|---|---|
| R1-LAY01 (overlap) | Xác nhận: đây là overlap lỗi hay badge-trên-icon có chủ ý? |
| R1-LAY02 (off-screen) | Xác nhận: element thật sự bị cắt? Hay là scroll container hợp lệ? |
| R1-LAY03 (overflow container) | Xác nhận: tràn lỗi hay thiết kế bleed/overflow scroll? |
| R1-LAY06 (z-order) | Xác nhận: element quan trọng có bị che không? |
| R1-CMP01 (touch target nhỏ) | Xác nhận: nút thật sự nhỏ không? Hay bbox A3 sai? |
| R1-ENV01/02/03 (safe-area) | Xác nhận: nội dung bị notch/status bar che không? |

### 2.2 Phát hiện mới

| Tiêu chí | G4 cần phán đoán |
|---|---|
| **LAY-09** Reflow/wrap vỡ (responsive) | Cột sập, text wrap xấu rõ ràng trong layout |
| **LAY-10** Scroll lỗi | Double scrollbar, scroll ngang không chủ ý (từ overflow) |
| **LAY-11** Sticky/fixed đè nội dung | Header/footer dính che khuất content phía sau |
| **LAY-13** Vùng trống bất thường | Khoảng trống lớn giữa màn không có lý do rõ ràng |
| **LAY-15** Thứ tự sắp xếp sai | Danh sách lộn xộn, thứ tự ngược logic |
| **ENV-04** Bàn phím che input | Keyboard overlay cắt mất ô input / nút submit |
| **ENV-05** Landscape vỡ layout | Khi xoay màn, layout không adapt |
| **ENV-06** Font-scale lớn làm vỡ | Text size trợ năng > 1.3 → overflow |

---

## 3. System Prompt G4

```
You are a layout and spatial geometry expert reviewing a UI screenshot.
Your task: identify LAYOUT and SPATIAL POSITIONING defects.

Focus areas:
1. Overlapping elements: elements that visually collide (not intentional like badge-on-icon)
2. Off-screen content: elements cut off at viewport edges
3. Container overflow: content extending beyond its parent container
4. Touch target sizing: interactive elements too small to tap reliably
5. Z-order issues: important content hidden behind other elements
6. Spacing problems: abnormally large gaps, inconsistent padding
7. Alignment issues: elements visually misaligned from their group
8. Safe area violations: content overlapping notch, status bar, or home indicator area
9. Responsive breakage: columns collapsed, text wrapping badly, unexpected horizontal scroll
10. Sticky element coverage: fixed header/footer obscuring content

Key: layout defects are geometric — describe them spatially using element IDs.
The marked image shows all element bounding boxes — use these to assess positioning.

Platform: [PLATFORM] | Viewport: [W]×[H] | Safe area: top=[TOP] bottom=[BOTTOM]
```

---

## 4. User Prompt G4

```
Review the screenshot for layout and spacing defects.

Elements summary:
[JSON: {id, role, bbox, parent, z, visible, interactive}]

Pre-computed relations (close pairs):
[JSON: relations[] from A0]

Candidate issues from geometry rules:
[JSON: R1-LAY*, R1-CMP*, R1-ENV* candidates]

Instructions:
1. Confirm/reject each candidate — visual confirmation is your primary tool.
2. Spatial issues to confirm: overlap, off-screen, overflow, touch target, safe-area.
3. Look for layout defects not caught by rules (especially responsive breakage, sticky issues, abnormal whitespace).
4. For overlaps: distinguish intentional (badge, modal, tooltip, dropdown) from accidental.
5. Report using report_ui_defects tool with specific element IDs.
```

---

## 5. Few-shot examples

### Example 1 — Overlap confirmed (accidental)

```
[Ảnh: e4 (text "Số điện thoại") chồng lên e3 (input field), rõ ràng không phải label-on-input]
Candidate: R1-LAY01, element=e4, iou=0.12

Expected:
{
  "findings": [{
    "issue_type": "LAY-01",
    "element_id": "e4",
    "severity": "high",
    "confidence": 0.88,
    "verdict": "confirmed",
    "original_candidate_rule": "R1-LAY01",
    "evidence": {
      "element_ids": ["e3", "e4"],
      "measured_value": "IoU=0.12",
      "description": "Label 'Số điện thoại' (e4) overlaps với input field (e3) — không phải label-inside-input design"
    },
    "reasoning": "Label nằm đè lên input field phía dưới, che mất khoảng nhập liệu.",
    "severity_justification": "High — cản trở thao tác nhập liệu."
  }]
}
```

### Example 2 — Off-screen bác bỏ (scroll container hợp lệ)

```
[Ảnh: horizontal scroll list, các item nằm ngoài viewport phải là bình thường]
Candidate: R1-LAY02, element=e17 (item trong list ngang)

Expected:
{
  "findings": [{
    "issue_type": "LAY-02",
    "element_id": "e17",
    "severity": "low",
    "confidence": 0.2,
    "verdict": "rejected",
    "original_candidate_rule": "R1-LAY02",
    "evidence": {
      "description": "e17 là item trong horizontal scroll list — nằm ngoài viewport là intentional design"
    },
    "reasoning": "Context cho thấy đây là horizontal scroll — items bên phải ngoài viewport là hành vi đúng.",
    "severity_justification": "Rejected."
  }]
}
```

---

## 6. Hướng dẫn phân biệt intentional vs bug

| Pattern | Intentional | Bug |
|---|---|---|
| Overlap | Badge số trên icon avatar, tooltip hover, modal đè content | 2 element content chồng nhau không có z-order rõ |
| Off-screen | Carousel/horizontal scroll | Nút/text bị cắt ở mép màn |
| Overflow | Parallax background vượt mép | Text/button tràn ra ngoài card |
| Small touch target | Paginator dots nhỏ (bình thường) | CTA button quá nhỏ |
| Large gap | Hero section intentional whitespace | Khoảng trống giữa 2 phần sau khi xóa element |

---

## 7. Ranh giới

| Kiểm tra | G4 | G6 |
|---|---|---|
| Bàn phím che input (visual) | ✅ ENV-04 | ✅ CMP-07 (focus/state) |
| Touch target size | ✅ LAY confirm | ✅ CMP-01 (chi tiết component) |
| Container overflow | ✅ LAY-03 | — |
| Modal đè sai (z-order) | ✅ LAY-06 | ✅ STATE-07 (state kẹt) |

→ G4 và G6 share một số tiêu chí — aggregate sau sẽ dedupe.

## Trạng thái: spec ✅
