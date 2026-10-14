#!/usr/bin/env python3
"""Step g -- snapshot vs live section: the numbers (as a multiset), the cite
keys (as a set) and the comments (as an ordered list) must all match. Numbers
inside citation commands are ignored, so a key's year is not a number.

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


print("baseline: snapshot %s" % name)
bad = 0
for sec in ctx.sections(names):
    on, oc, ok = parts(ctx.snapshot_lines(name, sec))
    nn, nc, nk = parts(sec.lines())
    print("== %s" % sec.key)
    print("  numbers: old %d new %d  %s" % (
        sum(on.values()), sum(nn.values()),
        "MATCH" if on == nn else "DIFF old-only %s new-only %s" % (dict(on - nn), dict(nn - on))))
    print("  page comments: old %d new %d  %s" % (len(oc), len(nc), "MATCH" if oc == nc else "DIFF"))
    if oc != nc:
        for c in [c for c in oc if c not in nc]:
            print("    old-only: %% %s" % c)
        for c in [c for c in nc if c not in oc]:
            print("    new-only: %% %s" % c)
    print("  cite keys: old %d new %d  %s" % (len(ok), len(nk), "MATCH" if ok == nk else "DIFF " + str(sorted(ok ^ nk))))
    bad += (on != nn) + (oc != nc) + (ok != nk)
sys.exit(1 if bad else 0)
