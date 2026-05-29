"""
Agent runner: gọi G1–G6 (sequential hoặc async), tổng hợp findings.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from ..schema.models import CanonicalDoc
from .g0_framework import (
    call_agent,
    filter_elements,
    filter_issues,
    render_som,
)
from .prompts import (
    SYSTEM_G1, SYSTEM_G2, SYSTEM_G3, SYSTEM_G4, SYSTEM_G5, SYSTEM_G6,
    make_user_prompt,
)


@dataclass
class AgentFinding:
    agent_id: str
    issue_type: str
    element_id: str | None
    severity: str
    confidence: float
    verdict: str
    original_candidate_rule: str | None
    evidence: dict
    reasoning: str
    severity_justification: str | None = None
    temporal: bool = False


@dataclass
class AgentRunResult:
    agent_id: str
    findings: list[AgentFinding] = field(default_factory=list)
    summary: str = ""
    error: str | None = None


def _elements_to_json(elements, max_items: int = 60) -> str:
    items = []
    for e in elements[:max_items]:
        item: dict[str, Any] = {
            "id": e.id, "role": e.role,
            "bbox": {"x": round(e.bbox.x), "y": round(e.bbox.y),
                     "w": round(e.bbox.w), "h": round(e.bbox.h)},
            "confidence": round(e.confidence, 2),
        }
        if e.text:
            item["text"] = e.text[:120]
        if e.interactive:
            item["interactive"] = True
        if e.style and e.style.contrast_ratio is not None:
            item["contrast_ratio"] = e.style.contrast_ratio
        items.append(item)
    return json.dumps(items, ensure_ascii=False, indent=None)


def _issues_to_json(issues, max_items: int = 30) -> str:
    items = [
        {"rule": i.rule, "element": i.element,
         "severity": i.severity, "confidence": round(i.confidence, 2),
         "detail": i.detail[:200] if i.detail else ""}
        for i in issues[:max_items]
    ]
    return json.dumps(items, ensure_ascii=False)


def _parse_findings(raw: dict, agent_id: str) -> list[AgentFinding]:
    findings = []
    raw_findings = raw.get("findings", [])
    critique_map: dict[int, dict] = {
        c.get("issue_index", -1): c
        for c in raw.get("self_critique", [])
    }
    for idx, f in enumerate(raw_findings):
        verdict = f.get("verdict", "uncertain")
        if verdict == "rejected":
            continue
        critique = critique_map.get(idx)
        if critique and critique.get("decision") == "remove":
            continue
        confidence = f.get("confidence", 0.5)
        if critique and critique.get("new_confidence") is not None:
            confidence = critique["new_confidence"]

        findings.append(AgentFinding(
            agent_id=agent_id,
            issue_type=f.get("issue_type", "UNKNOWN"),
            element_id=f.get("element_id"),
            severity=f.get("severity", "medium"),
            confidence=float(confidence),
            verdict=verdict,
            original_candidate_rule=f.get("original_candidate_rule"),
            evidence=f.get("evidence", {}),
            reasoning=f.get("reasoning", ""),
            severity_justification=f.get("severity_justification"),
        ))
    return findings


def run_agent(
    agent_id: str,
    doc: CanonicalDoc,
    marked_image: Image.Image,
    model: str | None = None,
) -> AgentRunResult:
    """Gọi 1 agent. Trả AgentRunResult."""
    screen = doc.screen

    # Context trimming
    elements = filter_elements(doc.elements, agent_id)
    raw_issues = [
        {"rule": i.rule, "element": i.element, "severity": i.severity,
         "confidence": i.confidence, "detail": i.detail}
        for i in doc.candidate_issues
    ]
    issues = filter_issues(raw_issues, agent_id)

    elements_json = _elements_to_json(elements)
    issues_json = _issues_to_json(issues)

    # System prompt
    safe_area = screen.safe_area
    system_map = {
        "G1": SYSTEM_G1.format(locale=screen.locale, platform=screen.platform),
        "G2": SYSTEM_G2,
        "G3": SYSTEM_G3.format(theme=screen.theme, platform=screen.platform),
        "G4": SYSTEM_G4.format(
            platform=screen.platform,
            vp_w=screen.viewport.w, vp_h=screen.viewport.h,
            safe_top=safe_area.top, safe_bottom=safe_area.bottom,
        ),
        "G5": SYSTEM_G5,
        "G6": SYSTEM_G6.format(
            platform=screen.platform,
            notch_type=getattr(screen, "notch_type", "unknown"),
        ),
    }
    system_prompt = system_map.get(agent_id, "You are a UI QA engineer.")

    extra_map = {
        "G1": f"Screen locale: {screen.locale}. Flag any text that appears to be in a different language.",
        "G6": "For skeleton/spinner: confirm presence but mark temporal=true — cannot confirm 'stuck' from 1 frame.",
    }
    user_prompt = make_user_prompt(
        elements_json, issues_json,
        extra=extra_map.get(agent_id, ""),
    )

    try:
        raw = call_agent(marked_image, system_prompt, user_prompt, model=model)
        findings = _parse_findings(raw, agent_id)
        return AgentRunResult(
            agent_id=agent_id,
            findings=findings,
            summary=raw.get("summary", ""),
        )
    except Exception as exc:
        return AgentRunResult(agent_id=agent_id, error=str(exc))


def run_all_agents(
    doc: CanonicalDoc,
    img: Image.Image,
    agent_ids: list[str] | None = None,
    model: str | None = None,
) -> list[AgentRunResult]:
    """
    Chạy tất cả agent G1–G6 tuần tự.
    (Parallel với asyncio/ThreadPoolExecutor — để caller tự quyết nếu muốn nhanh hơn.)
    """
    _ids = agent_ids or ["G1", "G2", "G3", "G4", "G5", "G6"]
    marked = render_som(img, doc.elements)
    results = []
    for aid in _ids:
        agent_elements = filter_elements(doc.elements, aid)
        marked_for_agent = render_som(img, agent_elements)
        results.append(run_agent(aid, doc, marked_for_agent, model=model))
    return results
