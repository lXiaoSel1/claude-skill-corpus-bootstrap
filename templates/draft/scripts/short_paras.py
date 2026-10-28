#!/usr/bin/env python3
"""Short corpus paragraphs of one chapter -- the candidates for its
short-paragraph bank, and the bank's verbatim check (factory 1.6.0).

The Version files quote one or two FIRST sentences per Version; a drafter
asked for a 100-170-word paragraph also needs whole paragraphs of that size to
imitate. This script lists every style-safe slice paragraph whose word count
and distinct-citation count fall in a band (page-break fragments -- a
lower-case opening or no closing punctuation -- left out), so a tagging pass
can assign each one to a Version. `--check` reads the finished bank
(references/sections/<job>/short-exemplars.md) and confirms every quoted
paragraph is verbatim in its paper's slice. `¶n` here is the paragraph's place
among the slice's recovered paragraphs (textseg), which can differ by one or two
from the PASS1 record numbering where a heading or footnote line was counted.

Bank format (one section per Version; `draftcheck.py version-card --full`
prints the section):

    ## Version 12 (03-evidence)
    - Silverstein2021 ¶6 · 128 words · 6 citations
      > <the paragraph, verbatim from slices/<job>/Silverstein2021.txt>

RUN
    py -3 scripts/short_paras.py <job> [--words 60-170] [--cites 2-6] [--tsv]
    py -3 scripts/short_paras.py <job> --check
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_structure as ms  # noqa: E402  (slices, style-safe set, citation counter)
from textseg import split_sentences  # noqa: E402


def band(s, default):
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", s or default)
    if not m:
        sys.exit("a band is LO-HI, e.g. 60-170")
    return int(m.group(1)), int(m.group(2))


def fragment(p):
    """A paragraph cut by a page break: lower-case first letter or no closing
    punctuation (a quotation mark or bracket after it is allowed)."""
    first = re.search(r"[A-Za-z]", p)
    return (first and first.group(0).islower()) or not re.search(r"[.?!][\"”’)\]]*\s*$", p.strip())


def footnote(p):
    """A footnote the slice kept as a paragraph: a 1-3 digit mark, then a
    capital ('4 Existing pension laws ...', '8. Another stream ...'; pension
    2026-10-27: 30 of 154 literature candidates). A year (four digits) is not."""
    return bool(re.match(r"\s*\d{1,3}\.?\s+[A-Z]", p))


def candidates(job, words, cites):
    out = []
    numbered = {}
    for key, p in ms.chapter_paragraphs(job):
        numbered[key] = numbered.get(key, 0) + 1
        w = len(p.split())
        c = len(ms.distinct_cites(p))
        if (words[0] <= w <= words[1] and cites[0] <= c <= cites[1] and not fragment(p)
                and not footnote(p)):
            out.append((key, numbered[key], w, c, len(split_sentences(p)), p))
    return out


def norm(s):
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def check(job):
    bank = os.path.join(ms.REF, "sections", job, "short-exemplars.md")
    if not os.path.isfile(bank):
        sys.exit("no bank at %s" % bank)
    with open(bank, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    paras = {}
    for key, p in ms.chapter_paragraphs(job, safe=set()):
        paras.setdefault(key, []).append(norm(p))
    bad = n = 0
    for m in re.finditer(r"(?m)^- (\S+) ¶(\d+)[^\n]*\n((?:  > [^\n]*\n?)+)", text):
        n += 1
        key = m.group(1)
        quoted = norm(re.sub(r"(?m)^  > ", "", m.group(3)))
        if not any(quoted and quoted == p for p in paras.get(key, [])):
            bad += 1
            print("NOT VERBATIM  %s ¶%s: not a whole paragraph of slices/%s/%s.txt" % (key, m.group(2), job, key))
    versions = len(re.findall(r"(?m)^## Version \d+", text))
    print("bank: %d paragraph(s) under %d Version heading(s); %d not verbatim" % (n, versions, bad))
    return 1 if bad or not n else 0


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    job = a[0]
    if "--check" in a:
        sys.exit(check(job))
    words = band(a[a.index("--words") + 1] if "--words" in a else None, "60-170")
    cites = band(a[a.index("--cites") + 1] if "--cites" in a else None, "2-6")
    rows = candidates(job, words, cites)
    if "--tsv" in a:
        print("key\tpara\twords\tcites\tsentences\ttext")
        for key, i, w, c, s, p in rows:
            print("%s\t%d\t%d\t%d\t%d\t%s" % (key, i, w, c, s, p.replace("\t", " ")))
    else:
        for key, i, w, c, s, p in rows:
            print("- %s ¶%d · %d words · %d citations · %d sentences\n  > %s\n" % (key, i, w, c, s, p))
    print("%d candidate paragraph(s) in %s from %d paper(s) (words %d-%d, citations %d-%d)"
          % (len(rows), job, len({r[0] for r in rows}), words[0], words[1], cites[0], cites[1]),
          file=sys.stderr)


if __name__ == "__main__":
    main()
