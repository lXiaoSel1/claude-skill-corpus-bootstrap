#!/usr/bin/env python3
"""Steps c / h2 -- every stretch of 7 or more words a cited sentence shares with
the paper it cites, unquoted.

Rule 2(a) exempts a cited paper's own wording up to about six words (a term, a
category, a short result phrase); a longer stretch is quoted with its page or
rebuilt from attested parts. This script finds the longer ones, in the whole
section: words are compared in lower case without punctuation, against the
paper's PDF text (else its lit corpus copy), and a stretch already inside
quotation marks (``...'', "...", \\enquote{...}) is not counted. A sentence
that cites nothing takes the citations of the sentence before it in its
paragraph.

RUN
    py -3 scripts/copy_check.py <section> [section ...] [--min N]
Exit code 1 when an unquoted stretch is found (rewrite it, or quote it with
its page), 2 when it cannot run.
"""
import re
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
MIN = int(_rp._pop(ctx.args, "--min", 7))
if not ctx.args:
    _rp.die(__doc__)
split = ctx.split_sentences()
WORD = re.compile(r"[a-z0-9]+")
QUOTED = re.compile(r"``.*?''|\"[^\"]*\"|“[^”]*”|\\enquote\{[^}]*\}", re.S)
_GRAMS = {}


def grams(key):
    """({MIN-gram: offset in the paper's text}, text) for one cited key."""
    if key not in _GRAMS:
        text, _ = ctx.source_text(key)
        toks = [(m.group(0), m.start()) for m in WORD.finditer(text.lower())] if text else []
        g = {}
        for i in range(len(toks) - MIN + 1):
            g.setdefault(tuple(w for w, _ in toks[i:i + MIN]), toks[i][1])
        _GRAMS[key] = (g, text)
    return _GRAMS[key]


def stretches(words, key):
    g, _ = grams(key)
    out, i, n = [], 0, len(words)
    while i <= n - MIN:
        hit = g.get(tuple(words[i:i + MIN]))
        if hit is None:
            i += 1
            continue
        j = i + MIN
        while j < n and tuple(words[j - MIN + 1:j + 1]) in g:
            j += 1
        out.append((j - i, " ".join(words[i:j]), hit))
        i = j
    return out


found = 0
for sec in ctx.sections(ctx.args):
    print("== %s (%s)" % (sec.key, sec.path))
    for pno, (first, plines) in enumerate(_rp.paragraphs(_rp.section_body(sec)), 1):
        raw = " ".join(re.sub(r"(?<!\\)%.*$", "", t).strip() for t in plines)
        prev = []
        for sno, s in enumerate(_rp.latex_sentences(raw, split), 1):
            keys = []
            for m in _rp.CITE_KEYS_RE.finditer(s):
                keys += [k.strip() for k in m.group(1).split(",") if k.strip() and k.strip() not in keys]
            if keys:
                prev = keys
            else:
                keys = prev
            if not keys:
                continue
            body = _rp.CITE_ANY_RE.sub(" ", QUOTED.sub(" ", s))
            words = WORD.findall(re.sub(r"\\[A-Za-z]+\*?", " ", body).lower())
            for k in keys:
                for n, stretch, off in stretches(words, k):
                    found += 1
                    print("  ¶%d S%d  %d words from %s %s: \"%s\" -- rewrite it, or quote it with its page"
                          % (pno, sno, n, k, ctx.page_label(k, off) or "(corpus copy)", stretch))
print("%d unquoted stretch(es) of %d+ words shared with a cited paper" % (found, MIN))
sys.exit(1 if found else 0)
