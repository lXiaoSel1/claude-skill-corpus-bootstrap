#!/usr/bin/env python3
"""Step h2 -- sentence-level diff of a section, snapshot vs live, block by block.

A block is one source's facts. With page comments, a block is the text up to
and including a line that ends in a comment (the `% Key p.N` page comment);
text after the last comment is one more block. Without page comments, a block
is one cited study: it starts at a sentence whose first citation names other
keys than the block before. Blocks are matched by their comment or keys (and
occurrence number), not by position, so a block inserted or dropped does not
shift every later comparison. For each changed block, the sentences only in
the snapshot print as `-`, the sentences only in the live text as `+`: check
each against the source.

RUN
    py -3 scripts/sent_diff.py <snapshot> <section> [section ...]
Exit code 1 when blocks were added or removed (the pairing is then partial).
"""
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
if len(ctx.args) < 2:
    _rp.die(__doc__)
name = ctx.args[0]
split_sentences = ctx.split_sentences()


def sentences(text):
    return _rp.latex_sentences(text, split_sentences)


def label(k):
    return k[0] if k[1] == 1 else "%s [#%d]" % k


uneven = 0
for sec in ctx.sections(ctx.args[1:]):
    old_lines, new_lines = ctx.snapshot_lines(name, sec), sec.lines()
    old, mode = _rp.section_blocks(old_lines, split_sentences)
    new, mode2 = _rp.section_blocks(new_lines, split_sentences)
    if mode != mode2:   # page comments added or removed: compare the same way
        old, new = _rp.comment_blocks(old_lines), _rp.comment_blocks(new_lines)
        mode = "comments"
    print("##### %s: %d blocks in snapshot %s, %d now (one block per %s)"
          % (sec.key, len(old), name, len(new),
             "page comment" if mode == "comments" else "cited study"))
    gone = [k for k in old if k not in new]
    added = [k for k in new if k not in old]
    if gone or added:
        uneven += 1
        print("  ! blocks changed: %d only in the snapshot, %d only now" % (len(gone), len(added)))
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
