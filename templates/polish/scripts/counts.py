#!/usr/bin/env python3
"""Step i -- whole-manuscript counts that polishing must not change:
  * cited keys (every \\cite... command, comments ignored);
  * page comments (`% Key p.N`, the per-fact source pointers), per section
    and in total;
  * \\bibitem entries in the compiled .bbl, and cited keys missing from it.

The expected values come from polish.yaml (expected_cited_keys,
expected_page_comments, expected_bibitems) when set; otherwise the first
run records a baseline in .polish/counts-baseline.json and later runs
compare against it (--rebaseline replaces it). Run it first at step a,
before any edit, so the baseline is the unedited manuscript. A baseline taken
before the first compile has no bibitems; that count is then not compared.

RUN
    py -3 scripts/counts.py [--rebaseline]
Exit code 1 when a count differs from what is expected, or a cited key is
missing from the .bbl.
"""
import json
import os
import re
import sys
from collections import OrderedDict

import _rp

ctx = _rp.Ctx(sys.argv)
rebase = _rp._pop(ctx.args, "--rebaseline", flag=True)
ms = ctx.ms
PAGE = re.compile(ctx.opts["page_comment_regex"])

keys = ms.cited_keys()
per = OrderedDict()
for s in ms.sections:
    per[s.key] = sum(len(PAGE.findall(t)) for _, t in s.lines())
pages = sum(per.values())
bbl_keys = []
if os.path.isfile(ms.bbl):
    bbl_keys = re.findall(r"\\bibitem(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?\{([^}]+)\}", _rp.read(ms.bbl))
now = {"cited_keys": len(keys), "page_comments": pages, "bibitems": len(bbl_keys)}

print("cited keys: %d" % now["cited_keys"])
print("page comments: %d  (%s)" % (pages, " · ".join("%s %d" % kv for kv in per.items() if kv[1]) or "none"))
by_ch = OrderedDict()
for s in ms.sections:
    if s.chapter:
        by_ch[s.chapter] = by_ch.get(s.chapter, 0) + per[s.key]
if by_ch:
    print("  by chapter: " + " · ".join("%s %d" % kv for kv in by_ch.items()))
print("bibitems: %s" % (len(bbl_keys) if bbl_keys else "no .bbl yet (compile.py)"))
fail = 0
if bbl_keys:
    miss = sorted(keys - set(bbl_keys))
    if miss:
        fail += 1
        print("  cited but not in the .bbl (%d): %s" % (len(miss), ", ".join(miss)))

exp = {k: ctx.opts["expected_" + k] for k in now}
exp = {k: int(v) for k, v in exp.items() if str(v).strip()}
base = os.path.join(ms.dir, ".polish", "counts-baseline.json")
src = "polish.yaml"
if not exp:
    if rebase or not os.path.isfile(base):
        os.makedirs(os.path.dirname(base), exist_ok=True)
        with open(base, "w", encoding="utf-8") as fh:
            json.dump(now, fh, indent=1)
        print("\nbaseline recorded in %s -- later runs compare against it" % base)
        sys.exit(1 if fail else 0)
    with open(base, encoding="utf-8") as fh:
        exp = json.load(fh)
    src = _rp.rel(base, ms.dir)
print("\nexpected (%s):" % src)
for k in now:
    if k in exp:
        if k == "bibitems" and (not bbl_keys or not exp[k]):
            print("  %-14s %4d  expect %4s  n/a (%s)" % (k, now[k], exp[k] or "-",
                  "no .bbl now" if not bbl_keys else "no .bbl when the baseline was taken"))
            continue
        ok = now[k] == exp[k]
        fail += not ok
        print("  %-14s %4d  expect %4d  %s" % (k, now[k], exp[k], "OK" if ok else "DIFF"))
sys.exit(1 if fail else 0)
