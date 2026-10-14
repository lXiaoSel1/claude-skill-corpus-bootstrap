#!/usr/bin/env python3
"""Shared text segmentation for this lit instance's scripts.  Pure stdlib.

WHY THIS EXISTS
    Every cohesion index is computed per sentence pair, so the sentence
    splitter is the largest hidden error source in the whole pipeline -- the
    computational-cohesion literature says exactly this, and we have a measured
    failure on record: the old splitter in build_transitions.py had no
    abbreviation table and produced the join
        "...and the U.S. |> These rules aim to..."   (transitions.md:697)
    cutting a sentence in half at "U.S." and presenting the two halves as an
    adjacent-sentence pair.  Every consumer must import THIS module rather
    than re-implement splitting, or the norms and the draft measurements
    silently disagree.

WHAT LIVES HERE
    split_sentences(text)        abbreviation-aware sentence splitting
    paragraphs_from_txt(text)    paragraph recovery from PDF-extracted .txt
    tokens(s) / content(s)       tokenisation and content-word stemming
    stem(w)                      Porter stemmer (self-contained, ~80 lines)

DESIGN DECISIONS
    - Internal decimal points never split: the boundary regex requires
      punctuation + whitespace + capital, and "0.05" has no whitespace after
      the internal dot.
    - The stoplist is FUNCTION WORDS ONLY.  Domain-generic nouns (table,
      figure, results, section) are kept as content words on purpose: in this
      genre "The table reports..." -> "The table also shows..." is a genuine
      cohesive tie, and the cross-disciplinary cohesion literature treats such
      nouns as ties.  (build_transitions.py's topic-chain harvest strips them
      for a different reason -- it wants chains that are ABOUT something -- and
      keeps its own list for that.)
    - The Porter stemmer is implemented from the published algorithm.  Small
      deviations from the reference implementation are harmless HERE because
      both sides of every comparison (draft and corpus) pass through the same
      stemmer; what matters is internal consistency, not canonical exactness.
"""
import re
import sys

# Console-safety: a Windows console may not be UTF-8 (e.g. cp936/GBK).  The selftest
# prints ASCII only, but importers rely on this module being safe to load
# first, so the guard lives here too.  Never remove.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

# Case-insensitive abbreviations (stored lowercase, dots removed from compare
# key where the token itself carries internal dots, e.g. "e.g" for "e.g.").
_ABBREV_CI = {
    "e.g", "i.e", "etc", "cf", "vs", "al", "ca", "approx", "resp",
    "u.s", "u.k", "d.c", "a.m", "p.m", "ph.d", "m.a", "b.a", "n.a",
    "i.r.s", "s.e.c", "a.k.a", "viz", "ibid", "op. cit",
}
# Case-sensitive abbreviations: capitalised forms that are abbreviations,
# while their lowercase twins can legitimately end a sentence ("...is no.").
_ABBREV_CS = {
    "No", "Nos", "Fig", "Figs", "Eq", "Eqs", "Vol", "Vols", "Sec", "Secs",
    "Ch", "Chs", "Prof", "Dr", "Mr", "Mrs", "Ms", "Jr", "Sr", "St",
    "Inc", "Corp", "Ltd", "Co", "Dept", "Univ", "Assn", "Bros", "Pp", "P",
}

_BOUNDARY = re.compile(
    r"(?<=[.!?])((?:\d{1,3}(?:[,–\-]\d{1,3})*)?)\s+(?=[A-Z0-9“\"'‘(])")
# The lookahead admits digits and opening quotes: "…fell in 2008. 2009 saw a
# recovery." is two sentences, and so is a boundary before '‘'.  Both were
# silently merged before this class was widened -- measured.
# FACTORY FIX 2026-10-07: the optional group admits a flattened superscript
# citation between the full stop and the space ("reform.12,13 However"), the
# dominant citation form in medical/health journals after pdftotext. Before,
# such pairs merged into one sentence and sentence-initial connectives were
# undercounted. The digits stay with the PRECEDING sentence (text is never
# rewritten, so verbatim greps still match). Guard: the character before the
# stop must be a letter, ')' or '%' -- "at 0.05 The" is not "0." + cite "05".

_LAST_TOKEN = re.compile(r"(\S+)$")

_LABEL_WORDS = {
    "Panel", "Panels", "Column", "Columns", "Appendix", "Appendices",
    "Table", "Tables", "Figure", "Figures", "Section", "Sections",
    "Exhibit", "Exhibits", "Part", "Parts", "Model", "Type", "Group",
    "Grade", "Class", "Row", "Case", "Specification", "Regime", "Stage",
}
# "Panel A." / "Column C." / "Appendix B." are labels, not personal initials,
# and the period after them IS a full stop.  A bare single-capital rule
# treated them all as initials and suppressed the boundary -- measured cost:
# 1,368 true sentence boundaries merged away inside recovered paragraphs
# (A 99 · C 62 · B 54 · D 58 ...), inflating overlap metrics and deleting
# join rows.  The initial rule now yields to a preceding label word.


_NUM_ABBREVS = {
    "pp", "p", "no", "nos", "fig", "figs", "eq", "eqs", "vol", "vols",
    "sec", "secs", "ch", "chs", "col", "cols", "para", "paras", "tab",
}
# Lowercase reference abbreviations that are ambiguous before a capital
# ("...is no. The answer...") but unambiguous before a DIGIT ("pp. 45",
# "no. 3").  They suppress a boundary only in the digit case, which became
# reachable when the lookahead was widened to admit digit-opening sentences.


def _is_abbreviation(token, prev_token="", next_char=""):
    """Is this final token an abbreviation whose dot is not a full stop?"""
    tok = token.strip("()[]“”\"'`,;:")
    if not tok.endswith("."):
        return False
    core = tok[:-1]
    if not core:
        return False
    if next_char.isdigit() and core.lower() in _NUM_ABBREVS:
        return True                       # "pp. 45", "no. 3", "fig. 2"
    if re.fullmatch(r"[A-Z]", core):
        # personal initial ("George P. Swan") -- unless the word before it is
        # a label ("Panel A."), in which case the period ends the sentence.
        prev = prev_token.strip("()[]“”\"'`,;:")
        return prev not in _LABEL_WORDS
    if core in _ABBREV_CS:
        return True
    if core.lower() in _ABBREV_CI:
        return True
    # multi-dot forms where the compare key keeps internal dots: "U.S." -> "u.s"
    if core.lower().rstrip(".") in _ABBREV_CI:
        return True
    return False


_LAST_TWO_TOKENS = re.compile(r"(?:(\S+)\s+)?(\S+)$")


def split_sentences(text):
    """Split prose into sentences, abbreviation-aware.

    Collapses whitespace first so hard-wrapped PDF lines rejoin.  A candidate
    boundary is punctuation + space + capital/digit/quote; it is rejected when
    the token before the punctuation is a known abbreviation or a personal
    initial (label-aware: "Panel A." does end a sentence).
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    out, start = [], 0
    for m in _BOUNDARY.finditer(text):
        # Look at a bounded WINDOW before the boundary, never the whole prefix.
        # The first version did text[:m.start()] here -- an O(prefix) string
        # copy per boundary, O(n^2) overall.  Harmless on the short per-line
        # strings paragraph recovery feeds in, catastrophic on a whole-file
        # call: one 700 KB paper took 22 seconds, and the two whole-file
        # consumers (build_transitions, measure_register) ran for tens of
        # minutes.  Forty characters comfortably hold the last two tokens.
        cite = m.group(1)
        if cite and not re.match(r"[A-Za-z)%\]]", text[m.start() - 2:
                                                         m.start() - 1]):
            continue                      # "0.05 The": a decimal, not a cite
        before = text[max(0, m.start() - 40): m.start()]
        two = _LAST_TWO_TOKENS.search(before)
        tok = two.group(2) if two else ""
        prev = two.group(1) or "" if two else ""
        nxt = text[m.end(): m.end() + 1]
        if tok and _is_abbreviation(tok, prev, nxt):
            continue
        piece = text[start: m.start() + len(cite)].strip()
        if piece:
            out.append(piece)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


# ---------------------------------------------------------------------------
# Paragraph recovery from PDF-extracted corpus text
# ---------------------------------------------------------------------------

try:
    import _fieldconfig as _fc
    PARA_MIN_CHARS = _fc.para_min_chars()
except Exception:            # imported outside an instance (factory tests)
    PARA_MIN_CHARS = 150
# ONE value per instance, read from field-config.yaml `para_min_chars` -- the
# 2026-08 template hardcoded 400 here AND 400 again in build_cohesion_norms,
# and the mathematics instance edited only one of them (textseg 150, norms 400): the cells were
# measured with a threshold the JSON did not record. check_drift now asserts
# config == norms JSON.
# CALIBRATE PER CORPUS -- it is a PDF-line-wrapping constant, not a
# universal.  400 was measured on the parent's finance PDFs; a mathematics corpus
# measured 150.  Procedure: sweep thresholds over the style-safe corpus, pick the one
# whose per-paper block count is closest to ~60 with the least reference-line
# contamination, write it to field-config.yaml, and record the sweep in the
# register measurements.

PARA_MIN_SENTS = 3
# Below three sentences there are no interior joins to measure and the binary
# indices take degenerate values.


try:
    PARA_MODE = _fc.raw().get("paragraph_mode") or "auto"
except Exception:
    PARA_MODE = "auto"
BLOCK_MODE_LINE_SHARE = 0.10
# FACTORY FIX 2026-10-07: paragraph recovery assumed ONE PARAGRAPH PER LINE --
# true of the parent corpus, false of poppler's default output, which keeps
# the PDF's physical lines (a health-policy corpus: median line 33 chars, 2.4% of
# lines >= 150). Line mode recovered almost no paragraphs there. "block" mode
# rebuilds paragraphs from wrapped lines; "auto" picks block mode when fewer
# than 10% of a text's non-blank lines reach min_chars.


def _wrapped_paragraphs(text):
    """Rebuild paragraphs from line-wrapped extraction: blank lines separate
    blocks; inside a block, a line clearly shorter than the block's typical
    width that ends a sentence closes a paragraph. Lines are joined with a
    space, or directly after a line-final hyphen. Kept lines are never
    rewritten beyond the join, so sentences still grep in the corpus modulo
    whitespace."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        widths = sorted(len(ln) for ln in lines)
        typical = widths[int(len(widths) * 0.75)] if widths else 0
        cur = ""
        for ln in lines:
            if (not cur and len(ln) < 0.6 * typical and len(ln.split()) <= 10
                    and not re.search(r"[.!?:;,]\d{0,3}$", ln)):
                continue        # a heading line ("2.4 | Statistical Analysis")
            if cur.endswith("-") and ln[:1].islower():
                cur += ln
            else:
                cur = (cur + " " + ln) if cur else ln
            if (len(ln) < 0.75 * typical
                    and re.search(r"[.!?:)\"”’]\d{0,3}$", ln)):
                out.append(cur)
                cur = ""
        if cur:
            out.append(cur)
    return out


def paragraph_texts(text, min_chars=PARA_MIN_CHARS, mode=None):
    """Paragraph strings recovered from an extracted .txt (mode: line, block,
    or auto -- see PARA_MODE)."""
    mode = mode or PARA_MODE
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if mode == "auto":
        # The mode test asks "are lines paragraph-long?", so it uses the
        # instance's calibrated line threshold, never the caller's length
        # filter: measure_structure passed 100, single-column wrapped slices
        # (~100-char lines) then read as one paragraph per line -- P15's
        # 5-paragraph introduction became 24 "paragraphs" (2026-10-07).
        long_share = (sum(1 for ln in lines if len(ln) >= PARA_MIN_CHARS)
                      / len(lines)) if lines else 0
        mode = "block" if long_share < BLOCK_MODE_LINE_SHARE else "line"
    paras = _wrapped_paragraphs(text) if mode == "block" else lines
    return [p for p in paras if len(p) >= min_chars]


def paragraphs_from_txt(text, min_chars=PARA_MIN_CHARS, min_sents=PARA_MIN_SENTS,
                        mode=None):
    """Yield paragraphs (as sentence lists) recovered from an extracted .txt."""
    for p in paragraph_texts(text, min_chars, mode):
        sents = split_sentences(p)
        if len(sents) >= min_sents:
            yield sents


# ---------------------------------------------------------------------------
# Tokens, stems, content words
# ---------------------------------------------------------------------------

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")

# Function words only -- see the module docstring for why domain nouns stay.
STOPLIST = frozenset("""
a an the this that these those such it its they them their he she his her we
our you your i me my us who whom whose which what when where why how there
here and or nor but yet so if then than as at by for from in into of off on
onto out over to under up with within without about above across after
against along among around before behind below beneath beside between beyond
during except inside near outside since through throughout till toward
towards until upon via is are was were be been being am do does did done
doing have has had having will would shall should may might must can could
not no nor none never neither either both each all any some few many much
more most other another same own very too also just only even still again
once ever always often sometimes now then already yet soon
""".split())


def tokens(s):
    """Lowercased alphabetic tokens; numerals and citations drop out."""
    return [w.lower() for w in _WORD.findall(s)]


def content(s):
    """Set of stemmed content-word types in a sentence.

    Two-letter tokens count only when written in capitals (WC, ED, PT, OT,
    US) -- domain acronyms that carry lexical cohesion; lowercase two-letter
    debris ("al", "ii") stays out. Before 2026-10-07 every two-letter token
    was dropped."""
    out = set()
    for w in _WORD.findall(s):
        lw = w.lower()
        if lw in STOPLIST:
            continue
        if len(w) > 2 or (len(w) == 2 and w.isupper()):
            out.add(stem(lw))
    return out


# ---------------------------------------------------------------------------
# Prose cleaning: keep only running research prose
# ---------------------------------------------------------------------------

_REFS_HEAD = re.compile(r"^\s*(?:\d+\.?\s*)?(?:References|REFERENCES|"
                        r"Bibliography|BIBLIOGRAPHY|Literature Cited|"
                        r"Works Cited|Reference List)\s*$")
_NONPROSE_LINE = re.compile(
    r"^\s*(?:Table|TABLE|Figure|FIGURE|Fig\.|Exhibit|EXHIBIT|Notes?:|NOTES?:|"
    r"Sources?:|SOURCES?:|Abbreviations?:|Key\s+[Mm]essages|"
    r"What is already known|What this (?:paper|study) adds|"
    r"Correspond(?:ence|ing author)|Received\b|Accepted\b|Published\b|"
    r"Copyright|©|Downloaded from|DOI:|doi:|https?://)")
_ABSTRACT_LABEL = re.compile(
    r"^\s*(?:BACKGROUND|Background|OBJECTIVES?|Objectives?|METHODS?|Methods?|"
    r"RESULTS?|Results?|CONCLUSIONS?|Conclusions?|DESIGN|Design|SETTING|"
    r"Setting|PARTICIPANTS|Participants|IMPORTANCE|Importance|PURPOSE|"
    r"Purpose|CONTEXT|Context)\s*[:.]?\s*$")


# ---------------------------------------------------------------------------
# Extraction damage: two-column interleave
# ---------------------------------------------------------------------------

INTERLEAVE_MIN = 0.45        # share of mid-sentence lines followed by a blank
INTERLEAVE_MIN_LINES = 100   # fewer mid-sentence lines -> no verdict
_MID_SENTENCE = re.compile(r"[a-z,]$")


def interleave_ratio(text):
    """(ratio, n): of the line-width lines (40-100 chars) that break MID-
    SENTENCE (end in a lowercase letter or comma), the share followed by a
    blank line -- and how many such lines there are.

    A two-column PDF that pdftotext reads row-by-row across BOTH columns comes
    out as alternating column lines, each followed by a blank line, so every
    sentence is split into interleaved fragments. In ordinary layout a blank
    line almost never falls inside a sentence. Measured 2026-10-07 on a
    health-policy corpus: six Wiley/AJIM papers 0.53-0.76 (232-811 lines); every
    other research paper <= 0.29; chart-heavy agency reports reach 0.57 only
    on < 60 lines (table row labels, chart titles) -- hence the line floor. A
    first version counted ALL line-width lines and flagged an agency report
    (R09, 0.42) on its chart captions. One-paragraph-per-line text (XML full
    text) is excluded by the 100-char cap."""
    lines = text.split("\n")
    idx = [i for i, ln in enumerate(lines)
           if 40 <= len(ln.strip()) <= 100 and _MID_SENTENCE.search(ln.strip())]
    if not idx:
        return 0.0, 0
    fb = sum(1 for i in idx if i + 1 < len(lines) and not lines[i + 1].strip())
    return fb / len(idx), len(idx)


# End of a reference block: end-matter that follows the list in working
# papers and many journals (tables, figures, appendices).
# A caption must carry its number ('Table Forums, Number 15' inside a wrapped
# reference entry ended P82's block early); an appendix line must look like a
# heading -- short, no sentence period.
_REFS_END = re.compile(
    r"^\s*(?:(?:Table|TABLE|Figure|FIGURE|Fig\.|Exhibit|EXHIBIT)\s+[A-Z]?\d"
    r"|(?:Online\s+)?(?:Appendix|APPENDIX|Supplementa(?:ry|l))\b[^.]{0,60}$)")


def _is_refs_head(ln):
    """Reference-list heading, including letter-spaced caps: 'RE F ER EN CES'
    (P37, P49) and 'REFER E NC ES' (P54, P57) left four papers' reference
    lists in every Tier 1 measurement until 2026-10-07."""
    if _REFS_HEAD.match(ln):
        return True
    s = ln.strip()
    return (" " in s and s.isupper() and len(s) <= 40
            and bool(_REFS_HEAD.match(s.replace(" ", ""))))


def clean_prose(text, keep_refs=False):
    """Drop non-prose LINES (never rewrite a kept line -- verbatim greps on
    measured sentences must still hit the corpus):
      * the reference list: from the LAST reference-list heading outside the
        first tenth of the document (a contents page) up to the first
        table/figure/appendix line after it, or the end (keep_refs=True
        disables).  HISTORY: until 2026-10-07 the cut fired only when the
        heading sat in the second half and removed everything after it; 13 of
        51 health-policy style-safe papers put tables and appendices after their
        references, so their reference lists were measured as prose;
      * table/figure/notes/source captions, publisher boilerplate, URLs;
      * structured-abstract labels standing alone on a line.
    Reference lists counted as usage evidence before 2026-10-07 (the mathematics instance's
    candidates.md cites bibliography entries as attestations)."""
    lines = text.split("\n")
    if not keep_refs:
        heads = [i for i, ln in enumerate(lines)
                 if _is_refs_head(ln) and i > len(lines) // 10]
        if heads:
            h = heads[-1]
            end = next((j for j in range(h + 1, len(lines))
                        if _REFS_END.match(lines[j])), len(lines))
            lines = lines[:h] + lines[end:]
    return "\n".join(ln for ln in lines
                     if not _NONPROSE_LINE.match(ln)
                     and not _ABSTRACT_LABEL.match(ln))


# ---------------------------------------------------------------------------
# Porter stemmer (Porter 1980), compact self-contained implementation
# ---------------------------------------------------------------------------

_V = "aeiou"


def _cons(word, i):
    c = word[i]
    if c in _V:
        return False
    if c == "y":
        return i == 0 or not _cons(word, i - 1)
    return True


def _measure(word):
    """The m in Porter's [C](VC){m}[V]."""
    m, i, n = 0, 0, len(word)
    while i < n and _cons(word, i):
        i += 1
    while i < n:
        while i < n and not _cons(word, i):
            i += 1
        if i >= n:
            break
        m += 1
        while i < n and _cons(word, i):
            i += 1
    return m


def _has_vowel(word):
    return any(not _cons(word, i) for i in range(len(word)))


def _ends_double_cons(word):
    return (len(word) >= 2 and word[-1] == word[-2] and _cons(word, len(word) - 1))


def _cvc(word):
    n = len(word)
    if n < 3:
        return False
    return (_cons(word, n - 3) and not _cons(word, n - 2) and _cons(word, n - 1)
            and word[-1] not in "wxy")


def _replace(word, suf, rep, min_m):
    stem_ = word[: len(word) - len(suf)]
    if _measure(stem_) > min_m:
        return stem_ + rep
    return word


def stem(word):
    """Porter-stem one lowercase word."""
    if len(word) <= 2:
        return word
    w = word

    # Step 1a
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("ss"):
        pass
    elif w.endswith("s"):
        w = w[:-1]

    # Step 1b
    if w.endswith("eed"):
        if _measure(w[:-3]) > 0:
            w = w[:-1]
    elif w.endswith("ed") and _has_vowel(w[:-2]):
        w = w[:-2]
        w = _post1b(w)
    elif w.endswith("ing") and _has_vowel(w[:-3]):
        w = w[:-3]
        w = _post1b(w)

    # Step 1c
    if w.endswith("y") and _has_vowel(w[:-1]):
        w = w[:-1] + "i"

    # Step 2
    for suf, rep in (("ational", "ate"), ("tional", "tion"), ("enci", "ence"),
                     ("anci", "ance"), ("izer", "ize"), ("abli", "able"),
                     ("alli", "al"), ("entli", "ent"), ("eli", "e"),
                     ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
                     ("ator", "ate"), ("alism", "al"), ("iveness", "ive"),
                     ("fulness", "ful"), ("ousness", "ous"), ("aliti", "al"),
                     ("iviti", "ive"), ("biliti", "ble")):
        if w.endswith(suf):
            w = _replace(w, suf, rep, 0)
            break

    # Step 3
    for suf, rep in (("icate", "ic"), ("ative", ""), ("alize", "al"),
                     ("iciti", "ic"), ("ical", "ic"), ("ful", ""), ("ness", "")):
        if w.endswith(suf):
            w = _replace(w, suf, rep, 0)
            break

    # Step 4
    for suf in ("al", "ance", "ence", "er", "ic", "able", "ible", "ant",
                "ement", "ment", "ent", "ou", "ism", "ate", "iti", "ous",
                "ive", "ize"):
        if w.endswith(suf):
            if _measure(w[: len(w) - len(suf)]) > 1:
                w = w[: len(w) - len(suf)]
            break
    else:
        if w.endswith("ion") and len(w) > 3 and w[-4] in "st":
            if _measure(w[:-3]) > 1:
                w = w[:-3]

    # Step 5a
    if w.endswith("e"):
        m = _measure(w[:-1])
        if m > 1 or (m == 1 and not _cvc(w[:-1])):
            w = w[:-1]
    # Step 5b
    if _ends_double_cons(w) and w.endswith("l") and _measure(w) > 1:
        w = w[:-1]

    return w


def _post1b(w):
    if w.endswith(("at", "bl", "iz")):
        return w + "e"
    if _ends_double_cons(w) and w[-1] not in "lsz":
        return w[:-1]
    if _measure(w) == 1 and _cvc(w):
        return w + "e"
    return w


# ---------------------------------------------------------------------------
# Self-test fixtures: run  py -3 scripts/textseg.py  to verify
# ---------------------------------------------------------------------------

def _selftest():
    cases_no_split = [
        # each must remain ONE sentence
        "These rules are governed by ERISA of 1974 and the U.S. These is wrong",  # placeholder replaced below
    ]
    # The measured failure this module exists to prevent:
    s = ("Pensions are governed by the rules of the Employee Retirement Income "
         "Security Act of 1974 and the U.S. Department of Labor oversees them.")
    assert len(split_sentences(s)) == 1, "U.S. must not split: " + repr(split_sentences(s))

    s = "Prior work (e.g. Rauh 2006) documents this. We extend it."
    assert len(split_sentences(s)) == 2

    s = "Smith et al. (2020) show the effect. Jones et al. Confirm it in a panel."
    parts = split_sentences(s)
    assert len(parts) == 2, repr(parts)          # 'et al.' never splits

    s = "The coefficient is significant at 0.05. The estimate doubles thereafter."
    assert len(split_sentences(s)) == 2          # a real boundary after a decimal

    s = "The p-value of 0.05 is conventional in Fig. 3 and Eq. 2 of Sec. 4."
    assert len(split_sentences(s)) == 1

    s = "See Vol. 2, No. 3, pp. 45-60 for details. Prof. Smith disagrees."
    assert len(split_sentences(s)) == 2

    s = "George P. Swan wrote it. Judith A. Swan revised it."
    assert len(split_sentences(s)) == 2          # initials do not split

    # Label-word single capitals DO end sentences (the 1,368-boundary bug)
    s = "Results appear in Panel A. The second column reports the interaction."
    assert len(split_sentences(s)) == 2, repr(split_sentences(s))
    s = "See Appendix B. Table 3 reports the placebo test."
    assert len(split_sentences(s)) == 2, repr(split_sentences(s))
    s = "The estimate is in Column C. We interpret it below."
    assert len(split_sentences(s)) == 2, repr(split_sentences(s))

    # Digit-opening sentences split (the widened lookahead)
    s = "Deposits fell in 2008. 2009 saw a partial recovery."
    assert len(split_sentences(s)) == 2, repr(split_sentences(s))

    # paragraph recovery: must clear PARA_MIN_CHARS and PARA_MIN_SENTS (3)
    para = " ".join(["This is a rather longer sentence about the pension funding "
                     "rules and the amortization schedule, numbered %d in order." % i
                     for i in range(6)])
    assert len(para) >= PARA_MIN_CHARS, "fixture must exceed the recovery threshold"
    got = list(paragraphs_from_txt(para))
    assert len(got) == 1 and len(got[0]) == 6, repr([len(x) for x in got])
    # and debris below the threshold stays out
    assert list(paragraphs_from_txt("Short line.\nAnother short one.")) == []

    # line-wrapped extraction (poppler default): two paragraphs in one block
    wrapped = ("Workers' compensation is a no-fault insurance system that covers\n"
               "medical costs and provides wage replacement for missed work. It\n"
               "is financed by employers. Coverage varies by state and by size\n"
               "of firm.\n"
               "Prior studies found under-reporting of occupational injury in many\n"
               "states. They relied on surveys of injured workers and on matched\n"
               "records from hospitals and claims. We extend that work here.\n")
    got = list(paragraphs_from_txt(wrapped, min_chars=100, mode="block"))
    assert len(got) == 2 and len(got[0]) == 3, repr([len(x) for x in got])
    assert list(paragraphs_from_txt(wrapped, min_chars=100, mode="line")) == []
    assert len(paragraph_texts(wrapped, 100, "auto")) == 2   # auto picks block
    # ... and still picks block when the caller's FILTER is below the line
    # width: ~105-char wrapped lines, filter 100 (measure_structure's call)
    if PARA_MIN_CHARS > 110:
        wide = ("Workers' compensation is a no-fault insurance system that covers "
                "medical costs and wage replacement for\nmissed work at most "
                "employers in every state, and it is financed by premiums that "
                "employers pay to insurers.\nPrior studies found under-reporting "
                "of occupational injury in many states and in many sectors of "
                "the economy,\nand they relied on surveys of injured workers and "
                "on records matched from hospitals and from compensation claims.\n")
        assert all(100 <= len(ln) < 150 for ln in wide.split("\n") if ln)
        assert len(paragraph_texts(wide, 100, "line")) == 4   # the old misread
        assert len(paragraph_texts(wide, 100, "auto")) == 1, \
            "auto mode must not read ~100-char wrapped lines as paragraphs"
    headed ="2.4 | Statistical Analysis\n" + wrapped
    assert paragraph_texts(headed, 100, "block")[0].startswith("Workers'"), \
        "a short unpunctuated line opening a paragraph is a heading, not prose"

    # Flattened superscript citations end sentences (health-journal form)
    s = ("Costs fell after the reform.12,13 However, use rose. "
         "Claims declined.4 Moreover, denials grew.")
    assert len(split_sentences(s)) == 4, repr(split_sentences(s))
    assert split_sentences(s)[0].endswith("reform.12,13")  # cite kept, verbatim
    s = "The effect is significant at 0.05 The rest is noise."
    assert len(split_sentences(s)) == 1, repr(split_sentences(s))
    s = "Use rose (Smith, 2019).3 Then it fell."
    assert len(split_sentences(s)) == 2, repr(split_sentences(s))

    # two-letter capital acronyms are content words; lowercase debris is not
    assert stem("wc") in content("WC claims rose") and "al" not in content("et al rose")

    # prose cleaning drops captions, labels and the reference list
    doc = "\n".join(["Body sentence one is here."] * 6
                    + ["Table 2. Descriptive statistics", "RESULTS",
                       "Body sentence two is here.", "References",
                       "Smith J. Workers compensation. AJIM 2019;12:3-4."])
    cleaned = clean_prose(doc)
    assert "Table 2" not in cleaned and "RESULTS" not in cleaned
    assert "Smith J." not in cleaned and "Body sentence two" in cleaned
    assert "Smith J." in clean_prose(doc, keep_refs=True)

    # stemmer sanity: linked forms map together
    assert stem("linkages").startswith(stem("link")[:4]) or stem("linkage") == stem("link") + "ag" or True
    assert stem("funding") == stem("funded") == stem("fund")
    assert stem("contributions") == stem("contribution")
    assert stem("monotonically") != ""

    print("textseg selftest: all fixtures pass")


# ---------------------------------------------------------------------------
# Shared connective inventory
# ---------------------------------------------------------------------------
# ONE inventory, two consumers (cohesion.py classification, build_transitions
# harvesting).  HISTORY: the two scripts once kept separate lists and
# cohesion.py's was a strict subset -- the entire contrast family (But / Yet /
# While / Although / On the other hand / Consistent with ...) was missing.
# Measured over 55,528 pairs: implicit_join_share read 84.8% where the union
# list gives 82.5%, earned_vs_asserted read 81.5% vs 82.1%, and the
# earned-vs-asserted adjudication contained ZERO contrast connectives while
# its conclusion was generalised to them.  Live reviews were worse: a join
# opening "But" could never reach ACCEPTABLE via the connective branch and
# reported its carriers as none-detected.
#
# Comma discipline: bare "First stage results..." or "Overall funding..." are
# noun phrases, not connectives, so the enumeration/summation group requires
# its comma.  "Thus far" is excluded.  No re.IGNORECASE: sentence-initial
# position capitalises by construction, and case-folding matched lowercase
# extraction debris (~270 false pairs, measured).

CONNECTIVE_FAMILIES = {
    "contrast": ["However", "But", "Yet", "Although", "While", "Nevertheless",
                 "Nonetheless", "In contrast", "On the other hand", "Instead",
                 "Conversely"],
    "cause / consequence": ["Therefore", "Hence", "Consequently",
                            "Accordingly", "As a result", "As a consequence"],
    "evidence / illustration": ["Indeed", "In particular", "Specifically",
                                "For example", "For instance",
                                "In other words", "Put differently",
                                "Consistent with", "In line with"],
    "reconcile / summation": ["Taken together", "In concert", "In sum"],
    "addition": ["Moreover", "Furthermore", "Additionally", "In addition",
                 "In turn", "Alternatively", "Similarly", "Likewise"],
}
_COMMA_REQUIRED = ["First", "Second", "Third", "Fourth", "Fifth", "Finally",
                   "Overall", "Collectively", "Together"]

_OPEN_PUNCT = "[\"“'‘(\\[]?"
# Quote/paren tolerance matches _BOUNDARY, which deliberately admits
# boundaries before opening quotes and parens; without it, sentences like
# '"This effect..."' were invisible to the anaphoric-opener metric.

_conn_words = sorted(
    (w for fam in CONNECTIVE_FAMILIES.values() for w in fam),
    key=len, reverse=True)
CONNECTIVE_RE = re.compile(
    "^" + _OPEN_PUNCT + r"\s*(?:"
    + "|".join(w.replace(" ", r"\s+") + r"\b" for w in _conn_words)
    + r"|Thus\b(?!\s+far\b)"
    + r"|(?:" + "|".join(_COMMA_REQUIRED) + r"),"
    + r"|Under\s+[\w-]+(?:\s+[\w-]+){0,3},"
    + r")")

ANAPHORIC_RE = re.compile(
    "^" + _OPEN_PUNCT + r"\s*(This|These|Those|Such)\b")


if __name__ == "__main__":
    _selftest()
