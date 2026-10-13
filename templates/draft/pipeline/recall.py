#!/usr/bin/env python3
"""Recall check of A1 heading extraction against a hand-measured ground truth.

INSTANCE VERSION.  The parent carried its 12-paper ground truth as an inline
dict (a second, unreconciled source next to groundtruth.json -- a documented
smell).  This instance reads groundtruth.json ONLY.  Build it at the Tier 2
gate: hand-list the top-level chapter heading line numbers for ~10-15 sample
papers, as {"PaperKey": [line, line, ...], ...}.

RUN
    py pipeline/recall.py
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
TOL = 2  # line-number tolerance (PDF extraction jitter)
# `--tol 0` when groundtruth.json was hand-built on THIS corpus text: with +/-2,
# a subsection heading on the next line can stand in for a missed chapter
# heading (a health-policy paper's 'M ETHODS' heading was "hit" by 'In-Depth Interviews'
# L122, 2026-10-07).
if "--tol" in sys.argv:
    TOL = int(sys.argv[sys.argv.index("--tol") + 1])

gt_path = os.path.join(BASE, "groundtruth.json")
if not os.path.exists(gt_path):
    sys.exit("no groundtruth.json -- build it at the Tier 2 gate (hand-list "
             "top-level heading line numbers for ~10-15 sample papers)")
with open(gt_path, encoding="utf-8") as fh:
    GT = json.load(fh)
with open(os.path.join(BASE, "a1_candidates.json"), encoding="utf-8") as fh:
    d = json.load(fh)

tot_gt = tot_hit = 0
for k, wanted in sorted(GT.items()):
    got = [c["line"] for c in d.get(k, {}).get("candidates", [])]
    hit = sum(1 for w in wanted
              if any(abs(g - w) <= TOL for g in got))
    tot_gt += len(wanted)
    tot_hit += hit
    missed = [w for w in wanted if not any(abs(g - w) <= TOL for g in got)]
    print("%-40s %d/%d %6.1f%%%s"
          % (k, hit, len(wanted), 100 * hit / len(wanted) if wanted else 100,
             ("   missed lines: %s" % missed) if missed else ""))
print("-" * 72)
print("%-40s %d/%d %6.1f%%"
      % ("TOTAL", tot_hit, tot_gt, 100 * tot_hit / tot_gt if tot_gt else 100))
sys.exit(0 if tot_hit == tot_gt else 1)
