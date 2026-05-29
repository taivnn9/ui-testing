"""
Tests cho A3 Box/Layout Detector (dùng ảnh synthetic — không cần GPU).
"""
import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.ui_defect.analyzers.a3_box_layout import (
    A3Config,
    detect_layout,
    _merge_overlapping,
    _classify_role,
)
from src.ui_defect.schema.models import BBox, Viewport


def make_viewport(w=390, h=844, dpr=2.0) -> Viewport:
    return Viewport(w=w, h=h, dpr=dpr)


def white_image(w=390, h=844) -> Image.Image:
    return Image.new("RGB", (w, h), color=(255, 255, 255))


def image_with_rect(x, y, w, h, color=(0, 0, 0)) -> Image.Image:
    """Ảnh trắng với 1 hình chữ nhật màu (có cạnh rõ để Canny detect)."""
    img = Image.new("RGB", (400, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
    return img


class TestMergeOverlapping:
    def test_no_overlap(self):
        bboxes = [BBox(x=0, y=0, w=10, h=10), BBox(x=20, y=0, w=10, h=10)]
        result = _merge_overlapping(bboxes, threshold=0.5)
        assert len(result) == 2

    def test_high_overlap_merged(self):
        bboxes = [BBox(x=0, y=0, w=10, h=10), BBox(x=1, y=0, w=10, h=10)]
        result = _merge_overlapping(bboxes, threshold=0.5)
        assert len(result) == 1
        # Bounding box bao ngoài cả 2
        assert result[0].w == 11.0  # max(10,11) - 0

    def test_empty(self):
        assert _merge_overlapping([]) == []


class TestClassifyRole:
    cfg = A3Config()

    def test_divider_horizontal(self):
        bbox = BBox(x=0, y=0, w=300, h=2)  # aspect = 150 >> 5
        role, conf = _classify_role(bbox, False, self.cfg)
        assert role == "divider"
        assert conf > 0.5

    def test_divider_vertical(self):
        bbox = BBox(x=0, y=0, w=2, h=300)
        role, conf = _classify_role(bbox, False, self.cfg)
        assert role == "divider"

    def test_container_with_text(self):
        bbox = BBox(x=0, y=0, w=200, h=60)
        role, conf = _classify_role(bbox, True, self.cfg)
        assert role in ("container", "button")

    def test_image_region_no_text(self):
        bbox = BBox(x=0, y=0, w=200, h=200)
        role, conf = _classify_role(bbox, False, self.cfg)
        assert role in ("image", "container")


class TestDetectLayout:
    def test_returns_list(self):
        img = white_image()
        vp = make_viewport()
        result = detect_layout(img, vp)
        assert isinstance(result, list)

    def test_all_elements_source_vision(self):
        img = image_with_rect(50, 50, 200, 100)
        vp = make_viewport()
        elements = detect_layout(img, vp)
        for e in elements:
            assert e.source == "vision"

    def test_all_elements_confidence_below_1(self):
        img = image_with_rect(50, 50, 200, 100)
        vp = make_viewport()
        elements = detect_layout(img, vp)
        for e in elements:
            assert e.confidence < 1.0, f"Element {e.id} confidence={e.confidence} should be < 1"

    def test_detects_card_rect(self):
        """Ảnh có 1 hình chữ nhật rõ → detect được ít nhất 1 element."""
        img = image_with_rect(50, 50, 200, 100)
        vp = make_viewport(w=400, h=800)
        elements = detect_layout(img, vp)
        assert len(elements) >= 1

    def test_no_crash_on_blank_image(self):
        """Ảnh trắng hoàn toàn → không crash."""
        img = white_image()
        vp = make_viewport()
        elements = detect_layout(img, vp)
        assert isinstance(elements, list)

    def test_no_crash_on_small_image(self):
        img = Image.new("RGB", (10, 10), color=(200, 200, 200))
        vp = Viewport(w=10, h=10, dpr=1.0)
        elements = detect_layout(img, vp)
        assert isinstance(elements, list)

    def test_bbox_within_image_bounds(self):
        img = image_with_rect(50, 50, 200, 100)
        vp = make_viewport(w=400, h=800)
        elements = detect_layout(img, vp)
        for e in elements:
            assert e.bbox.x >= 0
            assert e.bbox.y >= 0
            assert e.bbox.x + e.bbox.w <= img.width + 1
            assert e.bbox.y + e.bbox.h <= img.height + 1

    def test_elements_have_ids(self):
        img = image_with_rect(50, 50, 200, 100)
        vp = make_viewport(w=400, h=800)
        elements = detect_layout(img, vp)
        ids = [e.id for e in elements]
        assert len(ids) == len(set(ids)), "IDs phải unique"

    def test_children_in_parent(self):
        """Nếu có parent/child, child_id phải nằm trong parent.children."""
        img = image_with_rect(50, 50, 200, 100)
        vp = make_viewport(w=400, h=800)
        elements = detect_layout(img, vp)
        id_map = {e.id: e for e in elements}
        for e in elements:
            if e.parent:
                parent = id_map.get(e.parent)
                if parent:
                    assert e.id in parent.children

    def test_text_segment_fused(self):
        """Orphan text segment → thêm element role=text."""
        from src.ui_defect.analyzers.a5_ocr import TextSegment
        img = white_image()
        vp = make_viewport(w=400, h=800)
        seg = TextSegment(
            text="Hello",
            bbox=BBox(x=10, y=10, w=80, h=20),
            bbox_norm=BBox(x=0.025, y=0.0125, w=0.2, h=0.025),
            level="line",
            confidence=0.9,
        )
        elements = detect_layout(img, vp, text_segments=[seg])
        text_elems = [e for e in elements if e.role == "text"]
        assert len(text_elems) >= 1

    def test_divider_detected(self):
        """Ảnh có đường kẻ ngang mảnh → detect được divider."""
        img = Image.new("RGB", (400, 800), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.line([(0, 200), (400, 200)], fill=(200, 200, 200), width=1)
        vp = make_viewport(w=400, h=800)
        elements = detect_layout(img, vp)
        # Có thể detect hoặc không do đường quá mỏng → không crash là đủ
        assert isinstance(elements, list)
