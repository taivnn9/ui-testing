# V1 — Critic / Self-critique Pass

> **Mục đích:** lọc false positive từ tất cả findings của G1–G6 trước khi Summary.
> Đây là **pass cuối để bảo vệ precision** — hệ thống này sống chết ở false positive thấp.
>
> Có 2 cơ chế:
> 1. **Inline self-critique**: mỗi agent G1–G6 đã tự review findings trong cùng call.
> 2. **Standalone Critic V1**: 1 call VLM riêng nhìn toàn bộ findings → cross-validate.

---

## 1. Khi nào chạy V1 standalone?

Chạy V1 khi:
- Tổng số findings > 10 (nhiều → cần cross-check)
- Có findings `confidence` trong [0.4, 0.65] (vùng uncertain)
- Có issues từ nhiều agent report cùng 1 element (cần reconcile)
- Có findings `verdict="uncertain"` (G1–G6 chưa quyết)

Bỏ qua V1 khi:
- Tất cả findings `verdict="confirmed"` với `confidence >= 0.85` và rule tất định
- Tổng findings ≤ 3

---

## 2. Input V1

```json
{
  "marked_image": "temp/marked_<id>_all.png",  // SoM đầy đủ mọi element
  "all_findings": [/* gộp findings từ G1–G6 */],
  "original_candidates": [/* candidate_issues từ Rule Engine */],
  "screen": { "platform", "theme", "locale", "viewport" }
}
```

---

## 3. System Prompt V1

```
You are a senior QA lead doing a final review of automated UI defect findings.
Your task: identify false positives and duplicates before the final report.

You will see a list of findings from multiple specialized agents.
For each finding, assess:
1. Is this a real defect or intentional design?
2. Is this a duplicate of another finding (same issue, same element)?
3. Is the severity appropriate?
4. Are there missing findings you can spot?

Be conservative: only dismiss findings when you have clear evidence it's intentional design.
If uncertain, keep the finding with reduced confidence rather than dismissing.

Output the full reconciled list with your decisions.
```

---

## 4. V1 Output Schema

```json
{
  "reconciled_findings": [
    {
      "finding_ref": "G3-findings[2]",
      "decision": "keep|downgrade|remove|merge",
      "merged_with": "G4-findings[0]",  // nếu merge
      "new_severity": "medium",          // nếu downgrade
      "new_confidence": 0.75,
      "justification": "Confirmed defect — contrast 2.3:1 well below threshold"
    }
  ],
  "additional_findings": [/* lỗi mới V1 phát hiện */],
  "summary_stats": {
    "total_in": 15,
    "removed": 2,
    "downgraded": 3,
    "merged": 1,
    "added": 0,
    "total_out": 12
  }
}
```

---

## 5. Dedup logic (code, không cần VLM)

Trước khi gọi V1, **code** dedup đơn giản:

```python
def dedup_findings(findings: list[dict]) -> list[dict]:
    """Gộp finding có cùng issue_type + element_id từ nhiều agent."""
    seen: dict[tuple, dict] = {}
    for f in findings:
        key = (f["issue_type"], f.get("element_id", "global"))
        if key not in seen:
            seen[key] = f
        else:
            # Giữ cái confidence cao hơn; merge evidence
            existing = seen[key]
            if f["confidence"] > existing["confidence"]:
                seen[key] = f
            # Merge agent sources
            seen[key]["sources"] = seen[key].get("sources", []) + [f.get("agent_id")]
    return list(seen.values())
```

→ VLM V1 chỉ nhận danh sách đã dedup → tập trung vào false positive thay vì duplicate.

## Trạng thái: spec ✅
