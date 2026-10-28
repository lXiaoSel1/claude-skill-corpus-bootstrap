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

ONE CHAPTER (1.6.0)
    --section <job> measures the register of ONE chapter from the draft
    instance's slices (after Tier 2), style-safe papers only: sentence length,
    citations per sentence, narrative vs parenthetical citations, the verb
    after a narrative citation ("Smith (2019) finds"), sentence-initial
    contrast and addition connectors, "consistent with", and hedges. These are
    the chapter's own numbers for a review of one of its paragraphs -- the
    whole-corpus counts above mix every chapter.

RUN
    py -3 scripts/measure_register.py
    py -3 scripts/measure_register.py --scope term
    py -3 scripts/measure_register.py --section <job>
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
                 "\n  fix: py -3 scripts/build_corpus_meta.py")
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


# ---- one chapter (1.6.0) ---------------------------------------------------
_NAME = r"[A-Z][A-Za-z'’\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z'’\-]+|\s+et\s+al\.?)?"
NARRATIVE = re.compile(r"\b" + _NAME + r"(?:'s|’s)?\s*\(\s*(?:19|20)\d{2}[a-z]?(?:\s*,\s*(?:19|20)\d{2}[a-z]?)*\s*\)")
NARR_VERB = re.compile(r"\b" + _NAME + r"\s*\(\s*(?:19|20)\d{2}[a-z]?\s*\)\s+(?:also\s+|further\s+|similarly\s+)?([a-z]+)")
PAREN = re.compile(r"\((?:e\.g\.,?\s*|see\s+)?[^()]*?[A-Z][A-Za-z'’\-]+[^()]*?,?\s*(?:19|20)\d{2}[a-z]?[^()]*\)")
BRACKET = re.compile(r"\[\d{1,3}(?:\s*[,–\-]\s*\d{1,3})*\]")
CONNECTORS = ["However,", "In contrast,", "By contrast,", "On the other hand,", "Similarly,",
              "Likewise,", "Moreover,", "Furthermore,", "In addition,", "Additionally,",
              "Consistent with", "Building on", "Following", "Although", "While", "Yet,",
              "Nevertheless,", "More recently,", "Recently,", "Prior", "Previous", "Another strand",
              "A related", "Several", "Early", "Earlier"]
HEDGES = [("may", r"\bmay\b"), ("might", r"\bmight\b"), ("could", r"\bcould\b"),
          ("suggest(s/ed)", r"\bsuggest(?:s|ed)?\b"), ("appear(s) to", r"\bappears? to\b"),
          ("likely", r"\blikely\b"), ("tend(s) to", r"\btends? to\b"), ("potentially", r"\bpotentially\b")]


def _q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))] if xs else 0


def section_report(job):
    import _fieldconfig
    root = _fieldconfig.draft_slices_dir()
    d = os.path.join(root, job) if root else ""
    if not d or not os.path.isdir(d):
        sys.exit("no slices for %r (Tier 2 builds them in the draft instance's references/slices/)" % job)
    safe = set(load_scope("style"))
    from textseg import paragraph_texts
    paras = []
    for f in sorted(os.listdir(d)):
        key = f[:-4]
        if not f.endswith(".txt") or f.startswith("_") or (safe and key not in safe):
            continue
        with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
            text = "\n".join(l for l in fh.read().split("\n") if not l.startswith("====="))
        paras += [(key, p) for p in paragraph_texts(text)]
    if not paras:
        sys.exit("no style-safe paragraphs in slices/%s" % job)
    papers = sorted({k for k, _ in paras})
    sents = [(k, s) for k, p in paras for s in split_sentences(p)]
    words = sum(len(s.split()) for _, s in sents)
    slen = [len(s.split()) for _, s in sents]
    print("section=%s  papers=%d  paragraphs=%d  sentences=%d  words=%s  (style-safe only)\n"
          % (job, len(papers), len(paras), len(sents), format(words, ","), ))

    print("S1. Sentence length: P25 %d · P50 %d · P75 %d · P90 %d words"
          % (_q(slen, .25), _q(slen, .5), _q(slen, .75), _q(slen, .9)))
    narr = sum(len(NARRATIVE.findall(s)) for _, s in sents)
    paren = sum(len(PAREN.findall(s)) for _, s in sents)
    brk = sum(len(BRACKET.findall(s)) for _, s in sents)
    cited = sum(1 for _, s in sents if NARRATIVE.search(s) or PAREN.search(s) or BRACKET.search(s))
    print("S2. Citations: narrative %d · parenthetical %d · bracket %d  -> narrative share %.0f%%;"
          " sentences with a citation %.0f%%; per 10k words %.1f"
          % (narr, paren, brk, 100.0 * narr / max(1, narr + paren), 100.0 * cited / len(sents),
             (narr + paren + brk) / float(words) * 10000))

    verbs, vpapers = {}, {}
    for k, s in sents:
        for v in NARR_VERB.findall(s):
            verbs[v] = verbs.get(v, 0) + 1
            vpapers.setdefault(v, set()).add(k)
    top = sorted(verbs.items(), key=lambda kv: (-kv[1], kv[0]))[:18]
    print("\nS3. The word after a narrative citation (\"Smith (2019) ___\") -- top %d of %d forms"
          % (len(top), len(verbs)))
    for v, n in top:
        print("  %-14s %4d uses  %3d papers" % (v, n, len(vpapers[v])))

    print("\nS4. Sentence-initial connectors (share of the chapter's sentences)")
    for c in CONNECTORS:
        hits = [k for k, s in sents if s.startswith(c)]
        if hits:
            print("  %-22s %4d sentences (%.1f%%)  %3d papers"
                  % (c, len(hits), 100.0 * len(hits) / len(sents), len(set(hits))))
    cw = [k for k, s in sents if re.search(r"\bconsistent with\b", s, re.I)]
    print("  %-22s %4d sentences (%.1f%%)  %3d papers   (anywhere in the sentence)"
          % ("consistent with", len(cw), 100.0 * len(cw) / len(sents), len(set(cw))))

    print("\nS5. Hedges (per 10k words of the chapter)")
    for label, pat in HEDGES:
        rx = re.compile(pat, re.I)
        n = sum(len(rx.findall(s)) for _, s in sents)
        ps = len({k for k, s in sents if rx.search(s)})
        print("  %-16s %4d  /10k=%5.1f  %3d papers" % (label, n, n / float(words) * 10000, ps))
    print("\nRead these as the chapter's norms for ONE paragraph's review: a draft far from them is a"
          " question for judgment, never a rule.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["style", "term"], default="style")
    ap.add_argument("--section")
    args = ap.parse_args()
    if args.section:
        section_report(args.section)
        return

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
