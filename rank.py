#!/usr/bin/env python3
"""
rank.py v4 — Main entry point.
Usage: python rank.py
Produces: submission.csv (100 ranked candidates, validator-clean)
"""

import json
import csv
import sys
from collections import Counter
from scoring import score_candidate
from reasoning import generate_reasoning
from config import HONEYPOT_TITLES

INPUT_FILE  = "candidates.jsonl"
OUTPUT_FILE = "submission.csv"
TOP_N = 100


def load_candidates(path: str) -> list:
    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                candidates.append(json.loads(line))
    return candidates


def normalise(s: float, min_s: float, max_s: float) -> float:
    """Map raw score to 0.200-0.992 range."""
    spread = max_s - min_s if max_s != min_s else 1.0
    return round(0.200 + ((s - min_s) / spread) * (0.992 - 0.200), 6)


def main():
    print(f"Loading {INPUT_FILE}...")
    candidates = load_candidates(INPUT_FILE)
    print(f"Loaded {len(candidates):,} candidates.")

    print("Scoring...")
    results = []
    disqualified = 0
    honeypot_blocked = 0

    for i, c in enumerate(candidates):
        if i % 10_000 == 0 and i > 0:
            print(f"  {i:,} scored...")
        raw_score, breakdown = score_candidate(c)
        if raw_score <= 0:
            if breakdown.get("gate", "").startswith("honeypot"):
                honeypot_blocked += 1
            disqualified += 1
        else:
            results.append({
                "candidate_id": c["candidate_id"],
                "raw_score":    raw_score,
                "breakdown":    breakdown,
                "candidate":    c,
            })

    print(f"  Disqualified: {disqualified:,} (including {honeypot_blocked:,} honeypots)")
    print(f"  Eligible: {len(results):,}")

    results.sort(key=lambda x: (-x["raw_score"], x["candidate_id"]))
    top100 = results[:TOP_N]

    max_s = top100[0]["raw_score"]
    min_s = top100[-1]["raw_score"]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, row in enumerate(top100, start=1):
            ns = normalise(row["raw_score"], min_s, max_s)
            reasoning = generate_reasoning(row["candidate"], row["breakdown"])
            writer.writerow([row["candidate_id"], rank, ns, reasoning])

    print(f"\n✅ Wrote {OUTPUT_FILE}")
    print(f"Raw score range (top 100): {min_s:.2f} – {max_s:.2f}")

    # ── Audit ──────────────────────────────────────────────────────────────────
    print(f"\n{'Rk':<4} {'ID':<15} {'Sc':<8} {'Title':<40} {'Yrs':<5} {'RR':<5} {'Fam':<4} {'Not'}")
    print("─" * 95)
    for rank, row in enumerate(top100[:20], start=1):
        p  = row["candidate"]["profile"]
        s  = row["candidate"]["redrob_signals"]
        bd = row["breakdown"]
        ns = normalise(row["raw_score"], min_s, max_s)
        notice = s.get("notice_period_days", "?")
        print(
            f"{rank:<4} {row['candidate_id']:<15} {ns:<8} "
            f"{p['current_title'][:39]:<40} "
            f"{p['years_of_experience']:<5.1f} "
            f"{s.get('recruiter_response_rate',0):<5.2f} "
            f"{bd.get('career_families',0):<4} "
            f"{notice}d"
        )

    # Honeypot check
    hp = [r for r in top100 if any(ht in r["candidate"]["profile"]["current_title"].lower() for ht in HONEYPOT_TITLES)]
    print(f"\n{'✅' if not hp else '⚠️ '} Honeypot check: {len(hp)} in top 100 (limit: 10)")

    # Title distribution
    print("\nTitle distribution (top 100):")
    for t, n in Counter(r["candidate"]["profile"]["current_title"] for r in top100).most_common():
        print(f"  {n:>3}×  {t}")

    # Score monotonicity
    with open(OUTPUT_FILE) as f:
        rows = list(csv.DictReader(f))
    viols = sum(1 for i in range(len(rows)-1) if float(rows[i]["score"]) < float(rows[i+1]["score"]))
    print(f"\n{'✅' if not viols else '⚠️ '} Score monotonicity: {viols} violations")

    # Reasoning sample
    print("\nSample reasoning (ranks 1, 5, 10, 50, 100):")
    for idx in [0, 4, 9, 49, 99]:
        if idx < len(rows):
            print(f"  [{rows[idx]['rank']}] {rows[idx]['reasoning'][:120]}")


if __name__ == "__main__":
    main()
