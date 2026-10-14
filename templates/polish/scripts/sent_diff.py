#!/usr/bin/env python3
"""Step h2 -- sentence-level diff of a section, snapshot vs live, block by block.

A block is the text up to and including a line that ends in a comment (the
`% Key p.N` page comment that records where a fact came from), so one block
is one source's facts; text after the last comment is one more block. Blocks
are matched by their comment (and its occurrence number), not by position,
so a block inserted or dropped does not shift every later comparison. For
each changed block, the sentences only in the snapshot print as `-`, the
sentences only in the live text as `+`: check each against the source.

RUN
    py -3 scripts/sent_diff.py <snapshot> <section> [section ...]
Exit code 1 when blocks were added or removed (the pairing is then partial).
"""
import re
import sys
from collections import OrderedDict

import _rp

ctx = _rp.Ctx(sys.argv)
if len(ctx.args) < 2:
    _rp.die(__doc__)
name = ctx.args[0]
split_sentences = ctx.split_sentences()
COMMENT = re.compile(r"(?<!\\)%\s*(.*)$")


def blocks(lines):
    out, buf, seen = OrderedDict(), [], {}
    for _, line in _rp.body_lines(lines):
        m = COMMENT.search(line)
        body = re.sub(r"(?<!\\)%.*$", "", line).strip()
        if body:
            buf.append(body)
        if m:
            key = m.group(1).strip()
            seen[key] = seen.get(key, 0) + 1
            out[(key, seen[key])] = " ".join(buf)
            buf = []
    if buf:
        out[("(no comment)", 1)] = " ".join(buf)
    return out


CITE_ANY = re.compile(r"\\citetext\{(?:[^{}]|\{[^{}]*\})*\}|\\cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{[^}]*\}")


def sentences(text):
    """Split raw LaTeX; a sentence that opens with \\citet{} is still a new
    sentence (the splitter wants a capital), so citations are swapped for
    capitalised placeholders while splitting and put back after."""
    keep = []

    def hold(m):
        keep.append(m.group(0))
        return "Cite%dq" % (len(keep) - 1)
    out = split_sentences(CITE_ANY.sub(hold, text))
    return [re.sub(r"Cite(\d+)q", lambda m: keep[int(m.group(1))], s).strip() for s in out]


def label(k):
    return k[0] if k[1] == 1 else "%s [#%d]" % k


uneven = 0
for sec in ctx.sections(ctx.args[1:]):
    old, new = blocks(ctx.snapshot_lines(name, sec)), blocks(sec.lines())
    print("##### %s: %d blocks in snapshot %s, %d now" % (sec.key, len(old), name, len(new)))
    gone = [k for k in old if k not in new]
    added = [k for k in new if k not in old]
    if gone or added:
        uneven += 1
        print("  ! block count or comments changed: %d only in the snapshot, %d only now"
              % (len(gone), len(added)))
    for i, k in enumerate(new, 1):
        sn = sentences(new[k])
        so = sentences(old.get(k, ""))
        if so == sn:
            continue
        print("=== B%d %s%s" % (i, label(k), "" if k in old else "   (new block)"))
        for s in so:
            if s not in sn:
                print("  - %s" % s)
        for s in sn:
            if s not in so:
                print("  + %s" % s)
    for k in gone:
        print("=== %s   (only in the snapshot)" % label(k))
        for s in sentences(old[k]):
            print("  - %s" % s)
sys.exit(1 if uneven else 0)
