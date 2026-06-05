#!/usr/bin/env python3
"""
owleyes_hitrate.py — Đo hit rate / FP rate của rule engine trên ảnh OwlEyes.

Dùng ảnh augmented từ OwlEyes dataset (bug-aug + normal-aug) để kiểm tra:
  - Hit rate (bug set): % ảnh bug mà rule engine phát hiện ít nhất 1 candidate issue
  - FP rate (normal set): % ảnh normal mà rule engine sinh ra candidate issue (false positive)
  - Per-rule breakdown: rule nào kêu nhiều nhất

KHÔNG cần Codex/Cline — chạy rule-only (run_agents=False).

OwlEyes có 4 loại bug inject:
  1. null text         → R4-Text (CNT-01/CNT-02)
  2. broken image      → A9 pattern (IMG-01/STATE-01)
  3. text overlay      → R1-Geometry (LAY-01)
  4. element clipping  → R1-Geometry (LAY-02)

--fast: bỏ qua A4 (color sampler, ~4s/ảnh) và A10 (phash) để chạy nhanh hơn.
--focus-rules: chỉ tính hit rate cho các rule liên quan OwlEyes (bỏ LAY-04/ENV noise).

Usage:
  python scripts/owleyes_hitrate.py \\
      --bug-dir /tmp/owleye_extract/bug/bug-aug \\
      --normal-dir /tmp/owleye_extract/normal/normal-aug \\
      --n 100 --fast \\
      --out data/owleyes_hitrate.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PIL import Image  # noqa: E402

# ── Issue types liên quan đến 4 loại bug OwlEyes ──────────────────────────────
# null text, broken image, text overlay, element clipping
OWLEYES_RELEVANT = {
    "CNT-01", "CNT-02",                 # null/placeholder text
    "IMG-01", "IMG-08", "STATE-01",     # broken/missing image
    "LAY-01", "LAY-06",                 # overlap (text overlay)
    "LAY-02", "TYP-03",                 # clipping / text cut-off
}

# Rule codes hay gây noise không liên quan OwlEyes
NOISY_RULES = {"LAY-04", "ENV-01", "ENV-02", "ENV-03", "IMG-12"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _infer_viewport(img: Image.Image) -> tuple[int, int, float]:
    """Suy viewport từ kích thước ảnh OwlEyes. Trả về (w, h, dpr)."""
    w, h = img.size
    dpr = 2.0 if w >= 720 else 1.0
    return w, h, dpr


def _run_one(img_path: Path, fast: bool = False) -> tuple[list[str], float]:
    """Chạy rule engine trên 1 ảnh.
    Trả (list[issue_type], thời gian giây).
    fast=True: patch tạm A4/A10 bằng no-op để tránh bottleneck.
    """
    t0 = time.monotonic()
    try:
        img = Image.open(img_path).convert("RGB")
        vw, vh, dpr = _infer_viewport(img)

        import os
        if fast:
            # Đặt env để A4 tự giảm max elements về 0 → skip toàn bộ
            os.environ["A4_MAX_ELEMENTS"] = "0"
            os.environ["A10_SKIP"] = "1"

        from ui_defect.api.pipeline import run_pipeline
        out = run_pipeline(
            img=img, platform="android",
            viewport_w=vw, viewport_h=vh, dpr=dpr,
            run_agents=False,
        )

        if fast:
            os.environ.pop("A4_MAX_ELEMENTS", None)
            os.environ.pop("A10_SKIP", None)

        # issue_type từ IssueOutput (sources[0] là rule ID gốc nếu có)
        issue_types = [iss.issue_type for iss in out.issues]
    except Exception as e:
        print(f"  [error] {img_path.name}: {e}", file=sys.stderr)
        issue_types = []
    return issue_types, time.monotonic() - t0


# ── Core benchmark ────────────────────────────────────────────────────────────

def run_benchmark(
    bug_dir: Path,
    normal_dir: Path,
    n: int,
    seed: int,
    fast: bool = False,
    focus_rules: bool = False,
) -> dict:
    rng = random.Random(seed)

    bug_imgs = sorted(bug_dir.glob("*.jpg")) + sorted(bug_dir.glob("*.png"))
    normal_imgs = sorted(normal_dir.glob("*.jpg")) + sorted(normal_dir.glob("*.png"))

    if not bug_imgs:
        sys.exit(f"[error] Không tìm thấy ảnh trong {bug_dir}")
    if not normal_imgs:
        sys.exit(f"[error] Không tìm thấy ảnh trong {normal_dir}")

    sample_bug = rng.sample(bug_imgs, min(n, len(bug_imgs)))
    sample_normal = rng.sample(normal_imgs, min(n, len(normal_imgs)))

    mode = "fast" if fast else "full"
    focus_label = " [focus-owleyes]" if focus_rules else ""
    print(f"\nBenchmark OwlEyes — rule-only, mode={mode}{focus_label} (n={n}, seed={seed})")
    print(f"  bug dir   : {bug_dir}  ({len(bug_imgs)} ảnh → sample {len(sample_bug)})")
    print(f"  normal dir: {normal_dir}  ({len(normal_imgs)} ảnh → sample {len(sample_normal)})")
    if fast:
        print("  [fast] Bỏ qua A4 (color) + A10 (phash) để giảm thời gian")
    if focus_rules:
        print(f"  [focus] Chỉ tính hit rate cho {len(OWLEYES_RELEVANT)} rule liên quan OwlEyes")

    def _process_set(paths: list[Path], label: str) -> dict:
        hits = 0           # ít nhất 1 issue (bất kỳ rule nào)
        hits_focused = 0   # ít nhất 1 issue thuộc OWLEYES_RELEVANT
        total_types: dict[str, int] = defaultdict(int)
        times = []
        results = []
        print(f"\n── {label} ({len(paths)} ảnh) ──")
        for i, p in enumerate(paths, 1):
            issue_types, dt = _run_one(p, fast=fast)
            # Lọc noisy nếu focus mode
            display_types = issue_types
            if focus_rules:
                display_types = [t for t in issue_types if t not in NOISY_RULES]

            has_issue = len(display_types) > 0
            focused = any(t in OWLEYES_RELEVANT for t in display_types)
            if has_issue:
                hits += 1
            if focused:
                hits_focused += 1
            for t in display_types:
                total_types[t] += 1
            times.append(dt)
            results.append({"file": p.name, "issue_types": display_types, "has_issue": has_issue, "focused": focused})
            if i % 20 == 0 or i == len(paths):
                pct_all = hits / i * 100
                pct_focus = hits_focused / i * 100
                print(
                    f"  [{i:>3}/{len(paths)}] hit_all={hits}({pct_all:.0f}%)  "
                    f"hit_owleyes={hits_focused}({pct_focus:.0f}%)  "
                    f"avg {sum(times)/len(times)*1000:.0f}ms/img"
                )
        n_total = len(paths)
        return {
            "n": n_total,
            "hits_any": hits,
            "hits_owleyes": hits_focused,
            "hit_rate_any": hits / n_total if n_total else 0,
            "hit_rate_owleyes": hits_focused / n_total if n_total else 0,
            "per_type_count": dict(sorted(total_types.items(), key=lambda x: -x[1])),
            "avg_time_ms": sum(times) / len(times) * 1000 if times else 0,
            "results": results,
        }

    bug_stats = _process_set(sample_bug, "BUG set")
    normal_stats = _process_set(sample_normal, "NORMAL set")

    return {
        "config": {
            "n": n, "seed": seed,
            "bug_dir": str(bug_dir), "normal_dir": str(normal_dir),
            "fast": fast, "focus_rules": focus_rules,
        },
        "bug": bug_stats,
        "normal": normal_stats,
    }


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(data: dict) -> None:
    b = data["bug"]
    nm = data["normal"]
    print("\n" + "=" * 65)
    print("OwlEyes Benchmark — Kết quả")
    print("=" * 65)
    print(f"\n{'Set':<10} {'N':>4} {'HitAny':>8} {'HitOwlEyes':>11}  {'Avg(ms)':>8}")
    print("-" * 55)
    print(
        f"{'bug':<10} {b['n']:>4}  {b['hit_rate_any']:>6.1%}  {b['hit_rate_owleyes']:>10.1%}"
        f"  {b['avg_time_ms']:>8.0f}"
    )
    print(
        f"{'normal':<10} {nm['n']:>4}  {nm['hit_rate_any']:>6.1%}  {nm['hit_rate_owleyes']:>10.1%}"
        f"  {nm['avg_time_ms']:>8.0f}"
    )

    def _bar_table(title: str, counts: dict) -> None:
        if not counts:
            print(f"  (không có)")
            return
        max_cnt = max(counts.values(), default=1)
        for tp, cnt in list(counts.items())[:15]:
            marker = " ★" if tp in OWLEYES_RELEVANT else ""
            bar = "█" * int(cnt / max_cnt * 28)
            print(f"  {tp:<20} {cnt:>4}  {bar}{marker}")

    print("\n── Per-issue-type (bug set) ── [★ = liên quan OwlEyes]")
    _bar_table("bug", b["per_type_count"])

    print("\n── Per-issue-type (normal set / FP breakdown) ──")
    _bar_table("normal", nm["per_type_count"])

    print(f"\n{'═'*50}")
    print(f"Tóm tắt:")
    gap_any    = b["hit_rate_any"]    - nm["hit_rate_any"]
    gap_focus  = b["hit_rate_owleyes"] - nm["hit_rate_owleyes"]

    def _q(gap: float) -> str:
        return "Tốt" if gap > 0.3 else ("Chấp nhận" if gap > 0.1 else "Cần cải thiện")

    print(f"  Hit rate  bug (any issue)     = {b['hit_rate_any']:.1%}")
    print(f"  FP rate   normal (any issue)  = {nm['hit_rate_any']:.1%}")
    print(f"  Gap (any)                     = {gap_any:+.1%}  → {_q(gap_any)}")
    print()
    print(f"  Hit rate  bug (OwlEyes rules) = {b['hit_rate_owleyes']:.1%}")
    print(f"  FP rate   normal (OwlEyes)    = {nm['hit_rate_owleyes']:.1%}")
    print(f"  Gap (focused)                 = {gap_focus:+.1%}  → {_q(gap_focus)}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đo hit rate / FP rate trên OwlEyes dataset.")
    parser.add_argument("--bug-dir", default="/tmp/owleye_extract/bug/bug-aug", help="Thư mục ảnh bug.")
    parser.add_argument("--normal-dir", default="/tmp/owleye_extract/normal/normal-aug", help="Thư mục ảnh normal.")
    parser.add_argument("--n", type=int, default=100, help="Số ảnh sample mỗi set (default 100).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--out", default="data/owleyes_hitrate.json", help="File JSON kết quả.")
    parser.add_argument("--fast", action="store_true", help="Bỏ qua A4+A10 để chạy nhanh hơn (~5x).")
    parser.add_argument("--focus-rules", action="store_true", help="Chỉ tính hit rate cho rule liên quan OwlEyes.")
    args = parser.parse_args(argv)

    data = run_benchmark(
        bug_dir=Path(args.bug_dir),
        normal_dir=Path(args.normal_dir),
        n=args.n,
        seed=args.seed,
        fast=args.fast,
        focus_rules=args.focus_rules,
    )

    print_report(data)

    out_path = (_REPO_ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Bỏ "results" detail khi ghi để file nhỏ hơn; giữ summary
    summary = {k: v for k, v in data.items()}
    for key in ("bug", "normal"):
        summary[key] = {k: v for k, v in data[key].items() if k != "results"}
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n→ Kết quả chi tiết ghi tại {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
