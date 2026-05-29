"""
Tests cho A5 OCR (không cần PaddleOCR/Tesseract cài sẵn).
Các test kiểm tra helper functions nội bộ.
"""
import pytest
from src.ui_defect.analyzers.a5_ocr import (
    _detect_script,
    _has_replacement,
    _normalize_text,
    _group_into_lines,
    TextSegment,
)
from src.ui_defect.schema.models import BBox


def make_seg(text, x, y, w=50, h=15, conf=0.9) -> TextSegment:
    bbox = BBox(x=x, y=y, w=w, h=h)
    bbox_norm = BBox(x=x/1000, y=y/1000, w=w/1000, h=h/1000)
    return TextSegment(
        text=text, bbox=bbox, bbox_norm=bbox_norm,
        confidence=conf, level="word",
    )


class TestNormalizeText:
    def test_strips_whitespace(self):
        assert _normalize_text("  hello  ") == "hello"

    def test_nfc_normalization(self):
        # "à" = à (NFD), NFC = "à"
        raw = "à"
        assert _normalize_text(raw) == "à"

    def test_empty(self):
        assert _normalize_text("") == ""


class TestHasReplacement:
    def test_replacement_char(self):
        assert _has_replacement("hel�o") is True

    def test_box_char(self):
        assert _has_replacement("□") is True

    def test_clean_text(self):
        assert _has_replacement("Đăng nhập") is False


class TestDetectScript:
    def test_latin(self):
        assert _detect_script("Hello world") == "latin"

    def test_digit_dominant(self):
        assert _detect_script("1234567890") == "digit"

    def test_cjk(self):
        assert _detect_script("你好世界") == "cjk"

    def test_arabic(self):
        assert _detect_script("مرحبا") == "arabic"

    def test_mixed(self):
        # Mix latin + CJK ngang nhau → "mixed"
        result = _detect_script("Hello你好")
        assert result in ("mixed", "latin", "cjk")

    def test_empty(self):
        assert _detect_script("") == "unknown"


class TestGroupIntoLines:
    def test_two_words_same_line(self):
        words = [
            make_seg("Hello", x=0, y=100),
            make_seg("world", x=60, y=102),
        ]
        result = _group_into_lines(words, line_gap=6.0)
        lines = [s for s in result if s.level == "line"]
        assert len(lines) == 1
        assert "Hello" in lines[0].text
        assert "world" in lines[0].text

    def test_two_separate_lines(self):
        words = [
            make_seg("Line1", x=0, y=0),
            make_seg("Line2", x=0, y=50),
        ]
        result = _group_into_lines(words, line_gap=6.0)
        lines = [s for s in result if s.level == "line"]
        assert len(lines) == 2

    def test_words_have_parent(self):
        words = [
            make_seg("A", x=0, y=100),
            make_seg("B", x=60, y=101),
        ]
        result = _group_into_lines(words)
        word_segs = [s for s in result if s.level == "word"]
        for w in word_segs:
            assert w.parent is not None

    def test_line_confidence_is_min(self):
        words = [
            make_seg("A", x=0, y=0, conf=0.9),
            make_seg("B", x=60, y=2, conf=0.6),
        ]
        result = _group_into_lines(words)
        lines = [s for s in result if s.level == "line"]
        assert lines[0].confidence == pytest.approx(0.6)

    def test_empty_input(self):
        assert _group_into_lines([]) == []

    def test_line_has_replacement_propagated(self):
        words = [
            make_seg("ok", x=0, y=0),
            make_seg("□fail", x=60, y=1),
        ]
        for w in words:
            w.has_replacement = "□" in w.text
        result = _group_into_lines(words)
        lines = [s for s in result if s.level == "line"]
        assert lines[0].has_replacement is True

    def test_source_is_vision(self):
        words = [make_seg("X", x=0, y=0)]
        result = _group_into_lines(words)
        for seg in result:
            assert seg.source == "vision"
