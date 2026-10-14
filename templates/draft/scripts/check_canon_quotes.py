#!/usr/bin/env python3
"""Every *"quote"* in structure-canon.md must be found, verbatim, at a
`<key>.txt:<lines>` pointer next to it in the writing-canon sources.

The canon's rules quote published writing guides; a quotation whose pointer
has rotted is worse than none (the parent's own canon carried five such
pointers, one aimed at a blank line). For each quote:
  OK               found within +-2 lines of the pointer just before it (or,
                   when there is none in the paragraph, just after it);
  FOUND-ELSEWHERE  not at that pointer, but in one of the canon files -- the
                   real location is printed: fix the pointer;
  NOT-FOUND        in no canon file -- recalled, paraphrased, reordered or mistyped;
  UNPOINTED        no pointer in its paragraph (the real location is printed);
  TOO-SHORT        no piece of 3 characters or more, so nothing can be checked.
Every status but OK fails, and so does a pointer naming a missing file or a
line past the end of its file. Matching ignores whitespace, hyphens (a word
broken across two lines may be written joined, with or without its hyphen),
curly-versus-straight quotes, dash variants and ligatures. A quote is cut
into pieces at " / " (a jump between the two columns of a two-column page),
an ellipsis, or an editorial [insertion]; the pieces between two " / " marks
must appear in the order quoted, and each group may sit in the full line,
the left column or the right column.

RUN
    py -3 scripts/check_canon_quotes.py [--canon references/structure-canon.md] [--dir <canon_dir>]
Exit code 1 when any quote is not OK or any pointer is bad.
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
PTR = re.compile(r"`([A-Za-z0-9][\w.\-]*)\.txt:([\d][\d,\-– ]*)`")
QUOTE = re.compile(r'\*"(.+?)"\*', re.S)
COLJUMP = re.compile(r"\s+/\s+")
SPLIT = re.compile(r"\s*(?:…|\.\.\.)\s*|\[[^\]]*\]")
_MAP = {"‘": "'", "’": "'", "“": "'", "”": "'", '"': "'", "–": "-",
        "—": "-", "­": "", "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
        "ﬄ": "ffl"}
_COLS = re.compile(r"\s{3,}")
_RIGHT_ONLY = re.compile(r"^ {20,}\S")   # a line with text in the right column only


def norm(s):
    for k, v in _MAP.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip()


def fragments(q):
    """The quote's pieces as groups: one group per column stretch (split at
    " / "), each an ordered list of pieces (split at an ellipsis or an
    [insertion]), without the closing punctuation the canon author adds and
    without hyphens."""
    groups = []
    for g in COLJUMP.split(q):
        pieces = []
        for x in SPLIT.split(g):
            f = norm(x).strip(" .,;:").replace("-", "")
            if len(f) >= 3:
                pieces.append(f)
        if pieces:
            groups.append(pieces)
    return groups


def _join(parts):
    """Join lines; a line ending in a hyphen runs straight into the next."""
    s = ""
    for p in parts:
        if not p:
            continue
        s = s + p if s.endswith("-") else (s + " " + p if s else p)
    return s.replace("-", "")


def _in_order(pieces, text):
    pos = 0
    for f in pieces:
        i = text.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def _match(groups, texts):
    return all(any(_in_order(g, t) for t in texts) for g in groups)


class Source(object):
    """A canon text. Two-column PDFs extract with the columns interleaved line
    by line, so each line is also split at a wide gap into a left and a right
    column (a line indented 20 spaces or more holds the right column only),
    and a quote may match the joined left or right column."""

    def __init__(self, path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            self.lines = fh.read().split("\n")
        self.flat = [norm(l) for l in self.lines]
        cols = [["", l.strip()] if _RIGHT_ONLY.match(l) else _COLS.split(l.strip(), 1)
                for l in self.lines]
        self.left = [norm(c[0]) for c in cols]
        self.right = [norm(c[1]) if len(c) > 1 else "" for c in cols]

    def _texts(self, a, b):
        return [_join(self.flat[a:b]), _join(self.left[a:b]), _join(self.right[a:b])]

    def window(self, lo, hi):
        return self._texts(max(0, lo - 3), hi + 2)

    def has(self, groups, lo, hi):
        return _match(groups, self.window(lo, hi))

    def anywhere(self, groups):
        if not hasattr(self, "_all"):
            self._all = self._texts(0, len(self.lines))
        return _match(groups, self._all)

    def locate(self, frag):
        """First line (1-based) where frag starts."""
        for i in range(len(self.flat)):
            if any(frag in x for x in self._texts(i, i + 8)) and \
                    not any(frag in x for x in self._texts(i + 1, i + 8)):
                return i + 1
        return None


def verify(text, canon_dir):
    """{'pointers': [...], 'quotes': [...], 'bad_pointers': [...]} for one canon text."""
    srcs, bad_ptrs, ptrs = {}, [], []
    for m in PTR.finditer(text):
        key = m.group(1)
        nums = [int(x) for x in re.findall(r"\d+", m.group(2))]
        path = os.path.join(canon_dir, key + ".txt")
        if key not in srcs:
            srcs[key] = Source(path) if os.path.isfile(path) else None
        p = {"key": key, "spec": m.group(2).strip(), "lo": min(nums), "hi": max(nums),
             "start": m.start(), "end": m.end()}
        if srcs[key] is None:
            p["status"] = "NO-FILE"
            bad_ptrs.append(p)
        elif max(nums) > len(srcs[key].lines) or min(nums) < 1:
            p["status"] = "BAD-LINE"
            bad_ptrs.append(p)
        ptrs.append(p)
    every = {}
    for f in os.listdir(canon_dir) if os.path.isdir(canon_dir) else []:
        if f.endswith(".txt"):
            every[f[:-4]] = srcs.get(f[:-4]) or Source(os.path.join(canon_dir, f))
    quotes = []
    for m in QUOTE.finditer(text):
        q = m.group(1)
        para_lo = text.rfind("\n\n", 0, m.start()) + 1
        para_hi = text.find("\n\n", m.end())
        para_hi = len(text) if para_hi < 0 else para_hi
        before = [p for p in ptrs if para_lo <= p["start"] < m.start()]
        after = [p for p in ptrs if m.end() <= p["start"] < para_hi]
        tried = before[-1:] + after[:1]
        frs = fragments(q)
        rec = {"quote": q, "at": text.count("\n", 0, m.start()) + 1,
               "tried": ["%s.txt:%s" % (p["key"], p["spec"]) for p in tried]}
        if not frs:
            rec["status"] = "TOO-SHORT"
            quotes.append(rec)
            continue
        ok = False
        for p in tried:
            s = srcs.get(p["key"])
            if s and p.get("status") is None and s.has(frs, p["lo"], p["hi"]):
                ok = True
                break
        if ok:
            rec["status"] = "OK"
        else:
            where = None
            for key, s in sorted(every.items()):
                if s is not None and s.anywhere(frs):
                    where = "%s.txt:%s" % (key, s.locate(frs[0][0]) or "?")
                    break
            if where:
                rec["found_at"] = where
                rec["status"] = "FOUND-ELSEWHERE" if tried else "UNPOINTED"
            else:
                rec["status"] = "NOT-FOUND" if tried else "UNPOINTED-NOT-FOUND"
        quotes.append(rec)
    return {"pointers": ptrs, "quotes": quotes, "bad_pointers": bad_ptrs}


def failing(res):
    return [q for q in res["quotes"] if q["status"] != "OK"] + res["bad_pointers"]


def main():
    argv = sys.argv[1:]
    canon = os.path.join(SKILL, "references", "structure-canon.md")
    cdir = None
    if "--canon" in argv:
        canon = argv[argv.index("--canon") + 1]
    if "--dir" in argv:
        cdir = argv[argv.index("--dir") + 1]
    if cdir is None:
        sys.path.insert(0, os.path.join(SKILL, "pipeline"))
        import _jobs
        cdir = _jobs.canon_dir()
    if not os.path.isfile(canon):
        sys.exit("no canon file: " + canon)
    if not os.path.isdir(cdir):
        sys.exit("no canon-sources folder: " + cdir)
    with open(canon, encoding="utf-8") as fh:
        res = verify(fh.read(), cdir)
    for p in res["bad_pointers"]:
        print("%-16s %s.txt:%s" % (p["status"], p["key"], p["spec"]))
    for q in res["quotes"]:
        tail = ""
        if q["status"] == "FOUND-ELSEWHERE":
            tail = "  pointer %s -> actually %s" % ("/".join(q["tried"]), q["found_at"])
        elif q["status"] == "UNPOINTED":
            tail = "  no pointer in the paragraph; it is at %s" % q["found_at"]
        elif q["status"] in ("NOT-FOUND", "UNPOINTED-NOT-FOUND"):
            tail = "  tried %s" % ("/".join(q["tried"]) or "no pointer in the paragraph")
        print("%-16s line %-4d %s%s" % (q["status"], q["at"], q["quote"][:70].replace("\n", " "), tail))
    from collections import Counter
    c = Counter(q["status"] for q in res["quotes"])
    print("\n%d pointers, %d quotes: %s; %d bad pointers"
          % (len(res["pointers"]), len(res["quotes"]),
             ", ".join("%s %d" % kv for kv in sorted(c.items())) or "none", len(res["bad_pointers"])))
    sys.exit(1 if failing(res) else 0)


if __name__ == "__main__":
    main()
