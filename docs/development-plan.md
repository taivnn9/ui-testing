# Development Plan — UI Defect AI (Phase 1)

> ⚠️ **Cập nhật 2026-06-03:** tầng reasoning đã đổi VLM → **Codex CLI text-only** ([`F1.1`](F1.1-codex-cli-architecture.md)).
> Các task/mô tả nhắc VLM/llama.cpp ở dưới hiểu theo backend mới. Trạng thái mới nhất ở `../CLAUDE.md` §7.

> **Mục đích:** tracker tổng để **không miss task**. Mỗi component lớn (đặc biệt 14 analyzer)
> sẽ được **bóc tách chi tiết từng cái** vào `docs/analyzers/<id>.md` / `docs/agents/<id>.md`
> khi ta đi qua. Trạng thái cập nhật tại đây.
>
> Nguồn gốc: [`catalog-tieu-chi-loi-ui.md`](catalog-tieu-chi-loi-ui.md) (121 tiêu chí) +
> [`tieu-chi/`](tieu-chi/README.md) (đánh giá từng tiêu chí).
> Phiên: 2026-05-22.

**Goal:** API service nhận `screenshot (PNG)` → trả danh sách lỗi UI có
`severity / confidence / evidence`, vision-only (không nhận DOM/XML).

**Architecture:** Analyzers → Normalize (1 schema chung) → Rule Engine (code, tất định)
+ Judgment Agents (VLM) → Verify/Critic → Summary. Tách tất định khỏi phán đoán.

**Tech Stack:** ✅ **Python + FastAPI** + OpenCV/Pillow/numpy + OCR engine (PaddleOCR/Tesseract)
+ VLM qua API (Claude/self-host).

**Trạng thái ký hiệu:** `[ ]` chưa làm · `[~]` đang làm · `[x]` xong · `⏭` Phase 2+.

---

## Phase 0 — Nền tảng (làm TRƯỚC, gate mọi thứ)
- [x] **F0.1** Tech stack: **Python + FastAPI** + OpenCV/Pillow/numpy + OCR (PaddleOCR/Tesseract) + pydantic + VLM qua API.
- [x] **F0.2** Lock **Canonical Schema v1** → [`docs/F0.2-canonical-schema.md`](F0.2-canonical-schema.md): `screen / image / elements[] / relations[] / candidate_issues[]` + field-level `_sources` + severity **5 mức** (`critical/high/medium/low/trivial`) + Pydantic v2 skeleton.
- [x] **F0.3** Scaffold repo → `src/ui_defect/{schema,analyzers,rules,agents,api,utils}` + `tests/` + `pyproject.toml` + `requirements*.txt` (pip). Python 3.12 hệ thống.
- [x] **F0.4** Chốt **đơn vị & ngưỡng chuẩn** → [`docs/F0.4-thresholds.md`](F0.4-thresholds.md): pt/dp/px↔dpr, touch 44pt/48dp, contrast 4.5/3:1, font 11px, blur Laplacian, hash Hamming, grid 8pt. Ngưỡng `[tune]` cần golden set.

## Phase 1 — Analyzers (bóc tách từng cái → `docs/analyzers/<id>.md`)
> Thứ tự ưu tiên = mở khoá nhiều tiêu chí nhất + chuẩn zero-ref nhất.

> ~~**A1 — Tree Parser**~~ (đã bỏ — không còn DOM/XML input)
> ~~**A2 — Style Reader**~~ (đã bỏ — không còn DOM/XML input)

**Nhóm "dựng cấu trúc" (vision-only, tự dựng từ ảnh):**
- [x] **A3 — Box/Layout Detector** `[vision]` — code ✅ `src/ui_defect/analyzers/a3_box_layout.py`. OpenCV CV core; ML add-on dành Phase 2 sau golden set.
- [x] **A5 — OCR / Text Extractor** (text + box) `[vision]` — code ✅ `src/ui_defect/analyzers/a5_ocr.py`. PaddleOCR primary + Tesseract fallback.
- [ ] **A12 — Interactivity Classifier** (đoán phần tử nào tương tác) `[vision]` — ⚠ khó — **spec ✅** [`analyzers/A12-interactivity-classifier.md`](analyzers/A12-interactivity-classifier.md). Chưa code.
- [x] **A6 — Icon/Graphic Detector** `[vision]` — code ✅ `src/ui_defect/analyzers/a6_icon_detector.py`. CV: color_count + edge_density + template matching.
- [ ] **A7 — Image Region + Meta Reader** (intrinsic vs displayed) `[vision]` — ⚠ yếu khi thiếu intrinsic — **spec ✅** [`analyzers/A7-image-region-meta-reader.md`](analyzers/A7-image-region-meta-reader.md). Chưa code.

**Nhóm "đo diện mạo":**
- [x] **A4 — Pixel Color Sampler** (contrast/dark/opacity từ pixel thực) `[vision]` — code ✅ `src/ui_defect/analyzers/a4_pixel_color.py`. K-means k=2 Lab + WCAG tự code.
- [x] **A8 — Pixel/Glyph Inspector** (tofu □ / mờ / emoji-box / banding) `[vision]` — code ✅ `src/ui_defect/analyzers/a8_glyph_inspector.py`. Laplacian + connected-comp.
- [x] **A9 — Pixel Pattern Detector** (skeleton/spinner/overlay/keyboard/splash/broken/blank) `[vision]` — code ✅ `src/ui_defect/analyzers/a9_pixel_pattern.py`. 7 sub-detector CV.
- [x] **A10 — Perceptual Hashing** (ảnh/item trùng — trong-màn ở Phase 1) `[vision]` — code ✅ `src/ui_defect/analyzers/a10_perceptual_hash.py`. `imagehash.phash` + Hamming.
- [ ] **A11 — Face/Text-in-image Detector** → **Phase 2** (ưu tiên thấp).
- [x] **A13 — Device/Env Metadata provider** (safe_area/dpr/bar/orientation) `[vision]` — code ✅ `src/ui_defect/analyzers/a13_device_meta.py`. 3 tầng: tester-meta → device-profile → pixel-infer.

**Gộp:**
- [x] **A0 — Normalize + Relation pre-computer** — code ✅ `src/ui_defect/analyzers/a0_normalize.py`. Deduplicate + fill bbox_norm + tiền tính relations.
- ⏭ **A14 — Cross-screen Matcher** (CONS) → **Phase 2** (cần nhóm ảnh)

## Phase 2 — Rule Engine (code tất định → `candidate_issues`)
> **Spec ✅** toàn bộ R1–R5 tại `docs/rules/`. Chờ implement.
- [~] **R1** Geometry — **spec ✅** [`rules/R1-geometry.md`](rules/R1-geometry.md): 15 rules (LAY, CMP, ENV)
- [~] **R2** Color — **spec ✅** [`rules/R2-color.md`](rules/R2-color.md): 6 rules (STY)
- [~] **R3** Image — **spec ✅** [`rules/R3-image.md`](rules/R3-image.md): 6 rules (IMG), phụ thuộc A7
- [~] **R4** Text — **spec ✅** [`rules/R4-text.md`](rules/R4-text.md): 10 rules (CNT/TYP/STATE), regex thuần
- [~] **R5** Severity+Modifier — **spec ✅** [`rules/R5-severity.md`](rules/R5-severity.md): bảng baseline + modifier ngữ cảnh + auto-confirm logic

## Phase 3 — Reasoning: Coding-agent CLI (Codex) — *đã pivot khỏi VLM*
> Tầng reasoning = **Codex CLI headless text-only** (xem [`F1.1`](F1.1-codex-cli-architecture.md)).
> Spec VLM G0–G6 cũ **đã xóa**; tiêu chí nay sống ở `agents/skills/*.md` + [`tieu-chi/`](tieu-chi/README.md).
- [x] `agents/codex_client.py` + `backends.py` + `runner.run_review` (1 call text-only, `--output-schema`).
- [x] Skill files theo nhóm tiêu chí: `agents/skills/{10-text,20-typography,30-color-style,40-layout,50-images,60-components-states}.md`.
- ⏭ **Consistency (CONS, đa ảnh)** → **Phase 2**.

## Phase 4 — Verify + Summary
- [~] **V1** Critic — **spec ✅** [`agents/V1-critic.md`](agents/V1-critic.md): cross-validate findings, dedup code, false positive filter
- [~] **S1** Summary — **spec ✅** [`agents/S1-summary.md`](agents/S1-summary.md): severity finalization, sort priority, API response format, issue ID

## Phase 5 — API contract & service
- [~] **API1/2/3** — **spec ✅** [`docs/api-contract.md`](api-contract.md): POST /analyze multipart,
  request params (platform/viewport/locale/theme/safe_area), response schema đầy đủ,
  error codes, pipeline orchestration code, SLO targets (< 12s E2E)

## Phase 6 — Golden Set & đo lường (META — sống còn)
- [ ] **GS1** Mutation-testing UI harness (inject lỗi: đổi font/bóp ảnh/nhồi text/đổi màu → positive đã biết)
- [ ] **GS2** Tập ảnh có nhãn (golden set) — vision-only
- [ ] **GS3** Script đo precision/recall theo từng tiêu chí
- [ ] **GS4** Tune ngưỡng rule + calibrate severity dựa trên P/R

---

## Cross-cutting (áp cho mọi task, đừng quên)
- **Vision-only**: mọi element/style/geometry từ ảnh; `source: "vision" | "pixel"` theo field.
- **Severity** 5 mức `critical/high/medium/low/trivial` = baseline + range + modifier.
- **Evidence** mỗi issue: element_id, bbox, crop, giá trị đo, rule_id.
- **Confidence** ở cấp field & issue; ctx/temporal → đánh dấu thấp.
- **Precision-first**: false-positive là thứ giết hệ thống.

## Quyết định đang chờ
- [x] **F0.1 tech stack** — Python + FastAPI + OpenCV + PaddleOCR + scikit-learn + VLM API.
- [ ] **A12 Interactivity Classifier** — heuristic-only vs +ML (chưa code).
- [ ] **A7 Image Region Meta Reader** — chưa code.
- [ ] Granularity agent ~6–7 nhóm (đề xuất ở Phase 3, chốt khi tới).
- [ ] Deploy: 1 service monolith hay analyzer tách microservice gọi từ n8n? *(đề xuất monolith)*

## Tiến độ tổng — cập nhật 2026-05-29
- [x] Bước 1 — catalog 121 tiêu chí.
- [x] Bước 2 — kiến trúc + mapping + phasing.
- [x] **Phase 0** — schema, thresholds, scaffold xong.
- [x] **Phase 1** — tất cả analyzers code xong (A0/A3–A13).
- [x] **Phase 2** — Rule Engine code xong (R1–R4 + patterns + severity).
- [x] **Phase 3** — Agents code xong (G0 SoM+wrapper, G1–G6 runner, V1 critic, S1 summary).
- [x] **Phase 4** — Verify + Summary code xong (critic.py + summary.py).
- [x] **Phase 5** — FastAPI endpoint code xong (api/main.py + pipeline.py).
- [ ] **Phase 6** — Golden Set + đo P/R (chưa bắt đầu).
- [ ] **Testing** — chạy pytest, fix issues thực tế.
- [ ] **Integration test** — gọi thật với ảnh mẫu.
