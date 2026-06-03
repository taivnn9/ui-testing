# OCR sidecar (PaddleOCR remote)

Tách PaddleOCR sang **máy riêng**. App chính (`ui_defect`) gọi OCR qua HTTP nên
**không cần cài paddle** trên máy app — chỉ set `OCR_BASE_URL`.

```
┌────────────┐  POST /ocr (ảnh base64)   ┌──────────────────────┐
│  app máy A │ ─────────────────────────▶│ OCR sidecar (máy B)  │
│ ui_defect  │ ◀───────────────────────── │ FastAPI + PaddleOCR  │
└────────────┘   {segments:[…]}           └──────────────────────┘
```

## Cài & chạy (trên máy B — máy có paddle)

```bash
cd ocr_service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # kéo paddlepaddle + paddleocr (~1GB)
uvicorn server:app --host 0.0.0.0 --port 8081
```

Kiểm tra: `curl http://<máy-B>:8081/health` → `{"status":"ok",...}`

## Trỏ app sang sidecar (trên máy A)

Trong `.env` của app:
```bash
OCR_BASE_URL=http://<máy-B>:8081
OCR_TIMEOUT_SEC=60
```
Không set `OCR_BASE_URL` → app dùng OCR local (paddle/tesseract nếu cài), hoặc bỏ qua text.

## Contract

| | |
|---|---|
| `POST /ocr` | body `{ "image": "<base64 PNG/JPEG>", "lang": "en" }` |
| → | `{ "engine":"paddle", "segments":[ {"text":str,"bbox":{x,y,w,h},"confidence":float} ] }` |
| `GET /health` | `{ "status":"ok" }` |

`bbox` theo pixel ảnh gốc app gửi lên. `lang`: mã PaddleOCR (`en`, `vi`, `ch`, `japan`, `korean`, …).

> Client phía app: `src/ui_defect/analyzers/a5_ocr.py::_run_ocr_remote`.
> Đổi format ở đây thì sửa cả 2 đầu cho khớp.
