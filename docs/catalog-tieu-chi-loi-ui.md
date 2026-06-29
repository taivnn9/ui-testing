# Catalog tiêu chí lỗi UI

> **TL;DR:** Danh mục đầy đủ **121 tiêu chí** lỗi UI/UX (9 nhóm domain) cho hệ thống zero-reference, kèm thang **severity 5 mức** và bộ **tag trực giao**. Bản tóm tắt quyết định gọn ở `../CLAUDE.md`.

## 1. Thang severity (5 mức)

| Mức | Nghĩa |
|---|---|
| `critical` | Chặn hoàn toàn: mất chức năng chính / màn không dùng được. |
| `high` | Nặng: ảnh hưởng rõ tới thao tác & đọc hiểu, vẫn xoay sở được. |
| `medium` | Gây khó chịu / giảm tin cậy, không cản trở tác vụ. |
| `low` | Nhỏ, phải để ý mới thấy. |
| `trivial` | Thẩm mỹ cực nhỏ, gần như bỏ qua được. |

Mỗi tiêu chí ghi **severity nền** (mức điển hình) + **range** (khoảng dao động). Mức cuối phụ thuộc phần tử bị dính (vd chữ cắt cụt ở tagline = trivial, ở nút "Thanh toán" = critical).

## 2. Tag trực giao

| Tag | Nghĩa |
|---|---|
| `a11y` | Trợ năng (contrast, touch target, color-only, focus...). |
| `i18n` | Đa ngôn ngữ/localization (dịch, định dạng, RTL, glyph). |
| `dark` | Dark-mode / chuyển theme. |
| `resp` | Responsive / kích thước màn / breakpoint. |
| `mob` | Chủ yếu mobile. |
| `web` | Chủ yếu web. |
| `multi` | Cần **so nhiều ảnh** mới phát hiện (không bắt từ 1 ảnh). |
| `ctx` | Cần **ngữ cảnh / intent** màn hình (khó nhất với zero-reference). |

## 3. Khung 9 nhóm domain

| Nhóm (ID) | Bản chất |
|---|---|
| **Content & Semantics** (`CNT`) | Nội dung text *nói gì* — đúng/sai, đã render chưa. |
| **Typography & Text Rendering** (`TYP`) | Text *trông thế nào* — cách vẽ chữ. |
| **Color, Contrast & Visual Style** (`STY`) | Màu sắc, tương phản, style. |
| **Layout & Spatial Geometry** (`LAY`) | Hình học / bố cục. |
| **Images, Icons & Media** (`IMG`) | Ảnh / icon / media / branding. |
| **UI Components & Controls** (`CMP`) | Phần tử tương tác. |
| **State & Lifecycle** (`STATE`) | Trạng thái màn theo thời gian (gồm motion). |
| **Platform & Environment** (`ENV`) | Phụ thuộc thiết bị / môi trường. |
| **Consistency xuyên màn** (`CONS`) | Nhất quán giữa nhiều phần tử / màn (đều cần `multi`). |

## 4. Catalog 121 tiêu chí

### A — Content & Semantics (`CNT`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| CNT-01 | Placeholder/biến chưa render (`undefined`,`NaN`,`%s`,`{{user.name}}`,`${x}`) | high (med–crit) | |
| CNT-02 | i18n key lòi ra chưa dịch (`home.title`, `btn_submit`) | high (med–crit) | i18n |
| CNT-03 | Sai/lẫn ngôn ngữ (text Anh trong bản Việt) | medium (low–high) | i18n |
| CNT-04 | Lorem ipsum / placeholder copy ("Your text here") | high (med–high) | |
| CNT-05 | Text debug/nội bộ lòi ("asdf","TEST","DO NOT SHIP") | high (med–crit) | |
| CNT-06 | Mojibake / entity thô (`Ã©`, `â€™`, `&amp;`, `&#39;`) | medium (low–high) | i18n |
| CNT-07 | Ký tự escape lòi như text (`\n`, `\t`, `<br>`) | medium (low–high) | |
| CNT-08 | Số/ngày/tiền sai định dạng locale (epoch thô, `1234567.89`) | medium (low–high) | i18n |
| CNT-09 | Lỗi chính tả / ngữ pháp | low (triv–med) | ctx |
| CNT-10 | Nội dung sai ngữ cảnh / sai nhãn / dữ liệu nhầm user | high (med–crit) | ctx, multi |
| CNT-11 | Text trùng lặp / mâu thuẫn (giá hiển thị 2 chỗ khác nhau) | medium (low–high) | ctx |
| CNT-12 | Đơn vị/ký hiệu sai hoặc thiếu (thiếu ký hiệu tiền tệ) | medium (low–high) | i18n |
| CNT-13 | Giá trị vô lý ("0 sản phẩm" nhưng list có item, số âm sai chỗ) | medium (low–high) | ctx |
| CNT-14 | Văn bản pháp lý/cảnh báo thiếu hoặc sai (disclaimer) | high (med–crit) | ctx |

### B — Typography & Text Rendering (`TYP`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| TYP-01 | Tofu / glyph thiếu (□ ▯ — dấu tiếng Việt, emoji, CJK không hỗ trợ) | high (med–crit) | i18n |
| TYP-02 | Font chưa load / fallback sai (FOUT/FOIT, mất font brand) | medium (low–med) | |
| TYP-03 | Chữ tràn/cắt cụt khỏi container (unintended) | medium (triv–crit) | i18n, ctx |
| TYP-04 | Chữ đè lên chữ / đè phần tử khác | high (med–crit) | |
| TYP-05 | Cỡ chữ quá nhỏ (dưới ngưỡng đọc được) | medium (low–high) | a11y |
| TYP-06 | Ngắt dòng xấu (gãy giữa từ, 1 từ dài tràn, mồ côi) | low (triv–med) | |
| TYP-07 | Line-height sai (dòng dính nhau / cách quá xa) | low (triv–med) | |
| TYP-08 | Letter/word-spacing vỡ (kerning lỗi, giãn chữ bất thường) | low (triv–med) | |
| TYP-09 | Chữ mờ / vỡ / răng cưa (render scale lẻ) | medium (low–med) | resp |
| TYP-10 | Căn lề text sai (center nơi đáng left, justify tạo khe trắng) | low (triv–med) | |
| TYP-11 | Casing/transform sai (ALL CAPS sai chỗ) | low (triv–med) | |
| TYP-12 | RTL/bidi hỏng (Ả Rập/Do Thái sai chiều, dấu câu lệch) | high (med–crit) | i18n |
| TYP-13 | Trộn nhiều font không chủ ý trong cùng cụm | low (triv–med) | multi |
| TYP-14 | Emoji/icon-font render sai (emoji thành box, mất màu) | low (triv–med) | i18n |

### C — Color, Contrast & Visual Style (`STY`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| STY-01 | Contrast chữ/nền < WCAG (4.5:1 thường, 3:1 chữ lớn) | high (med–high) | a11y |
| STY-02 | Chữ tàng hình — cùng màu nền (trắng/trắng) | critical (high–crit) | a11y, dark |
| STY-03 | Dark-mode không đổi màu (màu hardcode, chữ tối nền tối) | high (med–crit) | dark |
| STY-04 | Icon/viền tàng hình trong theme (icon đen nền đen dark-mode) | high (med–crit) | dark, a11y |
| STY-05 | Opacity sai (phần tử mờ/trong suốt ngoài ý muốn) | medium (low–high) | |
| STY-06 | Lệch bảng màu / sai màu brand | low (triv–med) | multi |
| STY-07 | Disabled không phân biệt enabled (hoặc ngược lại) | medium (low–high) | a11y |
| STY-08 | Trạng thái focus/selected không nhìn thấy | medium (low–high) | a11y |
| STY-09 | Thông tin chỉ truyền bằng màu (color-only, không icon/label) | medium (low–med) | a11y |
| STY-10 | Gradient/shadow/blur lỗi render (banding, viền cứng, bóng lệch) | low (triv–med) | |
| STY-11 | Viền/divider thiếu, thừa, hoặc nhân đôi | low (triv–med) | |
| STY-12 | Màu nền sai vùng (vùng đáng trong suốt lại nền đặc) | medium (low–high) | |
| STY-13 | Tương phản icon/đồ hoạ chức năng < 3:1 | medium (low–high) | a11y |

### D — Layout & Spatial Geometry (`LAY`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| LAY-01 | Overlap / va chạm phần tử vô lý | high (med–crit) | |
| LAY-02 | Off-screen / cắt mép viewport | high (med–crit) | resp |
| LAY-03 | Tràn ra ngoài container cha (overflow) | medium (low–high) | i18n |
| LAY-04 | Lệch grid (không theo 8pt) / spacing không đều | low (triv–med) | |
| LAY-05 | Lệch optical alignment / lệch mép giữa phần tử | low (triv–med) | |
| LAY-06 | Z-order / occlusion (bị che sau phần tử khác / modal) | high (med–crit) | |
| LAY-07 | Quá chật / quá nhiều khoảng trắng (gap bất thường) | low (triv–med) | |
| LAY-08 | Lệch tâm / căn giữa sai | low (triv–med) | |
| LAY-09 | Reflow/wrap vỡ (responsive — cột sập, rớt dòng xấu) | high (med–crit) | resp, web |
| LAY-10 | Scroll lỗi (cắt không cuộn được, double scrollbar, scroll ngang ngoài ý) | high (med–crit) | resp |
| LAY-11 | Sticky/fixed đè nội dung (header/footer dính che) | medium (low–high) | |
| LAY-12 | Tỉ lệ / kích thước container sai (1 khối phình/teo bất thường) | medium (low–high) | |
| LAY-13 | Vùng trống bất thường (khoảng trống lớn giữa màn) | low (triv–med) | ctx |
| LAY-14 | Phần tử chồng vị trí (2 cái cùng toạ độ) | medium (low–high) | |
| LAY-15 | Thứ tự / trật tự sắp xếp sai (list lộn xộn, thứ tự đảo) | medium (low–high) | ctx |

### E — Images, Icons & Media (`IMG`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| IMG-01 | Ảnh vỡ / broken (icon hỏng, ô trống, alt text lòi) | high (med–crit) | |
| IMG-02 | Méo / sai tỉ lệ (kéo giãn/bóp — render ratio ≠ intrinsic) | medium (low–high) | |
| IMG-03 | Mờ / pixel hoá (upscale, thiếu @2x/@3x) | medium (low–med) | resp |
| IMG-04 | Crop sai (cắt mất phần quan trọng — mặt người, chữ trên ảnh) | medium (low–high) | ctx |
| IMG-05 | Thiếu ảnh (slot trống nơi đáng có ảnh) | medium (low–high) | |
| IMG-06 | Icon sai / không đúng ngữ nghĩa | medium (low–high) | ctx |
| IMG-07 | Icon lệch tâm trong nút / lệch baseline với label | low (triv–med) | |
| IMG-08 | Icon placeholder / chưa load (ô vuông, dấu ?) | medium (low–high) | |
| IMG-09 | Scale-mode sai (cover ↔ contain → méo hoặc cắt) | medium (low–high) | |
| IMG-10 | Ảnh/logo sai phiên bản, lộn brand | medium (low–high) | ctx, multi |
| IMG-11 | Logo / branding mờ, sai màu, sai tỉ lệ | low (triv–med) | |
| IMG-12 | Ảnh trùng lặp ngoài ý muốn | low (triv–med) | |
| IMG-13 | Media poster / thumbnail vỡ (video) | medium (low–high) | |
| IMG-14 | Ảnh load dở (chỉ 1 phần, progressive kẹt) | medium (low–med) | |
| IMG-15 | Ảnh không khớp nội dung (sai ảnh sản phẩm) | high (med–crit) | ctx |

### F — UI Components & Controls (`CMP`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| CMP-01 | Touch target nhỏ (<44pt iOS / 48dp Android) | high (med–high) | a11y, mob |
| CMP-02 | Nút/control không nhãn (icon-only, không text/aria) | medium (low–high) | a11y |
| CMP-03 | Không tap được do bị đè (phần tử trên chặn) | critical (high–crit) | |
| CMP-04 | Control sai state (toggle kẹt, checkbox sai, radio chọn nhiều) | high (med–crit) | ctx |
| CMP-05 | Trùng component (2 nút giống hệt) | medium (low–high) | ctx |
| CMP-06 | Thiếu component kỳ vọng (không có submit / back) | high (med–crit) | ctx |
| CMP-07 | Input: không thấy focus, label đè value, placeholder nhầm value | medium (low–high) | a11y |
| CMP-08 | Text nút / label bị cắt cụt | medium (low–high) | i18n |
| CMP-09 | Disabled sai (đáng enable lại disable / ngược lại) | high (med–crit) | ctx |
| CMP-10 | Control lệch hàng / không thẳng trong nhóm | low (triv–med) | |
| CMP-11 | Dropdown / menu / tooltip render lòi ra ngoài màn | medium (low–high) | resp |
| CMP-12 | Progress / loading indicator sai hoặc kẹt | medium (low–high) | |
| CMP-13 | Badge / notification count sai vị trí / tràn (99+) | low (triv–med) | |
| CMP-14 | Tab / segmented không rõ cái đang chọn | medium (low–high) | a11y |
| CMP-15 | Kích thước component không nhất quán (cùng nút khác cỡ) | low (triv–med) | multi |
| CMP-16 | Khoảng tap chồng nhau (2 control quá sát) | medium (low–high) | a11y, mob |
| CMP-17 | Scroll / swipe affordance thiếu (không biết cuộn được) | low (triv–med) | ctx |

### G — State & Lifecycle (`STATE`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| STATE-01 | Skeleton / loading kẹt (shimmer mãi không xong) | high (med–crit) | |
| STATE-02 | Empty state trống trơn / không có thông báo trống | medium (low–high) | ctx |
| STATE-03 | Error state lòi raw error / stack trace / mã lỗi thô | high (med–crit) | |
| STATE-04 | Render dở dang (một phần load, một phần chưa) | medium (low–high) | |
| STATE-05 | Dữ liệu cũ / placeholder còn sót (stale data) | medium (low–high) | ctx |
| STATE-06 | Spinner / overlay đè nội dung không tắt | medium (low–high) | |
| STATE-07 | Modal / toast / snackbar kẹt, không tự tắt, hoặc đè sai | medium (low–high) | |
| STATE-08 | Pull-to-refresh / pagination kẹt hoặc nhân đôi item | medium (low–high) | mob |
| STATE-09 | Animation / transition kẹt giữa chừng (frame dở) — *motion* | low (triv–med) | |
| STATE-10 | Trạng thái không khớp dữ liệu (badge "3" nhưng list rỗng) | medium (low–high) | ctx, multi |
| STATE-11 | Offline / no-network không xử lý (màn trắng) | high (med–crit) | ctx |

### H — Platform & Environment (`ENV`)

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| ENV-01 | Safe-area / notch che nội dung (tai thỏ, dynamic island) | high (med–crit) | mob |
| ENV-02 | Status bar / system nav bar đè hoặc lẫn màu | medium (low–high) | mob |
| ENV-03 | Home indicator (iOS) đè nút dưới cùng | medium (low–high) | mob |
| ENV-04 | Bàn phím che ô input / nút submit | high (med–crit) | mob |
| ENV-05 | Landscape / xoay màn vỡ layout | medium (low–high) | resp, mob |
| ENV-06 | Font-scale / Dynamic Type lớn làm vỡ layout | high (med–crit) | a11y, mob |
| ENV-07 | Vỡ ở kích thước / độ phân giải thiết bị khác (nhỏ/lớn) | medium (low–high) | resp |
| ENV-08 | Web responsive breakpoint vỡ (tablet / desktop) | high (med–crit) | resp, web |
| ENV-09 | Viewport-unit / 100vh lỗi do thanh trình duyệt mobile | medium (low–high) | resp, web |
| ENV-10 | Asset không đúng mật độ (@1x trên màn @3x → mờ) — *nguyên nhân của IMG-03* | low (triv–med) | mob |
| ENV-11 | Foldable / cutout / multi-window vỡ | low (triv–med) | mob |
| ENV-12 | Hover/cursor lỗi (web) / hover-only không tap được (mobile) | low (triv–med) | web |
| ENV-13 | Splash / launch screen kẹt hoặc sai tỉ lệ | medium (low–high) | mob |

### I — Consistency xuyên màn (`CONS`) — *toàn bộ cần `multi`*

| ID | Tiêu chí (ví dụ) | Sev nền (range) | Tags |
|---|---|---|---|
| CONS-01 | Cùng component khác kích cỡ giữa các màn | low (triv–med) | multi |
| CONS-02 | Lệch font (family/size/weight) giữa các màn | low (triv–med) | multi |
| CONS-03 | Lệch bảng màu / theme drift | low (triv–med) | multi |
| CONS-04 | Icon khác phong cách (outline lẫn filled) | low (triv–med) | multi |
| CONS-05 | Thuật ngữ / label không nhất quán cho cùng hành động ("Đăng xuất" vs "Thoát") | medium (low–high) | multi, ctx |
| CONS-06 | Spacing system không nhất quán giữa các màn | low (triv–low) | multi |
| CONS-07 | Định dạng số / ngày / tiền khác nhau giữa các màn | medium (low–high) | multi, i18n |
| CONS-08 | Vị trí phần tử chung lệch (nút back lúc trái lúc phải) | medium (low–high) | multi |
| CONS-09 | Phong cách ảnh không đồng nhất (tỉ lệ / bo góc / filter khác) | low (triv–med) | multi |

---

**Tổng: 121 tiêu chí / 9 nhóm** (A/B/C: 41 · D/E/F: 47 · G/H/I: 33).
Chi tiết dữ liệu · kỹ thuật · điều kiện đạt/không đạt cho từng tiêu chí: [`tieu-chi/`](tieu-chi/README.md) (sinh bởi `scripts/gen_criteria.py`).
