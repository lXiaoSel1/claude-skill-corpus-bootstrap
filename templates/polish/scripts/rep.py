#!/usr/bin/env python3
"""Exact, one-occurrence replacements read from a pairs file -- so LaTeX never
passes through a shell heredoc (which eats backslashes).

Pairs file: OLD text, a line `>>>`, NEW text; pairs separated by a line `===`
(see templates/pairs_example.txt). Every OLD must occur exactly once in the
target -- in a section of a single-file manuscript, once within that section
-- or nothing is written. The file's previous version is kept under
<manuscript dir>/.polish/rep-backup/.

RUN
    py -3 scripts/rep.py <section or file> <pairs.txt>
Exit code 1 when a pair does not match exactly once (nothing is written).
"""
import sys

import _rp
import _rep

ctx = _rp.Ctx(sys.argv)
if len(ctx.args) != 2:
    _rp.die(__doc__)
target, pairs = ctx.args
pairs = _rep.parse(_rp.read(pairs), multi=False)[None]
job = _rep.Job(ctx, pairs_file=ctx.args[1])
job.add(target, pairs)
sys.exit(job.commit())
