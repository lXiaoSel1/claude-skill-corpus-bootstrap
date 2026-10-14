#!/usr/bin/env python3
"""Tier 1, step 1: calibrate para_min_chars -- the one paragraph-length
threshold every style measurement uses (a PDF-line-wrapping constant, not a
universal: 400 suited the parent's finance PDFs, 150 a health-policy corpus's).

Sweeps the threshold over the style-safe corpus with the instance's own
paragraph recovery (textseg.paragraphs_from_txt on clean_prose text, the
auto line/block mode decided at each threshold, as build_cohesion_norms
will) and picks, by the rule a health-policy build used: the most recovered
paragraphs with NO paper at zero paragraphs and adjacent pairs > 0 (fewest
zero-paragraph papers first when no threshold reaches zero). Writes the value
into both field-configs and the sweep table to
<field>-lit/references/para-calibration.md (tier1_fill.py appends it to
register-measurements.md).

RUN
    py -3 scripts/calibrate_paragraphs.py <field> [--dest <skills dir>]
        [--grid 80,100,120,150,200,250,300,350,400] [--set N]
--set N skips the choice and records N with the sweep beside it.
"""
import argparse
import os
import statistics
import sys

import _factory as F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field")
    ap.add_argument("--dest")
    ap.add_argument("--grid", default="80,100,120,150,200,250,300,350,400")
    ap.add_argument("--set", type=int)
    a = ap.parse_args()
    fld = F.Field(a.field, a.dest).require()
    if 0 not in fld.built_tiers():
        F.die("Tier 0 is not accepted yet -- run tier0_accept.py first")
    sys.path.insert(0, os.path.join(fld.lit, "scripts"))
    import textseg
    ids = fld.style_safe_ids()
    corpus = os.path.join(fld.lit, "references", "corpus")
    texts = {}
    for k in ids:
        with open(os.path.join(corpus, k + ".txt"), encoding="utf-8", errors="replace") as fh:
            texts[k] = textseg.clean_prose(fh.read())
    grid = sorted({int(x) for x in a.grid.split(",") if x.strip()} | ({a.set} if a.set else set()))
    rows = []
    print("sweeping para_min_chars over %d style-safe papers: %s" % (len(ids), grid))
    for t in grid:
        textseg.PARA_MIN_CHARS = t          # the auto mode test reads the module value
        per, pairs = {}, 0
        for k, text in texts.items():
            ps = list(textseg.paragraphs_from_txt(text, t, textseg.PARA_MIN_SENTS))
            per[k] = len(ps)
            pairs += sum(len(p) - 1 for p in ps)
        n = sum(per.values())
        zero = sorted(k for k, v in per.items() if v == 0)
        thin = sorted(k for k, v in per.items() if 0 < v < 5)
        med = statistics.median(per.values()) if per else 0
        rows.append({"t": t, "paras": n, "pairs": pairs, "zero": zero, "thin": thin, "median": med})
        print("  %4d  paragraphs %6d  pairs %7d  median/paper %5.1f  zero %3d  thin(1-4) %3d"
              % (t, n, pairs, med, len(zero), len(thin)))
    ok = [r for r in rows if r["pairs"] > 0]
    if not ok:
        F.die("no threshold recovers any adjacent pair -- check the corpus extraction")
    if a.set:
        pick, how = next(r for r in rows if r["t"] == a.set), "set by hand (--set)"
    else:
        best_zero = min(len(r["zero"]) for r in ok)
        pool = [r for r in ok if len(r["zero"]) == best_zero]
        pick = max(pool, key=lambda r: (r["paras"], r["t"]))
        how = ("most paragraphs with no paper at zero" if best_zero == 0 else
               "WARNING: every threshold leaves %d paper(s) at zero; fewest zeros, then most paragraphs"
               % best_zero)
    fld.set_scalar("para_min_chars", pick["t"], "calibrated %s by calibrate_paragraphs.py" % F.TODAY)
    out = os.path.join(fld.lit, "references", "para-calibration.md")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("## Paragraph threshold calibration (%s)\n\n" % F.TODAY)
        fh.write("calibrate_paragraphs.py over %d style-safe papers; chosen **para_min_chars = %d** (%s).\n\n"
                 % (len(ids), pick["t"], how))
        fh.write("| para_min_chars | paragraphs | adjacent pairs | median per paper | papers at 0 | papers at 1-4 |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for r in rows:
            fh.write("| %s%d%s | %d | %d | %.1f | %d | %d |\n" % (
                "**" if r is pick else "", r["t"], "**" if r is pick else "", r["paras"], r["pairs"],
                r["median"], len(r["zero"]), len(r["thin"])))
        if pick["zero"]:
            fh.write("\nPapers with no recovered paragraph at the chosen value: %s\n" % ", ".join(pick["zero"]))
    print("\nchosen para_min_chars = %d (%s); both field-configs updated; sweep -> %s"
          % (pick["t"], how, os.path.relpath(out, fld.lit)))
    print("NEXT: py -3 %s %s" % (os.path.join(F.HERE, "tier1_fill.py"), a.field))


if __name__ == "__main__":
    main()
