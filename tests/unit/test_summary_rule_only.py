"""
Test chế độ rule-only (run_vlm=false): build_summary phải surface
candidate_issues từ rule engine trực tiếp khi không có VLM findings.
"""
from src.ui_defect.agents.summary import build_summary, _issue_type_from_rule
from src.ui_defect.schema.models import (
    BBox, CandidateIssue, CanonicalDoc, Element, Evidence, Image,
    SafeArea, Screen, SeverityRange, Viewport,
)


def _doc_with_candidate() -> CanonicalDoc:
    elem = Element(
        id="e1", role="text", source="vision", confidence=0.9,
        bbox=BBox(x=10, y=20, w=100, h=30),
        bbox_norm=BBox(x=0.02, y=0.02, w=0.25, h=0.04),
        text="undefined",
    )
    cand = CandidateIssue(
        rule="STY-01_contrast", element="e1",
        severity="medium", severity_range=SeverityRange(min="low", max="high"),
        confidence=0.85, detail="contrast_ratio=2.1 < 4.5",
        evidence=Evidence(bbox=BBox(x=10, y=20, w=100, h=30)),
    )
    return CanonicalDoc(
        screen=Screen(id="s1", platform="android",
                      viewport=Viewport(w=390, h=844, dpr=2.0),
                      safe_area=SafeArea()),
        image=Image(full="screens/s1.png", w=390, h=844),
        elements=[elem], candidate_issues=[cand],
    )


def test_issue_type_extracts_catalog_code():
    assert _issue_type_from_rule("STY-01_contrast") == "STY-01"
    assert _issue_type_from_rule("R1-LAY02") == "LAY-02"
    assert _issue_type_from_rule("touch_target_min") == "touch_target_min"


def test_rule_only_surfaces_candidates():
    """run_vlm=false → candidate_issues trở thành output issues."""
    doc = _doc_with_candidate()
    out = build_summary(findings=[], doc=doc, screen_id="s1", rule_only_fallback=True)
    assert out.summary["total_issues"] == 1
    iss = out.issues[0]
    assert iss.issue_type == "STY-01"
    assert iss.severity == "medium"
    assert iss.element_id == "e1"
    assert iss.element_role == "text"
    assert iss.element_bbox == {"x": 10, "y": 20, "w": 100, "h": 30}
    assert "rule-engine" in iss.sources
    assert iss.evidence.get("bbox") is not None


def test_no_fallback_when_disabled():
    """Mặc định (VLM mode): không có findings → 0 issue, KHÔNG lộ candidate."""
    doc = _doc_with_candidate()
    out = build_summary(findings=[], doc=doc, screen_id="s1", rule_only_fallback=False)
    assert out.summary["total_issues"] == 0
