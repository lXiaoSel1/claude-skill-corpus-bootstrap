"""`draftcheck.py src` -- every cited sentence of a drafted paragraph against the
cited papers' own text. Read-only.

FACTORY PORT (1.6.0) of the parent's fast-lane `_src.py`. What changed: the
corpus is the lit instance's (field-config `lit_instance`), a cite key's
corpus key and PDF come from the onboarding index
(<manuscript dir>/.polish/library-index.json), then from notes-index.md; names
such as MAP-21 are kept in the words (they used to be deleted, so a pasted
line holding "MAP-21" was reported NOT-VERBATIM) and dropped only where
numbers are read.

What it checks, per sentence (a sentence that cites nothing takes the
citations of the sentence before it in the paragraph):
  numbers  every number (decimals and integers >= 10; years included; the
           numbers in names such as MAP-21 and ordinals skipped), compared by
           value ("0.60" = "0.6", "1,830" = "1830", signs ignored), in the
           paper it is attached to: the parenthetical citation after it in its
           clause (\\citep at the clause's end), else the narrative citation
           before it (\\citet opens what it reports):
             TOGETHER   that paper holds them within 400 characters
             APART      that paper holds them, not close together
             FOUND      (one number of several) in the paper it is attached to
             ELSEWHERE  not in that paper but in another one the sentence
                        cites: check which study the number belongs to
             MISSING    in none of the cited papers
  copied   every stretch of 7 or more words the sentence shares with a cited
           paper: quote it (with its page) or rewrite it
Where the paper's text comes from: its corpus file (one paragraph per line, so
a hit is corpus:LINE); when that file is missing or does not hold the number or
stretch, the paper's PDF, read page by page (a hit is PDF p.N). A reading note
is a pointer to the paper, never the source itself.

Also:
  --line KEY "<pasted source line>"   is the line verbatim in the paper?
                                       (corpus:LINE / PDF p.N / NOT-VERBATIM)
  --find KEY "<phrase or number>"     every place it occurs, before a
                                       sentence is dropped as "not in the paper"
"""
import bisect
import json
import os
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402

CORPUS = _jobs.corpus_dir()
NOTES_INDEX = os.path.join(SKILL, "references", "notes-index.md")
WIN = 400
COPY_MIN = 7          # longer than the ~6 words of a source term (polish rule 2a)
CITE_CMD = r"\\(?!nocite\b|citetext\b)[A-Za-z]*[Cc]ite[A-Za-z]*\*?(?:\[[^\]]*\]){0,2}"
CITE = re.compile(CITE_CMD + r"\{([^}]*)\}")
NUM = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\d])|(?<![\w.])\.\d+(?![\d])")
NAME_NUM = re.compile(r"\b[A-Z][A-Za-z]*-\d+\b|\b\d+(?:st|nd|rd|th)\b")
WORD = re.compile(r"[a-z0-9]+")
# a stretch shared with a cited paper that is mostly a proper name ("the American
# Rescue Plan Act of 2021") is the name, not the paper's prose: it counts as
# copied only with this many words outside names
NAME_PROSE = 3
JOINERS = {"of", "the", "for", "and", "on"}
# the author's own work: a citation never carries into it
OWN = re.compile(r"^\W*(?:(?:in\s+)?this\s+(?:paper|study|article)\b|we\b|our\b)", re.I)


# ---- numbers ------------------------------------------------------------------
def canon(tok):
    try:
        d = Decimal(tok.replace(",", ""))
    except InvalidOperation:
        return None
    return format(d.normalize(), "f")


def numbers(text):
    t = re.sub(r"(?<=\d)\u00b7(?=\d)", ".", text).replace("{,}", ",")
    out = []
    for m in NUM.finditer(t):
        c = canon(m.group(0))
        if c is not None and c not in out:
            out.append(c)
    return out


def informative(v):
    return "." in v or Decimal(v) >= 10


# ---- where a cite key's text lives ---------------------------------------------
_LIB = None
_NOTES = None
_TEXT = {}


def library():
    """{cite key: entry} from the onboarding index, {} before onboarding."""
    global _LIB
    if _LIB is None:
        _LIB = {}
        tex = _jobs.manuscript_paths()[0]
        p = os.path.join(os.path.dirname(tex), ".polish", "library-index.json") if tex else ""
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            _LIB = data.get("keys", data) if isinstance(data, dict) else {}
    return _LIB


def notes_index():
    """{cite key: (corpus key, note path)} from references/notes-index.md."""
    global _NOTES
    if _NOTES is None:
        _NOTES = {}
        if os.path.isfile(NOTES_INDEX):
            with open(NOTES_INDEX, encoding="utf-8", errors="replace") as fh:
                for l in fh:
                    m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]*)`\s*\|\s*(.+?)\s*\|\s*$", l)
                    if m:
                        _NOTES[m.group(1)] = (m.group(2) or m.group(1), m.group(3).strip("` "))
    return _NOTES


def corpus_key(key):
    e = library().get(key) or {}
    return e.get("corpus_key") or notes_index().get(key, (key, ""))[0] or key


def note_of(key):
    e = library().get(key) or {}
    note = e.get("note_file") or e.get("note") or notes_index().get(key, ("", ""))[1]
    return note or None


def pdf_of(key):
    """The key's PDF: the onboarding index first, then the PDF its reading note
    names (对应PDF / pdf / file, with an optional PDF路径 / pdf_dir folder)."""
    e = library().get(key) or {}
    if e.get("pdf") and os.path.isfile(e["pdf"]):
        return e["pdf"]
    note = note_of(key)
    if not note or not os.path.isfile(note):
        return None
    with open(note, encoding="utf-8", errors="replace") as fh:
        head = fh.read(4000)
    m = re.search(r"^\s*(?:对应PDF|pdf|PDF|file)\s*[:：]\s*(.+?)\s*$", head, re.M)
    if not m:
        return None
    name = m.group(1).strip().strip("'\"")
    d = re.search(r"^\s*(?:PDF路径|pdf_dir)\s*[:：]\s*(.+?)\s*$", head, re.M)
    folders = [d.group(1).strip().strip("'\"")] if d else []
    folders.append(os.path.dirname(note))
    want = re.sub(r"[^0-9a-z]+", "", os.path.basename(name).lower())
    for folder in folders:
        p = name if os.path.isabs(name) else os.path.join(folder, name)
        if os.path.isfile(p):
            return p
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                if re.sub(r"[^0-9a-z]+", "", f.lower()) == want:
                    return os.path.join(folder, f)
    return None


def sources(key):
    """[(label, [(location, text)])]: the corpus file (one unit per line), then
    the PDF (one unit per page). Either may be missing."""
    if key in _TEXT:
        return _TEXT[key]
    out = []
    cp = os.path.join(CORPUS, corpus_key(key) + ".txt")
    if os.path.isfile(cp):
        with open(cp, encoding="utf-8", errors="replace") as fh:
            out.append(("corpus", [("corpus:%d" % i, l) for i, l in enumerate(fh.read().split("\n"), 1)]))
    pdf = pdf_of(key)
    if pdf:
        try:
            import fitz
            with fitz.open(pdf) as d:
                out.append(("pdf", [("PDF p.%d" % (i + 1), p.get_text()) for i, p in enumerate(d)]))
        except ImportError:
            pass
        except Exception:  # noqa: BLE001  (a damaged PDF must not stop the check)
            pass
    _TEXT[key] = out
    return out


class Text(object):
    """One source joined into a string, with the location of every offset."""

    def __init__(self, units):
        self.locs, self.starts, parts, n = [], [], [], 0
        for loc, t in units:
            t = re.sub(r"\s+", " ", re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t))
            self.locs.append(loc)
            self.starts.append(n)
            parts.append(t)
            n += len(t) + 1
        self.text = re.sub(r"(?<=\d)\u00b7(?=\d)", ".", " ".join(parts))
        self.pos = {}
        for m in NUM.finditer(self.text):
            c = canon(m.group(0))
            if c is not None:
                self.pos.setdefault(c, []).append(m.start())
        self.toks = [(m.group(0), m.start()) for m in WORD.finditer(self.text.lower())]

    def loc(self, offset):
        return self.locs[max(0, bisect.bisect_right(self.starts, offset) - 1)]


_JOINED = {}


def joined(key):
    if key not in _JOINED:
        _JOINED[key] = [(label, Text(units)) for label, units in sources(key)]
    return _JOINED[key]


def tightest(pos, vals):
    ev = sorted((o, v) for v in vals for o in pos[v])
    have, best, lo = Counter(), None, 0
    for o, v in ev:
        have[v] += 1
        while len(have) == len(vals):
            s = ev[lo][0]
            if best is None or o - s < best[1] - best[0]:
                best = (s, o)
            lv = ev[lo][1]
            have[lv] -= 1
            if not have[lv]:
                del have[lv]
            lo += 1
    return best


# ---- copied stretches -----------------------------------------------------------
_GRAMS = {}


def grams(key, label, t):
    k = (key, label)
    if k not in _GRAMS:
        g = {}
        words = [w for w, _ in t.toks]
        for i in range(len(words) - COPY_MIN + 1):
            g.setdefault(tuple(words[i:i + COPY_MIN]), t.toks[i][1])
        _GRAMS[k] = g
    return _GRAMS[k]


def name_mask(text):
    """[bool] aligned with WORD.findall(text.lower()): True for a word inside a
    proper name -- a run of capitalised words, the of/the/for/and/on joining
    them, the article before one and a number after one (Act of 2021, MAP-21).
    A capitalised first word counts only when the next word is capitalised too."""
    toks = re.findall(r"[A-Za-z0-9]+", text)
    if [t.lower() for t in toks] != WORD.findall(text.lower()):
        return []
    n = len(toks)
    cap = [t[0].isupper() for t in toks]
    if n and cap[0] and not (n > 1 and cap[1]):
        cap[0] = False
    name = list(cap)
    for i in range(1, n - 1):
        if toks[i].lower() in JOINERS and name[i - 1] and (cap[i + 1] or toks[i + 1].isdigit()):
            name[i] = True
    for i in range(1, n):
        if toks[i].isdigit() and name[i - 1]:
            name[i] = True
    for i in range(n - 1):
        if toks[i].lower() == "the" and cap[i + 1]:
            name[i] = True
    return name


def copied(sentence_words, key, mask=None, names=None):
    """[(n words, the stretch, location)] of every run of >= COPY_MIN words the
    sentence shares with the key's text (corpus first, then PDF). With mask
    (name_mask of the sentence), a run with fewer than NAME_PROSE words outside
    proper names is left out, and added to names when a list is given."""
    if mask is not None and len(mask) != len(sentence_words):
        mask = None
    out, nm = [], []
    for label, t in joined(key):
        g = grams(key, label, t)
        i, n = 0, len(sentence_words)
        while i <= n - COPY_MIN:
            hit = g.get(tuple(sentence_words[i:i + COPY_MIN]))
            if hit is None:
                i += 1
                continue
            j = i + COPY_MIN
            while j < n and tuple(sentence_words[j - COPY_MIN + 1:j + 1]) in g:
                j += 1
            stretch = (j - i, " ".join(sentence_words[i:j]), t.loc(hit))
            if mask and sum(1 for x in mask[i:j] if not x) < NAME_PROSE:
                nm.append(stretch)
            else:
                out.append(stretch)
            i = j
        if out or nm:
            break
    if names is not None:
        names.extend(nm)
    return out


# ---- the paragraph ----------------------------------------------------------------
NARRATIVE = re.compile(r"^\\(?:[Cc]ite[t]|textcite|[Cc]iteauthor|[Cc]ite)\b")
PLACE = re.compile(r"Citez(\d+)q")


def sentences(raw, split):
    """([(sentence with citations as placeholders, [cite keys])], marks) where
    marks[i] = (keys, narrative?) for placeholder Citez<i>q."""
    raw = re.sub(r"(?<!\\)%.*", "", raw)
    marks = []

    def hold(m):
        marks.append(([k.strip() for k in m.group(1).split(",") if k.strip()],
                      bool(NARRATIVE.match(m.group(0)))))
        return " Citez%dq " % (len(marks) - 1)
    t = re.sub(r"\s+", " ", CITE.sub(hold, raw))
    out = []
    for s in split(t):
        ks = []
        for m in PLACE.finditer(s):
            ks += [k for k in marks[int(m.group(1))][0] if k not in ks]
        out.append((s, ks))
    return out, marks


def clean(s, keep_marks=False, drop_names=False):
    """The sentence as words. Names such as MAP-21 stay in the text (a pasted
    line keeps them); drop_names=True blanks them where numbers are read, so
    the 21 of MAP-21 is never taken for a result."""
    if not keep_marks:
        s = PLACE.sub(" ", s)
    s = s.replace("\\%", "%").replace("\\$", "$").replace("---", " ").replace("--", "–")
    s = re.sub(r"\\[A-Za-z]+\*?", " ", s)
    s = re.sub(r"[{}~]", " ", s)
    return NAME_NUM.sub(" ", s) if drop_names else s


def owners(text, marks, fallback):
    """[(number, [owner keys])]: a number belongs to the parenthetical
    citation after it in its clause (\\citep at the clause's end), else to the
    narrative citation before it (\\citet opens what it reports), else to the
    sentence's citations. Pass text from clean(..., keep_marks=True,
    drop_names=True)."""
    at = [(m.start(), marks[int(m.group(1))]) for m in PLACE.finditer(text)]
    out = []
    # placeholders blanked to their own length: their index is not a number
    t = PLACE.sub(lambda m: " " * len(m.group(0)), text)
    t = NAME_NUM.sub(lambda m: " " * len(m.group(0)), t)
    t = re.sub(r"(?<=\d)\u00b7(?=\d)", ".", t)
    for m in NUM.finditer(t):
        v = canon(m.group(0))
        if v is None or not informative(v) or any(v == x for x, _ in out):
            continue
        x = m.start()
        nxt = next(((p, mk) for p, mk in at if p > x), None)
        prev = [(p, mk) for p, mk in at if p < x and mk[1]]
        if nxt and not nxt[1][1]:                      # \citep after it, no \citet between
            keys = nxt[1][0]
        elif prev:
            keys = prev[-1][1][0]
        else:
            keys = fallback
        out.append((v, keys))
    return out


def where(key, vals):
    """(span, location, context) of the tightest stretch of one key's text
    holding every value, or None."""
    best = None
    for label, t in joined(key):
        if all(v in t.pos for v in vals):
            s0, e0 = tightest(t.pos, vals)
            if best is None or e0 - s0 < best[0]:
                best = (e0 - s0, t.loc(s0), t.text[s0:min(e0 + 30, s0 + 200)].strip())
    return best


RANK = {"TOGETHER": 0, "FOUND": 0, "APART": 1, "ELSEWHERE": 2, "MISSING": 3}


def cmd_src(raw, split):
    tally, carried_keys = Counter(), []
    n_cited = 0
    sents, marks = sentences(raw, split)
    for sno, (s, keys) in enumerate(sents, 1):
        if not keys and OWN.match(clean(s)):
            carried_keys = []
            continue
        carried = not keys and bool(carried_keys)
        if keys:
            carried_keys = keys
        else:
            keys = carried_keys
        if not keys:
            continue
        n_cited += 1
        text = clean(s)
        words = WORD.findall(text.lower())
        mask = name_mask(text)
        print("\nS%d%s: %s" % (sno, " [cites carried from the sentence before]" if carried else "",
                               re.sub(r"\s+", " ", text).strip()[:150]))
        for k in keys:
            if not joined(k):
                print("   %-26s NO TEXT (no corpus file, no PDF in the onboarding index or its note)" % k)
        own = owners(clean(s, keep_marks=True, drop_names=True), marks, keys)
        groups = {}
        for v, ks in own:
            groups.setdefault(tuple(ks), []).append(v)
        worst = None
        for ks, vals in groups.items():
            hit = [(where(k, vals), k) for k in ks]
            hit = [(w, k) for w, k in hit if w]
            if hit:
                w, k = min(hit)
                verdict = "TOGETHER" if w[0] <= WIN else "APART"
                print("   %-9s %s in %s %s ...%s..." % (verdict, " ".join(vals), k, w[1], w[2]))
            else:
                for v in vals:
                    inside = next(((k, where(k, [v])) for k in ks if where(k, [v])), None)
                    other = next(((k, where(k, [v])) for k in keys if k not in ks and where(k, [v])), None)
                    if inside:
                        verdict = "FOUND"          # in its paper, one number of several
                        print("   %-9s %s in %s %s" % (verdict, v, inside[0], inside[1][1]))
                    elif other:
                        verdict = "ELSEWHERE"
                        print("   ELSEWHERE %s is not in %s, the paper it is attached to, but in %s %s"
                              " -- check which study it belongs to" % (v, "/".join(ks), other[0], other[1][1]))
                    else:
                        verdict = "MISSING"
                        print("   MISSING   %s: in none of %s" % (v, ", ".join(keys)))
                    if worst is None or RANK[verdict] > RANK[worst]:
                        worst = verdict
                continue
            if worst is None or RANK[verdict] > RANK[worst]:
                worst = verdict
        if worst:
            tally[worst] += 1
        for k in keys:
            nm = []
            for n, stretch, loc in copied(words, k, mask, nm):
                tally["copied"] += 1
                print("   COPIED %d words from %s %s: \"%s\" -- quote it with its page, or rewrite" % (n, k, loc, stretch))
            for n, stretch, loc in nm:
                print("   NAME   %d words from %s %s: \"%s\" -- a proper name, not counted" % (n, k, loc, stretch))
    print("\nSRC: %d cited sentences · sentences with numbers: %s · copied stretches (>= %d words) %d"
          % (n_cited, " ".join("%s %d" % (v, tally[v]) for v in ("TOGETHER", "FOUND", "APART", "ELSEWHERE", "MISSING")),
             COPY_MIN, tally["copied"]))
    return 1 if tally["MISSING"] or tally["ELSEWHERE"] or tally["copied"] else 0


def cmd_line(key, line):
    want = WORD.findall(clean(line).lower())
    if len(want) < 4:
        print("too short to check: %r" % line)
        return 1
    for label, t in joined(key):
        words = [w for w, _ in t.toks]
        n = len(want)
        for i in range(len(words) - n + 1):
            if words[i] == want[0] and words[i:i + n] == want:
                print("VERBATIM  %s %s" % (key, t.loc(t.toks[i][1])))
                return 0
    print("NOT-VERBATIM  %s: not in its corpus file or PDF -- use it only as a pointer;"
          " paste the paper's own line, or drop the claim to `note`" % key)
    return 1


def cmd_find(key, what):
    n = 0
    vals = [v for v in numbers(what)] if re.fullmatch(r"[\d.,%\s·]+", what.strip()) else []
    want = WORD.findall(what.lower())
    for label, t in joined(key):
        if vals:
            for v in vals:
                for o in t.pos.get(v, []):
                    n += 1
                    if n <= 10:
                        print("  %s %s ...%s..." % (v, t.loc(o), t.text[max(0, o - 60):o + 60]))
        else:
            words = [w for w, _ in t.toks]
            for i in range(len(words) - len(want) + 1):
                if words[i:i + len(want)] == want:
                    n += 1
                    if n <= 10:
                        o = t.toks[i][1]
                        print("  %s ...%s..." % (t.loc(o), t.text[max(0, o - 60):o + 100]))
    print("%s: %d hit(s) of %r in %s" % (key, n, what, " + ".join(l for l, _ in joined(key)) or "no text"))
    return 0 if n else 1
