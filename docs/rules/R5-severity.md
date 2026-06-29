# R5 — Severity Baseline + Modifier System

> **TL;DR:** Chuẩn hoá gán `severity` + `severity_range` cho mọi rule, kèm modifier ngữ cảnh (role/vị trí/content/platform) để chốt mức trong range. Rule Engine ghi range + mức nền; agent reasoning (Codex/Cline) chốt mức cuối trong range.

---

## 1. Bảng severity nền + range theo rule

| Rule ID | Severity nền | Range | Agent chốt? |
|---|---|---|---|
| R1-LAY01 Overlap | high | medium→critical | ✅ |
| R1-LAY02 Off-screen | high | medium→critical | ✅ |
| R1-LAY03 Overflow | medium | low→high | ✅ |
| R1-LAY04 Lệch grid | low | trivial→medium | ⚠ conf thấp |
| R1-LAY05 Optical misalign | low | trivial→medium | ✅ |
| R1-LAY06 Z-order occlusion | high | medium→critical | ✅ |
| R1-LAY07 Gap bất thường | low | trivial→medium | ✅ |
| R1-LAY08 Lệch tâm | low | trivial→low | ✅ |
| R1-LAY12 Container ratio | low | trivial→medium | ✅ |
| R1-LAY14 Near-dup pos | medium | low→high | ✅ |
| R1-CMP01 Touch target | high | medium→high | — tất định |
| R1-CMP16 Tap gap | medium | low→high | ✅ |
| R1-ENV01 Safe-area | high | medium→critical | ✅ |
| R1-ENV02 Status bar | medium | low→high | ✅ |
| R1-ENV03 Home indicator | medium | low→high | ✅ |
| R2-STY01 Contrast thấp | high | medium→high | ✅ |
| R2-STY02 Invisible text | critical | high→critical | — tất định |
| R2-STY03 Dark-mode hardcode | high | medium→critical | ✅ |
| R2-STY04 Icon tàng hình dark | high | medium→critical | ✅ |
| R2-STY05 Opacity sai | medium | low→high | ✅ |
| R2-STY13 Icon contrast <3:1 | medium | low→high | ✅ |
| R3-IMG02 Méo ảnh | medium | low→high | ✅ |
| R3-IMG03 Mờ/pixel | medium | low→medium | ✅ |
| R3-IMG03u Upscale | low | trivial→medium | ✅ |
| R3-IMG07 Icon lệch tâm | low | trivial→medium | ✅ |
| R3-IMG08 Icon placeholder | medium | low→high | ✅ |
| R3-IMG12 Ảnh trùng | low | trivial→medium | ✅ |
| R4-CNT01 Placeholder biến | high | medium→critical | ✅ |
| R4-CNT02 i18n key lòi | high | medium→critical | ✅ |
| R4-CNT04 Lorem ipsum | high | medium→high | — |
| R4-CNT05 Debug text | high | medium→critical | ✅ |
| R4-CNT06 Mojibake/entity | medium | low→high | ✅ |
| R4-CNT07 Escape literal | medium | low→high | — |
| R4-CNT08 Epoch/format | medium | low→high | ✅ |
| R4-STATE03 Stack trace | high | medium→critical | ✅ |
| R4-TYP03 Text cắt cụt | medium | trivial→critical | ✅ |
| R4-TYP05 Cỡ chữ nhỏ | medium | low→high | ✅ |

---

## 2. Modifier ngữ cảnh

Modifier = luật đẩy severity ↑/↓ theo context (đơn vị: số mức, vd +1 = lên 1 mức). Rule Engine tính → điều chỉnh trong range → ghi vào `candidate_issues`.

**Theo `role`:** button/interactive ↑+1 · CTA chính ↑+2 · input ↑+1 · nav ↑+1 · body text = baseline · caption ↓-1 · icon interactive = baseline · icon decorative ↓-2 · image hero/product ↑+1 · image background ↓-2 · container ↓-1 · skeleton/spinner ↓-2.

**Theo vị trí:** top-fold (`y < viewport.h×0.4`) ↑+1 · above-fold = baseline · below-fold ↓-1 · hidden/offscreen ↓-2 · safe-area zone ↑+1.

**Theo content:** chứa số tiền/giá ↑+1 · phủ định ("không"/"cancel") bị cắt ↑+2 · headline/title ↑+1 · legal/disclaimer ↑+1 · copyright/footnote ↓-1 · placeholder hint hợp lệ ↓-1.

**Theo platform:** ios + CMP-01 (44pt) ↑ · android + CMP-01 (48dp) ↑ · web + LAY-02 off-screen ↓-1 (web hay scroll) · `font_scale > 1.3` ↑+1 cho mọi TYP rule.

### Code áp modifier

```python
def apply_modifiers(severity: str, modifiers: list[int], severity_range: SeverityRange) -> str:
    ORDER = ["trivial", "low", "medium", "high", "critical"]
    idx = ORDER.index(severity)
    new_idx = max(0, min(len(ORDER)-1, idx + sum(modifiers)))
    # Clamp vào range
    min_idx = ORDER.index(severity_range.min)
    max_idx = ORDER.index(severity_range.max)
    return ORDER[max(min_idx, min(max_idx, new_idx))]
```

---

## 3. Confidence tổng hợp

```
final_confidence = clamp(elem.confidence × rule_factor × meta_factor, 0.1, 0.99)
```
| Loại rule | rule_factor |
|---|---|
| Tất định hoàn toàn (LAY-02, CMP-01, STY-02) | 0.95 |
| Pixel có sai số (STY-01, IMG-02) | 0.85 |
| Heuristic FP cao (LAY-04, LAY-05) | 0.55 |
| Regex có FP (R4-CNT02) | 0.75 |
| Phụ thuộc A13 metadata (ENV-01/02/03) | × meta_confidence |

---

## 4. Phân loại issue để agent reasoning xử lý

| Loại | Điều kiện | Hành động |
|---|---|---|
| **Auto-confirm** | conf ≥ 0.9 VÀ rule tất định | ghi thẳng output, không cần agent |
| **Agent-confirm** | 0.5 ≤ conf < 0.9 | gửi agent reasoning xác nhận |
| **Low-confidence** | conf < 0.5 | agent xem xét, có thể bỏ qua |
| **ctx-dependent** | rule có tag `ctx` | **luôn** gửi agent dù conf cao |

Auto-confirm: R4-CNT04 (conf≥0.9) · R2-STY02 (conf≥0.9) · R4-CNT07 (conf≥0.9) · R1-CMP01 (conf≥0.85).

---

## 5. Ví dụ end-to-end

```
Element e7 (role=button, interactive, text="Thanh toán"); platform=ios, dpr=2.0
  bbox {x:50,y:820,w:280,h:30}; touch_target.h=30; confidence=0.85

→ R1-CMP01 fires: touch_target.h=30 < touch_min_px(2.0,"ios")=88
  baseline=high; modifier role=button(+1)→critical; clamp tới max=high → high
  confidence = 0.85 × 0.9 = 0.77

CandidateIssue:
  rule:"R1-CMP01", element:"e7", severity:"high",
  severity_range:{min:"medium",max:"high"}, confidence:0.77,
  detail:"touch_target.h=30px < 88px (44pt×dpr=2); nút CTA chính",
  evidence:{bbox:{x:50,y:820,w:280,h:30}}
```

---

## 6. Open decisions

- [ ] **Ngưỡng auto-confirm:** đề xuất ≥0.9 (tất định) / ≥0.85 (regex rõ); tune sau standard set.
- [ ] **Số modifier tối đa:** clamp theo range là đủ (tránh overcorrect).
- [ ] **CTA detection:** agent reasoning Component đánh dấu `is_primary=true` pass đầu → R5 modifier dùng flag này.

## Trạng thái: spec ✅ — cần implement sau R1–R4.
