# Hướng dẫn dùng giao diện web

Trang web do chính FastAPI phục vụ — **không cần cài thêm gì** (không Node/build).
Sau khi chạy server (xem [SETUP.md](../SETUP.md)), mở **http://localhost:8000/**.

## Các bước
1. **Tải ảnh**: kéo-thả (hoặc bấm chọn) ảnh PNG/JPG vào vùng upload → ảnh hiện preview.
2. **(Tùy chọn) Cài đặt nâng cao**: bấm nút *"Cài đặt nâng cao"* để chỉnh:
   - `platform` (android / ios / web)
   - `min_severity` — mức lỗi tối thiểu muốn hiện
   - `min_confidence` — ngưỡng tin cậy
   - **"Chạy VLM"** — tắt = rule-only (nhanh, không cần llama.cpp); bật = có thêm VLM agents.
3. **Phân tích**: bấm nút *"Phân tích"* và chờ kết quả.
4. **Đọc kết quả**:
   - **Cột trái** — ảnh với **khung lỗi đánh số**, màu theo mức nghiêm trọng
     (🟥 critical · 🟧 high · 🟨 medium · 🟦 low · ⬜ trivial).
   - **Cột phải** — danh sách lỗi. Bấm 1 lỗi để xem chi tiết và **highlight khung tương ứng**
     trên ảnh (liên kết 2 chiều: bấm khung cũng highlight lỗi trong list).
   - Bấm các **chip severity** ở phần summary để ẩn/hiện lỗi theo từng mức.

> Tester chỉ cần ảnh; mọi metadata (theme/locale/viewport) hệ thống tự suy từ ảnh.

## Khi có lỗi
- Banner **đỏ** = lỗi xử lý (HTTP 4xx/5xx) — xem chi tiết & cách gỡ ở [go-loi.md](go-loi.md).
- Banner **vàng** = VLM agent lỗi nhưng phân tích vẫn chạy bằng rule (thường do cấu hình
  `LLM_BASE_URL` sai) — xem [go-loi.md](go-loi.md).

> Thiết kế & kiến trúc chi tiết của Web UI: [F2.0-web-ui.md](F2.0-web-ui.md).
