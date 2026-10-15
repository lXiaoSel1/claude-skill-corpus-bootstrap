#!/usr/bin/env python3
"""Step d2 -- paragraph openers and sentence-initial connectives of the named
sections, checked against the corpus paragraph openers in {{FIELD}}-draft's
references/records/*.md (the first sentence of every corpus paragraph,
verbatim; built at Tier 3).

The blind spot this targets: the sweep flags only frames found in 0 corpus
papers, so a paragraph-opening frame found in 1-2 papers passes, and L2 sees
only frames used twice. Here every opener is printed for attest.py, and each
sentence-initial connective (the words before the first comma, at most
`opener_max_lead_words`) is counted among corpus paragraph openers. Longer
lead-ins ("After controlling for pre-injury employment,") escape that limit,
so the first three words of every sentence are counted too, and those used
twice or more in a section are listed for attest.py.

RUN
    py -3 scripts/opener_check.py <section> [section ...]
"""
import re
import sys
from collections import Counter

import _rp

ctx = _rp.Ctx(sys.argv)
if not ctx.args:
    _rp.die(__doc__)
split_sentences = ctx.split_sentences()
MAXW = ctx.opts["opener_max_lead_words"]
if 3 not in ctx.built_tiers("draft"):
    _rp.die("opener_check needs the corpus paragraph openers that Tier 3 writes to\n"
            "  %s/references/records/ -- build Tier 3 first (see tier_status.py)." % ctx.draft)
openers = _rp.record_openers(ctx)          # (paper, chapter, sentence)
if not openers:
    _rp.die("no paragraph openers found in %s/references/records/*.md" % ctx.draft)

CITETEXT = re.compile(r"\\citetext\{(?:[^{}]|\{[^{}]*\})*\}")
CITE = _rp.CITE_ANY_RE


def clean(t):
    # citations -> CITE, not a one-letter placeholder: "X. However" reads as
    # an initial to the splitter and two sentences merged into one
    t = re.sub(r"(?<!\\)%.*", "", t)
    t = CITETEXT.sub("CITE", t)
    t = CITE.sub("CITE", t)
    t = t.replace("\\%", "%").replace("\\$", "$").replace("\\&", "&")
    t = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def lead(s):
    """sentence-initial connective: the words before the first comma, if few enough."""
    m = re.match(r"([A-Z][A-Za-z \-]{1,40}?),", s)
    if m and len(m.group(1).split()) <= MAXW:
        return m.group(1)
    return None


def first3(s):
    """The first three words of a sentence (a citation start excluded)."""
    ws = re.findall(r"[A-Za-z][A-Za-z\-']*", s)
    return " ".join(ws[:3]) if len(ws) >= 3 and not s.startswith("CITE") else None


def corpus_count(phrase):
    pat = re.compile(r"^" + re.escape(phrase) + r"\b", re.I)
    hits = [(p, c) for p, c, s in openers if pat.search(s)]
    return len(hits), len({p for p, _ in hits})


print("corpus paragraph openers: %d from %d papers (%s)\n"
      % (len(openers), len({p for p, _, _ in openers}), ", ".join(sorted({c for _, c, _ in openers}))))
for sec in ctx.sections(ctx.args):
    paras = [" ".join(clean(l) for l in pl)
             for _, pl in _rp.paragraphs(_rp.section_body(sec), comment_breaks=True)]
    paras = [p for p in paras if p.strip()]
    print("== %s: %d paragraphs" % (sec.key, len(paras)))
    leads, starts = Counter(), Counter()
    for i, p in enumerate(paras, 1):
        sents = [s for s in split_sentences(p) if len(s.split()) >= 3]
        if not sents:
            print("  ¶%d (no sentence of 3+ words; skipped): %s" % (i, p[:80]))
            continue
        print("  ¶%d OPENER: %s" % (i, sents[0][:150]))
        for s in sents:
            c = lead(s)
            if c and not c.startswith("CITE"):
                leads[c] += 1
            f = first3(s)
            if f:
                starts[f] += 1
    print("  sentence-initial connectives (draft count -> corpus paragraph openers: hits/papers):")
    for c, n in leads.most_common():
        h, pp = corpus_count(c)
        print("    %-40r x%d  ->  %d/%d" % (c, n, h, pp))
    rep = [(f, n) for f, n in starts.most_common() if n >= 2]
    print("  repeated sentence-initial frames (first 3 words, used >= 2 times; attest each with"
          " --scope style):")
    for f, n in rep:
        h, pp = corpus_count(f)
        print("    %-40r x%d  ->  %d/%d" % (f, n, h, pp))
    if not rep:
        print("    none")
    print()
