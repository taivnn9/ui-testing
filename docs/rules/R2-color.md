# R2 — Color Rules (màu sắc + contrast)

> **Nguồn dữ liệu:** `elements[].style.*` — tất cả được A4 đo từ pixel.
> Phần lớn đã có `candidate_issues[]` từ A4 — R2 **không duplicate**, chỉ bổ sung
> những gì A4 chưa emit hoặc cần thêm context.
> **Tất định hoàn toàn** — số học pixel, không cần LLM.

## Danh sách rules

| Rule ID | Tiêu chí | Input cần | Điều kiện fire |
|---|---|---|---|
| `R2-STY01` | STY-01 Contrast thấp | style.contrast_ratio_px | contrast < 4.5 (text) / 3.0 (chữ lớn) |
| `R2-STY02` | STY-02 Chữ tàng hình | style.contrast_ratio_px | contrast < 1.5 |
| `R2-STY03` | STY-03 Dark-mode không đổi màu | style.dark_mode_ok, theme | dark_mode_ok=false khi theme=dark |
| `R2-STY04` | STY-04 Icon tàng hình dark mode | style.contrast_ratio_px, role=icon | contrast < 3.0 và theme=dark |
| `R2-STY05` | STY-05 Opacity sai | style.opacity_px | opacity < 0.15 (gần trong suốt) |
| `R2-STY13` | STY-13 Icon/đồ hoạ contrast < 3:1 | style.contrast_ratio_px, role=icon | contrast < 3.0 |

---

## Chi tiết từng rule

### R2-STY01 — Contrast chữ/nền thấp

> **Lưu ý dedup:** A4 đã emit `STY-01_contrast` khi tính màu. R2 chỉ fire nếu A4 CHƯA
> có issue cho element này (tránh trùng).

```
Input:  elem.style.contrast_ratio_px (từ A4 Pixel Color Sampler)
        elem.style.font_size (px, tùy chọn)
        elem.role: phải là text|button|input|tab|nav
Điều kiện:
  cr = elem.style.contrast_ratio_px
  is_large = elem.style.font_size >= 18 * screen.dpr (pt→px)  hoặc là bold ≥ 14pt
  threshold = CONTRAST_TEXT_LARGE (3.0) nếu is_large else CONTRAST_TEXT_NORMAL (4.5)
  Fire nếu: cr != null AND cr < threshold
Confidence: elem.confidence × (A4 crop_confidence) × 0.9
Severity nền: high; range: medium→high  (theo catalog STY-01)
Modifier ↑: role=button(CTA) | nav(primary) → high
Modifier ↓: role=placeholder(hint text, opacity thấp chủ ý) → medium
```

**Edge cases:**
- Text trên ảnh nền phức tạp: A4 ghi `bg_is_solid_px=false` → contrast không đáng tin →
  `confidence` giảm thêm 0.3, ghi `detail="nền không đặc — cần VLM xác nhận"`.
- `contrast_ratio_px=null` (A4 không tách được fg/bg) → không fire R2-STY01, để VLM G3 xử lý.
- Font-scale trợ năng (`screen.font_scale > 1.3`): text lớn hơn → ngưỡng có thể hạ xuống 3.0.

---

### R2-STY02 — Chữ tàng hình (invisible text)

```
Input:  elem.style.contrast_ratio_px
        elem.role: text|button|input
Điều kiện:
  cr < CONTRAST_INVISIBLE (1.5)
Confidence: elem.confidence × 0.95
Severity nền: critical; range: high→critical
Modifier ↑: role=button|CTA|nav → critical
```

**Edge cases:**
- Chữ trắng trên nền trắng do CSS bug → contrast ≈ 1.0 → critical.
- Chữ màu background chủ ý (CAPTCHA) → cần VLM xác nhận ngữ cảnh.

---

### R2-STY03 — Dark-mode không đổi màu

```
Input:  elem.style.dark_mode_ok (bool từ A4)
        screen.theme = "dark"
        elem.style.bg_color_px
Điều kiện:
  screen.theme == "dark"
  elem.style.dark_mode_ok == False
  → bg_color_px có luminance cao (sáng) trong dark theme → hardcode màu sáng
Fire khi: luminance(bg_color_px) > 0.4 trên màn dark
Confidence: elem.confidence × 0.75   (A4 infer theme từ pixel — uncertain)
Severity nền: high; range: medium→critical
Ghi chú: chỉ fire khi screen.theme="dark"; nếu theme="system" → confidence giảm thêm.
```

**Edge cases:**
- Element cố tình màu sáng trong dark mode (avatar, badge màu brand) → VLM G3 xác nhận.
- Screenshot chụp trong sáng nhưng meta ghi dark → meta_confidence thấp → confidence issue thấp.

---

### R2-STY04 — Icon tàng hình trong dark mode

```
Input:  elem.role = "icon"
        elem.style.contrast_ratio_px
        screen.theme = "dark"
Điều kiện:
  elem.role == "icon" AND screen.theme == "dark"
  cr < CONTRAST_UI (3.0)   ← ngưỡng đồ hoạ (không phải 4.5)
Confidence: elem.confidence × 0.8
Severity nền: high; range: medium→critical  (STY-04)
```

---

### R2-STY05 — Opacity sai (gần trong suốt)

```
Input:  elem.style.opacity_px (từ A4)
        elem.visible = true
Điều kiện:
  opacity_px < 0.15   → gần như vô hình
  opacity_px trong [0.15, 0.35] → nghi mờ bất thường
  Fire với confidence cao khi < 0.15; confidence thấp khi 0.15–0.35
Confidence: elem.confidence × 0.7
Severity nền: medium; range: low→high
Modifier ↑: role=button|input (cần thấy rõ) → high
Modifier ↓: overlay/skeleton (mờ chủ ý) → trivial
Ghi chú: A4 opacity từ alpha-channel — chính xác nhất với RGBA; ước lượng với RGB.
```

---

### R2-STY13 — Tương phản icon/đồ hoạ chức năng < 3:1

```
Input:  elem.role = "icon"
        elem.style.contrast_ratio_px (tính giữa dominant_colors sáng nhất / tối nhất)
        elem.interactive = true  ← icon chức năng (không phải decorative)
Điều kiện:
  elem.interactive == True
  cr < CONTRAST_UI (3.0)
Confidence: elem.confidence × 0.8
Severity nền: medium; range: low→high  (a11y)
Modifier ↑: nav icon, primary action → high
Modifier ↓: decorative icon (interactive=false) → trivial
```

---

## Thứ tự chạy đề xuất

```
1. R2-STY02  (invisible — critical priority, nhanh)
2. R2-STY01  (contrast thấp — fire nhiều nhất)
3. R2-STY13  (icon contrast)
4. R2-STY04  (icon dark mode)
5. R2-STY03  (dark mode global)
6. R2-STY05  (opacity — confidence thấp nhất)
```

## Mối quan hệ với A4 (tránh duplicate)

Dedup logic:
```python
existing_rules = {(i.rule, i.element) for i in doc.candidate_issues}
if ("STY-01_contrast", elem.id) not in existing_rules:
    # R2 fire
```

A4 emit: `STY-01_contrast` khi tính inline.
R2 emit: `R2-STY01` — khác prefix → dedup bằng element_id + rule_prefix.

## Trạng thái: spec ✅ — chờ implement sau standard set.
