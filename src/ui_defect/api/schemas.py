"""Request / Response Pydantic schemas cho API."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    platform: str = Field(..., pattern="^(android|ios|web)$")
    viewport_w: int = Field(..., gt=0)
    viewport_h: int = Field(..., gt=0)
    dpr: float = Field(2.0, gt=0)
    locale: str = "en-US"
    theme: str = Field("light", pattern="^(light|dark|system)$")
    font_scale: float = 1.0
    route: Optional[str] = None
    safe_area_top: Optional[int] = None
    safe_area_bottom: Optional[int] = None
    min_severity: str = Field("low", pattern="^(critical|high|medium|low|trivial)$")
    min_confidence: float = Field(0.4, ge=0.0, le=1.0)
    agents: Optional[list[str]] = None


class EvidenceOut(BaseModel):
    element_ids: list[str] = []
    measured_value: Optional[str] = None
    expected_value: Optional[str] = None
    description: str = ""


class IssueOut(BaseModel):
    id: str
    issue_type: str
    title: str
    severity: str
    confidence: float
    tags: list[str]
    temporal: bool
    element_id: Optional[str]
    element_role: Optional[str]
    element_bbox: Optional[dict]
    element_text: Optional[str]
    evidence: dict
    description: str
    sources: list[str]


class SummaryOut(BaseModel):
    total_issues: int
    by_severity: dict[str, int]
    top_categories: list[str]
    confidence_avg: float


class AnalyzeResponse(BaseModel):
    screen_id: str
    analyzed_at: str
    screen: dict
    summary: SummaryOut
    issues: list[IssueOut]
    pipeline_meta: dict
