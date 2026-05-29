"""Protocol chung cho mọi analyzer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image

from ..schema.models import Viewport


@dataclass
class AnalyzerContext:
    """Dữ liệu đầu vào chung truyền qua pipeline."""
    image: Image.Image
    viewport: Viewport
    crops_dir: str = "crops"
