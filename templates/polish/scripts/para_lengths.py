#!/usr/bin/env python3
"""Step g / final check -- sentences per paragraph over the whole manuscript, in
document order, with {{FIELD}}-lit's sentence splitter (a sentence needs 3+
words). Rules:
  * a paragraph over `max_sentences` (default 9) sentences -> split it;
  * `uniform_run` (default 3) consecutive paragraphs with the same count ->
    uniformity flag; runs cross section boundaries, so check the whole text;
  * a sentence longer than `max_words` (default: the corpus words-per-sentence
    P90, as the sweep measures it), citation commands not counted -> shorten it.

Named sections narrow what FAILS (a long paragraph, a run touching them,
their long sentences); the whole-manuscript tables are printed either way.

RUN
    py -3 scripts/para_lengths.py [section ...]
Exit code 1 when a rule fails in scope.
"""
import re
import sys
from collections import Counter

import _rp

ctx = _rp.Ctx(sys.argv)
split_sentences = ctx.split_sentences()
o = ctx.opts
MAXS, RUN, MINW = o["max_sentences"], o["uniform_run"], o["min_words"]
scope = {s.key for s in ctx.sections(ctx.args)} if ctx.args else None
BREAK = re.compile(r"\s*(?:%|\\clearpage\b|\\newpage\b)")


def strip_tex(s):
    s = re.sub(r"(?<!\\)%.*", "", s)          # unescaped comments only; keep \%
    s = s.replace("\\%", "%")
    s = re.sub(r"\\cite[tp]?(?:alias)?\*?(?:\[[^\]]*\])*\{[^}]*\}", "CITE", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*", " ", s)
    return re.sub(r"[{}~]", " ", s)


def count(text):
    return len([x for x in split_sentences(strip_tex(text)) if len(x.split()) >= MINW])


rows = []                                    # (section, first line, sentences)
for sec in ctx.ms.sections:
    buf, start = [], None
    for ln, line in _rp.section_body(sec) + [(None, "")]:
        if not line.strip() or BREAK.match(line) or _rp.HEADING_LINE.match(line):
            if buf:
                rows.append((sec.key, start, count("\n".join(buf))))
            buf, start = [], None
            continue
        start = start or ln
        buf.append(line)

if not rows:
    _rp.die("no paragraphs found in %s" % ctx.ms.path)
print("paragraphs: %d" % len(rows))
dist = Counter(n for _, _, n in rows)
print("distribution:", " · ".join("%d×%d" % (k, dist[k]) for k in sorted(dist)))
ns = sorted(n for _, _, n in rows)
print("median %d, mean %.2f, max %d" % (ns[len(ns) // 2], sum(ns) / len(ns), ns[-1]))
fails = 0

print("\n>%d sentences (split):" % MAXS)
for s, ln, n in rows:
    if n > MAXS:
        mark = "" if scope is None or s in scope else "   (out of scope)"
        fails += mark == ""
        print("  L%d\t%s\t%d%s" % (ln, s, n, mark))

print("\nuniformity: %d consecutive identical counts (document order):" % RUN)
hit = False
for k in range(len(rows) - RUN + 1):
    win = rows[k:k + RUN]
    if len({r[2] for r in win}) == 1:
        hit = True
        inside = scope is None or any(r[0] in scope for r in win)
        fails += inside
        print("  %s\t%s|%s\t%d%s" % (",".join("L%d" % r[1] for r in win), win[0][0], win[-1][0],
                                     win[0][2], "" if inside else "   (out of scope)"))
if not hit:
    print("  none")

if str(o["max_words"]).lower() == "auto":
    _, MAXW = _rp.corpus_length_stats(ctx)
    how = "corpus P90"
else:
    MAXW, how = o["max_words"], "polish.yaml max_words"
print("\nsentences over %d words (%s)%s:" % (MAXW, how, "" if scope is None else " in " + ", ".join(sorted(scope))))
long_n = 0
for sec in ctx.ms.sections:
    if scope is not None and sec.key not in scope:
        continue
    for ln, snt in _rp.para_sentences(_rp.section_body(sec), split_sentences):
        n = len([t for t in _rp.toks(snt) if t != "citex"])     # citations not counted
        if n > MAXW:
            long_n += 1
            print("  L%d\t%s\t%dw  %s…" % (ln, sec.key, n, snt[:90]))
if not long_n:
    print("  none")
fails += long_n

print("\nper paragraph:")
for s, ln, n in rows:
    print("  L%d\t%s\t%d" % (ln, s, n))
sys.exit(1 if fails else 0)
