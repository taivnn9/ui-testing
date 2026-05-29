"""Tests cho utils/geometry.py."""
import pytest
from src.ui_defect.schema.models import BBox
from src.ui_defect.utils.geometry import (
    bbox_area, contains, gap_between, group_aligned, iou, normalize_bbox,
)


def bb(x, y, w, h):
    return BBox(x=x, y=y, w=w, h=h)


class TestIou:
    def test_no_overlap(self):
        assert iou(bb(0, 0, 10, 10), bb(20, 20, 10, 10)) == 0.0

    def test_full_overlap_identical(self):
        assert iou(bb(0, 0, 10, 10), bb(0, 0, 10, 10)) == pytest.approx(1.0)

    def test_partial_overlap(self):
        # 2 box 10×10, dịch 5px → overlap 5×10=50, union=150
        result = iou(bb(0, 0, 10, 10), bb(5, 0, 10, 10))
        assert result == pytest.approx(50 / 150, abs=0.01)

    def test_zero_area(self):
        assert iou(bb(0, 0, 0, 10), bb(0, 0, 10, 10)) == 0.0


class TestContains:
    def test_inner_fully_inside(self):
        outer = bb(0, 0, 100, 100)
        inner = bb(10, 10, 20, 20)
        assert contains(outer, inner) is True

    def test_inner_outside(self):
        outer = bb(0, 0, 50, 50)
        inner = bb(60, 60, 20, 20)
        assert contains(outer, inner) is False

    def test_partial_overlap_below_threshold(self):
        outer = bb(0, 0, 100, 100)
        inner = bb(80, 80, 40, 40)  # overlap = 20×20=400, inner area=1600 → 25%
        assert contains(outer, inner, threshold=0.8) is False

    def test_partial_overlap_above_threshold(self):
        outer = bb(0, 0, 100, 100)
        inner = bb(5, 5, 90, 90)   # inner mostly inside outer
        assert contains(outer, inner, threshold=0.8) is True


class TestNormalize:
    def test_normalize_center(self):
        bbox = bb(50, 50, 100, 100)
        norm = normalize_bbox(bbox, 200, 200)
        assert norm.x == pytest.approx(0.25)
        assert norm.y == pytest.approx(0.25)
        assert norm.w == pytest.approx(0.5)
        assert norm.h == pytest.approx(0.5)


class TestGap:
    def test_adjacent_boxes(self):
        a = bb(0, 0, 10, 10)
        b = bb(10, 0, 10, 10)  # giáp nhau
        assert gap_between(a, b) == pytest.approx(0.0)

    def test_gap_5px(self):
        a = bb(0, 0, 10, 10)
        b = bb(15, 0, 10, 10)
        assert gap_between(a, b) == pytest.approx(5.0)

    def test_overlapping_negative(self):
        # overlap → gap = 0 (không âm)
        a = bb(0, 0, 20, 20)
        b = bb(10, 0, 20, 20)
        assert gap_between(a, b) == pytest.approx(0.0)


class TestGroupAligned:
    def test_row_group(self):
        bboxes = [
            bb(0, 100, 50, 20),
            bb(60, 102, 50, 20),
            bb(120, 99, 50, 20),
        ]
        groups = group_aligned(bboxes, axis="row", tolerance=8.0)
        assert len(groups) == 1
        assert len(groups[0].indices) == 3

    def test_col_group(self):
        bboxes = [
            bb(100, 0, 50, 20),
            bb(102, 30, 50, 20),
            bb(99, 60, 50, 20),
        ]
        groups = group_aligned(bboxes, axis="col", tolerance=8.0)
        assert len(groups) == 1

    def test_no_group_below_min(self):
        # Chỉ 1 element → không tạo group
        bboxes = [bb(0, 0, 50, 20)]
        groups = group_aligned(bboxes, axis="row")
        assert groups == []

    def test_separate_rows(self):
        bboxes = [
            bb(0, 0, 50, 20),
            bb(60, 0, 50, 20),
            bb(0, 200, 50, 20),
            bb(60, 200, 50, 20),
        ]
        groups = group_aligned(bboxes, axis="row", tolerance=8.0)
        assert len(groups) == 2
