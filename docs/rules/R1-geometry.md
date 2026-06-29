# R1 — Geometry Rules (hình học không gian)

> **TL;DR:** Rule tất định về vị trí/kích thước (overlap, off-screen, overflow, touch target, safe-area…) tính từ `bbox` + `relations` — không cần agent reasoning.

> **Nguồn dữ liệu:** `elements[].bbox`, `relations[]` (tiền tính bởi A0), `screen.viewport`, `screen.safe_area`, `screen.platform`.

## Danh sách rules

| Rule ID | Tiêu chí | Điều kiện fire | Severity nền (range) |
|---|---|---|---|
| `R1-LAY01` | Overlap sibling | IoU > 0.05 giữa 2 sibling (không parent-child) | high (medium→critical) |
| `R1-LAY02` | Off-screen | bbox vượt viewport | high (medium→critical) |
| `R1-LAY03` | Overflow container | element vượt parent > 4px | medium (low→high) |
| `R1-LAY04` | Lệch grid 8pt | x/y không align 8pt±2px (chỉ element `source != "vision"`) | low (trivial→medium) |
| `R1-LAY05` | Optical misalignment | offset cạnh sibling trong 2–6px | low (trivial→medium) |
| `R1-LAY06` | Z-order occlusion | A che B, A có z cao hơn → B bị ẩn | high (medium→critical) |
| `R1-LAY07` | Gap bất thường | gap <4px hoặc > median×3 | low (trivial→medium) |
| `R1-LAY08` | Lệch tâm | center element lệch center parent >5px | low (trivial→low) |
| `R1-LAY12` | Container tỉ lệ sai | aspect >15 (hoặc h<4px, w>50px) | low (trivial→medium) |
| `R1-LAY14` | Near-dup vị trí | IoU > 0.9 (không parent-child) | medium (low→high) |
| `R1-CMP01` | Touch target nhỏ | w hoặc h < 44pt×dpr (iOS) / 48dp×dpr (Android) | high (medium→high) |
| `R1-CMP16` | Tap gap chồng | gap < 8pt×dpr giữa 2 interactive | medium (low→high) |
| `R1-ENV01` | Safe-area violation | bbox overlap safe_area > 10px | high (medium→critical) |
| `R1-ENV02` | Status bar overlap | bbox.y < status_bar_h + 4px | medium (low→high) |
| `R1-ENV03` | Home indicator overlap (iOS) | bbox vượt `viewport.h - nav_bar_h` + 4px | medium (low→high) |

> ⚠️ **R1-LAY04** chỉ chạy trên element có `source != "vision"` — toạ độ CV (vision) nhiễu, không đo được grid → trên ảnh vision-only rule này nằm im.

---

## Chi tiết từng rule

### R1-LAY01 — Overlap / va chạm phần tử
- **Fire:** IoU > `OVERLAP_IOU_MIN` (0.05); KHÔNG parent-child; cả 2 `visible=true`; không phải chủ ý.
- **Chủ ý (skip):** a/b có role=modal/tooltip/skeleton; hoặc z(a) > z(b) rõ rệt.
- **Confidence:** `min(a.conf, b.conf) × (0.5 + iou×0.5)`
- **Modifier:** ↑ một bên là button/input/nav → high–critical · ↓ IoU<0.15 → medium · ↓ decorative → low
- **Output:** element = id của phần tử nhỏ hơn (bị che).
- **Edge:** badge số trên icon avatar (icon, size<30px) → skip · sticky header khi scroll → A9 đa-frame Phase 2 · modal overlay (z cao, role=modal) → skip.

### R1-LAY02 — Off-screen / cắt mép viewport
- **Fire (tolerance ±2px AA/rounding):**
  - `x < -2` (left) · `y < -safe_area.top - 5` (top) · `x+w > viewport.w + 2` (right) · `y+h > viewport.h + 5` (bottom)
- **Confidence:** `elem.conf × 0.95`
- **Modifier:** ↑ button/input/text → high–critical · ↓ decorative/background → low
- **Edge:** ảnh nền parallax (image, z thấp) → giảm · `offscreen=true` từ A3 → confidence cao hơn.

### R1-LAY03 — Overflow container
- **Fire:** với element e có parent p, overflow bất kỳ cạnh > `OVERFLOW_THRESHOLD` (4px):
  `overflow_x = max(0,(e.x+e.w)-(p.x+p.w))`, tương tự y, left, top.
- **Confidence:** `min(e.conf, p.conf) × 0.85`
- **Modifier:** ↑ `text_truncated=true` (A5) → high · ↑ i18n locale → thêm cờ i18n
- **Edge:** bleed design (image, overflow<10px) → trivial · scroll container cần A9 xác nhận.

### R1-LAY04 — Lệch grid 8pt
- **Chỉ áp element có `source != "vision"`** và role không phải icon/decorative.
- `grid_unit_px = GRID_UNIT_LOGICAL × dpr` (8×dpr); `tolerance_px = GRID_TOLERANCE_PX` (2px).
- **Fire:** với orphan element (không parent), cả `x` và `y` đều KHÔNG aligned (rem ≤ tol hoặc ≥ unit-tol).
- **Confidence:** `elem.conf × 0.7`
- **Edge:** grid 4pt/10px → auto-detect grid unit từ histogram x-coords orphan, ghi `screen.grid_unit_detected`.

### R1-LAY05 — Optical misalignment
- **Fire:** 2 sibling cùng group, offset cạnh trái/phải trong **[2, 6]px** (quá nhỏ để chủ ý, quá lớn để tolerance).
- **Confidence:** `min(a.conf, b.conf) × 0.5` (heuristic yếu — agent reasoning Layout xác nhận mới fire).

### R1-LAY06 — Z-order occlusion
- **Fire:** cặp IoU>0.05, intersection chứa text/interactive của a, và b có z < a.z (b che phần quan trọng của a). a.z==b.z → uncertainty.
- **Confidence:** `min(a.conf, b.conf) × 0.7`

### R1-LAY07 — Gap bất thường
- **Fire:** (a) quá chật `gap < GAP_MIN_PX` (4px) → candidate overlap; (b) quá rộng `gap > median×3` trong list → spacing không đều (chỉ khi A3 đã detect group/list).
- **Confidence:** 0.4 (cần agent reasoning xác nhận ngữ cảnh).

### R1-LAY08 — Lệch tâm
- **Fire:** element trong container nhỏ (`p.w < 200`) có `|e_cx - p_cx| > 5px`.
- **Confidence:** `min(e.conf, p.conf) × 0.6` · áp chính cho icon trong button/nav tab.

### R1-LAY12 — Container tỉ lệ bất thường
- **Fire:** role=container/card/modal, `aspect = max(w,h)/min(w,h) > 15` và w>100px; hoặc h<4px và w>50px (divider sai).
- **Confidence:** `elem.conf × 0.65`

### R1-LAY14 — Near-duplicate vị trí
- **Fire:** IoU > 0.9 giữa 2 element không parent-child → gần trùng khít → khả năng duplicate.
- **Confidence:** `min(a.conf, b.conf) × 0.9` (khác LAY-01 ở ngưỡng IoU).

### R1-CMP01 — Touch target nhỏ
- **Fire:** `interactive=true`; `target = touch_target nếu có else bbox`; `min_touch = touch_min_px(dpr, platform)` (44pt×dpr iOS / 48dp×dpr Android); fire nếu w hoặc h < min_touch.
- **Confidence:** `elem.conf × 0.9`
- **Modifier:** ↑ button CTA → high · ↓ icon decorative trong nav → medium

### R1-CMP16 — Tap gap chồng
- **Fire:** 2 element `interactive=true`, `gap < touch_gap_px(dpr)` (8pt×dpr) → dễ tap nhầm.
- **Confidence:** `min(a.conf, b.conf) × 0.8`

### R1-ENV01 — Safe-area / notch violation
- safe_area theo device px (A13 cấp). Vùng cấm: top `[0, safe_area.top]`, bottom `[h-safe_area.bottom, h]`, left/right tương tự.
- **Fire:** bbox overlap vùng cấm > 10px (không chỉ chạm), `role != background`, `visible=true`.
- **Confidence:** `elem.conf × screen.meta_confidence` (A13)
- **Modifier:** ↑ button/input → critical · ↓ background/image → medium

### R1-ENV02 — Status bar overlap
- **Fire:** `bbox.y < screen.status_bar_h + 4px` (A13) → đè vùng giờ/pin/signal.
- **Confidence:** `elem.conf × meta_confidence`

### R1-ENV03 — Home indicator overlap (iOS)
- **Chỉ platform=ios.** `home_start_y = viewport.h - nav_bar_h`; fire nếu `bbox.y+bbox.h > home_start_y + 4px`.
- **Confidence:** `elem.conf × meta_confidence`

---

## Thứ tự chạy đề xuất

1. R1-LAY02 (off-screen) → 2. R1-ENV01/02/03 (cần A13) → 3. R1-LAY01 (overlap) → 4. R1-LAY14 (near-dup) → 5. R1-LAY03 (overflow) → 6. R1-LAY06 (z-order) → 7. R1-CMP01 (touch) → 8. R1-CMP16 (tap gap) → 9. R1-LAY07 (gap) → 10. R1-LAY04/05/08/12 (alignment, low priority).

## Trạng thái: spec ✅ — chờ implement sau standard set.
