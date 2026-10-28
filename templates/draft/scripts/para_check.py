#!/usr/bin/env python3
"""Fast lane step 3 -- every mechanical check of a drafted paragraph in one call.

FACTORY PORT (1.6.0) of the parent's `para_check.py`, plus a paragraph-shape
check: `--band LO-HI` (rendered words) and `--cites N` (distinct cited keys)
are must-pass when given, and the paragraph's place in its chapter's corpus
distribution (structure-norms.json layer F) is printed beside them.

Input (a file, - for stdin, or the text itself): the LaTeX paragraph, then a
line `=== map`, then one line per sentence that says which card lines it
rests on:
    <the sentence's first words> | KEY#R1 KEY#D2
    <first words of a sentence of the author's own> | -
Card lines come from `cards.py` (references/cards/<KEY>.md).

Checks (each prints one line, then the items to fix or review):
  MAP        every sentence that cites a paper rests on that paper's card lines;
             every cited key has a line; no line the note has and the paper lacks
  NUMBERS    each number in the paper it is attached to (the src logic)
  COPIED     no stretch of 7+ words shared with a cited paper
  LENGTH     no sentence over the chapter's P90; the rendered word count
             (citations as the .bbl prints them) within --cap / --band
  SHAPE      distinct cited keys within --cites; percentiles of the paragraph's
             words and citations in the chapter's corpus paragraphs
  STRENGTH   no word stronger than the card lines it rests on, no hedge dropped
  WORDING    a field term (in 3+ corpus papers) inside a paper's clause that the
             paper itself never uses: the field's word put in the paper's mouth
  FRAMES     word pairs in 0 corpus papers (and the spans around them), words in
             0-2 papers -- the style-safe corpus, one pass for the paragraph
  CITATIONS  keys per citation command (how many share a block)
Exit 1 when MAP, NUMBERS, COPIED, LENGTH or SHAPE fails; STRENGTH, WORDING and
FRAMES are REVIEW items, kept or fixed by judgment.

RUN
    py -3 scripts/para_check.py <input> [--chapter <job>] [--cap WORDS] [--band LO-HI] [--cites N]
"""
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _src  # noqa: E402
import _tiers  # noqa: E402
import _ngram  # noqa: E402
import cards  # noqa: E402
import draftcheck  # noqa: E402
import _jobs  # noqa: E402
from textseg import split_sentences  # noqa: E402  (draftcheck put the lit scripts on the path)

SHOW = 12                    # items printed per check
FIELD_MIN = 3                # papers that make a word sequence the field's (attest.py's ATTESTED_MIN)
# a pair counts as a term when it is in at least this share of its rarer word's
# papers: "riskier firms" 0.10 is a term, "can shift" 0.05 and "firms take" 0.06 are
# chance pairings (calibrated on the parent's 2026-10-17 test paragraphs)
TERM_TIE = 0.08
STOP = set("""a an the and or but nor of in on at to for from by with without within into onto over under
as than then that this these those which who whom whose what when where while whether if is are was were be
been being has have had do does did not no so such its their his her our we they it he she them us also more
most less least very much many both each either neither any all some other another same own only just even
between among across after before during about against through per via upon one two three
high low large small great new""".split())


def opt(a, name, conv=str):
    return conv(a[a.index(name) + 1]) if name in a else None


def args():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    band = opt(a, "--band")
    if band:
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", band)
        if not m:
            sys.exit("--band takes LO-HI, e.g. --band 100-170")
        band = (int(m.group(1)), int(m.group(2)))
    chapter, cites = opt(a, "--chapter"), opt(a, "--cites", int)
    # 1.6.1: with --chapter and no --band / --cites, the manuscript's own
    # target for that chapter (field-config paragraph_targets); flags win
    if chapter and (band is None or cites is None):
        t_band, t_cites = _jobs.paragraph_target(chapter)
        if band is None and t_band:
            band = t_band
            print("(band %d-%d from field-config paragraph_targets)" % band)
        if cites is None and t_cites is not None:
            cites = t_cites
            print("(max %d citations from field-config paragraph_targets)" % cites)
    return (draftcheck.read_arg(a[0]), opt(a, "--cap", int), chapter, band, cites)


# ---- rendering (for the word count) -------------------------------------------------
_LAB = None


def labels():
    """{cite key: (authors as printed, year)} from the manuscript's .bbl."""
    global _LAB
    if _LAB is None:
        _LAB = {}
        tex = _jobs.manuscript_paths()[0]
        p = os.path.splitext(tex)[0] + ".bbl" if tex else ""
        if p and os.path.isfile(p):
            text = open(p, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"\\bibitem\[(.*?)\((\d{4}[a-z]?)\)(.*?)\]\{([^}]+)\}", text, re.S):
                _LAB[m.group(4).strip()] = (re.sub(r"[{}]", "", m.group(1)).replace("~", " ").strip(), m.group(2))
    return _LAB


def rendered(raw):
    lab = labels()

    def one(m):
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        names = [lab.get(k, (k, "")) for k in keys]
        if _src.NARRATIVE.match(m.group(0)):
            return ", ".join("%s (%s)" % n for n in names)
        return "(" + "; ".join("%s, %s" % n for n in names) + ")"
    t = _src.CITE.sub(one, re.sub(r"(?<!\\)%.*", "", raw))
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t.replace("\\%", "%").replace("\\$", "$"))
    return re.sub(r"\s+", " ", re.sub(r"[{}~]", " ", t)).strip()


# ---- the chapter's paragraph shape (structure-norms.json layer F) --------------------
def shape_norms(chapter):
    p = os.path.join(draftcheck.REF, "structure-norms.json")
    if not chapter or not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return (json.load(fh).get("F_paragraph_shape") or {}).get(chapter)


def pct(value, samples):
    if not samples:
        return None
    below = sum(1 for x in samples if x < value)
    equal = sum(1 for x in samples if x == value)
    return round(100.0 * (below + 0.5 * equal) / len(samples))


# ---- clauses and the paper each one reports ------------------------------------------
def segments(s, marks, fallback):
    """[(text, owner keys)]: the words before a parenthetical citation belong to it,
    the words after a narrative citation (to the next citation) to that one. A
    lead-in that ends in a colon before the first citation ("Early studies fit
    the put-option view:") is the author's own: owner []."""
    out, last, pending = [], 0, None
    first = _src.PLACE.search(s)
    if first:
        head = s[:first.start()]
        colon = head.rfind(":")
        if colon > 0 and not marks[int(first.group(1))][1]:
            out.append((head[:colon], []))
            last = colon + 1
    for m in _src.PLACE.finditer(s):
        keys, narrative = marks[int(m.group(1))]
        chunk = s[last:m.start()]
        if narrative:
            if pending is not None:
                out.append((chunk, pending))
            elif chunk.strip():
                out.append((chunk, fallback))
            pending = keys
        else:
            out.append((chunk, keys if pending is None else pending + keys))
            pending = None
        last = m.end()
    tail = s[last:]
    if tail.strip():
        out.append((tail, pending if pending is not None else fallback))
    return [(_src.clean(t), ks) for t, ks in out if len(_src.WORD.findall(_src.clean(t).lower())) >= 2]


def raw_words(s):
    """The sentence's words with citations dropped but names such as MAP-21 kept."""
    t = re.sub(r"\\[A-Za-z]+\*?", " ", _src.PLACE.sub(" ", s))
    return [w for w in _src.WORD.findall(t.lower()) if not w.isdigit()]


def rendered_words(s, marks):
    """The sentence's words with each citation as its authors' surnames (no years)."""
    lab = labels()

    def names(m):
        keys, _narr = marks[int(m.group(1))]
        return " " + " ".join(lab.get(k, (k, ""))[0] for k in keys) + " "
    return [w for w in _src.WORD.findall(_src.clean(_src.PLACE.sub(names, s)).lower()) if not w.isdigit()]


def matches(prefix, cand):
    """The map line's first words are the sentence's first words (digits and
    citations aside): a subsequence of its first len+4 words, starting in the
    first three."""
    p = [w for w in prefix if not w.isdigit()]
    c = cand[:len(p) + 4]
    if not p or p[0] not in c[:3]:
        return False
    it = iter(c)
    return all(w in it for w in p)


_PAPER_GRAMS = {}


def paper_bigrams(key):
    if key not in _PAPER_GRAMS:
        g = set()
        for _label, _t, ws, _offs in cards.wordpos(key):
            g.update(zip(ws, ws[1:]))
        _PAPER_GRAMS[key] = g
    return _PAPER_GRAMS[key]


def runs(text):
    """Token runs of a clause, broken at punctuation and numbers (a frame never
    spans either)."""
    out = []
    for piece in re.split(r"[,;:()\[\]!?.]", text):
        cur = []
        for w in _ngram.tokens(piece):
            if w.isdigit():
                if cur:
                    out.append(cur)
                cur = []
            else:
                cur.append(w)
        if cur:
            out.append(cur)
    return out


def main():
    raw, cap, chapter, band, cites_max = args()
    para, _sep, maptext = raw.partition("\n=== map")
    sents, marks = _src.sentences(para, split_sentences)
    sents = [(s, ks) for s, ks in sents if len(_src.clean(s).split()) >= 3]
    clean = [re.sub(r"\s+", " ", _src.clean(s)).strip() for s, _ in sents]
    swords = [_src.WORD.findall(c.lower()) for c in clean]
    rwords = [rendered_words(s, marks) for s, _ in sents]
    must = []

    # ---- MAP ------------------------------------------------------------------------
    maps = {}
    bad_lines = []
    for l in maptext.strip().split("\n"):
        if "|" not in l:
            continue
        pre, ids = l.split("|", 1)
        want = _src.WORD.findall(pre.lower())[:6]
        hit = next((i for i, w in enumerate(swords) if i not in maps and want
                    and (matches(want, w) or matches(want, rwords[i]) or matches(want, raw_words(sents[i][0])))),
                   None)
        if hit is None:
            bad_lines.append(pre.strip())
            continue
        maps[hit] = [x for x in ids.split() if x.strip() and x.strip() != "-"]
    card_of = {}
    map_items = []
    for i, (s, keys) in enumerate(sents):
        ids = maps.get(i)
        if ids is None:
            if keys:
                map_items.append("S%d cites %s but has no map line" % (i + 1, ", ".join(keys)))
            continue
        mk = []
        for x in ids:
            if "#" not in x:
                map_items.append("S%d: %r is not KEY#ID" % (i + 1, x))
                continue
            k, lid = x.split("#", 1)
            if k not in card_of:
                card_of[k] = cards.load(k)
            c = card_of[k]
            if c is None:
                map_items.append("S%d: no card for %s (py -3 scripts/cards.py build %s)" % (i + 1, k, k))
            elif lid not in c:
                map_items.append("S%d: %s has no line %s" % (i + 1, k, lid))
            elif lid.startswith("Q") and c[lid][0].startswith("NOT IN PAPER"):
                map_items.append("S%d: %s#%s is in the note, not in the paper" % (i + 1, k, lid))
            mk.append(k)
            if keys and k not in keys:
                map_items.append("S%d rests on %s's card but does not cite %s" % (i + 1, k, k))
        for k in keys:
            if k not in mk:
                map_items.append("S%d cites %s but rests on none of its lines" % (i + 1, k))
    for p in bad_lines:
        map_items.append("map line %r matches no sentence's first words" % p[:40])
    if bad_lines or any(i not in maps for i, (_s, ks) in enumerate(sents) if ks):
        # what the map lines can start with: each sentence's first words, citations as authors
        map_items.append("sentence starts: " + " · ".join(
            "S%d %s" % (i + 1, " ".join(rwords[i][:4])) for i in range(len(sents))))
    print("PARA: %d sentences" % len(sents))
    print("MAP: %d of %d sentences mapped · %s" % (len(maps), len(sents), "problems %d" % len(map_items)
                                                   if map_items else "OK"))
    for x in map_items[:SHOW]:
        print("   " + x)
    if map_items:
        must.append("MAP")

    def keys_of(i):
        ks = list(sents[i][1])
        for x in maps.get(i, []):
            k = x.split("#", 1)[0]
            if k not in ks:
                ks.append(k)
        return ks

    # ---- NUMBERS ----------------------------------------------------------------------
    num_items, tally = [], {}
    for i, (s, _keys) in enumerate(sents):
        ks = keys_of(i)
        if not ks:
            continue
        own = _src.owners(_src.clean(s, keep_marks=True, drop_names=True), marks, ks)
        groups = {}
        for v, owner in own:
            groups.setdefault(tuple(owner), []).append(v)
        for owner, vals in groups.items():
            hit = [(w, k) for w, k in ((_src.where(k, vals), k) for k in owner) if w]
            if hit:
                w, k = min(hit)
                verdict = "TOGETHER" if w[0] <= _src.WIN else "APART"
                tally[verdict] = tally.get(verdict, 0) + 1
                if verdict == "APART":
                    num_items.append("S%d APART %s in %s %s" % (i + 1, " ".join(vals), k, w[1]))
                continue
            for v in vals:
                inside = next((k for k in owner if _src.where(k, [v])), None)
                other = next((k for k in ks if k not in owner and _src.where(k, [v])), None)
                verdict = "FOUND" if inside else ("ELSEWHERE" if other else "MISSING")
                tally[verdict] = tally.get(verdict, 0) + 1
                if verdict != "FOUND":
                    num_items.append("S%d %s %s (attached to %s%s)" % (
                        i + 1, verdict, v, "/".join(owner), (", but in " + other) if other else ""))
    print("NUMBERS: %s" % (" ".join("%s %d" % kv for kv in sorted(tally.items())) or "none"))
    for x in num_items[:SHOW]:
        print("   " + x)
    if any(x.split()[1] in ("ELSEWHERE", "MISSING") for x in num_items):
        must.append("NUMBERS")

    # ---- COPIED -----------------------------------------------------------------------
    cp = []
    for i in range(len(sents)):
        for k in keys_of(i):
            for n, stretch, loc in _src.copied(swords[i], k, _src.name_mask(clean[i])):
                cp.append("S%d %d words from %s %s: \"%s\"" % (i + 1, n, k, loc, stretch))
    print("COPIED (>= %d words): %d" % (_src.COPY_MIN, len(cp)))
    for x in cp[:SHOW]:
        print("   " + x)
    if cp:
        must.append("COPIED")

    # ---- LENGTH -----------------------------------------------------------------------
    p90, _n = draftcheck.chapter_p90(chapter)
    lens = [len(c.split()) for c in clean]
    over = [(i + 1, n) for i, n in enumerate(lens) if p90 and n > p90]
    total = len(rendered(para).split())
    limits = []
    if cap:
        limits.append("cap %d: %s" % (cap, "OK" if total <= cap else "OVER"))
    if band:
        limits.append("band %d-%d: %s" % (band[0], band[1], "OK" if band[0] <= total <= band[1]
                                           else ("UNDER" if total < band[0] else "OVER")))
    print("LENGTH: words per sentence %s · P90 %s: %s · rendered %d words%s" % (
        "/".join(str(n) for n in lens), p90, "none over" if not over else "over " + ", ".join(
            "S%d %dw" % o for o in over), total, (" (" + "; ".join(limits) + ")") if limits else ""))
    if over or (cap and total > cap) or (band and not band[0] <= total <= band[1]):
        must.append("LENGTH")

    # ---- SHAPE: cited keys and the chapter's corpus distribution ------------------------
    n_keys = len({k.strip() for m in _src.CITE.finditer(para) for k in m.group(1).split(",") if k.strip()})
    norms = shape_norms(chapter)
    where = ""
    if norms:
        where = " · in %s's corpus paragraphs (n=%d): words P%s, citations P%s (corpus P50 %s words, %s citations)" % (
            chapter, norms["paragraphs"], pct(total, norms.get("word_samples")),
            pct(n_keys, norms.get("cite_samples")), norms["words"]["p50"], norms["cites"]["p50"])
    elif chapter:
        where = " · no layer-F norm for %s (py -3 scripts/measure_structure.py)" % chapter
    cites_flag = ""
    if cites_max is not None:
        cites_flag = " (max %d: %s)" % (cites_max, "OK" if n_keys <= cites_max else "OVER")
        if n_keys > cites_max:
            must.append("SHAPE")
    print("SHAPE: %d distinct cited keys%s%s" % (n_keys, cites_flag, where))

    segs = []                       # (sentence no, clause text, owner keys)
    for i, (s, keys) in enumerate(sents):
        for text, ks in segments(s, marks, keys_of(i)):
            segs.append((i, text, ks))

    # ---- STRENGTH: each paper's clause against that paper's mapped lines ----------------
    st = []
    for i, text, ks in segs:
        lines = []
        for x in maps.get(i) or []:
            k, lid = x.split("#", 1) if "#" in x else (x, "")
            c = card_of.get(k) or {}
            if k in ks and lid in c:
                lines.append(c[lid][1])
        if lines:
            for f in _tiers.compare(text, lines):
                st.append("S%d (%s) %s" % (i + 1, "/".join(ks), f))
    print("STRENGTH vs the card lines: %d" % len(st))
    for x in st[:SHOW]:
        print("   REVIEW " + x)

    # ---- WORDING and FRAMES (one corpus pass) ---------------------------------------------
    grams = set()
    pairs_of = []
    for i, text, ks in segs:
        for r in runs(text):
            for n in (1, 2, 3, 4):
                grams.update(tuple(r[j:j + n]) for j in range(len(r) - n + 1))
            pairs_of.append((i, text, ks, r))
    df = _ngram.df(grams)
    wording = []
    for i, text, ks, r in pairs_of:
        if not ks:
            continue
        for a, b in zip(r, r[1:]):
            if a in STOP or b in STOP or len(a) < 3 or len(b) < 3:
                continue
            n2 = df.get((a, b), 0)
            if n2 < FIELD_MIN or any((a, b) in paper_bigrams(k) for k in ks):
                continue
            # a term, not a chance pairing: the pair is a real share of its rarer word's papers
            tie = n2 / float(max(1, min(df.get((a,), 0), df.get((b,), 0))))
            if tie >= TERM_TIE:
                wording.append("S%d \"%s %s\" (%d corpus papers, tie %.2f) is not in %s" % (
                    i + 1, a, b, n2, tie, "/".join(ks)))
    print("WORDING (a field term the cited paper does not use): %d" % len(wording))
    for x in wording[:SHOW]:
        print("   REVIEW " + x)

    rare, core = [], []
    seen_rare = set()
    for i, text, ks, r in pairs_of:
        for w in r:
            if len(w) >= 4 and w not in STOP and df.get((w,), 0) <= 2 and w not in seen_rare:
                seen_rare.add(w)
                rare.append("%s (%d)" % (w, df.get((w,), 0)))
        zero = [j for j in range(len(r) - 1) if df.get((r[j], r[j + 1]), 0) == 0
                and df.get((r[j],), 0) >= FIELD_MIN and df.get((r[j + 1],), 0) >= FIELD_MIN]
        for j in zero:
            lo, hi = j, j + 2
            # widen to the 3-4 word spans around the pair that are also in 0 papers
            for n in (3, 4):
                for a in range(max(0, j + 2 - n), min(j, len(r) - n) + 1):
                    if df.get(tuple(r[a:a + n]), 0) == 0:
                        lo, hi = min(lo, a), max(hi, a + n)
            core.append((i, lo, hi, r))
    merged = []
    for i, lo, hi, r in core:
        if merged and merged[-1][0] == i and merged[-1][3] is r and lo <= merged[-1][2]:
            merged[-1] = (i, merged[-1][1], max(hi, merged[-1][2]), r)
        else:
            merged.append((i, lo, hi, r))
    spans = ["S%d \"%s\"" % (i + 1, " ".join(r[lo:hi])) for i, lo, hi, r in merged]
    print("FRAMES in 0 of %d corpus papers: %d span(s) around a 0-paper word pair · words in 0-2 papers: %d"
          % (_ngram.n_papers(), len(spans), len(rare)))
    for x in spans[:SHOW]:
        print("   REVIEW " + x)
    if rare:
        print("   rare words: " + ", ".join(rare[:20]))

    # ---- CITATIONS --------------------------------------------------------------------
    cmds = [[k for k in m.group(1).split(",") if k.strip()] for m in _src.CITE.finditer(para)]
    n_cite_keys = sum(len(c) for c in cmds)
    in_blocks = sum(len(c) for c in cmds if len(c) >= 2)
    print("CITATIONS: %d keys in %d commands · in blocks of 2+: %d (%d%%)" % (
        n_cite_keys, len(cmds), in_blocks, 100 * in_blocks // max(1, n_cite_keys)))

    n_review = len(st) + len(wording) + len(spans)
    print("\nRESULT: %s · review items %d (strength %d, wording %d, frames %d)" % (
        ("FIX " + ", ".join(must)) if must else "all must-pass checks OK", n_review, len(st), len(wording), len(spans)))
    sys.exit(1 if must else 0)


if __name__ == "__main__":
    main()
