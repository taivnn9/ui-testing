# Phân tích ban đầu: Giải pháp tự động phân tích lỗi UI bằng AI

> **Lưu ý:** tài liệu lịch sử (phân tích mở đầu). Trạng thái & quyết định hiện tại xem ../CLAUDE.md và OVERVIEW.md.

> **TL;DR:** Phân tích mở đầu (phiên 2026-05-21) trả lời 4 câu hỏi gốc: tiêu chí đủ chưa, lấy dữ liệu gì/thế nào, tổ chức dữ liệu ra sao, làm sao AI làm đúng. Nhiều đề xuất ở đây (multimodal, dùng view hierarchy/DOM) **đã bị đảo ngược** về sau — chốt cuối: vision-only + reasoning text-only (xem ../CLAUDE.md).

> ⚠️ Ví dụ trong file dùng **4 mức severity cũ** (`blocker/major/minor/cosmetic`); schema hiện hành đã đổi sang **5 mức** `critical/high/medium/low/trivial`.

---

## Bối cảnh & ý tưởng gốc

Pipeline gốc: "Trích xuất → JSON map → đưa **JSON** cho AI suy luận." Phân tích này chỉ ra 4 vấn đề và đề xuất hướng đi.

## 1. Bộ tiêu chí đã đủ chưa? — Chưa

Bộ 4 nhóm gốc (Text · Images · Spatial · Components) thiên về *layout tĩnh*, thiếu các nhóm lỗi hay gặp & rẻ nhất trong QA mobile:

- **Placeholder/biến chưa render:** `undefined`, `NaN`, `%s`, `{{user.name}}`, `lorem ipsum`, i18n key lòi ra.
- **i18n/localization:** sai ngôn ngữ, chưa dịch, text nở dài vỡ layout, RTL.
- **Safe area / notch / system bars / bàn phím che input.**
- **States:** skeleton kẹt, empty/error state, ảnh vỡ.
- **Dark mode / font scale** làm vỡ layout.
- **Nhất quán xuyên màn** (cùng nút khác cỡ, lệch màu/font) — *cần so nhiều ảnh*.
- **Truncation chủ ý vs lỗi · Z-order/occlusion · trùng lặp/thiếu · lệch grid/optical alignment.**

Và 2 thứ sống còn (thuộc tính mỗi phát hiện, không phải tiêu chí):

1. **Severity + Confidence + Evidence** trên mọi lỗi (mức độ, độ tin cậy 0–1, bằng chứng: element_id/bbox/crop/rule). Thiếu → QA chết chìm trong noise; **false positive giết hệ thống**.
2. **"Nội dung hợp lý" là khó nhất** — bản chất *cần reference*; zero-reference rất yếu ở nhóm này → phải hạ kỳ vọng hoặc cấp thêm ngữ cảnh (tên màn, intent test).

→ Bộ tiêu chí đầy đủ về sau thành **catalog 121 tiêu chí / 9 nhóm** (`catalog-tieu-chi-loi-ui.md`).

## 2. Lấy dữ liệu gì & thế nào? *(đề xuất gốc — sau bị đảo)*

Phân tích gốc lập luận: hơn nửa tiêu chí **không thể** phán đoán chỉ từ bounding box + text (contrast, ảnh méo, tofu, nội dung ngữ cảnh đều cần pixel). Từ đó đề xuất:

- **Đa phương thức (multimodal):** đưa cho AI cả ảnh screenshot + JSON map.
- **Ưu tiên môi trường instrumented** (Playwright/Appium) để lấy thẳng view hierarchy/DOM làm "ground truth" toạ độ + role + text + style, thay vì OCR pixel nhiễu.

> ⚠️ **Đã đảo ngược.** Chốt cuối: **vision-only** (CV+OCR trích map, không DOM/XML) + **reasoning text-only** (pixel cần thiết được CV tính sẵn thành số/flag trong JSON, không gửi ảnh cho model). Lý do: user không có model multimodal; tầng lý luận chuyển sang **agent reasoning (Codex/Cline)** chạy CLI headless text-only. Xem ../CLAUDE.md §2–3.

Mô hình 4 tầng dữ liệu đề xuất gốc (vẫn còn giá trị tham khảo): A cây phần tử (ground truth) · B đặc trưng hình học tính bằng code (rule engine tất định) · C đặc trưng pixel per-element (crop) · D ảnh gốc.

## 3. Tổ chức dữ liệu — schema chuẩn hoá + quan hệ tiền-tính

Mấu chốt **vẫn đúng tới nay**: đừng bắt LLM tự suy quan hệ không gian từ toạ độ thô (suy kém, hay sai) → **tiền-tính** rồi đưa vào JSON.

- Phân cấp: `parent/children` + `z`.
- Quan hệ tương đối (`left_of`/`above`/`contains`/`overlaps`) tiền-tính trong `relations`.
- `candidate_issues` = output rule engine, đưa kèm để tầng lý luận *xác nhận/bác bỏ* thay vì tự mò.

> Schema canonical đầy đủ (đã cập nhật) ở ../CLAUDE.md §5 và `F0.2-canonical-schema.md`.

## 4. Làm sao Agent/Model làm ĐÚNG?

Nguyên tắc xương sống (**vẫn là kim chỉ nam**):

> **Cái gì tính được thì để code tính (tất định). Chỉ hỏi AI cái cần phán đoán.**

LLM dở số học toạ độ → rule engine lo overlap, touch-target nhỏ, contrast thấp (có công thức). Tầng lý luận chỉ: (a) xác nhận candidate có *thật sự vô lý* không, (b) bắt lỗi cần thẩm mỹ/ngữ cảnh, (c) gán severity + giải thích.

**Pipeline gốc** (cấu trúc còn nguyên, riêng "VLM reasoning ảnh+JSON" → nay là **agent reasoning text-only**):
```
Capture → Normalize (schema) → Rule Engine (candidate_issues)
   → Reasoning (confirm/reject + lỗi phán đoán + severity)
   → Verify/Critic (giảm false positive) → Aggregate + dedupe + report
```

**Chiến lược prompt:**
1. **Structured output bắt buộc** (JSON schema), không free text.
2. **Decompose theo nhóm tiêu chí** (checklist/nhóm), không hỏi "tìm hết bug" 1 phát.
3. **Set-of-Marks** — gắn ID lên phần tử để model trỏ theo ID thay vì đoán toạ độ.
4. **Few-shot có nhãn** để calibrate severity.
5. **Self-critique pass** — chỉ giữ confidence cao, giảm false positive.

**Rule / Skill / Workflow:**
- **Rule** = tiêu chí + ngưỡng máy đọc (touch ≥44pt/48dp, contrast ≥4.5:1, grid 8pt…); chia *tất định* (code) và *soft* (guidance cho model).
- **Skill** = playbook tái dùng / 1 screenshot (rubric, schema, template prompt, few-shot, định nghĩa check).
- **Workflow** = orchestration cả pipeline + chạy batch (spawn subagent song song).

**Phần META 90% dự án quên → rồi sập:**
> **Phải có Standard Set** — tập screenshot có nhãn lỗi sẵn để đo **precision/recall**, tune ngưỡng. Mẹo tạo positive nhanh: **mutation testing UI** (inject lỗi: đổi font-size, bóp ảnh, nhồi text dài, đổi màu). → Về sau thành bộ chuẩn `standard_v1`.
