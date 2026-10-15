#!/usr/bin/env python3
"""Steps e / h2 -- print every context of a regex in one cited paper's text.

The text is the paper's PDF (or its lit corpus copy) with ligatures restored
and words split at a line end re-joined, so `follow-\\nup` reads `followup`.
When the regex as given finds nothing, it is retried once with every hyphen
or space between words loosened to [\\s-]*, then with abbreviations defined
as "Long Name (ABBR)" in the manuscript or the paper spelled the other way;
the output says which retry found the matches. Each context starts with its
page (p.N counts the PDF file's pages from 1; none for a lit corpus copy).

RUN
    py -3 scripts/pdf_ctx.py KEY "regex" [width]
Exit code 1 when the paper has no text to search.
"""
import re
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
if len(ctx.args) < 2:
    _rp.die(__doc__)
key, rx = ctx.args[0], ctx.args[1]
w = int(ctx.args[2]) if len(ctx.args) > 2 else 160
t, src = ctx.source_text(key)
if not t:
    print("%s: NO PDF TEXT (%s)" % (key, src))
    sys.exit(1)
hits = list(re.finditer(rx, t, re.I))
note = ""
if not hits:
    loose = re.sub(r"(?<=\w)(?:\\?-|\\? |\\s\+?|\\s\*)(?=\w)", r"[\\s-]*", rx)
    if loose != rx:
        hits = list(re.finditer(loose, t, re.I))
        note = " (0 for the regex as given; retried as %r)" % loose
if not hits:
    defs = dict(_rp.abbreviations(ctx.ms.expanded_body()), **_rp.abbreviations(t))
    for v, why in _rp.term_variants(rx, defs):
        try:
            more = list(re.finditer(v, t, re.I))
        except re.error:
            continue
        if more:
            hits, note = more, " (0 for the regex as given; found via %s as %r)" % (why, v)
            break
for m in hits:
    pg = ctx.page_label(key, m.start())
    print((pg + " " if pg else "") + "...", t[max(0, m.start() - w):m.end() + w], "...\n")
print("%s: %d match(es) in %s%s" % (key, len(hits), src, note))
