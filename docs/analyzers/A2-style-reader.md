# A2 — Style Reader (computed-style → canonical `style`)

> Bóc tách chi tiết. Phase 1, nhóm "dựng cấu trúc". Tech: **Python**. **Mode A only.**
> Liên quan: [`A1-tree-parser.md`](A1-tree-parser.md) · [`../development-plan.md`](../development-plan.md)

## 1. Trách nhiệm
Nhận **computed-style** từ web capture (do A1 parse) → chuẩn hoá thành canonical `style`
object, và **tính các trị tất định KHÔNG cần pixel** — đáng giá nhất là **`contrast_ratio`
khi nền là màu đặc**. **KHÔNG đo pixel** (đó là A4/A8).

> ⚠ **Ranh giới (đính chính):** A2 chỉ chạy Mode A (có computed-style). Mode B (chỉ ảnh) và
> XML (android/ios — không có style) → field style do **A4** (màu/contrast từ pixel) + **A8**
> (font-size từ glyph) điền, **A0 Normalize** gộp. A2 KHÔNG gánh Mode B.

## 2. Input
- **Web capture** `style{}` mỗi node (từ A1): `fontSize, fontFamily, fontWeight, color,
  backgroundColor, opacity, borderRadius, zIndex, overflow, textOverflow, lineHeight,
  letterSpacing, textAlign, display, visibility, backgroundImage`.
- **XML android/ios:** gần như KHÔNG có style → A2 trả `style` rỗng + cờ "cần pixel".
→ A2 chủ yếu ăn theo **Web capture**.

## 3. Output — canonical `style` (chuẩn hoá, `source=dom`)
```jsonc
"style": {
  "font_size_px": 16, "font_size_pt": 12,
  "font_family": "Inter", "font_weight": 600,
  "color": [17,17,17],                 // RGB tuple đã chuẩn hoá
  "bg_color": [255,255,255], "bg_is_solid": true,   // bg hiệu dụng (đã kế thừa + blend)
  "contrast_ratio": 16.1,              // tính từ color+bg khi bg_is_solid; else null → A4 đo
  "opacity": 1.0, "border_radius": 4,
  "line_height": 24, "letter_spacing": 0, "text_align": "left",
  "overflow": "hidden", "text_overflow": "ellipsis",
  "truncation_styled": true,           // overflow:hidden + ellipsis ⇒ cắt CÓ CHỦ Ý
  "visible": true                      // display!=none & visibility!=hidden & opacity>0 & size>0
}
```

## 4. Kỹ thuật / lib (Python)
| Việc | Lib / cách | Ghi chú |
|---|---|---|
| Parse màu CSS → RGB | **`tinycss2.color3.parse_color`** (hex/rgb/rgba/hsl/named) | đã dùng ở A1; `webcolors` backup cho named |
| Contrast WCAG | **tự code** (relative luminance) | KHÔNG cần lib; tái dùng ở Rule R2 |
| Alpha blend (opacity / rgba) | tự code (`out = α·fg + (1-α)·bg`) | để ra bg/màu hiệu dụng trước khi tính contrast |
| Quy đổi px↔pt/dp | theo **bảng đơn vị F0.4** (cần chốt) | web: pt = px·72/96; mobile theo dpr |
| Resolve `inherit/currentColor/transparent` | traverse cây cha | xem mục 7 |

→ A2 thuần tính toán, **không CV/ML**.

## 5. Giá trị lớn: tính tất định KHÔNG cần pixel
- **`contrast_ratio` (WCAG)** khi `bg_is_solid`: lấy `color` + `bg_color` hiệu dụng → công
  thức relative-luminance → **bật ngay STY-01/02 ở Mode A, miễn pixel**. Nếu nền là
  ảnh/gradient/không xác định → `contrast_ratio=null` + cờ "cần A4 đo pixel".
- **bg kế thừa:** element bg trong suốt → truy `bg_color` của cha (lên dần) để ra nền hiệu
  dụng. *Điểm tinh tế hay sai — phải làm.*
- **`truncation_styled`:** `overflow:hidden`+`text-overflow:ellipsis` ⇒ biết cắt có chủ ý →
  giúp **TYP-03** phân biệt lỗi vs chủ ý.
- **`visible`:** tổng hợp display/visibility/opacity/size.

## 6. Tiêu chí phục vụ
STY-01/02 (contrast — Mode A tính thẳng), STY-03 (màu cho dark), STY-05 (opacity),
STY-07 (so màu disabled vs sibling), TYP-05 (font-size), TYP-03 (`truncation_styled`),
TYP-07 (line-height), TYP-10 (align), TYP-13 (font-mix qua font_family).

## 7. Edge cases
- `currentColor` / `inherit` / `transparent` → resolve theo cây cha.
- `rgba()` / `hsla()` alpha → blend với nền.
- `background-image` / gradient → `bg_is_solid=false` → contrast để A4.
- `em/rem/%` trong *computed*-style thường đã resolve ra px → ổn; nếu chưa, resolve theo cha.
- Element 0×0 hoặc `display:none` → `visible=false` nhưng vẫn giữ (cho occlusion/duplicate).

## 8. Open decisions (cần anh chốt)
- [ ] **F0.4 quy ước đơn vị** (px/pt/dp ↔ dpr) — A2 + Rule engine dùng chung. *(đề xuất: lưu
  cả `*_px` device-px và `*_pt`/`*_dp` logic; ngưỡng a11y so theo pt iOS / dp Android.)*
- [ ] Web Capture Contract phải include đủ style key ở mục 2 — chốt **cùng A1**.

## 9. TDD outline
- test parse màu hex/rgb/rgba/hsl/named → RGB.
- test contrast WCAG chuẩn (#000/#fff = 21.0; cặp 4.5 ranh giới).
- test bg kế thừa khi element trong suốt → lấy nền cha.
- test alpha blend khi opacity<1 / rgba.
- test `truncation_styled` từ overflow+ellipsis.
- test `visible` từ display/visibility/opacity/size.
- test XML input → `style` rỗng + cờ "cần pixel".

## Trạng thái: spec ✅ — phụ thuộc F0.4 (đơn vị) + Web Capture Contract (A1).
