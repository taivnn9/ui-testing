"""Tests cho utils/color.py."""
import numpy as np
import pytest

from src.ui_defect.utils.color import (
    contrast_ratio,
    delta_e_cie76,
    relative_luminance,
    rgb_to_lab,
)


class TestRelativeLuminance:
    def test_black(self):
        assert relative_luminance((0, 0, 0)) == pytest.approx(0.0)

    def test_white(self):
        assert relative_luminance((255, 255, 255)) == pytest.approx(1.0, abs=0.001)

    def test_pure_red(self):
        L = relative_luminance((255, 0, 0))
        assert 0.2 < L < 0.22  # WCAG spec: ~0.2126

    def test_midgray(self):
        L = relative_luminance((128, 128, 128))
        assert 0.2 < L < 0.22


class TestContrastRatio:
    def test_black_on_white(self):
        cr = contrast_ratio((0, 0, 0), (255, 255, 255))
        assert cr == pytest.approx(21.0, abs=0.1)

    def test_white_on_white(self):
        cr = contrast_ratio((255, 255, 255), (255, 255, 255))
        assert cr == pytest.approx(1.0)

    def test_symmetric(self):
        a = (100, 100, 100)
        b = (200, 200, 200)
        assert contrast_ratio(a, b) == pytest.approx(contrast_ratio(b, a))

    def test_wcag_aa_fail(self):
        # xám nhạt trên trắng → fail AA (< 4.5)
        cr = contrast_ratio((180, 180, 180), (255, 255, 255))
        assert cr < 4.5

    def test_wcag_aa_pass(self):
        # đen đậm trên trắng → pass AA
        cr = contrast_ratio((0, 0, 0), (255, 255, 255))
        assert cr >= 4.5


class TestRgbToLab:
    def test_black_lab(self):
        black = np.array([[0, 0, 0]], dtype=np.uint8)
        lab = rgb_to_lab(black)
        assert lab[0, 0] == pytest.approx(0.0, abs=1.0)  # L≈0

    def test_white_lab(self):
        white = np.array([[255, 255, 255]], dtype=np.uint8)
        lab = rgb_to_lab(white)
        assert lab[0, 0] == pytest.approx(100.0, abs=2.0)  # L≈100

    def test_shape_preserved(self):
        pixels = np.random.randint(0, 255, (100, 3), dtype=np.uint8)
        lab = rgb_to_lab(pixels)
        assert lab.shape == (100, 3)

    def test_red_blue_different_a(self):
        red = rgb_to_lab(np.array([[255, 0, 0]], dtype=np.uint8))
        blue = rgb_to_lab(np.array([[0, 0, 255]], dtype=np.uint8))
        # a* của đỏ > a* của xanh
        assert red[0, 1] > blue[0, 1]


class TestDeltaE:
    def test_same_color_zero(self):
        white = np.array([100.0, 0.0, 0.0])
        assert delta_e_cie76(white, white) == pytest.approx(0.0)

    def test_black_white_large(self):
        black_lab = np.array([0.0, 0.0, 0.0])
        white_lab = np.array([100.0, 0.0, 0.0])
        assert delta_e_cie76(black_lab, white_lab) == pytest.approx(100.0)
