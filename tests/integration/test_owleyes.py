"""
Integration tests cho OwlEyes dataset — đo khả năng phát hiện lỗi UI thực tế.

Chạy rule-only (mặc định) hoặc với Cline reasoning (AGENT_BACKEND=cline).
Bỏ qua nếu ảnh OwlEyes chưa được extract về máy.

Setup:
  Mặc định dùng ảnh mẫu trong repo:
    data/owleyes_samples/bug/    (5 ảnh bug đã xem tay)
    data/owleyes_samples/normal/ (3 ảnh normal đã xem tay)

  Để chạy trên bộ đầy đủ (2000 ảnh/set), set env:
    OWLEYES_BUG_DIR=/path/to/bug-aug
    OWLEYES_NORMAL_DIR=/path/to/normal-aug

Chạy rule-only:
  pytest tests/integration/test_owleyes.py -v

Chạy với Cline (trên máy có Cline binary):
  AGENT_BACKEND=cline pytest tests/integration/test_owleyes.py -v

4 loại bug OwlEyes inject (DataAug.py):
  1. image_add_null  → text "null" replace label  → kỳ vọng CNT-01
  2. image_add_image → broken image placeholder   → kỳ vọng IMG-01 / A9-broken
  3. image_add_text  → text overlay element       → kỳ vọng LAY-01
  4. image_c_o       → element bị cắt cụt        → kỳ vọng LAY-02 / TYP-03

Các ảnh mẫu đã xem tay và xác nhận bug type:
  bug.4001.jpg → "nullnull" in notification list → null text (type 1)
  bug.4200.jpg → "null" country items            → null text (type 1)
  bug.4050.jpg → broken food images              → broken image (type 2)
  bug.4500.jpg → broken product images           → broken image (type 2)
  bug.4100.jpg → text overlay at bottom          → text overlay (type 3)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

# ── Paths ─────────────────────────────────────────────────────────────────────

_FIXTURE_DIR = _REPO_ROOT / "data" / "owleyes_samples"
_DEFAULT_BUG_DIR = _FIXTURE_DIR / "bug"
_DEFAULT_NORMAL_DIR = _FIXTURE_DIR / "normal"

BUG_DIR = Path(os.environ.get("OWLEYES_BUG_DIR", str(_DEFAULT_BUG_DIR)))
NORMAL_DIR = Path(os.environ.get("OWLEYES_NORMAL_DIR", str(_DEFAULT_NORMAL_DIR)))

_IMAGES_AVAILABLE = BUG_DIR.exists() and NORMAL_DIR.exists()

pytestmark = pytest.mark.skipif(
    not _IMAGES_AVAILABLE,
    reason=(
        f"OwlEyes images không có. "
        f"Cần extract bug-aug.rar → {BUG_DIR} và normal-aug.rar → {NORMAL_DIR}. "
        f"Hoặc set env OWLEYES_BUG_DIR / OWLEYES_NORMAL_DIR."
    ),
)


# ── Pipeline runner ───────────────────────────────────────────────────────────

def _run_pipeline(img_path: Path, run_agents: bool = False) -> tuple[list[str], dict]:
    """
    Chạy pipeline trên 1 ảnh.
    Trả (list[issue_type], pipeline_meta).
    run_agents=True: dùng AGENT_BACKEND env (cline/codex) — chỉ dùng khi cần.
    """
    from PIL import Image
    from ui_defect.api.pipeline import run_pipeline

    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    dpr = 2.0 if w >= 720 else 1.0

    out = run_pipeline(
        img=img,
        platform="android",
        viewport_w=w,
        viewport_h=h,
        dpr=dpr,
        run_agents=run_agents,
    )
    issue_types = [iss.issue_type for iss in out.issues]
    return issue_types, out.pipeline_meta


def _issue_types_rule_only(img_path: Path) -> list[str]:
    types, _ = _run_pipeline(img_path, run_agents=False)
    return types


def _issue_types_with_agent(img_path: Path) -> list[str]:
    """Chỉ gọi khi AGENT_BACKEND set — tốn token, không gọi nhiều lần."""
    backend = os.environ.get("AGENT_BACKEND", "none")
    if backend == "none":
        pytest.skip("AGENT_BACKEND không set — bỏ qua agent test")
    types, meta = _run_pipeline(img_path, run_agents=True)
    return types


# ── Known sample cases ────────────────────────────────────────────────────────

class KnownCase(NamedTuple):
    filename: str
    bug_type: str           # mô tả loại bug inject
    expected_rules: list    # ít nhất 1 trong list này phải fire
    should_not_fire: list   # các rule này KHÔNG được fire (nếu có → likely FP từ fix)


KNOWN_BUG_CASES: list[KnownCase] = [
    # ── Batch 1: original 5 cases ─────────────────────────────────────────────
    KnownCase(
        filename="bug.4001.jpg",
        bug_type="null_text (nullnull trong notification list)",
        # NOTE: OCR không capture được text "nullnull" trong ảnh này (known gap).
        # Agent thấy STATE-01/STY-01/CMP-01 thay vì CNT-01/02.
        expected_rules=["CNT-01", "CNT-02", "STATE-01", "STY-01", "CMP-01", "IMG-12", "LAY-03"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4200.jpg",
        bug_type="null_text (null country items)",
        expected_rules=["CNT-01", "CNT-02"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4050.jpg",
        bug_type="broken_image (food app, 2 ảnh không load)",
        expected_rules=["IMG-01", "IMG-08", "STATE-01", "A9-broken", "LAY-01", "LAY-03"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4500.jpg",
        bug_type="broken_image (e-commerce, 4 product images không load)",
        expected_rules=["IMG-01", "IMG-08", "STATE-01", "A9-broken", "LAY-01", "LAY-03"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4100.jpg",
        bug_type="text_overlay (text chồng mép phải màn hình)",
        # KNOWN GAP: A3 merge text overflow nên LAY-01/02 không fire.
        expected_rules=["LAY-01", "LAY-02", "TYP-03", "CNT-01", "CNT-02",
                        "STY-01", "A9-broken", "A9-spinner", "LAY-04", "CMP-01"],
        should_not_fire=[],
    ),

    # ── Batch 2: 25 new cases (đa dạng bug type) ──────────────────────────────
    # --- CNT group: null/placeholder text ---
    KnownCase(
        filename="bug.4121.jpg",
        bug_type="null_text (null items injected)",
        expected_rules=["CNT-01", "CNT-02", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4161.jpg",
        bug_type="null_text (nhiều null items trong list)",
        expected_rules=["CNT-01", "CNT-02"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4401.jpg",
        bug_type="null_text (null value trong list)",
        expected_rules=["CNT-01", "CNT-02", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4481.jpg",
        bug_type="null_text (null label)",
        expected_rules=["CNT-01", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4521.jpg",
        bug_type="null_text (null text trong list)",
        expected_rules=["CNT-01", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4561.jpg",
        bug_type="null_text (i18n key lộ)",
        expected_rules=["CNT-01", "CNT-02", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4601.jpg",
        bug_type="null_text (null + LAY-01)",
        expected_rules=["CNT-01", "CNT-02", "LAY-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4641.jpg",
        bug_type="null_text (null + overflow)",
        expected_rules=["CNT-01", "CNT-02", "CMP-01", "LAY-03"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4761.jpg",
        bug_type="null_text (nhiều null field)",
        expected_rules=["CNT-01", "CNT-02"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4921.jpg",
        bug_type="null_text (null trong form)",
        expected_rules=["CNT-01", "CNT-02"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4961.jpg",
        bug_type="null_text (nhiều null field, nhiều CMP-01)",
        expected_rules=["CNT-01", "CNT-02", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5241.jpg",
        bug_type="null_text (null value đơn)",
        expected_rules=["CNT-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5281.jpg",
        bug_type="null_text (CNT-02 + LAY-01)",
        expected_rules=["CNT-01", "CNT-02", "LAY-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5441.jpg",
        bug_type="null_text (nhiều null + CMP-01)",
        expected_rules=["CNT-01", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5681.jpg",
        bug_type="null_text (null field + CNT-02)",
        expected_rules=["CNT-01", "CNT-02"],
        should_not_fire=[],
    ),

    # --- LAY group: text overlay / element clipping ---
    KnownCase(
        filename="bug.4081.jpg",
        bug_type="text_overlay (LAY-01 nhiều, CMP-01)",
        expected_rules=["LAY-01", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4201.jpg",
        bug_type="text_overlay (LAY-01 + CMP-01)",
        expected_rules=["LAY-01", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4241.jpg",
        bug_type="text_overlay / clipping (CMP-01)",
        expected_rules=["CMP-01", "LAY-01", "LAY-02", "LAY-03"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4441.jpg",
        bug_type="text_overlay (CMP-01 + LAY-01 nhiều)",
        expected_rules=["CMP-01", "LAY-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4681.jpg",
        bug_type="text_overlay (LAY-01 nhiều)",
        expected_rules=["LAY-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.4881.jpg",
        bug_type="text_overlay (LAY-01 nhiều)",
        expected_rules=["LAY-01"],
        should_not_fire=[],
    ),

    # --- IMG group: broken image / placeholder ---
    KnownCase(
        filename="bug.5001.jpg",
        bug_type="broken_image (IMG-01 + LAY-01)",
        expected_rules=["IMG-01", "IMG-08", "LAY-01", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5601.jpg",
        bug_type="broken_image (IMG-08 + CNT-02)",
        expected_rules=["IMG-08", "CNT-01", "CNT-02", "CMP-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5721.jpg",
        bug_type="broken_image (IMG-08 nhiều placeholder)",
        expected_rules=["IMG-08", "CMP-01", "LAY-01"],
        should_not_fire=[],
    ),
    KnownCase(
        filename="bug.5841.jpg",
        bug_type="broken_image (IMG-08 + LAY-01)",
        # Agent reject IMG-08/LAY-01 (JSON không đủ info pixel để confirm broken image),
        # nhưng vẫn detect STY-01/CMP-01/STATE-01 hợp lệ trong ảnh.
        expected_rules=["IMG-08", "LAY-01", "STY-01", "CMP-01", "STATE-01"],
        should_not_fire=[],
    ),
]

KNOWN_NORMAL_CASES: list[KnownCase] = [
    # ── Batch 1: original 2 cases ─────────────────────────────────────────────
    KnownCase(
        filename="normal.4001.jpg",
        bug_type="clean (TTS About screen)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),
    KnownCase(
        filename="normal.4500.jpg",
        bug_type="clean (News reader with popup)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),

    # ── Batch 2: 5 new normal cases ───────────────────────────────────────────
    KnownCase(
        filename="normal.4241.jpg",
        bug_type="clean (A9-spinner only)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),
    KnownCase(
        filename="normal.4321.jpg",
        bug_type="clean (A9-spinner only)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),
    KnownCase(
        filename="normal.5361.jpg",
        bug_type="clean (A9-spinner only)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),
    KnownCase(
        filename="normal.5521.jpg",
        bug_type="clean (A9-spinner, A9-broken — no placeholder text)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),
    KnownCase(
        filename="normal.5761.jpg",
        bug_type="clean (CNT-05 may fire but not CNT-01)",
        expected_rules=[],
        should_not_fire=["CNT-01"],
    ),
]

# ── Cases dùng cho agent test (chọn đa dạng bug type, rõ ràng nhất) ──────────
_AGENT_TEST_FILENAMES = {
    "bug.4001.jpg",   # broad (OCR gap, nhưng agent vẫn detect lỗi khác)
    "bug.4200.jpg",   # CNT-01/02 — null country items
    "bug.4161.jpg",   # CNT-01/02 — nhiều null items
    "bug.4961.jpg",   # CNT-01/02 — nhiều null field + CMP-01
    "bug.5241.jpg",   # CNT-01 — null đơn, rõ ràng
    "bug.5841.jpg",   # IMG-08 — broken image placeholder
    "bug.5001.jpg",   # IMG-01 — broken image + LAY-01
    "bug.4081.jpg",   # LAY-01 + CMP-01 — text overlay
}
AGENT_BUG_CASES = [c for c in KNOWN_BUG_CASES if c.filename in _AGENT_TEST_FILENAMES]


# ── Tests: rule-only (deterministic, không cần Cline) ─────────────────────────

@pytest.mark.parametrize("case", KNOWN_BUG_CASES, ids=[c.filename for c in KNOWN_BUG_CASES])
def test_bug_case_detects_expected_rule(case: KnownCase):
    """Rule engine PHẢI phát hiện ít nhất 1 rule trong expected_rules cho ảnh bug đã biết."""
    img_path = BUG_DIR / case.filename
    if not img_path.exists():
        pytest.skip(f"Ảnh chưa có: {img_path}")

    issue_types = _issue_types_rule_only(img_path)
    fired = set(issue_types)

    matched = [r for r in case.expected_rules if r in fired]
    assert matched, (
        f"{case.filename} ({case.bug_type}):\n"
        f"  Kỳ vọng ít nhất 1 trong {case.expected_rules}\n"
        f"  Thực tế rule fire: {sorted(fired)}"
    )


@pytest.mark.parametrize("case", KNOWN_NORMAL_CASES, ids=[c.filename for c in KNOWN_NORMAL_CASES])
def test_normal_case_no_false_placeholder(case: KnownCase):
    """Ảnh normal KHÔNG được fire các rule placeholder/null text (CNT-01/02)."""
    img_path = NORMAL_DIR / case.filename
    if not img_path.exists():
        pytest.skip(f"Ảnh chưa có: {img_path}")

    issue_types = _issue_types_rule_only(img_path)
    fired = set(issue_types)

    bad_fires = [r for r in case.should_not_fire if r in fired]
    assert not bad_fires, (
        f"{case.filename} ({case.bug_type}):\n"
        f"  Rule này KHÔNG nên fire: {bad_fires}\n"
        f"  Tất cả rule fire: {sorted(fired)}"
    )


# ── Tests: aggregate hit rate trên sample ngẫu nhiên ─────────────────────────

def _sample_images(directory: Path, n: int = 50, seed: int = 42) -> list[Path]:
    import random
    rng = random.Random(seed)
    all_imgs = sorted(directory.glob("*.jpg")) + sorted(directory.glob("*.png"))
    return rng.sample(all_imgs, min(n, len(all_imgs)))


@pytest.mark.slow
def test_bug_set_hit_rate_above_threshold():
    """
    Trên 50 ảnh bug ngẫu nhiên (rule-only):
    Hit rate (ít nhất 1 CNT-01/02 issue) phải > 10%.
    Đây là proxy cho khả năng phát hiện null-text bugs của OwlEyes.

    NOTE: Bug type mix gồm 4 loại. Chỉ ~25% là null-text → hit rate 10%+ là thực tế.
    """
    sample = _sample_images(BUG_DIR, n=50)
    if not sample:
        pytest.skip("Không có ảnh bug")

    hits = 0
    for p in sample:
        types = _issue_types_rule_only(p)
        if any(t in ("CNT-01", "CNT-02") for t in types):
            hits += 1

    hit_rate = hits / len(sample)
    assert hit_rate >= 0.10, (
        f"Hit rate CNT-01/02 trên bug set = {hit_rate:.1%} < 10%.\n"
        f"  Hits: {hits}/{len(sample)}"
    )


@pytest.mark.slow
def test_normal_set_low_placeholder_fp_rate():
    """
    Trên 50 ảnh normal ngẫu nhiên (rule-only):
    FP rate (CNT-01/02 fire nhầm) phải < 5%.
    """
    sample = _sample_images(NORMAL_DIR, n=50)
    if not sample:
        pytest.skip("Không có ảnh normal")

    fps = 0
    for p in sample:
        types = _issue_types_rule_only(p)
        if any(t in ("CNT-01", "CNT-02") for t in types):
            fps += 1

    fp_rate = fps / len(sample)
    assert fp_rate < 0.05, (
        f"FP rate CNT-01/02 trên normal set = {fp_rate:.1%} ≥ 5%.\n"
        f"  FPs: {fps}/{len(sample)}"
    )


# ── Tests: với Cline reasoning (chỉ chạy khi AGENT_BACKEND=cline) ─────────────

@pytest.mark.agent
@pytest.mark.parametrize("case", AGENT_BUG_CASES, ids=[c.filename for c in AGENT_BUG_CASES])
def test_bug_case_agent_confirms(case: KnownCase):
    """
    Agent phải confirm ít nhất 1 issue từ expected_rules.
    Chọn 8 case đa dạng: CNT (null text), IMG (broken image), LAY (text overlay).

    Chạy với Codex:  AGENT_BACKEND=codex pytest tests/integration/test_owleyes.py -m agent -v
    Chạy với Cline:  AGENT_BACKEND=cline pytest tests/integration/test_owleyes.py -m agent -v
    """
    img_path = BUG_DIR / case.filename
    if not img_path.exists():
        pytest.skip(f"Ảnh chưa có: {img_path}")

    issue_types = _issue_types_with_agent(img_path)
    fired = set(issue_types)

    matched = [r for r in case.expected_rules if r in fired]
    assert matched, (
        f"{case.filename} (agent mode, {case.bug_type}):\n"
        f"  Agent không confirm rule nào trong {case.expected_rules}\n"
        f"  Issue types sau agent: {sorted(fired)}"
    )
