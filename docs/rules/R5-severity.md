# R5 — Severity Baseline + Modifier System

> **Mục đích:** chuẩn hoá cách gán `severity` + `severity_range` cho mọi rule,
> bao gồm **modifier ngữ cảnh** để chốt mức cuối trong range trước khi VLM xem xét.
>
> **Nguyên tắc:** Rule Engine ghi `severity_range {min, max}` + `severity` (mức nền).
> VLM agent nhìn range + context → chốt mức cuối trong range (không vượt ngoài).

---

## 1. Bảng severity nền + range theo rule

| Rule ID | Tiêu chí | Severity nền | Range | VLM có chốt không? |
|---|---|---|---|---|
| R1-LAY01 | Overlap sibling | high | medium→critical | ✅ (xác nhận chủ ý/lỗi) |
| R1-LAY02 | Off-screen | high | medium→critical | ✅ |
| R1-LAY03 | Overflow container | medium | low→high | ✅ |
| R1-LAY04 | Lệch grid | low | trivial→medium | ⚠ (confidence thấp) |
| R1-LAY05 | Optical misalign | low | trivial→medium | ✅ (VLM confirm) |
| R1-LAY06 | Z-order occlusion | high | medium→critical | ✅ |
| R1-LAY07 | Gap bất thường | low | trivial→medium | ✅ |
| R1-LAY08 | Lệch tâm | low | trivial→low | ✅ |
| R1-LAY12 | Container ratio | low | trivial→medium | ✅ |
| R1-LAY14 | Near-dup pos | medium | low→high | ✅ |
| R1-CMP01 | Touch target nhỏ | high | medium→high | — (tất định) |
| R1-CMP16 | Tap gap chồng | medium | low→high | ✅ |
| R1-ENV01 | Safe-area violation | high | medium→critical | ✅ |
| R1-ENV02 | Status bar overlap | medium | low→high | ✅ |
| R1-ENV03 | Home indicator | medium | low→high | ✅ |
| R2-STY01 | Contrast thấp | high | medium→high | ✅ |
| R2-STY02 | Invisible text | critical | high→critical | — (tất định) |
| R2-STY03 | Dark-mode hardcode | high | medium→critical | ✅ |
| R2-STY04 | Icon tàng hình dark | high | medium→critical | ✅ |
| R2-STY05 | Opacity sai | medium | low→high | ✅ |
| R2-STY13 | Icon contrast < 3:1 | medium | low→high | ✅ |
| R3-IMG02 | Méo ảnh | medium | low→high | ✅ |
| R3-IMG03 | Mờ/pixel | medium | low→medium | ✅ |
| R3-IMG03u | Upscale | low | trivial→medium | ✅ |
| R3-IMG07 | Icon lệch tâm | low | trivial→medium | ✅ |
| R3-IMG08 | Icon placeholder | medium | low→high | ✅ |
| R3-IMG12 | Ảnh trùng | low | trivial→medium | ✅ |
| R4-CNT01 | Placeholder biến | high | medium→critical | ✅ |
| R4-CNT02 | i18n key lòi | high | medium→critical | ✅ |
| R4-CNT04 | Lorem ipsum | high | medium→high | — |
| R4-CNT05 | Debug text | high | medium→critical | ✅ |
| R4-CNT06 | Mojibake/entity | medium | low→high | ✅ |
| R4-CNT07 | Escape literal | medium | low→high | — |
| R4-CNT08 | Epoch/format | medium | low→high | ✅ |
| R4-STATE03 | Stack trace | high | medium→critical | ✅ |
| R4-TYP03 | Text cắt cụt | medium | trivial→critical | ✅ |
| R4-TYP05 | Cỡ chữ nhỏ | medium | low→high | ✅ |

---

## 2. Modifier ngữ cảnh

Modifier là **luật đẩy severity lên ↑ hoặc xuống ↓** dựa vào context của element bị dính.
Rule Engine tính modifier → điều chỉnh severity trong range → ghi vào `candidate_issues`.

### 2.1 Modifier theo `role` element

| Role | Modifier |
|---|---|
| `button` (role=button, interactive=true) | ↑ +1 mức (vd medium → high) |
| Nút CTA chính (được VLM đánh dấu) | ↑ +2 mức (vd medium → critical) |
| `input` | ↑ +1 |
| `nav` (navigation chính) | ↑ +1 |
| `text` (body text) | = baseline |
| `text` (label phụ/caption) | ↓ -1 |
| `icon` (interactive) | = baseline |
| `icon` (decorative, interactive=false) | ↓ -2 |
| `image` (hero/product) | ↑ +1 |
| `image` (background/decorative) | ↓ -2 |
| `container` | ↓ -1 (lỗi của container thường ít nghiêm trọng hơn content) |
| `skeleton`, `spinner` | ↓ -2 (trạng thái loading, lỗi là expected) |

### 2.2 Modifier theo vị trí màn

| Vị trí | Modifier |
|---|---|
| Top-fold (y < viewport.h × 0.4) | ↑ +1 (người dùng thấy ngay) |
| Above-the-fold visible | = baseline |
| Below-fold (cần scroll) | ↓ -1 |
| Hidden / offscreen | ↓ -2 (không thấy ngay) |
| Safe-area zone | ↑ +1 (dễ bị cắt/che) |

### 2.3 Modifier theo content

| Content hint | Modifier |
|---|---|
| Text chứa số tiền / giá | ↑ +1 |
| Text chứa phủ định ("không", "cancel") bị cắt | ↑ +2 |
| Text là headline/title chính | ↑ +1 |
| Text là legal/disclaimer | ↑ +1 |
| Text là copyright/footnote | ↓ -1 |
| Text là placeholder/hint (hợp lệ) | ↓ -1 |

### 2.4 Modifier theo platform

| Điều kiện | Modifier |
|---|---|
| platform=ios + rule CMP-01 (44pt) | ↑ (touch target bắt buộc trên iOS HIG) |
| platform=android + rule CMP-01 (48dp) | ↑ |
| platform=web + rule LAY-02 (off-screen) | ↓ -1 (web thường scroll) |
| screen.font_scale > 1.3 (trợ năng) | ↑ +1 cho mọi TYP rule |

### 2.5 Cách áp modifier (code logic)

```python
def apply_modifiers(severity: str, modifiers: list[int], severity_range: SeverityRange) -> str:
    """
    severity: baseline ("critical"|"high"|"medium"|"low"|"trivial")
    modifiers: list of int (+1 = lên 1 mức, -1 = xuống 1 mức)
    severity_range: clamp output vào [min, max]
    """
    ORDER = ["trivial", "low", "medium", "high", "critical"]
    idx = ORDER.index(severity)
    delta = sum(modifiers)
    new_idx = max(0, min(len(ORDER)-1, idx + delta))
    result = ORDER[new_idx]
    # Clamp vào range
    min_idx = ORDER.index(severity_range.min)
    max_idx = ORDER.index(severity_range.max)
    result_idx = max(min_idx, min(max_idx, new_idx))
    return ORDER[result_idx]
```

---

## 3. Confidence tổng hợp

```
Confidence của mỗi issue = f(element.confidence, rule.confidence_factor, modifier)

rule_confidence_factors:
  Tất định hoàn toàn (LAY-02, CMP-01, STY-02): 0.95
  Tính từ pixel nhưng có sai số (STY-01, IMG-02): 0.85
  Heuristic có false positive (LAY-04, LAY-05): 0.55
  Regex có false positive (R4-CNT02): 0.75
  Phụ thuộc A13 metadata (ENV-01/02/03): × meta_confidence
  
final_confidence = clamp(elem.confidence × rule_factor × meta_factor, 0.1, 0.99)
```

---

## 4. Phân loại issue để VLM xử lý

Sau khi Rule Engine chạy, mỗi `CandidateIssue` được phân loại:

| Loại | Điều kiện | Hành động |
|---|---|---|
| **Auto-confirm** | confidence >= 0.9 VÀ rule hoàn toàn tất định | Không cần VLM; ghi thẳng vào output |
| **VLM-confirm** | 0.5 <= confidence < 0.9 | Gửi cho VLM agent nhóm phù hợp để xác nhận |
| **Low-confidence** | confidence < 0.5 | VLM xem xét nhưng có thể bỏ qua; cần context |
| **ctx-dependent** | Rule có tag `ctx` | **Luôn** gửi VLM dù confidence cao |

Auto-confirm (không cần VLM):
- R4-CNT04 (lorem ipsum) + confidence ≥ 0.9
- R2-STY02 (invisible text) + confidence ≥ 0.9
- R4-CNT07 (escape literal rõ ràng) + confidence ≥ 0.9
- R1-CMP01 (touch target tính px chính xác) + confidence ≥ 0.85

---

## 5. Ví dụ end-to-end

```
Element: e7 (role=button, interactive=true, text="Thanh toán", visible=true)
  bbox: {x:50, y:820, w:280, h:30}   ← h=30px < 44pt×3dpr=132px (WAI tính: 44pt×2dpr=88px)
  touch_target: {w:280, h:30}
  confidence: 0.85
  screen.platform: ios, dpr: 2.0

→ R1-CMP01 fires:
  touch_target.h = 30 < touch_min_px(2.0, "ios") = 88
  severity_baseline = high
  modifiers: role=button(+1) → high+1 = critical; clamp tới max=high → high
  confidence = 0.85 × 0.9 = 0.77
  
CandidateIssue:
  rule: "R1-CMP01"
  element: "e7"
  severity: "high"
  severity_range: {min:"medium", max:"high"}
  confidence: 0.77
  detail: "touch_target.h=30px < 88px (44pt×dpr=2); nút CTA chính"
  evidence: {bbox: {x:50,y:820,w:280,h:30}}
```

---

## 6. Open decisions

- [ ] **Ngưỡng auto-confirm confidence?** Đề xuất: ≥ 0.9 cho rule tất định; ≥ 0.85 cho regex rõ. Tune sau khi có standard set.
- [ ] **Số lượng modifier tối đa?** Nếu quá nhiều modifier cùng hướng có thể overcorrect → clamp theo range là đủ.
- [ ] **Bảng CTA detection:** làm sao biết button là CTA chính? Đề xuất: VLM agent G6 (Component) đánh dấu `is_primary=true` trong pass đầu → R5 modifier dùng flag này.

## Trạng thái: spec ✅ — cần implement sau R1–R4.
