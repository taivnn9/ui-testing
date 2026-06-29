# A12 — Interactivity Classifier (đoán phần tử tương tác từ pixel)

> Bóc tách chi tiết. Phase 1. **⚠ Analyzer rủi ro cao — precision-first.**
> Tech: **Python + OpenCV + heuristic**.
> Vì hệ thống chỉ nhận ảnh, **không có `clickable`/`enabled`/`role` ground-truth** từ DOM/XML.
> A12 đoán tất cả từ pixel.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A6`](#) Icon/Graphic Detector

## 1. Trách nhiệm
Hệ thống **không có thuộc tính `clickable`/`enabled`/`role` ground-truth** từ cây. A12 đoán
phần tử nào **tương tác được** (nút, link, input, toggle, tab item) để:
- Cho **Rule CMP-01** (touch-target) biết áp check lên đâu — nếu không biết element tương tác,
  check này sẽ áp sai (FP cao) hoặc bỏ sót.
- Cho **Rule CMP-16** (tap-gap) đo khoảng cách giữa các control tương tác.
- Cho **Agent CMP** xác nhận nhãn, disabled-state, focus.

> ⚠ **Rủi ro cao:** sai ở đây → mọi check touch-target/tap-gap bị sai. **Ưu tiên precision
> tuyệt đối: thà bỏ sót element tương tác còn hơn gán nhầm element không tương tác** (FP gây
> báo lỗi touch-target nhầm cho text/image). `confidence` bắt buộc thấp, `source=vision`.

**KHÔNG** quyết định phần tử có bị disabled không (cần ngữ cảnh → VLM); chỉ đoán
`interactive: true/false` + `interactive_type` + `confidence`.

## 2. Input / Output
- **Input:** `elements[]` từ A3 (bbox + role thô + text từ A5 + icon-label từ A6) + PNG crop từng element.
- **Output:** bổ sung vào mỗi element:
```jsonc
{
  "interactive": true,
  "interactive_type": "button",    // "button" | "link" | "input" | "toggle" | "tab" | "unknown"
  "interactive_confidence": 0.72,  // ⚠ thường thấp (0.5–0.85) — bắt buộc phản ánh đúng
  "interactive_signals": ["rounded_rect", "center_text", "action_label", "elevated_bg"],
  "source": "vision"
}
```
Element không đủ tín hiệu → `interactive: false`, `interactive_confidence: 0.3` (không chắc
là non-interactive, chỉ không đủ bằng chứng là interactive).

## 3. Tín hiệu heuristic (đa tín hiệu kết hợp — precision-first)
Mỗi tín hiệu cộng điểm confidence; ngưỡng để gán `interactive=true` cao (đề xuất ≥ 0.65):

**Hình dạng / affordance:**
- `rounded_rect`: bounding box có bo góc đều (OpenCV `approxPolyDP` + tỉ lệ cạnh), nền màu
  nổi khác nền xung quanh.
- `bordered_box`: có đường viền rõ (input field, card tương tác).
- `circle_shape`: nút tròn / FAB (Floating Action Button).

**Nội dung text (từ A5 OCR):**
- `action_label`: text khớp từ điển hành động vi/en ("Đăng nhập", "Tiếp tục", "Submit",
  "Cancel", "Buy", "Save", "OK", "Đồng ý"...) — từ điển tĩnh + mở rộng.
- `short_centered_text`: text ngắn (≤ 30 ký tự), căn giữa trong box → gợi ý nút.

**Icon (từ A6):**
- `icon_only_box`: box chứa duy nhất icon không có text gần → nghi nút icon (tab/toolbar).
- `icon_plus_label`: icon + text label ngay bên → tab bar item.
- `arrow_chevron`: icon mũi tên / chevron → nghi link/card tapping.

**Vị trí / context:**
- `bottom_tab_bar`: row nằm ở ~20% dưới cùng màn, chứa 3–5 icon đều nhau → tab bar.
- `top_app_bar_icon`: icon nằm trong dải ~5–8% trên cùng → back/menu/action.
- `fab_position`: box tròn/lớn nằm góc dưới phải → FAB.
- `form_field`: box dài nằm trong vùng có label bên trên → input field.

**Màu / contrast (từ A4/pixel):**
- `elevated_bg`: nền box khác rõ màu nền ngoài (delta E hay contrast đơn giản).
- `primary_color`: nền màu primary của app (phát hiện bằng dominant color heuristic).

## 4. Kỹ thuật / lib (Python)

| Việc | Lib/tool (Python) | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Phát hiện bo góc / hình dạng | **OpenCV** (`approxPolyDP`, `minEnclosingCircle`, `HoughCircles`) | deterministic, nhanh | nhạy nhiễu flat design | ✅ **core** |
| Phát hiện viền / cạnh | **OpenCV** (Canny + `findContours`) | tái dùng từ A3 | — | ✅ tái dùng A3 |
| Màu nền box (contrast vs ngoài) | **Pillow + numpy** (lấy mẫu pixel trong / ngoài bbox) | đơn giản | — | ✅ |
| Text label + căn chỉnh | output **A5 OCR** (text + bbox) | không tính lại | phụ thuộc A5 | ✅ tái dùng |
| Từ điển action label | dict tĩnh Python (vi/en) | kiểm soát được, dễ mở rộng | cần bảo trì | ✅ |
| Phát hiện icon | output **A6** (role=icon) | không tính lại | phụ thuộc A6 | ✅ tái dùng |
| ML pretrained UI classifier | **CLIP** (zero-shot "button / text / image") | không train, recall cao | ⚠ thêm dependency, nặng, có thể FP | tùy chọn — anh quyết (mục 8) |
| ML pretrained UI classifier | **ScreenRecognition / UIBert** (fine-tuned trên UI screenshots) | chuyên biệt | phụ thuộc model sẵn; còn hỏng trên app domain khác | tùy chọn nếu heuristic không đủ |

> ⚠ **Về ML pretrained:** khác với YOLO cần train lại, một classifier pretrained trên
> UI screenshots (CLIP zero-shot hoặc model fine-tuned tập chung như Rico/MoTif) KHÔNG đòi
> gán nhãn per-app → vẫn zero-reference. Nhưng Phase 1 **đề xuất heuristic trước** — đơn giản,
> dễ debug, dễ tune ngưỡng; thêm ML nếu standard set cho thấy recall heuristic quá thấp.
> Trade-off: ML tăng recall nhưng tăng FP và dependency nặng — anh quyết.

## 5. Pipeline A12 (đề xuất)
1. **Nhận input:** `elements[]` từ A3; bỏ qua element có `role ∈ {text, divider, image}`
   (độ ưu tiên thấp; trừ text-box có thể là link).
2. **Tính tín hiệu heuristic** cho từng element (mục 3) từ crop + metadata A5/A6.
3. **Scoring:** mỗi tín hiệu có trọng số → tính `interactive_score ∈ [0,1]`.
4. **Ngưỡng:**
   - score ≥ 0.65 → `interactive=true` (precision threshold — cao hơn mức trung bình).
   - 0.4 ≤ score < 0.65 → `interactive=true` nhưng `confidence < 0.6` + cờ `ambiguous`.
   - score < 0.4 → `interactive=false`.
5. **Ghi tín hiệu:** `interactive_signals[]` = danh sách tín hiệu đã fire (để debug/explain).
6. **Emit** bổ sung vào `elements[]`; A0 Normalize dùng khi điền field `interactive`.

## 6. Tiêu chí phục vụ
| Tiêu chí | Vai trò A12 |
|---|---|
| **CMP-01** Touch target < 44pt/48dp | **điều kiện cần**: rule chỉ áp với element có `interactive=true` |
| **CMP-16** Tap-gap (2 control quá sát) | cần danh sách element tương tác để tính khoảng cách |
| **CMP-03** Không tap được do bị đè | phối hợp với Rule IoU+z — cần biết phần tử nào tương tác |
| **CMP-02** Nút không nhãn | xác định xem box-icon là nút không nhãn hay chỉ là ảnh trang trí |
| **CMP-07** Input field / label | phân loại `interactive_type=input` để agent CMP kiểm tra |
| **LAY-06** Z-order / occlusion | tăng severity khi phần tử bị che là `interactive=true` |

## 7. Open decisions (cần anh chốt — lựa chọn lớn)
- [ ] **Thuần heuristic hay thêm ML pretrained (CLIP zero-shot)?**
  - *Thuần heuristic:* dễ debug, nhanh, controllable, đề xuất Phase 1.
    Nhược: recall thấp với nút flat (không bo, không nền rõ — xu hướng modern design).
  - *Thêm CLIP zero-shot ("is this a button?"):* tăng recall, không cần train.
    Nhược: dependency nặng (CLIP model ~400MB), thêm latency, FP với ảnh/thumbnail.
  - *Model chuyên biệt (ScreenRecognition/UIBert):* precision+recall tốt nhất cho UI.
    Nhược: phụ thuộc model sẵn + có thể drift với app domain khác.
  → **Đề xuất:** heuristic là core; chỉ thêm CLIP nếu standard set cho thấy recall < 70%.
- [ ] **Ngưỡng precision (0.65 để gán `interactive=true`):** cao hay thấp — đây là trade-off
  trực tiếp FP vs FN. FP → báo lỗi touch-target nhầm. FN → bỏ sót lỗi thật. Anh xác nhận
  ưu tiên precision hay recall?
- [ ] **Mở rộng từ điển action label:** bắt đầu với vi/en, thêm ngôn ngữ khác khi cần i18n.
  Anh có danh sách app/ngôn ngữ mục tiêu để ưu tiên?

## 8. TDD outline (khi vào code)
- test: crop nút bo góc + text "Đăng nhập" → `interactive=true`, `type=button`, conf ≥ 0.65.
- test: crop text label dài → `interactive=false`.
- test: crop icon tab bar (row 4 icon đều, gần đáy) → `interactive=true`, `type=tab`.
- test: crop input field (box dài, border mỏng) → `interactive=true`, `type=input`.
- test: crop ảnh product card không có dấu hiệu nút → `interactive=false` (tránh FP).
- test: tất cả output có `source=vision` + `interactive_confidence < 1.0`.
- test: element `ambiguous` → confidence < 0.6 + cờ đúng chỗ.
- test: không crash khi crop rỗng / role không xác định.

## Trạng thái: spec ✅ — ⚠ Analyzer rủi ro cao; chờ chốt mục 7 (heuristic-only vs +ML, ngưỡng precision).
