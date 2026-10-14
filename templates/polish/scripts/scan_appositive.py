#!/usr/bin/env python3
"""Step g -- list noun phrases tacked on after a comma (", a difference ...",
", a gap that ...", ", one ... and the other ...", ", the lowest ..."). Such
a tail has no finite verb of its own; rewrite the real ones as clauses.
List items and a subject after an opening adverbial also match: read each.

RUN
    py -3 scripts/scan_appositive.py [section ...] [--first N]   # N: only each section's first N paragraphs
"""
import re
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
first = _rp._pop(ctx.args, "--first")
CITE = re.compile(r"\\(cite(?!text)[a-zA-Z]*)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
CITETEXT = re.compile(r"\\citetext\{((?:[^{}]|\{[^{}]*\})*)\}")
COMMENT = re.compile(r"(?<!\\)%.*$", re.M)
PAT = re.compile(r",\s+((?:a|an|the|one|both|each|this|these|which)\s+[^,;.]{0,90})")


def strip_cites(s):
    s = CITETEXT.sub("", s)
    s = CITE.sub("", s)
    return COMMENT.sub("", s)


n = 0
for sec in ctx.sections(ctx.args):
    paras = ["\n".join(pl) for _, pl in _rp.paragraphs(_rp.section_body(sec))]
    if first:
        paras = paras[:int(first)]
    for i, p in enumerate(paras, 1):
        t = re.sub(r"\s+", " ", strip_cites(p))
        for m in PAT.finditer(t):
            n += 1
            print("%s p%d: ...%s" % (sec.key, i, t[max(0, m.start() - 60):m.end()]))
print("%d candidate(s)" % n)
