# R3 — Image Rules (ảnh + icon)

> **Nguồn dữ liệu:** `elements[].image_meta` (từ A7), `elements[]` role=image/icon,
> output A6 (icon_regions), output A9 (broken_image), output A10 (hash duplicates).
> **Tất định hoàn toàn** (số học ratio + hash Hamming).

## Danh sách rules

| Rule ID | Tiêu chí | Input cần | Điều kiện fire |
|---|---|---|---|
| `R3-IMG02` | IMG-02 Méo / sai tỉ lệ | image_meta.intrinsic_*, displayed_* | |intrinsic_ratio - displayed_ratio| > threshold |
| `R3-IMG03` | IMG-03 Mờ / pixel hoá | image_meta.blur_score | blur_score < BLUR_WARN |
| `R3-IMG07` | IMG-07 Icon lệch tâm trong nút | bbox icon vs bbox parent button | offset center > threshold |
| `R3-IMG08` | IMG-08 Icon placeholder | A6.possible_placeholder | possible_placeholder=true |
| `R3-IMG12` | IMG-12 Ảnh trùng lặp | A10 duplicate pairs | hamming < HASH_NEAR_DUP |
| `R3-IMG03u`| IMG-03 Upscale (thiếu @2x/@3x) | image_meta.intrinsic/displayed size | displayed > intrinsic × UPSCALE_RATIO |

---

## Chi tiết từng rule

### R3-IMG02 — Méo / sai tỉ lệ ảnh

```
Input:  elem.image_meta.{intrinsic_w, intrinsic_h, displayed_w, displayed_h}
        (từ A7 Image Region Meta Reader)
Điều kiện:
  Nếu intrinsic_w == null hoặc intrinsic_h == null → không thể tính → skip
  intrinsic_ratio = intrinsic_w / intrinsic_h
  displayed_ratio = displayed_w / displayed_h
  deviation = abs(intrinsic_ratio - displayed_ratio) / intrinsic_ratio
  
  if deviation > ASPECT_ERROR (0.15): fire HIGH
  if deviation > ASPECT_WARN  (0.05): fire MEDIUM

Confidence: elem.confidence × 0.85
  (A7 ước lượng intrinsic từ pixel → không chắc 100%)
Severity nền: medium; range: low→high
Modifier ↑: role=image (ảnh người / sản phẩm) + deviation > 0.3 → high
Modifier ↑: branding/logo ảnh → high (thương hiệu)
Modifier ↓: icon nhỏ ≤ 32px → low (khó nhận ra méo)
Evidence: { intrinsic_ratio, displayed_ratio, deviation }
```

**Edge cases:**
- `scale_mode="fill"` hoặc `"cover"`: crop chủ ý → không phải méo, nhưng aspect ratio hiển thị KHÁC intrinsic là chủ ý. **Không fire** nếu `scale_mode in ("fill","cover","tile")`.
- `scale_mode="stretch"`: đây là méo thật → vẫn fire.
- Intrinsic không có (`image_meta=null`): A7 không detect được → skip R3-IMG02 hoàn toàn; VLM G5 xử lý visual.
- Icon SVG: vector → intrinsic ratio có thể không có → skip.

---

### R3-IMG03 — Mờ / pixel hoá (ảnh quality thấp)

```
Input:  elem.image_meta.blur_score  (Laplacian variance từ A7)
        screen.viewport.dpr
Điều kiện:
  blur_thresh = BLUR_WARN (50.0) được scale theo dpr:
    effective_thresh = BLUR_WARN × dpr  [dpr=1→50, dpr=2→100, dpr=3→150]
  
  if blur_score < BLUR_CLEAR × dpr / 2: fire HIGH  (rất mờ)
  if blur_score < effective_thresh: fire MEDIUM

Confidence: elem.confidence × 0.75  (Laplacian nhạy với ảnh có ít texture thật)
Severity nền: medium; range: low→medium
Modifier ↑: ảnh sản phẩm / ảnh người / banner → medium–high
Modifier ↓: background decorative, icon nhỏ → low–trivial
Ghi chú: Laplacian cao ≠ ảnh đẹp — chỉ đo độ sắc nét pixel-level.
```

---

### R3-IMG03u — Upscale (thiếu @2x/@3x asset)

```
Input:  elem.image_meta.{intrinsic_w, displayed_w}  (A7)
        screen.viewport.dpr
Điều kiện:
  displayed_w > intrinsic_w × UPSCALE_RATIO (1.5)
  → ảnh hiển thị lớn hơn kích thước thực 1.5× → bị pixel hoá
  Thực tế quan trọng: trên màn @3x (dpr=3), ảnh @1x đã bị pixel khi displayed = intrinsic
    → Kiểm thêm: intrinsic_w < displayed_w × dpr (thiếu asset đủ dpi)
    
Confidence: elem.confidence × 0.8
Severity nền: low; range: trivial→medium
Modifier ↑: banner, hero image, ảnh sản phẩm → medium
Tags: resp, mob
```

---

### R3-IMG07 — Icon lệch tâm trong nút

```
Input:  icon element với parent có role=button|tab|nav
        icon.bbox.center vs parent.bbox.center
Điều kiện:
  icon_cx = icon.bbox.x + icon.bbox.w / 2
  icon_cy = icon.bbox.y + icon.bbox.h / 2
  parent_cx = parent.bbox.x + parent.bbox.w / 2
  parent_cy = parent.bbox.y + parent.bbox.h / 2
  h_offset = abs(icon_cx - parent_cx)
  v_offset = abs(icon_cy - parent_cy)
  
  threshold = max(3.0, parent.bbox.w * 0.05)  [5% width của parent, tối thiểu 3px]
  Fire nếu h_offset > threshold OR v_offset > threshold

Confidence: min(icon.confidence, parent.confidence) × 0.7
Severity nền: low; range: trivial→medium  (IMG-07)
Ghi chú: threshold tỉ lệ vì nút lớn có tolerance lớn hơn.
```

---

### R3-IMG08 — Icon placeholder / chưa load

```
Input:  A6.icon_regions.possible_placeholder  (từ A6 Icon Detector)
        (tùy chọn: A9.pattern_detections[type="broken_image"])
Điều kiện:
  icon_region.possible_placeholder == True
  Hoặc: A9 detect broken_image ở vùng trùng với icon element
Confidence: icon_region.confidence × 0.7
Severity nền: medium; range: low→high  (IMG-08)
Modifier ↑: placeholder nằm ở top-fold, là ảnh sản phẩm / avatar → high
Modifier ↓: icon nhỏ, decorative → low
Ghi chú: VLM G5 xác nhận "đây thật sự là icon vỡ hay icon thiết kế trông giống vậy".
```

---

### R3-IMG12 — Ảnh trùng lặp ngoài ý muốn

```
Input:  A10.duplicate_pairs  (từ A10 Perceptual Hash)
        elements[] để lấy context (role, position)
Điều kiện:
  pair.is_identical (hamming ≤ HASH_IDENTICAL=4) → fire MEDIUM
  pair.is_near_dup  (hamming ≤ HASH_NEAR_DUP=10) → fire LOW
  
  Loại trừ chủ ý:
    Nếu 2 element có cùng parent list-row (kiểu thumbnail list) → có thể ảnh mẫu → confidence thấp
    Nếu 2 element ở vị trí gần nhau trong list → likely chủ ý → confidence 0.3
    
Confidence: min(a.confidence, b.confidence) × (1 - hamming/64)
Severity nền: low; range: trivial→medium  (IMG-12)
Modifier ↑: cả 2 là hero image / banner → medium
Modifier ↓: icon trong list (lặp lại là bình thường) → trivial
```

---

## Phân chia trách nhiệm R3 vs A7/A9/A10

| Kiểm tra | Rule R3 | Analyzer output |
|---|---|---|
| Tính deviation | R3-IMG02 | A7 cấp intrinsic/displayed |
| Laplacian blur | R3-IMG03 | A7 cấp blur_score |
| Upscale ratio | R3-IMG03u | A7 cấp intrinsic/displayed |
| Icon centering | R3-IMG07 | A3/A6 cấp bbox |
| Placeholder detect | R3-IMG08 | A6 cấp possible_placeholder |
| Hash duplicate | R3-IMG12 | A10 cấp duplicate_pairs |

## Hạn chế (đánh dấu confidence thấp)

- A7 **yếu khi không có intrinsic size** → R3-IMG02/03u confidence thấp; fire với note.
- A10 **không phân biệt** trùng chủ ý (list thumbnail) vs trùng lỗi → VLM G5 xác nhận.

## Trạng thái: spec ✅ — phụ thuộc A7 implement (chưa có).
