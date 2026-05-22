# Development Plan — UI Defect AI (Phase 1)

> **Mục đích:** tracker tổng để **không miss task**. Mỗi component lớn (đặc biệt 14 analyzer)
> sẽ được **bóc tách chi tiết từng cái** vào `docs/analyzers/<id>.md` / `docs/agents/<id>.md`
> khi ta đi qua. Trạng thái cập nhật tại đây.
>
> Nguồn gốc: [`catalog-tieu-chi-loi-ui.md`](catalog-tieu-chi-loi-ui.md) (121 tiêu chí) +
> [`buoc-2-kien-truc-xu-ly.md`](buoc-2-kien-truc-xu-ly.md) (kiến trúc + mapping).
> Phiên: 2026-05-22.

**Goal:** API service nhận `screenshot (+ DOM/XML tùy chọn)` → trả danh sách lỗi UI có
`severity / confidence / evidence`, chạy được cả khi có cây (Mode A) lẫn chỉ ảnh (Mode B).

**Architecture:** Analyzers → Normalize (1 schema chung) → Rule Engine (code, tất định)
+ Judgment Agents (VLM) → Verify/Critic → Summary. Tách tất định khỏi phán đoán.

**Tech Stack:** ✅ **Python + FastAPI** + OpenCV/Pillow/numpy + OCR engine (PaddleOCR/Tesseract)
+ lxml/BeautifulSoup (parse DOM/XML) + VLM qua API (Claude/self-host).

**Trạng thái ký hiệu:** `[ ]` chưa làm · `[~]` đang làm · `[x]` xong · `⏭` Phase 2+.

---

## Phase 0 — Nền tảng (làm TRƯỚC, gate mọi thứ)
- [x] **F0.1** Tech stack: **Python + FastAPI** + OpenCV/Pillow/numpy + OCR (PaddleOCR/Tesseract) + lxml/pydantic + VLM qua API.
- [ ] **F0.2** Lock **Canonical Schema v1** (hoàn thiện từ CLAUDE.md §5): `screen / image / elements[] / relations[] / candidate_issues[]` + `source` (dom|xml|vision) + `confidence` + `mode` ở cấp field. → Đây là **contract** mọi analyzer ghi vào.
- [ ] **F0.3** Scaffold repo: cấu trúc thư mục, test framework, lint, CI, định dạng crop/evidence.
- [ ] **F0.4** Chốt **đơn vị & ngưỡng chuẩn**: pt/dp/px↔dpr, touch≥44pt/48dp, contrast 4.5/3, grid 8pt (bảng ngưỡng dùng chung cho Rule Engine).

## Phase 1 — Analyzers (bóc tách từng cái → `docs/analyzers/<id>.md`)
> Thứ tự ưu tiên = mở khoá nhiều tiêu chí nhất + chuẩn zero-ref nhất.

**Nhóm "dựng cấu trúc" (Mode A đọc cây / Mode B phải tự dựng):**
- [~] **A1 — Tree Parser** (DOM/XML → schema) `[Mode A]` — **spec ✅** [`analyzers/A1-tree-parser.md`](analyzers/A1-tree-parser.md); chờ chốt Web Capture Contract
- [ ] **A2 — Style Reader** (computed-style: font/màu/border/align/opacity) `[A]`
- [ ] **A3 — Box/Layout Detector** (element detect + segment + cluster → bounds/parent/child) `[B]`
- [ ] **A5 — OCR / Text Extractor** (text + box) `[B]`
- [ ] **A12 — Interactivity Classifier** (đoán phần tử nào tương tác) `[B]` — ⚠ khó
- [ ] **A6 — Icon/Graphic Detector** `[A·B]`
- [ ] **A7 — Image Region + Meta Reader** (intrinsic vs displayed) `[A·B]` — ⚠ B yếu

**Nhóm "đo diện mạo" (chạy ở CẢ hai mode):**
- [ ] **A4 — Pixel Color Sampler** (contrast/dark/opacity từ pixel thực) `[A·B]`
- [ ] **A8 — Pixel/Glyph Inspector** (tofu □ / mờ / emoji-box / banding) `[B]`
- [ ] **A9 — Pixel Pattern Detector** (skeleton/spinner/overlay/keyboard/splash/broken/blank) `[B]`
- [ ] **A10 — Perceptual Hashing** (ảnh/item trùng — trong-màn ở Phase 1) `[A·B]`
- [ ] **A11 — Face/Text-in-image Detector** (cho IMG-04 crop) `[B]` — ưu tiên thấp
- [ ] **A13 — Device/Env Metadata provider** (safe_area/dpr/bar/orientation) `[—]`

**Gộp:**
- [ ] **A0 — Normalize + Relation pre-computer** (gộp output analyzer → schema chung, tiền tính `relations`: overlap/gap/align; routing Mode A/B/mixed, gán `source` theo field)
- ⏭ **A14 — Cross-screen Matcher** (CONS) → **Phase 2** (cần nhóm ảnh)

## Phase 2 — Rule Engine (code tất định → `candidate_issues`)
- [ ] **R1** Geometry: IoU/overlap · parent-overflow · viewport/off-screen · grid-8pt/gap · alignment · near-dup-pos · scroll-overflow · touch-target · tap-gap · safe-area · icon-centering · badge-geom
- [ ] **R2** Color: WCAG contrast (4.5/3 text, 3:1 graphic) · invisible-text · opacity
- [ ] **R3** Image: distortion-ratio · broken-image · upscale · hash-dup
- [ ] **R4** Text: token/placeholder regex · i18n-key · mojibake/entity · escape-literal · lorem/debug dict · epoch/format · all-caps · stack-trace
- [ ] **R5** Gắn `severity nền + range` (5 mức) cho mỗi rule + bộ **modifier** ngữ cảnh

## Phase 3 — Judgment Agents (VLM, ~6–7 nhóm → `docs/agents/<id>.md`)
> Nhận: ảnh + schema + candidate_issues liên quan. Set-of-Marks · structured output · few-shot · decompose theo nhóm.
- [ ] **G1** Text/Content agent (CNT + TYP nội dung)
- [ ] **G2** Typography-Render agent (TYP pixel)
- [ ] **G3** Color/Style agent (STY phán đoán)
- [ ] **G4** Layout agent (LAY xác nhận)
- [ ] **G5** Image agent (IMG)
- [ ] **G6** Component+State agent (CMP + STATE)
- ⏭ **G7** Consistency agent (CONS, đa ảnh) → **Phase 2**
- [ ] **G0** Prompt framework chung: schema tool-use, Set-of-Marks renderer (vẽ ID lên ảnh), few-shot calibrate severity

## Phase 4 — Verify + Summary
- [ ] **V1** Critic/self-critique pass (lọc confidence thấp, giảm false-positive)
- [ ] **S1** Summary agent: dedupe (1 lỗi nhiều nguồn) + gộp + chốt severity cuối trong range + sắp xếp

## Phase 5 — API contract & service
- [ ] **API1** Request/response schema (input: ảnh + DOM/XML tùy chọn; output: issues[])
- [ ] **API2** Endpoint + orchestrate pipeline + dò mode (A/B/mixed)
- [ ] **API3** Tài liệu API cho tester

## Phase 6 — Golden Set & đo lường (META — sống còn)
- [ ] **GS1** Mutation-testing UI harness (inject lỗi: đổi font/bóp ảnh/nhồi text/đổi màu → positive đã biết)
- [ ] **GS2** Tập ảnh có nhãn (golden set) — cả Mode A & B
- [ ] **GS3** Script đo precision/recall theo từng tiêu chí
- [ ] **GS4** Tune ngưỡng rule + calibrate severity dựa trên P/R

---

## Cross-cutting (áp cho mọi task, đừng quên)
- **Mode A/B/mixed routing** (mục 1.4 buoc-2): không giả định luôn có cây; `source` theo field.
- **Severity** 5 mức `critical/high/medium/low/trivial` = baseline + range + modifier.
- **Evidence** mỗi issue: element_id, bbox, crop, giá trị đo, rule_id.
- **Confidence** ở cấp field & issue; Mode B + ctx/temporal → đánh dấu thấp.
- **Precision-first**: false-positive là thứ giết hệ thống.

## Quyết định đang chờ
- [ ] **F0.1 tech stack** (đang hỏi).
- [ ] Granularity agent ~6–7 nhóm (đề xuất ở Phase 3, chốt khi tới).
- [ ] Deploy: 1 service monolith hay analyzer tách microservice gọi từ n8n? *(Phase 1 đề xuất monolith)*

## Tiến độ tổng
- [x] Bước 1 — catalog 121 tiêu chí.
- [x] Bước 2 — kiến trúc + mapping + phasing.
- [~] **Bóc tách analyzer** (đang ở đây) — bắt đầu sau khi chốt F0.1.
