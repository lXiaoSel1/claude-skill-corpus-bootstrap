#!/usr/bin/env python3
"""Measure every register.md rule against the corpus.

WHY THIS EXISTS
    register.md sections 1 and 6 were assertion lists: banned verbs and banned
    phrases with no counts behind them.  Measuring them refuted most of the
    list -- "it is important to note that" is in 24 papers, "not only ... but
    also" in 47, "In this paper, we" in 55.  A skill whose premise is that the
    corpus is the only authority on style cannot carry a style blacklist the
    corpus contradicts.

    This script regenerates references/register-measurements.md's numbers.  It
    is the register-side analogue of draft-section's verb-ladder.md, which
    states its own measurement commands so any figure can be recomputed.

    Read-only.  Writes nothing; prints tables.

THE NOUN/VERB COLLISION
    Section C prints the verbs whose counts are unusable because English plural
    nouns are homographs of third-person verbs: "courts", "rewards", "loads",
    "strips".  Those rows exist to document why the verb ban stays a judgment
    rule.  draft-section's verb-ladder.md recorded the identical failure for
    "(in)?consistent with", where a pattern swallowed the negation and the
    statistic measured its own opposite.

RUN
    py scripts/measure_register.py
    py scripts/measure_register.py --scope term
"""
import argparse
import os
import re
import sys

# Console-safety: a Windows console may not be UTF-8 (e.g. cp936/GBK), and the corpus
# carries U+FFFD in 140 of 165 files (errors="replace" artefacts).  Without
# this, printing a concordance line kills the script mid-report -- measured:
# attest.py died on almost every term, and cohesion.py died AT the M8 line,
# before the JOINS table ever printed.  Never remove.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from textseg import split_sentences, clean_prose  # noqa: E402
SKILL = os.path.dirname(HERE)
CORPUS = os.path.join(SKILL, "references", "corpus")
META = os.path.join(SKILL, "references", "corpus_meta.yaml")

ATTESTED_MIN_PAPERS = 3
# Kept identical to scripts/attest.py.  If these two ever disagree, a phrase
# can be "attested" for a term check and "an AI tell" for a register check in
# the same run.

# --- The items under measurement -------------------------------------------
# Grouped exactly as register-measurements.md reports them.

PHRASES = [
    ("it is important to note that", r"\bit is important to note that\b"),
    ("it is worth noting that", r"\bit is worth noting that\b"),
    ("not only X ... but also Y", r"\bnot only\b[^.]{0,60}\bbut also\b"),
    ("might potentially", r"\bmight potentially\b"),
    ("In this paper, we", r"\bIn this (?:paper|article|study), we\b"),
]

# Sentence-initial openers are counted by SPLITTING INTO SENTENCES, never by
# line anchors.  HISTORY: the first version used (?m)^\s*Moreover, -- but the
# corpus stores a paragraph as ONE line, so ^ saw only each paragraph's first
# sentence and the published counts were 2-9x too low (Moreover 26 papers as
# shipped vs 91 in truth; Additionally 11 vs 37; Furthermore 24 vs 76;
# Notably 8 vs 18; Importantly 5 vs 31).  The R5 conclusion survived -- these
# are register, not AI tells -- but every quoted number was wrong.
SENT_INITIAL = ["Moreover,", "Additionally,", "Furthermore,", "Notably,",
                "Importantly,"]

GLUE = [
    ("as a result", r"\bas a result\b"),
    ("in order to", r"\bin order to\b"),
    ("thereby", r"\bthereby\b"),
]

# Verbs whose plural-noun homograph makes a bare count meaningless.  The third
# column is what sampling found IN THE PARENT (economics) corpus -- printed
# with a [parent sample] tag, because before 2026-10-07 these notes were
# printed as if they described every instance's corpus. Re-sample here with
# `attest.py --all <verb form>` and replace the note when you quote a row.
COLLIDING_VERBS = [
    ("court", r"\b(?:courts|courted|courting)\b",
     "zero verb uses; 'bankruptcy courts', 'District of Columbia Courts'"),
    ("load", r"\b(?:loads|loaded|loading)\b",
     "'loading and unloading of property on aircraft'; 'front-loaded plans'"),
    ("strip", r"\b(?:strips|stripped|stripping)\b",
     "'Asset Stripping' (title); 'stripping out embedded optionality'"),
    ("tilt", r"\b(?:tilts|tilted|tilting)\b",
     "'tilted toward bonds'; 'inverse probability tilting' (estimator)"),
    ("reward", r"\b(?:rewards|rewarded|rewarding)\b",
     "'risks and rewards' -- noun"),
    ("push", r"\b(?:pushes|pushed|pushing)\b",
     "mixed; some genuine metaphor, some headline titles"),
]

RARE_CANDIDATES = [
    ("adjudicate", r"\b(?:adjudicate|adjudicates|adjudicated|adjudicating)\b"),
    ("might potentially", r"\bmight potentially\b"),
    ("loosen", r"\b(?:loosens|loosened|loosening)\b"),
    ("retreat", r"\b(?:retreats|retreated|retreating)\b"),
    ("surface (verb forms)", r"\b(?:surfaced|surfacing)\b"),
]

WHITELIST = [
    "increases", "reduces", "affects", "holds", "limits",
    "creates", "raises", "lowers", "induces",
]


def load_scope(scope):
    """Paper ids for the requested scope, read from the manifest."""
    if not os.path.exists(META):
        sys.exit("missing references/corpus_meta.yaml"
                 "\n  fix: py scripts/build_corpus_meta.py")
    field = "style_safe" if scope == "style" else "terminology_safe"
    ids, cur = [], None
    with open(META, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\s+- id:\s*(\S+)", line)
            if m:
                cur = m.group(1)
                continue
            if cur and re.match(r"\s+%s:\s*true" % field, line):
                ids.append(cur)
                cur = None
    return ids


def measure(texts, total_words, pattern):
    rx = re.compile(pattern, re.I)
    hits = papers = 0
    for t in texts.values():
        n = len(rx.findall(t))
        if n:
            hits += n
            papers += 1
    return hits, papers, (hits / total_words * 10000 if total_words else 0.0)


def table(title, rows, texts, total_words, note_col=False, target=False):
    """Print one measured block.

    `target=True` marks a table where attestation is the GOAL rather than a
    refutation -- the whitelist verbs are supposed to be everywhere.  Labelling
    those "REFUTED" reads as though the corpus disagreed with them, which is
    the opposite of what the number means.
    """
    print(title)
    width = 42 if not note_col else 12
    for row in rows:
        label, pattern = row[0], row[1]
        h, p, r = measure(texts, total_words, pattern)
        if target:
            flag = "attested" if p >= ATTESTED_MIN_PAPERS else "THIN -- check"
        else:
            flag = "REFUTED" if p >= ATTESTED_MIN_PAPERS else "rare"
        if note_col:
            print("  %-12s w=%-6d papers=%-4d %-8s [parent sample] %s"
                  % (label, h, p, flag, row[2]))
        else:
            print("  %-*s w=%-6d papers=%-4d /10k=%6.2f  %s"
                  % (width, label, h, p, r, flag))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["style", "term"], default="style")
    args = ap.parse_args()

    ids = load_scope(args.scope)
    texts = {}
    for k in ids:
        path = os.path.join(CORPUS, k + ".txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                # running prose only: captions, boilerplate and the reference
                # list are not register evidence
                texts[k] = clean_prose(fh.read())
    total_words = sum(len(t.split()) for t in texts.values())
    if not total_words:
        sys.exit("no %s-scope text to measure (0 eligible papers or all text"
                 " cut as non-prose) -- check corpus_meta.yaml denominators"
                 % args.scope)

    print("scope=%s  papers=%d  words=%s  (attested threshold: >=%d papers)\n"
          % (args.scope, len(texts), format(total_words, ","),
             ATTESTED_MIN_PAPERS))

    table("A. Phrases section 6 banned", PHRASES, texts, total_words)

    print("A2. Sentence-initial openers (counted per sentence via the shared splitter)")
    sent_cache = {k: split_sentences(t) for k, t in texts.items()}
    for opener in SENT_INITIAL:
        hits = papers = 0
        for k, sents in sent_cache.items():
            n = sum(1 for x in sents if x.startswith(opener))
            if n:
                hits += n
                papers += 1
        flag = "REFUTED" if papers >= ATTESTED_MIN_PAPERS else "rare"
        print("  %-42s w=%-6d papers=%-4d /10k=%6.2f  %s"
              % (opener + " (sentence-initial)", hits, papers,
                 hits / total_words * 10000, flag))
    print()
    table("B. Explanatory glue section 1 banned", GLUE, texts, total_words)
    table("C. Verbs whose counts are unusable (plural-noun homograph)",
          COLLIDING_VERBS, texts, total_words, note_col=True)
    table("D. Candidates that survived -- genuinely rare",
          RARE_CANDIDATES, texts, total_words)
    table("E. The whitelist, for contrast -- attestation here is the GOAL",
          [(w, r"\b%s\b" % w) for w in WHITELIST], texts, total_words,
          target=True)

    print("Reading the flags: REFUTED means the corpus uses it in >=%d papers,"
          % ATTESTED_MIN_PAPERS)
    print("so flagging it would push the author's prose away from the corpus.")
    print("In table E the same count reads as 'attested': those verbs are the")
    print("positive target, and being everywhere is what makes them the target.")


if __name__ == "__main__":
    main()
