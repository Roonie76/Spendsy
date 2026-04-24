"""Produce a human-readable report from the JSONL stress-test output.

Usage:
    cd backend && python -m tests.tora_eval.stress.report stress_results.jsonl
    cd backend && python -m tests.tora_eval.stress.report stress_results.jsonl --md report.md

The report covers:
  - Resolver accuracy per category (recall: right plugin picked)
  - Track-1 false positive rate (profile queries that leaked to a plugin)
  - Track-2 miss rate (plugin queries that got no match)
  - Wrong-plugin rate (track 2, matched but wrong plugin)
  - Thinking-mode gating accuracy
  - Latency distribution (p50/p95/p99/max)
  - Plugin coverage in the match outputs
  - Top-20 problematic queries (sorted by category × error type)
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    header: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("__header__"):
                header = {k: v for k, v in obj.items() if k != "__header__"}
            else:
                rows.append(obj)
    return header, rows


def _classify(row: dict[str, Any]) -> str:
    """Classify each query result into one outcome bucket.

    Buckets:
      - hit           : track 2 query with expected_plugin in matches (primary)
      - hit_supporting: track 2 query with expected plugin as supporting (still a win)
      - wrong_plugin  : track 2 query matched, but a different plugin
      - miss_track2   : track 2 query with zero matches
      - ok_track1     : track 1 query with zero matches (correct)
      - false_pos     : track 1 query that matched a plugin
      - error         : exception during run
    """
    if "error" in row:
        return "error"
    label = row["label"]
    matches = row.get("matched_plugins", [])
    matched_primary = next((m for m in matches if m.get("role") == "primary"), None)
    matched_any_ids = {m["plugin_id"] for m in matches}

    if label["track"] == 2:
        expected = label["expected_plugin"]
        if not matches:
            return "miss_track2"
        if matched_primary and matched_primary["plugin_id"] == expected:
            return "hit"
        if expected in matched_any_ids:
            return "hit_supporting"
        return "wrong_plugin"
    # Track 1
    if matches:
        return "false_pos"
    return "ok_track1"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = int(round((pct / 100.0) * (len(values) - 1)))
    return values[max(0, min(k, len(values) - 1))]


def build_report(header: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    out: list[str] = []
    total = len(rows)
    out.append("# TORA Engine Stress Test Report\n")
    out.append(f"**Corpus**: {total} queries · seed={header.get('seed')} · ")
    out.append(
        f"total run {header.get('total_elapsed_seconds')}s · "
        f"concurrency={header.get('concurrency')}\n\n"
    )
    cs = header.get("corpus_summary", {})
    out.append(
        f"**Mix**: {cs.get('by_track', {})} tracks, {cs.get('by_style', {})} styles, "
        f"{cs.get('distinct_personas', 0)} personas\n\n"
    )

    # --- Outcome classification ---
    classes = [_classify(r) for r in rows]
    class_counts = Counter(classes)
    out.append("## Outcome summary\n\n")
    out.append("| Outcome | Count | % |\n|---|---:|---:|\n")
    order = [
        ("hit", "✓ track-2 primary plugin correct"),
        ("hit_supporting", "~ track-2 expected plugin as supporting"),
        ("wrong_plugin", "✗ track-2 matched but wrong plugin"),
        ("miss_track2", "✗ track-2 got zero matches"),
        ("ok_track1", "✓ track-1 correctly skipped enrichment"),
        ("false_pos", "✗ track-1 leaked to a plugin"),
        ("error", "✗ engine raised"),
    ]
    for key, label in order:
        n = class_counts.get(key, 0)
        pct = 100.0 * n / total if total else 0.0
        out.append(f"| {label} | {n} | {pct:.1f}% |\n")
    out.append("\n")

    # Headline accuracy numbers
    track2_total = sum(1 for r in rows if r["label"]["track"] == 2)
    track1_total = total - track2_total
    track2_hit = class_counts.get("hit", 0) + class_counts.get("hit_supporting", 0)
    track2_miss = class_counts.get("miss_track2", 0)
    track2_wrong = class_counts.get("wrong_plugin", 0)
    track1_ok = class_counts.get("ok_track1", 0)

    track2_recall = (track2_hit / track2_total * 100) if track2_total else 0.0
    track1_precision = (track1_ok / track1_total * 100) if track1_total else 0.0
    out.append("## Headline metrics\n\n")
    out.append(f"- **Track-2 recall** (right plugin found): `{track2_recall:.1f}%` ")
    out.append(
        f"({track2_hit}/{track2_total} hits, {track2_miss} misses, "
        f"{track2_wrong} wrong plugin)\n"
    )
    out.append(f"- **Track-1 precision** (no false enrichment): `{track1_precision:.1f}%` ")
    out.append(
        f"({track1_ok}/{track1_total} clean, "
        f"{class_counts.get('false_pos', 0)} false positives)\n\n"
    )

    # --- Per-category breakdown ---
    out.append("## Per-category recall (track-2)\n\n")
    out.append("| Category | Queries | Hit | Hit-supporting | Wrong | Miss | Recall |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|\n")
    per_cat: dict[str, Counter[str]] = defaultdict(Counter)
    for r, cls in zip(rows, classes):
        if r["label"]["track"] != 2:
            continue
        per_cat[r["label"]["category_tag"]][cls] += 1
    for cat in sorted(per_cat.keys()):
        counts = per_cat[cat]
        qn = sum(counts.values())
        hit = counts["hit"]
        hit_sup = counts["hit_supporting"]
        wrong = counts["wrong_plugin"]
        miss = counts["miss_track2"]
        recall = 100.0 * (hit + hit_sup) / qn if qn else 0.0
        out.append(
            f"| {cat} | {qn} | {hit} | {hit_sup} | {wrong} | {miss} | "
            f"{recall:.1f}% |\n"
        )
    out.append("\n")

    # --- Per-style breakdown ---
    out.append("## Per-style accuracy\n\n")
    out.append("| Style | Queries | Track-2 recall | Track-1 precision |\n")
    out.append("|---|---:|---:|---:|\n")
    by_style: dict[str, Counter[str]] = defaultdict(Counter)
    for r, cls in zip(rows, classes):
        by_style[r["label"]["style"]][cls] += 1
    for style in sorted(by_style.keys()):
        counts = by_style[style]
        t2 = counts["hit"] + counts["hit_supporting"] + counts["wrong_plugin"] + counts["miss_track2"]
        t1 = counts["ok_track1"] + counts["false_pos"]
        recall = 100.0 * (counts["hit"] + counts["hit_supporting"]) / t2 if t2 else 0.0
        prec = 100.0 * counts["ok_track1"] / t1 if t1 else 0.0
        out.append(
            f"| {style} | {t1 + t2} | {recall:.1f}% ({t2}) | {prec:.1f}% ({t1}) |\n"
        )
    out.append("\n")

    # --- Thinking-mode gating accuracy ---
    thinking_correct = 0
    thinking_total = 0
    for r in rows:
        if "error" in r:
            continue
        expected = r["label"]["should_enable_thinking"]
        actual = r.get("thinking_enabled", False)
        thinking_total += 1
        if expected == actual:
            thinking_correct += 1
    thinking_acc = 100.0 * thinking_correct / thinking_total if thinking_total else 0.0
    out.append(
        f"## Thinking-mode gating\n\n"
        f"- Accuracy vs expected: `{thinking_acc:.1f}%` "
        f"({thinking_correct}/{thinking_total})\n\n"
    )

    # --- Latency distribution ---
    latencies = [r["elapsed_ms"] for r in rows if "elapsed_ms" in r and "error" not in r]
    if latencies:
        out.append("## Latency distribution (ms)\n\n")
        out.append(f"- mean:  {statistics.mean(latencies):.2f}\n")
        out.append(f"- p50:   {_percentile(latencies, 50):.2f}\n")
        out.append(f"- p95:   {_percentile(latencies, 95):.2f}\n")
        out.append(f"- p99:   {_percentile(latencies, 99):.2f}\n")
        out.append(f"- max:   {max(latencies):.2f}\n")
        budget_violations = [v for v in latencies if v > 800.0]
        out.append(
            f"- queries above 800ms budget: "
            f"{len(budget_violations)} ({100*len(budget_violations)/len(latencies):.2f}%)\n\n"
        )

    # --- Plugin match coverage ---
    plugin_hits: Counter[str] = Counter()
    for r in rows:
        for m in r.get("matched_plugins", []):
            plugin_hits[m["plugin_id"]] += 1
    out.append("## Plugin match volume (all queries combined)\n\n")
    out.append("| Plugin | Times matched |\n|---|---:|\n")
    for pid, n in plugin_hits.most_common():
        out.append(f"| {pid} | {n} |\n")
    # Also surface plugins that never matched (coverage gap).
    # We'd need the registry for a full list; deriving from rows:
    registered = {
        "mobility", "real_estate", "electronics", "appliances",
        "travel", "gold", "investments", "education",
        "healthcare", "wedding", "furniture", "lifestyle",
    }
    never_matched = registered - set(plugin_hits.keys())
    if never_matched:
        out.append(f"\n**⚠ Plugins never matched**: {sorted(never_matched)}\n")
    out.append("\n")

    # --- Top problematic queries ---
    out.append("## Top problematic queries (actionable)\n\n")
    # Group misses + wrong-plugin + false_pos by (category, outcome)
    problems: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r, cls in zip(rows, classes):
        if cls in ("miss_track2", "wrong_plugin", "false_pos", "error"):
            problems[(r["label"]["category_tag"], cls)].append(r)

    # Show each problem group with up to 5 sample queries.
    for (cat, cls), items in sorted(problems.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        out.append(f"### {cls} in `{cat}` (n={len(items)})\n\n")
        for r in items[:5]:
            matches_repr = (
                ", ".join(
                    f"{m['plugin_id']}({m['entity']},{m['role']})"
                    for m in r.get("matched_plugins", [])
                )
                or "—"
            )
            out.append(f"- `{r['text']}` → matched: {matches_repr}\n")
        if len(items) > 5:
            out.append(f"- _(+{len(items) - 5} more)_\n")
        out.append("\n")

    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="TORA stress-test report")
    parser.add_argument("jsonl", type=str, help="path to stress_results.jsonl")
    parser.add_argument(
        "--md",
        type=str,
        default=None,
        help="optional: write markdown report to this path",
    )
    args = parser.parse_args()

    path = Path(args.jsonl).resolve()
    header, rows = _load_jsonl(path)
    report = build_report(header, rows)
    print(report)
    if args.md:
        Path(args.md).write_text(report, encoding="utf-8")
        print(f"\n[wrote {args.md}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
