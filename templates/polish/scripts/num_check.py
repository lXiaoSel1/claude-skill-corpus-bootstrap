#!/usr/bin/env python3
"""Steps e / h2 -- look up every number of every cited sentence of a section in
the cited paper's own text (its PDF, else the lit corpus copy).

The whole section is checked, not only the sentences an edit changed, so a
number the draft copied wrong is caught even when no step touched it. Numbers
are compared by value in one written form: a range ("0.98--1.58", "0.98–1.58")
as its two ends, a middle-dot decimal ("1·24") as 1.24, thousands separators,
"\\%" and "\\$" dropped, ".41" as 0.41, trailing zeros ignored. Signs are not
compared (a PDF's minus sign may be any of several characters). Integers under
10 are listed but not looked up: they occur in every paper, and so do the
numbers in names (MAP-21, COVID-19) and ordinals (21st), which are skipped. A
sentence that cites nothing takes the citations of the sentence before it in
its paragraph (a result sentence after its design sentence). Each number is
looked up in the paper it is attached to: the parenthetical citation after it
in its clause (\\citep at the clause's end), else the narrative citation
before it (\\citet opens what it reports). Per paper and its numbers:
  TOGETHER   the paper holds them within --window characters (default 400):
             page, the words just before, the context
  APART      the paper holds them, not that close together
  FOUND      (one number of several) in the paper it is attached to
  ELSEWHERE  not in that paper but in another one the sentence cites: check
             which study the number belongs to
  MISSING    in none of the cited papers -- a typo, a number in a table the
             PDF does not hold as text, or one the author computed
Pages with no text layer are named, since they were not searched.

RUN
    py -3 scripts/num_check.py <section> [section ...] [--window N]
Exit code 0 (the verdicts go into the record), 2 when it cannot run.
"""
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation

import _rp

ctx = _rp.Ctx(sys.argv)
WIN = int(_rp._pop(ctx.args, "--window", 400))
if not ctx.args:
    _rp.die(__doc__)
split = ctx.split_sentences()
# a leading-dot decimal (".41") only after a space, bracket or sign, never a
# footnote mark after a word ("model.6")
NUM = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\d])|(?<![\w.])\.\d+(?![\d])")
DROP = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref|label|url|href|input|include)\{[^}]*\}")
NAME_NUM = re.compile(r"\b[A-Z][A-Za-z]*-\d+\b|\b\d+(?:st|nd|rd|th)\b")   # MAP-21, COVID-19, 21st


def canon(tok):
    """'1,830' -> '1830', '0.60' -> '0.6', '.41' -> '0.41'."""
    try:
        d = Decimal(tok.replace(",", ""))
    except InvalidOperation:
        return None
    s = format(d.normalize(), "f")
    return s if s != "-0" else "0"


def numbers(text):
    """[canonical number] of a text in reading order, one written form."""
    t = re.sub(r"(?<=\d)\u00b7(?=\d)", ".", text)         # 1·24
    t = t.replace("{,}", ",")
    out = []
    for m in NUM.finditer(t):
        c = canon(m.group(0))
        if c is not None:
            out.append(c)
    return out


def informative(v):
    return "." in v or Decimal(v) >= 10


def latex_clean(s):
    s = _rp.CITE_ANY_RE.sub(" ", s)
    s = DROP.sub(" ", s)
    s = s.replace("\\%", "%").replace("\\$", "$").replace("---", " – ").replace("--", "–")
    s = re.sub(r"\\[A-Za-z]+\*?", " ", s)
    return NAME_NUM.sub(" ", s)


_POS = {}


def positions(key):
    """({canonical number: [offsets]}, text, source label) of a cited paper."""
    if key not in _POS:
        text, src = ctx.source_text(key)
        pos = {}
        if text:
            t = re.sub(r"(?<=\d)\u00b7(?=\d)", ".", text)
            for m in NUM.finditer(t):
                c = canon(m.group(0))
                if c is not None:
                    pos.setdefault(c, []).append(m.start())
        _POS[key] = (pos, text, src)
    return _POS[key]


def tightest(pos, vals):
    """(start, end) of the shortest stretch holding one occurrence of every value."""
    ev = sorted((o, v) for v in vals for o in pos[v])
    need, have, best, lo = len(vals), Counter(), None, 0
    for hi, (o, v) in enumerate(ev):
        have[v] += 1
        while len(have) == need:
            s, e = ev[lo][0], o
            if best is None or e - s < best[1] - best[0]:
                best = (s, e)
            lv = ev[lo][1]
            have[lv] -= 1
            if not have[lv]:
                del have[lv]
            lo += 1
    return best


NARRATIVE = re.compile(r"^\\(?:[Cc]ite[t]|textcite|[Cc]iteauthor|[Cc]ite)\b")
PLACE = re.compile(r"Citez(\d+)q")
RANK = {"TOGETHER": 0, "FOUND": 0, "APART": 1, "ELSEWHERE": 2, "MISSING": 3}


def owners(text, marks, fallback):
    """[(number, [owner keys])] in reading order: a number belongs to the
    parenthetical citation after it in its clause (\\citep at the clause's
    end), else to the narrative citation before it (\\citet opens what it
    reports), else to the sentence's citations."""
    at = [(m.start(), marks[int(m.group(1))]) for m in PLACE.finditer(text)]
    t = PLACE.sub(lambda m: " " * len(m.group(0)), text)     # an index is not a number
    t = re.sub(r"(?<=\d)·(?=\d)", ".", t).replace("{,}", ",")
    out = []
    for m in NUM.finditer(t):
        v = canon(m.group(0))
        if v is None or not informative(v) or any(v == x for x, _ in out):
            continue
        nxt = next(((p, mk) for p, mk in at if p > m.start()), None)
        prev = [mk for p, mk in at if p < m.start() and mk[1]]
        keys = nxt[1][0] if nxt and not nxt[1][1] else (prev[-1][0] if prev else fallback)
        out.append((v, keys))
    return out


def where(k, text, s0, e0):
    """Page, the words just before, and the stretch itself."""
    before = " ".join(re.findall(r"[A-Za-z][\w'-]*", text[max(0, s0 - 120):s0])[-6:])
    return "%s · before: \"%s\" · ...%s..." % (ctx.page_label(k, s0), before,
                                              text[s0:min(e0 + 30, s0 + 220)].strip())


tally = Counter()
used = set()
for sec in ctx.sections(ctx.args):
    print("== %s (%s)" % (sec.key, sec.path))
    paras = _rp.paragraphs(_rp.section_body(sec))
    for pno, (first, plines) in enumerate(paras, 1):
        raw = " ".join(re.sub(r"(?<!\\)%.*$", "", t).strip() for t in plines)
        prev = []
        for sno, s in enumerate(_rp.latex_sentences(raw, split), 1):
            keys = []
            for m in _rp.CITE_KEYS_RE.finditer(s):
                keys += [k.strip() for k in m.group(1).split(",") if k.strip() and k.strip() not in keys]
            carried = not keys and bool(prev)
            if keys:
                prev = keys
            else:
                keys = prev
            marks = []

            def hold(m):
                marks.append(([k.strip() for k in m.group(1).split(",") if k.strip()],
                              bool(NARRATIVE.match(m.group(0)))))
                return " Citez%dq " % (len(marks) - 1)
            text = latex_clean(_rp.CITE_KEYS_RE.sub(hold, s))
            own = owners(text, marks, keys)
            look = [v for v, _ in own]
            if not look:
                continue
            small = [v for v in numbers(PLACE.sub(" ", text)) if not informative(v)]
            print("\n¶%d S%d (line %d)%s: %s" % (pno, sno, first, " [cites carried from the sentence before]"
                                                 if carried else "", re.sub(r"\s+", " ", s)[:160]))
            print("   numbers: %s%s" % (" ".join(look), ("   (not looked up: %s)" % " ".join(small)) if small else ""))
            if not keys:
                print("   no citation in this paragraph so far: not checked")
                tally["no citation"] += 1
                continue
            texts = {}
            for k in keys:
                used.add(k)
                pos, text, src = positions(k)
                if text:
                    texts[k] = (pos, text)
                else:
                    print("   %-26s NO TEXT (%s)" % (k, src))
            if not texts:
                tally["no text"] += 1
                continue
            # each number in the paper it is attached to, grouped by that paper
            groups = {}
            for v, ks in own:
                groups.setdefault(tuple(ks), []).append(v)
            worst = "TOGETHER"
            for ks, vals in groups.items():
                full = []
                for k in ks:
                    if k in texts and all(v in texts[k][0] for v in vals):
                        s0, e0 = tightest(texts[k][0], vals)
                        full.append((e0 - s0, k, s0, e0))
                if full:
                    span, k, s0, e0 = min(full)
                    verdict = "TOGETHER" if span <= WIN else "APART"
                    print("   %-9s %-26s %s%s" % (verdict, k, " ".join(vals) + " · " if len(groups) > 1 else "",
                                                 where(k, texts[k][1], s0, e0)))
                    worst = max(worst, verdict, key=RANK.get)
                    continue
                for v in vals:
                    k_in = next((k for k in ks if k in texts and v in texts[k][0]), None)
                    k_out = next((k for k in texts if k not in ks and v in texts[k][0]), None)
                    if k_in:
                        verdict = "FOUND"
                        o = texts[k_in][0][v][0]
                        print("   FOUND     %s in %s %s" % (v, k_in, where(k_in, texts[k_in][1], o, o)))
                    elif k_out:
                        verdict = "ELSEWHERE"
                        o = texts[k_out][0][v][0]
                        print("   ELSEWHERE %s is not in %s, the paper it is attached to, but in %s %s"
                              " -- check which study it belongs to" % (v, "/".join(ks), k_out, ctx.page_label(k_out, o)))
                    else:
                        verdict = "MISSING"
                        print("   MISSING   %s: in none of %s" % (v, ", ".join(texts)))
                    worst = max(worst, verdict, key=RANK.get)
            tally[worst] += 1
print("\n" + " · ".join("%s %d" % kv for kv in sorted(tally.items())) if tally else "\nno numbers in cited sentences")
for k in sorted(used):
    for n in ctx.pdf_notes(k):
        print("  %s: %s" % (k, n))
