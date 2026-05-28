from ui_defect.schema.models import (
    BBox,
    CandidateIssue,
    CanonicalDoc,
    Element,
    SeverityRange,
    Style,
    StyleSources,
)


def test_canonical_doc_empty(minimal_doc: CanonicalDoc) -> None:
    assert minimal_doc.elements == []
    assert minimal_doc.relations == []
    assert minimal_doc.candidate_issues == []


def test_element_defaults() -> None:
    el = Element(
        id="e1",
        role="button",
        source="vision",
        bbox=BBox(x=0, y=0, w=100, h=48),
        bbox_norm=BBox(x=0, y=0, w=0.1, h=0.02),
    )
    assert el.confidence == 1.0
    assert el.children == []
    assert el.interactive is False
    assert el.visible is True


def test_style_sources_alias() -> None:
    style = Style.model_validate({
        "font_size": 16,
        "contrast_ratio": 4.8,
        "_sources": {"contrast_ratio": "pixel"},
    })
    assert style.sources is not None
    assert style.sources.contrast_ratio == "pixel"


def test_candidate_issue_severity() -> None:
    issue = CandidateIssue(
        rule="touch_target_min",
        element="e1",
        severity="high",
        severity_range=SeverityRange(min="medium", max="critical"),
        detail="h=30px < 144px",
    )
    assert issue.severity == "high"
    assert issue.confidence == 1.0
