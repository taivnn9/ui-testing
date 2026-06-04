"""
Integration test cho Golden Set scoring harness (scripts/score_golden.py).

2 phần:
  1. Synthetic — tự dựng case+label inline (tmp_path) để kiểm logic matching TP/FP/FN
     KHÔNG phụ thuộc Agent A (golden thật có thể chưa tồn tại lúc test này chạy).
  2. Baseline — chạy rule-only trên golden THẬT (data/golden/schema). Nếu trống → skip.

Không import codex_client. Không gọi agent backend (rule-only, deterministic).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "score_golden.py"

# Baseline thoáng lúc đầu (xem F4.0 §5.7). TODO: siết lên ~0.9 sau khi golden ổn định.
BASELINE_PRECISION = 0.8
BASELINE_RECALL = 0.8


def _load_scorer():
    """Import scripts/score_golden.py như module (không nằm trong package)."""
    spec = importlib.util.spec_from_file_location("score_golden", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Đăng ký vào sys.modules TRƯỚC exec để @dataclass introspect được module
    # (annotation kiểu `str | None` cần cls.__module__ có trong sys.modules).
    sys.modules["score_golden"] = mod
    spec.loader.exec_module(mod)
    return mod


scorer = _load_scorer()


# ── Synthetic doc builders ────────────────────────────────────────────────────
def _clean_doc_json(button_wh: float = 144.0) -> dict:
    """
    1 CanonicalDoc tối giản & SẠCH (rule engine ra 0 issue khi button_wh đủ lớn).
    - bbox x=120,y=216 nằm trên lưới 8dp*dpr=24px → KHÔNG fire R1-LAY04.
    - touch target >= min_touch(android,dpr3)=144 → KHÔNG fire R1-CMP01.
    """
    return {
        "screen": {
            "id": "scr1",
            "platform": "android",
            "viewport": {"w": 1080, "h": 2400, "dpr": 3.0},
            "safe_area": {"top": 0, "bottom": 0, "left": 0, "right": 0},
        },
        "image": {"full": "x.png", "w": 1080, "h": 2400},
        "elements": [
            {
                "id": "e1",
                "role": "button",
                "source": "vision",
                "confidence": 1.0,
                "bbox": {"x": 120, "y": 216, "w": button_wh, "h": button_wh},
                "bbox_norm": {"x": 0, "y": 0, "w": 0, "h": 0},
                "interactive": True,
                "touch_target": {"w": button_wh, "h": button_wh},
            }
        ],
    }


def _tiny_button_doc_json() -> dict:
    """
    Touch target nhỏ (72 < min_touch 144) → R1-CMP01 fire trên e1.
    Vẫn để x=120,y=216 trên lưới → CHỈ R1-CMP01 fire (cô lập rule cho test matching).
    """
    return _clean_doc_json(button_wh=72.0)


def _write_pair(golden_dir: Path, case_id: str, case_json: dict, label: dict) -> None:
    (golden_dir / "cases").mkdir(parents=True, exist_ok=True)
    (golden_dir / "labels").mkdir(parents=True, exist_ok=True)
    (golden_dir / "cases" / f"{case_id}.json").write_text(json.dumps(case_json), encoding="utf-8")
    (golden_dir / "labels" / f"{case_id}.json").write_text(json.dumps(label), encoding="utf-8")


# ── Synthetic tests: TP / FP / FN ─────────────────────────────────────────────
def test_synthetic_true_positive(tmp_path: Path):
    """Case positive: tiny button → R1-CMP01 kêu đúng element → TP, precision=recall=1."""
    gdir = tmp_path / "schema"
    _write_pair(
        gdir,
        "cmp01_tiny_v1",
        _tiny_button_doc_json(),
        {
            "case_id": "cmp01_tiny_v1",
            "base": "syn",
            "mutation": "shrink_touch_target",
            "kind": "positive",
            "expected": [
                {"rule": "R1-CMP01", "element": "e1",
                 "severity_range": {"min": "low", "max": "critical"}},
            ],
        },
    )
    golden = scorer.load_golden(gdir)
    assert len(golden) == 1
    res = scorer.score(golden)
    assert res.overall.tp == 1
    assert res.overall.fn == 0
    assert res.overall.fp == 0
    assert res.overall.precision() == 1.0
    assert res.overall.recall() == 1.0


def test_synthetic_false_negative(tmp_path: Path):
    """Expected R1-CMP01 nhưng dùng doc SẠCH (button to) → rule không kêu → FN."""
    gdir = tmp_path / "schema"
    _write_pair(
        gdir,
        "cmp01_miss_v1",
        _clean_doc_json(),  # button to → không fire
        {
            "case_id": "cmp01_miss_v1",
            "base": "syn",
            "mutation": "none",
            "kind": "positive",
            "expected": [
                {"rule": "R1-CMP01", "element": "e1",
                 "severity_range": {"min": "low", "max": "critical"}},
            ],
        },
    )
    res = scorer.score(scorer.load_golden(gdir))
    assert res.overall.fn == 1
    assert res.overall.tp == 0
    assert res.overall.recall() == 0.0
    assert any(r.rule == "R1-CMP01" for r in res.false_negatives)


def test_synthetic_false_positive(tmp_path: Path):
    """Case negative (kind=negative, expected=[]) nhưng doc làm rule kêu → FP."""
    gdir = tmp_path / "schema"
    _write_pair(
        gdir,
        "neg_unexpected_v1",
        _tiny_button_doc_json(),  # sẽ fire R1-CMP01 dù không kỳ vọng
        {
            "case_id": "neg_unexpected_v1",
            "base": "syn",
            "mutation": "none",
            "kind": "negative",
            "expected": [],
        },
    )
    res = scorer.score(scorer.load_golden(gdir))
    assert res.overall.fp >= 1
    assert res.overall.tp == 0
    assert res.overall.precision() < 1.0
    assert any(r.rule == "R1-CMP01" for r in res.false_positives)


def test_synthetic_clean_negative_no_fp(tmp_path: Path):
    """Case negative với doc SẠCH → không issue nào → không FP."""
    gdir = tmp_path / "schema"
    _write_pair(
        gdir,
        "neg_clean_v1",
        _clean_doc_json(),
        {"case_id": "neg_clean_v1", "base": "syn", "mutation": "none",
         "kind": "negative", "expected": []},
    )
    res = scorer.score(scorer.load_golden(gdir))
    assert res.overall.fp == 0
    assert res.overall.tp == 0
    assert res.overall.fn == 0


def test_synthetic_severity_out_of_range_is_fn(tmp_path: Path):
    """Rule kêu đúng element nhưng severity NGOÀI range kỳ vọng → không TP (FN)."""
    gdir = tmp_path / "schema"
    _write_pair(
        gdir,
        "cmp01_sevbad_v1",
        _tiny_button_doc_json(),
        {
            "case_id": "cmp01_sevbad_v1",
            "base": "syn",
            "mutation": "shrink_touch_target",
            "kind": "positive",
            # range chỉ trivial..trivial — rule chắc chắn nặng hơn → không khớp.
            "expected": [
                {"rule": "R1-CMP01", "element": "e1",
                 "severity_range": {"min": "trivial", "max": "trivial"}},
            ],
        },
    )
    res = scorer.score(scorer.load_golden(gdir))
    # expected không match (severity lệch) → FN; candidate thừa → FP.
    assert res.overall.tp == 0
    assert res.overall.fn == 1


def test_severity_in_range_helper():
    assert scorer._severity_in_range("high", "medium", "critical")
    assert scorer._severity_in_range("medium", "medium", "medium")
    assert not scorer._severity_in_range("low", "high", "critical")
    # range ghi ngược vẫn chuẩn hoá đúng
    assert scorer._severity_in_range("high", "critical", "medium")


def test_rule_filter(tmp_path: Path):
    """--rule chỉ chấm rule chỉ định: lọc cả expected lẫn candidate."""
    gdir = tmp_path / "schema"
    _write_pair(
        gdir,
        "cmp01_tiny_v2",
        _tiny_button_doc_json(),
        {
            "case_id": "cmp01_tiny_v2", "base": "syn", "mutation": "shrink_touch_target",
            "kind": "positive",
            "expected": [
                {"rule": "R1-CMP01", "element": "e1",
                 "severity_range": {"min": "low", "max": "critical"}},
                {"rule": "R2-STY01", "element": "e1",
                 "severity_range": {"min": "low", "max": "critical"}},
            ],
        },
    )
    res = scorer.score(scorer.load_golden(gdir), rule_filter="R1-CMP01")
    # Chỉ xét R1-CMP01: TP=1, không tính expected R2 (đã lọc khỏi expected).
    assert res.overall.tp == 1
    assert "R2-STY01" not in res.per_rule


# ── Baseline test trên golden THẬT (skip nếu trống) ───────────────────────────
def test_golden_baseline_rule_only():
    """
    Rule-only trên golden thật: precision & recall >= BASELINE.
    TODO: siết baseline lên sau khi golden set ổn định (hiện 0.8/0.8).
    """
    golden_dir = _REPO_ROOT / "data" / "golden" / "schema"
    golden = scorer.load_golden(golden_dir)
    if not golden:
        pytest.skip(
            f"Golden set trống ({golden_dir}/cases + labels). "
            "Agent A chưa sinh dữ liệu — bỏ qua baseline."
        )
    res = scorer.score(golden)
    p, r = res.overall.precision(), res.overall.recall()
    assert p >= BASELINE_PRECISION, (
        f"precision={p:.3f} < baseline {BASELINE_PRECISION}. "
        f"FP={[(x.case_id, x.rule, x.element) for x in res.false_positives]}"
    )
    assert r >= BASELINE_RECALL, (
        f"recall={r:.3f} < baseline {BASELINE_RECALL}. "
        f"FN={[(x.case_id, x.rule, x.element) for x in res.false_negatives]}"
    )
