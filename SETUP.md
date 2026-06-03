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

#### Windows (chi tiết)

Code gọi Tesseract qua PATH (không hardcode đường dẫn), nên **bắt buộc thêm Tesseract vào PATH**.

1. **Tải & cài bộ cài** — bản build chính thức của UB Mannheim:
   <https://github.com/UB-Mannheim/tesseract/wiki> → tải `tesseract-ocr-w64-setup-*.exe` (64-bit).

2. **Trong lúc cài, chọn language data** — ở bước *"Select components" → "Additional language data"*,
   tick **Vietnamese** và **English** (cần cho `vie`/`eng`). Mặc định cài vào
   `C:\Program Files\Tesseract-OCR`.
   > Quên tick? Cài lại installer hoặc tải `vie.traineddata`/`eng.traineddata` từ
   > <https://github.com/tesseract-ocr/tessdata> bỏ vào thư mục `...\Tesseract-OCR\tessdata`.

3. **Thêm vào PATH** (để Python tìm được `tesseract.exe`):
   - Mở *Start → "Edit the system environment variables" → Environment Variables*.
   - Trong **System variables**, chọn `Path` → **Edit** → **New** → dán
     `C:\Program Files\Tesseract-OCR` → OK.
   - **Mở lại terminal** (PowerShell/CMD mới) để PATH có hiệu lực.

   Hoặc cài nhanh bằng winget (tự thêm PATH):
   ```powershell
   winget install -e --id UB-Mannheim.TesseractOCR
   ```

4. **Cài Python wrapper** (trong venv đã activate):
   ```powershell
   pip install pytesseract
   ```

5. **Kiểm tra** — terminal MỚI:
   ```powershell
   tesseract --version
   tesseract --list-langs        # phải thấy 'vie' và 'eng'
   python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
   ```

   > **Nếu không muốn / không sửa được PATH:** trỏ trực tiếp tới binary bằng cách thêm dòng sau
   > vào đầu code trước khi gọi OCR (hoặc đặt biến này 1 lần lúc khởi tạo):
   > ```python
   > import pytesseract
   > pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   > ```

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

> Các tùy chọn khác (timeout, OCR remote, gỡ lỗi) xem comment trong `.env.example`.

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

Mẹo: thêm `-F "run_vlm=false"` (hoặc tắt *"Chạy VLM"* trên web) để chạy thuần rule, loại trừ LLM.

---

## Tóm tắt chế độ chạy

| Chế độ | Cần gì | Kết quả |
|---|---|---|
| **Rule-only** (`run_vlm=false`) | pip install + OpenCV | Layout, color, text regex rules |
| **Rule + OCR** | + Tesseract hoặc PaddleOCR | Thêm text detection, CNT/TYP rules |
| **Full** (default) | + llama.cpp server chạy model vision | Tất cả + VLM agents xác nhận |
