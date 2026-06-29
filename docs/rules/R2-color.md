# R2 — Color Rules (màu sắc + contrast)

> **TL;DR:** Rule tất định về contrast/opacity/dark-mode, tính từ pixel màu do A4 đo (`style.*`). Chỉ bổ sung phần A4 chưa emit — dedup theo `(rule_prefix, element_id)`.

> **Nguồn dữ liệu:** `elements[].style.*` (A4 đo từ pixel). Phần lớn đã có `candidate_issues[]` từ A4; R2 không duplicate.

## Danh sách rules

| Rule ID | Tiêu chí | Điều kiện fire | Severity nền (range) |
|---|---|---|---|
| `R2-STY01` | Contrast chữ/nền thấp | cr < 4.5 (text) / 3.0 (chữ lớn) | high (medium→high) |
| `R2-STY02` | Chữ tàng hình | cr < 1.5 | critical (high→critical) |
| `R2-STY03` | Dark-mode không đổi màu | `dark_mode_ok=false` khi `theme=dark` | high (medium→critical) |
| `R2-STY04` | Icon tàng hình dark mode | role=icon, theme=dark, cr < 3.0 | high (medium→critical) |
| `R2-STY05` | Opacity sai | opacity < 0.15 (gần trong suốt) | medium (low→high) |
| `R2-STY13` | Icon/đồ hoạ contrast < 3:1 | role=icon interactive, cr < 3.0 | medium (low→high) |

`cr` = `style.contrast_ratio_px`. Ngưỡng: `CONTRAST_TEXT_NORMAL`=4.5, `CONTRAST_TEXT_LARGE`=3.0, `CONTRAST_INVISIBLE`=1.5, `CONTRAST_UI`=3.0.

---

## Chi tiết từng rule

### R2-STY01 — Contrast chữ/nền thấp
- **Dedup:** A4 đã emit `STY-01_contrast` → R2 chỉ fire nếu element CHƯA có issue đó.
- **Fire:** role ∈ text/button/input/tab/nav; `is_large = font_size >= 18×dpr hoặc bold ≥14pt`; threshold = 3.0 nếu large else 4.5; fire khi `cr != null AND cr < threshold`.
- **Confidence:** `elem.conf × crop_confidence × 0.9`
- **Modifier:** ↑ button CTA / nav primary → high · ↓ placeholder hint → medium
- **Edge:** `bg_is_solid_px=false` → conf −0.3, detail "nền không đặc — cần agent xác nhận" · `cr=null` → không fire (để agent reasoning Text/Color xử lý) · `font_scale > 1.3` → ngưỡng có thể hạ 3.0.

### R2-STY02 — Chữ tàng hình (invisible text)
- **Fire:** role ∈ text/button/input, `cr < 1.5`.
- **Confidence:** `elem.conf × 0.95`
- **Modifier:** ↑ button/CTA/nav → critical
- **Edge:** trắng/trắng do CSS bug → cr≈1.0 critical · chữ ẩn chủ ý (CAPTCHA) → agent xác nhận.

### R2-STY03 — Dark-mode không đổi màu
- **Fire:** `theme=dark`, `dark_mode_ok=false`, `luminance(bg_color_px) > 0.4` → hardcode màu sáng.
- **Confidence:** `elem.conf × 0.75` (A4 infer theme từ pixel); `theme=system` → conf giảm thêm.
- **Edge:** màu sáng chủ ý (badge brand) → agent xác nhận · meta dark nhưng ảnh sáng → meta_confidence thấp.

### R2-STY04 — Icon tàng hình dark mode
- **Fire:** `role=icon`, `theme=dark`, `cr < CONTRAST_UI` (3.0).
- **Confidence:** `elem.conf × 0.8`

### R2-STY05 — Opacity sai
- **Fire:** `opacity_px < 0.15` (conf cao); `0.15–0.35` (conf thấp, nghi mờ).
- **Confidence:** `elem.conf × 0.7`
- **Modifier:** ↑ button/input → high · ↓ overlay/skeleton (mờ chủ ý) → trivial
- **Ghi chú:** A4 lấy opacity từ alpha-channel (chính xác với RGBA, ước lượng với RGB).

### R2-STY13 — Contrast icon/đồ hoạ chức năng < 3:1
- **Fire:** `role=icon`, `interactive=true`, `cr < CONTRAST_UI` (3.0). cr tính giữa dominant_colors sáng nhất/tối nhất.
- **Confidence:** `elem.conf × 0.8`
- **Modifier:** ↑ nav icon / primary action → high · ↓ decorative (interactive=false) → trivial

---

## Thứ tự chạy đề xuất

1. R2-STY02 (invisible, critical) → 2. R2-STY01 (contrast) → 3. R2-STY13 (icon contrast) → 4. R2-STY04 (icon dark) → 5. R2-STY03 (dark global) → 6. R2-STY05 (opacity).

## Dedup với A4

```python
existing_rules = {(i.rule, i.element) for i in doc.candidate_issues}
if ("STY-01_contrast", elem.id) not in existing_rules:
    # R2 fire
```
A4 emit `STY-01_contrast`; R2 emit `R2-STY01` (khác prefix) → dedup theo element_id + rule_prefix.

## Trạng thái: spec ✅ — chờ implement sau standard set.
