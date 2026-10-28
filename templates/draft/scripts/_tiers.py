"""Claim strength in three tiers -- hedges, findings, strong claims -- for the
fast lane's strength check (para_check.py) and the evidence cards' profile.

The tiers are the ones the <field>-polish instance uses in `sent_diff.py`
(factory 1.5.0), copied here so the draft instance runs without a polish
instance (factory 1.6.0 port of the parent's fast lane). A sentence that reports a paper's result is compared with the
paper's own lines: a word above their strongest tier, or a hedge they all
carry and the sentence drops, is listed for the drafter to check.
"""
import re
from collections import Counter

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
TIER_OF = {w: t for t, w, _ in TIER_RE}
NAMES = ("hedge", "finding", "strong")


def strength(text):
    """(Counter of claim words, strongest tier present or -1)."""
    t = re.sub(r"\s+", " ", text).lower()
    c = Counter()
    for _t, w, rx in TIER_RE:
        n = len(rx.findall(t))
        if n:
            c[w] = n
    top = max((TIER_OF[w] for w in c), default=-1)
    return c, top


def profile(c):
    """'hedge: suggest x2, may x1 · finding: find x3' for a Counter."""
    parts = []
    for t, name in enumerate(NAMES):
        ws = ["%s x%d" % (w, n) for w, n in sorted(c.items()) if TIER_OF[w] == t]
        if ws:
            parts.append("%s: %s" % (name, ", ".join(ws)))
    return " · ".join(parts) or "no claim words"


def compare(sentence, source_lines):
    """Flags for a sentence against the source lines it rests on."""
    cs, top_s = strength(sentence)
    cl, top_l = strength(" ".join(source_lines))
    out = []
    # a line that states its result plainly ("there is no evidence that ...") reports
    # a finding: "X finds" is not stronger than it
    base = top_l if top_l >= 0 else 1
    if top_s > base:
        up = sorted(w for w in cs if TIER_OF[w] == top_s)
        out.append("STRONGER? %s (%s) -- the paper's own lines go no higher than %s (%s)"
                   % (", ".join(up), NAMES[top_s], NAMES[base], profile(cl)))
    hedges_l = [w for w in cl if TIER_OF[w] == 0]
    if top_l == 0 and hedges_l and not any(TIER_OF[w] == 0 for w in cs):
        out.append("HEDGE LOST? the paper only says %s; the sentence drops it" % ", ".join(sorted(hedges_l)))
    return out
