# Tổng hợp tiêu chí đánh giá lỗi UI

**121 tiêu chí / 9 nhóm.** Mỗi tiêu chí có file chi tiết riêng (dữ liệu · kỹ thuật · đạt/không đạt). _Sinh tự động bởi `scripts/gen_criteria.py`._

**Cột Triển khai (đối chiếu code thực):** 🟦 rule = code tất định emit candidate · 🟥 agent = chỉ agent Codex (chưa có rule) · ⏳ chưa = cần nhìn ảnh/đa ảnh/tương tác (Phase 2).

Liên quan: [`../catalog-tieu-chi-loi-ui.md`](../catalog-tieu-chi-loi-ui.md) (danh sách gốc), [`../F0.4-thresholds.md`](../F0.4-thresholds.md) (ngưỡng), [`../F1.1-codex-cli-architecture.md`](../F1.1-codex-cli-architecture.md) (kiến trúc reasoning).

> **Độ phủ thực tế:** 🟦 có rule tất định **40** · 🟥 chỉ agent Codex **55** · ⏳ chưa xử lý **26** / 121.

## CNT — Content & Semantics — nội dung text nói gì

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `CNT-01` | Placeholder/biến chưa render | high | 🟦 rule | [CNT-01.md](CNT-01.md) |
| `CNT-02` | i18n key lòi ra chưa dịch | high | 🟦 rule | [CNT-02.md](CNT-02.md) |
| `CNT-03` | Sai/lẫn ngôn ngữ | medium | 🟥 agent | [CNT-03.md](CNT-03.md) |
| `CNT-04` | Lorem ipsum / placeholder copy | high | 🟦 rule | [CNT-04.md](CNT-04.md) |
| `CNT-05` | Text debug/nội bộ lòi | high | 🟦 rule | [CNT-05.md](CNT-05.md) |
| `CNT-06` | Mojibake / entity thô | medium | 🟦 rule | [CNT-06.md](CNT-06.md) |
| `CNT-07` | Ký tự escape lòi như text | medium | 🟦 rule | [CNT-07.md](CNT-07.md) |
| `CNT-08` | Số/ngày/tiền sai định dạng locale | medium | 🟦 rule | [CNT-08.md](CNT-08.md) |
| `CNT-09` | Lỗi chính tả / ngữ pháp | low | 🟥 agent | [CNT-09.md](CNT-09.md) |
| `CNT-10` | Nội dung sai ngữ cảnh / nhầm dữ liệu user | high | 🟥 agent | [CNT-10.md](CNT-10.md) |
| `CNT-11` | Text trùng lặp / mâu thuẫn | medium | 🟥 agent | [CNT-11.md](CNT-11.md) |
| `CNT-12` | Đơn vị/ký hiệu sai hoặc thiếu | medium | 🟥 agent | [CNT-12.md](CNT-12.md) |
| `CNT-13` | Giá trị vô lý | medium | 🟥 agent | [CNT-13.md](CNT-13.md) |
| `CNT-14` | Văn bản pháp lý/cảnh báo thiếu/sai | high | 🟥 agent | [CNT-14.md](CNT-14.md) |

## TYP — Typography & Text Rendering — text trông thế nào

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `TYP-01` | Tofu / glyph thiếu | high | 🟦 rule | [TYP-01.md](TYP-01.md) |
| `TYP-02` | Font chưa load / fallback sai | medium | 🟥 agent | [TYP-02.md](TYP-02.md) |
| `TYP-03` | Chữ tràn/cắt cụt khỏi container | medium | 🟦 rule | [TYP-03.md](TYP-03.md) |
| `TYP-04` | Chữ đè lên chữ / phần tử khác | high | 🟥 agent | [TYP-04.md](TYP-04.md) |
| `TYP-05` | Cỡ chữ quá nhỏ | medium | 🟦 rule | [TYP-05.md](TYP-05.md) |
| `TYP-06` | Ngắt dòng xấu | low | 🟥 agent | [TYP-06.md](TYP-06.md) |
| `TYP-07` | Line-height sai | low | ⏳ chưa | [TYP-07.md](TYP-07.md) |
| `TYP-08` | Letter/word-spacing vỡ | low | ⏳ chưa | [TYP-08.md](TYP-08.md) |
| `TYP-09` | Chữ mờ / vỡ / răng cưa | medium | 🟦 rule | [TYP-09.md](TYP-09.md) |
| `TYP-10` | Căn lề text sai | low | 🟥 agent | [TYP-10.md](TYP-10.md) |
| `TYP-11` | Casing/transform sai | low | 🟥 agent | [TYP-11.md](TYP-11.md) |
| `TYP-12` | RTL/bidi hỏng | high | 🟥 agent | [TYP-12.md](TYP-12.md) |
| `TYP-13` | Trộn nhiều font không chủ ý | low | 🟥 agent | [TYP-13.md](TYP-13.md) |
| `TYP-14` | Emoji/icon-font render sai | low | 🟦 rule | [TYP-14.md](TYP-14.md) |

## STY — Color, Contrast & Visual Style — màu, tương phản, style

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `STY-01` | Contrast chữ/nền < WCAG | high | 🟦 rule | [STY-01.md](STY-01.md) |
| `STY-02` | Chữ tàng hình (cùng màu nền) | critical | 🟦 rule | [STY-02.md](STY-02.md) |
| `STY-03` | Dark-mode không đổi màu | high | 🟦 rule | [STY-03.md](STY-03.md) |
| `STY-04` | Icon/viền tàng hình trong theme | high | 🟦 rule | [STY-04.md](STY-04.md) |
| `STY-05` | Opacity sai | medium | 🟦 rule | [STY-05.md](STY-05.md) |
| `STY-06` | Lệch bảng màu / sai màu brand | low | ⏳ chưa | [STY-06.md](STY-06.md) |
| `STY-07` | Disabled không phân biệt enabled | medium | 🟥 agent | [STY-07.md](STY-07.md) |
| `STY-08` | Focus/selected không nhìn thấy | medium | 🟥 agent | [STY-08.md](STY-08.md) |
| `STY-09` | Thông tin chỉ truyền bằng màu | medium | 🟥 agent | [STY-09.md](STY-09.md) |
| `STY-10` | Gradient/shadow/blur lỗi render | low | 🟦 rule | [STY-10.md](STY-10.md) |
| `STY-11` | Viền/divider thiếu/thừa/đôi | low | 🟥 agent | [STY-11.md](STY-11.md) |
| `STY-12` | Màu nền sai vùng | medium | 🟥 agent | [STY-12.md](STY-12.md) |
| `STY-13` | Contrast icon/đồ hoạ chức năng < 3:1 | medium | 🟦 rule | [STY-13.md](STY-13.md) |

## LAY — Layout & Spatial Geometry — bố cục, hình học

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `LAY-01` | Overlap / va chạm phần tử vô lý | high | 🟦 rule | [LAY-01.md](LAY-01.md) |
| `LAY-02` | Off-screen / cắt mép viewport | high | 🟦 rule | [LAY-02.md](LAY-02.md) |
| `LAY-03` | Tràn ra ngoài container cha | medium | 🟦 rule | [LAY-03.md](LAY-03.md) |
| `LAY-04` | Lệch grid (không theo 8pt) | low | 🟥 agent | [LAY-04.md](LAY-04.md) |
| `LAY-05` | Lệch optical alignment | low | 🟥 agent | [LAY-05.md](LAY-05.md) |
| `LAY-06` | Z-order / occlusion | high | 🟥 agent | [LAY-06.md](LAY-06.md) |
| `LAY-07` | Quá chật / quá nhiều khoảng trắng | low | 🟥 agent | [LAY-07.md](LAY-07.md) |
| `LAY-08` | Lệch tâm / căn giữa sai | low | 🟥 agent | [LAY-08.md](LAY-08.md) |
| `LAY-09` | Reflow/wrap vỡ (responsive) | high | ⏳ chưa | [LAY-09.md](LAY-09.md) |
| `LAY-10` | Scroll lỗi | high | ⏳ chưa | [LAY-10.md](LAY-10.md) |
| `LAY-11` | Sticky/fixed đè nội dung | medium | 🟥 agent | [LAY-11.md](LAY-11.md) |
| `LAY-12` | Tỉ lệ / kích thước container sai | medium | 🟥 agent | [LAY-12.md](LAY-12.md) |
| `LAY-13` | Vùng trống bất thường | low | 🟥 agent | [LAY-13.md](LAY-13.md) |
| `LAY-14` | Phần tử chồng vị trí (cùng toạ độ) | medium | 🟦 rule | [LAY-14.md](LAY-14.md) |
| `LAY-15` | Thứ tự sắp xếp sai | medium | 🟥 agent | [LAY-15.md](LAY-15.md) |

## IMG — Images, Icons & Media — ảnh, icon, media

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `IMG-01` | Ảnh vỡ / broken | high | 🟦 rule | [IMG-01.md](IMG-01.md) |
| `IMG-02` | Méo / sai tỉ lệ | medium | 🟥 agent | [IMG-02.md](IMG-02.md) |
| `IMG-03` | Mờ / pixel hoá | medium | 🟦 rule | [IMG-03.md](IMG-03.md) |
| `IMG-04` | Crop sai (cắt mất phần quan trọng) | medium | ⏳ chưa | [IMG-04.md](IMG-04.md) |
| `IMG-05` | Thiếu ảnh (slot trống) | medium | 🟦 rule | [IMG-05.md](IMG-05.md) |
| `IMG-06` | Icon sai ngữ nghĩa | medium | 🟥 agent | [IMG-06.md](IMG-06.md) |
| `IMG-07` | Icon lệch tâm trong nút | low | 🟦 rule | [IMG-07.md](IMG-07.md) |
| `IMG-08` | Icon placeholder / chưa load | medium | 🟦 rule | [IMG-08.md](IMG-08.md) |
| `IMG-09` | Scale-mode sai | medium | 🟥 agent | [IMG-09.md](IMG-09.md) |
| `IMG-10` | Sai phiên bản / lộn brand | medium | ⏳ chưa | [IMG-10.md](IMG-10.md) |
| `IMG-11` | Logo mờ/sai màu/tỉ lệ | low | ⏳ chưa | [IMG-11.md](IMG-11.md) |
| `IMG-12` | Ảnh trùng lặp ngoài ý muốn | low | 🟦 rule | [IMG-12.md](IMG-12.md) |
| `IMG-13` | Poster/thumbnail video vỡ | medium | 🟥 agent | [IMG-13.md](IMG-13.md) |
| `IMG-14` | Ảnh load dở (progressive kẹt) | medium | 🟦 rule | [IMG-14.md](IMG-14.md) |
| `IMG-15` | Ảnh không khớp nội dung | high | ⏳ chưa | [IMG-15.md](IMG-15.md) |

## CMP — UI Components & Controls — thành phần điều khiển

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `CMP-01` | Touch target nhỏ | high | 🟦 rule | [CMP-01.md](CMP-01.md) |
| `CMP-02` | Control không nhãn | medium | 🟥 agent | [CMP-02.md](CMP-02.md) |
| `CMP-03` | Không tap được do bị đè | critical | 🟥 agent | [CMP-03.md](CMP-03.md) |
| `CMP-04` | Control sai state | high | 🟥 agent | [CMP-04.md](CMP-04.md) |
| `CMP-05` | Trùng component | medium | 🟥 agent | [CMP-05.md](CMP-05.md) |
| `CMP-06` | Thiếu component kỳ vọng | high | 🟥 agent | [CMP-06.md](CMP-06.md) |
| `CMP-07` | Input lỗi (label/focus/placeholder) | medium | 🟥 agent | [CMP-07.md](CMP-07.md) |
| `CMP-08` | Text nút / label bị cắt cụt | medium | 🟥 agent | [CMP-08.md](CMP-08.md) |
| `CMP-09` | Disabled sai | high | 🟥 agent | [CMP-09.md](CMP-09.md) |
| `CMP-10` | Control lệch hàng trong nhóm | low | 🟥 agent | [CMP-10.md](CMP-10.md) |
| `CMP-11` | Dropdown/menu/tooltip lòi ra ngoài màn | medium | 🟥 agent | [CMP-11.md](CMP-11.md) |
| `CMP-12` | Progress/loading indicator sai/kẹt | medium | 🟦 rule | [CMP-12.md](CMP-12.md) |
| `CMP-13` | Badge/notification count sai vị trí/tràn | low | 🟥 agent | [CMP-13.md](CMP-13.md) |
| `CMP-14` | Tab/segment không rõ cái đang chọn | medium | 🟥 agent | [CMP-14.md](CMP-14.md) |
| `CMP-15` | Component khác cỡ (cùng loại) | low | ⏳ chưa | [CMP-15.md](CMP-15.md) |
| `CMP-16` | Khoảng tap chồng nhau | medium | 🟦 rule | [CMP-16.md](CMP-16.md) |
| `CMP-17` | Thiếu affordance cuộn/swipe | low | 🟥 agent | [CMP-17.md](CMP-17.md) |

## STATE — State & Lifecycle — trạng thái màn

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `STATE-01` | Skeleton / loading kẹt | high | 🟦 rule | [STATE-01.md](STATE-01.md) |
| `STATE-02` | Empty state trống trơn | medium | 🟥 agent | [STATE-02.md](STATE-02.md) |
| `STATE-03` | Error/stack trace lòi | high | 🟦 rule | [STATE-03.md](STATE-03.md) |
| `STATE-04` | Render dở dang | medium | 🟥 agent | [STATE-04.md](STATE-04.md) |
| `STATE-05` | Stale data / placeholder còn sót | medium | 🟥 agent | [STATE-05.md](STATE-05.md) |
| `STATE-06` | Spinner/overlay đè không tắt | medium | 🟦 rule | [STATE-06.md](STATE-06.md) |
| `STATE-07` | Modal/toast/snackbar kẹt | medium | 🟥 agent | [STATE-07.md](STATE-07.md) |
| `STATE-08` | Pull-refresh/pagination kẹt | medium | 🟥 agent | [STATE-08.md](STATE-08.md) |
| `STATE-09` | Animation/transition kẹt giữa chừng | low | ⏳ chưa | [STATE-09.md](STATE-09.md) |
| `STATE-10` | Trạng thái không khớp dữ liệu | medium | 🟥 agent | [STATE-10.md](STATE-10.md) |
| `STATE-11` | Offline / no-network không xử lý | high | 🟥 agent | [STATE-11.md](STATE-11.md) |

## ENV — Platform & Environment — nền tảng, môi trường

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `ENV-01` | Safe-area / notch che nội dung | high | 🟦 rule | [ENV-01.md](ENV-01.md) |
| `ENV-02` | Status/nav bar đè hoặc lẫn màu | medium | 🟦 rule | [ENV-02.md](ENV-02.md) |
| `ENV-03` | Home indicator (iOS) đè nút | medium | 🟦 rule | [ENV-03.md](ENV-03.md) |
| `ENV-04` | Bàn phím che input/submit | high | 🟦 rule | [ENV-04.md](ENV-04.md) |
| `ENV-05` | Landscape / xoay màn vỡ layout | medium | ⏳ chưa | [ENV-05.md](ENV-05.md) |
| `ENV-06` | Font-scale lớn làm vỡ layout | high | 🟥 agent | [ENV-06.md](ENV-06.md) |
| `ENV-07` | Vỡ ở thiết bị/độ phân giải khác | medium | ⏳ chưa | [ENV-07.md](ENV-07.md) |
| `ENV-08` | Web responsive breakpoint vỡ | high | ⏳ chưa | [ENV-08.md](ENV-08.md) |
| `ENV-09` | Viewport-unit / 100vh lỗi mobile | medium | ⏳ chưa | [ENV-09.md](ENV-09.md) |
| `ENV-10` | Asset không đúng mật độ (@1x) | low | 🟥 agent | [ENV-10.md](ENV-10.md) |
| `ENV-11` | Foldable / cutout / multi-window vỡ | low | ⏳ chưa | [ENV-11.md](ENV-11.md) |
| `ENV-12` | Hover/cursor lỗi (web) / hover-only (mobile) | low | ⏳ chưa | [ENV-12.md](ENV-12.md) |
| `ENV-13` | Splash / launch screen kẹt/sai tỉ lệ | medium | 🟥 agent | [ENV-13.md](ENV-13.md) |

## CONS — Consistency xuyên màn — cần nhiều ảnh

| ID | Tiêu chí | Sev | Triển khai | Chi tiết |
|---|---|---|---|---|
| `CONS-01` | Component khác cỡ giữa các màn | low | ⏳ chưa | [CONS-01.md](CONS-01.md) |
| `CONS-02` | Lệch font giữa các màn | low | ⏳ chưa | [CONS-02.md](CONS-02.md) |
| `CONS-03` | Lệch bảng màu / theme drift | low | ⏳ chưa | [CONS-03.md](CONS-03.md) |
| `CONS-04` | Icon khác phong cách | low | ⏳ chưa | [CONS-04.md](CONS-04.md) |
| `CONS-05` | Thuật ngữ/label không nhất quán | medium | ⏳ chưa | [CONS-05.md](CONS-05.md) |
| `CONS-06` | Spacing system không nhất quán | low | ⏳ chưa | [CONS-06.md](CONS-06.md) |
| `CONS-07` | Định dạng số/ngày/tiền khác nhau | medium | ⏳ chưa | [CONS-07.md](CONS-07.md) |
| `CONS-08` | Vị trí phần tử chung lệch | medium | ⏳ chưa | [CONS-08.md](CONS-08.md) |
| `CONS-09` | Phong cách ảnh không đồng nhất | low | ⏳ chưa | [CONS-09.md](CONS-09.md) |
