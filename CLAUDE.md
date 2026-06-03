# Dự án: Tự động phân tích lỗi UI bằng AI (Zero-Reference Layout Reasoning)

> File này là bối cảnh dự án cho mọi phiên Claude Code / agent làm việc trong repo này.
> Trao đổi với chủ dự án **bằng tiếng Việt** (user là kỹ sư QA mobile).

## 0. Quy tắc làm việc (agent — QUAN TRỌNG)
- **Luôn ghi phân tích/thiết kế/quyết định ra file trong `docs/` NGAY khi trao đổi**, cập nhật
  tăng dần theo từng phần đã chốt — KHÔNG chỉ giữ trong chat. Lý do: **đề phòng mất session
  chat** thì công việc vẫn còn nguyên trong repo.
- `docs/` là **nguồn sự thật** (tài liệu sống, chi tiết); `CLAUDE.md` là bản **tóm tắt quyết
  định gọn** (đọc tự động mỗi phiên) — chốt gì ở docs thì cập nhật lại đây.
- **Mỗi khi xong một việc / tạo hoặc sửa xong file → commit & push lên git NGAY** (không chờ
  user nhắc). Repo `taivnn9/ui-testing`, branch `main`.
- **User mạnh về lập trình & tin tưởng đề xuất kỹ thuật** → chủ động **SUGGEST** tech stack /
  lib / cách làm, KHÔNG hỏi từng quyết định nhỏ; chỉ nêu rõ các lựa chọn lớn để user nắm.
  Mỗi analyzer/agent: **list rõ technique + lib (bám Python)**. Agent: mạnh dạn đề xuất
  prompting / skill / rule.
- **Chủ động & thường xuyên cập nhật memory session** (quyết định, preference, tiến độ) để
  xuyên phiên không mất ngữ cảnh.

## 1. Mục tiêu
Xây **API service** tự động phát hiện lỗi giao diện (UI/UX) trên ảnh chụp màn hình app
(mobile + web), theo hướng **Zero-Reference**: KHÔNG đối chiếu design mẫu, KHÔNG dùng
object detection kiểu YOLO (tránh phải gán nhãn / train lại liên tục).

## 2. Kiến trúc đã chốt
**Mô hình triển khai: API service.**
- **Input** (tester gửi lên): `screenshot (PNG)` — **duy nhất, không nhận DOM/XML/HTML**.
- **Output**: danh sách lỗi có cấu trúc, mỗi lỗi kèm `severity`, `confidence`, `evidence` (element_id, bbox, crop).
- Hỗ trợ **cả web + mobile** — phân biệt qua metadata (platform, dpr, safe_area).
- **Runtime / orchestration**: tool nội bộ kiểu **n8n** (gọi qua API) và/hoặc **Cline (VSCode)**.
  Model suy luận: **open model self-host gọi qua API** (và/hoặc hosted VLM).

### 2.1. MỘT CHẾ ĐỘ DUY NHẤT: vision-only
Chỉ có một mode: **vision-only**. Toàn bộ element, style, geometry đều lấy từ ảnh thông qua
**OCR + CV + VLM**. Không có DOM/XML adapter, không có Mode A/B.

## 3. Nguyên tắc thiết kế (QUAN TRỌNG — đừng làm sai)
1. **Đa phương thức (multimodal)**: đưa cho model **CẢ ảnh + JSON map**, không chỉ JSON.
   Hơn nửa tiêu chí (contrast, distortion, font tofu, ảnh vỡ, ngữ cảnh) không phán đoán
   được từ toạ độ/text → bắt buộc cần pixel. JSON cho hình học chính xác; ảnh cho diện mạo.
2. **Vision-only là nguồn duy nhất**: mọi element/geometry/style đều suy ra từ ảnh qua
   OCR + CV + VLM. Không có DOM/XML; không giả định có hierarchy sẵn.
3. **Tách tất định khỏi phán đoán**: cái gì TÍNH ĐƯỢC bằng code (overlap, touch-target nhỏ,
   contrast ratio, off-screen, vượt safe-area, tỉ lệ ảnh méo) → **rule engine** làm, KHÔNG
   hỏi LLM (LLM dở số học toạ độ, hay bịa). LLM chỉ lo: xác nhận candidate có "vô lý" thật
   không + bắt lỗi cần thẩm mỹ/ngữ cảnh + gán severity + giải thích.
4. **Mỗi lỗi phải có `severity` + `confidence` + `evidence`**. False positive là thứ giết
   hệ thống loại này → ưu tiên precision, có pass self-critique/verify.
5. **Phải có Golden Set** (tập ảnh có nhãn lỗi sẵn) để đo precision/recall và tune ngưỡng.
   Mẹo tạo nhanh: **mutation testing UI** (cố tình inject lỗi: đổi font-size, bóp ảnh,
   nhồi text dài, đổi màu) → có ngay tập positive đã biết.

## 4. Bộ tiêu chí đánh giá
**4 nhóm gốc:** Text & Semantics · Images & Assets · Spatial Layout · UI Components.
**Bổ sung (hay gặp & rẻ, gốc còn thiếu):**
- Placeholder/biến chưa render: `undefined`, `null`, `NaN`, `%s`, `{{var}}`, i18n key lòi ra, `lorem ipsum`.
- i18n/localization: sai ngôn ngữ, chưa dịch, text nở dài làm vỡ layout, lỗi RTL.
- Safe area / notch / system bar / bàn phím che input.
- States: loading/skeleton kẹt, empty state, error state, ảnh vỡ (broken image).
- Dark mode / font scale (trợ năng) làm vỡ layout.
- Nhất quán xuyên màn hình (cùng nút khác cỡ, lệch bảng màu/font) — cần so nhiều ảnh.
- Truncation chủ ý vs lỗi · Z-order/occlusion · Trùng lặp/thiếu phần tử · Lệch grid/optical alignment.
- Lưu ý: tiêu chí "nội dung hợp lý" là khó nhất với zero-reference (cần ngữ cảnh màn/intent test).

## 5. Schema dữ liệu chung (vision-only)
> **Chi tiết đầy đủ + Pydantic v2 skeleton:** [`docs/F0.2-canonical-schema.md`](docs/F0.2-canonical-schema.md)
> **Đơn vị & ngưỡng:** [`docs/F0.4-thresholds.md`](docs/F0.4-thresholds.md)

Tóm tắt nhanh:
- Toạ độ nội bộ: **device px** (CSS px × dpr / dp × dpr / pt × dpr)
- `source` ở cấp element/field: `"vision" | "pixel"` (không còn `"dom" | "xml"`)
- `style._sources`: dict override source theo field (vd: `contrast_ratio: "pixel"`)
- `candidate_issues.severity`: **5 mức** `critical | high | medium | low | trivial`
  (bỏ 4 mức cũ `blocker/major/minor/cosmetic`)
- `candidate_issues.severity_range`: Rule Engine ghi range, VLM chốt mức cuối

```jsonc
{
  "screen": { "id","platform":"android|ios|web","route",
              "viewport":{"w":0,"h":0,"dpr":0},
              "safe_area":{"top":0,"bottom":0,"left":0,"right":0},
              "theme":"light|dark","locale","font_scale","ts" },
  "image":  { "full":"path.png","w":0,"h":0 },
  "elements":[{
     "id":"e12","role":"button|text|image|icon|input|toggle|...",
     "source":"vision|pixel","confidence":1.0,
     "bbox":{"x":0,"y":0,"w":0,"h":0},"bbox_norm":{},
     "parent":"e3","children":["e13"],"z":2,
     "text":"","text_truncated":false,
     "style":{"font_size":0,"font_family":"","color":"","bg_color":"",
              "contrast_ratio":0,"opacity":1,"border_radius":0,
              "_sources":{"contrast_ratio":"pixel"}},
     "image_meta":{"intrinsic_w":0,"intrinsic_h":0,"displayed_w":0,"displayed_h":0,"scale_mode":""},
     "interactive":true,"touch_target":{"w":0,"h":0},
     "visible":true,"clipped":false,"offscreen":false,"crop":"crops/e12.png"
  }],
  "relations":[{"a":"e7","rel":"left_of|above|contains|overlaps","b":"e8","gap":0,"iou":0}],
  "candidate_issues":[{
     "rule":"touch_target_min","element":"e12",
     "severity":"high","severity_range":{"min":"medium","max":"critical"},
     "confidence":1.0,"detail":"","evidence":{"bbox":{},"crop":""}
  }]
}
```
- Phân cấp: `parent/children` + `z`. Quan hệ tương đối **tiền-tính** trong `relations`
  (đừng bắt LLM tự suy từ toạ độ thô).
- `candidate_issues` = output rule engine, đưa kèm để VLM xác nhận/bác bỏ.

## 6. Pipeline xử lý
```
Input (ảnh PNG)
  →  Vision Adapter: OCR + CV element detect + VLM → schema mục 5
  →  Rule Engine (tập con tính được từ box+pixel) → candidate_issues
  →  VLM Reasoning (ảnh + JSON + candidates → confirm/reject + lỗi phán đoán + severity)
  →  Verify/Critic pass (giảm false positive)
  →  Aggregate + dedupe → trả về API
```
**Prompt:** structured output bắt buộc (JSON schema nhúng prompt + `response_format=json_object`,
llama.cpp — không tool_use) · decompose theo nhóm tiêu chí
(không hỏi "tìm hết bug" 1 phát) · **Set-of-Marks** (vẽ ID lên ảnh để model trỏ theo ID,
không đoán toạ độ) · few-shot có nhãn để calibrate severity · self-critique trước khi báo.

## 7. Trạng thái & việc tiếp theo
- [x] Chốt kiến trúc (API service, input ảnh duy nhất, vision-only, rule+VLM).
- [x] Vision adapter: A0, A3–A10, A12, A13 analyzers (`src/ui_defect/analyzers/`) — CV+OCR+pixel.
      (A1/A2 đã bỏ — DOM/XML; **A11** face/text-in-image: **hoãn Phase 2**, chỉ có spec.)
- [x] Rule engine R1–R4 (`src/ui_defect/rules/`) — geometry, color, image, text.
- [x] Prompt template + VLM agents G0–G6 (`src/ui_defect/agents/`) — Set-of-Marks, JSON output
      qua llama.cpp OpenAI-compatible endpoint (không dùng tool_use).
- [x] API service (`src/ui_defect/api/`) — FastAPI, POST /analyze, zero-config (chỉ cần ảnh).
- [x] Web UI (`src/ui_defect/web/`) — upload, phân tích, list lỗi + overlay Set-of-Marks
      (bbox màu theo severity, liên kết 2 chiều, filter). FastAPI serve `GET /` + `/static`. Spec: `docs/F2.0-web-ui.md`.
- [x] Cài deps (`pip install -e ".[dev]"`) + pytest unit: **103/103 pass** (2026-06-03, +3 test web serving).
- [ ] Golden set + script đo precision/recall (mutation testing UI) → `data/golden/`.
- [ ] Integration test với ảnh thật (cần OCR backend + llama.cpp server).
- [ ] Few-shot examples cho agents G1–G6 (cần ảnh mẫu có lỗi biết trước).
