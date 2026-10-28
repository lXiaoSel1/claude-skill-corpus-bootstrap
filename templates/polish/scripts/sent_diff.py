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

Rule 1 keeps the source's strength, and an edit can raise it without changing
a number or a key ("evidence pointed to X" -> "studies support the X
hypothesis"). Each changed block's claim words are counted in three tiers --
hedges (suggest, consistent with, point to, may, argue, ...), findings (find,
show, document, ...), strong claims (support ... hypothesis, confirm,
demonstrate, cause, lead to, ...) -- and two changes are listed:
  STRONGER?    a finding or strong-claim word is used more, and it is above the
               snapshot block's strongest tier or a weaker word is used less
  HEDGE LOST?  a hedge is used less, and the block has fewer hedges in all
               (one hedge for another, "linked to" -> "associated with", is not listed)
Each one is checked against the source in h2: kept only if the source says it
that strongly, else the snapshot's wording comes back. They do not change the
exit code.

RUN
    py -3 scripts/sent_diff.py <snapshot> <section> [section ...]
Exit code 1 when blocks were added or removed (the pairing is then partial).
"""
import re
import sys
from collections import Counter

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


# claim words by tier: 0 hedge, 1 finding, 2 strong claim
TIERS = [
    {"suggest": r"suggest(?:s|ed|ing)?", "indicate": r"indicat(?:e|es|ed|ing)",
     "consistent with": r"consistent with", "in line with": r"in line with",
     "point to": r"point(?:s|ed|ing)? to", "may": r"may", "might": r"might", "could": r"could",
     "appear to": r"appear(?:s|ed)? to", "associated with": r"associated with",
     "related to": r"related to", "linked to": r"linked to", "note": r"not(?:e|es|ed)",
     "argue": r"argu(?:e|es|ed|ing)", "tend to": r"tend(?:s|ed)? to"},
    {"find": r"find(?:s|ing)?|found", "show": r"show(?:s|ed|n|ing)?",
     "document": r"document(?:s|ed|ing)?", "report": r"report(?:s|ed|ing)?",
     "estimate": r"estimat(?:e|es|ed|ing)", "observe": r"observ(?:e|es|ed|ing)"},
    {"support ... hypothesis": r"support(?:s|ed|ing)?\s+(?:the|their|this|that|a|an|our)\s+(?:[\w-]+\s+){0,3}"
                               r"(?:hypothesis|hypotheses|view|prediction|predictions|theory|idea)",
     "confirm": r"confirm(?:s|ed|ing)?", "demonstrate": r"demonstrat(?:e|es|ed|ing)",
     "establish": r"establish(?:es|ed|ing)?", "prove": r"prov(?:e|es|ed|en|ing)",
     "cause": r"caus(?:e|es|ed|ing)", "lead to": r"(?:lead(?:s|ing)?|led) to",
     "drive": r"driv(?:e|es|en|ing)|drove", "due to": r"due to", "because of": r"because of",
     # the verb only: "the results in this paper" is a noun
     "attributable to": r"attributable to",
     "result in": r"(?<!the )(?<!our )(?<!these )(?<!those )(?<!their )(?<!its )(?<!of )result(?:s|ed|ing)? in"},
]
TIER_RE = [(t, w, re.compile(r"\b(?:%s)\b" % p)) for t, d in enumerate(TIERS) for w, p in d.items()]


def strength(text):
    """Counter of claim words, and the strongest tier present (-1 for none)."""
    t = re.sub(r"\s+", " ", _rp.CITE_ANY_RE.sub(" ", text)).lower()
    c = Counter()
    for _t, w, rx in TIER_RE:
        n = len(rx.findall(t))
        if n:
            c[w] = n
    top = max((t for t, w, _ in TIER_RE if c[w]), default=-1)
    return c, top


TIER_OF = {w: t for t, w, _ in TIER_RE}


def strength_changes(old_text, new_text, sec_old, sec_new):
    """['STRONGER? +w (a -> b)' / 'HEDGE LOST? -w (a -> b)'] for one block; a
    hedge the whole section still has as often is marked as possibly moved."""
    (co, top), (cn, _) = strength(old_text), strength(new_text)

    def weaker_dropped(t):          # a word below tier t is used less: replaced upward?
        return any(co[x] > cn[x] for x in co if TIER_OF[x] < t)

    def hedges(c):
        return sum(n for x, n in c.items() if TIER_OF[x] == 0)
    fewer_hedges = hedges(cn) < hedges(co)      # one hedge for another is not a loss
    out = []
    for w in sorted(set(co) | set(cn), key=lambda x: (-TIER_OF[x], x)):
        t = TIER_OF[w]
        if t >= 1 and cn[w] > co[w] and (t > max(top, 0) or weaker_dropped(t)):
            out.append("STRONGER? +%s (%d -> %d)" % (w, co[w], cn[w]))
        elif t == 0 and cn[w] < co[w] and fewer_hedges:
            moved = " (the section still has it %d times: moved to another block with a split?)" % sec_new[w] \
                if sec_new[w] >= sec_old[w] else ""
            out.append("HEDGE LOST? -%s (%d -> %d)%s" % (w, co[w], cn[w], moved))
    return out


uneven = 0
flagged = 0
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
    sec_old, sec_new = strength(" ".join(old.values()))[0], strength(" ".join(new.values()))[0]
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
        if k in old:
            for c in strength_changes(old[k], new[k], sec_old, sec_new):
                flagged += 1
                print("  ? %s -- check against the source; keep only if it says this" % c)
        else:
            print("  ? new block: compare its claim words with the snapshot by hand")
    for k in gone:
        print("=== %s   (only in the snapshot)" % label(k))
        for s in sentences(old[k]):
            print("  - %s" % s)
print("\nclaim strength: %s" % ("%d change(s) -- each one checked against its source in h2 (rule 1)" % flagged
                                if flagged else "no change"))
sys.exit(1 if uneven else 0)
