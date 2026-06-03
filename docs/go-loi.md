# Gỡ lỗi — xem lý do khi lỗi

Giai đoạn dev đặt **`DEBUG_ERRORS=1`** (mặc định) để thấy chi tiết. Có 2 nơi xem.

## A. Console server (uvicorn)
Luôn in **full traceback** khi pipeline lỗi (chỉ rõ file / dòng / hàm), kể cả khi
`DEBUG_ERRORS=0`. Đây là nơi đầu tiên nên nhìn.

Cấu hình mức log qua `LOG_LEVEL` (`INFO` | `DEBUG` | `WARNING`).

## B. Response trả về

### Lỗi 500 (pipeline hỏng)
`detail` là object có `stage`, `type`, `message`, `cause`, và `traceback` (khi
`DEBUG_ERRORS=1`). Web UI hiện thẳng traceback trong banner đỏ.
```jsonc
{"detail": {"error":"pipeline_failed","stage":"pipeline",
            "type":"KeyError","message":"'x'","traceback":[ "...", "..." ]}}
```

### Lỗi VLM/LLM KHÔNG làm hỏng phân tích
Pipeline degrade graceful → vẫn trả **HTTP 200**, xem **`pipeline_meta.agent_errors`**.
Web UI hiện **banner vàng**. Lỗi kết nối kèm rõ **URL + model + timeout + nguyên nhân**:
```
RuntimeError: Không gọi được LLM tại http://host:8080/v1/chat/completions
(model=gemma-4, timeout=120s): ConnectError: [Errno 111] Connection refused
```

## Phân biệt nhanh: cấu hình hay code?
| Triệu chứng | Nguyên nhân |
|---|---|
| `agent_errors` kèm `Connection refused` / timeout | **Cấu hình** — sai `LLM_BASE_URL` hoặc server LLM chưa chạy |
| HTTP 500 + `traceback` | **Lỗi code** |

## Mẹo
- Loại trừ LLM khi debug: gửi `run_vlm=false` (hoặc tắt *"Chạy VLM"* trên web) → chạy thuần
  rule, không gọi llama.cpp.
- **Production**: đặt `DEBUG_ERRORS=0` để response không lộ traceback (console vẫn log đầy đủ).
