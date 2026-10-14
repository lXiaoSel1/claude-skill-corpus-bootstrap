#!/usr/bin/env python3
"""Like rep.py, across sections: a line `FILE <section>` starts the pairs for
that section (see templates/pairs_example_multi.txt). Every pair in every
section is checked first; if any fails to match exactly once, no file is
written.

RUN
    py -3 scripts/rep_multi.py <pairs.txt>
Exit code 1 when a pair does not match exactly once (nothing is written).
"""
import sys

import _rp
import _rep

ctx = _rp.Ctx(sys.argv)
if len(ctx.args) != 1:
    _rp.die(__doc__)
groups = _rep.parse(_rp.read(ctx.args[0]), multi=True)
if None in groups:
    _rp.die("pairs before the first `FILE <section>` line")
job = _rep.Job(ctx)
for target, pairs in groups.items():
    job.add(target, pairs)
sys.exit(job.commit())
