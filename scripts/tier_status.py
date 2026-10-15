#!/usr/bin/env python3
"""Report a field's build progress and forecast the next tier's cost.

Reads the two instances' registry.json (built_tiers) plus disk facts, prints
what is live and what the NEXT tier will cost -- the cost model comes from
references/provenance.md (the parent build's measured pass counts), scaled by
the STYLE-SAFE sample size (the papers the model passes actually read), not
the raw file count.

RUN
    py -3 scripts/tier_status.py <field-slug> [--dest <skills-dir>]
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _factory as F  # noqa: E402  (paths, cost models, launcher)

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


# the measured token and hour model (see _factory.TOKEN_MODEL for its source)
REF_PAPERS = F.TOKEN_MODEL["papers"]
TOKENS_M = F.TOKEN_MODEL["tokens_m"]
HOURS = F.TOKEN_MODEL["hours"]

def load_reg(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def canon_status(field, dest, draft):
    """The writing guides in the draft's canon_dir and the drafting pass's cost."""
    import canon_ingest
    fld = F.Field(field, dest)
    try:
        cp = fld.cfgparse()
        d = cp.as_str(cp.parse(os.path.join(draft, "references", "field-config.yaml"))
                      .get("canon_dir")) or ""
    except Exception:
        d = ""
    txt = [f for f in os.listdir(d) if f.endswith(".txt")] if d and os.path.isdir(d) else []
    if not txt:
        return ("writing canon: no guides yet -- collect the field's writing guides, then"
                " canon_ingest.py <field> --src <folder>")
    words = 0
    for f in txt:
        with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
            words += len(fh.read().split())
    done = os.path.isfile(os.path.join(draft, "references", "structure-canon.md"))
    return ("writing canon: %d guides, %s words; structure-canon.md %s; drafting it: %s"
            % (len(txt), format(words, ","), "drafted" if done else "not drafted",
               canon_ingest.canon_estimate(words)))


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
    ap.add_argument("--dest", default=F.DEFAULT_DEST)
    args = ap.parse_args()
    args.field, args.dest = F.norm_field(args.field), F.user_path(args.dest)
    lit = os.path.join(args.dest, args.field + "-lit")
    draft = os.path.join(args.dest, args.field + "-draft")

    lit_reg = load_reg(os.path.join(lit, "references", "registry.json"))
    draft_reg = load_reg(os.path.join(draft, "references", "registry.json"))
    if not lit_reg:
        sys.exit("no stamped instance at %s -- run stamp.py first" % lit)

    lit_tiers = set(int(t) for t in lit_reg.get("built_tiers", []))
    draft_tiers = set(int(t) for t in draft_reg.get("built_tiers", [])) \
        if draft_reg else set()
    tiers = lit_tiers | draft_tiers

    corpus = os.path.join(lit, "references", "corpus")
    n_files = len([f for f in os.listdir(corpus) if f.endswith(".txt")]) \
        if os.path.isdir(corpus) else 0
    n = style_safe_count(lit) or n_files

    # parent cost model (provenance.md): 60-paper sample -> 8 A2 passes,
    # ~27 PASS1, one PASS2 per chapter, tagging ~10 papers per agent.
    pm = F.PASS_MODEL
    scale = max(n, 1) / float(pm["papers"])
    costs = {"a2": max(pm["a2_min"], round(pm["a2"] * scale)),
             "p1": max(pm["pass1_min"], round(pm["pass1"] * scale)),
             "p2": "one per chapter (taxonomy decides)",
             "ex": max(1, math.ceil(n / float(pm["tag_per_agent"]))) if n else "?"}

    print("field: %s   corpus: %d txt (%d style-safe)   built tiers: %s\n"
          % (args.field, n_files, n, sorted(tiers) or "none"))
    nxt = min(set(range(5)) - tiers, default=None)
    k = max(n, 1) / float(REF_PAPERS)
    for t in range(5):
        mark = "DONE" if t in tiers else ("NEXT" if t == nxt else "    ")
        name, cost = TIER_DESC[t]
        print("  [%s] Tier %d  %-46s %s"
              % (mark, t, name, cost.format(**costs)))
        if t in TOKENS_M and t not in tiers:
            print("  %s          ≈ %.0f million tokens, ≈ %.1f h"
                  % (" " * 4, TOKENS_M[t] * k, HOURS[t] * k))
        if t == 4 and t not in tiers:
            print("  %s          %s" % (" " * 4, canon_status(args.field, args.dest, draft)))
    left = [t for t in TOKENS_M if t not in tiers]
    if left:
        print("\ntoken estimate for Tier %s at %d style-safe papers: ≈ %.0f million"
              " tokens processed (≈ 96%% prompt-cache reads), ≈ %.1f h -- scaled"
              " from a measured %d-paper health-policy build; ask the user first."
              % ("-".join(str(t) for t in (left[0], left[-1])) if len(left) > 1
                 else left[0], n, sum(TOKENS_M[t] for t in left) * k,
                 sum(HOURS[t] for t in left) * k, REF_PAPERS))
    if nxt is None:
        print("\nall tiers built -- run both instances' check_drift for the"
              " full-green acceptance")
    else:
        print("\nnext tier's driver: see corpus-bootstrap/SKILL.md Tier %d"
              % nxt)

    polish = os.path.normpath(os.path.join(args.dest, args.field + "-polish"))
    if not os.path.isdir(polish):
        print("\npolish: not stamped (%s scripts/stamp.py %s --add polish)"
              % (F.PY, args.field))
        return
    # which polish steps are ready also depends on TeX, the .bbl and the PDFs:
    # the polish instance's own doctor.py is the one place that checks them
    print("\npolish: %s\n  which steps are ready: %s %s"
          % (polish, F.PY, os.path.join(polish, "scripts", "doctor.py")))


if __name__ == "__main__":
    main()
