#!/usr/bin/env python3
"""Measure paragraph cohesion against the corpus norms.  Pure stdlib.

WHY THIS EXISTS
    The skill's cohesion check used to be a read-through: a run could print
    "cohesion: 0 issues" without ever visiting a single sentence join, and a
    measured case exists where it did exactly that -- a limitations paragraph
    whose point (ii) and whose "Third," restated the same argument passed with
    zero findings.  This script makes every join and every paragraph produce
    numbers, so the review starts from a prioritised worklist instead of a
    blank page.

WHAT THE NUMBERS MAY AND MAY NOT SAY -- read before editing the output text
    The validation literature is one-directional here:

      - Local cohesion indices do NOT predict expert coherence judgments
        (TAACO's own validation; Crossley & McNamara 2010 found them
        uncorrelated or negatively correlated with rated quality).
      - The reverse cohesion effect (McNamara et al. 1996): high-knowledge
        readers learn MORE from low-cohesion text.  "Higher overlap is
        better" is empirically false, and most false in expert-to-expert
        registers like finance journals.
      - Over-smooth transition density is itself an AI tell.

    Therefore this script reports PERCENTILES AGAINST THE CORPUS and flags
    BOTH tails.  It never says "less coherent", "poorly written", or any
    quality verdict.  Low tail = candidate break; high tail = candidate
    redundancy.  The wording is "unusual relative to the corpus", always.

METRICS (ordered by validity in the literature, not by fame)
    M6b  singleton rate      content types used exactly once / all types.
                             The best cheap operationalisation of "a list of
                             disconnected sentences"; nearly length-robust.
    M4   centroid overlap    mean share of each sentence's content words that
                             appear elsewhere in the paragraph.  The one
                             family validated as positively predicting expert
                             judgments (global, not pairwise).
    M5'  orphan sentences    sentences sharing no content stem with ANY
                             earlier sentence -- named by index, actionable.
    M3   two-span overlap    C_i vs C_{i+1} | C_{i+2}: topics legitimately
                             return after one intervening sentence.
    M1   adjacent binary     near ceiling in the corpus; a floor test only.
    M9   anaphoric openers   This/These/Those/Such-opener rate.  Near zero is
                             a deficit the overlap metrics cannot see.
                             ("The" is deliberately excluded: formulaic
                             Results openers -- "The results show..." --
                             would saturate the index in this genre.)

RUN
    py -3 scripts/cohesion.py "<paragraph text>"
    py -3 scripts/cohesion.py --section results --file para.txt
    py -3 scripts/cohesion.py --json "<paragraph text>"
"""
import argparse
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


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from textseg import (split_sentences, content, tokens, stem,  # noqa: E402
                     STOPLIST, CONNECTIVE_RE, ANAPHORIC_RE)

SKILL = os.path.dirname(HERE)
NORMS = os.path.join(SKILL, "references", "cohesion-norms.json")

TOPIC_ZONE_TOKENS = 7
# Adjudication D5 of the writing canon: the topic is the first few words, not
# the grammatical subject (Williams' underline-the-first-six/seven; Gopen's
# up-to-the-main-verb).  Seven tokens, no parser.

STRESS_ZONE_TOKENS = 8
# Gopen & Swan: the stress position is the final point of syntactic closure.
# Without a parser: the text after the last internal colon/semicolon, else the
# last ~8 tokens.

CONNECTIVE_OPENERS = CONNECTIVE_RE
ANAPHORIC_OPENER = ANAPHORIC_RE
# Both are the SHARED inventory from textseg.py.  This file once kept its own
# lists; the connective one was a strict subset missing the entire contrast
# family, which biased the shipped adjudications (84.8->82.5, 81.5->82.1)
# and made "But"-opening joins unreachable for the ACCEPTABLE branch.  One
# inventory, every consumer -- same rule as the sentence splitter.


def zones(sentence):
    """(topic_zone_stems, stress_zone_stems) for one sentence.

    Stress zone = the clause after the last internal semicolon/colon, else the
    tail tokens.  Two guards, both measured: (a) a colon flanked by digits is
    a ratio/time/citation ("60:40", "15(2): iii"), not a clause boundary --
    214 corpus sentences would otherwise split there; (b) if the post-colon
    tail carries no content stems (616 corpus sentences end IN a colon), fall
    back to the sentence tail rather than returning an empty stress zone.
    Sensitivity of the D1 adjudication to (b): +0.16pp -- robust either way,
    but an empty zone is an unforced error.
    """
    toks = tokens(sentence)
    topic = {stem(w) for w in toks[:TOPIC_ZONE_TOKENS]
             if w not in STOPLIST and len(w) > 2}
    parts = re.split(r"(?<!\d)[;:](?!\d)", sentence)
    tail = parts[-1] if len(parts) > 1 else sentence
    ttoks = tokens(tail)[-STRESS_ZONE_TOKENS:]
    stress = {stem(w) for w in ttoks
              if w not in STOPLIST and len(w) > 2}
    if not stress:
        ttoks = toks[-STRESS_ZONE_TOKENS:]
        stress = {stem(w) for w in ttoks
                  if w not in STOPLIST and len(w) > 2}
    return topic, stress


def metrics(sents):
    """All paragraph-level indices for a list of sentences."""
    n = len(sents)
    C = [content(s) for s in sents]
    out = {"n_sentences": n}
    if n < 3:
        out["note"] = "fewer than 3 sentences; no interior structure to measure"
        return out

    # M1 adjacent binary
    adj = [1 if C[i] & C[i + 1] else 0 for i in range(n - 1)]
    out["m1_adjacent_binary"] = sum(adj) / (n - 1)

    # M3 two-span binary
    if n >= 3:
        two = [1 if C[i] & (C[i + 1] | C[i + 2]) else 0 for i in range(n - 2)]
        out["m3_two_span_binary"] = sum(two) / (n - 2)

    # M4 centroid overlap
    vals = []
    for i in range(n):
        if not C[i]:
            continue
        rest = set().union(*(C[j] for j in range(n) if j != i))
        vals.append(len(C[i] & rest) / len(C[i]))
    out["m4_centroid_overlap"] = sum(vals) / len(vals) if vals else 0.0

    # M5' orphans: no link to ANYTHING earlier
    orphans = []
    seen = set(C[0])
    for i in range(1, n):
        if C[i] and not (C[i] & seen):
            orphans.append(i + 1)          # 1-indexed sentence number
        seen |= C[i]
    out["m5_orphan_rate"] = len(orphans) / (n - 1)
    out["m5_orphan_sentences"] = orphans

    # M6 singleton / chained coverage.  Keys are ALWAYS emitted: a paragraph
    # of pure function words is degenerate, but a silently missing key turned
    # into a KeyError downstream and an omitted row in the report -- and an
    # omitted row is the one thing the output contract forbids.
    from collections import Counter
    df = Counter()
    for c in C:
        for t in c:
            df[t] += 1
    V = len(df)
    out["vocab_types"] = V
    if V:
        out["m6b_singleton_rate"] = sum(1 for v in df.values() if v == 1) / V
        out["m6a_chained_coverage"] = sum(1 for v in df.values() if v >= 2) / V
    else:
        out["m6b_singleton_rate"] = 0.0
        out["m6a_chained_coverage"] = 0.0
        out["note"] = "no content words in any sentence; M6 degenerate"

    # M8 max non-adjacent pair overlap -- the redundancy detector.
    # The motivating failure case for this whole check was a limitations
    # paragraph whose S1 clause (ii) and S6 restated one argument.  That pair
    # is NON-adjacent, so every adjacent index and even M4 diluted it (M4 sat
    # at P60 when the plan predicted an upper-tail hit -- measured, and the
    # prediction was wrong).  Pair granularity is what the case needs:
    # overlap = |Ci ∩ Cj| / min(|Ci|,|Cj|), maximised over pairs j >= i+2.
    best, bi, bj, bshared = 0.0, None, None, []
    for i in range(n):
        for j in range(i + 2, n):
            if not C[i] or not C[j]:
                continue
            ov = len(C[i] & C[j]) / min(len(C[i]), len(C[j]))
            if ov > best:
                best, bi, bj = ov, i + 1, j + 1
                bshared = sorted(C[i] & C[j])
    out["m8_max_nonadj_overlap"] = best
    if bi:
        out["m8_pair"] = "S%d↔S%d" % (bi, bj)
        out["m8_shared_stems"] = bshared[:8]

    # M9 anaphoric openers
    out["m9_anaphoric_opener_rate"] = (
        sum(1 for s in sents if ANAPHORIC_OPENER.match(s)) / n)

    return out


def join_details(sents):
    """Per-join mechanical facts for the JOINS table.  N-1 rows, no verdicts.

    The relation label and the final verdict are the model's job (register.md
    R9); this function supplies what a script can know: overlap, carrier
    candidates, zone hits, and the graded antecedent distance.
    """
    n = len(sents)
    C = [content(s) for s in sents]
    Z = [zones(s) for s in sents]
    rows = []
    seen = set()
    for i in range(n - 1):
        seen |= C[i]
        s2 = sents[i + 1]
        topic2, _ = Z[i + 1]
        _, stress1 = Z[i]
        shared_adj = C[i] & C[i + 1]
        shared_any = seen & C[i + 1]
        topic_from_stress = topic2 & stress1
        topic_from_prev = topic2 & C[i]
        topic_from_para = topic2 & seen
        conn = CONNECTIVE_OPENERS.match(s2.strip())
        dem = ANAPHORIC_OPENER.match(s2.strip())

        if topic_from_stress:
            grade = "STRONG"
        elif topic_from_prev or (dem and C[i]):
            grade = "GOOD"
        elif topic_from_para or shared_adj or (conn and shared_any):
            grade = "ACCEPTABLE"
        elif shared_any:
            grade = "WEAK"
        else:
            grade = "BROKEN?"        # candidate only -- the model adjudicates
                                     # (a relation-signalling connective with
                                     # no carrier is McCloskey's
                                     # asserted-not-earned, not automatically
                                     # broken; see canon E6/D3)

        carriers = []
        if shared_adj:
            carriers.append("lexical:" + ",".join(sorted(shared_adj)[:4]))
        if dem:
            carriers.append("demonstrative:" + dem.group(1))
        if conn:
            # group(0) is the whole matched opener (the shared regex has no
            # capture groups); trim wrapping punctuation and the comma.
            carriers.append("connective:" + conn.group(0).strip("\"“'‘([ ,").strip())

        rows.append({
            "pair": "S%d→S%d" % (i + 1, i + 2),
            "grade": grade,
            "overlap_prop": (len(shared_adj) / len(C[i])) if C[i] else 0.0,
            "overlap_stems": sorted(shared_adj)[:6],
            "stress_to_topic": sorted(topic_from_stress)[:4],
            "carriers": carriers or ["none-detected"],
            "connective_opener": (conn.group(0).strip("\"“'‘([ ,").strip()
                                  if conn else None),
        })
    return rows


# ---------------------------------------------------------------------------
# Norms lookup
# ---------------------------------------------------------------------------

def length_bin(n):
    if n <= 4:
        return "3-4"
    if n <= 6:
        return "5-6"
    if n <= 9:
        return "7-9"
    return "10+"


def load_norms():
    if not os.path.exists(NORMS):
        return None
    with open(NORMS, encoding="utf-8") as fh:
        return json.load(fh)


def percentile_of(value, samples):
    """Percentile rank of value within a sample.  ORDER-INDEPENDENT by
    design -- do not "optimise" this into bisect: the samples arrays in
    cohesion-norms.json are sorted only as a serialisation side effect, and
    nothing may depend on it."""
    if not samples:
        return None
    below = sum(1 for x in samples if x < value)
    equal = sum(1 for x in samples if x == value)
    return round(100.0 * (below + 0.5 * equal) / len(samples))


def lookup(norms, section, nbin, metric, value):
    """Percentile within the best-matching cell; says which cell was used."""
    for scope, key in (("section", section), ("all", "all")):
        if scope == "section" and not section:
            continue
        cell = norms.get("cells", {}).get("%s|%s" % (key, nbin))
        if cell and metric in cell.get("samples", {}):
            pct = percentile_of(value, cell["samples"][metric])
            return pct, "%s × %s (n=%d)" % (key, nbin, cell["n_paragraphs"])
    return None, "no norm cell"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(sents, section):
    n = len(sents)
    m = metrics(sents)
    norms = load_norms()
    nbin = length_bin(n)

    print("paragraph: %d sentences · length bin %s · section %s"
          % (n, nbin, section or "(unspecified → corpus-wide norm)"))
    if n < 3:
        print("  " + m.get("note", ""))
        return

    print()
    print("MEASUREMENTS (percentile = position in the corpus distribution;")
    print("both tails are reportable: low = candidate break, high = candidate")
    print("redundancy. These are priorities for the review, never verdicts.)")
    order = [("m6b_singleton_rate", "M6b singleton rate"),
             ("m4_centroid_overlap", "M4 centroid overlap"),
             ("m5_orphan_rate", "M5' orphan rate"),
             ("m3_two_span_binary", "M3 two-span overlap"),
             ("m1_adjacent_binary", "M1 adjacent binary"),
             ("m8_max_nonadj_overlap", "M8 max non-adj overlap"),
             ("m9_anaphoric_opener_rate", "M9 anaphoric openers")]
    used_cell = None
    for key, label in order:
        if key not in m:
            continue
        v = m[key]
        if norms:
            pct, cell = lookup(norms, section, nbin, key, v)
            used_cell = used_cell or cell
            tail = ""
            if pct is not None:
                if pct <= 10:
                    tail = "  ⚠ low tail"
                elif pct >= 90:
                    tail = "  ⚠ high tail"
                print("  %-24s %.3f   P%02d%s" % (label, v, pct, tail))
            else:
                print("  %-24s %.3f   (no norm)" % (label, v))
        else:
            print("  %-24s %.3f   (norms not built: py -3 scripts/build_cohesion_norms.py)"
                  % (label, v))
    if m.get("m5_orphan_sentences"):
        print("  orphan sentences: %s (no content stem shared with anything earlier)"
              % ", ".join("S%d" % i for i in m["m5_orphan_sentences"]))
    if m.get("m8_pair"):
        print("  M8 pair: %s share {%s}"
              % (m["m8_pair"], ", ".join(m.get("m8_shared_stems", []))))
        print("           MANDATORY R10 slot: the review must read this pair and")
        print("           answer — same argument restated, or legitimate term")
        print("           recurrence? (Lexical overlap cannot tell them apart in")
        print("           this register, where repeating terms is the norm; only")
        print("           reading the pair can. The percentile does not exempt.)")
    if used_cell:
        print("  norm cell: " + used_cell)

    print()
    print("JOINS (%d rows for %d sentences — mechanical facts; relation" % (n - 1, n))
    print("labels and verdicts are the review's job, per register.md R9)")
    for r in join_details(sents):
        print("  %-8s %-11s overlap %.2f  %s" % (
            r["pair"], r["grade"], r["overlap_prop"],
            " · ".join(r["carriers"])))
        if r["stress_to_topic"]:
            print("           stress→topic: %s" % ", ".join(r["stress_to_topic"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("text", nargs="?", help="paragraph text (or use --file)")
    ap.add_argument("--file")
    # FACTORY PARAMETERIZATION: choices come from the field taxonomy when
    # one exists; unknown sections fall back to corpus-wide cells anyway.
    import _fieldconfig
    _jobs = _fieldconfig.jobs()
    ap.add_argument("--section", choices=_jobs or None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    sents = split_sentences(text)
    if args.json:
        n = len(sents)
        out = {"metrics": metrics(sents),
               "joins": join_details(sents) if n >= 3 else [],
               "length_bin": length_bin(n) if n >= 3 else None}
        # n<3: render() prints the too-short note; --json must not instead
        # hand back a fabricated "3-4" bin and join rows for a passage that
        # has no interior structure.  Same input, same contract.
        norms = load_norms()
        if norms and len(sents) >= 3:
            for key in list(out["metrics"].keys()):
                if key.startswith("m") and isinstance(out["metrics"][key], float):
                    pct, cell = lookup(norms, args.section,
                                       length_bin(len(sents)), key,
                                       out["metrics"][key])
                    out["metrics"][key + "_pct"] = pct
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        render(sents, args.section)


if __name__ == "__main__":
    main()
