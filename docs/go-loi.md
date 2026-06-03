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

### Lỗi tầng agent (Codex) KHÔNG làm hỏng phân tích
Pipeline degrade graceful → vẫn trả **HTTP 200** (giữ kết quả rule), xem **`pipeline_meta.agent_errors`**.
Web UI hiện **banner vàng**. Lỗi Codex kèm rõ nguyên nhân:
```
RuntimeError: Codex exec exit=1 (sandbox=workspace-write, model=default). stderr: ...
RuntimeError: Không tìm thấy Codex CLI 'codex'. Cài Codex hoặc đặt env CODEX_BIN.
```

## Phân biệt nhanh: cấu hình hay code?
| Triệu chứng | Nguyên nhân |
|---|---|
| `agent_errors`: "Không tìm thấy Codex CLI" | **Cấu hình** — chưa cài Codex / sai `CODEX_BIN` |
| `agent_errors`: Codex exit≠0 / timeout / auth | **Cấu hình** — chưa `codex login`, hết quota, hoặc sandbox |
| HTTP 500 + `traceback` | **Lỗi code** |

## Mẹo
- Loại trừ Codex khi debug: gửi `run_vlm=false` (hoặc tắt *"Chạy agent reasoning"* trên web) →
  chạy thuần rule.
- Kiểm tra Codex độc lập: `echo 'hi' | codex exec --ephemeral -s read-only -` và `codex login status`.
- **Production**: đặt `DEBUG_ERRORS=0` để response không lộ traceback (console vẫn log đầy đủ).
