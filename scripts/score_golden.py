#!/usr/bin/env python3
"""
score_golden.py — Harness chấm điểm Golden Set (precision/recall/F1) cho rule engine.

Đọc dữ liệu do Agent A sinh ra ở `data/golden/schema/{cases,labels}/`:
  - cases/<id>.json   = 1 CanonicalDoc đã mutate (INPUT cho rule engine)
  - labels/<id>.json  = ground truth (expected[] + kind positive|negative)

Mặc định **rule-only** (deterministic, backend-agnostic):
  doc = CanonicalDoc.model_validate(case); out = run_rule_engine(doc) → out.candidate_issues

Matching (xem docs/F4.0-golden-set.md §5):
  1 expected = TP nếu tồn tại candidate cùng `rule` AND cùng `element`
  (element=null khớp issue cấp screen) AND `severity` nằm trong `severity_range`.
  - expected không match → FN.
  - candidate không khớp expected nào (kể cả mọi candidate ở case negative) → FP.

Tùy chọn `--with-agent`: thay rule-only bằng full reasoning QUA ABSTRACTION
  (`run_review(doc)` → backend theo env AGENT_BACKEND: codex máy này / cline prod).
  TUYỆT ĐỐI KHÔNG import codex_client trực tiếp. Backend lỗi → cảnh báo, vẫn xuất rule-only.

CLI:
  python scripts/score_golden.py [--golden data/golden/schema] [--with-agent] [--rule R1-CMP01]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Cho phép chạy trực tiếp `python scripts/score_golden.py` (thêm src/ vào path).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ui_defect.rules import run_rule_engine  # noqa: E402
from ui_defect.schema.models import CandidateIssue, CanonicalDoc  # noqa: E402

# Thứ tự severity: critical > high > medium > low > trivial.
_SEVERITY_ORDER = {"trivial": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


# ── Cấu trúc kết quả ──────────────────────────────────────────────────────────
@dataclass
class MatchRecord:
    """1 dòng FP/FN để debug (case_id, rule, element)."""

    case_id: str
    rule: str
    element: str | None


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 1.0

    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 1.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return (2 * p * r / (p + r)) if (p + r) else 0.0


@dataclass
class ScoreResult:
    overall: Counts = field(default_factory=Counts)
    per_rule: dict[str, Counts] = field(default_factory=dict)
    false_positives: list[MatchRecord] = field(default_factory=list)
    false_negatives: list[MatchRecord] = field(default_factory=list)
    n_cases: int = 0
    backend_warnings: list[str] = field(default_factory=list)

    def bucket(self, rule: str) -> Counts:
        return self.per_rule.setdefault(rule, Counts())


# ── Severity helper ───────────────────────────────────────────────────────────
def _severity_in_range(severity: str, rng_min: str, rng_max: str) -> bool:
    sv = _SEVERITY_ORDER.get(severity)
    lo = _SEVERITY_ORDER.get(rng_min)
    hi = _SEVERITY_ORDER.get(rng_max)
    if sv is None or lo is None or hi is None:
        return False
    if lo > hi:  # range ghi ngược → chuẩn hoá
        lo, hi = hi, lo
    return lo <= sv <= hi


def _expected_matches_candidate(exp: dict, cand: CandidateIssue) -> bool:
    """1 expected khớp 1 candidate khi cùng rule + cùng element + severity trong range."""
    if exp.get("rule") != cand.rule:
        return False
    # element=null khớp issue cấp screen (cand.element is None).
    if (exp.get("element") or None) != (cand.element or None):
        return False
    rng = exp.get("severity_range") or {}
    return _severity_in_range(cand.severity, rng.get("min", "trivial"), rng.get("max", "critical"))


# ── Load golden pairs ─────────────────────────────────────────────────────────
@dataclass
class GoldenCase:
    case_id: str
    case_json: dict
    label: dict


def load_golden(golden_dir: Path) -> list[GoldenCase]:
    cases_dir = golden_dir / "cases"
    labels_dir = golden_dir / "labels"
    if not cases_dir.is_dir() or not labels_dir.is_dir():
        return []
    out: list[GoldenCase] = []
    for case_path in sorted(cases_dir.glob("*.json")):
        cid = case_path.stem
        label_path = labels_dir / f"{cid}.json"
        if not label_path.is_file():
            print(f"[warn] thiếu label cho case {cid}, bỏ qua", file=sys.stderr)
            continue
        case_json = json.loads(case_path.read_text(encoding="utf-8"))
        label = json.loads(label_path.read_text(encoding="utf-8"))
        out.append(GoldenCase(case_id=cid, case_json=case_json, label=label))
    return out


# ── Lấy candidate issues (rule-only hoặc qua agent) ───────────────────────────
def _candidates_rule_only(case_json: dict) -> list[CandidateIssue]:
    doc = CanonicalDoc.model_validate(case_json)
    out = run_rule_engine(doc)
    return list(out.candidate_issues)


def _candidates_with_agent(case_json: dict, warnings: list[str]) -> list[CandidateIssue]:
    """
    Đường full-reasoning QUA ABSTRACTION run_review (backend theo AGENT_BACKEND).
    KHÔNG import codex_client. Map AgentFinding → CandidateIssue để matching đồng nhất.
    Lỗi backend (mỗi result.error) → cảnh báo + fallback rule-only cho case đó.
    """
    from ui_defect.agents.runner import run_review  # qua abstraction, không phải codex_client

    doc = CanonicalDoc.model_validate(case_json)
    # Bơm sẵn candidate rule-only để agent có cái xác nhận/bác bỏ (như pipeline thật).
    seeded = run_rule_engine(doc)
    results = run_review(seeded)

    issues: list[CandidateIssue] = []
    any_error = False
    for res in results:
        if res.error:
            any_error = True
            warnings.append(res.error)
            continue
        for f in res.findings:
            if f.verdict == "rejected":
                continue
            # rule = original_candidate_rule nếu confirm candidate, else issue_type (new_finding).
            rule = f.original_candidate_rule or f.issue_type
            sev = f.severity if f.severity in _SEVERITY_ORDER else "medium"
            issues.append(
                CandidateIssue(
                    rule=rule,
                    element=f.element_id,
                    severity=sev,
                    severity_range={"min": sev, "max": sev},
                    confidence=f.confidence,
                    detail=f.reasoning[:200],
                )
            )
    if any_error:
        # Backend chết → vẫn cho ra phần rule-only của case này (degrade graceful).
        return list(seeded.candidate_issues)
    return issues


# ── Scoring core ──────────────────────────────────────────────────────────────
def score(
    golden: list[GoldenCase],
    *,
    with_agent: bool = False,
    rule_filter: str | None = None,
) -> ScoreResult:
    result = ScoreResult(n_cases=len(golden))

    for gc in golden:
        expected: list[dict] = list(gc.label.get("expected") or [])
        if rule_filter:
            expected = [e for e in expected if e.get("rule") == rule_filter]

        if with_agent:
            candidates = _candidates_with_agent(gc.case_json, result.backend_warnings)
        else:
            candidates = _candidates_rule_only(gc.case_json)

        if rule_filter:
            candidates = [c for c in candidates if c.rule == rule_filter]

        matched_cand_idx: set[int] = set()

        # TP / FN: với mỗi expected, tìm 1 candidate chưa dùng khớp được.
        for exp in expected:
            hit_idx = None
            for i, cand in enumerate(candidates):
                if i in matched_cand_idx:
                    continue
                if _expected_matches_candidate(exp, cand):
                    hit_idx = i
                    break
            rule = exp.get("rule", "?")
            bucket = result.bucket(rule)
            if hit_idx is not None:
                matched_cand_idx.add(hit_idx)
                bucket.tp += 1
                result.overall.tp += 1
            else:
                bucket.fn += 1
                result.overall.fn += 1
                result.false_negatives.append(
                    MatchRecord(case_id=gc.case_id, rule=rule, element=exp.get("element"))
                )

        # FP: candidate nào không được expected nào dùng tới.
        for i, cand in enumerate(candidates):
            if i in matched_cand_idx:
                continue
            bucket = result.bucket(cand.rule)
            bucket.fp += 1
            result.overall.fp += 1
            result.false_positives.append(
                MatchRecord(case_id=gc.case_id, rule=cand.rule, element=cand.element)
            )

    return result


# ── Render ────────────────────────────────────────────────────────────────────
def _fmt_row(name: str, c: Counts) -> str:
    return (
        f"| {name:<14} | {c.tp:>3} | {c.fp:>3} | {c.fn:>3} "
        f"| {c.precision():.3f} | {c.recall():.3f} | {c.f1():.3f} |"
    )


def render_report(result: ScoreResult, *, mode: str) -> str:
    lines: list[str] = []
    lines.append("# Golden Set — Report\n")
    lines.append(f"- Mode: **{mode}**")
    lines.append(f"- Số case: **{result.n_cases}**")
    o = result.overall
    lines.append(
        f"- Tổng (micro): precision=**{o.precision():.3f}** "
        f"recall=**{o.recall():.3f}** F1=**{o.f1():.3f}** "
        f"(TP={o.tp} FP={o.fp} FN={o.fn})\n"
    )
    if result.backend_warnings:
        lines.append("## Cảnh báo backend (agent)\n")
        for w in result.backend_warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Per-rule\n")
    lines.append("| rule | TP | FP | FN | precision | recall | F1 |")
    lines.append("|------|----|----|----|-----------|--------|----|")
    for rule in sorted(result.per_rule):
        lines.append(_fmt_row(rule, result.per_rule[rule]))
    lines.append(_fmt_row("**TỔNG**", o))
    lines.append("")

    lines.append("## False Negatives (rule kỳ vọng KHÔNG kêu)\n")
    if result.false_negatives:
        lines.append("| case_id | rule | element |")
        lines.append("|---------|------|---------|")
        for r in result.false_negatives:
            lines.append(f"| {r.case_id} | {r.rule} | {r.element} |")
    else:
        lines.append("_(không có)_")
    lines.append("")

    lines.append("## False Positives (candidate thừa, không expected)\n")
    if result.false_positives:
        lines.append("| case_id | rule | element |")
        lines.append("|---------|------|---------|")
        for r in result.false_positives:
            lines.append(f"| {r.case_id} | {r.rule} | {r.element} |")
    else:
        lines.append("_(không có)_")
    lines.append("")
    return "\n".join(lines)


def print_console(result: ScoreResult, *, mode: str) -> None:
    o = result.overall
    print(f"\n=== Golden Set scoring (mode={mode}, cases={result.n_cases}) ===")
    print(f"{'rule':<16} {'TP':>3} {'FP':>3} {'FN':>3}  {'P':>6} {'R':>6} {'F1':>6}")
    print("-" * 52)
    for rule in sorted(result.per_rule):
        c = result.per_rule[rule]
        print(
            f"{rule:<16} {c.tp:>3} {c.fp:>3} {c.fn:>3}  "
            f"{c.precision():.3f} {c.recall():.3f} {c.f1():.3f}"
        )
    print("-" * 52)
    print(
        f"{'TỔNG (micro)':<16} {o.tp:>3} {o.fp:>3} {o.fn:>3}  "
        f"{o.precision():.3f} {o.recall():.3f} {o.f1():.3f}"
    )
    if result.backend_warnings:
        print(f"\n[warn] {len(result.backend_warnings)} lỗi backend agent (xem report.md)")
    if result.false_negatives:
        print(f"\n[FN] {len(result.false_negatives)} expected không kêu:")
        for r in result.false_negatives:
            print(f"   - {r.case_id}: {r.rule} (element={r.element})")
    if result.false_positives:
        print(f"\n[FP] {len(result.false_positives)} candidate thừa:")
        for r in result.false_positives:
            print(f"   - {r.case_id}: {r.rule} (element={r.element})")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chấm điểm Golden Set (precision/recall/F1).")
    parser.add_argument(
        "--golden",
        default="data/golden/schema",
        help="Thư mục golden (chứa cases/ + labels/). Mặc định data/golden/schema.",
    )
    parser.add_argument(
        "--with-agent",
        action="store_true",
        help="Dùng full reasoning qua AGENT_BACKEND (run_review) thay vì rule-only.",
    )
    parser.add_argument("--rule", default=None, help="Chỉ chấm 1 rule ID (vd R1-CMP01).")
    parser.add_argument(
        "--report",
        default="data/golden/report.md",
        help="Đường dẫn ghi report markdown.",
    )
    args = parser.parse_args(argv)

    golden_dir = (_REPO_ROOT / args.golden) if not Path(args.golden).is_absolute() else Path(args.golden)
    golden = load_golden(golden_dir)
    mode = "agent" if args.with_agent else "rule-only"

    if not golden:
        print(
            f"[skip] Không tìm thấy golden case ở {golden_dir} "
            f"(cases/ + labels/). Agent A có thể chưa sinh dữ liệu.",
            file=sys.stderr,
        )
        return 0

    result = score(golden, with_agent=args.with_agent, rule_filter=args.rule)
    print_console(result, mode=mode)

    report_path = (_REPO_ROOT / args.report) if not Path(args.report).is_absolute() else Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result, mode=mode), encoding="utf-8")
    print(f"\n→ Report ghi tại {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
