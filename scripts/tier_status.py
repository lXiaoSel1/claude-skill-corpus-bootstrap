#!/usr/bin/env python3
"""Report a field's build progress and forecast the next tier's cost.

Reads the two instances' registry.json (built_tiers) plus disk facts, prints
what is live and what the NEXT tier will cost -- the cost model comes from
references/provenance.md (the parent build's measured pass counts), scaled by
the STYLE-SAFE sample size (the papers the model passes actually read), not
the raw file count.

FACTORY FIXES 2026-10-07: tagging was forecast at one pass PER PAPER while
SKILL.md and the tagging prompt dispatch ~10 papers per agent (a 10x
overstatement); `--dest` without a path raised IndexError.

RUN
    py -3 scripts/tier_status.py <field-slug> [--dest <skills-dir>]
"""
import argparse
import json
import math
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

TIER_DESC = {
    0: ("corpus + manifest", "scripts only, minutes"),
    1: ("style layer (<field>-lit usable)", "scripts only, zero agents"),
    2: ("chapter map (taxonomy + waves + slices)",
        "1 taxonomy pass (USER APPROVES) + ~{a2} wave/correction passes"
        " + A3 gate reads"),
    3: ("records + Versions (<field>-draft usable)",
        "~{p1} PASS1 reading passes + {p2} PASS2 induction passes"),
    4: ("exemplars + verb ladder",
        "~{ex} tagging passes (~10 papers per agent)"),
}


def load_reg(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def style_safe_count(lit):
    meta = os.path.join(lit, "references", "corpus_meta.yaml")
    try:
        with open(meta, encoding="utf-8") as fh:
            m = re.search(r"^\s+style_safe:\s*(\d+)", fh.read(), re.M)
        return int(m.group(1)) if m else None
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field")
    ap.add_argument("--dest", default=os.path.dirname(SKILL))
    args = ap.parse_args()
    lit = os.path.join(args.dest, args.field + "-lit")
    draft = os.path.join(args.dest, args.field + "-draft")

    lit_reg = load_reg(os.path.join(lit, "references", "registry.json"))
    draft_reg = load_reg(os.path.join(draft, "references", "registry.json"))
    if not lit_reg:
        sys.exit("no stamped instance at %s -- run stamp.py first" % lit)

    tiers = set(int(t) for t in lit_reg.get("built_tiers", []))
    if draft_reg:
        tiers |= set(int(t) for t in draft_reg.get("built_tiers", []))

    corpus = os.path.join(lit, "references", "corpus")
    n_files = len([f for f in os.listdir(corpus) if f.endswith(".txt")]) \
        if os.path.isdir(corpus) else 0
    n = style_safe_count(lit) or n_files

    # parent cost model (provenance.md): 60-paper sample -> 8 A2 passes,
    # ~27 PASS1, one PASS2 per chapter, tagging ~10 papers per agent.
    scale = max(n, 1) / 60.0
    costs = {"a2": max(4, round(8 * scale)),
             "p1": max(4, round(27 * scale)),
             "p2": "one per chapter (taxonomy decides)",
             "ex": max(1, math.ceil(n / 10)) if n else "?"}

    print("field: %s   corpus: %d txt (%d style-safe)   built tiers: %s\n"
          % (args.field, n_files, n, sorted(tiers) or "none"))
    nxt = min(set(range(5)) - tiers, default=None)
    for t in range(5):
        mark = "DONE" if t in tiers else ("NEXT" if t == nxt else "    ")
        name, cost = TIER_DESC[t]
        print("  [%s] Tier %d  %-46s %s"
              % (mark, t, name, cost.format(**costs)))
    if nxt is None:
        print("\nall tiers built -- run both instances' check_drift for the"
              " full-green acceptance")
    else:
        print("\nnext tier's driver: see corpus-bootstrap/SKILL.md Tier %d"
              % nxt)


if __name__ == "__main__":
    main()
