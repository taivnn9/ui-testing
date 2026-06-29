# S1 — Summary Agent

> ℹ️ **Cập nhật 2026-06-03:** vẫn dùng (`agents/summary.py`), nhưng nhận findings từ **Codex CLI**
> thay vì VLM. Xem [`../F1.1`](../F1.1-codex-cli-architecture.md).

> **Mục đích:** tổng hợp findings sau V1 → output cuối API:
> dedupe, chốt severity, sắp xếp ưu tiên, format response.
>
> **Đây là bước CUỐI** trước khi trả về API consumer (tester).

---

## 1. Input

```json
{
  "reconciled_findings": [/* output V1 — đã dedup và lọc */],
  "candidate_issues": [/* Rule Engine candidates gốc — để cross-ref */],
  "screen": { ... }
}
```

---

## 2. Thuật toán Summary (code, không cần VLM)

### 2.1 Final severity selection

Mỗi finding sau V1 có `severity_range {min, max}` từ Rule Engine + `severity` từ VLM agent.
S1 chốt `final_severity`:

```python
def finalize_severity(
    rule_severity: str,         # từ R5 baseline
    rule_range: SeverityRange,  # từ R5 range
    agent_severity: str,        # VLM agent đề xuất
    v1_decision: str,           # "keep"|"downgrade"
    v1_new_severity: str | None,
) -> str:
    ORDER = ["trivial", "low", "medium", "high", "critical"]
    
    # V1 đã downgrade → dùng V1
    if v1_decision == "downgrade" and v1_new_severity:
        return v1_new_severity
    
    # Clamp agent severity vào rule range
    agent_idx = ORDER.index(agent_severity)
    min_idx = ORDER.index(rule_range.min)
    max_idx = ORDER.index(rule_range.max)
    clamped = ORDER[max(min_idx, min(max_idx, agent_idx))]
    return clamped
```

### 2.2 Sort priority

Sắp xếp issues trong output:

```
Priority = severity_weight × confidence × fold_weight

severity_weight: critical=5, high=4, medium=3, low=2, trivial=1
fold_weight: top-fold (y < viewport.h×0.4) = 1.5, else = 1.0
confidence: 0.0–1.0

→ Sort descending by priority
→ Tie-break: alphabetical issue_type
```

### 2.3 Final dedup (rule-based)

```python
def final_dedup(findings: list) -> list:
    """
    Remove absolute duplicates sau V1.
    Giữ lại issue có confidence cao nhất khi:
      - Cùng issue_type + element_id
      - Hoặc cùng evidence (same bbox, khác agent)
    """
```

---

## 3. Output format (API response)

```json
{
  "screen_id": "scr_abc123",
  "analyzed_at": "2026-05-29T10:30:00Z",
  "summary": {
    "total_issues": 7,
    "by_severity": { "critical":0, "high":3, "medium":2, "low":2, "trivial":0 },
    "top_categories": ["STY", "LAY", "CMP"],
    "confidence_avg": 0.82
  },
  "issues": [
    {
      "id": "iss_001",
      "issue_type": "STY-01",
      "title": "Contrast chữ/nền dưới WCAG AA",
      "severity": "high",
      "confidence": 0.92,
      "element_id": "e3",
      "evidence": {
        "bbox": {"x":50, "y":100, "w":200, "h":30},
        "crop": "crops/e3.png",
        "measured_value": "contrast_ratio=2.8",
        "expected_value": ">= 4.5 (WCAG AA)"
      },
      "description": "Label 'Giỏ hàng' trên navigation bar có contrast 2.8:1 — thấp hơn ngưỡng WCAG AA 4.5:1.",
      "sources": ["R2-STY01", "agent-confirmed"],
      "tags": ["a11y"],
      "temporal": false
    }
  ],
  "pipeline_meta": {
    "analyzers_ran": ["A5", "A3", "A4", "A6", "A8", "A9", "A10", "A13"],
    "rules_ran": ["R1", "R2", "R3", "R4"],
    "agents_ran": ["codex"],
    "total_candidates_pre_filter": 23,
    "removed_by_critic": 5,
    "final_issues": 7
  }
}
```

---

## 4. Issue ID generation

```python
import hashlib

def make_issue_id(issue_type: str, element_id: str, screen_id: str) -> str:
    key = f"{screen_id}:{issue_type}:{element_id or 'global'}"
    return "iss_" + hashlib.md5(key.encode()).hexdigest()[:8]
```

→ Deterministic ID: cùng lỗi trên cùng màn → cùng ID → tracking qua nhiều scan.

---

## 5. Title generation (template-based, không cần VLM)

```python
ISSUE_TITLES = {
    "STY-01": "Contrast chữ/nền dưới WCAG AA",
    "STY-02": "Chữ tàng hình — màu giống nền",
    "LAY-01": "Va chạm phần tử — overlap",
    "LAY-02": "Nội dung bị cắt khỏi viewport",
    "CMP-01": "Vùng tap nhỏ hơn tiêu chuẩn",
    "CNT-01": "Biến/placeholder chưa render",
    "TYP-01": "Glyph thiếu / tofu box",
    "IMG-01": "Ảnh vỡ / không load được",
    "STATE-01": "Skeleton loader visible",
    # ... 121 entries
}
def get_title(issue_type: str) -> str:
    return ISSUE_TITLES.get(issue_type, issue_type)
```

## Trạng thái: spec ✅
