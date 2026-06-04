# Rule Engine — Tổng quan

> ℹ️ **Thuật ngữ:** "VLM xác nhận" trong các file rule dưới đây nay = **tầng agent reasoning
> (Codex CLI text-only)** xác nhận/bác bỏ candidate. Cơ chế đổi (xem [`../F1.1`](../F1.1-codex-cli-architecture.md)),
> nhưng vai trò "rule sinh candidate → agent xác nhận" giữ nguyên.

> **Mục đích:** chạy kiểm tra **tất định từ code** trên output của analyzers →
> sinh `candidate_issues[]` trước khi agent xác nhận/bác bỏ.
>
> Nguyên tắc cốt lõi (từ CLAUDE.md §3): cái gì TÍNH ĐƯỢC bằng code từ bbox + pixel
> → rule engine làm. LLM **không được** làm số học toạ độ.

## Input đầu vào cho Rule Engine

```
CanonicalDoc {
  screen:   viewport, safe_area, platform, theme, dpr, locale, font_scale
  image:    full (path), w, h
  elements[]: bbox, bbox_norm, role, parent, children, z, text, style.*, interactive,
              touch_target, visible, clipped, offscreen, confidence, source
  relations[]: a, rel, b, gap, iou   ← đã tiền tính bởi A0
  candidate_issues[]: (từ analyzers A4/A8/A9/A10 — không xoá, chỉ bổ sung)
}
```

## Output

Thêm vào `candidate_issues[]`. Không sửa/xoá issue cũ từ analyzers.
Mỗi issue: `{ rule, element?, severity, severity_range, confidence, detail, evidence }`.

## Nguyên tắc chạy

1. Rule Engine chạy **sau** tất cả analyzers, **trước** VLM agents.
2. Mỗi rule function: **pure** — nhận doc/elements, trả list `CandidateIssue`.
3. **Confidence rule** = confidence của element nguồn × hệ số rule.
   Rule chạy trên element có `confidence < 0.4` → bỏ qua hoặc ghi `confidence` thấp.
4. **Không fire rule** trên element `visible=false`.
5. **Không duplicate**: nếu A4 đã tạo issue `STY-01_contrast` cho element, R2 không tạo thêm
   (dedup theo rule+element_id).

## Danh sách rule files

| File | Nhóm | Tiêu chí phục vụ |
|---|---|---|
| [`R1-geometry.md`](R1-geometry.md) | Hình học không gian | LAY-01/02/03/04/05/06/07/08/12/14, CMP-01/16, ENV-01/02/03 |
| [`R2-color.md`](R2-color.md) | Màu sắc + contrast | STY-01/02/03/04/05/13 |
| [`R3-image.md`](R3-image.md) | Ảnh + icon | IMG-02/03/07/08/12 |
| [`R4-text.md`](R4-text.md) | Text + placeholder | CNT-01/02/04/05/06/07/08, TYP-03/05 |
| [`R5-severity.md`](R5-severity.md) | Severity + modifier | Áp cho mọi rule |

## Phân chia trách nhiệm (tránh nhầm lẫn với analyzer)

| Kiểm tra | Rule Engine | Analyzer / VLM |
|---|---|---|
| Overlap 2 element có IoU > 0.05 | R1 (tính IoU từ bbox) | A0 đã tiền tính relations |
| Touch target nhỏ | R1 (bbox vs threshold) | — |
| Contrast text/bg | R2 (lấy từ A4.contrast_ratio_px) | A4 tính pixel; VLM xác nhận |
| Text = "undefined" | R4 (regex) | — |
| Ảnh méo | R3 (intrinsic vs displayed ratio) | A7 đo pixel |
| Ảnh vỡ / broken | A9 detect; R3 emit issue | VLM xác nhận |
| Placeholder icon | A6 cờ; R3 emit | VLM xác nhận |
| Tofu/glyph | A8 detect; glyph_issues_to_candidates | VLM xác nhận |
| Nội dung sai | — | VLM (cần ngữ cảnh) |
| Lỗi chính tả | — | VLM |

---

## Quyết định đang chờ

- [ ] **Có dedup rule vs analyzer issue không?** Đề xuất: dedup bằng `(rule_prefix, element_id)` — nếu A4 đã có `STY-01_contrast` thì R2 không thêm nữa.
- [ ] **Ngưỡng confidence tối thiểu để fire rule?** Đề xuất: `element.confidence >= 0.35`.
- [ ] **Grid unit detection:** 8pt chuẩn; nhưng nếu dự án dùng 10px hay 4px thì sao? Đề xuất: **auto-detect** từ distribution của gaps trong màn → tune bằng standard set.
