# Hướng dẫn cài đặt & chạy

## Yêu cầu
- Python 3.11+
- RAM ≥ 4GB (8GB nếu dùng PaddleOCR)
- **Codex CLI** đã đăng nhập (`codex login`) — dùng cho tầng reasoning (xem mục 3).
  Không dùng thì vẫn chạy được ở chế độ rule-only (`run_vlm=false`).

---

## 1. Clone & cài dependencies

```bash
git clone https://github.com/taivnn9/ui-testing.git
cd ui-testing

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e .
```

---

## 2. Cài OCR backend (chọn 1)

### Option 0 — OCR remote (paddle ở máy khác) — khuyến nghị nếu tách máy

App **không cần cài paddle**. Chạy sidecar trên máy có paddle rồi trỏ env:

```bash
# Trên MÁY OCR (có paddle): xem ocr_service/README.md
cd ocr_service && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8081

# Trên MÁY APP: thêm vào .env
OCR_BASE_URL=http://<máy-OCR>:8081
```
→ Bỏ qua Option A/B bên dưới. Không set `OCR_BASE_URL` thì app dùng OCR local:

### Option A — Tesseract (nhẹ hơn, khuyến nghị thử trước)

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng

# macOS
brew install tesseract

# Python wrapper (mọi OS)
pip install pytesseract
```

> Windows: cần thêm Tesseract vào PATH — xem [docs/cai-tesseract-windows.md](docs/cai-tesseract-windows.md).

### Option B — PaddleOCR (chính xác hơn, nặng hơn ~1GB)

```bash
pip install paddlepaddle paddleocr          # CPU
# hoặc: pip install paddlepaddle-gpu paddleocr  # GPU CUDA
```

> Nếu không cài OCR nào → text rules (R4) và G1/G2 agents sẽ không detect text.
> Layout, color, image rules vẫn hoạt động bình thường.

---

## 3. Cấu hình môi trường

Tầng reasoning dùng **Codex CLI headless** (`codex exec`) — chỉ cần đăng nhập Codex 1 lần:
```bash
codex login          # đăng nhập (ChatGPT hoặc API key)
codex login status   # kiểm tra
```

(Tùy chọn) tạo `.env` để chỉnh backend/sandbox:
```bash
cp .env.example .env
```
```bash
AGENT_BACKEND=codex            # codex | none(=rule-only)
CODEX_SANDBOX=workspace-write  # quyền đọc/ghi file trong project
# CODEX_MODEL=                 # bỏ trống = mặc định của codex
```

> Các tùy chọn khác (timeout, OCR remote, gỡ lỗi) xem comment trong `.env.example`.
>
> `.env` được **nạp tự động** khi chạy app. **Sửa `.env` xong phải khởi động lại server** mới có hiệu lực.

---

## 4. Chạy server

```bash
uvicorn src.ui_defect.api.main:app --reload --port 8000
```

- **Giao diện web:** http://localhost:8000/ — upload ảnh, ấn Phân tích, xem lỗi trực quan.
  Cách dùng: [docs/huong-dan-web-ui.md](docs/huong-dan-web-ui.md).
- **Swagger UI (API docs):** http://localhost:8000/docs

---

## 5. Test nhanh

```bash
# Minimal — chỉ cần ảnh
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen.png"

# Rule-only — không gọi LLM (nhanh, dùng để debug)
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen.png" \
  -F "run_vlm=false"

# iOS, tiếng Việt, retina
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@screen.png" \
  -F "platform=ios" \
  -F "locale=vi-VN" \
  -F "dpr=3"
```

---

## 6. Chạy tests

```bash
pip install -e ".[dev]"
pytest
```

---

## 7. Gặp lỗi?

Đặt `DEBUG_ERRORS=1` (mặc định) để thấy chi tiết lỗi trong console server và response.
Hướng dẫn đọc lỗi & phân biệt lỗi cấu hình vs lỗi code: [docs/go-loi.md](docs/go-loi.md).

Mẹo: thêm `-F "run_vlm=false"` (hoặc tắt *"Chạy agent reasoning"* trên web) để chạy thuần rule, không gọi Codex.

---

## Tóm tắt chế độ chạy

| Chế độ | Cần gì | Kết quả |
|---|---|---|
| **Rule-only** (`run_vlm=false`) | pip install + OpenCV | Layout, color, text regex rules |
| **Rule + OCR** | + Tesseract hoặc PaddleOCR | Thêm text detection, CNT/TYP rules |
| **Full** (default) | + Codex CLI đã `codex login` | Tất cả + agent reasoning xác nhận/lọc (text-only) |
