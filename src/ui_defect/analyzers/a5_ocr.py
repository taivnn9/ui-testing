"""
A5 — OCR / Text Extractor
Trích text + bbox từ ảnh. PaddleOCR (primary) + Tesseract (fallback).
Spec: docs/analyzers/A5-ocr-text-extractor.md
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

from ..schema.models import BBox, Viewport
from ..utils.geometry import normalize_bbox


# ── Kiểu dữ liệu đầu ra ─────────────────────────────────────────────────────

@dataclass
class TextSegment:
    text: str
    bbox: BBox
    bbox_norm: BBox
    confidence: float = 1.0
    level: str = "line"          # word | line | block
    parent: Optional[int] = None # index segment cha
    script: str = "unknown"      # latin|cjk|arabic|cyrillic|digit|mixed|unknown
    lang_hint: Optional[str] = None
    angle: float = 0.0
    has_replacement: bool = False # U+FFFD □ nghi tofu
    source: str = "vision"


# ── Helpers ──────────────────────────────────────────────────────────────────

_REPLACEMENT_CHARS = {"�", "□", "■"}


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def _has_replacement(text: str) -> bool:
    return any(c in text for c in _REPLACEMENT_CHARS)


def _detect_script(text: str) -> str:
    if not text:
        return "unknown"
    latin = cjk = arabic = cyrillic = digit = 0
    for ch in text:
        cp = ord(ch)
        if 0x0030 <= cp <= 0x0039:
            digit += 1
        elif 0x0041 <= cp <= 0x007A or 0x00C0 <= cp <= 0x024F or 0x1E00 <= cp <= 0x1EFF:
            latin += 1
        elif 0x4E00 <= cp <= 0x9FFF or 0x3040 <= cp <= 0x30FF or 0xAC00 <= cp <= 0xD7A3:
            cjk += 1
        elif 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
            arabic += 1
        elif 0x0400 <= cp <= 0x04FF:
            cyrillic += 1
    counts = {"latin": latin, "cjk": cjk, "arabic": arabic,
              "cyrillic": cyrillic, "digit": digit}
    dominant = max(counts, key=lambda k: counts[k])
    total = sum(counts.values())
    if total == 0:
        return "unknown"
    if counts[dominant] / total >= 0.6:
        return dominant
    return "mixed"


# ── PaddleOCR backend ────────────────────────────────────────────────────────

def _run_paddle(
    img: Image.Image,
    viewport: Viewport,
    lang: str = "en",
) -> list[TextSegment]:
    """Chạy PaddleOCR; raise ImportError nếu không có paddle."""
    from paddleocr import PaddleOCR  # type: ignore[import]

    ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    arr = np.array(img.convert("RGB"))
    result = ocr.ocr(arr, cls=True)

    segments: list[TextSegment] = []
    if not result or not result[0]:
        return segments

    img_w, img_h = img.width, img.height
    for line in result[0]:
        if line is None:
            continue
        points, (text, conf) = line
        # points: 4 góc [[x,y],...] → lấy bbox bao quanh
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bbox = BBox(
            x=float(min(xs)), y=float(min(ys)),
            w=float(max(xs) - min(xs)),
            h=float(max(ys) - min(ys)),
        )
        text_n = _normalize_text(text)
        segments.append(TextSegment(
            text=text_n,
            bbox=bbox,
            bbox_norm=normalize_bbox(bbox, img_w, img_h),
            confidence=float(conf),
            level="line",
            script=_detect_script(text_n),
            has_replacement=_has_replacement(text_n),
        ))
    return segments


# ── Tesseract backend ────────────────────────────────────────────────────────

def _run_tesseract(
    img: Image.Image,
    viewport: Viewport,
) -> list[TextSegment]:
    """Chạy Tesseract qua pytesseract; raise ImportError nếu không có."""
    import pytesseract  # type: ignore[import]

    img_w, img_h = img.width, img.height
    data = pytesseract.image_to_data(
        img.convert("RGB"),
        output_type=pytesseract.Output.DICT,
        config="--psm 3",
    )
    segments: list[TextSegment] = []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i]
        if not text or not text.strip():
            continue
        conf = float(data["conf"][i])
        if conf < 0:
            continue
        x, y, w, h = (
            float(data["left"][i]),
            float(data["top"][i]),
            float(data["width"][i]),
            float(data["height"][i]),
        )
        if w <= 0 or h <= 0:
            continue
        bbox = BBox(x=x, y=y, w=w, h=h)
        text_n = _normalize_text(text)
        segments.append(TextSegment(
            text=text_n,
            bbox=bbox,
            bbox_norm=normalize_bbox(bbox, img_w, img_h),
            confidence=conf / 100.0,
            level="word",
            script=_detect_script(text_n),
            has_replacement=_has_replacement(text_n),
        ))
    return segments


# ── Group word → line ────────────────────────────────────────────────────────

def _group_into_lines(
    words: list[TextSegment],
    line_gap: float = 6.0,
) -> list[TextSegment]:
    """
    Gom word-level segments → line-level bằng cách cluster theo y-center.
    Trả về list gồm cả lines mới và words gốc (với parent trỏ về line index).
    """
    if not words:
        return []
    sorted_words = sorted(words, key=lambda s: s.bbox.y)
    lines: list[list[TextSegment]] = []
    current: list[TextSegment] = [sorted_words[0]]

    for seg in sorted_words[1:]:
        prev = current[-1]
        y_center_prev = prev.bbox.y + prev.bbox.h / 2
        y_center_curr = seg.bbox.y + seg.bbox.h / 2
        if abs(y_center_curr - y_center_prev) <= line_gap + prev.bbox.h * 0.5:
            current.append(seg)
        else:
            lines.append(current)
            current = [seg]
    lines.append(current)

    result: list[TextSegment] = []
    for line_words in lines:
        # Sắp theo x trong dòng (reading order LTR)
        line_words_sorted = sorted(line_words, key=lambda s: s.bbox.x)
        xs = [s.bbox.x for s in line_words_sorted]
        ys = [s.bbox.y for s in line_words_sorted]
        x2s = [s.bbox.x + s.bbox.w for s in line_words_sorted]
        y2s = [s.bbox.y + s.bbox.h for s in line_words_sorted]
        line_bbox = BBox(
            x=min(xs), y=min(ys),
            w=max(x2s) - min(xs),
            h=max(y2s) - min(ys),
        )
        line_text = " ".join(s.text for s in line_words_sorted)
        img_w = max(x2s)  # proxy; sẽ bị normalize_bbox dùng — để nguyên 0 nếu không biết
        # bbox_norm tính sau (cần img_w, img_h)
        line_idx = len(result)
        line_seg = TextSegment(
            text=_normalize_text(line_text),
            bbox=line_bbox,
            bbox_norm=BBox(x=0, y=0, w=0, h=0),  # điền sau
            confidence=min(s.confidence for s in line_words_sorted),
            level="line",
            script=_detect_script(line_text),
            has_replacement=any(s.has_replacement for s in line_words_sorted),
        )
        result.append(line_seg)
        for w in line_words_sorted:
            w.parent = line_idx
            result.append(w)

    return result


def _fill_bbox_norm(segments: list[TextSegment], img_w: int, img_h: int) -> None:
    for seg in segments:
        seg.bbox_norm = normalize_bbox(seg.bbox, img_w, img_h)


# ── Public API ───────────────────────────────────────────────────────────────

def extract_text(
    img: Image.Image,
    viewport: Viewport,
    lang: str = "en",
) -> list[TextSegment]:
    """
    Trích text từ ảnh. Thử PaddleOCR trước; nếu không có thì Tesseract.
    Trả về list TextSegment (level=line là chính, level=word có parent).
    """
    try:
        segments = _run_paddle(img, viewport, lang=lang)
        engine = "paddle"
    except (ImportError, Exception):
        try:
            segments = _run_tesseract(img, viewport)
            # Tesseract trả words → gom thành lines
            words = [s for s in segments if s.level == "word"]
            segments = _group_into_lines(words)
            engine = "tesseract"
        except (ImportError, Exception):
            return []

    _fill_bbox_norm(segments, img.width, img.height)
    return segments


def extract_text_in_regions(
    img: Image.Image,
    viewport: Viewport,
    regions: list[BBox],
    lang: str = "en",
) -> list[TextSegment]:
    """
    OCR từng vùng cụ thể (từ A3 bbox) → chính xác và nhanh hơn quét cả ảnh.
    Trả về segments với tọa độ trong hệ tọa độ ảnh gốc (không phải crop).
    """
    all_segments: list[TextSegment] = []
    for region in regions:
        from ..utils.image_io import crop_bbox
        crop = crop_bbox(img, region)
        if crop.width < 4 or crop.height < 4:
            continue
        # Tạo viewport tạm cho crop
        region_vp = Viewport(w=crop.width, h=crop.height, dpr=viewport.dpr)
        segs = extract_text(crop, region_vp, lang=lang)
        # Dịch bbox về tọa độ ảnh gốc
        for seg in segs:
            seg.bbox = BBox(
                x=seg.bbox.x + region.x,
                y=seg.bbox.y + region.y,
                w=seg.bbox.w,
                h=seg.bbox.h,
            )
        _fill_bbox_norm(segs, img.width, img.height)
        all_segments.extend(segs)
    return all_segments
