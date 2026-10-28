"""How many corpus papers use a word or a word sequence -- the whole
paragraph in one pass, for the fast lane's frame and wording checks.

FACTORY PORT (1.6.0) of the parent's `_ngram.py`. The papers are the lit
instance's style-safe set (corpus_meta.yaml, the set `attest.py --scope style`
counts), each read through attest's own text loader (running prose, the
reference list cut); ligatures are folded ("ﬁ" -> "fi") and hyphens and dashes
split words, so "investment-grade" and "investment grade" are one sequence.
Counting is by paper, not by occurrence, as attest.py's range: does.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402

LIT = _jobs.lit_dir() or os.path.normpath(os.path.join(_jobs.corpus_dir(), "..", ".."))
sys.path.insert(0, os.path.join(LIT, "scripts"))
import attest  # noqa: E402  (the lit instance's corpus manifest and eligibility)

LIG = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}
TOK = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+")


def fold(text):
    for a, b in LIG.items():
        text = text.replace(a, b)
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"[-‐-―]", " ", text.lower())


def tokens(text):
    return TOK.findall(fold(text))


_PAPERS = None


def papers(scope="style"):
    """{paper id: token list} of the scope's papers, built once per run."""
    global _PAPERS
    if _PAPERS is None:
        _PAPERS = {}
        for pid in attest.eligible(attest.load_meta(), scope):
            t = attest._text(pid, False)
            if t:
                _PAPERS[pid] = tokens(t)
    return _PAPERS


def df(grams):
    """{gram (tuple of tokens): number of papers that contain it}."""
    grams = {tuple(g) for g in grams if g}
    out = {g: 0 for g in grams}
    if not grams:
        return out
    first = {}
    for g in grams:
        first.setdefault(g[0], set()).add(len(g))
    for toks in papers().values():
        seen = set()
        n = len(toks)
        for i, w in enumerate(toks):
            lens = first.get(w)
            if not lens:
                continue
            for k in lens:
                g = tuple(toks[i:i + k]) if i + k <= n else None
                if g in grams:
                    seen.add(g)
        for g in seen:
            out[g] += 1
    return out


def n_papers():
    return len(papers())
