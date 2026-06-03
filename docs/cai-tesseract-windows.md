# Cài Tesseract OCR trên Windows

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
