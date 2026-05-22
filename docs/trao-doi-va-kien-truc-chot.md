# Trao đổi & kiến trúc chốt

> Nối tiếp `phan-tich-ban-dau.md`. Ghi lại 3 câu hỏi chốt + câu trả lời của chủ dự án,
> kiến trúc suy ra, và **2 chế độ vận hành**. Bản quyết định gọn nằm ở `../CLAUDE.md`.

---

## 1. Ba câu hỏi chốt & câu trả lời

**Q1 — Nguồn dữ liệu: có cây phần tử (DOM/a11y/view hierarchy) hay chỉ có ảnh?**
→ **Tùy nền tảng.** Web có DOM; mobile native hạn chế hơn. Cần thiết kế lai cho cả hai.
→ Bổ sung sau: **đôi khi tester CHỈ có ảnh, không có cây đi kèm.**

**Q2 — Model/runtime để suy luận?**
→ **Option 2 + 3:** dựng thành **Agent** (có Skill/Rule/workflow) **và** dùng **open model
self-host gọi qua API**. Công cụ sẵn có: **Cline trong VSCode** + **tool nội bộ kiểu n8n**
(orchestrate, gọi API).

**Q3 — Bối cảnh chạy thực tế?**
→ **Cung cấp API cho tester.** Tester gửi lên `screenshot` + `xml`/`html` → service phân tích
và trả về lỗi.

---

## 2. Kiến trúc suy ra từ câu trả lời

- **Đây là một API service**, không phải tool chạy nội bộ. Input = ảnh (bắt buộc) + cây phần
  tử (tùy chọn); Output = danh sách lỗi có cấu trúc.
- **Lai web + mobile**: HTML/DOM (web, Playwright) và XML (Android uiautomator / iOS) phải quy
  về **một schema chung**.
- **Runtime**: orchestrate bằng tool kiểu n8n (gọi API) và/hoặc Cline; model suy luận có thể
  là open model self-host gọi qua API (và/hoặc hosted VLM).
- ⇒ Khẳng định hướng **hierarchy-first** ở `phan-tich-ban-dau.md` (Thế giới B) là đúng —
  nhưng KHÔNG bắt buộc, vì không phải lúc nào cũng có cây (xem mục 3).

---

## 3. HAI CHẾ ĐỘ VẬN HÀNH (cùng một schema đầu ra, xuống cấp mượt)

Vì tester **không phải lúc nào cũng gửi cây**, hệ thống phải chạy được cả khi chỉ có ảnh.
Stage **Normalize** có nhiều adapter, đầu ra luôn về schema chung; thêm `source`/`confidence`
để downstream biết độ tin cậy.

| | **Mode A — có cây (DOM/XML)** | **Mode B — chỉ có ảnh** |
|---|---|---|
| Dựng `elements[]` | đọc thẳng từ DOM/XML (ground truth) | OCR + detect element/icon + VLM |
| Contrast / clip | đọc từ computed-style | **đo từ pixel** |
| Rule engine | chạy **đầy đủ** | chạy **tập con** (cái gì tính được từ box+pixel) |
| `source` | `dom` / `xml` | `vision` |
| Confidence | cao | thấp hơn, đánh dấu rõ |

- Element/field từ cây có thể **trộn** với phát hiện từ pixel (vd: cây cho box, pixel cho
  contrast/clip thực tế). Luôn ghi `source` ở cấp element/field.
- Nguyên tắc: **đừng viết code giả định luôn có hierarchy.**

---

## 4. Khác gì so với ý tưởng gốc?

| Ý tưởng gốc | Điều chỉnh |
|---|---|
| Đưa **JSON** cho AI suy luận | Đưa **ảnh + JSON** (multimodal) — pixel là bắt buộc cho >½ tiêu chí |
| Trích xuất bằng phân tích ảnh | **Ưu tiên DOM/XML** (ground truth); ảnh+OCR chỉ khi thiếu cây |
| AI tự phát hiện mọi lỗi | **Tách tất định (rule engine) khỏi phán đoán (VLM)** |
| (không nói tới) | Mỗi lỗi kèm **severity + confidence + evidence**; cần **golden set** đo P/R |
| Giả định có dữ liệu đầy đủ | **2 chế độ** A/B, xuống cấp mượt khi chỉ có ảnh |

---

## 5. Việc tiếp theo (chi tiết ở `../CLAUDE.md` mục 7)
- Parser DOM(HTML) → schema (Mode A) · Parser XML(uiautomator) → schema (Mode A)
- **Vision adapter** cho Mode B (OCR + detect + đo contrast/clip từ pixel) ← nhánh khó, đáng làm sớm
- Rule engine + ngưỡng · Prompt template/few-shot theo nhóm · Golden set + script đo P/R
- **API contract** (request/response) cho tester
