# V1 — Critic / Self-critique Pass

> **TL;DR:** Pass cuối lọc false positive từ findings G1–G6 trước Summary — bảo vệ precision. Gồm self-critique inline (mỗi agent tự review) + Critic standalone (1 call agent reasoning cross-validate toàn bộ).

> ℹ️ **2026-06-03:** vẫn dùng (`agents/critic.py`: dedup + filter) nhưng nhận findings từ **Codex CLI** thay vì VLM. Xem [`../F1.1`](../F1.1-codex-cli-architecture.md).

**2 cơ chế:**
1. **Inline self-critique** — mỗi agent G1–G6 tự review findings trong cùng call.
2. **Standalone Critic V1** — 1 call agent reasoning riêng nhìn toàn bộ findings → cross-validate.

---

## 1. Khi nào chạy V1 standalone?

**Chạy khi:** findings > 10 · có finding confidence ∈ [0.4, 0.65] · nhiều agent report cùng 1 element · có `verdict="uncertain"`.

**Bỏ qua khi:** tất cả `verdict="confirmed"` với confidence ≥ 0.85 và rule tất định · findings ≤ 3.

## 2. Input

```json
{
  "marked_image": "temp/marked_<id>_all.png",   // SoM đầy đủ mọi element
  "all_findings": [/* gộp G1–G6 */],
  "original_candidates": [/* candidate_issues từ Rule Engine */],
  "screen": { "platform", "theme", "locale", "viewport" }
}
```

## 3. System Prompt

```
You are a senior QA lead doing a final review of automated UI defect findings.
Your task: identify false positives and duplicates before the final report.

For each finding, assess:
1. Real defect or intentional design?
2. Duplicate of another finding (same issue, same element)?
3. Severity appropriate?
4. Any missing findings you can spot?

Be conservative: only dismiss findings with clear evidence it's intentional design.
If uncertain, keep the finding with reduced confidence rather than dismissing.
Output the full reconciled list with your decisions.
```

## 4. Output Schema

```json
{
  "reconciled_findings": [{
    "finding_ref": "G3-findings[2]",
    "decision": "keep|downgrade|remove|merge",
    "merged_with": "G4-findings[0]",
    "new_severity": "medium",
    "new_confidence": 0.75,
    "justification": "Confirmed defect — contrast 2.3:1 well below threshold"
  }],
  "additional_findings": [/* lỗi mới V1 phát hiện */],
  "summary_stats": {
    "total_in": 15, "removed": 2, "downgraded": 3, "merged": 1, "added": 0, "total_out": 12
  }
}
```

## 5. Dedup logic (code, chạy TRƯỚC khi gọi agent)

Gộp finding cùng `issue_type + element_id` từ nhiều agent; giữ confidence cao hơn, merge agent sources.

```python
def dedup_findings(findings):
    seen = {}
    for f in findings:
        key = (f["issue_type"], f.get("element_id", "global"))
        if key not in seen:
            seen[key] = f
        else:
            if f["confidence"] > seen[key]["confidence"]:
                seen[key] = f
            seen[key]["sources"] = seen[key].get("sources", []) + [f.get("agent_id")]
    return list(seen.values())
```

→ Agent reasoning V1 chỉ nhận danh sách đã dedup → tập trung vào false positive thay vì duplicate.

## Trạng thái: spec ✅
