#!/usr/bin/env python3
"""Rebuild references/transitions.md over the full corpus.

WHY THIS EXISTS
    transitions.md was harvested from 45 of 165 corpus files -- 27% coverage --
    and register.md section 8 quoted its distribution as if it described the
    corpus.  Nothing said so anywhere until check_drift.py started asserting it.

THE SAMPLING BUG THIS FIXES
    The old harvest found joins by searching for CONNECTIVES.  Topic-chaining
    is defined by the ABSENCE of a connective -- the next sentence's subject
    picks up a noun the previous one introduced -- so that method could not
    find it except by accident.  Result: topic-chain showed as 17 of 126 joins
    (14%) while section 8 called it the default, which reads as a rule
    contradicting its own evidence.  It was not.  It was a measurement that
    could not see its own subject.

    So topic-chain is harvested by a DIFFERENT rule here: a sentence whose
    opening noun phrase repeats a content word from the previous sentence, with
    no connective present.  The two methods are not comparable as raw counts,
    and the generated file says so at the top of the section rather than
    inviting the same misreading again.

RUN
    py scripts/build_transitions.py
    py scripts/build_transitions.py --per-category 40
"""
import argparse
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
from textseg import split_sentences as _shared_split, clean_prose  # noqa: E402
# The shared abbreviation-aware splitter (scripts/textseg.py).  This script's
# original splitter had no abbreviation table and produced the measured
# "...the U.S. |> These rules..." false join at transitions.md:697; every
# consumer now imports the one fixed implementation.
SKILL = os.path.dirname(HERE)
REFS = os.path.join(SKILL, "references")
CORPUS = os.path.join(REFS, "corpus")
META = os.path.join(REFS, "corpus_meta.yaml")
OUT = os.path.join(REFS, "transitions.md")

CATEGORIES = [
    ("contrast",
     "However / In contrast / On the other hand / But / Yet / While / Although / Nevertheless / Instead",
     r"(?:However|In contrast|On the other hand|But|Yet|While|Although|Nevertheless|Instead)"),
    ("cause / consequence", "Thus / Therefore / Hence / As a consequence / As a result",
     r"(?:Thus|Therefore|Hence|As a consequence|As a result)"),
    ("evidence / illustration",
     "Consistent with / In line with / Indeed / In particular / For example / In other words / Put differently",
     r"(?:Consistent with|In line with|Indeed|In particular|For example|For instance|In other words|Put differently)"),
    ("reconcile / summation", "Taken together / In concert / Together / Overall",
     r"(?:Taken together|In concert|Together|Overall|Collectively)"),
    ("sequence / enumeration", "First / Second / Third / Finally",
     r"(?:First|Second|Third|Fourth|Finally)"),
    ("parallel", "Under X ... Under Y / Alternatively / Similarly / Likewise",
     r"(?:Alternatively|Similarly|Likewise|Conversely|Under \w+,)"),
]

STOP = set("""the a an and or of to in for on with by is are was were be been being that this these those
it its their his her our your as at from than then so such which who whom what when where how not no
we they he she i you can could may might must shall should will would have has had do does did if
more most less least other another same both each any all some many much very also only just even
one two three first second new same time paper study results result table figure section""".split())

SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
WORD = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")


def eligible():
    ids, cur = [], None
    if not os.path.exists(META):
        sys.exit("missing corpus_meta.yaml -- run build_corpus_meta.py first")
    for line in open(META, encoding="utf-8"):
        m = re.match(r"\s+- id:\s*(\S+)", line)
        if m:
            cur = m.group(1)
            continue
        if cur and re.match(r"\s+style_safe:\s*true", line):
            ids.append(cur)
            cur = None
    return ids


def sentences(text):
    out = []
    for s in _shared_split(text):
        # Reject extraction debris: reference lines, table rows, fragments.
        if 40 <= len(s) <= 400 and s[0].isupper() and s.count("(") <= 3 \
                and not re.search(r"\d{4}\)\s*[,.]?\s*$", s) \
                and sum(c.isdigit() for c in s) / len(s) < 0.12:
            out.append(s)
    return out


def content_words(s):
    return {w.lower() for w in WORD.findall(s) if w.lower() not in STOP}


def harvest(ids, per_cat):
    found = defaultdict(list)
    seen = set()
    for pid in ids:
        path = os.path.join(CORPUS, pid + ".txt")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            # clean_prose cuts reference lists in BOTH citation styles; the
            # sentences() filter below only caught author-year entries
            sents = sentences(clean_prose(fh.read()))
        for a, b in zip(sents, sents[1:]):
            # --- connective-based categories -----------------------------
            hit = None
            for name, _label, pat in CATEGORIES:
                if re.match(r"^%s\b" % pat, b):
                    hit = name
                    break
            if hit:
                if len(found[hit]) < per_cat and (pid, hit) not in seen:
                    found[hit].append((pid, a, b))
                    seen.add((pid, hit))
                continue

            # --- topic-chain: harvested by a DIFFERENT rule ---------------
            # No connective, and the second sentence opens on a noun phrase
            # that repeats a content word from the first.  Searching for
            # connectives can never find this, which is exactly why the old
            # harvest under-counted it.
            m = re.match(r"^(This|These|Those|Such|The)\s+([A-Za-z\-]+)", b)
            if m:
                lead = m.group(2).lower()
                if lead not in STOP and lead in content_words(a):
                    if len(found["topic-chain"]) < per_cat \
                            and (pid, "topic-chain") not in seen:
                        found["topic-chain"].append((pid, a, b))
                        seen.add((pid, "topic-chain"))
    return found


def clip(s, n=150):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "..."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=40)
    args = ap.parse_args()

    ids = eligible()
    found = harvest(ids, args.per_category)
    papers = {pid for rows in found.values() for pid, _, _ in rows}
    total = sum(len(v) for v in found.values())

    L = ["# transitions.md — how this literature connects adjacent sentences",
         "",
         "> **GENERATED FILE.** Rebuild with `py scripts/build_transitions.py`.",
         "> Harvested %s from **%d style-safe papers** (`corpus_meta.yaml`), the full"
         % (date.today().isoformat(), len(ids)),
         "> eligible corpus (the parent economics build once used a 45-paper sample).",
         "> %d joins drawn from %d papers; each line is `…end of sentence 1 ↳ start of"
         % (total, len(papers)),
         "> sentence 2` — CiteKey, capped at %d per category." % args.per_category,
         "",
         "> ## Contents",
         "> " + " · ".join(n for n, _, _ in CATEGORIES) + " · topic-chain",
         "",
         "---",
         "",
         "## ⚠️ Read the counts correctly — two harvest methods, not one",
         "",
         "The connective categories are found **by searching for their connective**.",
         "`topic-chain` cannot be: it is *defined* by the absence of one. It is harvested",
         "by a different rule — a sentence opening on `This/These/Such/The + noun` where",
         "that noun repeats a content word from the sentence before.",
         "",
         "**So the raw counts across the two groups are not comparable, and topic-chain's",
         "is a floor, not an estimate.** (In the parent economics build this file invited",
         "exactly that misreading: topic-chain came out at 17 of 126 joins while the",
         "register called it the default.)",
         "",
         "Whether topic-chaining is the default join in THIS literature is answered by",
         "`cohesion-norms.json` (`adjudications.implicit_join_share`, measured over every",
         "adjacent pair), not by these capped harvest counts. `register.md` §8 quotes that",
         "number once Tier 1 has filled it.",
         ""]

    order = [n for n, _, _ in CATEGORIES] + ["topic-chain"]
    labels = {n: lab for n, lab, _ in CATEGORIES}
    labels["topic-chain"] = ("next sentence's subject repeats a noun the previous "
                             "introduced; no explicit connective")

    L.append("## Distribution")
    L.append("")
    L.append("| category | joins | papers | harvested by |")
    L.append("|---|---|---|---|")
    for n in order:
        rows = found.get(n, [])
        L.append("| %s | %d | %d | %s |"
                 % (n, len(rows), len({p for p, _, _ in rows}),
                    "noun repetition" if n == "topic-chain" else "connective"))
    L.append("")
    L.append("---")
    L.append("")

    for n in order:
        rows = found.get(n, [])
        if not rows:
            continue
        L.append("## %s — %s" % (n, labels[n]))
        L.append("")
        for pid, a, b in rows:
            L.append('- "...%s ↳ %s" — %s' % (clip(a[-110:]), clip(b), pid))
        L.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")

    print("wrote references/transitions.md")
    print("  %d joins from %d papers (eligible %d)" % (total, len(papers), len(ids)))
    for n in order:
        print("    %-24s %d" % (n, len(found.get(n, []))))
    print("\nnow update registry.transitions to joins=%d papers_covered=%d"
          % (total, len(papers)))


if __name__ == "__main__":
    main()
