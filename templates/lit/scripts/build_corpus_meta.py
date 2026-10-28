#!/usr/bin/env python3
"""Build references/corpus_meta.yaml -- the admission manifest for the corpus.

WHY THIS EXISTS
    Before this manifest, a "0 hits" verdict had four indistinguishable causes:
    the term is genuinely absent; the query was silently truncated; the term IS
    present but the file's PDF extraction is damaged so it cannot match; or the
    term sits in one of six byte-identical duplicate files and got counted
    twice.  The manifest makes eligibility explicit so every verdict can report
    n_attesting / n_eligible honestly.

    Read-only with respect to the corpus.  Writes exactly one file:
    references/corpus_meta.yaml.

DAMAGE MODES (measured, not assumed -- thresholds justified below)
    ligature_dropped   "de ned bene t" for "defined benefit"  CoronadoLiang2006
    ligature_replaced  every fi/fl became U+FFFD              Romaniuk2021
    spacing_lost       inter-word spaces gone, giant tokens   PennacchiLewis1994
    column_interleaved two columns read row-by-row: alternating
                       column lines, each followed by a blank  a health-policy paper (AJIM)
                                                              DonelsonYust2017

RUN
    py -3 scripts/build_corpus_meta.py
"""
import hashlib
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

from collections import defaultdict
from datetime import date

import json

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CORPUS = os.path.join(SKILL, "references", "corpus")
OUT = os.path.join(SKILL, "references", "corpus_meta.yaml")
SOURCES = os.path.join(SKILL, "references", "corpus_sources.json")

import _fieldconfig  # noqa: E402
import textseg  # noqa: E402  (interleave_ratio)

# The manuscript, consulted only to decide which member of a byte-identical
# alias group should be the canonical one.  See pick_canonical below.
# was hardcoded to the parent's
# ../../../<manuscript>/main.tex (a path that existed on the parent's
# machine, so the wrong manuscript was read silently). Now field-config's
# manuscript_tex, absolute or relative to the project root; empty = none.
_ms = _fieldconfig.manuscript_tex()
MANUSCRIPT = _ms \
    if _ms else ""

# A text this short is not a paper whatever its extraction verdict: an
# image-only scan, a landing page, an abstract. It is never alias-grouped
# (two empty scans are byte-identical without being the same document).
MIN_WORDS_READABLE = 300

# --- Thresholds -------------------------------------------------------------
# Each is a CATEGORICAL test, not a tuned cutoff.  Rationale is mandatory: an
# unexplained constant is a constant nobody can revise later.

NO_FI_MIN_WORDS = 2000
# An English research paper over 2000 words in which the fi-ligature appears
# in NO form -- neither the ASCII pair "fi" ("first", "find", "significant")
# nor the Unicode ligature U+FB01 -- has had its ligatures mapped to something
# else during extraction.  Both forms count: see the "fi" metric.  Measured in
# the parent: Romaniuk2021 had zero of either across 11,920 words, its
# ligatures having become U+FFFD; no other file came close.

BROKEN_WORDS_PER_10K = 10
# The dropped-ligature signature: "de ned", "bene t", "signi cant", "rms".
# Measured: CoronadoLiang2006 = 47.9 per 10k; every other file = 0.0.  The
# threshold sits an order of magnitude below the single true positive.

LONG_TOKENS_PER_10K = 10
# Alphabetic tokens longer than LONG_TOKEN_CHARS mean inter-word spaces were
# lost.  Measured: PennacchiLewis1994 = 29.2, DonelsonYust2017 = 20.4, then a
# gap down to Ederington1974 = 8.5 which spot-checks as legitimate long words.

LONG_TOKEN_CHARS = 28
# "counterintuitively" is 18 characters, "institutionalization" is 20.  28 is
# past the longest ordinary English word in this corpus and well below the
# run-together fragments the damaged files produce.

# In-word U+FFFD is RECORDED per paper but is deliberately NOT a gate.  Its
# distribution across the 165 files is continuous -- P50 1.8, P75 6.7, P90
# 14.9, P95 27.4, max 65.4 per 10k -- with no natural break, and the
# overwhelming majority of U+FFFD here is legitimate symbol substitution:
# en-dashes in page ranges, copyright signs, plus-minus, accented author names.
# DonelsonYust2017 carries 1,903 U+FFFD of which exactly 2 sit inside a word.
# Gating on it would exclude roughly 100 sound papers to catch one that the
# fi==0 test already catches.

# Documents that are terminology or institutional references rather than
# research papers.  Legitimate sources for what a term MEANS, but they must not
# be sampled for research-prose style.  Declared in field-config.yaml
# (terminology_only:), reviewed at Tier 0 acceptance -- the parent hardcoded
# six pension reference documents here.  `excluded:` keys leave BOTH samples
# (abstract-only entries, scans nobody OCR'd).
TERMINOLOGY_ONLY = _fieldconfig.terminology_only()
EXCLUDED = _fieldconfig.excluded()
# 1.6.0: review and survey articles (field-config `reviews:`) -- terminology
# yes, style sample no; their role says why.
REVIEWS = _fieldconfig.reviews()

# Per-paper citation culture (mixed corpora: economics author-year beside
# medicine numeric/superscript). Measured, per 10k words, on the text before
# the reference list; recorded so measurements can be split by culture.
CITE_AY_RE = re.compile(r"\([^()]{0,120}?(?:1[89]|20)\d{2}[a-z]?\)"
                        r"|[A-Z][A-Za-z'\-]+(?: et al\.)?\s\((?:1[89]|20)\d{2}")
CITE_BRACKET_RE = re.compile(r"\[\d{1,3}(?:[,–\-]\s*\d{1,3})*\]")
CITE_SUP_RE = re.compile(r"(?<=[a-z\)])[.,;]?\d{1,3}(?:[,–\-]\d{1,3})*(?=\s[A-Z])")
REFS_HEAD_RE = re.compile(r"^\s*(?:References|REFERENCES|Bibliography|"
                          r"Literature Cited|Works Cited)\s*$", re.M)

BROKEN_RE = re.compile(
    r"\b(?:bene|signi|classi|identi|speci|justi|con|de|ef|suf|pro)"
    r"\s+(?:t|ts|cant|cantly|ed|rm|ne|ned|ciency|cient|dence)\b"
)
INWORD_FFFD_RE = re.compile("[A-Za-z]�[A-Za-z]")


def measure(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        s = fh.read()
    toks = s.split()
    n = len(toks) or 1
    long_toks = sum(1 for t in toks if len(t) > LONG_TOKEN_CHARS and t.isalpha())
    il_ratio, il_lines = textseg.interleave_ratio(s)
    return {
        "words": len(toks),
        "sha256": hashlib.sha256(s.encode("utf-8", "replace")).hexdigest(),
        # Counts the fi-ligature in EITHER surviving form: the ASCII pair
        # "fi", or the Unicode ligature U+FB01 / U+FB03 that a
        # LaTeX-produced PDF legitimately yields.  Counting only the
        # ASCII pair mis-flagged 11 of 27 clean papers in a mathematics
        # instance (2026-08-28): modern maths PDFs preserve U+FB01, so
        # zero ASCII "fi" is normal there, not damage.
        "fi": (len(re.findall(r"fi", s))
               + s.count("ﬁ") + s.count("ﬃ")),
        "fl": len(re.findall(r"fl", s)),
        "broken_per10k": len(BROKEN_RE.findall(s)) / n * 10000,
        "longtok_per10k": long_toks / n * 10000,
        "inword_fffd_per10k": len(INWORD_FFFD_RE.findall(s)) / n * 10000,
        "citation_style": cite_style(s),
        "interleave": round(il_ratio, 3),
        "interleave_lines": il_lines,
    }


def cite_style(s):
    """'author-year' | 'numeric' | 'unclear', from citation-marker density in
    the body (text before the last References heading)."""
    heads = list(REFS_HEAD_RE.finditer(s))
    body = s[:heads[-1].start()] if heads else s
    n = len(body.split()) or 1
    per10k = lambda rx: len(rx.findall(body)) / n * 10000
    bracket = per10k(CITE_BRACKET_RE)
    ay = per10k(CITE_AY_RE)
    sup = per10k(CITE_SUP_RE)
    # Tiered, because footnote markers in economics papers flatten into the
    # same "sentence.12 Next" shape as medical superscript citations: a
    # bracket citation is unambiguous; otherwise a dense author-year culture
    # wins; only then are superscripts read as citations.
    if bracket >= 5:
        return "numeric"
    if ay >= 10:
        return "author-year"
    if sup >= 10:
        return "numeric"
    return "unclear"


def load_sources():
    """Ingest provenance (corpus_sources.json): converter, flags, group, role.
    Absent for corpora built before 2026-10-07 -- then every lookup is {}."""
    try:
        with open(SOURCES, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def cited_keys():
    """Cite-keys the manuscript actually uses.  Empty set if it is unreadable.

    Only ever used as a tie-break for canonical selection, so an unreadable
    manuscript degrades to alphabetical order rather than failing the build.
    """
    if not MANUSCRIPT:
        print("note: no manuscript_tex in field-config.yaml -- canonical alias"
              " ids use alphabetical order (normal before onboarding).")
        return set()
    try:
        with open(MANUSCRIPT, encoding="utf-8", errors="replace") as fh:
            tex = fh.read()
    except OSError:
        print("WARNING: manuscript unreadable at %s -- canonical alias ids"
              " fall back to alphabetical order, which is known to flip 4 of"
              " 6 groups. Fix the path before trusting this rebuild."
              % MANUSCRIPT, file=sys.stderr)
        return set()
    keys = set()
    # natbib and biblatex commands; same pattern as -polish/scripts/manuscript.py
    for m in re.finditer(r"\\(?!nocite\b|citetext\b)[A-Za-z]*[Cc]ite[A-Za-z]*\*?(?:\[[^\]]*\])*"
                         r"\{([^}]*)\}", tex):
        for k in m.group(1).split(","):
            k = k.strip()
            if k:
                keys.add(k)
    # Markdown/pandoc manuscripts: [@key], @key
    for m in re.finditer(r"@([A-Za-z0-9][A-Za-z0-9_:\-]*)", tex):
        keys.add(m.group(1))
    return keys


def pick_canonical(keys, cited):
    """Choose which member of a byte-identical group is the canonical id.

    Prefer the key the manuscript cites.  This is not cosmetic.  A dedup pass
    that picks alphabetically will report evidence under a cite-key the paper
    does not use, and the author cannot cite what the verdict names --
    draft-section's sample.md records the same trap costing it two papers
    (NovyMarx2015 and CurrieGruber1996 were dropped, and the manuscript cited
    exactly those).  Measured here: 4 of 6 groups have a different canonical
    under the two rules.  Ties and no-citation groups fall back to alphabetical
    so the build stays deterministic.
    """
    keys = sorted(keys)
    hits = [k for k in keys if k in cited]
    return hits[0] if hits else keys[0]


def classify(m, src=None):
    """Return the primary extraction verdict.  Order matters.

    scans were labelled "clean" -- every damage test
    needs words, and an image-only PDF yields almost none, so it fell through
    to the default and entered the style sample. Ingest's SCAN flag (words per
    page) and a near-empty text are now verdicts of their own."""
    flags = (src or {}).get("flags", [])
    if "ERROR" in flags:
        return "conversion_failed"
    if "SCAN" in flags or m["words"] < MIN_WORDS_READABLE:
        return "scan_or_empty"
    if m["words"] > NO_FI_MIN_WORDS and m["fi"] == 0:
        return "ligature_replaced"
    if m["broken_per10k"] >= BROKEN_WORDS_PER_10K:
        return "ligature_dropped"
    if m["longtok_per10k"] >= LONG_TOKENS_PER_10K:
        return "spacing_lost"
    if (m.get("interleave_lines", 0) >= textseg.INTERLEAVE_MIN_LINES
            and m.get("interleave", 0) >= textseg.INTERLEAVE_MIN):
        # re-extract: ingest.py --map ... --force KEY --converter pymupdf
        return "column_interleaved"
    return "clean"


def main():
    if not os.path.isdir(CORPUS):
        sys.exit("corpus not found: " + CORPUS)

    sources = load_sources()
    rec = {}
    for f in sorted(x for x in os.listdir(CORPUS) if x.endswith(".txt")):
        m = measure(os.path.join(CORPUS, f))
        m["src"] = sources.get(f[:-4], {})
        m["extraction"] = classify(m, m["src"])
        rec[f[:-4]] = m
    unknown = sorted((TERMINOLOGY_ONLY | EXCLUDED) - set(rec))
    if unknown:
        print("WARNING: field-config lists keys with no corpus file "
              "(typo, or comment kept as part of a key?): %s" % unknown,
              file=sys.stderr)

    # Alias groups: byte-identical files share one sha256.  NORMALISE, never
    # delete.  draft-section's sample.md records why -- a dedup pass once
    # dropped NovyMarx2015 and CurrieGruber1996, and the manuscript cites
    # exactly those keys.  The canonical member is chosen by pick_canonical
    # (manuscript-cited key wins; alphabetical only as the tie-break);
    # the rest carry alias_of and are excluded from denominators.
    cited = cited_keys()
    by_hash = defaultdict(list)
    for k, m in rec.items():
        # near-empty texts are never grouped: two blank scans hash alike
        # without being the same document
        h = m["sha256"] if m["words"] >= MIN_WORDS_READABLE else "solo:" + k
        by_hash[h].append(k)
    canonical = {}
    for keys in by_hash.values():
        keys.sort()
        canon = pick_canonical(keys, cited)
        for k in keys:
            canonical[k] = canon

    n_files = len(rec)
    distinct = [k for k in rec if canonical[k] == k]
    damaged = {k for k in distinct if rec[k]["extraction"] != "clean"}
    term_safe = [k for k in distinct if k not in damaged and k not in EXCLUDED]
    style_safe = [k for k in term_safe if k not in TERMINOLOGY_ONLY and k not in REVIEWS]

    def role(k):
        if k in EXCLUDED:
            return "excluded"
        if k in TERMINOLOGY_ONLY:
            return "terminology_reference"
        if k in REVIEWS:
            return "review_article"
        return "research_paper"

    L = []
    add = L.append
    add("# corpus_meta.yaml -- admission manifest for the %s-lit corpus."
        % _fieldconfig.field())
    add("#")
    add("# GENERATED FILE. Do not hand-edit -- rerun scripts/build_corpus_meta.py.")
    add("#")
    add("# Every attestation verdict must quote a denominator from this file, never")
    add("# the bare file count (%d here): the file count includes byte-identical"
        % n_files)
    add("# duplicates, damaged extractions, excluded entries and reference-only")
    add("# documents, none of which can attest research-prose usage.")
    add("")
    add("schema_version: 2")
    add("generated: " + date.today().isoformat())
    add("generator: scripts/build_corpus_meta.py")
    add("")
    add("denominators:")
    add("  files: %d                # .txt files on disk" % n_files)
    add("  distinct: %d             # after alias-normalising byte-identical duplicates"
        % len(distinct))
    add("  terminology_safe: %d     # distinct minus extraction-damaged and excluded -- USE THIS for term verdicts"
        % len(term_safe))
    add("  style_safe: %d           # terminology_safe minus non-research reference documents and review articles"
        % len(style_safe))
    add("")
    add("thresholds:")
    add("  no_fi_min_words: %d" % NO_FI_MIN_WORDS)
    add("  broken_words_per_10k: %d" % BROKEN_WORDS_PER_10K)
    add("  long_tokens_per_10k: %d" % LONG_TOKENS_PER_10K)
    add("  long_token_chars: %d" % LONG_TOKEN_CHARS)
    add("  # in-word U+FFFD is recorded per paper but is NOT a gate; the rationale")
    add("  # block in scripts/build_corpus_meta.py explains why.")
    add("")
    add("alias_groups:")
    add("  # Byte-identical files. The canonical id is the one the manuscript")
    add("  # cites, not the alphabetically first -- evidence reported under a")
    add("  # cite-key the paper does not use cannot be cited by the author.")
    for g in sorted(sorted(v) for v in by_hash.values() if len(v) > 1):
        canon = canonical[g[0]]
        rest = [k for k in g if k != canon]
        add("  - canonical: " + canon)
        add("    aliases: [" + ", ".join(rest) + "]")
        add("    cited_in_manuscript: " + str(canon in cited).lower())
    add("")
    add("papers:")
    for k in sorted(rec):
        m = rec[k]
        is_canon = canonical[k] == k
        clean = m["extraction"] == "clean"
        add("  - id: " + k)
        add("    sha256: " + m["sha256"][:16])
        add("    words: %d" % m["words"])
        if not is_canon:
            add("    alias_of: " + canonical[k])
        add("    role: " + role(k))
        src = m["src"]
        if src.get("group"):
            add("    group: " + src["group"])
        if src.get("role"):
            add("    source_role: " + src["role"])
        add("    citation_style: " + m["citation_style"])
        add("    extraction: " + m["extraction"])
        if src.get("converter"):
            add("    converter: " + src["converter"])
        if src.get("flags"):
            add("    ingest_flags: [" + ", ".join(src["flags"]) + "]")
        add("    terminology_safe: "
            + str(is_canon and clean and k not in EXCLUDED).lower())
        add("    style_safe: "
            + str(is_canon and clean and role(k) == "research_paper").lower())
        if not clean:
            add("    damage_metrics: {fi: %d, fl: %d, broken_per10k: %.1f, "
                "longtok_per10k: %.1f}"
                % (m["fi"], m["fl"], m["broken_per10k"], m["longtok_per10k"]))
        add("    inword_fffd_per10k: %.1f" % m["inword_fffd_per10k"])

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")

    print("wrote " + os.path.relpath(OUT, SKILL))
    print("  files            %d" % n_files)
    print("  distinct         %d  (%d alias-normalised)"
          % (len(distinct), n_files - len(distinct)))
    print("  terminology_safe %d" % len(term_safe))
    print("  style_safe       %d" % len(style_safe))
    print("  extraction-damaged (%d):" % len(damaged))
    for k in sorted(damaged):
        print("    %-26s %s" % (k, rec[k]["extraction"]))
    styles = defaultdict(int)
    for k in style_safe:
        styles[rec[k]["citation_style"]] += 1
    print("  style_safe citation cultures: %s" % dict(styles))
    short = [k for k in distinct if "SHORT" in rec[k]["src"].get("flags", [])
             and k not in TERMINOLOGY_ONLY | EXCLUDED]
    if short:
        print("  SHORT texts still in the style sample (decide at Tier 0:"
              " terminology_only or excluded?): %s" % short)


if __name__ == "__main__":
    main()
