#!/usr/bin/env python3
"""Recompute paragraph-length statistics over ALL paragraph records.

INSTANCE VERSION.  The parent's records mixed two formats (a Chinese-note
round and a tagged table round); an instance built under PASS1_SPEC has ONE:
a plain `N sentences` line per paragraph.  This script scans every
references/records/*.md, aggregates per-paper sentence-count sequences, and
prints the distribution + the uniformity-gate calibration (identical
consecutive pairs and triples, windows never spanning a paper boundary).

The printed numbers ARE the instance's uniformity gate: copy them into the
draft instance's SKILL.md and registry at Tier 3 acceptance.

RUN
    py -3 pipeline/recount.py
"""
import glob
import os
import re
import statistics as st
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.normpath(os.path.join(BASE, "..", "references", "records"))

PAT = re.compile(r"^\s*(\d+)\s+sentences?\s*$", re.I)


def counts(path):
    out, cur, key = [], [], None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            m = re.match(r"^###\s+(\S+)", ln)
            if m:
                if key and cur:
                    out.append((key, cur))
                key, cur = m.group(1), []
                continue
            m = PAT.match(ln)
            if m:
                cur.append(int(m.group(1)))
    if key and cur:
        out.append((key, cur))
    return out


papers = []
for f in sorted(glob.glob(os.path.join(REC, "*.md"))):
    papers += counts(f)
if not papers:
    sys.exit("no `N sentences` paragraph records under references/records/ "
             "-- has Tier 3 PASS1 run?")

allc = [c for _, v in papers for c in v]


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


print("paper blocks        : %d" % len(papers))
print("paragraphs counted  : %d" % len(allc))
print("mean %.2f · P25 %.0f · median %.0f · P75 %.0f · P90 %.0f · P95 %.0f"
      " · range %d-%d"
      % (st.mean(allc), pct(allc, 25), st.median(allc), pct(allc, 75),
         pct(allc, 90), pct(allc, 95), min(allc), max(allc)))

pair = pairwin = trip = tripwin = 0
for _, v in papers:
    for i in range(len(v) - 1):
        pairwin += 1
        if v[i] == v[i + 1]:
            pair += 1
    for i in range(len(v) - 2):
        tripwin += 1
        if v[i] == v[i + 1] == v[i + 2]:
            trip += 1
if pairwin:
    print("identical consecutive PAIRS   : %d/%d = %.1f%%"
          % (pair, pairwin, 100 * pair / pairwin))
if tripwin:
    print("identical consecutive TRIPLES : %d/%d = %.1f%%"
          % (trip, tripwin, 100 * trip / tripwin))
