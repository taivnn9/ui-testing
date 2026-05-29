"""Analyzers — Phase 1 implementations."""
from .a5_ocr import extract_text, extract_text_in_regions, TextSegment
from .a3_box_layout import detect_layout, A3Config
from .a4_pixel_color import sample_colors, enrich_elements, PixelColorResult
from .a6_icon_detector import detect_icons, icon_regions_to_elements, A6Config
from .a8_glyph_inspector import inspect_glyph, inspect_batch, glyph_issues_to_candidates
from .a9_pixel_pattern import detect_patterns, patterns_to_candidates
from .a10_perceptual_hash import compute_hashes, find_duplicates, duplicates_to_candidates
from .a13_device_meta import resolve_metadata, MetaResult
from .a0_normalize import normalize, compute_relations

__all__ = [
    "extract_text", "extract_text_in_regions", "TextSegment",
    "detect_layout", "A3Config",
    "sample_colors", "enrich_elements", "PixelColorResult",
    "detect_icons", "icon_regions_to_elements", "A6Config",
    "inspect_glyph", "inspect_batch", "glyph_issues_to_candidates",
    "detect_patterns", "patterns_to_candidates",
    "compute_hashes", "find_duplicates", "duplicates_to_candidates",
    "resolve_metadata", "MetaResult",
    "normalize", "compute_relations",
]
