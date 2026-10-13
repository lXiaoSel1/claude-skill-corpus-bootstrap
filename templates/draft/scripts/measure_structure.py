#!/usr/bin/env python3
"""Measure the writing canon's STRUCTURAL claims against this skill's corpus.

WHY THIS EXISTS
    structure-canon.md distills Swales 2004, Head, Evans, Cochrane, Bellemare,
    McCloskey and the econ genre-analysis literature into rules.  This skill's
    iron law does not exempt authorities: a canon rule enters the checker only
    with a corpus number beside it, and a rule the corpus contradicts is
    recorded as refuted.  This script produces every number, and writes
    references/structure-norms.json for check_drift and the canon to quote.

DATA LAYERS -- three, with different denominators, never mixed silently
    A. TAGGED-18: records/_superseded/introduction-tagged.md carries exact
       per-paragraph move sequences for 18 papers (8 old move labels).  The
       only layer with exact move order; cyclicity/order/typing read from it.
       CAVEAT: old 8 labels (opener stakes theory-tension mechanism-claim
       methods results contribution gap) map only approximately onto the
       introduction chapter's 8 parts.
    B. SLICES-59: references/slices/introduction/*.txt, lexical-marker
       measurements (question position, roadmap, antecedents PROXY).
       A "paragraph" is a line >= MIN_PARA_CHARS -- the corpus stores one
       paragraph per line, and shorter lines are mastheads/footnote debris.
    C. FULL-60: the mimic-lit corpus text of the keys60 sample, for
       previews/recalls and the meta-sentence share (McCloskey).
    D. ATTRIB-LB: per-part attested-paper counts parsed from the 49 part
       files' "-- PaperKey" attributions.  A LOWER BOUND on part presence
       (examples are selective); typing from this layer alone is never
       "obligatory", only "attested-in >= n/den".

RUN
    py scripts/measure_structure.py            # report + write norms json
    py scripts/measure_structure.py --dry      # report only
"""
import collections
import glob
import json
import os
import re
import sys

# Console-safety: corpus text carries U+FFFD on decode; cp936 console would
# crash on print.  Same guard as every script in this tree.  Never remove.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REF = os.path.join(SKILL, "references")
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402
CORPUS_DIR = _jobs.corpus_dir()
LIT = os.path.normpath(os.path.join(CORPUS_DIR, "..", ".."))
CORPUS = CORPUS_DIR
sys.path.insert(0, os.path.join(LIT, "scripts"))
from textseg import split_sentences, paragraph_texts, clean_prose  # noqa: E402  (shared)

TAGGED = os.path.join(REF, "records", "_superseded", "introduction-tagged.md")
# FACTORY PARAMETERIZATION: layer B measures the INTRODUCTION-EQUIVALENT
# chapter -- where a paper states its question, positions itself and (in some
# fields) states its results.  The parent called that job "introduction"; this
# field calls it "frame".  Read the name from the config's `intro_job`, else
# fall back to the first non-abstract job in the approved taxonomy.  Hardcoding
# the parent's name crashed this script outright on a mathematics instance.
_jb = _jobs.jobs()
# intro_job is a documented field-config key since 2026-10-07 (it was read
# here but never declared in the template config); default = the first job
# after the front positional block.
_intro = _jobs.intro_job() or "introduction"
SLICES = os.path.join(REF, "slices", _intro)
# FACTORY: the sample list is pipeline/sample-keys.txt at the skill root
# (the parent kept pipeline/ inside references/ and called it keys60.txt).
KEYS60 = os.path.join(SKILL, "pipeline", "sample-keys.txt")
SECTIONS = os.path.join(REF, "sections")
OUT = os.path.join(REF, "structure-norms.json")

MIN_PARA_CHARS = 100

# Swales 2004 typing thresholds (structure-canon.md quotes these).
OBLIGATORY = 0.95
OPTIONAL_FLOOR = 0.40


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ---------------------------------------------------------------- layer A
def parse_tagged():
    """{paper: [(move, n_sent), ...]} in paragraph order, 18 papers."""
    text = read(TAGGED)
    out = {}
    cur = None
    for line in text.split("\n"):
        m = re.match(r"^### (\S+)", line)
        if m:
            cur = m.group(1)
            out[cur] = []
            continue
        m = re.match(r"^\W*\d+\s*\|\s*move:\s*([a-z-]+)\s*\|.*?\|\s*(\d+)\s*sent\s*\|", line)
        if m and cur:
            out[cur].append((m.group(1), int(m.group(2))))
    return {k: v for k, v in out.items() if v}


def layer_a(tagged):
    moves = ["opener", "stakes", "theory-tension", "mechanism-claim",
             "methods", "results", "contribution", "gap"]
    n = len(tagged)

    presence = {mv: sum(1 for seq in tagged.values()
                        if any(m == mv for m, _ in seq)) for mv in moves}

    def typing(k):
        r = k / n
        return "obligatory" if r >= OBLIGATORY else (
            "optional" if r >= OPTIONAL_FLOOR else "rare")

    # cyclicity: a REVISIT is a paragraph whose move already appeared and at
    # least one different move intervened since its last appearance.
    revisits = {}
    for p, seq in tagged.items():
        mv = [m for m, _ in seq]
        rev = 0
        for i, m in enumerate(mv):
            j = max((k for k in range(i) if mv[k] == m), default=None)
            if j is not None and any(mv[k] != m for k in range(j + 1, i)):
                rev += 1
        revisits[p] = (rev, len(mv))
    with_rev = sum(1 for r, _ in revisits.values() if r)
    long_p = {p: rl for p, rl in revisits.items() if rl[1] >= 10}
    short_p = {p: rl for p, rl in revisits.items() if rl[1] < 10}

    # order: mean normalized position (0=first paragraph, 1=last) per move
    pos = collections.defaultdict(list)
    for seq in tagged.values():
        L = len(seq)
        for i, (m, _) in enumerate(seq):
            pos[m].append(i / (L - 1) if L > 1 else 0.0)
    order = {}
    for mv in moves:
        xs = pos.get(mv, [])
        if xs:
            mean = sum(xs) / len(xs)
            sd = (sum((x - mean) ** 2 for x in xs) / len(xs)) ** 0.5
            order[mv] = {"mean_pos": round(mean, 3), "sd": round(sd, 3),
                         "n_paragraphs": len(xs)}

    # results share, paragraph- and sentence-weighted
    para_sh, sent_sh = [], []
    for seq in tagged.values():
        tp = len(seq)
        ts = sum(s for _, s in seq)
        rp = sum(1 for m, _ in seq if m == "results")
        rs = sum(s for m, s in seq if m == "results")
        if tp:
            para_sh.append(rp / tp)
        if ts:
            sent_sh.append(rs / ts)

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else 0.0

    return {
        "denominator": n,
        "presence": {mv: {"papers": presence[mv], "rate": round(presence[mv] / n, 3),
                          "typing": typing(presence[mv])} for mv in moves},
        "cyclicity": {
            "papers_with_revisit": with_rev,
            "rate": round(with_rev / n, 3),
            "long_intros_10plus": {"n": len(long_p),
                                   "with_revisit": sum(1 for r, _ in long_p.values() if r)},
            "short_intros": {"n": len(short_p),
                             "with_revisit": sum(1 for r, _ in short_p.values() if r)},
            "total_revisit_paragraphs": sum(r for r, _ in revisits.values()),
            "total_paragraphs": sum(l for _, l in revisits.values()),
        },
        "order": order,
        "results_share": {
            "paragraph_median": round(med(para_sh), 3),
            "sentence_median": round(med(sent_sh), 3),
            "paragraph_mean": round(sum(para_sh) / len(para_sh), 3),
            "sentence_mean": round(sum(sent_sh) / len(sent_sh), 3),
        },
    }


# ---------------------------------------------------------------- layer B
# 2026-10-07 (health-policy instance, Tier 4): IMRaD fields state the question as an AIM
# ("The aim of this study was to ...", "we sought to ...", "This study
# assessed ...") -- the economics-only list measured 0/51 by paragraph 2 on a
# corpus whose introductions end in an aim statement in 33 of 51 papers.
Q_MARKERS = re.compile(
    r"\b(?:this (?:paper|study|article|review|analysis) (?:addresses|examines|"
    r"studies|asks|investigates|analyzes|analyses|explores|tests|documents|"
    r"provides|assesses|assessed|evaluates|evaluated|estimates|estimated|"
    r"examined|investigated|explored|describes|described|quantifies|"
    r"quantified|compares|compared|aims|aimed|seeks|sought)|"
    r"we (?:ask|examine|study|investigate|address|analyze|analyse|explore|"
    r"test whether|ask whether|aim|aimed|sought|assess|assessed|evaluate|"
    r"evaluated|examined|investigated|quantify|describe|estimate)|"
    r"in this (?:paper|study|article|review),? we|"
    r"(?:this|the present|the current|our) (?:[\w-]+ ){0,2}?(?:paper|study|"
    r"article|review|analysis) (?:was designed to|aim(?:s|ed)? to|sought to|"
    r"attempt(?:s|ed)? to|had (?:\w+ )?aims?|evaluates|evaluated|assesses|"
    r"assessed|examines|examined)|"
    r"(?:aims?|objectives?|purposes?|goals?) (?:of|for) (?:this|the present|"
    r"the current|our|the) (?:[\w-]+ ){0,2}?(?:paper|study|article|review|"
    r"analysis|research|project|survey)|"
    r"(?:our|study) (?:aims?|objectives?|purposes?|goals?) (?:was|were|is|are)|"
    r"we (?:performed|conducted|carried out) an? (?:[\w-]+ ){0,2}?"
    r"(?:investigation|analysis|study|review))\b", re.I)


def _flat(s):
    """Line wraps are not word breaks: "purpose of this\\nstudy" must match."""
    return re.sub(r"\s+", " ", s)

ROADMAP = re.compile(
    r"\b(?:organi[sz]ed as follows|proceeds as follows|structured as follows|"
    r"(?:remainder|rest) of th(?:e|is) (?:paper|article|study)|"
    r"paper proceeds|proceed as follows)\b", re.I)

# FACTORY PARAMETERIZATION: the citation proxy must match the field's citation
# style.  Author-year fields cite "Smith (2020)"; numeric fields (mathematics,
# physics, engineering) cite "[15]", and the author-year regex then measures a
# flat zero -- which is exactly what a mathematics instance first reported
# (median 0 distinct cites per introduction, in a literature that cites
# heavily).  _fieldstyle reads the style from field-config.yaml.
import _fieldstyle
_NUM_CITE = re.compile(r"\[(\d{1,3}(?:\s*[,–-]\s*\d{1,3})*)\]"
                       r"|(?<=[a-z\)])[.,;]?(\d{1,3}(?:[,–-]\d{1,3})*)(?=\s[A-Z])")
# author-year: narrative "Smith (2019)" AND parenthetical "(Smith, 2019;
# Lee and Kim 2020a)" -- the 2026-08 pattern saw only the narrative form
_AY_CITE = re.compile(
    r"\b([A-Z][A-Za-z'’-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z'’-]+)?"
    r"(?:\s+et\s+al\.?)?)[\s,]*\(?\s*((?:19|20)\d{2}[a-z]?)")


def distinct_cites(text):
    """Distinct citations under the field's citation_style (author-year |
    numeric | mixed). Numeric bracket/superscript groups are expanded into
    their individual numbers ("[3-5]" -> 3, 4, 5)."""
    out = set()
    st = _fieldstyle.style()
    if st in ("author-year", "mixed"):
        out |= {("ay", a.lower(), y) for a, y in _AY_CITE.findall(text)}
    if st in ("numeric", "mixed"):
        for m in _NUM_CITE.finditer(text):
            grp = m.group(1) or m.group(2) or ""
            for part in re.split(r"\s*,\s*", grp):
                rng = re.split(r"\s*[–-]\s*", part)
                if (len(rng) == 2 and rng[0].isdigit() and rng[1].isdigit()
                        and 0 <= int(rng[1]) - int(rng[0]) < 50):
                    out |= {("n", str(i))
                            for i in range(int(rng[0]), int(rng[1]) + 1)}
                elif part.isdigit():
                    out.add(("n", part))
    return out


def layer_b():
    files = sorted(f for f in os.listdir(SLICES)
                   if f.endswith(".txt") and not f.startswith("_"))
    q_by2 = q_late = q_none = 0
    road = 0
    cites = []
    for f in files:
        text = read(os.path.join(SLICES, f))
        # 2026-10-07: paragraphs via the shared textseg recovery (line mode
        # for one-paragraph-per-line corpora, block mode for line-wrapped
        # pdftotext). The old "a line >= 100 chars" rule read wrapped slices
        # as almost no paragraphs, so "by paragraph 2" meant "by line 2".
        paras = [_flat(p) for p in paragraph_texts(text, min_chars=MIN_PARA_CHARS)]
        first2 = "\n".join(paras[:2])
        rest = "\n".join(paras[2:])
        if Q_MARKERS.search(first2):
            q_by2 += 1
        elif Q_MARKERS.search(rest):
            q_late += 1
        else:
            q_none += 1
        if ROADMAP.search(_flat(text)):
            road += 1
        cites.append(len(distinct_cites(text)))
    cites.sort()
    n = len(files)

    def pct(p):
        return cites[min(n - 1, int(p * (n - 1)))] if cites else 0

    return {
        "denominator": n,
        "question_position": {"by_para2": q_by2, "later": q_late,
                              "no_marker": q_none,
                              "by_para2_rate": round(q_by2 / n, 3)},
        "roadmap": {"papers": road, "rate": round(road / n, 3)},
        "antecedents_PROXY_distinct_cites_in_intro": {
            "median": pct(0.5), "p25": pct(0.25), "p75": pct(0.75),
            "min": cites[0] if cites else 0, "max": cites[-1] if cites else 0,
            "note": "distinct (name, year) pairs in the intro slice -- an upper"
                    " bound on 'closest studies discussed', since it counts"
                    " every parenthetical citation once",
        },
    }


# ---------------------------------------------------------------- layer C
PREVIEW = re.compile(
    r"\b(?:as we (?:will|shall) (?:see|show|discuss|argue)|"
    r"recall (?:from|that)|as (?:discussed|shown|noted|mentioned) "
    r"(?:above|below|earlier|in section)|we (?:will|shall) (?:return|see below)|"
    r"we now turn)\b", re.I)

META = re.compile(
    r"\b(?:this (?:paper|section|subsection)|in section \d|"
    r"organi[sz]ed as follows|proceeds as follows|"
    r"(?:remainder|rest) of th(?:e|is) paper|we now turn|"
    r"as (?:discussed|shown|noted) (?:above|below|earlier)|"
    r"the (?:next|following|previous) section|"
    r"summari[sz]e[sd]? (?:our|the|these)|to summari[sz]e|in summary|"
    r"as we (?:will|shall) (?:see|show))\b", re.I)


def layer_c():
    keys = [l.strip() for l in read(KEYS60).split("\n") if l.strip()]
    prev_counts, meta_shares, words_total, prev_total = [], [], 0, 0
    covered = 0
    for k in keys:
        path = os.path.join(CORPUS, k + ".txt")
        if not os.path.exists(path):
            continue
        covered += 1
        # 2026-10-07: same prose cut as attest.py and Tier 1 -- reference
        # lists are not sentences of the paper and diluted the meta share.
        t = clean_prose(read(path))
        w = len(t.split())
        pv = len(PREVIEW.findall(_flat(t)))
        prev_counts.append((pv / w * 10000) if w else 0.0)
        prev_total += pv
        words_total += w
        sents = split_sentences(t)
        if sents:
            meta_shares.append(sum(1 for s in sents if META.search(_flat(s))) / len(sents))
    prev_counts.sort()
    meta_shares.sort()

    def med(xs):
        return xs[len(xs) // 2] if xs else 0.0

    return {
        "denominator": covered,
        "previews_recalls": {
            "total": prev_total,
            "per_10k_median": round(med(prev_counts), 2),
            "per_10k_p90": round(prev_counts[int(0.9 * (len(prev_counts) - 1))], 2)
            if prev_counts else 0,
            "note": "conservative marker list; Cochrane's target is 0",
        },
        "meta_sentence_share": {
            "median": round(med(meta_shares), 4),
            "p90": round(meta_shares[int(0.9 * (len(meta_shares) - 1))], 4)
            if meta_shares else 0,
            "note": "share of sentences containing a meta/signpost marker;"
                    " LOWER BOUND (conservative list). McCloskey's complaint"
                    " is about drafts that are 'mostly' meta.",
        },
    }


# ---------------------------------------------------------------- layer D
# FACTORY: attribution comes in two shapes -- "— Key ¶n" and, where one paper
# contributes several sections to a chapter, "— Key §s ¶n".  The parent only
# ever produced the first, so the parent regex silently counted almost zero
# attestations on this instance (properties read 0/7 for every part while its
# Versions each carried three or four papers).  Both shapes, plus abstract's
# sentence unit "S<n>", must match.
ATTR = re.compile(r"—\s+([A-Za-z0-9][A-Za-z0-9_\-]+)"
                  r"(?:\s+§[^¶]*)?\s*(?:¶|S\d|T\d)")
# 2026-10-07: T-series (back-ports from a mathematics instance) and hyphenated keys, identical to
# check_drift's key_re -- the two counted different things before.

WITHHELD_STUB = re.compile(r"(?m)^### \(Version \d+ withheld\)")
WITHHELD_PART = re.compile(r"—\s*withheld\s*$")

# FACTORY PARAMETERIZATION: working denominators come from the instance
# registry (filled at Tier 3 from each record's own header), never from
# the parent's economics numbers.
import json as _json
with open(os.path.join(REF, 'registry.json'), encoding='utf-8') as _fh:
    _reg = _json.load(_fh)
# A chapter key is created at Tier 2 with value null and filled at Tier 3;
# a not-yet-filled chapter is skipped, not a crash (2026-10-07).
DENOMS = {ch: v['denominator']
          for ch, v in _reg.get('sections', {}).get('chapters', {}).items()
          if isinstance(v, dict) and v.get('denominator')}


def layer_d():
    out = {}
    for ch, den in DENOMS.items():
        d = os.path.join(SECTIONS, ch)
        # A chapter can legitimately have NO sections directory: an instance may
        # decide a chapter is out of scope for drafting (a mathematics instance does this for
        # `proof` and `machinery` -- formula chains, not prose, where a paragraph
        # skeleton means nothing).  Report the absence, do not crash on it.
        if not os.path.isdir(d):
            out[ch] = {"working_denominator": den, "parts": {},
                       "note": "no sections/ directory -- chapter out of drafting scope"}
            continue
        parts = {}
        for f in sorted(os.listdir(d)):
            if not f.endswith(".md") or f == "00-skeleton.md":
                continue
            body = read(os.path.join(d, f))
            keys = set(ATTR.findall(body))
            parts[f[:-3]] = {"attested_papers": len(keys),
                             "lb_rate": round(len(keys) / den, 3)}
            # 2026-10-07: Versions withheld pending an owner sign-off leave a
            # stub (`### (Version N withheld)`; a whole part: a "— withheld"
            # title and no Versions). Their papers are not counted, so the
            # bound is lowered by the withholding, not by the corpus -- say so.
            n_wh = len(WITHHELD_STUB.findall(body))
            if n_wh or WITHHELD_PART.search(body.split("\n", 1)[0]):
                parts[f[:-3]]["withheld"] = n_wh or "whole part"
        out[ch] = {"working_denominator": den, "parts": parts,
                   "note": "LOWER BOUND -- Version examples are selective;"
                           " a part can be present in papers never quoted"}
    return out


# FACTORY, added 2026-08-29 after a real drafting failure.  A drafter read the
# frame skeleton's "follow PaperX1993's placement, do not run Versions 22-26
# here" -- a rule about displayed THEOREMS -- and dropped every displayed
# EQUATION from the introduction as well.  The two are different objects and
# the corpus proves it: PaperX1993, the very paper named there, displays
# equations (1), (2) and hypothesis (A6) in its introduction and states no
# theorem at all.  Prose could not prevent that misreading; a printed count can.
#
# The proxy is deliberate.  Extracted PDF text has no \begin{equation}, so a
# displayed equation is counted by the NUMBER a paper gave it: a paper that
# labelled an equation displayed it.  That under-counts unnumbered displays and
# over-counts back-references to the same label, so the figure is an ORDER OF
# MAGNITUDE, never a target -- which is all a drafter needs to notice a zero.
EQ_LABEL = re.compile(r"\((?!(?:1[89]|20)\d{2}[a-z]?\))(\d+(?:\.\d+)*[a-z]?)\)")
# 2026-10-07: a 4-digit year in parentheses -- "(2019)", the author-year
# citation -- is never an equation label; counting it made every health
# introduction "carry equations" and draftcheck `section` FAIL a prose draft.
# Fields without displayed equations set `equation_layer: off` in
# field-config.yaml; layer E is then not measured and draftcheck skips it.
from _cfgparse import as_str as _as_str  # noqa: E402
EQUATION_LAYER = _as_str(_jobs._DATA.get("equation_layer"), "on") != "off"


def layer_e():
    """Displayed-equation density per chapter, from the slices."""
    root = os.path.join(REF, "slices")
    out = {}
    if not EQUATION_LAYER or not os.path.isdir(root):
        return out
    for job in sorted(os.listdir(root)):
        d = os.path.join(root, job)
        if not os.path.isdir(d):
            continue
        counts = []
        for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
            with open(f, encoding="utf-8", errors="replace") as fh:
                counts.append(len(set(EQ_LABEL.findall(fh.read()))))
        if not counts:
            continue
        counts.sort()
        n = len(counts)
        out[job] = {
            "papers": n,
            "median": counts[n // 2],
            "p25": counts[n // 4],
            "p75": counts[(3 * n) // 4],
            "max": counts[-1],
            "papers_with_zero": sum(1 for c in counts if c == 0),
            "_why": "distinct numbered equation labels in the chapter slice; a"
                    " PROXY for displayed equations (see EQ_LABEL comment)",
        }
    return out


def main():
    dry = "--dry" in sys.argv
    tagged = parse_tagged() if os.path.exists(TAGGED) else {}
    if tagged:
        print("A. TAGGED exact move sequences (%d papers)" % len(tagged))
        a = layer_a(tagged)
    else:
        print("A. TAGGED layer absent (no tagged record round in this instance) -- skipped")
        a = None
    if a:
        for mv, d in a["presence"].items():
            print("   %-16s %2d/%d = %5.1f%%  %s"
                  % (mv, d["papers"], a["denominator"], d["rate"] * 100, d["typing"]))
        cy = a["cyclicity"]
        print("   cyclicity: %d/%d papers revisit a move (%.0f%%);"
              % (cy["papers_with_revisit"], a["denominator"], cy["rate"] * 100))
        print("     long intros (>=10 para): %d/%d revisit · short: %d/%d"
              % (cy["long_intros_10plus"]["with_revisit"], cy["long_intros_10plus"]["n"],
                 cy["short_intros"]["with_revisit"], cy["short_intros"]["n"]))
        print("   results share of intro: median %.0f%% of paragraphs, %.0f%% of sentences"
              % (a["results_share"]["paragraph_median"] * 100,
                 a["results_share"]["sentence_median"] * 100))
        print("   order (mean normalized position, 0=start):")
        for mv, d in sorted(a["order"].items(), key=lambda kv: kv[1]["mean_pos"]):
            print("     %-16s %.2f (sd %.2f, n=%d)"
                  % (mv, d["mean_pos"], d["sd"], d["n_paragraphs"]))

    print("\nB. %s-slice lexical markers" % _intro)
    b = layer_b()
    q = b["question_position"]
    print("   question marker by para 2: %d/%d (%.0f%%) · later %d · none %d"
          % (q["by_para2"], b["denominator"], q["by_para2_rate"] * 100,
             q["later"], q["no_marker"]))
    print("   roadmap: %d/%d (%.0f%%)"
          % (b["roadmap"]["papers"], b["denominator"], b["roadmap"]["rate"] * 100))
    ap = b["antecedents_PROXY_distinct_cites_in_intro"]
    print("   distinct cites in intro (PROXY): median %d, IQR %d-%d, range %d-%d"
          % (ap["median"], ap["p25"], ap["p75"], ap["min"], ap["max"]))

    print("\nC. full-sample signposting")
    c = layer_c()
    print("   previews/recalls: %d total, median %.2f/10k, P90 %.2f/10k"
          % (c["previews_recalls"]["total"], c["previews_recalls"]["per_10k_median"],
             c["previews_recalls"]["per_10k_p90"]))
    print("   meta-sentence share: median %.1f%%, P90 %.1f%%"
          % (c["meta_sentence_share"]["median"] * 100,
             c["meta_sentence_share"]["p90"] * 100))

    print("\nD. ATTRIB-LB per-part attested papers (lower bounds)")
    dd = layer_d()
    for ch, info in dd.items():
        row = " · ".join("%s %d/%d%s" % (p.split("-", 1)[-1], v["attested_papers"],
                                         info["working_denominator"],
                                         " (withheld: %s)" % v["withheld"]
                                         if v.get("withheld") else "")
                         for p, v in info["parts"].items())
        print("   %-26s %s" % (ch, row))

    print("\nE. EQUATION DENSITY per chapter (proxy: distinct numbered labels)"
          + ("" if EQUATION_LAYER else " -- equation_layer: off, not measured"))
    ee = layer_e()
    for ch, info in sorted(ee.items()):
        flag = "" if info["papers_with_zero"] else "   <- NO paper has zero"
        print("   %-13s n=%2d  median %2d  P25 %2d  P75 %2d  max %2d  zero %d/%d%s"
              % (ch, info["papers"], info["median"], info["p25"], info["p75"],
                 info["max"], info["papers_with_zero"], info["papers"], flag))

    import datetime as _dt
    norms = {"_built": _dt.date.today().isoformat(),
             "_script": "scripts/measure_structure.py",
             "_layers": {"A": "tagged exact move sequences (null = no tagged round)",
                         "B": "intro-job slice lexical markers (textseg paragraphs)",
                         "C": "full-sample signposting (clean_prose text)",
                         "D": "part-attribution lower bounds",
                         "E": "displayed-equation density per chapter"},
             "A_tagged18": a, "B_slices": b, "C_full60": c, "D_attrib_lb": dd,
             "E_equation_density": ee,
             "thresholds": {"obligatory": OBLIGATORY,
                            "optional_floor": OPTIONAL_FLOOR,
                            "_why": "Swales 2004 three-way typing, adapted:"
                                    " >=95% obligatory, 40-95% optional,"
                                    " <40% rare/PISF"}}
    if not dry:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(norms, fh, indent=1, ensure_ascii=False)
        print("\nwrote", os.path.relpath(OUT, SKILL))


if __name__ == "__main__":
    main()
