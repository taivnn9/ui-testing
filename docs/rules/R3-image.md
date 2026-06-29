# R3 — Image Rules (ảnh + icon)

> **TL;DR:** Rule tất định về chất lượng/tỉ lệ ảnh & icon (méo, mờ, upscale, lệch tâm, placeholder, trùng lặp) — số học ratio + hash Hamming, dựa trên output A6/A7/A9/A10.

> **Nguồn dữ liệu:** `elements[].image_meta` (A7), role=image/icon, A6 (icon_regions), A9 (broken_image), A10 (hash duplicates).

## Danh sách rules

| Rule ID | Tiêu chí | Điều kiện fire | Severity nền (range) |
|---|---|---|---|
| `R3-IMG02` | Méo / sai tỉ lệ | deviation ratio > 0.05 (warn) / 0.15 (high) | medium (low→high) |
| `R3-IMG03` | Mờ / pixel hoá | `blur_score < BLUR_WARN×dpr` | medium (low→medium) |
| `R3-IMG03u` | Upscale (thiếu @2x/@3x) | `displayed_w > intrinsic_w × 1.5` | low (trivial→medium) |
| `R3-IMG07` | Icon lệch tâm trong nút | offset center > threshold | low (trivial→medium) |
| `R3-IMG08` | Icon placeholder / chưa load | `possible_placeholder=true` | medium (low→high) |
| `R3-IMG12` | Ảnh trùng lặp | hamming ≤ 4 (identical) / ≤ 10 (near-dup) | low (trivial→medium) |

Ngưỡng: `ASPECT_WARN`=0.05, `ASPECT_ERROR`=0.15, `BLUR_WARN`=50.0, `UPSCALE_RATIO`=1.5, `HASH_IDENTICAL`=4, `HASH_NEAR_DUP`=10.

---

## Chi tiết từng rule

### R3-IMG02 — Méo / sai tỉ lệ ảnh
- **Fire:** `intrinsic_ratio = intrinsic_w/intrinsic_h`; `displayed_ratio = displayed_w/displayed_h`; `deviation = |intrinsic_ratio - displayed_ratio| / intrinsic_ratio`.
  - `deviation > 0.15` → HIGH · `> 0.05` → MEDIUM
- **Confidence:** `elem.conf × 0.85` (A7 ước lượng intrinsic)
- **Modifier:** ↑ image người/sản phẩm + deviation>0.3 → high · ↑ logo/branding → high · ↓ icon ≤32px → low
- **Evidence:** `{intrinsic_ratio, displayed_ratio, deviation}`
- **Edge:** `scale_mode in ("fill","cover","tile")` → crop chủ ý, KHÔNG fire · `scale_mode="stretch"` → méo thật, fire · `image_meta=null` hoặc SVG vector → skip (agent reasoning Image xử lý).

### R3-IMG03 — Mờ / pixel hoá
- **Fire (Laplacian variance, scale theo dpr):** `effective_thresh = BLUR_WARN×dpr` (dpr1→50, 2→100, 3→150).
  - `blur_score < BLUR_CLEAR×dpr/2` → HIGH (rất mờ) · `< effective_thresh` → MEDIUM
- **Confidence:** `elem.conf × 0.75` (Laplacian nhạy với ảnh ít texture)
- **Modifier:** ↑ sản phẩm/người/banner → medium–high · ↓ background/icon nhỏ → low–trivial

### R3-IMG03u — Upscale (thiếu @2x/@3x asset)
- **Fire:** `displayed_w > intrinsic_w × 1.5` → pixel hoá. Bổ sung: `intrinsic_w < displayed_w × dpr` (thiếu asset đủ dpi, quan trọng trên @3x).
- **Confidence:** `elem.conf × 0.8`
- **Modifier:** ↑ banner/hero/sản phẩm → medium · **Tags:** resp, mob

### R3-IMG07 — Icon lệch tâm trong nút
- **Fire:** icon có parent role=button/tab/nav; `threshold = max(3.0, parent.w × 0.05)`; fire nếu `|icon_cx-parent_cx| > threshold` OR `|icon_cy-parent_cy| > threshold`.
- **Confidence:** `min(icon.conf, parent.conf) × 0.7` (threshold tỉ lệ — nút lớn tolerance lớn hơn).

### R3-IMG08 — Icon placeholder / chưa load
- **Fire:** `A6.icon_region.possible_placeholder=true`; hoặc A9 detect broken_image trùng vùng icon.
- **Confidence:** `icon_region.conf × 0.7`
- **Modifier:** ↑ placeholder top-fold, ảnh sản phẩm/avatar → high · ↓ icon nhỏ decorative → low
- **Ghi chú:** agent reasoning Image xác nhận "icon vỡ thật hay thiết kế trông giống vậy".

### R3-IMG12 — Ảnh trùng lặp ngoài ý muốn
- **Fire (A10.duplicate_pairs):** `hamming ≤ 4` (identical) → MEDIUM · `≤ 10` (near-dup) → LOW.
  - **Loại trừ chủ ý:** cùng parent list-row / gần nhau trong list (thumbnail mẫu) → conf 0.3.
- **Confidence:** `min(a.conf, b.conf) × (1 - hamming/64)`
- **Modifier:** ↑ cả 2 là hero/banner → medium · ↓ icon trong list (lặp bình thường) → trivial

---

## Phân chia trách nhiệm R3 vs analyzer

| Kiểm tra | Rule R3 | Analyzer cấp |
|---|---|---|
| Deviation tỉ lệ | R3-IMG02 | A7 intrinsic/displayed |
| Laplacian blur | R3-IMG03 | A7 blur_score |
| Upscale ratio | R3-IMG03u | A7 intrinsic/displayed |
| Icon centering | R3-IMG07 | A3/A6 bbox |
| Placeholder | R3-IMG08 | A6 possible_placeholder |
| Hash duplicate | R3-IMG12 | A10 duplicate_pairs |

## Hạn chế (confidence thấp, fire kèm note)
- A7 yếu khi thiếu intrinsic size → R3-IMG02/03u confidence thấp.
- A10 không phân biệt trùng chủ ý (list thumbnail) vs lỗi → agent reasoning Image xác nhận.

## Trạng thái: spec ✅ — phụ thuộc A7 implement (chưa có).
