# Phân tích ban đầu: Giải pháp tự động phân tích lỗi UI bằng AI

> Bản phân tích mở đầu (phiên 2026-05-21), trả lời 4 câu hỏi: (1) tiêu chí đã đủ chưa,
> (2) lấy dữ liệu gì & lấy thế nào, (3) tổ chức dữ liệu thế nào, (4) làm sao Agent/Model
> làm đúng (prompt/Skill/Rule/workflow). Quyết định chốt sau đó nằm trong `../CLAUDE.md`.

---

## 0. Vấn đề cốt lõi cần sửa ngay trong ý tưởng gốc

> Pipeline gốc: "Trích xuất → JSON map → đưa **JSON** cho AI suy luận."

**Đưa JSON thôi là vứt mất pixel.** Hơn một nửa tiêu chí liệt kê *không thể* phán đoán từ
bounding box + text:

| Tiêu chí | Phán đoán được từ JSON (toạ độ/text)? | Bắt buộc cần pixel? |
|---|---|---|
| Chữ tràn/cắt cụt khỏi container | ✅ (so box text vs box cha) | một phần |
| Độ tương phản / readability | ❌ | ✅ (màu pixel thực tế) |
| Ảnh méo / kéo giãn (distortion) | ❌ | ✅ (so tỉ lệ render vs gốc) |
| Icon lệch tâm trong nút | ✅ (toạ độ) | một phần |
| Overlap vô lý | ✅ | để xác nhận "vô lý" thì cần ảnh |
| Font chưa load (□ tofu), ảnh vỡ | ❌ | ✅ |
| Nội dung sai ngữ cảnh | ❌ | ✅ (cần nhìn cả màn hình) |

→ **Kết luận #1: kiến trúc phải đa phương thức (multimodal).** Đưa cho VLM **cả ảnh
screenshot + JSON map**. JSON cho hình học chính xác (VLM rất dở đoán toạ độ pixel, hay bịa);
ảnh cho diện mạo (JSON không nắm được). Hai cái bù nhau.

→ **Kết luận #2 (quan trọng hơn nữa): đừng chỉ OCR ảnh để lấy JSON.** Môi trường
*instrumented* (Playwright/Appium) có sẵn **view hierarchy / DOM / accessibility tree** — đó
là "ground truth" của toạ độ + role + text + style, chính xác tuyệt đối và miễn phí. Lấy OCR
từ pixel là tự nguyện làm việc với dữ liệu nhiễu trong khi vàng đang nằm sẵn. Đây là khác
biệt lớn nhất giữa "đồ chơi demo" và "hệ thống chạy nghìn case".

---

## 1. Bộ tiêu chí đã đủ chưa? — Chưa, thiếu ~10 nhóm lỗi phổ biến nhất

Bộ 4 nhóm hiện tại tốt nhưng thiên về *layout tĩnh*. Trong thực tế QA mobile, những lỗi
**bắt được nhiều nhất và rẻ nhất** lại đang thiếu:

| Nhóm còn thiếu | Ví dụ cụ thể (rất hay gặp) |
|---|---|
| **Placeholder/biến chưa render** | `undefined`, `null`, `NaN`, `%s`, `{0}`, `{{user.name}}`, `lorem ipsum`, `home.title` (i18n key lòi ra) |
| **i18n / localization** | Text sai ngôn ngữ, key dịch chưa dịch, text tiếng Đức/Việt nở dài làm vỡ layout, lỗi RTL |
| **Safe area / notch / system bars** | Nội dung chui dưới tai thỏ, status bar, home indicator, bàn phím che ô input |
| **Trạng thái (states)** | Skeleton/loading kẹt, empty state trống trơn, error state, ảnh vỡ (broken image icon) |
| **Dark mode / font scale** | Chữ trắng nền trắng ở dark mode, layout vỡ khi bật cỡ chữ trợ năng |
| **Tính nhất quán xuyên màn hình** | Cùng 1 nút mà 3 kích cỡ khác nhau, lệch bảng màu, lệch font — *cần so nhiều ảnh, không chỉ 1* |
| **Truncation chủ ý vs lỗi** | Phân biệt "…" do design vs cắt cụt do bug |
| **Z-order / occlusion** | Phần tử bị che sau modal/overlay |
| **Trùng lặp / thiếu** | Nút bị nhân đôi, ảnh/icon biến mất |
| **Alignment theo lưới** | Lệch grid, lệch optical alignment (khác với padding/margin đã có) |

Và **2 thứ thiếu mang tính sống còn của cả hệ thống** — không phải tiêu chí lỗi mà là
*thuộc tính của mỗi phát hiện*:

1. **Severity + Confidence + Evidence.** Mỗi lỗi phải kèm: mức độ
   (blocker/major/minor/cosmetic), độ tin cậy (0–1), và *bằng chứng* (element_id, bbox, ảnh
   crop, rule vi phạm). Thiếu cái này → QA chết chìm trong noise và **false positive sẽ giết
   hệ thống** (lý do #1 các tool kiểu này bị bỏ).
2. **Tiêu chí "nội dung hợp lý" là khó & chủ quan nhất** — về bản chất nó *cần reference*
   (màn này đáng lẽ hiện gì). Zero-reference làm cái này rất yếu. Cần thành thật: hạ kỳ vọng
   nhóm này hoặc cấp cho AI thêm ngữ cảnh (tên màn, intent của test case).

---

## 2. Lấy dữ liệu gì & lấy như thế nào? — Phân tầng theo "có view hierarchy hay không"

Đây là chỗ rẽ nhánh lớn nhất. Có 2 thế giới:

**Thế giới A — Black-box (chỉ có ảnh PNG):** phải OCR (text + box), detect icon/ảnh bằng CV,
dò edge/contour. Nhiễu, tốn, kém chính xác. Chỉ dùng khi *bắt buộc* không truy cập được app.

**Thế giới B — Instrumented (Playwright/Appium):** lấy thẳng cây phần tử. **Đây là hướng nên đi.**
- **Web (Playwright):** DOM + `getBoundingClientRect()` + `getComputedStyle()` → có
  font-size, color, background, z-index, overflow… → tính được **contrast ratio chuẩn WCAG**
  bằng code, không cần đoán.
- **Android:** `uiautomator` dump / accessibility tree (bounds, text, class, clickable…).
- **iOS:** XCUITest element tree.

**Mô hình dữ liệu 4 tầng nên thu thập đồng thời cho mỗi screenshot:**

- **Tầng A — Cây phần tử (ground truth):** role, bbox, text, style, parent/child, z-order. *Từ hierarchy/DOM.*
- **Tầng B — Đặc trưng hình học suy ra (tính bằng code):** overlap, khoảng cách/đều lề, lệch
  grid, off-screen, vượt safe-area, touch-target < ngưỡng. *Đây là phần "rule engine tất định".*
- **Tầng C — Đặc trưng pixel per-element (crop từng phần tử):** thực sự có bị clip không,
  contrast màu render thực, blur, tỉ lệ ảnh render vs intrinsic (bắt distortion), có □ tofu không.
- **Tầng D — Ảnh screenshot gốc** (full + crop) để đưa cho VLM nhìn.

→ Hierarchy lo phần "chính xác", pixel lo phần "diện mạo". Kết hợp mới đủ bộ tiêu chí.

---

## 3. Tổ chức dữ liệu thế nào? — Schema chuẩn hóa + quan hệ tiền-tính

Mấu chốt: **đừng bắt LLM tự suy quan hệ không gian từ toạ độ thô** — nó suy kém và hay sai.
Hãy *tiền-tính* quan hệ rồi đưa vào JSON. Đề xuất schema canonical:

```jsonc
{
  "screen": { "id", "platform":"android|ios|web", "route",
              "viewport":{w,h,dpr}, "safe_area":{top,bottom,left,right},
              "theme":"light|dark", "locale", "font_scale", "ts" },
  "image":   { "full":"path.png", "w","h" },
  "elements":[{
     "id":"e12", "role":"button|text|image|icon|input|toggle|...",
     "bbox":{x,y,w,h}, "bbox_norm":{...},            // tuyệt đối + chuẩn hoá 0–1
     "parent":"e3", "children":["e13"], "z":2,
     "text":"Đăng nhập", "text_truncated":false,
     "style":{ font_size, font_family, color, bg_color,
               contrast_ratio, opacity, border_radius },
     "image_meta":{ intrinsic_w, intrinsic_h, displayed_w, displayed_h, scale_mode },
     "interactive":true, "touch_target":{w,h},
     "visible":true, "clipped":false, "offscreen":false,
     "crop":"crops/e12.png"
  }],
  "relations":[ {"a":"e12","rel":"overlaps","b":"e15","iou":0.34},
                {"a":"e7","rel":"left_of","b":"e8","gap":4} ],   // tiền-tính
  "candidate_issues":[ {"rule":"touch_target_min","element":"e12",
                        "severity":"major","detail":"40x40 < 44x44"} ]
}
```

Ý chính: **phân cấp** lưu bằng `parent/children` + `z`; **quan hệ tương đối** (left_of /
above / contains / overlaps) tiền-tính sẵn trong `relations`; và `candidate_issues` là output
của rule engine (mục 4) — đưa kèm để VLM *xác nhận/bác bỏ* thay vì tự mò.

---

## 4. Làm sao Agent/Model làm ĐÚNG yêu cầu? (prompt / Skill / Rule / workflow)

Nguyên tắc xương sống:

> **Cái gì tính được thì để code tính (tất định). Chỉ hỏi AI cái cần phán đoán.**

LLM dở số học trên toạ độ → đừng bắt nó tự phát hiện overlap, touch-target nhỏ, contrast thấp
(những cái này có công thức). Để rule engine làm, rồi VLM chỉ: (a) xác nhận lỗi candidate có
*thật sự vô lý* không, (b) bắt lỗi cần *thẩm mỹ/ngữ cảnh*, (c) gán severity + giải thích.

**Pipeline (workflow) tổng:**
```
Capture (ảnh + hierarchy)  →  Normalize (schema mục 3)
   →  Rule Engine (checks tất định → candidate_issues)
   →  VLM Reasoning (ảnh + JSON + candidates → confirm/reject + lỗi phán đoán + severity)
   →  Verify/Critic pass (giảm false positive)
   →  Aggregate + dedupe + report
```

**Chiến lược prompt (rất cụ thể):**
1. **Structured output bắt buộc** (tool-use/JSON schema), không bao giờ free text. Mỗi issue =
   `{category, element_id, bbox, severity, confidence, evidence, rule_id, explanation}`.
2. **Decompose theo nhóm tiêu chí** — đừng hỏi "tìm hết bug" 1 phát (cho kết quả nông). Walk
   theo *checklist* từng nhóm, hoặc 1 lượt/nhóm. Chạy song song được.
3. **Set-of-Marks prompting** — vẽ số ID lên từng phần tử trên ảnh để VLM *trỏ theo ID* thay
   vì đoán toạ độ. Kỹ thuật chuẩn để tăng grounding không gian cho VLM, cực hợp bài này.
4. **Few-shot có nhãn** (cặp good/bad) để calibrate severity.
5. **Self-critique pass**: detect → tự phản biện → chỉ giữ confidence cao. Giảm false positive.

**Skill / Rule / Workflow ánh xạ thế nào (trong ngữ cảnh agent):**
- **Rule** = bộ tiêu chí + ngưỡng *máy đọc được*: touch target ≥ 44pt (iOS) / 48dp (Android),
  contrast ≥ 4.5:1, max line length, gap grid 8pt… Chia 2 loại: *rule tất định* (code chạy)
  và *soft rule* (đưa VLM làm guidance).
- **Skill** = playbook tái dùng cho 1 screenshot: chứa rubric, schema JSON, template prompt,
  few-shot, định nghĩa các deterministic check. Mỗi ảnh gọi skill này.
- **Workflow** = orchestration cả pipeline + chạy batch nghìn case: agent điều phối, spawn
  subagent song song (mỗi ảnh / mỗi nhóm tiêu chí).

**Phần META mà 90% dự án kiểu này quên → và rồi sập:**
> **Phải có Golden Set** — tập screenshot có nhãn lỗi sẵn (ground truth) để đo
> **precision/recall**. Không có nó thì không tune được ngưỡng, không biết hệ thống đáng tin
> hay không. Mẹo tạo positive nhanh: **mutation testing UI** — cố tình inject lỗi (đổi
> font-size, bóp ảnh, thêm text dài, đổi màu) vào app rồi chụp → có ngay tập lỗi đã biết.
