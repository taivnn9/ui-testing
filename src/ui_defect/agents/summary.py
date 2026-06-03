"""S1 — Summary: chốt severity, sort, format output."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from ..schema.models import BBox, CandidateIssue, SeverityRange
from ..schema.models import CanonicalDoc
from .runner import AgentFinding

# Mã catalog dạng XXX-NN (vd STY-01, LAY-02) nhúng trong tên rule.
# Khớp cả "STY-01_contrast" và "R1-LAY02" (không gạch giữa chữ và số).
_CODE_RE = re.compile(r"([A-Z]{3})-?(\d{2})")

_SEVERITY_ORDER = ["trivial", "low", "medium", "high", "critical"]
_SEVERITY_WEIGHT = {s: i + 1 for i, s in enumerate(_SEVERITY_ORDER)}

_ISSUE_TITLES: dict[str, str] = {
    "STY-01": "Contrast chữ/nền dưới WCAG AA",
    "STY-02": "Chữ tàng hình — màu giống nền",
    "STY-03": "Dark-mode không đổi màu",
    "STY-04": "Icon tàng hình trong dark mode",
    "STY-05": "Opacity sai",
    "STY-07": "Disabled không phân biệt enabled",
    "STY-08": "Trạng thái focus/selected không rõ",
    "STY-09": "Thông tin chỉ truyền bằng màu",
    "STY-10": "Gradient/shadow lỗi render",
    "STY-13": "Tương phản icon/đồ hoạ < 3:1",
    "LAY-01": "Va chạm phần tử — overlap",
    "LAY-02": "Nội dung bị cắt khỏi viewport",
    "LAY-03": "Tràn ra ngoài container cha",
    "LAY-04": "Lệch grid 8pt",
    "LAY-06": "Z-order: phần tử quan trọng bị che",
    "LAY-14": "Hai phần tử gần trùng vị trí",
    "CMP-01": "Vùng tap nhỏ hơn tiêu chuẩn",
    "CMP-02": "Nút icon-only không nhãn",
    "CMP-04": "Control sai state",
    "CMP-07": "Input thiếu label / focus",
    "CMP-16": "Khoảng tap giữa 2 control quá nhỏ",
    "CNT-01": "Biến/placeholder chưa render",
    "CNT-02": "i18n key lòi ra chưa dịch",
    "CNT-03": "Sai/lẫn ngôn ngữ",
    "CNT-04": "Lorem ipsum / placeholder copy",
    "CNT-05": "Text debug nội bộ",
    "CNT-06": "Mojibake / HTML entity thô",
    "CNT-07": "Escape literal hiện như text",
    "CNT-08": "Epoch / số sai format",
    "TYP-01": "Glyph thiếu / tofu box",
    "TYP-03": "Chữ bị cắt cụt",
    "TYP-05": "Cỡ chữ quá nhỏ",
    "TYP-09": "Chữ mờ / vỡ / răng cưa",
    "TYP-12": "RTL/bidi hỏng",
    "IMG-01": "Ảnh vỡ / không load được",
    "IMG-02": "Méo / sai tỉ lệ ảnh",
    "IMG-03": "Ảnh mờ / pixel hoá",
    "IMG-07": "Icon lệch tâm trong nút",
    "IMG-08": "Icon placeholder / chưa load",
    "IMG-12": "Ảnh trùng lặp",
    "STATE-01": "Skeleton loader visible",
    "STATE-02": "Empty state thiếu thông báo",
    "STATE-03": "Error state hiển thị lỗi thô",
    "STATE-06": "Loading overlay không tắt",
    "ENV-01": "Safe-area / notch che nội dung",
    "ENV-02": "Status bar overlap",
    "ENV-03": "Home indicator overlap",
}


@dataclass
class IssueOutput:
    id: str
    issue_type: str
    title: str
    severity: str
    confidence: float
    tags: list[str]
    temporal: bool
    element_id: str | None
    element_role: str | None
    element_bbox: dict | None
    element_text: str | None
    evidence: dict
    description: str
    sources: list[str]


@dataclass
class AnalyzeOutput:
    screen_id: str
    summary: dict
    issues: list[IssueOutput]
    pipeline_meta: dict


_ISSUE_TAGS: dict[str, list[str]] = {
    "STY-01": ["a11y"], "STY-02": ["a11y"], "STY-03": ["dark"],
    "STY-04": ["dark", "a11y"], "STY-07": ["a11y"], "STY-08": ["a11y"],
    "STY-09": ["a11y"], "STY-13": ["a11y"],
    "CMP-01": ["a11y", "mob"], "CMP-16": ["a11y", "mob"],
    "CNT-02": ["i18n"], "CNT-03": ["i18n"], "CNT-06": ["i18n"],
    "CNT-07": ["i18n"], "CNT-08": ["i18n"],
    "TYP-01": ["i18n"], "TYP-12": ["i18n"],
    "LAY-02": ["resp"], "TYP-09": ["resp"],
    "ENV-01": ["mob"], "ENV-02": ["mob"], "ENV-03": ["mob"],
}


def _make_issue_id(issue_type: str, element_id: str | None, screen_id: str) -> str:
    key = f"{screen_id}:{issue_type}:{element_id or 'global'}"
    return "iss_" + hashlib.md5(key.encode()).hexdigest()[:8]


def _sort_priority(issue: IssueOutput, viewport_h: int) -> float:
    sev_w = _SEVERITY_WEIGHT.get(issue.severity, 1)
    fold_w = 1.5 if (issue.element_bbox and issue.element_bbox.get("y", 999) < viewport_h * 0.4) else 1.0
    return sev_w * issue.confidence * fold_w


def _issue_type_from_rule(rule: str) -> str:
    """Trích mã catalog (STY-01…) từ tên rule; không có thì trả nguyên tên rule."""
    m = _CODE_RE.search(rule)
    return f"{m.group(1)}-{m.group(2)}" if m else rule


def _candidate_to_issue(
    c: CandidateIssue, screen_id: str, elem_map: dict
) -> IssueOutput:
    """
    Map CandidateIssue (rule engine) → IssueOutput trực tiếp, KHÔNG qua VLM.
    Dùng cho chế độ rule-only (run_vlm=false) để vẫn trả lỗi tất định.
    """
    issue_type = _issue_type_from_rule(c.rule)
    elem = elem_map.get(c.element or "")
    bbox_dict = None
    if elem:
        bbox_dict = {"x": round(elem.bbox.x), "y": round(elem.bbox.y),
                     "w": round(elem.bbox.w), "h": round(elem.bbox.h)}
    evidence: dict = {}
    if c.evidence:
        if c.evidence.bbox:
            b = c.evidence.bbox
            evidence["bbox"] = {"x": round(b.x), "y": round(b.y),
                                "w": round(b.w), "h": round(b.h)}
        if c.evidence.crop:
            evidence["crop"] = c.evidence.crop
    return IssueOutput(
        id=_make_issue_id(issue_type, c.element, screen_id),
        issue_type=issue_type,
        title=_ISSUE_TITLES.get(issue_type, issue_type),
        severity=c.severity,
        confidence=round(c.confidence, 2),
        tags=_ISSUE_TAGS.get(issue_type, []),
        temporal=False,
        element_id=c.element,
        element_role=elem.role if elem else None,
        element_bbox=bbox_dict,
        element_text=elem.text[:80] if elem and elem.text else None,
        evidence=evidence,
        description=c.detail,
        sources=[c.rule, "rule-engine"],
    )


def build_summary(
    findings: list[AgentFinding],
    doc: CanonicalDoc,
    screen_id: str,
    pipeline_meta: dict | None = None,
    rule_only_fallback: bool = False,
) -> AnalyzeOutput:
    """
    Gom findings (VLM) → output.

    `rule_only_fallback=True` (chế độ run_vlm=false): không có VLM findings nên
    surface thẳng `doc.candidate_issues` từ rule engine → vẫn có kết quả tất định
    (contrast, touch-target, placeholder…) mà không cần llama.cpp server.
    """
    elem_map = {e.id: e for e in doc.elements}
    viewport_h = doc.screen.viewport.h

    issues: list[IssueOutput] = []

    if rule_only_fallback and not findings:
        for c in doc.candidate_issues:
            issues.append(_candidate_to_issue(c, screen_id, elem_map))

    for f in findings:
        elem = elem_map.get(f.element_id or "")
        bbox_dict = None
        if elem:
            bbox_dict = {"x": round(elem.bbox.x), "y": round(elem.bbox.y),
                         "w": round(elem.bbox.w), "h": round(elem.bbox.h)}

        sources = [f"agent:{f.agent_id}"]
        if f.original_candidate_rule:
            sources.insert(0, f.original_candidate_rule)

        iss = IssueOutput(
            id=_make_issue_id(f.issue_type, f.element_id, screen_id),
            issue_type=f.issue_type,
            title=_ISSUE_TITLES.get(f.issue_type, f.issue_type),
            severity=f.severity,
            confidence=round(f.confidence, 2),
            tags=_ISSUE_TAGS.get(f.issue_type, []),
            temporal=f.temporal,
            element_id=f.element_id,
            element_role=elem.role if elem else None,
            element_bbox=bbox_dict,
            element_text=elem.text[:80] if elem and elem.text else None,
            evidence=f.evidence,
            description=f.reasoning,
            sources=sources,
        )
        issues.append(iss)

    issues.sort(key=lambda i: _sort_priority(i, viewport_h), reverse=True)

    by_severity: dict[str, int] = {s: 0 for s in _SEVERITY_ORDER}
    for iss in issues:
        by_severity[iss.severity] = by_severity.get(iss.severity, 0) + 1

    cats: dict[str, int] = {}
    for iss in issues:
        prefix = iss.issue_type.split("-")[0]
        cats[prefix] = cats.get(prefix, 0) + 1
    top_cats = sorted(cats, key=lambda k: -cats[k])[:3]

    avg_conf = round(sum(i.confidence for i in issues) / len(issues), 2) if issues else 0.0

    return AnalyzeOutput(
        screen_id=screen_id,
        summary={
            "total_issues": len(issues),
            "by_severity": by_severity,
            "top_categories": top_cats,
            "confidence_avg": avg_conf,
        },
        issues=issues,
        pipeline_meta=pipeline_meta or {},
    )
