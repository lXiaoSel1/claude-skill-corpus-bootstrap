#!/usr/bin/env python3
"""Step g -- snapshot vs live section: the numbers (as a multiset), the cite
keys (as a set) and the comments (as an ordered list) must all match. Numbers
inside citation commands are ignored, so a key's year is not a number.

The numbers are also compared block by block (one block per page comment, or
per cited study when there are none): a number that moved to another study's
block prints MOVED?, a block whose numbers changed order prints ORDER?. Both
are for h2 to judge (a reordered comparison can be correct) and do not change
the exit code.

RUN
    py -3 scripts/trial_diff.py <snapshot> [section ...]   # default: every section in the snapshot
Exit code 1 when any section shows a DIFF.
"""
import os
import re
import sys
from collections import Counter

import _rp

ctx = _rp.Ctx(sys.argv)
if not ctx.args:
    _rp.die(__doc__)
name = ctx.args[0]
names = ctx.args[1:]
if not names:
    d = os.path.join(ctx.snapshot_root(), name)
    if not os.path.isdir(d):
        _rp.die("no snapshot %r under %s" % (name, ctx.snapshot_root()))
    names = sorted(f[:-4] for f in os.listdir(d) if f.endswith(".tex"))
COMMENT = re.compile(r"(?<!\\)%\s*(.*)$")
NUM = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")
CITE = _rp.CITE_KEYS_RE
split_sentences = ctx.split_sentences()


def numbers(text):
    return [x.replace(",", "") for x in NUM.findall(CITE.sub(" ", text))]


def parts(lines):
    body, comments, keys = [], [], set()
    for _, line in _rp.body_lines(lines):
        m = COMMENT.search(line)
        if m:
            comments.append(m.group(1).strip())
            line = line[:m.start()]
        for k in CITE.findall(line):
            keys |= {x.strip() for x in k.split(",") if x.strip()}
        body.append(CITE.sub(" ", line))
    nums = Counter(x.replace(",", "") for x in NUM.findall("\n".join(body)))
    return nums, comments, keys


def by_block(old_lines, new_lines):
    """[(label, verdict, old numbers, new numbers)] for blocks whose numbers differ."""
    old, mode = _rp.section_blocks(old_lines, split_sentences)
    new, mode2 = _rp.section_blocks(new_lines, split_sentences)
    if mode != mode2:
        old, new = _rp.comment_blocks(old_lines), _rp.comment_blocks(new_lines)
    out = []
    for k in list(old) + [k for k in new if k not in old]:
        a, b = numbers(old.get(k, "")), numbers(new.get(k, ""))
        if a == b:
            continue
        verdict = "ORDER?" if Counter(a) == Counter(b) else "MOVED?"
        out.append((k[0] if k[1] == 1 else "%s [#%d]" % k, verdict, a, b))
    return out


print("baseline: snapshot %s" % name)
bad = 0
for sec in ctx.sections(names):
    old_lines = ctx.snapshot_lines(name, sec)
    on, oc, ok = parts(old_lines)
    nn, nc, nk = parts(sec.lines())
    print("== %s" % sec.key)
    print("  numbers: old %d new %d  %s" % (
        sum(on.values()), sum(nn.values()),
        "MATCH" if on == nn else "DIFF old-only %s new-only %s" % (dict(on - nn), dict(nn - on))))
    moved = by_block(old_lines, sec.lines())
    if not moved:
        print("  numbers by block: SAME")
    for lab, verdict, a, b in moved:
        print("  numbers by block: %s %s  old %s  new %s" % (verdict, lab, a, b))
    print("  page comments: old %d new %d  %s" % (len(oc), len(nc), "MATCH" if oc == nc else "DIFF"))
    if oc != nc:
        for c in [c for c in oc if c not in nc]:
            print("    old-only: %% %s" % c)
        for c in [c for c in nc if c not in oc]:
            print("    new-only: %% %s" % c)
    print("  cite keys: old %d new %d  %s" % (len(ok), len(nk), "MATCH" if ok == nk else "DIFF " + str(sorted(ok ^ nk))))
    bad += (on != nn) + (oc != nc) + (ok != nk)
sys.exit(1 if bad else 0)
