#!/usr/bin/env python3
"""Steps e / h2 -- print the quoted English source sentences in the reading
notes of the given keys that match a regex, with the page the note gives for
each quote: `p.N: "quote"` (page before the quote) or `"quote" (p.N)` (page
right after it). A quote with neither prints no page. Needs reading notes
(onboarding --notes, or polish.yaml notes_dir); one note per key, named
<KEY>.md, anywhere under that folder.

RUN
    py -3 scripts/note_terms.py KEY1,KEY2 "regex"
"""
import re
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
if len(ctx.args) < 2:
    _rp.die(__doc__)
if not (ctx.opts["notes_dir"] or ctx.library_index_meta().get("notes_dir")):
    _rp.die("no reading notes: onboard with --notes <folder>, or set notes_dir in polish.yaml")
keys = [k.strip() for k in ctx.args[0].split(",") if k.strip()]
pat = re.compile(ctx.args[1], re.I)
QUOTE = re.compile(r"[\"“]([^\"”]{15,400})[\"”]")
PAGE = r"pp?\.\s?\d+(?:[—–-]\d+)?"
# a page followed by a colon introduces the next quote; one in brackets or
# after a comma closes the quote before it
BEFORE = re.compile(r"(%s)\s*[:：]\s*$" % PAGE)                         # p.4："quote"
AFTER = re.compile(r"^\s*[,，]?\s*[(（]?\s*(%s)(?!\s*[:：])" % PAGE)      # "quote" (p.4)


def page_of(line, m):
    b = BEFORE.search(line[:m.start()])
    if b:
        return b.group(1)
    a = AFTER.search(line[m.end():])
    return a.group(1) if a else ""


for k in keys:
    note = ctx.note_path(k)
    if not note:
        print("== %s: NO NOTE" % k)
        continue
    seen = set()
    nd = ctx.opts["notes_dir"] or ctx.library_index_meta().get("notes_dir") or ctx.ms.dir
    print("== %s  (%s)" % (k, _rp.rel(note, nd)))
    for line in _rp.read(note).splitlines():
        for m in QUOTE.finditer(line):
            q = m.group(1)
            if pat.search(q) and q not in seen:
                seen.add(q)
                print("   %-8s %s" % (page_of(line, m), q[:300]))
