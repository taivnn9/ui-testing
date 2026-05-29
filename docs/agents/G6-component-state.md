# G6 — Component + State Agent

> **Nhiệm vụ:** xác nhận lỗi **UI component cụ thể** và **trạng thái màn hình**
> (loading, empty, error state) + safe-area platform.
>
> **Tiêu chí:** CMP-01–17, STATE-01–11, ENV-01–03/13
>
> Đặc thù: nhiều STATE/CMP tiêu chí cần ngữ cảnh flow → confidence thấp hơn;
> A9 Pixel Pattern Detector đã detect pattern, G6 xác nhận + thêm severity context.

---

## 1. Input

```json
{
  "marked_image": "temp/marked_<id>_G6.png",
  "screen": { "platform", "viewport", "safe_area", "notch_type" },
  "elements": [/* role=button|input|toggle|tab|nav|container|skeleton|spinner */],
  "pattern_detections": [/* từ A9: skeleton|spinner|overlay|keyboard|blank|broken_image */],
  "candidate_issues": [/* prefix R1-CMP*, R1-ENV*, A9-* */]
}
```

---

## 2. Nhiệm vụ chi tiết

### 2.1 Xác nhận / bác bỏ candidates

| Candidate | G6 làm gì |
|---|---|
| R1-CMP01 (touch target nhỏ) | Xác nhận: nút thật nhỏ không? Có phải A3 crop sai không? |
| R1-CMP16 (tap gap chồng) | Xác nhận: 2 element tương tác quá sát → dễ tap nhầm |
| R1-ENV01 (safe-area) | Xác nhận: nội dung bị notch/DI che thật sự? |
| A9-skeleton | Xác nhận: có skeleton loader trên màn không? |
| A9-spinner | Xác nhận: có loading spinner không? |
| A9-overlay | Xác nhận: có loading overlay che toàn màn không? |
| A9-blank | Xác nhận: màn trống — là empty state lỗi hay loading hợp lệ? |
| A9-broken_image | Xác nhận (xem G5 cũng làm) |

### 2.2 Phát hiện mới

| Tiêu chí | G6 cần phán đoán |
|---|---|
| **CMP-02** Nút icon-only không nhãn | Icon button không có text label/tooltip visible |
| **CMP-04** Control sai state | Toggle ON nhưng nhìn như OFF; checkbox trung gian sai |
| **CMP-05** Trùng component | 2 nút giống hệt (cùng icon/text) trên cùng màn |
| **CMP-06** Thiếu component kỳ vọng | Form không có submit; flow không có back |
| **CMP-07** Input không rõ focus/label | Input không có placeholder; label đè value |
| **CMP-08** Text nút bị cắt | Button label bị truncate |
| **CMP-11** Dropdown lòi ra ngoài màn | Menu/popover clip mép viewport |
| **CMP-13** Badge vị trí sai / tràn | Badge "99+" ở vị trí lạ hoặc tràn ra ngoài icon |
| **CMP-14** Tab/segment không rõ selected | Active tab không phân biệt được |
| **STATE-02** Empty state thiếu message | List/section trống không có "Không có dữ liệu" |
| **STATE-03** Error state raw | Màn lỗi hiển thị stack trace / mã lỗi thô |
| **STATE-04** Render dở dang | 1 phần loaded, 1 phần chưa rõ ràng |
| **STATE-06** Spinner/overlay không tắt | Overlay đè lên màn có nội dung sẵn |
| **STATE-07** Modal/toast kẹt | Toast/snackbar còn đó dù có thể dismiss |
| **ENV-13** Splash screen kẹt | Logo/loading screen trong màn đang active |

---

## 3. System Prompt G6

```
You are a UI components and app state expert reviewing a mobile/web screenshot.
Your task: identify COMPONENT and APP STATE defects.

Focus areas:
A. UI Component defects:
   1. Touch targets: buttons/toggles too small to tap reliably (< 44pt iOS / 48dp Android)
   2. Missing labels: icon-only buttons with no visible text or accessible label
   3. Wrong component state: toggle appears ON but should be OFF, checkbox indeterminate state
   4. Duplicate components: same button/control appearing twice unintentionally
   5. Missing expected components: form with no submit button, navigation with no back
   6. Input fields: missing label, placeholder overlapping entered value
   7. Truncated button labels: text cut off in buttons
   8. Badge issues: notification count mispositioned or overflowing
   9. Tab/segment control: active/selected state not visually distinct

B. App state defects:
   1. Skeleton loaders: visible skeleton UI (shimmer bars/boxes) — note: "stuck" needs 2+ frames
   2. Loading spinners: spinning indicators visible
   3. Loading overlay: semi-transparent overlay covering content
   4. Empty states: blank sections with no empty-state message
   5. Raw errors: stack traces, error codes, "Error 500" visible to users
   6. Partial render: half-loaded content mixed with loading state
   7. Stuck overlays: loading UI covering already-loaded content
   8. Stuck modals/toasts: dismissible UI elements that appear stuck

C. Platform environment:
   1. Safe area violations: content hidden under notch/Dynamic Island/status bar
   2. Home indicator overlap: buttons/content overlapping iOS home bar
   3. Stuck splash: app launch screen visible during active use

For "stuck" states (skeleton, spinner): mark temporal=true — single frame cannot confirm "stuck".
Platform: [PLATFORM] | Notch: [NOTCH_TYPE]
```

---

## 4. User Prompt G6

```
Review for component and app state defects.

Interactive elements:
[JSON: {id, role, bbox, text, interactive, touch_target, visible}]

App state patterns detected from pixels:
[JSON: pattern_detections từ A9]

Candidate issues:
[JSON: CMP/STATE/ENV candidates]

Instructions:
1. Confirm/reject each candidate visually.
2. For skeleton/spinner: confirm presence, mark temporal=true (can't determine "stuck" from 1 frame).
3. For empty states: check if there's a proper empty-state message or just blank.
4. For touch targets: look at actual button size relative to screen — small is relative.
5. Look for missing components: does this screen have all expected controls for its apparent function?
6. Platform safe area: safe_area top=[TOP]px, bottom=[BOTTOM]px — check if content overlaps.
```

---

## 5. Few-shot examples

### Example 1 — STATE-01 Skeleton detected

```
[Ảnh: màn có 4 khối xám lặp lại với shimmer — skeleton loader]
A9: [{pattern_type:"skeleton", confidence:0.82, block_count:4, temporal:true}]

Expected:
{
  "findings": [{
    "issue_type": "STATE-01",
    "element_id": null,
    "severity": "high",
    "confidence": 0.78,
    "verdict": "confirmed",
    "original_candidate_rule": "A9-skeleton",
    "evidence": {
      "measured_value": "4 skeleton blocks detected",
      "description": "Skeleton loader chiếm phần lớn màn hình"
    },
    "reasoning": "Skeleton loader visible — content chưa load xong.",
    "severity_justification": "High — content không accessible. Note: 'stuck' không confirm được từ 1 frame."
  }],
  "self_critique": [{
    "issue_index": 0,
    "concern": "Skeleton có thể là loading bình thường, không phải stuck.",
    "decision": "keep",
    "new_confidence": 0.65
  }]
}
```

### Example 2 — CMP-02 phát hiện mới (icon-only button)

```
[Ảnh: e19 là icon nút với icon "⋯" (3 chấm) nhưng không có text label]

Expected:
{
  "findings": [{
    "issue_type": "CMP-02",
    "element_id": "e19",
    "severity": "medium",
    "confidence": 0.72,
    "verdict": "new_finding",
    "evidence": {
      "element_ids": ["e19"],
      "description": "Icon-only button (⋯ more actions) without visible text label"
    },
    "reasoning": "Nút chỉ có icon không có text — người dùng cần đoán chức năng.",
    "severity_justification": "Medium — a11y issue nhưng icon ⋯ khá phổ biến, user quen."
  }]
}
```

---

## 6. Temporal issues (STATE / ENV-13)

Các issue từ A9 có `temporal=true`:
- **Không thể xác nhận "kẹt"** từ 1 frame.
- G6 chỉ xác nhận **sự hiện diện** của pattern, không kết luận "bug" hay "stuck".
- Ghi `"temporal": true` trong evidence + note trong reasoning.
- Severity giữ nguyên nhưng confidence = A9.confidence × 0.85.

```
evidence: {
  "temporal": true,
  "note": "Single frame — 'stuck' requires ≥2 frames comparison (Phase 2 feature)"
}
```

---

## 7. Ranh giới

| Kiểm tra | G6 | G4 | G5 |
|---|---|---|---|
| Touch target size | ✅ CMP-01 | ✅ LAY confirm | — |
| Skeleton/spinner (pattern) | ✅ | — | — |
| Ảnh vỡ | — | — | ✅ IMG-01 |
| Safe-area overlap | ✅ ENV-01/02/03 | ✅ LAY confirm | — |
| Modal đè content (state kẹt) | ✅ STATE-07 | ✅ LAY-06 z-order | — |

→ Dedupe sau bằng S1 Summary agent.

## Trạng thái: spec ✅
