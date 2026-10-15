#!/usr/bin/env python3
"""Build references/cohesion-norms.json -- the corpus cohesion distributions.

WHY THIS EXISTS
    A draft paragraph's cohesion numbers mean nothing in isolation: the
    literature warns that expert judgments do not track local cohesion, that
    high overlap can be redundancy, and that over-smoothness is an AI tell.
    The only defensible reading is "where does this paragraph sit in the
    corpus's own distribution" -- which requires the distribution to exist.

TWO SETS OF NORMS (both built, per the approved plan)
    coarse   all style-safe corpus papers, paragraph-recovered.  Covers every
             draft paragraph as the fallback cell.
    fine     draft-section's references/slices/<section>/ -- section-labelled
             verbatim chapter text.  JEAP 2023 measured that rhetorical
             sections differ in cohesion type, so a Results paragraph and an
             Introduction paragraph are different populations.  Coverage is
             the 60-paper sample, so cells are smaller; the lookup in
             cohesion.py prefers the fine cell and falls back to coarse, and
             always names the cell it used.

LENGTH BINS
    {3-4, 5-6, 7-9, 10+} sentences.  Binary indices on a 4-sentence paragraph
    can only take values {0, 1/3, 2/3, 1}; comparing them against a
    distribution dominated by longer paragraphs is bias, not measurement.

ADJUDICATION MEASUREMENTS (settle canon disagreements with data)
    earned_vs_asserted   Among adjacent pairs whose second sentence opens
                         with a connective: what fraction also carry a
                         lexical link?  McCloskey says a connective without a
                         carrier is fake cohesion; Dudenhefer counts the
                         connective itself as old information.  The corpus
                         decides what this literature actually does.
    antecedent_position  Among pairs whose topic zone links backward: what
                         fraction link to the previous sentence's STRESS zone
                         (Schimel's strict stress-to-topic) versus anywhere?
                         Settles canon disagreement D1 empirically.
    implicit_join_share  Fraction of adjacent pairs with NO sentence-initial
                         connective -- the first real measurement behind
                         register.md §8's "topic-chaining is the default"
                         claim, with a true denominator.

RUN
    py -3 scripts/build_cohesion_norms.py
"""
import json
import os
import re
import sys

# Console-safety: a Windows console may not be UTF-8 (e.g. cp936/GBK), and the corpus
# carries U+FFFD in 140 of 165 files (errors="replace" artefacts).  Without
# this, printing a concordance line kills the script mid-report -- measured:
# attest.py died on almost every term, and cohesion.py died AT the M8 line,
# before the JOINS table ever printed.  Never remove.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from collections import defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from textseg import (paragraphs_from_txt, content, split_sentences,  # noqa: E402
                     clean_prose, PARA_MIN_CHARS, PARA_MIN_SENTS, PARA_MODE)
from cohesion import (metrics, zones, length_bin,                   # noqa: E402
                      CONNECTIVE_OPENERS, ANAPHORIC_OPENER, join_details)

SKILL = os.path.dirname(HERE)
CORPUS = os.path.join(SKILL, "references", "corpus")
META = os.path.join(SKILL, "references", "corpus_meta.yaml")
# FACTORY PARAMETERIZATION: fine cells come from the sibling draft
# instance, which does not exist before Tier 2 -- coarse-only until then.
import _fieldconfig
SLICES = _fieldconfig.draft_slices_dir()
OUT = os.path.join(SKILL, "references", "cohesion-norms.json")

METRIC_KEYS = ["m1_adjacent_binary", "m3_two_span_binary", "m4_centroid_overlap",
               "m5_orphan_rate", "m6b_singleton_rate", "m6a_chained_coverage",
               "m8_max_nonadj_overlap", "m9_anaphoric_opener_rate"]

SECTIONS = _fieldconfig.jobs()   # [] before Tier 2 => fine cells skipped
# draft-section also has slices/model/ (formal-derivation chapters); excluded
# because our manuscript has no such section and its prose is a different
# register (proofs).


def style_safe_ids():
    ids, cur = [], None
    for line in open(META, encoding="utf-8"):
        m = re.match(r"\s+- id:\s*(\S+)", line)
        if m:
            cur = m.group(1)
            continue
        if cur and re.match(r"\s+style_safe:\s*true", line):
            ids.append(cur)
            cur = None
    return ids


def add_paragraph(cells, key, sents, adjud):
    m = metrics(sents)
    if m["n_sentences"] < 3:
        return False
    nbin = length_bin(m["n_sentences"])
    cell = cells["%s|%s" % (key, nbin)]
    cell["n_paragraphs"] += 1
    cell["sent_counts"].append(m["n_sentences"])
    for k in METRIC_KEYS:
        if k in m:
            cell["samples"][k].append(round(m[k], 4))

    # adjudication counters over every interior adjacent pair
    C = [content(s) for s in sents]
    Z = [zones(s) for s in sents]
    for i in range(len(sents) - 1):
        s2 = sents[i + 1].strip()
        adjud["pairs"] += 1
        conn = bool(CONNECTIVE_OPENERS.match(s2))
        lex = bool(C[i] & C[i + 1])
        if conn:
            adjud["connective_pairs"] += 1
            if lex:
                adjud["connective_with_carrier"] += 1
        else:
            adjud["implicit_pairs"] += 1
        topic2, _ = Z[i + 1]
        _, stress1 = Z[i]
        if topic2 & C[i]:
            adjud["topic_linked_pairs"] += 1
            if topic2 & stress1:
                adjud["topic_from_stress"] += 1

    # Join-grade histogram.  Exists because cohesion-canon.md's pillar 1 once
    # claimed "the join-grade distribution in the norms shows BROKEN-grade
    # pairs are the rare tail" while no such distribution existed anywhere --
    # a designed corpus status inside a file whose premise is that every rule
    # carries its measurement.  Now the claim has a number behind it.
    for r in join_details(sents):
        adjud["grade_" + r["grade"].rstrip("?")] += 1
    return True


def main():
    ids = set(style_safe_ids())
    cells = defaultdict(lambda: {"n_paragraphs": 0, "sent_counts": [],
                                 "samples": defaultdict(list)})
    adjud = defaultdict(int)
    # the fine (slice) pass used to feed the SAME
    # adjudication counter, so every sliced paragraph was counted twice
    # (the mathematics instance's pairs jumped 6,923 -> 8,157 after Tier 2). Adjudications are
    # corpus-level facts: coarse pass only; fine cells get a throwaway counter.
    adjud_fine = defaultdict(int)

    # ---- coarse: whole corpus, paragraph-recovered -------------------------
    per_paper = {}
    for pid in sorted(ids):
        path = os.path.join(CORPUS, pid + ".txt")
        if not os.path.exists(path):
            continue
        # running prose only: numeric-style reference entries ("Smith J.
        # Title. AJIM. 2019;12:3.") split into 3+ "sentences" and would
        # enter the norms as paragraphs
        text = clean_prose(open(path, encoding="utf-8", errors="replace").read())
        n = 0
        for sents in paragraphs_from_txt(text):
            if add_paragraph(cells, "all", sents, adjud):
                n += 1
        per_paper[pid] = n

    recovered = {k: v for k, v in per_paper.items() if v >= 5}
    failed = sorted(k for k, v in per_paper.items() if v == 0)
    # 1-4 paragraphs: neither "recovered" (>=5) nor "failed" (0). Before
    # 2026-10-07 such papers vanished from the report; three of them had
    # cleared the bar only on their reference-list entries.
    thin = sorted(k for k, v in per_paper.items() if 0 < v < 5)

    # ---- fine: section-labelled slices ------------------------------------
    fine_counts = {}
    for sec in (SECTIONS if SLICES and os.path.isdir(SLICES) else []):
        d = os.path.join(SLICES, sec)
        if not os.path.isdir(d):
            continue
        n = 0
        for f in sorted(os.listdir(d)):
            if not f.endswith(".txt"):
                continue
            key = f[:-4]
            if key not in ids:
                continue          # damaged / alias / non-research papers stay out
            text = clean_prose(open(os.path.join(d, f), encoding="utf-8",
                                    errors="replace").read())
            text = "\n".join(ln for ln in text.split("\n")
                             if not ln.startswith("====="))   # slice headers
            # same paragraph recovery as the coarse pass (line or block mode)
            for sents in paragraphs_from_txt(text):
                if add_paragraph(cells, sec, sents, adjud_fine):
                    n += 1
        fine_counts[sec] = n

    # ---- summarise ---------------------------------------------------------
    def summarize(cell):
        s = {}
        for k, vals in cell["samples"].items():
            vals.sort()
            n = len(vals)
            if not n:
                continue
            q = lambda p: vals[min(n - 1, int(n * p))]
            s[k] = {"n": n, "p10": q(.10), "p25": q(.25), "median": q(.50),
                    "p75": q(.75), "p90": q(.90)}
        return s

    out = {
        "_comment": [
            "GENERATED by scripts/build_cohesion_norms.py -- do not hand-edit.",
            "Percentile cells for paragraph cohesion, keyed 'scope|length_bin'.",
            "scope 'all' = %d style-safe corpus papers, paragraph-recovered;"
            % len(ids),
            "scope '<section>' = %s-draft slices (style-safe papers only)."
            % _fieldconfig.field(),
            "Both tails are reportable: low = candidate break, high = candidate",
            "redundancy. The numbers prioritise; they never judge -- see the",
            "validity warnings in scripts/cohesion.py's docstring.",
        ],
        "schema_version": 1,
        "generated": date.today().isoformat(),
        "coverage": {
            "style_safe_papers": len(ids),
            "papers_with_recovered_paragraphs": len(recovered),
            "papers_failed_recovery": failed,
            "papers_thin_recovery": thin,
            "_why_failed": [
                "These papers' extraction wraps every line short, so no line",
                "clears the %d-char paragraph threshold. Declared here rather"
                % PARA_MIN_CHARS,
                "than silently missing -- the same manifest discipline as",
                "corpus_meta.yaml. Their prose still counts in terms.md and",
                "transitions.md, which do not need paragraph boundaries.",
            ],
            "total_paragraphs": sum(c["n_paragraphs"] for k, c in cells.items()
                                    if k.startswith("all|")),
            "fine_paragraphs_by_section": fine_counts,
        },
        "thresholds": {
            "para_min_chars": PARA_MIN_CHARS, "para_min_sents": PARA_MIN_SENTS,
            "paragraph_mode": PARA_MODE,
            "topic_zone_tokens": 7, "stress_zone_tokens": 8,
            "length_bins": ["3-4", "5-6", "7-9", "10+"],
        },
        "adjudications": {
            "_what": [
                "Corpus measurements that settle writing-canon disagreements;",
                "quoted in cohesion-canon.md and cohesion-measurements.md.",
            ],
            "pairs_total": adjud["pairs"],
            "implicit_join_share": round(adjud["implicit_pairs"] / adjud["pairs"], 4)
                if adjud["pairs"] else None,
            "connective_pairs": adjud["connective_pairs"],
            "earned_vs_asserted": {
                "connective_with_lexical_carrier": adjud["connective_with_carrier"],
                "share": round(adjud["connective_with_carrier"]
                               / adjud["connective_pairs"], 4)
                if adjud["connective_pairs"] else None,
            },
            "antecedent_position_D1": {
                "topic_linked_pairs": adjud["topic_linked_pairs"],
                "from_stress_zone": adjud["topic_from_stress"],
                "share_stress_to_topic": round(adjud["topic_from_stress"]
                                               / adjud["topic_linked_pairs"], 4)
                if adjud["topic_linked_pairs"] else None,
            },
            "join_grade_histogram": {
                g: adjud["grade_" + g]
                for g in ("STRONG", "GOOD", "ACCEPTABLE", "WEAK", "BROKEN")
                if ("grade_" + g) in adjud
            },
        },
        "cells": {},
    }

    for key in sorted(cells):
        cell = cells[key]
        out["cells"][key] = {
            "n_paragraphs": cell["n_paragraphs"],
            "summary": summarize(cell),
            "samples": {k: v for k, v in cell["samples"].items()},
        }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    cov = out["coverage"]
    adj = out["adjudications"]
    print("wrote references/cohesion-norms.json")
    print("  style-safe papers          %d" % cov["style_safe_papers"])
    print("  with recovered paragraphs  %d" % cov["papers_with_recovered_paragraphs"])
    print("  failed recovery            %s" % (cov["papers_failed_recovery"] or "none"))
    print("  thin recovery (1-4 paras)  %s" % (cov.get("papers_thin_recovery") or "none"))
    print("  total paragraphs (coarse)  %d" % cov["total_paragraphs"])
    print("  fine paragraphs by section %s" % cov["fine_paragraphs_by_section"])
    print()
    print("  adjudications over %d adjacent pairs:" % adj["pairs_total"])
    pct = lambda v: "n/a" if v is None else "%.1f%%" % (100 * v)
    print("    implicit joins (no sentence-initial connective)  %s"
          % pct(adj["implicit_join_share"]))
    print("    connective openers that ALSO carry a lexical link %s  (earned vs asserted)"
          % pct(adj["earned_vs_asserted"]["share"]))
    print("    backward topic links coming from the stress zone  %s  (D1)"
          % pct(adj["antecedent_position_D1"]["share_stress_to_topic"]))
    if not adj["pairs_total"]:
        print("  WARNING: zero adjacent pairs -- para_min_chars too high for this"
              " corpus's line wrapping? Calibrate it in field-config.yaml.")
    hist = adj.get("join_grade_histogram", {})
    if hist:
        tot = sum(hist.values())
        print("    join-grade histogram: " + " · ".join(
            "%s %.1f%%" % (g, 100 * v / tot) for g, v in hist.items()))


if __name__ == "__main__":
    main()
