"""
Reasoning runner (text-only): build prompt từ schema map + candidate + skill,
gọi coding-agent CLI (Codex/Cline) qua backends → parse findings.

KHÔNG gửi ảnh cho model (xem docs/F1.1). Ảnh chỉ dùng ở tầng CV để trích map.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..schema.models import CanonicalDoc
from .backends import active_backend, run_backend

_SKILLS_DIR = Path(__file__).resolve().parent / "skills"


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


# ── JSON Schema khóa output (truyền cho codex --output-schema) ─────────────────
REASONING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings", "summary"],
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "issue_type", "element_id", "verdict", "severity",
                    "confidence", "reasoning", "original_candidate_rule", "temporal",
                ],
                "properties": {
                    "issue_type": {"type": "string"},
                    "element_id": {"type": ["string", "null"]},
                    "verdict": {
                        "type": "string",
                        "enum": ["confirmed", "rejected", "uncertain", "new_finding"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "trivial"],
                    },
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "original_candidate_rule": {"type": ["string", "null"]},
                    "temporal": {"type": "boolean"},
                },
            },
        },
    },
}


def _fill(template: str, **kwargs: Any) -> str:
    """
    Thay placeholder {name} đã biết trong text — KHÔNG dùng str.format vì text có thể chứa
    dấu ngoặc literal (vd '{{var}}', '${x}') sẽ làm format() ném KeyError. Giữ mọi ngoặc khác.
    """
    out = template
    for key, val in kwargs.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def _elements_to_json(elements, max_items: int = 80) -> str:
    items = []
    for e in elements[:max_items]:
        item: dict[str, Any] = {
            "id": e.id, "role": e.role,
            "bbox": {"x": round(e.bbox.x), "y": round(e.bbox.y),
                     "w": round(e.bbox.w), "h": round(e.bbox.h)},
        }
        if e.text:
            item["text"] = e.text[:120]
        if getattr(e, "text_truncated", False):
            item["text_truncated"] = True
        if getattr(e, "interactive", False):
            item["interactive"] = True
        tt = getattr(e, "touch_target", None)
        if tt is not None:
            item["touch_target"] = {"w": round(tt.w), "h": round(tt.h)}
        style = getattr(e, "style", None)
        if style is not None:
            if style.contrast_ratio is not None:
                item["contrast_ratio"] = round(style.contrast_ratio, 2)
            if getattr(style, "font_family", None):
                item["font_family"] = style.font_family
        im = getattr(e, "image_meta", None)
        if im is not None:
            item["image_meta"] = {
                "intrinsic_w": im.intrinsic_w, "intrinsic_h": im.intrinsic_h,
                "displayed_w": im.displayed_w, "displayed_h": im.displayed_h,
                "scale_mode": im.scale_mode,
            }
        items.append(item)
    return json.dumps(items, ensure_ascii=False)


def _issues_to_json(issues: list[dict], max_items: int = 60) -> str:
    # issues là list[dict] (từ rule engine) — đọc bằng key, KHÔNG phải attribute
    items = [
        {"rule": i.get("rule"), "element": i.get("element"),
         "severity": i.get("severity"), "confidence": round(i.get("confidence", 0.0), 2),
         "detail": (i.get("detail") or "")[:200]}
        for i in issues[:max_items]
    ]
    return json.dumps(items, ensure_ascii=False)


def _relations_to_json(relations, max_items: int = 60) -> str:
    items = [
        {"a": r.a, "rel": r.rel, "b": r.b,
         "gap": round(getattr(r, "gap", 0) or 0), "iou": round(getattr(r, "iou", 0) or 0, 2)}
        for r in (relations or [])[:max_items]
    ]
    return json.dumps(items, ensure_ascii=False)


def load_skills(skip_system: bool = False) -> str:
    """Đọc & nối tất cả file skill (*.md) theo thứ tự tên.

    skip_system=True: bỏ qua 00-system.md (đã có trong .clinerules/ với backend Cline).
    """
    if not _SKILLS_DIR.is_dir():
        return ""
    parts = []
    for f in sorted(_SKILLS_DIR.glob("*.md")):
        if skip_system and f.name == "00-system.md":
            continue
        parts.append(f.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(parts)


def build_review_prompt(doc: CanonicalDoc, *, backend: str | None = None) -> str:
    """Build prompt text-only: skill (tiêu chí) + map (elements/relations) + candidate issues.

    Khi backend=cline, bỏ 00-system.md (đã tự load từ .clinerules/).
    """
    _backend = (backend or active_backend()).strip().lower()
    skip_system = _backend == "cline"
    s = doc.screen
    raw_issues = [
        {"rule": i.rule, "element": i.element, "severity": i.severity,
         "confidence": i.confidence, "detail": i.detail}
        for i in doc.candidate_issues
    ]
    context = {
        "platform": s.platform, "locale": s.locale, "theme": s.theme,
        "viewport": {"w": s.viewport.w, "h": s.viewport.h, "dpr": s.viewport.dpr},
        "safe_area": {"top": s.safe_area.top, "bottom": s.safe_area.bottom},
        "font_scale": s.font_scale,
    }
    return (
        f"{load_skills(skip_system=skip_system)}\n\n"
        "===== DỮ LIỆU MÀN HÌNH (text-only, trích từ ảnh bằng CV/OCR) =====\n\n"
        f"screen = {json.dumps(context, ensure_ascii=False)}\n\n"
        f"elements = {_elements_to_json(doc.elements)}\n\n"
        f"relations = {_relations_to_json(doc.relations)}\n\n"
        f"candidate_issues = {_issues_to_json(raw_issues)}\n\n"
        "===== YÊU CẦU =====\n"
        "1. Xét từng candidate_issue: confirmed | rejected | uncertain.\n"
        "2. Phát hiện thêm lỗi text/ngữ nghĩa rule bỏ sót: verdict=\"new_finding\".\n"
        "3. Gán severity cuối + reasoning ngắn, trỏ theo element_id (null nếu toàn màn hình).\n"
        "4. Trạng thái loading/skeleton/spinner: temporal=true.\n"
        "5. Trả về DUY NHẤT JSON đúng schema (findings + summary). Không bịa toạ độ/số liệu.\n"
    )


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
            temporal=bool(f.get("temporal", False)),
        ))
    return findings


def run_review(
    doc: CanonicalDoc,
    *,
    model: str | None = None,
    backend: str | None = None,
    log_callback=None,
) -> list[AgentRunResult]:
    """
    Chạy 1 lượt reasoning qua coding-agent CLI (backend). Trả list[AgentRunResult] (1 phần tử)
    để tương thích critic/summary. Lỗi backend → result.error (degrade graceful, không raise).

    Tham số `backend` ghi đè env AGENT_BACKEND (codex | cline | none).
    """
    _backend = (backend or active_backend()).strip().lower()
    prompt = build_review_prompt(doc, backend=_backend)
    try:
        raw = run_backend(prompt, REASONING_SCHEMA, backend=_backend, log_callback=log_callback)
    except Exception as exc:
        return [AgentRunResult(agent_id=_backend, error=f"{type(exc).__name__}: {exc}")]
    findings = _parse_findings(raw, _backend)
    return [AgentRunResult(agent_id=_backend, findings=findings, summary=raw.get("summary", ""))]


# Alias tương thích (chữ ký cũ có img — bỏ qua, text-only)
def run_all_agents(doc: CanonicalDoc, img=None, agent_ids=None, model: str | None = None):
    return run_review(doc, model=model)
