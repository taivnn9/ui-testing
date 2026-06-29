# A12 — Interactivity Classifier (đoán phần tử tương tác từ pixel)

> **TL;DR:** Đoán element nào tương tác được (button/link/input/toggle/tab) bằng heuristic đa tín hiệu từ pixel — không có `clickable`/`enabled` từ DOM; precision-first (thà bỏ sót còn hơn gán nhầm). Output `interactive` + type + confidence cho rule CMP touch-target/tap-gap.

> Phase 1. **⚠ Analyzer rủi ro cao — precision-first.** Tech: **Python + OpenCV + heuristic**.
> Liên quan: [`A3-box-layout-detector.md`](A3-box-layout-detector.md) · [`A5-ocr-text-extractor.md`](A5-ocr-text-extractor.md) · [`A6`](#) Icon/Graphic Detector

## 1. Trách nhiệm
Hệ thống **không có `clickable`/`enabled`/`role` ground-truth** từ cây. A12 đoán element nào **tương tác được** (nút, link, input, toggle, tab) để:
- **Rule CMP-01** (touch-target) biết áp check lên đâu — không biết → check sai (FP cao) hoặc bỏ sót.
- **Rule CMP-16** (tap-gap) đo khoảng cách giữa control tương tác.
- **Agent CMP** xác nhận nhãn, disabled-state, focus.

> ⚠ **Rủi ro cao:** sai ở đây → mọi check touch-target/tap-gap sai. **Precision tuyệt đối: thà bỏ sót element tương tác còn hơn gán nhầm element không tương tác** (FP → báo lỗi touch-target nhầm cho text/image). `confidence` bắt buộc thấp, `source=vision`.

KHÔNG quyết disabled (cần ngữ cảnh → agent); chỉ đoán `interactive: true/false` + `interactive_type` + `confidence`.

## 2. Input / Output
- **Input:** `elements[]` từ A3 (bbox + role thô + text A5 + icon-label A6) + PNG crop từng element.
- **Output:** bổ sung vào element:
```jsonc
{
  "interactive": true,
  "interactive_type": "button",    // "button" | "link" | "input" | "toggle" | "tab" | "unknown"
  "interactive_confidence": 0.72,  // ⚠ thường thấp (0.5–0.85)
  "interactive_signals": ["rounded_rect", "center_text", "action_label", "elevated_bg"],
  "source": "vision"
}
```
Không đủ tín hiệu → `interactive: false`, `interactive_confidence: 0.3` (không chắc non-interactive, chỉ không đủ bằng chứng là interactive).

## 3. Tín hiệu heuristic (đa tín hiệu — precision-first)
Mỗi tín hiệu cộng điểm confidence; ngưỡng gán `interactive=true` cao (đề xuất ≥ 0.65):

**Hình dạng / affordance:**
- `rounded_rect`: bbox bo góc đều (OpenCV `approxPolyDP` + tỉ lệ cạnh), nền màu nổi khác xung quanh.
- `bordered_box`: viền rõ (input field, card tương tác).
- `circle_shape`: nút tròn / FAB (Floating Action Button).

**Nội dung text (A5 OCR):**
- `action_label`: text khớp từ điển hành động vi/en ("Đăng nhập", "Tiếp tục", "Submit", "Cancel", "Buy", "Save", "OK", "Đồng ý"...) — dict tĩnh + mở rộng.
- `short_centered_text`: text ngắn (≤ 30 ký tự), căn giữa trong box → gợi ý nút.

**Icon (A6):**
- `icon_only_box`: box chỉ chứa icon, không text gần → nghi nút icon (tab/toolbar).
- `icon_plus_label`: icon + text label bên cạnh → tab bar item.
- `arrow_chevron`: icon mũi tên / chevron → nghi link/card tapping.

**Vị trí / context:**
- `bottom_tab_bar`: row ~20% dưới cùng, 3–5 icon đều nhau → tab bar.
- `top_app_bar_icon`: icon ~5–8% trên cùng → back/menu/action.
- `fab_position`: box tròn/lớn góc dưới phải → FAB.
- `form_field`: box dài có label bên trên → input field.

**Màu / contrast (A4/pixel):**
- `elevated_bg`: nền box khác rõ màu nền ngoài (delta E / contrast đơn giản).
- `primary_color`: nền màu primary của app (dominant color heuristic).

## 4. Kỹ thuật / lib (Python)
| Việc | Lib/tool | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|---|
| Bo góc / hình dạng | **OpenCV** (`approxPolyDP`, `minEnclosingCircle`, `HoughCircles`) | deterministic, nhanh | nhạy nhiễu flat design | ✅ **core** |
| Viền / cạnh | **OpenCV** (Canny + `findContours`) | tái dùng A3 | — | ✅ tái dùng A3 |
| Màu nền box (contrast vs ngoài) | **Pillow + numpy** (lấy mẫu pixel trong/ngoài bbox) | đơn giản | — | ✅ |
| Text label + căn chỉnh | output **A5 OCR** | không tính lại | phụ thuộc A5 | ✅ tái dùng |
| Từ điển action label | dict tĩnh Python (vi/en) | kiểm soát, dễ mở rộng | cần bảo trì | ✅ |
| Phát hiện icon | output **A6** (role=icon) | không tính lại | phụ thuộc A6 | ✅ tái dùng |
| ML pretrained UI classifier | **CLIP** (zero-shot "button / text / image") | không train, recall cao | ⚠ dependency nặng, có thể FP | tùy chọn — anh quyết (mục 7) |
| ML pretrained UI classifier | **ScreenRecognition / UIBert** (fine-tuned UI screenshots) | chuyên biệt | phụ thuộc model sẵn; drift app domain khác | tùy chọn nếu heuristic không đủ |

> ⚠ **ML pretrained:** khác YOLO cần train lại, classifier pretrained trên UI screenshots (CLIP zero-shot / model fine-tuned tập chung như Rico/MoTif) KHÔNG đòi gán nhãn per-app → vẫn zero-reference. Phase 1 **đề xuất heuristic trước** (đơn giản, dễ debug, dễ tune); thêm ML nếu standard set recall quá thấp. Trade-off: ML tăng recall nhưng tăng FP + dependency nặng.

## 5. Pipeline A12 (đề xuất)
1. **Nhận input:** `elements[]` từ A3; bỏ qua `role ∈ {text, divider, image}` (trừ text-box có thể là link).
2. **Tính tín hiệu heuristic** (mục 3) từ crop + metadata A5/A6.
3. **Scoring:** mỗi tín hiệu có trọng số → `interactive_score ∈ [0,1]`.
4. **Ngưỡng:**
   - score ≥ 0.65 → `interactive=true` (precision threshold).
   - 0.4 ≤ score < 0.65 → `interactive=true` nhưng `confidence < 0.6` + cờ `ambiguous`.
   - score < 0.4 → `interactive=false`.
5. **Ghi `interactive_signals[]`** = tín hiệu đã fire (debug/explain).
6. **Emit** vào `elements[]`; A0 Normalize dùng khi điền field `interactive`.

## 6. Tiêu chí phục vụ
| Tiêu chí | Vai trò A12 |
|---|---|
| **CMP-01** Touch target < 44pt/48dp | **điều kiện cần**: rule chỉ áp với `interactive=true` |
| **CMP-16** Tap-gap (2 control quá sát) | cần danh sách element tương tác để tính khoảng cách |
| **CMP-03** Không tap được do bị đè | phối hợp Rule IoU+z — cần biết phần tử nào tương tác |
| **CMP-02** Nút không nhãn | box-icon là nút không nhãn hay ảnh trang trí |
| **CMP-07** Input field / label | `interactive_type=input` để agent CMP kiểm tra |
| **LAY-06** Z-order / occlusion | tăng severity khi phần tử bị che là `interactive=true` |

## 7. Open decisions (cần anh chốt)
- [ ] **Thuần heuristic hay thêm ML pretrained (CLIP zero-shot)?**
  - *Heuristic:* dễ debug, nhanh, controllable, đề xuất Phase 1. Nhược: recall thấp với nút flat (modern design).
  - *CLIP zero-shot:* tăng recall, không train. Nhược: dependency nặng (~400MB), thêm latency, FP với ảnh/thumbnail.
  - *Model chuyên biệt (ScreenRecognition/UIBert):* precision+recall tốt nhất. Nhược: phụ thuộc model sẵn + drift app domain khác.
  - → **Đề xuất:** heuristic là core; thêm CLIP nếu standard set recall < 70%.
- [ ] **Ngưỡng precision (0.65):** cao hay thấp — trade-off FP vs FN trực tiếp. FP → báo touch-target nhầm; FN → bỏ sót lỗi thật. Anh xác nhận ưu tiên precision hay recall?
- [ ] **Mở rộng từ điển action label:** bắt đầu vi/en. Anh có danh sách app/ngôn ngữ mục tiêu?

## 8. TDD outline
- nút bo góc + text "Đăng nhập" → `interactive=true`, `type=button`, conf ≥ 0.65.
- text label dài → `interactive=false`.
- icon tab bar (4 icon đều, gần đáy) → `interactive=true`, `type=tab`.
- input field (box dài, border mỏng) → `interactive=true`, `type=input`.
- ảnh product card không dấu hiệu nút → `interactive=false` (tránh FP).
- mọi output có `source=vision` + `interactive_confidence < 1.0`.
- element `ambiguous` → confidence < 0.6 + cờ đúng chỗ.
- không crash khi crop rỗng / role không xác định.

## Trạng thái: spec ✅ — ⚠ Analyzer rủi ro cao; chờ chốt mục 7 (heuristic-only vs +ML, ngưỡng precision).
