#!/usr/bin/env python3
r"""
A1 - heading extraction (mechanical only; assigns NO job labels).

Design principle: OPTIMISE FOR RECALL. A2 reads content and will reject false
candidates; a missed chapter is unrecoverable. So we drop only on high-precision
rules (footnote-sentence shape, table caption) and otherwise FLAG rather than drop.

CRITICAL: corpus is CRLF. Never use a bare `$`. Patterns end \s*$ on rstrip'd text.
"""
import re, os, json, collections

# Console-safety: the mimic-lit corpus is not valid UTF-8 in 140 of 165 files;
# decoding with errors="replace" manufactures U+FFFD in memory, and printing it
# on a non-UTF-8 Windows console (e.g. cp936/GBK) raises UnicodeEncodeError.  Same
# guard as every mimic-lit script (measured failure: attest.py died on almost
# every term before the guard existed).  Never remove.
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


BASE = os.path.dirname(os.path.abspath(__file__))
# LAYOUT: the parent kept pipeline/ INSIDE references/, so "BASE/.." was
# references/.  A stamped instance puts pipeline/ at the skill root, so
# references/ is BASE/../references.  Caught 2026-08-28 when a2_build
# looked for <skill>/sample.md instead of <skill>/references/sample.md.
REF = os.path.normpath(os.path.join(BASE, "..", "references"))            # references/
SKILLS = os.path.normpath(os.path.join(REF, "..", ".."))    # .claude/skills/
import _jobs
CORPUS = _jobs.corpus_dir()

KEYS = os.path.join(BASE, "sample-keys.txt")
OUT = os.path.join(BASE, "a1_candidates.json")

# ---------- patterns ----------
# Title char class must include '?' -- DeFondZhang2014's top-level chapters are
# questions ("2. What is audit quality?") and were silently dropped without it.
# Length cap raised 70 -> 110: NovyMarx2015's section IV title is 72 chars
# ("IV. The Value of State ABO Pension Promises under Appropriate Discount
# Rates") and the paper's headline results chapter vanished for two characters.
# Length cap: 70 -> 110 -> 150. It bit three separate times (NovyMarx2015's
# section IV at 72 chars; RauhStefanescuZeldes2020's section 2 at 121, where a
# chapter heading and its first subsection share one line). Precision is carried
# by numbered_ok(), not by a length guess.
# FIELD ADAPTATION (mathematics, 2026-08-29): the class must admit the
# relation symbols and Greek letters that maths section titles carry.
# Measured on a mathematics corpus: '3. Ground states in the case p > 2',
# '4. Bound states for p > 2' and '5. The case p = 2; proof of Theorem
# 1.3' never even reached the candidate scan because '>' and '=' were
# outside the class -- three real chapters of 09_IanniI2012 silently
# lost, and the same pattern in 23_VairaG2011 and 24_WangJ2017.
T = r'[A-Za-z0-9 ,:;&?!\'’\-–—\(\)/\.~<>=≤≥≠+*\^_\{\}\[\]\|\u0370-\u03ff\ufb00-\ufb06]'
# FIELD ADAPTATION (mathematics, 2026-08-29): maths journals prefix section
# numbers with a section sign -- "§ 1. Introduction" (08_HeppK1974,
# 11_LiebEH1977b).  Requiring the line to START with the digit lost both
# papers' introductions entirely: neither had a `frame` slice at all until
# this was allowed.  Also admit '~' inside titles: OCR of scanned journals
# renders capital O as a tilde ("0. INTR~D~JCTION", 05_FloerA1986), which
# blocked that paper's introduction the same way.  Third strike from the
# same fact (2026-08-29): LaTeX-produced maths PDFs keep the Unicode
# LIGATURES, and one 'fi' inside a title is enough -- one mathematics
# paper's section 2, 'The Field Equation as a Hamiltonian System with
# Inﬁnitely Many Degrees of Freedom', was rejected on that single
# character, so its introduction slice swallowed two thirds of the paper.
# U+FB00-FB06 are therefore title characters.
_SEC = r'(?:§\s*|Section\s+)?'
# Wiley journals
# (AJIM, newer HSR) set the number and title apart with a bar --
# '1 | INTRODUCTION', '2.2.3 | Independent neighborhood SE variables'.
# P1_NUM demanded the title straight after the number, so all five chapters
# of P63 produced no candidate at all (not even a rejection).
_BAR = r'(?:\|\s*)?'
P1_NUM = re.compile(r'^\s*' + _SEC + r'(\d{1,2}(?:\.\d{1,2}){0,2})\.?\s+' + _BAR + r'([A-Z~]' + T + r'{3,150})\s*$')
# 'Part I: Group Health and Employer Insurance:
# Parallel Health Care Reimbursement' (P18, NBER WP) -- 11 words, past
# P1_BARE's word cap, so the chapter was dropped silently. Working papers and
# reports number top-level chapters 'Part I:' / 'Chapter 2.'.
# Same Wiley bar, as PyMuPDF lays it out: the number alone on one line, then
# '| INTRODUCTION' (P63 re-extracted 2026-10-07). The number is read back
# from the previous non-blank line.
P1_BARHEAD = re.compile(r'^\s*\|\s*([A-Z~]' + T + r'{3,150})\s*$')
_BARE_NUM = re.compile(r'^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\s*$')
P1_PART = re.compile(r'^\s*((?:Part|PART|Chapter|CHAPTER)\s+(?:[IVX]{1,6}|\d{1,2}))\s*[:.\-–—]?\s+([A-Z]' + T + r'{3,150})\s*$')
P1_ROM = re.compile(r'^\s*' + _SEC + r'([IVX]{1,6})\.\s+([A-Za-z~]' + T + r'{3,150})\s*$')
P1_LET = re.compile(r'^\s*([A-H])\.\s+([A-Z]' + T + r'{3,150})\s*$')
# Curly apostrophe admitted 2026-10-07: "Description of the Plan
# Members’" (a health-policy paper, a top-level chapter) failed on the ’ alone.
P1_BARE = re.compile(r'^\s*([A-Z][A-Za-z]+(?:[ ,:&\'’\-]+[A-Za-z0-9\'’\-\.]+){1,9})\s*$')
# Roman numeral WITHOUT a period: 'V Survey Evidence' (a health-policy
# NBER paper). P1_ROM demands 'V.' and P1_BARE's first token needs two letters, so a
# one-letter numeral fell through both. Accepted only when the title is
# title-case (checked at the call site) -- 'I was told ...' must not pass.
P1_ROM_NP = re.compile(r'^\s*([IVX]{1,6})\s+([A-Z]' + T + r'{3,150})\s*$')
# Single-word bare heading: 'Conclusion' (ChenYuZhang2013 L820) is a real
# chapter title and P1_BARE's {1,9} makes >=2 words mandatory, so it was missed.
P1_WORD = re.compile(r'^\s*([A-Z][A-Za-z]{3,25})\s*$')

P2_NUM = re.compile(r'^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\.?\s+([A-Z][A-Za-z0-9 ,:;&\'\-\(\)/]{3,60}?)\s+(?=[A-Z][a-z])')
P2_CAPS = re.compile(r'^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\.?\s+([A-Z][A-Z0-9 ,:;&\'\-\(\)/]{3,70}?)\s+(?=[A-Z][a-z])')
# Tail-glued. Two refinements forced by DambraQuinnWertz2023:
#   (a) a footnote marker can sit between the sentence period and the section
#       number -- "...rent seeking.9 4. Sample, Research Design, ..."
#   (b) a line can end with TWO headings, chapter then subsection --
#       "... 2. Background and Legislative History 2.1 Multiemployer pension plans"
P3 = re.compile(
    r'[.:;)]\d{0,2}\s+'
    r'(\d{1,2})\.\s+([A-Z][A-Za-z ,:;&\'\-\(\)/]{4,60}?)'
    r'(?:\s+(\d{1,2}\.\d{1,2})\.?\s+([A-Z][A-Za-z ,:;&\'\-\(\)/]{3,50}))?'
    r'\s*$')

# RUN-IN HEADINGS. Mid-century
# journals set the section title and its first sentence on ONE line --
# "2. The particular solutions. In this section, we construct the particular
# solutions of equations (1.9)..." (r06_MorreyCB1958, Amer. J. Math. 1958,
# 388 chars). Such a line falls into a gap: too long for the P1 branch
# (<200) and invisible to P2_NUM, whose title class excludes '.' and which
# then demands a SPACE before the body -- a run-in heading gives it '. '.
# Both of Morrey's interior chapters were lost this way. The title is the
# run of non-period characters between the section number and the first
# sentence-ending period followed by a capital.
P4_RUNIN = re.compile(r'^\s*(\d{1,2})\.\s+([A-Z][^.]{3,70}?)\.\s+[A-Z]')

STOP_SECTION = re.compile(r'^\s*(references|bibliography|reference list|works cited)\s*$', re.I)
APPENDIX = re.compile(r'^\s*(appendix|appendices)\b', re.I)

# FACTORY PARAMETERIZATION: the parent's headword list is quantitative-
# social-science-biased (identif|endogen|placebo...).  A field declares
# its own regex fragment in field-config.yaml (headwords:); empty means
# title-case detection carries recall alone.  Parent list kept below as
# a commented reference.
# HEADWORDS = re.compile(
#     r'\b(introduction|background|institution|regulat|literature|hypothes|theor|'
#     r'data|sample|method|design|strateg|identif|empiric|result|analys|'
#     r'robust|sensitivit|endogen|placebo|alternative|additional|extended|'
#     r'conclusion|conclud|discussion|summar|implication|evidence|model|framework|'
#     r'estimat|specification|test|effect|determinant|impact|relation|setting|'
#     r'measure|construct|statistic|abstract|remark|finding)', re.I)
import _jobs
_hw = _jobs.headwords_re()
HEADWORDS = re.compile(_hw, re.I) if _hw else None

# with `headwords` empty -- the template
# default -- a single-word heading was emitted only on a headwords match, so
# unnumbered `Methods`, `Results`, `Discussion`, `Background` vanished; and a
# sentence-case heading ('Study population and data') failed titleish(). This
# small genre-neutral vocabulary rescues both. It is NOT the parent's econ
# list; a field's own `headwords` still takes precedence where declared.
GENERIC_SECTION = re.compile(
    r'^(?:abstract|summary|introduction|background|context|objectives?|'
    r'methods?|methodology|materials?|data|study|sample|population|setting|'
    r'participants?|measures?|outcomes?|variables?|analys[ie]s|statistical|'
    r'design|results?|findings|discussion|limitations?|strengths?|'
    r'conclusions?|implications?|policy|acknowledg(?:e)?ments?|appendix|'
    r'references|bibliography|supplementary|'
    # end-matter sections (working papers: 'Figures' / 'Tables' after the
    # conclusion -- without them a conclusion slice runs through every table)
    r'figures|tables|exhibits)\b', re.I)
_FINITE = re.compile(r'\b(?:was|were|is|are|has|have|had|be|been|did|does|'
                     r'do|can|could|may|might|will|would|should)\b', re.I)


def despace(title):
    """Letter-spaced capitals from some publishers' fonts survive extraction
    as 'M E TH O D S', 'RE SULTS', 'C ONC LU SI ON S' (P63), 'M ETHODS' (HSR).
    Collapse ONLY when the collapsed form is a generic section word and the
    spaced form is not -- 'DATA AND METHODS' is left alone. Applied to the
    candidate's display string (`verbatim`); `title` stays literal because
    a2_build locates it in the source line."""
    if ' ' in title and title.upper() == title:
        flat = title.replace(' ', '')
        if (len(flat) <= 30 and GENERIC_SECTION.match(flat)
                and not GENERIC_SECTION.match(title)):
            return flat
    return title


def heading_word(t):
    """Single-word / sentence-case rescue: field headwords first, else the
    generic section vocabulary."""
    if HEADWORDS is not None and HEADWORDS.search(t):
        return True
    return bool(GENERIC_SECTION.match(t.strip()))

# Sentence-initial words: a heading essentially never starts with these.
# This is the high-precision footnote killer.
STOPINIT = re.compile(
    r'^(we|our|i|my|this|that|these|those|the|a|an|it|there|they|he|she|'
    r'in|on|at|to|for|from|by|with|as|if|when|while|since|because|although|'
    r'however|thus|therefore|prior|following|see|note|notes|source|sources|'
    r'all|both|each|such|one|two|three|first|second|third|more|most|many|'
    r'using|use|used|based|given|due|unlike|specifically|similarly|likewise|'
    r'appendix)\b', re.I)

CAPTION = re.compile(r'^\s*(table|figure|fig|panel|exhibit|chart|graph|plate)\b', re.I)
NUMTOK = re.compile(r'(?<![A-Za-z])[-+]?\d[\d,\.]*%?(?![A-Za-z])')
YESNO = re.compile(r'\b(yes|no)\b', re.I)


# FIELD ADAPTATION (mathematics, 2026-08-29): a maths heading routinely
# carries numbers -- theorem numbers, equation numbers, exponents, parameter
# values.  Measured: '5. The case p = 2; proof of Theorem 1.3' was rejected as
# a table row on its three numerals, losing a real chapter of 09_IanniI2012.
# The discriminator that still works is that a TABLE row has bare numbers with
# no connective prose, so numbers bound to a named object (Theorem 1.3,
# equation (2.4), p = 2) are discounted before the count is taken.
# the word list was SINGULAR only,
# so 'Proofs of Theorems 1 and 2' (r46_SirakovB2007 L887, a real chapter) kept
# both numerals free and tableish() rejected it as a table row. Maths chapters
# routinely discharge several numbered results at once -- 'Proofs of Theorems
# 1 and 2', 'Proof of Lemmas 3.1 and 3.2'. Plurals are now bound too, and a
# trailing 'and <n>' after a bound reference is absorbed with it.
_BOUND_NUM = re.compile(
    r'(?i)(?:theorems?|lemmas?|propositions?|corollar(?:y|ies)|remarks?|'
    r'sections?|chapters?|equations?|eqs?\.|figs?\.|figures?|tables?|steps?|'
    r'cases?|parts?|problems?)\s*\(?\d[\d.]*(?:\s*(?:,|and)\s*\(?\d[\d.]*)*|'
    r'[A-Za-z]\s*[=<>≤≥≠]\s*[-+]?\d[\d.]*')


def tableish(t):
    """A heading never carries two FREE numbers, nor a row of Yes/No cells."""
    nums = NUMTOK.findall(_BOUND_NUM.sub(" ", t))
    if len(nums) >= 2:
        return True, f'table row ({len(nums)} numeric tokens)'
    toks = re.findall(r"[A-Za-z][A-Za-z'\-]*", t)
    if toks and len(YESNO.findall(t)) / len(toks) >= 0.4:
        return True, 'table row (Yes/No cells)'
    return False, ''


def dehead(s):
    """Census key for running headers: page numbers vary, the rest does not.
    'Jeffrey R. Brown 179' / '... 183' / '... 187' collapse to one key."""
    return re.sub(r'\d+', '#', norm(s))


def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    return raw.decode('utf-8', errors='replace').split('\n')


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def titleish(t):
    """ALL-CAPS, or Title Case (most content words capitalised)."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", t)]
    if not words:
        return False
    if all(w.isupper() for w in words if len(w) > 2):
        return True
    minor = {'and', 'or', 'of', 'the', 'a', 'an', 'in', 'on', 'for', 'to',
             'with', 'from', 'by', 'at', 'as', 'vs', 'versus', 'into', 'over'}
    content = [w for w in words if w.lower() not in minor]
    if not content:
        return False
    return sum(1 for w in content if w[0].isupper()) / len(content) >= 0.8


def numbered_ok(title):
    """A NUMBERED bare line is either a chapter heading or a numbered footnote.
    The discriminator is NOT the opening word -- NovyMarx2015's real section IV
    is 'The Value of State ABO Pension Promises...' and starts with 'The'.
    It is sentence-hood: a footnote is a complete sentence and ends in a period;
    a heading does not."""
    if title.rstrip().endswith('.') and not re.search(r'\b[A-Z]\.$', title.rstrip()):
        return False, 'numbered footnote (complete sentence, ends in period)'
    if re.search(r'https?://|www\.', title):
        return False, 'numbered footnote (contains URL)'
    # A sentence boundary is a period NOT preceded by a digit. Without the
    # lookbehind this rule eats chapter+subsection double headings, where the
    # period belongs to the section number: RauhStefanescuZeldes2020's
    # '4 Empirical tests: Data and methodology 4.1. Sample selection' and
    # '5 Results 5.1. Accrual comparisons' -- the paper's data and results
    # chapters -- were both destroyed by it.
    if re.search(r'(?<![0-9])\.\s+[A-Z]', title) and not titleish(title):
        return False, 'numbered footnote (sentence boundary inside)'
    # A NUMBERED line beginning with an article is a heading far more often
    # than a footnote in mathematics -- '5 A compactness lemma',
    # '3 The unconstrained case'.  The stopword test keeps its bite for
    # sentence-initial pronouns and connectives, which never open a title.
    # STOPINIT carries 'appendix'
    # as a footnote-killer, but a NUMBERED line opening with it is an appendix
    # CHAPTER, not a footnote -- '7 Appendix: Computation of beta_i(lambda) for
    # N = 1' (r53_WeiJC2022 L3990) was killed outright. titleish() could not
    # save it either: Greek in the title ('βi') yields the bare lowercase token
    # 'i' from the [A-Za-z] word scan, dragging title-case to 0.75 < 0.8.
    # An explicit appendix exemption is the honest fix; the ratio is not.
    if (STOPINIT.match(title) and not titleish(title)
            and not APPENDIX.match(title)
            and not re.match(r'(?i)^(a|an|the)\s+\S', title)):
        return False, 'numbered footnote (stopword-initial, not title-case)'
    return True, ''


def glued_ok(title):
    """Accept a GLUED candidate only if it looks like a title, not a sentence."""
    if STOPINIT.match(title):
        return False, 'glued: sentence-initial stopword'
    if len(title) > 70:
        return False, 'glued: too long'
    if not ((HEADWORDS is not None and HEADWORDS.search(title))
            or titleish(title)):
        return False, 'glued: neither headword nor title-case'
    return True, ''


def extract(lines):
    n = len(lines)
    cutoff = n
    for i in range(n - 1, max(0, int(n * 0.45)), -1):
        if STOP_SECTION.match(despace(norm(lines[i]))):  # 'RE F ER EN CES'
            cutoff = i
            break

    census = collections.Counter(dehead(l) for l in lines if 3 < len(norm(l)) < 90)
    # Format = how prose is laid out. B (line-per-PDF-line) has a HIGH median
    # line length and no runaway tail; A (reflowed) has a tiny median (table
    # fragments) plus very long paragraph-lines. Median is the discriminator,
    # not the count of long lines -- IPW2022 median 82 / max 156 vs
    # DQW2023 median 6 / max 2540.
    lens = sorted(len(l) for l in lines)
    med = lens[len(lens) // 2] if lens else 0
    mx = lens[-1] if lens else 0
    fmt = 'B' if (med >= 40 and mx < 400) else ('A' if mx > 800 else 'mixed')

    cands, rejected = [], []

    def emit(idx, num, title, pat, level=None, flags=None):
        title = norm(title)
        if not title:
            return
        full = norm(f"{num} {despace(title)}") if num else despace(title)
        if census[dehead(lines[idx])] >= 3 and len(lines[idx]) < 90:
            rejected.append(dict(line=idx + 1, verbatim=full, pattern=pat,
                                 reason='running header (repeats >=3x, page no. masked)'))
            return
        bad, why = tableish(title)
        if bad:
            rejected.append(dict(line=idx + 1, verbatim=full, pattern=pat, reason=why))
            return
        if level is None:
            level = num.count('.') + 1 if num and '.' in num else 1
        cands.append(dict(line=idx + 1, num=num or '', title=title, verbatim=full,
                          level=level, pattern=pat, flags=flags or []))

    def reject(idx, num, title, pat, reason):
        rejected.append(dict(line=idx + 1, verbatim=norm(f"{num} {title}"),
                             pattern=pat, reason=reason))

    for i in range(cutoff):
        s = lines[i].rstrip()
        if not s.strip():
            continue
        stripped = s.strip()

        # ---------- P1: bare heading on its own line ----------
        if len(stripped) < 200:
            hit = None
            m = P1_NUM.match(s)
            if m:
                hit = (m.group(1), m.group(2), 'P1-num', None)
            elif (m := P1_ROM.match(s)):
                hit = (m.group(1) + '.', m.group(2), 'P1-rom', 1)
            elif (m := P1_LET.match(s)):
                hit = (m.group(1) + '.', m.group(2), 'P1-let', 2)
            elif (m := P1_PART.match(s)):
                hit = (m.group(1), m.group(2), 'P1-part', 1)
            elif (m := P1_BARHEAD.match(s)):
                j = i - 1
                while j >= 0 and not lines[j].strip():
                    j -= 1
                pm = _BARE_NUM.match(lines[j]) if j >= 0 else None
                num = pm.group(1) if pm else ''
                hit = (num, m.group(1), 'P1-bar', None if num else 1)
            elif (m := P1_ROM_NP.match(s)) and titleish(m.group(2)):
                hit = (m.group(1), m.group(2), 'P1-rom', 1)
            if hit:
                num, ttl, pat, lvl = hit
                ok, why = numbered_ok(norm(ttl))
                if ok:
                    emit(i, num, ttl, pat, lvl)
                    continue
                # Rejected as a footnote -- but do NOT `continue`. '.' has to
                # stay in the title class ('5 Sensitivity analysis ... SFAS
                # No. 158'), which lets P1_NUM swallow a whole opening
                # sentence: '1. Introduction Pension funding shortfalls
                # remain ... States.' Falling through lets the glued branch
                # recover the real heading, which is exactly what happens for
                # DambraQuinnWertz2023 L12.
                reject(i, num, ttl, pat, why)
            if APPENDIX.match(stripped) and len(stripped) < 90:
                emit(i, '', stripped, 'P1-appendix', 1); continue
            # Unnumbered letter-spaced caps ('M ETHODS', P09 L121): not one
            # word, not title-case prose -- every other branch misses it, and
            # recall.py's +/-2 tolerance hid the miss behind the subsection
            # heading on the next line (2026-10-07).
            if stripped.upper() == stripped and despace(stripped) != stripped:
                emit(i, '', stripped, 'P1-spaced', 1, ['unnumbered', 'letter-spaced'])
                continue
            m = P1_WORD.match(s)
            if m and not heading_word(stripped):
                # A single word whose section NUMBER sits alone on the previous
                # non-blank line -- '5' / '' / 'Estimation' (a health-policy
                # NBER paper via pdftotext). The number is the evidence the
                # vocabulary test cannot supply.
                # Table cells look the same ('30.9' / 'Male'), so the layout
                # must match too: a blank line between number and word, a blank
                # line after the word, and a section-sized number (page numbers
                # like '21' / '27' sit above headings in the same way).
                j = i - 1
                while j >= 0 and not lines[j].strip():
                    j -= 1
                pm = _BARE_NUM.match(lines[j]) if j >= 0 else None
                if (pm and j < i - 1 and int(pm.group(1).split('.')[0]) <= 12
                        and (i + 1 >= len(lines) or not lines[i + 1].strip())):
                    emit(i, pm.group(1), stripped, 'P1-word', None, ['numbered-above'])
                    continue
            if m and heading_word(stripped):
                emit(i, '', stripped, 'P1-word', 1, ['unnumbered']); continue
            if 6 < len(stripped) < 85 and P1_BARE.match(s):
                # NOTE: STOPINIT is deliberately NOT applied to bare lines.
                # Real chapter headings do start with "The"/"Both"
                # (Brown2008: "The U.S. Corporate Pension Landscape", "The Way
                # Forward"). STOPINIT is precise only for GLUED candidates,
                # where the rival hypothesis is footnote prose.
                prev_blank = i == 0 or not lines[i - 1].strip()
                if CAPTION.match(stripped):
                    reject(i, '', stripped, 'P1-bare', 'table/figure caption')
                elif titleish(stripped) or (HEADWORDS is not None
                                            and HEADWORDS.search(stripped)):
                    emit(i, '', stripped, 'P1-bare', 1, ['unnumbered'])
                elif (GENERIC_SECTION.match(stripped) and prev_blank
                      and len(stripped.split()) <= 6
                      and not _FINITE.search(stripped)):
                    # sentence-case heading ('Study population and data'):
                    # section-word start, short, verbless, after a blank line
                    emit(i, '', stripped, 'P1-sentcase', 1,
                         ['unnumbered', 'sentence-case'])
                else:
                    reject(i, '', stripped, 'P1-bare', 'neither title-case nor headword')
                continue

        # ---------- P4: run-in heading (title + first sentence, one line) ----------
        # Runs AFTER P1 (so a clean bare heading still wins) and BEFORE the
        # glued branch, whose patterns cannot see a title that ends in a period.
        m = P4_RUNIN.match(s)
        if m:
            _num, _ttl = m.group(1), norm(m.group(2))
            ok, why = numbered_ok(_ttl)
            if ok:
                emit(i, _num, _ttl, 'P4-runin', 1, ['run-in'])
                continue
            reject(i, _num, _ttl, 'P4-runin', why)

        # ---------- P2 / P3: glued into a reflowed line ----------
        # Threshold is 90, not 200: shi2023multiemployer's five real chapter
        # headings sit on 134-181 char lines and fell into the gap between the
        # bare branch (<130) and a 200 gate -- they produced ZERO candidates.
        if len(s) > 90:
            m = P2_CAPS.match(s) or P2_NUM.match(s)
            if m:
                ok, why = glued_ok(norm(m.group(2)))
                if ok:
                    emit(i, m.group(1), m.group(2), 'P2-head', flags=['glued-head'])
                else:
                    reject(i, m.group(1), m.group(2), 'P2-head', why)
            m = P3.search(s)
            if m:
                for num, ttl in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
                    if not num:
                        continue
                    ok, why = glued_ok(norm(ttl))
                    if ok:
                        emit(i, num, ttl, 'P3-tail', flags=['glued-tail'])
                    else:
                        reject(i, num, ttl, 'P3-tail', why)

    return cands, rejected, fmt, cutoff, n


def flag_nonmonotone(cands):
    """FLAG ONLY -- never drop. Sparse detection makes a hard monotone rule
    destroy the very headings it is meant to protect (DQW2023 lost '3.' and
    '6.' that way in v1)."""
    tops = [(idx, int(c['num'].rstrip('.')))
            for idx, c in enumerate(cands)
            if c['num'] and '.' not in c['num'] and c['num'].rstrip('.').isdigit()]
    if not tops:
        return cands
    # longest increasing subsequence over the top-level numbers
    best = []
    for i in range(len(tops)):
        chain = [tops[i]]
        for j in range(i + 1, len(tops)):
            if tops[j][1] > chain[-1][1]:
                chain.append(tops[j])
        if len(chain) > len(best):
            best = chain
    spine = {idx for idx, _ in best}
    for idx, _ in tops:
        if idx not in spine:
            cands[idx]['flags'] = cands[idx].get('flags', []) + ['off-spine']
    return cands


def main():
    with open(KEYS, encoding='utf-8') as fh:   # pinned: bare open() uses the
        keys = [l.strip() for l in fh if l.strip()]   # locale codepage (e.g. cp936)
    out = {}
    tot_c = tot_r = 0
    for k in keys:
        lines = load(os.path.join(CORPUS, k + '.txt'))
        cands, rej, fmt, cutoff, total = extract(lines)
        cands = flag_nonmonotone(cands)
        out[k] = dict(format=fmt, total_lines=total, ref_cutoff=cutoff,
                      candidates=cands, rejected=rej)
        tot_c += len(cands); tot_r += len(rej)
        off = sum(1 for c in cands if 'off-spine' in c.get('flags', []))
        print(f"{k:44s} fmt={fmt:5s} lines={total:5d} cand={len(cands):3d} "
              f"(off-spine {off:2d})  rej={len(rej):3d}")
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\ntotal candidates {tot_c} | rejected {tot_r}\nwrote {OUT}")


if __name__ == '__main__':
    main()
