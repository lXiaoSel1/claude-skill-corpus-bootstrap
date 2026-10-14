#!/usr/bin/env python3
"""Step g (optional) -- words per sentence in the corpus chapter slices
({{FIELD}}-draft references/slices/<job>/, built at Tier 2) against the
manuscript; words per paragraph in the manuscript; the longest paragraphs;
the median by chapter (sections grouped under their parent heading).

RUN
    py -3 scripts/words_compare.py [--jobs introduction,discussion]   # default: every job sliced
"""
import os
import re
import sys
from statistics import median, quantiles

import _rp

ctx = _rp.Ctx(sys.argv)
jobs_arg = _rp._pop(ctx.args, "--jobs")
split_sentences = ctx.split_sentences()
SLICES = os.path.join(ctx.draft, "references", "slices")


def words(s):
    return len(re.findall(r"[A-Za-z0-9][\w'’.,%-]*", s))


def q(xs):
    if len(xs) < 2:
        return "n=%d" % len(xs)
    p, f = quantiles(xs, n=10), quantiles(xs, n=4)
    return "n=%d median %.0f · P25 %.0f · P75 %.0f · P90 %.0f" % (len(xs), median(xs), f[0], f[2], p[8])


if os.path.isdir(SLICES):
    jobs = jobs_arg.split(",") if jobs_arg else sorted(
        d for d in os.listdir(SLICES) if os.path.isdir(os.path.join(SLICES, d))
        and not d.startswith("_") and d != "back-matter")
else:
    jobs = jobs_arg.split(",") if jobs_arg else []
if not jobs:
    print("no corpus slices (%s): Tier 2 not built -- corpus comparison skipped" % SLICES)
for chap in jobs:
    d = os.path.join(SLICES, chap)
    files = sorted(f for f in os.listdir(d) if f.endswith(".txt")) if os.path.isdir(d) else []
    if not files:
        print("corpus %-12s missing or empty (%s) -- skipped" % (chap, d))
        continue
    ws = []
    for f in files:
        txt = _rp.read(os.path.join(d, f))
        txt = re.sub(r"(?m)^=====.*$", " ", txt)
        txt = re.sub(r"-\n(?=[a-z])", "", txt)
        txt = re.sub(r"\s+", " ", txt)
        txt = re.sub(r"\[[\d,\s–-]+\]", " ", txt)          # numeric cites
        for s in split_sentences(txt):
            n = words(s)
            if 3 <= n <= 150:
                ws.append(n)
    print("corpus %-12s words/sentence: %s" % (chap, q(ws)))


def strip_tex(s):
    s = re.sub(r"(?<!\\)%.*", "", s).replace("\\%", "%")
    s = re.sub(r"\\cite[tp](?:alias)?\{([^}]*)\}", lambda m: "Author (2000)", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*", " ", s)
    return re.sub(r"[{}~$]", " ", s)


BREAK = re.compile(r"\s*(?:%|\\clearpage\b|\\newpage\b)")
paras = []                                   # (section, chapter, first line, text)
for sec in ctx.ms.sections:
    buf, start = [], None
    for ln, line in _rp.section_body(sec) + [(None, "")]:
        if not line.strip() or BREAK.match(line) or _rp.HEADING_LINE.match(line):
            if buf:
                paras.append((sec.key, sec.chapter or sec.key, start, " ".join(buf)))
            buf, start = [], None
            continue
        start = start or ln
        buf.append(re.sub(r"(?<!\\)%.*", "", line))

sw, pw, rows = [], [], []
for key, chap, ln, t in paras:
    sents = [x for x in split_sentences(strip_tex(t)) if len(x.split()) >= 3]
    w = [words(x) for x in sents]
    sw += w
    pw.append(sum(w))
    rows.append((key, ln, len(sents), sum(w), round(sum(w) / max(len(w), 1))))
print("manuscript words/sentence: %s" % q(sw))
print("manuscript words/paragraph: %s" % q(pw))
print("\nlongest paragraphs (words):")
for r in sorted(rows, key=lambda r: -r[3])[:12]:
    print("  L%d\t%s\t%d sent\t%d words\t%d w/sent" % (r[1], r[0], r[2], r[3], r[4]))
print("\nby chapter (median words/sentence):")
chapters = []
for _, chap, _, _ in paras:
    if chap not in chapters:
        chapters.append(chap)
for ch in chapters:
    xs = []
    for _, c, _, t in paras:
        if c == ch:
            xs += [words(x) for x in split_sentences(strip_tex(t)) if len(x.split()) >= 3]
    print("  %-28s n=%d median %s" % (ch[:28], len(xs), "%.0f" % median(xs) if xs else "-"))
