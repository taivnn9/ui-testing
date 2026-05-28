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
- [x] **F0.2** Lock **Canonical Schema v1** → [`docs/F0.2-canonical-schema.md`](F0.2-canonical-schema.md): `screen / image / elements[] / relations[] / candidate_issues[]` + field-level `_sources` + severity **5 mức** (`critical/high/medium/low/trivial`) + Pydantic v2 skeleton.
- [x] **F0.3** Scaffold repo → `src/ui_defect/{schema,analyzers,rules,agents,api,utils}` + `tests/` + `pyproject.toml` + `requirements*.txt` (pip). Python 3.12 hệ thống.
- [x] **F0.4** Chốt **đơn vị & ngưỡng chuẩn** → [`docs/F0.4-thresholds.md`](F0.4-thresholds.md): pt/dp/px↔dpr, touch 44pt/48dp, contrast 4.5/3:1, font 11px, blur Laplacian, hash Hamming, grid 8pt. Ngưỡng `[tune]` cần golden set.

## Phase 1 — Analyzers (bóc tách từng cái → `docs/analyzers/<id>.md`)
> Thứ tự ưu tiên = mở khoá nhiều tiêu chí nhất + chuẩn zero-ref nhất.

**Nhóm "dựng cấu trúc" (Mode A đọc cây / Mode B phải tự dựng):**
- [~] **A1 — Tree Parser** (DOM/XML → schema) `[Mode A]` — **spec ✅** [`analyzers/A1-tree-parser.md`](analyzers/A1-tree-parser.md); chờ chốt Web Capture Contract
- [~] **A2 — Style Reader** (computed-style → canonical style) `[A]` — **spec ✅** [`analyzers/A2-style-reader.md`](analyzers/A2-style-reader.md). Mode A only; contrast tất định khi nền đặc; Mode B/XML style do A4/A8 bù.
- [~] **A3 — Box/Layout Detector** `[B]` — **spec ✅** [`analyzers/A3-box-layout-detector.md`](analyzers/A3-box-layout-detector.md). Hybrid OpenCV+OCR (UIED-style); chờ chốt CV-thuần vs +ML-detector (OmniParser/GroundingDINO).
- [~] **A5 — OCR / Text Extractor** (text + box) `[A·B]` — **spec ✅** [`analyzers/A5-ocr-text-extractor.md`](analyzers/A5-ocr-text-extractor.md). PaddleOCR primary + Tesseract fallback; chạy CẢ 2 mode (Mode A đối chiếu DOM-text↔ảnh để bắt tofu/che/cắt). Chờ chốt engine + bộ ngôn ngữ.
- [~] **A12 — Interactivity Classifier** (đoán phần tử nào tương tác) `[B]` — ⚠ khó — **spec ✅** [`analyzers/A12-interactivity-classifier.md`](analyzers/A12-interactivity-classifier.md). Mode B only (Mode A đã có `interactive`); heuristic đa tín hiệu, precision-first; chờ chốt heuristic-only vs +ML.
- [~] **A6 — Icon/Graphic Detector** `[A·B]` — **spec ✅** [`analyzers/A6-icon-graphic-detector.md`](analyzers/A6-icon-graphic-detector.md). Mode A từ DOM svg/icon-font; Mode B CV (color_count + edge_density). Chờ chốt CV-thuần vs +ML.
- [~] **A7 — Image Region + Meta Reader** (intrinsic vs displayed) `[A·B]` — ⚠ B yếu — **spec ✅** [`analyzers/A7-image-region-meta-reader.md`](analyzers/A7-image-region-meta-reader.md). Mode A đọc naturalW/H → IMG-09 méo; Mode B chỉ blur_score (thiếu intrinsic).

**Nhóm "đo diện mạo" (chạy ở CẢ hai mode):**
- [~] **A4 — Pixel Color Sampler** (contrast/dark/opacity từ pixel thực) `[A·B]` — **spec ✅** [`analyzers/A4-pixel-color-sampler.md`](analyzers/A4-pixel-color-sampler.md). K-means k=2 (Lab) tách fg/bg + WCAG tự code; bù A2 khi nền ảnh/gradient + toàn bộ Mode B/XML.
- [~] **A8 — Pixel/Glyph Inspector** (tofu □ / mờ / emoji-box / banding) `[B]` — **spec ✅** [`analyzers/A8-pixel-glyph-inspector.md`](analyzers/A8-pixel-glyph-inspector.md). CV tất định (Laplacian + connected-comp); **CHỐT cờ `has_replacement` mà A5 chỉ NGHI**.
- [~] **A9 — Pixel Pattern Detector** (skeleton/spinner/overlay/keyboard/splash/broken/blank) `[B]` — **spec ✅** [`analyzers/A9-pixel-pattern-detector.md`](analyzers/A9-pixel-pattern-detector.md). 7 sub-detector CV; 1-frame (cờ `temporal` → "kẹt" chờ Phase 2 đa-frame).
- [~] **A10 — Perceptual Hashing** (ảnh/item trùng — trong-màn ở Phase 1) `[A·B]` — **spec ✅** [`analyzers/A10-perceptual-hashing.md`](analyzers/A10-perceptual-hashing.md). `imagehash.phash` + Hamming; in-screen (cross-screen→Phase 2). Chờ chốt ngưỡng + xử lý trùng-chủ-ý.
- [~] **A11 — Face/Text-in-image Detector** (cho IMG-04 crop) `[B]` — ưu tiên thấp — **spec ✅** [`analyzers/A11-face-text-in-image-detector.md`](analyzers/A11-face-text-in-image-detector.md). MediaPipe face (pretrained) + text-in-image qua IoU(A5,A7). Có thể để Phase 2.
- [~] **A13 — Device/Env Metadata provider** (safe_area/dpr/bar/orientation) `[—]` — **spec ✅** [`analyzers/A13-device-env-metadata.md`](analyzers/A13-device-env-metadata.md). Chạy đầu pipeline; 3 tầng nguồn: tester-meta → device-profile → pixel-infer. Chờ chốt bắt buộc meta? + phạm vi bảng device.

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
