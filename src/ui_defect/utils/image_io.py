"""Tiện ích đọc/crop ảnh."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from ..schema.models import BBox


def load_image(path: str | Path) -> Image.Image:
    """Đọc ảnh; tự convert sang RGB (bỏ alpha channel nếu có, giữ cho RGBA)."""
    img = Image.open(path)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    return img


def image_to_numpy(img: Image.Image, mode: str = "RGB") -> np.ndarray:
    if img.mode != mode:
        img = img.convert(mode)
    return np.array(img, dtype=np.uint8)


def crop_bbox(img: Image.Image, bbox: BBox, padding: int = 0) -> Image.Image:
    """Crop vùng bbox (device px); padding tùy chọn."""
    x = max(0, int(bbox.x) - padding)
    y = max(0, int(bbox.y) - padding)
    x2 = min(img.width, int(bbox.x + bbox.w) + padding)
    y2 = min(img.height, int(bbox.y + bbox.h) + padding)
    return img.crop((x, y, x2, y2))


def save_crop(
    img: Image.Image,
    bbox: BBox,
    out_path: str | Path,
    padding: int = 0,
) -> None:
    crop = crop_bbox(img, bbox, padding)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path)
