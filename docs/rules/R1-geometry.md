# R1 — Geometry Rules (hình học không gian)

> **Nguồn dữ liệu:** `elements[].bbox`, `relations[]` (đã tiền tính bởi A0),
> `screen.viewport`, `screen.safe_area`, `screen.platform`.
> **Tất định hoàn toàn** — không cần LLM.

## Danh sách rules

| Rule ID | Tiêu chí | Input cần | Điều kiện fire |
|---|---|---|---|
| `R1-LAY01` | LAY-01 Overlap | relations[rel="overlaps"] | iou > 0.05 giữa 2 sibling |
| `R1-LAY02` | LAY-02 Off-screen | bbox, viewport | bbox vượt ra ngoài viewport |
| `R1-LAY03` | LAY-03 Overflow container | bbox, parent.bbox | element vượt ra ngoài parent > threshold |
| `R1-LAY04` | LAY-04 Lệch grid | bbox, screen.dpr | x hoặc y không align 8pt ± tolerance |
| `R1-LAY05` | LAY-05 Optical misalignment | bbox, siblings | elements gần cùng cạnh nhưng lệch nhỏ |
| `R1-LAY06` | LAY-06 Z-order occlusion | bbox, z, overlap | element A che B, A có z cao → B bị ẩn |
| `R1-LAY07` | LAY-07 Gap bất thường | relations[gap] | gap giữa 2 element quá nhỏ (<4px) hoặc quá lớn bất thường |
| `R1-LAY08` | LAY-08 Lệch tâm | bbox, parent.bbox | center element lệch center parent > threshold |
| `R1-LAY12` | LAY-12 Container tỉ lệ sai | bbox | aspect ratio quá bất thường (>10:1 hay <1:10) |
| `R1-LAY14` | LAY-14 Phần tử chồng vị trí | relations[rel="overlaps",iou] | iou > 0.9 giữa 2 element → gần trùng hoàn toàn |
| `R1-CMP01` | CMP-01 Touch target nhỏ | bbox, touch_target, interactive, platform | w hoặc h < 44pt×dpr (iOS) / 48dp×dpr (Android) |
| `R1-CMP16` | CMP-16 Khoảng tap chồng | gap, interactive | gap < 8pt×dpr giữa 2 interactive element |
| `R1-ENV01` | ENV-01 Safe-area violation | bbox, safe_area | element bbox trong vùng safe_area (notch/DI) |
| `R1-ENV02` | ENV-02 Status bar overlap | bbox, status_bar_h | element bbox overlap vùng status bar |
| `R1-ENV03` | ENV-03 Home indicator overlap | bbox, viewport.h, nav_bar_h | element bbox overlap home indicator area |

---

## Chi tiết từng rule

### R1-LAY01 — Overlap / va chạm phần tử vô lý

```
Input:  relations[] lọc rel="overlaps"; elements[] để lấy role + z
Điều kiện:
  - IoU > OVERLAP_IOU_MIN (0.05) giữa a và b
  - KHÔNG phải quan hệ parent-child (b.parent != a.id và ngược lại)
  - Cả 2 đều visible=true
  - Không phải trường hợp chủ ý: badge-trên-icon, tooltip, modal-overlay
    → Cờ "chủ ý" khi: a hoặc b có role=modal/tooltip/skeleton; z của a > z của b rõ rệt
Confidence:
  = min(elem_a.confidence, elem_b.confidence) × (0.5 + iou × 0.5)
Severity nền: high; range: medium→critical
Modifier ↑: một trong 2 là role=button|input|nav → high–critical
Modifier ↓: IoU < 0.15 → medium; 1 là decorative → low
Output: 1 issue cho cặp (a, b), element = id của element nhỏ hơn (bị che)
```

**Edge cases:**
- Badge icon (số thông báo) đè lên icon avatar → chủ ý: loại khi 1 element có role=icon và kích thước < 30px.
- Sticky header đè content khi scroll → không detect từ 1 frame (A9 phát hiện sticky-overlap ở Phase 2 đa-frame).
- Modal overlay → z cao hơn hẳn và role=modal → skip.

---

### R1-LAY02 — Off-screen / cắt mép viewport

```
Input:  elements[].bbox, screen.viewport.{w,h}
Điều kiện:
  elem.bbox.x < -2                 → offscreen left
  elem.bbox.y < -screen.safe_area.top - 5   → offscreen top (trừ safe_area)
  elem.bbox.x + elem.bbox.w > viewport.w + 2  → offscreen right
  elem.bbox.y + elem.bbox.h > viewport.h + 5  → offscreen bottom
  Tolerance ±2px cho anti-aliasing / rounding error
Confidence: elem.confidence × 0.95
Severity nền: high; range: medium→critical
Modifier ↑: role=button|input|text (nội dung chính) → high–critical
Modifier ↓: role=decorative|background → low
```

**Edge cases:**
- Ảnh nền cố tình vượt mép (parallax) → role=image + z thấp → giảm severity.
- Off-screen -1px → tolerance loại trừ.
- `offscreen=true` đã được A3 đánh dấu → nếu có, rule lấy confidence cao hơn.

---

### R1-LAY03 — Overflow container (tràn ra ngoài cha)

```
Input:  elements[].bbox, elements[].parent → parent.bbox
Điều kiện:
  Với mỗi element e có parent p:
  overflow_x = max(0, (e.bbox.x + e.bbox.w) - (p.bbox.x + p.bbox.w))
  overflow_y = max(0, (e.bbox.y + e.bbox.h) - (p.bbox.y + p.bbox.h))
  left_overflow = max(0, p.bbox.x - e.bbox.x)
  top_overflow  = max(0, p.bbox.y - e.bbox.y)
  Fire nếu bất kỳ overflow > OVERFLOW_THRESHOLD (đề xuất: 4px)
Confidence: min(e.confidence, parent.confidence) × 0.85
Severity nền: medium; range: low→high
Modifier ↑: text cắt cụt rõ (text_truncated=true từ A5) → high
Modifier ↑: i18n locale (text dài hơn) → thêm cờ i18n
```

**Edge cases:**
- Card image vượt mép có chủ ý (bleed design) → role=image + overflow < 10px → trivial.
- Parent confidence thấp (A3 bbox sai) → confidence issue thấp, VLM xác nhận.
- Scroll container: element đúng ra nằm ngoài viewport của scroll container → cần A9 xác nhận scroll.

---

### R1-LAY04 — Lệch grid (không theo 8pt)

```
Input:  elements[].bbox, screen.viewport.dpr
Điều kiện:
  grid_unit_px = GRID_UNIT_LOGICAL × dpr   (8 × dpr)
  tolerance_px = GRID_TOLERANCE_PX          (2px)
  
  Với mỗi orphan element e (không có parent):
    x_rem = e.bbox.x % grid_unit_px
    y_rem = e.bbox.y % grid_unit_px
    x_aligned = x_rem <= tolerance_px or x_rem >= (grid_unit_px - tolerance_px)
    y_aligned = y_rem <= tolerance_px or y_rem >= (grid_unit_px - tolerance_px)
    if NOT x_aligned AND NOT y_aligned: fire
  
Confidence: elem.confidence × 0.7  (confidence thấp — vision bbox không pixel-perfect)
Severity nền: low; range: trivial→medium
Ghi chú: ưu tiên thấp — chỉ áp cho element có role không phải icon/decorative
```

**Edge cases:**
- Design dùng grid 4pt hoặc 10px → false positive. Giải pháp: auto-detect grid unit từ distribution x-coords của tất cả orphan elements (histogram → peak = grid unit). Ghi vào `screen.grid_unit_detected`.
- A3 bbox có sai số ±2–3px → tolerance bao gồm sai số này.

---

### R1-LAY05 — Optical misalignment

```
Input:  elements[].bbox, relations[rel="sibling"|"above"|"below"|"left_of"]
Điều kiện:
  Với 2 sibling element a, b trong cùng group (gần nhau, có thể cùng parent):
    Cạnh trái a gần cạnh trái b (|a.bbox.x - b.bbox.x| trong [2, 6]):
      → nghi lệch nhỏ (intentional hay bug?)
    Cạnh phải a gần cạnh phải b tương tự.
    → Fire nếu offset trong khoảng 2–6px (quá nhỏ để chủ ý, quá lớn để tolerance)

Confidence: min(a.confidence, b.confidence) × 0.5   (rất uncertain — VLM xác nhận)
Severity nền: low; range: trivial→medium
Ghi chú: đây là heuristic yếu — VLM agent G4 (Layout) xác nhận mới fire.
```

---

### R1-LAY06 — Z-order occlusion

```
Input:  elements[].bbox, elements[].z, relations[rel="overlaps"]
Điều kiện:
  Cặp (a, b) có IoU > 0.05 và:
    a.z == b.z (không rõ thứ tự) → uncertainty
    a.z < b.z nhưng a bị b che (b ngồi trên) → đây là bình thường, không fire
    a.z > b.z nhưng b che phần quan trọng của a (contains phần text/button của a) → fire
Fire khi: intersection chứa text/interactive element của a và b có z < a.z
Confidence: min(a.confidence, b.confidence) × 0.7
Severity nền: high; range: medium→critical
```

---

### R1-LAY07 — Gap bất thường

```
Input:  relations[].gap giữa các element có cùng parent hoặc sibling gần
Điều kiện (2 loại):
  a) Quá chật: gap < GAP_MIN_PX (4px) giữa 2 sibling visible → candidate overlap
  b) Quá rộng: gap trong cùng list/group lớn hơn median × 3 → spacing không đều
Confidence: low (0.4)   (cần VLM xác nhận ngữ cảnh)
Severity nền: low; range: trivial→medium
Ghi chú: (b) chỉ fire khi đã detect được group/list từ A3 alignment clustering.
```

---

### R1-LAY08 — Lệch tâm

```
Input:  elements[].bbox, elements[].parent → parent.bbox
Điều kiện:
  Với element e có parent p:
    e_cx = e.bbox.x + e.bbox.w / 2
    p_cx = p.bbox.x + p.bbox.w / 2
    offset = abs(e_cx - p_cx)
    Nếu element nằm trong container nhỏ (p.bbox.w < 200) và offset > 5px → fire
Confidence: min(e.confidence, p.confidence) × 0.6
Severity nền: low; range: trivial→low
Áp dụng chính cho: icon trong button, icon trong nav tab.
```

---

### R1-LAY12 — Container tỉ lệ bất thường

```
Input:  elements[].bbox có role=container|card|modal
Điều kiện:
  aspect = max(w, h) / min(w, h)
  Nếu aspect > 15 và w > 100px (hàng ngang dài bất thường) → fire
  Nếu h < 4px và w > 50px → có thể divider render sai
Confidence: elem.confidence × 0.65
Severity nền: low; range: trivial→medium
```

---

### R1-LAY14 — Phần tử chồng vị trí (near-duplicate position)

```
Input:  relations[rel="overlaps", iou]
Điều kiện:
  IoU > 0.9 giữa 2 element không có quan hệ parent-child
  → 2 phần tử gần như chồng khít nhau (gần như trùng)
Confidence: min(a.confidence, b.confidence) × 0.9
Severity nền: medium; range: low→high
Ghi chú: khác LAY-01 (IoU > 0.05) — đây là gần trùng hoàn toàn → khả năng duplicate element.
```

---

### R1-CMP01 — Touch target nhỏ

```
Input:  elements[].touch_target (hoặc bbox nếu không có touch_target),
        elements[].interactive, screen.platform, screen.viewport.dpr
Điều kiện:
  elem.interactive == True
  target_w = elem.touch_target.w if elem.touch_target else elem.bbox.w
  target_h = elem.touch_target.h if elem.touch_target else elem.bbox.h
  min_touch = touch_min_px(dpr, platform)  [44pt×dpr iOS / 48dp×dpr Android]
  if target_w < min_touch OR target_h < min_touch: fire
Confidence: elem.confidence × 0.9
Severity nền: high; range: medium→high
Modifier ↑: role=button(primary/CTA) → high
Modifier ↓: role=icon(decorative) trong nav → medium
```

---

### R1-CMP16 — Khoảng tap chồng nhau

```
Input:  relations[].gap giữa các interactive element
Điều kiện:
  a.interactive=true, b.interactive=true
  gap_between(a.bbox, b.bbox) < touch_gap_px(dpr)  [8pt×dpr]
  → 2 nút quá sát nhau → dễ tap nhầm
Confidence: min(a.confidence, b.confidence) × 0.8
Severity nền: medium; range: low→high
```

---

### R1-ENV01 — Safe-area / notch violation

```
Input:  elements[].bbox, screen.safe_area, screen.viewport
Điều kiện (safe_area tính theo device px — A13 đã cấp):
  Vùng cấm top: y trong [0, safe_area.top]
  Vùng cấm bottom: y trong [viewport.h - safe_area.bottom, viewport.h]
  Vùng cấm left: x trong [0, safe_area.left]
  Vùng cấm right: x trong [viewport.w - safe_area.right, viewport.w]
  
  Fire nếu: elem.bbox overlap vùng cấm > 10px (không chỉ chạm cạnh)
  Chỉ fire khi elem.role != "background" và elem.visible=true
  
Confidence: elem.confidence × screen.meta_confidence (từ A13)
Severity nền: high; range: medium→critical
Modifier ↑: role=button|input → critical (không bấm được)
Modifier ↓: role=background|image (decor) → medium
```

---

### R1-ENV02 — Status bar overlap / lẫn màu

```
Input:  elements[].bbox, screen.status_bar_h (từ A13)
Điều kiện:
  elem.bbox.y < screen.status_bar_h + 4px
  → element content chồng lên vùng status bar (giờ / pin / signal)
Confidence: elem.confidence × screen.meta_confidence
Severity nền: medium; range: low→high
```

---

### R1-ENV03 — Home indicator overlap (iOS)

```
Input:  elements[].bbox, screen.nav_bar_h, screen.viewport.h, screen.platform
Điều kiện:
  Chỉ áp với platform=ios
  home_start_y = screen.viewport.h - screen.nav_bar_h
  elem.bbox.y + elem.bbox.h > home_start_y + 4px
  → element chồng lên home indicator area
Confidence: elem.confidence × screen.meta_confidence
Severity nền: medium; range: low→high
```

---

## Thứ tự chạy đề xuất

```
1. R1-LAY02  (off-screen — nhanh, cần trước các rule containment)
2. R1-ENV01/02/03  (safe-area — cần A13 metadata)
3. R1-LAY01  (overlap — dùng relations[] đã có)
4. R1-LAY14  (near-dup — dùng relations[])
5. R1-LAY03  (overflow — cần parent)
6. R1-LAY06  (z-order)
7. R1-CMP01  (touch target)
8. R1-CMP16  (tap gap)
9. R1-LAY07  (gap bất thường)
10. R1-LAY04/05/08/12  (low-priority alignment)
```

## Trạng thái: spec ✅ — chờ implement sau standard set.
