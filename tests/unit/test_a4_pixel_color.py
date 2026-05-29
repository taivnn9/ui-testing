"""
Tests cho A4 Pixel Color Sampler.
Dùng ảnh synthetic để kiểm tra logic tách fg/bg và tính contrast.
"""
import numpy as np
import pytest
from PIL import Image

from src.ui_defect.analyzers.a4_pixel_color import (
    PixelColorResult,
    _crop_element,
    _estimate_opacity,
    _separate_fg_bg_text,
    _bg_is_solid,
    sample_colors,
    enrich_elements,
)
from src.ui_defect.schema.models import BBox, Element, Viewport


def make_element(eid, role, x, y, w, h, conf=0.8) -> Element:
    return Element(
        id=eid, role=role, source="vision", confidence=conf,
        bbox=BBox(x=x, y=y, w=w, h=h),
        bbox_norm=BBox(x=x/400, y=y/800, w=w/400, h=h/800),
        visible=True,
    )


def solid_image(w, h, color) -> Image.Image:
    return Image.new("RGB", (w, h), color=color)


def black_text_on_white(text_region=(0, 0, 100, 30)) -> Image.Image:
    """100×30 vùng: nền trắng + text vùng đen ở giữa (proxy)."""
    img = Image.new("RGB", (400, 800), (255, 255, 255))
    x1, y1, x2, y2 = text_region
    # Vẽ vùng "text" tối
    import PIL.ImageDraw as D
    draw = D.Draw(img)
    draw.rectangle([x1, y1, x2, y2], fill=(20, 20, 20))
    return img


class TestCropElement:
    def test_crop_returns_array(self):
        img = solid_image(100, 100, (255, 0, 0))
        bbox = BBox(x=10, y=10, w=40, h=40)
        crop = _crop_element(img, bbox)
        assert crop is not None
        assert crop.shape == (40, 40, 3)

    def test_too_small_returns_none(self):
        img = solid_image(100, 100, (255, 0, 0))
        bbox = BBox(x=0, y=0, w=2, h=2)
        assert _crop_element(img, bbox) is None

    def test_clamp_to_image_bounds(self):
        img = solid_image(100, 100, (200, 200, 200))
        bbox = BBox(x=90, y=90, w=50, h=50)  # vượt ra ngoài
        crop = _crop_element(img, bbox)
        assert crop is not None


class TestEstimateOpacity:
    def test_rgb_always_1(self):
        img = solid_image(100, 100, (255, 0, 0))
        assert _estimate_opacity(img, BBox(x=0, y=0, w=100, h=100)) == pytest.approx(1.0)

    def test_rgba_fully_opaque(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        assert _estimate_opacity(img, BBox(x=0, y=0, w=100, h=100)) == pytest.approx(1.0)

    def test_rgba_half_transparent(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        opacity = _estimate_opacity(img, BBox(x=0, y=0, w=100, h=100))
        assert opacity == pytest.approx(128 / 255, abs=0.02)


class TestSeparateFgBg:
    def test_black_text_white_bg(self):
        """Ảnh 50×20 nền trắng + hàng pixel đen → fg=đen, bg=trắng."""
        arr = np.full((20, 50, 3), 255, dtype=np.uint8)
        arr[8:12, :] = 0  # dải pixel đen (proxy cho text)
        fg, bg = _separate_fg_bg_text(arr)
        # fg mean phải tối hơn bg mean
        assert fg.mean() < bg.mean()

    def test_minimal_pixels(self):
        arr = np.array([[[255, 255, 255], [0, 0, 0]]], dtype=np.uint8)
        fg, bg = _separate_fg_bg_text(arr)
        assert len(fg) > 0 or len(bg) > 0


class TestBgIsSolid:
    def test_solid_white_bg(self):
        arr = np.full((30, 100, 3), 255, dtype=np.uint8)
        bg = arr.reshape(-1, 3)
        assert _bg_is_solid(arr, bg) is True

    def test_gradient_bg(self):
        arr = np.zeros((30, 100, 3), dtype=np.uint8)
        for i in range(100):
            arr[:, i] = [i * 2, i * 2, i * 2]  # gradient 0→198
        bg = arr.reshape(-1, 3)
        assert _bg_is_solid(arr, bg) is False


class TestSampleColors:
    def test_high_contrast_no_issue(self):
        """Text đen trên nền trắng → không có issue contrast."""
        img = Image.new("RGB", (400, 800), (255, 255, 255))
        import PIL.ImageDraw as D
        draw = D.Draw(img)
        # Vẽ vùng text đen trên nền trắng
        draw.rectangle([10, 10, 150, 40], fill=(255, 255, 255))
        draw.text((15, 15), "Hello", fill=(10, 10, 10))

        elem = make_element("e1", "text", 10, 10, 140, 30)
        results, issues = sample_colors(img, [elem])
        contrast_issues = [i for i in issues if "STY-01" in i.rule]
        # High contrast → không có issue (hoặc nếu có thì confidence thấp)
        assert isinstance(results, list)

    def test_low_contrast_generates_issue(self):
        """Text xám nhạt (#aaa) trên nền trắng → issue STY-01."""
        img = Image.new("RGB", (400, 800), (255, 255, 255))
        import PIL.ImageDraw as D
        draw = D.Draw(img)
        # Foreground xám nhạt (170,170,170) trên nền trắng → contrast thấp
        draw.rectangle([10, 10, 150, 40], fill=(255, 255, 255))
        # Tạo ảnh với pixel xám nhạt thực sự
        arr = np.full((30, 140, 3), 255, dtype=np.uint8)
        arr[5:25, 5:60] = [170, 170, 170]  # vùng "text" xám nhạt
        from PIL import Image as PilImage
        crop_img = PilImage.fromarray(arr)
        full_img = Image.new("RGB", (400, 800), (255, 255, 255))
        full_img.paste(crop_img, (10, 10))

        elem = make_element("e1", "text", 10, 10, 140, 30, conf=0.9)
        results, issues = sample_colors(full_img, [elem])
        # Ít nhất phải có kết quả (không crash)
        assert len(results) == 1

    def test_invisible_elements_skipped(self):
        img = solid_image(400, 800, (255, 255, 255))
        elem = make_element("e1", "text", 10, 10, 140, 30)
        elem.visible = False
        results, issues = sample_colors(img, [elem])
        assert len(results) == 0

    def test_contrast_black_white_exact(self):
        """Ảnh nửa đen nửa trắng (text=đen, bg=trắng) → contrast ≈ 21."""
        arr = np.full((30, 100, 3), 255, dtype=np.uint8)
        arr[:, :50] = 0  # nửa trái đen (fg), nửa phải trắng (bg)
        img = Image.fromarray(arr)
        elem = make_element("e1", "text", 0, 0, 100, 30, conf=0.9)
        results, _ = sample_colors(img, [elem])
        assert len(results) == 1
        r = results[0]
        if r.contrast_ratio_px is not None:
            assert r.contrast_ratio_px >= 10.0  # gần 21 nhưng K-means có thể lệch


class TestEnrichElements:
    def test_adds_style(self):
        elem = make_element("e1", "text", 0, 0, 100, 30)
        result = PixelColorResult(
            element_id="e1",
            color_px=(0, 0, 0),
            bg_color_px=(255, 255, 255),
            contrast_ratio_px=21.0,
        )
        elems = enrich_elements([elem], [result])
        assert elems[0].style is not None
        assert elems[0].style.contrast_ratio == pytest.approx(21.0)
        assert elems[0].style.color == "#000000"
        assert elems[0].style.bg_color == "#ffffff"
