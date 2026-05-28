from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

SourceType = Literal["dom", "xml", "vision", "pixel"]
ModeType = Literal["A_tree", "B_vision", "mixed"]
PlatformType = Literal["android", "ios", "web"]
SeverityType = Literal["critical", "high", "medium", "low", "trivial"]
RelType = Literal["left_of", "right_of", "above", "below", "contains", "overlaps", "sibling"]
RoleType = Literal[
    "button", "text", "image", "icon", "input", "toggle",
    "list", "container", "tab", "nav", "modal", "skeleton", "spinner", "unknown",
]


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Viewport(BaseModel):
    w: int
    h: int
    dpr: float = 1.0


class SafeArea(BaseModel):
    top: int = 0
    bottom: int = 0
    left: int = 0
    right: int = 0


class Screen(BaseModel):
    id: str
    platform: PlatformType
    route: Optional[str] = None
    mode: ModeType
    viewport: Viewport
    safe_area: SafeArea = Field(default_factory=SafeArea)
    theme: Literal["light", "dark", "system"] = "light"
    locale: str = "en-US"
    font_scale: float = 1.0
    ts: Optional[str] = None


class Image(BaseModel):
    full: str
    w: int
    h: int


class StyleSources(BaseModel):
    font_size: Optional[SourceType] = None
    font_family: Optional[SourceType] = None
    color: Optional[SourceType] = None
    bg_color: Optional[SourceType] = None
    contrast_ratio: Optional[SourceType] = None
    opacity: Optional[SourceType] = None
    border_radius: Optional[SourceType] = None


class Style(BaseModel):
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    color: Optional[str] = None
    bg_color: Optional[str] = None
    contrast_ratio: Optional[float] = None
    opacity: float = 1.0
    border_radius: Optional[float] = None
    sources: Optional[StyleSources] = Field(None, alias="_sources")

    model_config = {"populate_by_name": True}


class ImageMeta(BaseModel):
    intrinsic_w: Optional[int] = None
    intrinsic_h: Optional[int] = None
    displayed_w: Optional[int] = None
    displayed_h: Optional[int] = None
    scale_mode: Optional[Literal["fill", "fit", "stretch", "tile", "none"]] = None


class TouchTarget(BaseModel):
    w: float
    h: float


class Element(BaseModel):
    id: str
    role: RoleType
    source: SourceType
    confidence: float = 1.0
    bbox: BBox
    bbox_norm: BBox
    parent: Optional[str] = None
    children: list[str] = Field(default_factory=list)
    z: int = 0
    text: Optional[str] = None
    text_truncated: bool = False
    style: Optional[Style] = None
    image_meta: Optional[ImageMeta] = None
    interactive: bool = False
    touch_target: Optional[TouchTarget] = None
    visible: bool = True
    clipped: bool = False
    offscreen: bool = False
    crop: Optional[str] = None


class Relation(BaseModel):
    a: str
    rel: RelType
    b: str
    gap: float = 0.0
    iou: float = 0.0


class SeverityRange(BaseModel):
    min: SeverityType
    max: SeverityType


class Evidence(BaseModel):
    bbox: Optional[BBox] = None
    crop: Optional[str] = None


class CandidateIssue(BaseModel):
    rule: str
    element: Optional[str] = None
    severity: SeverityType
    severity_range: SeverityRange
    confidence: float = 1.0
    detail: str = ""
    evidence: Optional[Evidence] = None


class CanonicalDoc(BaseModel):
    screen: Screen
    image: Image
    elements: list[Element] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    candidate_issues: list[CandidateIssue] = Field(default_factory=list)
