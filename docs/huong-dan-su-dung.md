# Hướng dẫn sử dụng

> **TL;DR:** Cách chạy & dùng (web UI + API), cài Tesseract OCR trên Windows, và cách đọc lỗi.
> Cài đặt môi trường: [../SETUP.md](../SETUP.md). Kiến trúc Web UI: [F2.0-web-ui.md](F2.0-web-ui.md).

## 1. Dùng giao diện web

FastAPI phục vụ luôn trang web — **không cần cài thêm** (không Node/build). Chạy server (xem
[SETUP.md](../SETUP.md)) rồi mở **http://localhost:8000/**.

1. **Tải ảnh** — kéo-thả hoặc bấm chọn ảnh PNG/JPG → hiện preview.
2. **(Tùy chọn) Cài đặt nâng cao:**
   - `platform`: android / ios / web
   - `min_severity`: mức lỗi tối thiểu muốn hiện
   - `min_confidence`: ngưỡng tin cậy
   - **"Chạy agent reasoning"** — tắt = rule-only (nhanh, không gọi agent); bật = agent
     (Codex/Cline) xác nhận/lọc candidate + bắt thêm lỗi text (cần `codex login`).
3. **Bấm "Phân tích"** và chờ.
4. **Đọc kết quả:**
   - **Cột trái** — ảnh + khung lỗi đánh số, màu theo mức: 🟥 critical · 🟧 high · 🟨 medium · 🟦 low · ⬜ trivial.
   - **Cột phải** — danh sách lỗi. Bấm 1 lỗi → highlight khung tương ứng (liên kết 2 chiều).
   - Bấm **chip severity** ở summary để ẩn/hiện lỗi theo mức.

> Tester chỉ cần ảnh; metadata (theme/locale/viewport) hệ thống tự suy từ ảnh.

## 2. Gọi API trực tiếp

Chi tiết đầy đủ: [api-contract.md](api-contract.md). Tối giản:

```bash
# Chỉ cần ảnh
curl -X POST http://localhost:8000/analyze -F "screenshot=@screen.png"

# Rule-only (không gọi agent — nhanh, để debug)
curl -X POST http://localhost:8000/analyze -F "screenshot=@screen.png" -F "agent_backend=none"
```

## 3. Cài Tesseract OCR (Windows)

Code gọi Tesseract qua PATH (không hardcode), nên **phải thêm Tesseract vào PATH**.

1. **Cài bộ cài UB Mannheim** (64-bit): <https://github.com/UB-Mannheim/tesseract/wiki> →
   `tesseract-ocr-w64-setup-*.exe`.
2. **Chọn language data** ở bước *"Additional language data"*: tick **Vietnamese** + **English**
   (cho `vie`/`eng`). Mặc định cài vào `C:\Program Files\Tesseract-OCR`.
   > Quên tick? Tải `vie.traineddata`/`eng.traineddata` từ
   > <https://github.com/tesseract-ocr/tessdata> bỏ vào `...\Tesseract-OCR\tessdata`.
3. **Thêm vào PATH:** System variables → `Path` → New → `C:\Program Files\Tesseract-OCR` → OK.
   Mở **terminal mới** để PATH có hiệu lực. Hoặc nhanh: `winget install -e --id UB-Mannheim.TesseractOCR`.
4. **Cài wrapper:** `pip install pytesseract` (trong venv).
5. **Kiểm tra** (terminal mới):
   ```powershell
   tesseract --version
   tesseract --list-langs        # phải thấy 'vie' và 'eng'
   ```
   > Không sửa được PATH? Trỏ thẳng tới binary trong code:
   > `pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"`

## 4. Đọc & gỡ lỗi

Giai đoạn dev để **`DEBUG_ERRORS=1`** (mặc định) để thấy chi tiết. Mức log qua `LOG_LEVEL`
(`INFO`|`DEBUG`|`WARNING`).

**Console server (uvicorn):** luôn in full traceback khi pipeline lỗi (file/dòng/hàm) — nơi đầu tiên nên nhìn.

**Trong response:**

| Triệu chứng | Nghĩa | Nguyên nhân |
|---|---|---|
| Banner **đỏ** / HTTP 500 + `traceback` | Pipeline hỏng | **Lỗi code** |
| Banner **vàng** / HTTP 200 + `pipeline_meta.agent_errors` | Agent lỗi nhưng vẫn trả kết quả rule | **Cấu hình** (chưa cài/đăng nhập Codex…) |

Lỗi 500: `detail` có `stage`, `type`, `message`, `cause`, `traceback` (khi `DEBUG_ERRORS=1`).
Lỗi agent KHÔNG làm hỏng phân tích → degrade graceful, vẫn HTTP 200 (giữ kết quả rule).

Ví dụ lỗi agent (cấu hình):
```
RuntimeError: Không tìm thấy Codex CLI 'codex'. Cài Codex hoặc đặt env CODEX_BIN.
RuntimeError: Codex exec exit=1 ... (chưa codex login / hết quota / sandbox)
```

**Mẹo:**
- Tách agent ra khi debug: gửi `agent_backend=none` (hoặc tắt *"Chạy agent reasoning"* trên web) → chạy thuần rule.
- Kiểm tra Codex độc lập: `echo 'hi' | codex exec --ephemeral -s read-only -` và `codex login status`.
- **Production:** đặt `DEBUG_ERRORS=0` để response không lộ traceback (console vẫn log đầy đủ).
