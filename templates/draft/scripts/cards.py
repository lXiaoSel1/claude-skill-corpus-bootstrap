#!/usr/bin/env python3
"""Evidence cards (fast lane): each cited paper's own result and design lines,
verified once and reused by every paragraph and every later check.

FACTORY PORT (1.6.0) of the parent's `cards.py`. The corpus is the lit
instance's; a key's PDF and reading note come from the onboarding index
(_src.py); the design-line vocabulary is generic empirical English plus the
field's own `design_terms` from field-config.yaml (the parent hardcoded
its own field's data-set names).

A card holds lines taken verbatim from the paper's corpus file (one paragraph
per line), each with its corpus:LINE and the PDF page it is on:
  R  result lines -- the abstract, the introduction and the conclusion where the
     paper states what it finds ("we find", "our results suggest", ...), and
     lines with that shape elsewhere; a line that cites another paper is left
     out (the claim may be that paper's)
  D  design lines -- data, sample, period
  Q  quotations in the reading note, each looked up in the paper: FOUND with
     its place, or NOT IN PAPER (the note is a pointer, never the source)
and the paper's own strength profile (its hedges and finding verbs). The
drafter marks the lines a paragraph cites the paper for (`mark`) and adds a
line the card missed (`add`, checked verbatim first).

Write path: references/cards/<KEY>.md only (the skill's second whitelisted
write path; a rebuilt card keeps a .bak).

RUN
    py -3 scripts/cards.py build KEY [KEY ...] [--force]   # make missing cards
    py -3 scripts/cards.py show  KEY [KEY ...]             # print them, compact
    py -3 scripts/cards.py add   KEY "<the paper's own sentence>"
    py -3 scripts/cards.py mark  KEY:R1,R3 [KEY2:R2 ...]          # the lines a paragraph cites
Exit 1 when a card is missing (show), a line is not verbatim (add) or a key has
no text at all (build).
"""
import datetime
import os
import re
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _src  # noqa: E402
import _tiers  # noqa: E402
from _ngram import fold  # noqa: E402
import _jobs  # noqa: E402  (_src put pipeline/ on the path)
import _cfgparse  # noqa: E402

SKILL = _src.SKILL
sys.path.insert(0, os.path.join(_jobs.lit_dir() or os.path.normpath(os.path.join(_src.CORPUS, "..", "..")),
                                "scripts"))
from textseg import split_sentences  # noqa: E402

CARDS = os.environ.get("DRAFT_CARDS_DIR") or os.path.join(SKILL, "references", "cards")
MAX_R, MAX_D = 12, 5

RESULT = re.compile(
    r"\b(?:we|this (?:paper|study|article)|our (?:results?|findings|evidence|estimates|analysis|tests?))\b"
    r"[^.;]{0,80}?\b(?:find|finds|found|show|shows|showed|document|documents|provide|provides|present|"
    r"demonstrate|demonstrates|conclude|report|estimate|suggest|suggests|indicate|indicates|observe|"
    r"argue|argues|confirm)\b", re.I)
RESULT2 = re.compile(
    r"\b(?:results?|findings|evidence|estimates)\b[^.;]{0,40}?\b(?:show|shows|suggest|suggests|"
    r"indicate|indicates|imply|implies|support|supports|reveal|reveals|are consistent)\b", re.I)
# design vocabulary: generic empirical English + the field's design_terms
_EXTRA = [re.escape(t) for t in _cfgparse.as_list(_jobs._DATA.get("design_terms")) if t]
DESIGN = re.compile(
    r"\b(?:sample|data|dataset|data set|panel|cross[- ]section(?:al)?|observations|survey|cohort|"
    r"participants|respondents|records|registry|database|archive"
    + "".join("|" + t for t in _EXTRA) + r")\b", re.I)
DESIGN_N = re.compile(r"\b(?:19|20)\d{2}\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+\s+(?:firms|plans|companies|observations|"
                      r"sponsors|countries|funds|patients|participants|respondents|hospitals|schools|students|"
                      r"households|individuals|workers|cases)\b", re.I)
CJK = re.compile(r"[　-鿿＀-￯]")
# signposts and table walk-throughs, not results
NOISE = re.compile(r"\b(?:columns?|tables?|figures?|graphs?|panels?|sections?|appendix)\b\s*\(?\d"
                   r"|\b(?:in|for) (?:this|the next|the following|the remainder of this) section\b"
                   r"|\bwe (?:discuss|describe|present|report)\b[^.;]{0,30}\b(?:data|statistics|sample|"
                   r"sources)\b|\bthe (?:top|bottom|left|right) (?:two |three )?(?:graphs?|panels?|figures?)\b"
                   r"|\bsymbol\b|\bwe (?:want|will|wish) (?:to )?(?:show|present)\b", re.I)
THIRD = re.compile(r"[A-Z][A-Za-z'\-]+(?: et al\.?| and [A-Z][A-Za-z'\-]+)?,? \(?(?:1[89]|20)\d{2}[a-z]?\)?")
QUOTE = re.compile(r"[“\"「]([^”\"」]{30,500})[”\"」]")


def words(s):
    """Lower-case words with ligatures folded and hyphens split, for verbatim checks."""
    return re.findall(r"[a-z0-9]+", fold(s))


def zones(lines):
    """[zone name] per line: abstract / intro / body / conclusion / refs."""
    n = len(lines)
    z = ["body"] * n
    abstract = next((i for i, l in enumerate(lines[:max(60, n // 10)])
                     if re.match(r"^\s*(?:a\s*b\s*s\s*t\s*r\s*a\s*c\s*t|summary)\b", l, re.I)), None)
    intro = next((i for i, l in enumerate(lines)
                  if re.match(r"^\s*(?:\d+\.?|[IVX]+\.)?\s*introduction\b", l, re.I) and len(l) < 60), None)
    concl = None
    refs = None
    for i, l in enumerate(lines):
        if i > 0.5 * n and re.match(r"^\s*(?:\d+\.?|[IVX]+\.)?\s*(?:conclusions?|concluding remarks|"
                                    r"summary and conclusions?)\b", l, re.I) and len(l) < 60:
            concl = i
        if i > 0.4 * n and re.match(r"^\s*(?:references|bibliography|works cited)\s*$", l, re.I):
            refs = i if refs is None else refs
    if abstract is not None:
        # the abstract runs from its marker to the introduction, six lines at most
        a1 = min(intro if intro is not None and intro > abstract else n, abstract + 7)
        for i in range(abstract, a1):
            z[i] = "abstract"
    else:
        # no marker: only the first substantial paragraph may be one ("abstract?")
        first = next((i for i, l in enumerate(lines[:25]) if len(l) >= 400
                      and not re.search(r"JSTOR|Published|Downloaded|Copyright|©", l)), None)
        if first is not None and (intro is None or first < intro):
            z[first] = "abstract?"
    if intro is not None:
        for i in range(intro, min(n, intro + max(8, n // 12))):
            z[i] = "intro"
    if concl is not None:
        for i in range(concl, refs if refs else n):
            z[i] = "conclusion"
    if refs is not None:
        for i in range(refs, n):
            z[i] = "refs"
    return z


_WPOS = {}
WORDCH = re.compile(r"[A-Za-z0-9ﬀ-ﬄ]+")


def wordpos(key):
    """[(label, Text, [folded words], [offsets])] per source of a key, built once."""
    if key not in _WPOS:
        out = []
        for label, t in _src.joined(key):
            ws, offs = [], []
            for m in WORDCH.finditer(t.text):
                for w in words(m.group(0)):
                    ws.append(w)
                    offs.append(m.start())
            out.append((label, t, ws, offs))
        _WPOS[key] = out
    return _WPOS[key]


def locate(key, sentence, only=None, head=None):
    """Where the sentence (or its first `head` words) is, word for word: 'corpus:N' /
    'PDF p.N', or ''. `only` restricts the search to one source."""
    want = words(sentence)
    if head:
        want = want[:head]
    if len(want) < 5:
        return ""
    n = len(want)
    for label, t, ws, offs in wordpos(key):
        if only and label != only:
            continue
        for i in range(len(ws) - n + 1):
            if ws[i] == want[0] and ws[i:i + n] == want:
                return t.loc(offs[i])
    return ""


def pdf_page(key, sentence):
    """'PDF p.N' where the sentence's first words sit in the paper's PDF, or ''."""
    return locate(key, sentence, only="pdf", head=8)


def verbatim(key, sentence):
    """Where the sentence is, word for word, in the corpus file or the PDF; ''."""
    return locate(key, sentence) if len(words(sentence)) >= 6 else ""


def candidates(key):
    """(R lines, D lines) as [(corpus line no, zone, sentence)]."""
    src = dict(_src.sources(key))
    units = src.get("corpus")
    if not units:
        return [], []
    lines = [t for _, t in units]
    z = zones(lines)
    scored, design = [], []
    for i, line in enumerate(lines):
        if z[i] == "refs" or len(line) < 60:
            continue
        for j, s in enumerate(split_sentences(line)):
            n = len(s.split())
            if n < 8 or n > 90:
                continue
            score = 3 * bool(RESULT.search(s)) + 2 * bool(RESULT2.search(s))
            # an abstract states results without "we find": every sentence of it is a candidate
            if z[i] == "abstract" and n >= 10:
                score += 2
            if score and not NOISE.search(s):
                score += {"abstract": 3, "abstract?": 2, "conclusion": 2, "intro": 1}.get(z[i], 0)
                score += bool(re.search(r"\d", s))
                if not THIRD.search(s):
                    scored.append((score, i + 1, j, z[i], s.strip()))
            if (DESIGN.search(s) and DESIGN_N.search(s) and i < 0.6 * len(lines) and not THIRD.search(s)
                    and not re.search(r"\bSections? \d", s)):
                design.append((i + 1, z[i], s.strip()))
    top = sorted(scored, key=lambda x: (-x[0], x[1], x[2]))[:MAX_R]
    r = [(ln, zn, s) for _, ln, _j, zn, s in sorted(top, key=lambda x: (x[1], x[2]))]
    seen, d = set(), []
    for ln, zn, s in design:
        if s not in seen and all(s != x for _, _, x in r):
            seen.add(s)
            d.append((ln, zn, s))
    return r, d[:MAX_D]


def note_quotes(key):
    note = _src.note_of(key)
    if not note or not os.path.isfile(note):
        return []
    with open(note, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    out = []
    for m in QUOTE.finditer(text):
        q = re.sub(r"\*\*?", "", m.group(1)).strip()
        if CJK.search(q) or "\n" in q:                      # a Chinese gloss between two quote marks
            continue
        page = re.search(r"p{1,2}\.\s*(\d+)", text[max(0, m.start() - 30):m.start()])
        # an elided quotation is looked up piece by piece
        for piece in re.split(r"\s*(?:\.\.\.|…)\s*", q):
            if len(re.findall(r"[A-Za-z]{2,}", piece)) >= 6:
                out.append((piece.strip(" ,;"), page.group(1) if page else ""))
    return out


def path(key):
    return os.path.join(CARDS, key + ".md")


def build(key, force=False):
    p = path(key)
    if os.path.exists(p) and not force:
        print("%-36s exists (%s)" % (key, "reviewed" if "reviewed: yes" in open(p, encoding="utf-8").read()
                                      else "not reviewed"))
        return 0
    srcs = dict(_src.sources(key))
    if not srcs:
        print("%-36s NO TEXT: no corpus file and no PDF in the onboarding index or its reading note" % key)
        return 1
    r, d = candidates(key)
    qs = note_quotes(key)
    prof = _tiers.profile(_tiers.strength(" ".join(s for _, _, s in r))[0])
    out = ["# %s -- evidence card" % key, "",
           "generated %s by cards.py · reviewed: no · sources: %s" % (
               datetime.date.today().isoformat(), " + ".join(sorted(srcs))),
           "the paper's own strength in its result lines: " + prof, "",
           "main: (not marked)", "", "## R · result lines (the paper's own words)", ""]
    for n, (ln, zn, s) in enumerate(r, 1):
        out.append("R%d [corpus:%d%s · %s] %s" % (n, ln, (" · " + pdf_page(key, s)) if pdf_page(key, s) else "",
                                                 zn, s))
    if not r:
        out.append("(none found by the patterns: add the lines you cite with `cards.py add`)")
    out += ["", "## D · design lines (data, sample, period)", ""]
    for n, (ln, zn, s) in enumerate(d, 1):
        out.append("D%d [corpus:%d%s · %s] %s" % (n, ln, (" · " + pdf_page(key, s)) if pdf_page(key, s) else "",
                                                 zn, s))
    if not d:
        out.append("(none found)")
    out += ["", "## Q · quotations in the reading note", ""]
    for n, (q, pg) in enumerate(qs, 1):
        at = verbatim(key, q)
        out.append("Q%d %s%s \"%s\"" % (n, ("FOUND " + at) if at else "NOT IN PAPER (note only)",
                                        (" · note says p.%s" % pg) if pg else "", q))
    if not qs:
        out.append("(the note quotes nothing in English)")
    os.makedirs(CARDS, exist_ok=True)
    if os.path.exists(p):
        shutil.copy2(p, p + ".bak")
    text = "\n".join(out) + "\n"
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with open(p, encoding="utf-8") as fh:
        if fh.read() != text:
            sys.exit("write-back verification FAILED for " + p)
    print("%-36s built: R %d · D %d · Q %d (%d not in paper)" % (
        key, len(r), len(d), len(qs), sum(1 for q, _ in qs if not verbatim(key, q))))
    return 0


def load(key):
    """{line id: (place, text)} of a card, plus 'main' -> marked ids; None if missing."""
    p = path(key)
    if not os.path.exists(p):
        return None
    out = {}
    with open(p, encoding="utf-8", errors="replace") as fh:
        for l in fh:
            m = re.match(r"^([RDQ]\d+) (?:\[([^\]]*)\]|(FOUND \S+(?: p\.\d+)?|NOT IN PAPER \(note only\)))\s*(.*)$", l)
            if m:
                out[m.group(1)] = ((m.group(2) or m.group(3) or "").strip(), m.group(4).strip())
            elif l.startswith("main:"):
                out["main"] = l[5:].strip()
    return out


def show(keys):
    rc = 0
    for k in keys:
        p = path(k)
        if not os.path.exists(p):
            print("== %s: NO CARD -- py -3 scripts/cards.py build %s" % (k, k))
            rc = 1
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
        print("== " + k)
        for l in lines[2:]:
            if not l.strip() or l.startswith("## "):
                continue
            print("  " + (l if len(l) <= 420 else l[:417] + "..."))
    return rc


def add(key, sentence):
    at = verbatim(key, sentence)
    if not at:
        print("NOT VERBATIM in %s: paste the paper's own sentence (draftcheck.py src --find %s \"<words>\""
              " finds it)" % (key, key))
        return 1
    p = path(key)
    if not os.path.exists(p):
        build(key)
    card = load(key) or {}
    same = next((i for i, v in card.items() if i != "main" and words(v[1]) == words(sentence)), None)
    if same:
        print("already in the card: %s#%s" % (key, same))
        return 0
    with open(p, encoding="utf-8") as fh:
        text = fh.read()
    n = 1 + max([int(x) for x in re.findall(r"(?m)^R(\d+) ", text)] or [0])
    row = "R%d [%s%s · added] %s" % (n, at, (" · " + pdf_page(key, sentence)) if at.startswith("corpus")
                                      and pdf_page(key, sentence) else "", sentence.strip())
    head, sep, tail = text.partition("\n## D ")
    head = re.sub(r"\(none found by the patterns[^)]*\)\n", "", head).rstrip("\n") + "\n" + row + "\n\n"
    shutil.copy2(p, p + ".bak")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(head + sep + tail if sep else head)
    print("added %s#R%d (%s)" % (key, n, at))
    return 0


def mark(key, ids, why=""):
    """Record which lines a paragraph cites the paper for (the card is then reviewed)."""
    p = path(key)
    card = load(key)
    if card is None:
        print("NO CARD for %s" % key)
        return 1
    bad = [i for i in ids.split(",") if i.strip() and i.strip() not in card]
    if bad:
        print("no such line(s) in %s: %s" % (key, ", ".join(bad)))
        return 1
    with open(p, encoding="utf-8") as fh:
        text = fh.read()
    old = card.get("main", "")
    keep = [] if old.startswith("(not marked)") else [x for x in re.split(r"[,\s]+", old.split(" -- ")[0]) if x]
    ids = ",".join(dict.fromkeys(keep + [i.strip() for i in ids.split(",") if i.strip()]))
    text = re.sub(r"(?m)^main:.*$", lambda m: "main: %s%s" % (ids, (" -- " + why.replace("\n", " ")) if why else ""),
                  text, count=1)
    text = text.replace("reviewed: no", "reviewed: yes (%s)" % datetime.date.today().isoformat(), 1)
    shutil.copy2(p, p + ".bak")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("marked %s: %s" % (key, ids))
    return 0


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "build":
        force = "--force" in a
        keys = [k for k in a[1:] if k != "--force"]
        sys.exit(max(build(k, force) for k in keys))
    if cmd == "show":
        sys.exit(show(a[1:]))
    if cmd == "add":
        sys.exit(add(a[1], a[2]))
    if cmd == "mark":
        # mark KEY:R1,R3 [KEY2:R2 ...]   (or the older form: mark KEY R1,R3 "why")
        if ":" in a[1]:
            sys.exit(max(mark(*x.split(":", 1)) for x in a[1:]))
        sys.exit(mark(a[1], a[2], a[3] if len(a) > 3 else ""))
    sys.exit("unknown command: %s\n%s" % (cmd, __doc__))


if __name__ == "__main__":
    main()
