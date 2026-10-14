#!/usr/bin/env python3
"""Step e -- for each (cite key, term) pair, search the cited paper's own text
for the term; print the hit count and the first context.

A low-frequency word in the draft is kept as a SOURCE TERM only if the paper
itself uses it. Matching is case-insensitive; words may be joined by a space,
a hyphen or nothing; the last word may inflect (`analys` hits `analyses`).
The paper's text comes from its PDF (library index, else the reading note's
PDF field), else from the lit corpus copy; ligatures are restored and words
split at a line end are re-joined.

RUN
    py -3 scripts/source_term_check.py pairs.tsv          # lines: KEY<TAB>term
    py -3 scripts/source_term_check.py KEY "term" ["term" ...]
Exit code 1 when some key has no text to search (NO PDF TEXT).
"""
import os
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
a = ctx.args
if not a:
    _rp.die(__doc__)
if len(a) == 1 and os.path.isfile(a[0]):
    pairs = []
    for line in _rp.read(a[0]).splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            _rp.die("%s: not KEY<TAB>term: %r" % (a[0], line))
        key, term = line.split("\t", 1)
        pairs.append((key.strip(), term.strip()))
else:
    pairs = [(a[0], t) for t in a[1:]]
    if not pairs:
        _rp.die("give a pairs file, or a key followed by terms")

texts, sources, missing = {}, {}, set()
for key, term in pairs:
    if key not in texts:
        texts[key], sources[key] = ctx.source_text(key)
    t = texts[key]
    if not t:
        missing.add(key)
        print("%-24s %-34s NO PDF TEXT (%s)" % (key, term, sources[key]))
        continue
    hits = list(_rp.term_pattern(term).finditer(t))
    c = ""
    if hits:
        j = hits[0].start()
        c = t[max(0, j - 70):j + 90]
    print("%-24s %-34s %3d  %s" % (key, term, len(hits), c))

print("\nsources:")
for key in texts:
    print("  %-24s %s" % (key, sources[key]))
if missing:
    print("\n%d key(s) without text: %s" % (len(missing), ", ".join(sorted(missing))))
    sys.exit(1)
