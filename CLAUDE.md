# Dự án: Tự động phân tích lỗi UI bằng AI (Zero-Reference Layout Reasoning)

> File này là bối cảnh dự án cho mọi phiên Claude Code / agent làm việc trong repo này.
> Trao đổi với chủ dự án **bằng tiếng Việt** (user là kỹ sư QA mobile).
> User có thể nhắn bằng tiếng Anh hoặc tiếng Việt — agent **luôn trả lời bằng tiếng Việt**.

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
- **Runtime / orchestration**: tầng reasoning = **coding-agent CLI headless** —
  **Codex** (`codex exec`, máy này) / **Cline** (máy công ty). Gọi trực tiếp từ folder project,
  có quyền **đọc/ghi file** (`-s workspace-write`). **KHÔNG dùng VLM/hosted multimodal nữa**
  (user không có model multimodal). Chi tiết: [`docs/F1.1-codex-cli-architecture.md`](docs/F1.1-codex-cli-architecture.md).

### 2.1. MỘT CHẾ ĐỘ DUY NHẤT: vision-only (CV trích map) + reasoning text-only
Element/style/geometry lấy từ ảnh qua **OCR + CV** (ảnh CHỈ dùng ở tầng CV). Tầng lý luận
(coding-agent CLI) **chỉ nhận dữ liệu ký tự** (JSON map + candidate + skill), **không nhận ảnh**.
Không có DOM/XML adapter, không có Mode A/B.

## 3. Nguyên tắc thiết kế (QUAN TRỌNG — đừng làm sai)
1. **Model reasoning chỉ nhận TEXT** (đổi 2026-06-03, thay nguyên tắc multimodal cũ): không
   gửi ảnh cho model. Các tiêu chí cần pixel (contrast, ảnh méo/vỡ, font tofu) được **CV tính
   tất định** và đưa vào JSON dưới dạng số/flag (`contrast_ratio`, `image_meta`, `has_replacement`)
   → agent lý luận trên số đó. JSON cho hình học chính xác; CV thay "mắt".
2. **Vision-only là nguồn duy nhất** (cho việc trích map): element/geometry/style suy ra từ ảnh
   qua OCR + CV. Không có DOM/XML; không giả định có hierarchy sẵn.
3. **Tách tất định khỏi phán đoán**: cái gì TÍNH ĐƯỢC bằng code (overlap, touch-target nhỏ,
   contrast ratio, off-screen, vượt safe-area, tỉ lệ ảnh méo) → **rule engine** làm, KHÔNG
   hỏi LLM (LLM dở số học toạ độ, hay bịa). LLM chỉ lo: xác nhận candidate có "vô lý" thật
   không + bắt lỗi cần thẩm mỹ/ngữ cảnh + gán severity + giải thích.
4. **Mỗi lỗi phải có `severity` + `confidence` + `evidence`**. False positive là thứ giết
   hệ thống loại này → ưu tiên precision, có pass self-critique/verify.
5. **Phải có bộ chuẩn** (`standard_v1` — tập ảnh/dữ liệu có nhãn lỗi sẵn) để đo precision/recall và tune ngưỡng.
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
  →  Vision Adapter: OCR + CV element detect → schema mục 5   (ảnh CHỈ dùng ở đây)
  →  Rule Engine (tập con tính được từ box+pixel) → candidate_issues
  →  Reasoning: coding-agent CLI headless (Codex/Cline), TEXT-ONLY
        prompt = skill (tiêu chí) + JSON map + candidate → confirm/reject + lỗi text + severity
        khóa output bằng `codex exec --output-schema` (xem F1.1)
  →  Verify/Critic pass (dedup + filter low-confidence)
  →  Aggregate + dedupe → trả về API
```
**Prompt:** structured output khóa bằng `--output-schema` (Codex) · "skill" = file `agents/skills/*.md`
theo nhóm tiêu chí · KHÔNG gửi ảnh (số pixel đã có trong JSON) · ưu tiên precision (confirm/reject
candidate) · 1 lần `codex exec`/ảnh (rẻ). Backend chọn qua env `AGENT_BACKEND` (codex|none).

## 7. Trạng thái & việc tiếp theo
- [x] Chốt kiến trúc (API service, input ảnh duy nhất, vision-only, rule + coding-agent CLI).
- [x] Vision adapter: A0, A3–A10, A12, A13 analyzers (`src/ui_defect/analyzers/`) — CV+OCR+pixel.
      (A1/A2 đã bỏ — DOM/XML; **A11** face/text-in-image: **hoãn Phase 2**, chỉ có spec.)
- [x] Rule engine R1–R4 (`src/ui_defect/rules/`) — geometry, color, image, text.
- [x] **Reasoning: Codex CLI headless** (`agents/codex_client.py` + `backends.py` + `runner.run_review`)
      — text-only, skill files `agents/skills/*.md`, output khóa `--output-schema`. **Thay VLM** (F1.1).
      (Code VLM cũ `g0_framework.py`/`llm_client.py`/`prompts.py` + docs G0–G6/F1.0 **đã xóa**.)
- [x] Tài liệu tiêu chí: tổng hợp + 1 file/tiêu chí ở `docs/tieu-chi/` (sinh bởi `scripts/gen_criteria.py`).
      **Độ phủ thực tế (đối chiếu code):** 🟦 43 có rule tất định · 🟥 52 chỉ agent Codex · ⏳ 26 chưa xử lý / 121.
- [x] Wire rule còn thiếu so với F0.4: **R3-IMG02** (méo tỉ lệ), **R3-IMG09** (scale-mode), **R1-LAY04** (lệch grid) — có test.
- [x] API service (`src/ui_defect/api/`) — FastAPI, POST /analyze, zero-config (chỉ cần ảnh).
- [x] Web UI (`src/ui_defect/web/`) — upload, phân tích, list lỗi + overlay Set-of-Marks
      (bbox màu theo severity, liên kết 2 chiều, filter). FastAPI serve `GET /` + `/static`. Spec: `docs/F2.0-web-ui.md`.
- [x] Pivot VLM→Codex CLI verify end-to-end: ảnh→CV→rule→`codex exec`→findings (mode=codex, lọc FP).
- [x] **Bộ chuẩn `standard_v1` Tier-1 + đo precision/recall** (kiểm thử đột biến schema-level, backend-agnostic) —
      `scripts/gen_standard.py` (42 case: 32 positive 1/rule + 10 negative) + `scripts/score_standard.py`
      (precision/recall/F1 per-rule, cờ `--with-agent` qua `AGENT_BACKEND` để chạy Cline/Codex) +
      `tests/integration/test_standard.py`. Rule-only **P=R=F1=1.000**, phủ **32/32 rule**. Spec: `docs/F4.0-standard-set.md`.
- [x] **Vá gap tích hợp 4 rule chết** (2026-06-04): analyzer A13/A6/A10 sinh field nhưng pipeline không nối
      vào doc → R1-ENV02/03, R3-IMG08, R3-IMG12 không bao giờ fire. Đã thêm field vào schema
      (`Screen.status_bar_h`/`nav_bar_h`, `ImageMeta.possible_placeholder`, `CanonicalDoc.duplicate_pairs`)
      + nối pipeline (A13→screen, A6 conversion, A10→`doc.duplicate_pairs`; gom dedup ảnh về rule R3-IMG12,
      bỏ rule lạ `IMG-dup-*`). Có 6 unit test (`test_rules_wired.py`).
- [x] **Backend Cline** (`agents/cline_client.py` + `backends.py` `AGENT_BACKEND=cline`) — cùng giao diện
      `(prompt,schema)→dict`, cấu hình lệnh qua env `CLINE_*`, schema nhúng prompt + trích JSON. Có 9 unit
      test mock subprocess. Default `CLINE_PROMPT_MODE=stdin` (an toàn trên Windows).
- [x] pytest: **151 pass** (2026-06-05, +30 owleyes rule-only, +8 agent, fix CNT-02 FP SCREAMING_SNAKE).
- [x] **OwlEyes dataset integration** (2026-06-05):
      - `data/owleyes_samples/`: 30 bug + 8 normal ảnh mẫu xem tay (commit vào repo).
      - `tests/integration/test_owleyes.py`: 30 rule-only cases + 8 agent cases (`AGENT_BUG_CASES`).
      - `scripts/owleyes_hitrate.py`: benchmark hit rate / FP rate trên toàn bộ dataset.
      - Fix CNT-02 FP: SCREAMING_SNAKE pattern giờ require underscore (SKIP/DONE không phải key).
      - Fix `issue_type` normalization: `_normalize_issue_type()` map alias → canonical ID.
      - Fix skill `00-system.md`: bảng canonical codes bắt buộc cho `issue_type` field.
      - **Kết quả Codex**: 8/8 agent tests pass, 37/37 rule-only pass.
      - ⚠️ **Cline máy công ty (Windows): 8/8 agent tests FAIL** — "Agent không confirm rule nào trong [...]".
        Cline chạy được (không RuntimeError), nhưng trả `issue_type` tên khác chưa rõ.
        **Việc cần làm phiên tới**: chạy debug script để thấy Cline trả gì, rồi thêm alias vào
        `_normalize_issue_type()` hoặc tune skill. Debug script:
        ```
        $env:AGENT_BACKEND="cline"
        .venv\Scripts\python -c "
        import sys; sys.path.insert(0, 'src')
        from PIL import Image; from ui_defect.api.pipeline import run_pipeline
        img = Image.open('data/owleyes_samples/bug/bug.4200.jpg').convert('RGB')
        w, h = img.size
        out = run_pipeline(img=img, platform='android', viewport_w=w, viewport_h=h, dpr=2.0, run_agents=True)
        print('issue_types:', [i.issue_type for i in out.issues])
        print('errors:', out.pipeline_meta.get('agent_errors'))
        "
        ```
- [ ] **Fix Cline issue_type mismatch** — xem debug output trên Windows, thêm alias vào
      `_normalize_issue_type()` trong `runner.py`. Sau đó re-run 8 agent tests trên máy công ty.
- [ ] **Standard Tier-2** (ảnh thật Playwright) — test full pipeline ảnh→CV→OCR→rule end-to-end. Cần OCR backend.
- [ ] Tinh chỉnh skill files `agents/skills/*.md` theo kết quả thực tế với Cline.
