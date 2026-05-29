"""V1 — Critic: dedup findings, filter low-confidence, reconcile."""
from __future__ import annotations

from .runner import AgentFinding


def dedup_findings(findings: list[AgentFinding]) -> list[AgentFinding]:
    """
    Gộp findings có cùng (issue_type, element_id) từ nhiều agent.
    Giữ cái confidence cao nhất.
    """
    seen: dict[tuple[str, str | None], AgentFinding] = {}
    for f in findings:
        key = (f.issue_type, f.element_id)
        if key not in seen or f.confidence > seen[key].confidence:
            seen[key] = f
    return list(seen.values())


def filter_low_confidence(
    findings: list[AgentFinding],
    min_confidence: float = 0.35,
) -> list[AgentFinding]:
    return [f for f in findings if f.confidence >= min_confidence]


def run_critic(
    all_results,
    min_confidence: float = 0.35,
) -> list[AgentFinding]:
    """
    V1 code-only critic: dedup + filter.
    VLM cross-validate gọi thêm nếu cần (optional, Phase 2).
    """
    all_findings: list[AgentFinding] = []
    for result in all_results:
        all_findings.extend(result.findings)
    deduped = dedup_findings(all_findings)
    return filter_low_confidence(deduped, min_confidence)
