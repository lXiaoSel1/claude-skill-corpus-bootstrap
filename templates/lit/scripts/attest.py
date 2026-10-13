#!/usr/bin/env python3
"""Attest a term or phrase against this lit instance's corpus.

FACTORY FIXES 2026-10-07 (each was a measured silent under-count):
  * straight and curly apostrophes are the same character class -- a typed
    "workers' compensation" never matched the U+2019 most PDFs carry;
  * whitespace inside a phrase matches any whitespace run, so a phrase
    wrapped across a line break in the extracted text still counts;
  * EVERY variant runs and hits are UNIONED (by position) -- the old loop
    returned the first variant with any hit, so a literal form found in one
    paper hid the same phrase hyphenated or wrapped in three others;
  * British/American spelling variants (-ise/-ize, -isation/-ization,
    -our/-or, -yse/-yze, centre/center, ae/e) are tried;
  * reference lists and captions are cut before searching (textseg.
    clean_prose; --include-refs restores them) -- bibliography entries used
    to be counted as usage;
  * range is split into research papers vs reference documents
    (terminology_only); a term carried only by reference documents is
    REFERENCE-ONLY, not ATTESTED.

WHY THIS EXISTS -- the bug it makes impossible
    The skill used to ask the model to hand-write one batched Grep per run,
    alternating several terms into a single pattern.  Measured failure: the
    term "monotonic" occurs in 32 papers, but inside a six-term alternation its
    first hit lands at position 379 of the result stream, past the Grep tool's
    default head_limit of 250.  The term was reported as 0 hits across 165
    papers and refused on that basis.  The query looked like it succeeded.

    Three properties here make that class of failure structural rather than
    incidental:

      1. ONE TERM PER SEARCH. Terms are never alternated together, so a common
         term cannot crowd out a rare one.
      2. COUNTING IS SEPARATE FROM DISPLAY. Totals are computed over the whole
         corpus first; the concordance is capped afterwards and the cap is
         always announced ("showing 8 of 42, 34 not shown").  A truncated
         display can never be mistaken for a small count.
      3. A ZERO IS RETRIED, LOUDLY. Zero hits for the literal form triggers an
         automatic widened pass over spelling variants, and the report says
         which variants were tried.  A bare zero is never returned without
         evidence that the widened pass also found nothing.

    Read-only.  Writes nothing.

DENOMINATORS
    Verdicts quote references/corpus_meta.yaml, never the raw file count.
    "0 hits across 165 papers" counts six byte-identical duplicates and four
    files whose extraction is too damaged for a present term to match.

RANGE, NOT RAW FREQUENCY
    The headline number is `range` -- how many distinct papers contain the
    term -- not the raw hit count.  Gries (2008), "Dispersions and adjusted
    frequencies in corpora": raw frequency misleads because it cannot tell a
    term used once by forty authors from a term used forty times by one.  For
    the binary question this skill asks -- is this phrasing part of the
    literature's register -- range is the right measure and, unlike DP, is not
    entangled with relative frequency.

RUN
    py scripts/attest.py "funding ratio" "de-risking"
    py scripts/attest.py --all "monotonically"        # full concordance
    py scripts/attest.py --scope style "risk shifting"
    py scripts/attest.py --json "moral hazard"
"""
import argparse
import json
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
SKILL = os.path.dirname(HERE)
CORPUS = os.path.join(SKILL, "references", "corpus")
META = os.path.join(SKILL, "references", "corpus_meta.yaml")
sys.path.insert(0, HERE)
import textseg  # noqa: E402

APOS = "['’‘ʼ`]"
# every apostrophe-like character a PDF or a keyboard produces


def _lit_pattern(term):
    """Escape a literal term; apostrophes match any apostrophe form and
    internal whitespace matches any whitespace run (line wraps)."""
    out = []
    for ch in term.strip():
        if ch in "'’‘ʼ`":
            out.append(APOS)
        elif ch.isspace():
            if not out or out[-1] != r"\s+":
                out.append(r"\s+")
        else:
            out.append(re.escape(ch))
    return "".join(out)


_SPELL = [(r"isation", "ization"), (r"ization", "isation"),
          (r"ise\b", "ize"), (r"ize\b", "ise"), (r"ised\b", "ized"),
          (r"ized\b", "ised"), (r"ising\b", "izing"), (r"izing\b", "ising"),
          (r"yse\b", "yze"), (r"yze\b", "yse"), (r"our\b", "or"),
          (r"centre", "center"), (r"center", "centre"),
          (r"paed", "ped"), (r"haem", "hem"), (r"oe(?=sophag|dema)", "e")]


def spelling_variant(term):
    """One British<->American swap of the term (first rule that changes it),
    or None. Applied word by word."""
    words = term.split()
    changed = False
    for i, w in enumerate(words):
        for pat, rep in _SPELL:
            nw = re.sub(pat, rep, w)
            if nw != w and len(w) > 4:
                words[i], changed = nw, True
                break
    return " ".join(words) if changed else None

KWIC_WINDOW = 60
KWIC_DEFAULT_CAP = 8
# The cap exists only to keep a report readable.  It is applied after counting
# and is always reported, so it can never be confused with the true total.

ATTESTED_MIN_PAPERS = 3
# A term is attested when at least three distinct eligible papers use it.
# Corpus-linguistics practice puts minimum frequency thresholds for collocation
# work at 3-10 occurrences; 3 is the low end, chosen because the question here
# is existence-in-register rather than collocation strength, and because a
# phrase carried by three independent author teams is no longer one author's
# habit.  Raising it would silently reclassify attested terms, so it lives here
# with its rationale rather than inline at the comparison.


def load_meta():
    """Parse corpus_meta.yaml.

    Uses PyYAML when present.  Falls back to a small parser for the exact shape
    build_corpus_meta.py emits, so this script has no hard dependency: a
    missing package must not be able to stop an attestation.
    """
    if not os.path.exists(META):
        sys.exit(
            "missing " + os.path.relpath(META, SKILL)
            + "\n  fix: py scripts/build_corpus_meta.py"
        )
    try:
        import yaml
        with open(META, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except ImportError:
        pass

    data = {"denominators": {}, "papers": [], "alias_groups": []}
    cur = None
    with open(META, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if re.match(r"^denominators:", line):
                cur = "den"
                continue
            if re.match(r"^papers:", line):
                cur = "papers"
                continue
            if re.match(r"^[a-z_]+:", line):
                cur = None
                continue
            if cur == "den":
                m = re.match(r"\s+([a-z_]+):\s*(\d+)", line)
                if m:
                    data["denominators"][m.group(1)] = int(m.group(2))
            elif cur == "papers":
                m = re.match(r"\s+- id:\s*(\S+)", line)
                if m:
                    data["papers"].append({"id": m.group(1)})
                elif data["papers"]:
                    m = re.match(r"\s+([a-z_0-9]+):\s*(.+)", line)
                    if m:
                        k, v = m.group(1), m.group(2).strip()
                        if v in ("true", "false"):
                            v = v == "true"
                        elif re.fullmatch(r"\d+", v):
                            v = int(v)
                        data["papers"][-1][k] = v
    return data


def eligible(meta, scope):
    """Return {paper_id: word_count} for the requested scope."""
    field = {
        "term": "terminology_safe",
        "style": "style_safe",
    }.get(scope)
    out = {}
    for p in meta["papers"]:
        if field is None:
            if p.get("alias_of") or p.get("role") == "excluded":
                continue
        elif not p.get(field):
            continue
        out[p["id"]] = p.get("words", 0)

    return out


def reference_ids(meta):
    """Papers whose role is terminology_reference (agency reports etc.)."""
    return {p["id"] for p in meta["papers"]
            if p.get("role") == "terminology_reference"}


def variants(term):
    """Spelling variants to try, in order, each with a label.

    The widened pass is what turns a silent miss into a reported one.  Every
    variant that is actually distinct from the literal form gets tried and
    named in the report.
    """
    out = [(_lit_pattern(term), "literal")]
    t = term.strip()
    sv = spelling_variant(t)
    if sv:
        out.append((_lit_pattern(sv), "spelling (%s)" % sv))

    # Hyphen / space / closed-form equivalence: de-risking ~ de risking ~
    # derisking.  One pattern covers all three so they cannot disagree.
    #
    # HISTORY -- this variant was broken from birth and never matched anything.
    # The original built it as re.sub(r"[-\s]+", gap, re.escape(t)):
    # re.escape("de-risking") gives "de\-risking", the sub replaced the "-"
    # but left the orphan backslash, producing "de\[-...]*risking" -- an
    # escaped "[", matching the literal text "de[".  Every NOT-ATTESTED
    # verdict issued while it was broken printed "variants tried:
    # hyphen/space flexible" -- a false claim of search coverage, the exact
    # failure class this script exists to prevent.  The correct construction
    # escapes the PARTS and joins them with the unescaped gap:
    if "-" in t or " " in t:
        gap = r"[-‐-―\s]*"
        parts = [p for p in re.split(r"[-\s]+", t) if p]
        flexible = gap.join(_lit_pattern(p) for p in parts)
        out.append((flexible, "hyphen/space flexible"))

    # Suffix family: monotonically -> monotonic, monotonicity.  This is the
    # variant that would have saved the "monotonic" refusal.
    # Only the LAST word is stemmed, and the length bar applies to that word's
    # stem: single-word terms need >=5 chars (a 4-char stem plus [a-z]* is
    # close to a wildcard -- "proc" matches procedure/proceed/process...);
    # the last word of a phrase needs >=4, the preceding words anchoring it.
    #
    # HISTORY (2026-10-07) -- the bar used to be measured on the whole phrase,
    # so "clinical need" was stemmed to "clinical ne" (11 chars, passed) and
    # matched "Clinical Neuropsychologist"; "-ed"/"-es" were stripped from
    # words where they are not suffixes at all (need, rates -> rat -> ratio).
    words = re.split(r"([-\s]+)", t)
    last = words[-1]
    last_stem = re.sub(r"(ally|ically|ly|ness|ity|ies|es|ed|ing|s)$", "", last)
    min_len = 5 if len(words) == 1 else 4
    if last_stem != last and len(last_stem) >= min_len:
        stem = "".join(words[:-1]) + last_stem
        out.append((_lit_pattern(stem) + r"[a-z]*",
                    "suffix family (stem: %s)" % stem))

    return out


_TEXT_CACHE = {}


def _text(pid, include_refs):
    key = (pid, include_refs)
    if key not in _TEXT_CACHE:
        path = os.path.join(CORPUS, pid + ".txt")
        if not os.path.exists(path):
            _TEXT_CACHE[key] = None
        else:
            with open(path, encoding="utf-8", errors="replace") as fh:
                s = fh.read()
            _TEXT_CACHE[key] = textseg.clean_prose(s, keep_refs=include_refs)
    return _TEXT_CACHE[key]


def search(pattern, papers, include_refs=False):
    """Hit spans per paper for one pattern: {pid: {(start, end), ...}}.

    Counting runs over every eligible paper before anything is displayed, so
    the returned totals are always complete.
    """
    rx = re.compile(r"(?<![A-Za-z])(?:%s)(?![A-Za-z])" % pattern, re.I)
    spans = {}
    for pid in sorted(papers):
        s = _text(pid, include_refs)
        if not s:
            continue
        found = {(m.start(), m.end()) for m in rx.finditer(s)}
        if found:
            spans[pid] = found
    return spans


def attest(term, papers, total_words, cap, scope_label, refs=frozenset(),
           include_refs=False):
    """Run EVERY variant. Same-form variants (literal, spelling,
    hyphen/space) are UNIONED and decide the verdict; the suffix family
    (other forms of the lemma: increase/increasing for "increased") is
    reported separately and decides only when every same-form variant is
    zero -- the original zero-retry semantics, without letting related forms
    inflate the range of a form that is itself attested."""
    tried, contributed = [], []
    exact, related = {}, {}

    def merge(into, spans):
        new = 0
        for pid, ss in spans.items():
            have = into.setdefault(pid, set())
            for a, b in sorted(ss):
                if not any(a < y and x < b for x, y in have):
                    have.add((a, b))
                    new += 1
        return new

    for pattern, label in variants(term):
        spans = search(pattern, papers, include_refs)
        tried.append(label)
        new = merge(related if label.startswith("suffix family") else exact,
                    spans)
        if new:
            contributed.append("%s (+%d)" % (label, new))
    n_exact = sum(len(v) for v in exact.values())
    union = exact if n_exact else related
    related_only = {p: len(v) for p, v in related.items()
                    if v and p not in exact}
    per_paper = {pid: len(ss) for pid, ss in union.items() if ss}
    lines = []
    for pid in sorted(per_paper, key=lambda k: -per_paper[k]):
        s = _text(pid, include_refs)
        for a, b in sorted(union[pid]):
            ctx = re.sub(r"\s+", " ", s[max(0, a - KWIC_WINDOW):
                                        min(len(s), b + KWIC_WINDOW)]).strip()
            lines.append((pid, ctx))
    hits = sum(per_paper.values())
    research = [p for p in per_paper if p not in refs]
    reference = [p for p in per_paper if p in refs]
    if len(research) >= ATTESTED_MIN_PAPERS:
        verdict = "ATTESTED"
    elif hits and len(research) + len(reference) >= ATTESTED_MIN_PAPERS:
        verdict = "REFERENCE-ONLY"
    elif hits:
        verdict = "THIN"
    else:
        verdict = "NOT ATTESTED"
    return {
        "term": term,
        "matched_via": contributed[0].rsplit(" (+", 1)[0] if contributed else None,
        "contributions": contributed,
        "variants_tried": tried,
        "hits": hits,
        "range": len(per_paper),
        "range_research": len(research),
        "range_reference": len(reference),
        "eligible": len(papers),
        "per_10k": (hits / total_words * 10000) if total_words else 0.0,
        "papers": sorted(per_paper, key=lambda k: -per_paper[k]),
        "per_paper": per_paper,
        "lines": lines,
        "cap": cap,
        "scope": scope_label,
        "verdict": verdict,
        "attested": verdict == "ATTESTED",
        "via_related_forms": not n_exact and bool(related),
        "related_forms_hits": (sum(len(v) for v in related.values())
                               if n_exact else 0),
        "related_forms_extra_papers": len(related_only) if n_exact else 0,
    }


def render(r):
    out = []
    out.append("TERM  " + r["term"])
    if r["hits"] == 0:
        out.append("  w: 0 · range: 0/%d %s papers" % (r["eligible"], r["scope"]))
        out.append("  variants tried: " + ", ".join(r["variants_tried"]))
        out.append("  verdict: NOT ATTESTED"
                   " (widened pass ran; every variant above returned zero)")
        return "\n".join(out)

    pct = r["range"] / r["eligible"] * 100 if r["eligible"] else 0
    out.append("  w: %d · range: %d/%d %s papers (%.0f%%) · %.2f per 10k words"
               % (r["hits"], r["range"], r["eligible"], r["scope"], pct,
                  r["per_10k"]))
    out.append("  range split: %d research papers · %d reference documents"
               % (r["range_research"], r["range_reference"]))
    out.append("  hits by variant: " + "; ".join(r["contributions"]))
    if r.get("via_related_forms"):
        out.append("  matched ONLY via the suffix family (other forms of the"
                   " lemma) -- the exact form returned zero")
    elif r.get("related_forms_hits"):
        out.append("  related forms (suffix family, not counted above): %d hits,"
                   " %d further papers" % (r["related_forms_hits"],
                                           r["related_forms_extra_papers"]))
    out.append("  verdict: %s (research range %d vs threshold %d)"
               % (r["verdict"], r["range_research"], ATTESTED_MIN_PAPERS))

    shown = r["lines"] if r["cap"] is None else r["lines"][: r["cap"]]
    omitted = len(r["lines"]) - len(shown)
    head = "  concordance (showing %d of %d" % (len(shown), r["hits"])
    head += "; %d not shown -- rerun with --all)" % omitted if omitted else ")"
    out.append(head)
    for pid, ctx in shown:
        out.append("    %-26s %s" % (pid[:26], ctx[:120]))
    out.append("  papers: " + ", ".join(
        "%s(%d)" % (p, r["per_paper"][p]) for p in r["papers"][:12]
    ) + (" ..." if len(r["papers"]) > 12 else ""))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(
        description="Attest terms against this instance's corpus.")
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--scope", choices=["term", "style", "all"], default="term",
                    help="term = terminology_safe (default), style = style_safe,"
                         " all = every distinct paper")
    ap.add_argument("--all", action="store_true",
                    help="print the full concordance instead of the first %d"
                         % KWIC_DEFAULT_CAP)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--include-refs", action="store_true",
                    help="also search reference lists and captions (default:"
                         " running prose only)")
    args = ap.parse_args()

    meta = load_meta()
    papers = eligible(meta, args.scope)
    if not papers:
        sys.exit("no eligible papers for scope=%s -- is corpus_meta.yaml stale?"
                 "\n  fix: py scripts/build_corpus_meta.py" % args.scope)
    total_words = sum(papers.values())
    cap = None if args.all else KWIC_DEFAULT_CAP

    refs = reference_ids(meta)
    results = [attest(t, papers, total_words, cap, args.scope, refs,
                      args.include_refs)
               for t in args.terms]

    if args.json:
        for r in results:
            # Carry one representative concordance line into the JSON.  Callers
            # that record a verdict (scripts/cache.py) must be able to write the
            # evidence WITH the verdict; a cache row whose ctx: a human has to
            # remember to paste is a cache row that ships without one -- 38 of
            # terms.md's 41 section A rows lost their cite-key exactly that way.
            r["sample"] = r["lines"][0][1][:200] if r["lines"] else ""
            r["sample_paper"] = r["lines"][0][0] if r["lines"] else ""
            r.pop("lines", None)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("corpus: %d eligible papers (scope=%s), %s words"
              % (len(papers), args.scope, format(total_words, ",")))
        print()
        for r in results:
            print(render(r))
            print()

    return 0 if all(r["attested"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
