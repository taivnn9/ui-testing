# Rule Engine — Tổng quan

> **TL;DR:** Rule Engine chạy kiểm tra **tất định từ code** trên output analyzers → sinh `candidate_issues[]`, chạy SAU analyzers và TRƯỚC tầng agent reasoning (Codex/Cline) xác nhận/bác bỏ.

> ℹ️ "VLM xác nhận" trong các file rule = **tầng agent reasoning (Codex CLI, text-only)** confirm/reject candidate. Cơ chế đổi (xem [`../F1.1`](../F1.1-codex-cli-architecture.md)) nhưng vai trò "rule sinh candidate → agent xác nhận" giữ nguyên.
>
> Nguyên tắc cốt lõi (CLAUDE.md §3): cái gì TÍNH ĐƯỢC bằng code từ bbox + pixel → rule engine làm. LLM **không** làm số học toạ độ.

## Input

```
CanonicalDoc {
  screen:   viewport, safe_area, platform, theme, dpr, locale, font_scale
  image:    full (path), w, h
  elements[]: bbox, bbox_norm, role, parent, children, z, text, style.*, interactive,
              touch_target, visible, clipped, offscreen, confidence, source
  relations[]: a, rel, b, gap, iou   ← tiền tính bởi A0
  candidate_issues[]: (từ A4/A8/A9/A10 — không xoá, chỉ bổ sung)
}
```

## Output

Thêm vào `candidate_issues[]` (không sửa/xoá issue cũ từ analyzers). Mỗi issue: `{ rule, element?, severity, severity_range, confidence, detail, evidence }`.

## Nguyên tắc chạy

1. Chạy **sau** tất cả analyzers, **trước** agent reasoning.
2. Mỗi rule function **pure**: nhận doc/elements → trả list `CandidateIssue`.
3. Confidence rule = `elem.confidence × hệ số rule`. Element `confidence < 0.4` → bỏ qua hoặc conf thấp.
4. **Không fire** trên element `visible=false`.
5. **Không duplicate**: A4 đã tạo `STY-01_contrast` → R2 không thêm (dedup theo rule+element_id).

## Danh sách rule files

| File | Nhóm | Tiêu chí |
|---|---|---|
| [`R1-geometry.md`](R1-geometry.md) | Hình học | LAY-01/02/03/04/05/06/07/08/12/14, CMP-01/16, ENV-01/02/03 |
| [`R2-color.md`](R2-color.md) | Màu + contrast | STY-01/02/03/04/05/13 |
| [`R3-image.md`](R3-image.md) | Ảnh + icon | IMG-02/03/07/08/12 |
| [`R4-text.md`](R4-text.md) | Text + placeholder | CNT-01/02/04/05/06/07/08, TYP-03/05 |
| [`R5-severity.md`](R5-severity.md) | Severity + modifier | mọi rule |

## Phân chia trách nhiệm (rule vs analyzer/agent)

| Kiểm tra | Rule Engine | Analyzer / agent reasoning |
|---|---|---|
| Overlap IoU > 0.05 | R1 (tính IoU) | A0 tiền tính relations |
| Touch target nhỏ | R1 (bbox vs threshold) | — |
| Contrast text/bg | R2 (từ A4.contrast_ratio_px) | A4 tính pixel; agent xác nhận |
| Text = "undefined" | R4 (regex) | — |
| Ảnh méo | R3 (intrinsic vs displayed) | A7 đo pixel |
| Ảnh vỡ / broken | A9 detect; R3 emit | agent xác nhận |
| Placeholder icon | A6 cờ; R3 emit | agent xác nhận |
| Tofu/glyph | A8 detect; glyph_issues_to_candidates | agent xác nhận |
| Nội dung sai / lỗi chính tả | — | agent reasoning (cần ngữ cảnh) |

---

## Quyết định đang chờ

- [ ] **Dedup rule vs analyzer issue?** Đề xuất: theo `(rule_prefix, element_id)` — A4 có `STY-01_contrast` thì R2 không thêm.
- [ ] **Ngưỡng confidence tối thiểu để fire?** Đề xuất: `element.confidence >= 0.35`.
- [ ] **Grid unit detection:** 8pt chuẩn; nếu dự án dùng 10px/4px → auto-detect từ distribution gaps, tune bằng standard set.
