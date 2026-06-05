"""
A10 — Perceptual Hashing
Phát hiện ảnh/element trùng lặp trong cùng màn hình.
Spec: docs/analyzers/A10-perceptual-hashing.md
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PIL import Image

from ..schema.models import BBox, CandidateIssue, Element, SeverityRange
from ..schema.thresholds import HASH_IDENTICAL, HASH_NEAR_DUP


@dataclass
class HashResult:
    element_id: str
    hash_value: object  # imagehash.ImageHash
    bbox: BBox


@dataclass
class DuplicatePair:
    id_a: str
    id_b: str
    hamming_distance: int
    is_identical: bool
    is_near_dup: bool
    bbox_a: BBox
    bbox_b: BBox


def compute_hashes(
    img: Image.Image,
    elements: list[Element],
) -> list[HashResult]:
    """Tính perceptual hash (pHash) cho mỗi element có role=image."""
    import os
    if os.environ.get("A10_SKIP") == "1":
        return []
    import imagehash  # type: ignore[import]

    results = []
    for elem in elements:
        if elem.role not in ("image", "icon") or not elem.visible:
            continue
        x1 = max(0, int(elem.bbox.x))
        y1 = max(0, int(elem.bbox.y))
        x2 = min(img.width, int(elem.bbox.x + elem.bbox.w))
        y2 = min(img.height, int(elem.bbox.y + elem.bbox.h))
        if (x2 - x1) < 8 or (y2 - y1) < 8:
            continue
        crop = img.crop((x1, y1, x2, y2)).convert("RGB")
        h = imagehash.phash(crop)
        results.append(HashResult(element_id=elem.id, hash_value=h, bbox=elem.bbox))
    return results


def find_duplicates(
    hash_results: list[HashResult],
    identical_threshold: int = HASH_IDENTICAL,
    near_dup_threshold: int = HASH_NEAR_DUP,
) -> list[DuplicatePair]:
    """So sánh mọi cặp hash → tìm trùng lặp."""
    pairs: list[DuplicatePair] = []
    n = len(hash_results)
    for i in range(n):
        for j in range(i + 1, n):
            dist = int(hash_results[i].hash_value - hash_results[j].hash_value)
            if dist <= near_dup_threshold:
                pairs.append(DuplicatePair(
                    id_a=hash_results[i].element_id,
                    id_b=hash_results[j].element_id,
                    hamming_distance=dist,
                    is_identical=dist <= identical_threshold,
                    is_near_dup=dist <= near_dup_threshold,
                    bbox_a=hash_results[i].bbox,
                    bbox_b=hash_results[j].bbox,
                ))
    return pairs


def duplicates_to_candidates(
    pairs: list[DuplicatePair],
) -> list[CandidateIssue]:
    """Chuyển cặp trùng lặp thành CandidateIssue."""
    result = []
    for pair in pairs:
        if pair.is_identical:
            sev = "medium"
            sev_range = SeverityRange(min="low", max="high")
            rule = "IMG-dup-identical"
        else:
            sev = "low"
            sev_range = SeverityRange(min="trivial", max="medium")
            rule = "IMG-dup-near"
        result.append(CandidateIssue(
            rule=rule,
            element=pair.id_a,
            severity=sev,
            severity_range=sev_range,
            confidence=round(1.0 - pair.hamming_distance / 64.0, 2),
            detail=(
                f"element {pair.id_a} và {pair.id_b} trùng lặp "
                f"(hamming={pair.hamming_distance})"
            ),
        ))
    return result
