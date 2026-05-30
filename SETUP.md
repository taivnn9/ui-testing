# Hướng dẫn cài đặt & chạy

## Yêu cầu
- Python 3.11+
- RAM ≥ 4GB (8GB nếu dùng PaddleOCR)
- llama.cpp server đang chạy với model vision (Gemma 4 hoặc tương đương)

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

### Option A — Tesseract (nhẹ hơn, khuyến nghị thử trước)

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng

# macOS
brew install tesseract

# Python wrapper
pip install pytesseract
```

### Option B — PaddleOCR (chính xác hơn, nặng hơn ~1GB)

```bash
pip install paddlepaddle paddleocr          # CPU
# hoặc: pip install paddlepaddle-gpu paddleocr  # GPU CUDA
```

> Nếu không cài OCR nào → text rules (R4) và G1/G2 agents sẽ không detect text.
> Layout, color, image rules vẫn hoạt động bình thường.

---

## 3. Cấu hình môi trường

```bash
cp .env.example .env
```

Mở `.env` và sửa:
```bash
LLM_BASE_URL=http://<địa_chỉ_llama_cpp_server>:8080
LLM_MODEL=gemma-4        # tên model đang serve trên llama.cpp
LLM_API_KEY=none         # điền nếu server yêu cầu auth
```

---

## 4. Chạy server

```bash
uvicorn src.ui_defect.api.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

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

## Tóm tắt chế độ chạy

| Chế độ | Cần gì | Kết quả |
|---|---|---|
| **Rule-only** (`run_vlm=false`) | pip install + OpenCV | Layout, color, text regex rules |
| **Rule + OCR** | + Tesseract hoặc PaddleOCR | Thêm text detection, CNT/TYP rules |
| **Full** (default) | + llama.cpp server chạy model vision | Tất cả + VLM agents xác nhận |
