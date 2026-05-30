# Hướng dẫn cài đặt & chạy

## Yêu cầu
- Python 3.11+
- RAM ≥ 4GB (8GB nếu dùng PaddleOCR)
- ANTHROPIC_API_KEY (nếu muốn dùng VLM agents)

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

# Sau đó cài Python wrapper
pip install pytesseract
```

### Option B — PaddleOCR (chính xác hơn, nặng hơn ~1GB)

```bash
# CPU only
pip install paddlepaddle paddleocr

# GPU (CUDA 11.x)
pip install paddlepaddle-gpu paddleocr
```

> Nếu không cài OCR nào → A5 trả `[]` → text rules (R4) và G1/G2 agents không chạy.
> Layout, color, image rules vẫn hoạt động bình thường.

---

## 3. Cấu hình môi trường

```bash
cp .env.example .env
# Mở .env và điền ANTHROPIC_API_KEY
```

---

## 4. Chạy server

```bash
uvicorn src.ui_defect.api.main:app --reload --port 8000
```

Mở trình duyệt: http://localhost:8000/docs (Swagger UI tự động)

---

## 5. Test nhanh

```bash
# Chỉ cần ảnh — không cần field nào khác
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@/path/to/screen.png"

# Rule-only (không gọi Claude API — nhanh, miễn phí)
curl -X POST http://localhost:8000/analyze \
  -F "screenshot=@/path/to/screen.png" \
  -F "run_vlm=false"

# iOS với locale tiếng Việt
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
| **Rule + OCR** | + Tesseract | Thêm text detection, CNT/TYP rules |
| **Full** (default) | + ANTHROPIC_API_KEY | Tất cả + VLM agents xác nhận |
