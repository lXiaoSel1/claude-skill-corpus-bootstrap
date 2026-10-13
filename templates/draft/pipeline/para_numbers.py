# -*- coding: utf-8 -*-
"""Resolve paragraph numbers for Example attributions in sections/introduction/*.md.

Ground truth = records/intro-read.md + records/_superseded/introduction-tagged.md,
which record each paragraph's verbatim FIRST sentence. Mid-paragraph quotes are
resolved by locating both the quote and every anchor first-sentence inside
slices/introduction/<key>.txt and taking the nearest preceding anchor.

Only attributions inside an `Example` field block count. `Pattern` lines carry
quoted templates and em-dashes too, and must not be annotated.

Run bare to audit, `--write` to annotate. It is IDEMPOTENT: an attribution that
already carries `¶n` or `epigraph` is skipped, so a second run is a no-op. The
regression check is a bare run reporting 0 UNRESOLVED (the parent's
introduction: 402 attributions / 402 annotated). `--write` emits
para_resolved.json only when there is work.

    py -3 pipeline/para_numbers.py <chapter> [--write]

Use `py` on Windows; the WindowsApps `python.exe` is a Store stub that fails.

KNOWN LIMITS (documented, not fixed -- the pipeline is dormant):
  - Example-block continuation lines are detected by a 10-space indent;
    an 8/9-space or tab-indented continuation silently ends the block and
    its attributions vanish from the audit (count just comes out lower).
  - Quote->paragraph binding is a bidirectional 60-char fingerprint prefix
    match, first hit wins; formulaic paragraph openings can bind wrong.
  - A quote found in-slice but BEFORE the first resolved anchor is stamped
    `epigraph` even though it is inside the numbered text.
"""
import os
import _jobs, re, sys, json, glob

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
# FACTORY FIX 2026-10-07: was BASE/.. (the skill root in a stamped instance,
# where pipeline/ sits beside references/), so every path below pointed at
# nothing and `--write` found zero attributions.
REF  = os.path.normpath(os.path.join(BASE, "..", "references"))
CHAP = next((a for a in sys.argv[1:] if not a.startswith("-")), "introduction")
SEC  = os.path.join(REF, "sections", CHAP)
REC  = os.path.join(REF, "records")
SLI  = os.path.join(REF, "slices", CHAP)
# Every chapter of a stamped instance has ONE record file, records/<chap>.md.
# (The parent's introduction alone was read in two rounds -- intro-read.md +
# _superseded/introduction-tagged.md; those are read only if present.)
RECFILES = [(os.path.join(REC, CHAP + ".md"), "plain")]
if CHAP == "introduction":
    RECFILES += [(os.path.join(REC, "intro-read.md"), "plain"),
                 (os.path.join(REC, "_superseded", "introduction-tagged.md"),
                  "tagged")]

def rd(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")

def fp(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

KEY = r"[A-Za-z0-9][A-Za-z0-9_\-]*"
# shared corpus-key shape (2026-10-07): keys may start with a digit
# (01_PaperX1993, P08) or contain '-' -- the old letter-first pattern
# rejected every digit-initial key, so those papers never got a para number.

# ---------- 1. anchors: key -> {para_no: first_sentence} ----------
anchors = {}
def add(key, n, sent):
    anchors.setdefault(key, {}).setdefault(n, sent)

for path, kind in RECFILES:
    if not os.path.exists(path):
        continue
    cur = pending = None
    for line in rd(path).split("\n"):
        m = re.match(r"^###\s+(" + KEY + ")", line)
        if m:
            cur, pending = m.group(1), None; continue
        # plain records: `¶3 what the paragraph does` then `> "first sentence"`
        # tagged records: `¶3 | move: … ` then an indented bare-quoted first sentence
        # literature-hypotheses/AnHuangZhang2013 marks its 18 paragraphs P1..P18 where
        # every other record uses ¶1..¶n. Accept both — the evidence layer is not edited.
        m = (re.match(r"^¶(\d+)\s*\|", line) if kind == "tagged"
             else re.match(r"^[¶P](\d+)\b", line))
        if m:
            pending = int(m.group(1)); continue
        m = (re.match(r'^\s+"(.+?)"?\s*$', line) if kind == "tagged"
             else re.match(r'^>\s*"?(.+?)"?\s*$', line))
        if m and cur and pending is not None:
            add(cur, pending, m.group(1)); pending = None

# ---------- 2. slices ----------
slices = {}
for p in glob.glob(os.path.join(SLI, "*.txt")):
    slices[os.path.splitext(os.path.basename(p))[0]] = fp(rd(p))

REAL = set(anchors) | set(slices)

# ---------- 3. anchor offsets inside each slice ----------
offsets = {}
for k, paras in anchors.items():
    s = slices.get(k)
    if not s:
        continue
    lst = []
    for n, sent in sorted(paras.items()):
        f = fp(sent)[:70]
        if len(f) >= 25:
            i = s.find(f)
            if i >= 0:
                lst.append((i, n))
    lst.sort()
    mono, last = [], -1
    for off, n in lst:
        if n > last:
            mono.append((off, n)); last = n
    offsets[k] = mono

# ---------- 4. Example-block attributions only ----------
FIELD = re.compile(r"^(Pattern|Example|Use it when|Not this when)\b")
# Attribution = em-dash + a REAL paper key, optionally already carrying a para no.
# The quote is everything since the previous attribution on the line, so internal
# double quotes ("pecking order") and double attributions (\u2014 Voltaire \u2014 Key) survive.
ATTR = re.compile(r"\u2014\s*(" + KEY + r")(\s*\u00b6\s*\d+|\s+epigraph)?")

rows = []
# a chapter is either split (sections/<chap>/*.md) or one file under 25 KB
# (sections/<chap>.md) -- the PASS2 split rule
SEC_FILES = sorted(glob.glob(os.path.join(SEC, "*.md")))
if os.path.exists(SEC + ".md"):
    SEC_FILES.append(SEC + ".md")
for path in SEC_FILES:
    lines = rd(path).split("\n")
    # An Example block = its label line plus every continuation line. A quote may
    # wrap across several of them, and its attribution may sit alone on the last.
    blocks, cur = [], None
    for i, line in enumerate(lines):
        m = FIELD.match(line)
        if m:
            if cur:
                blocks.append(cur)          # a new field label closes the Example block
            cur = [(i, line)] if m.group(1) == "Example" else None
        elif cur is not None and line.startswith(" " * 10) and line.strip():
            cur.append((i, line))
        else:
            if cur:
                blocks.append(cur)
            cur = None
    if cur:
        blocks.append(cur)

    for blk in blocks:
        joined, pos = "", []          # pos[j] = (line_index, col) of joined[j]
        for (i, line) in blk:
            for c, ch in enumerate(line):
                joined += ch; pos.append((i, c))
            joined += "\n"; pos.append((i, len(line)))
        prev = 0
        for a in ATTR.finditer(joined):
            if a.group(1) not in REAL:
                continue
            seg, prev = joined[prev:a.start()], a.end()
            # The quote is whatever sits between some opening " and the LAST " before
            # the attribution. Which opening is right depends on whether the previous
            # attribution trailed a parenthetical that itself contained quotes, so
            # offer every span and let resolution pick — a wrong span matches nothing.
            qs = [j for j, ch in enumerate(seg) if ch == '"']
            if len(qs) < 2:
                continue
            cand = [" ".join(seg[j + 1:qs[-1]].split()) for j in qs[:-1]]
            cand += [" ".join(x.split()) for x in re.findall(r'"([^"]+)"', seg, re.S)]
            cand = sorted(dict.fromkeys(c for c in cand if c), key=len, reverse=True)
            li, col = pos[a.end(1) - 1]
            rows.append(dict(file=os.path.basename(path), line=li + 1, key=a.group(1),
                             quote=cand[0], cand=cand, has=bool(a.group(2)),
                             end=col + 1))

need = [r for r in rows if not r["has"]]

# ---------- 5. resolve ----------
def probe(s):
    """Fingerprint, truncated at an ellipsis: '…' marks text the quoter elided, so
    anything after it will not be contiguous in the source."""
    s = re.split(r"…|\.\.\.", s)[0]
    return fp(s)

for r in need:
    k = r["key"]
    pn, how = None, "fail"
    for q in [p for p in (probe(c) for c in r["cand"]) if len(p) >= 25]:
        for n, sent in sorted(anchors.get(k, {}).items()):
            f = fp(sent)
            if f and (f.startswith(q[:60]) or q.startswith(f[:60])):
                pn, how = n, "exact"; break
        if pn is None and offsets.get(k):
            i = slices[k].find(q[:80])
            if i >= 0:
                c = [n for off, n in offsets[k] if off <= i]
                pn, how = (c[-1], "slice") if c else ("epigraph", "epigraph")
        if pn is None:
            # Not in the introduction slice at all. If the sentence is real text from
            # that paper, the slicer started after it — an epigraph, which sits
            # outside the numbered paragraphs and must not be given a number.
            # FACTORY: was a hardcoded ../../mimic-lit hop -- in a stamped
            # instance that reads the ECONOMICS corpus to decide whether a
            # sentence of THIS field's paper is an epigraph.  The sibling is
            # declared as lit_instance in field-config.yaml; _jobs resolves it.
            cp = os.path.join(_jobs.corpus_dir(), k + ".txt")
            if os.path.exists(cp) and fp(rd(cp)).find(q[:60]) >= 0:
                pn, how = "epigraph", "epigraph"
        if pn is not None:
            break
    r["para"], r["how"] = pn, how

ok = [r for r in need if r["para"]]
bad = [r for r in need if not r["para"]]
print("Example attributions      :", len(rows))
print("  already carry a para no :", sum(1 for r in rows if r["has"]))
print("  need one                :", len(need))
print("    by first sentence     :", sum(1 for r in need if r["how"] == "exact"))
print("    by slice position     :", sum(1 for r in need if r["how"] == "slice"))
print("    UNRESOLVED            :", len(bad))
print("papers cited w/o record   :", sorted({r["key"] for r in need if r["key"] not in anchors}))
print("papers cited w/o slice    :", sorted({r["key"] for r in need if r["key"] not in slices}))

print("\n--- unresolved ---")
for r in bad:
    print(f'{r["file"]}:{r["line"]}  {r["key"]}  {r["quote"][:78]}')

# ---------- 6. write ----------
if "--write" in sys.argv:
    # para_resolved.json records the work items of THIS write pass. Until
    # 2026-08-26 this dump ran unconditionally on every bare audit, clobbering
    # the file on each run -- against the docstring's own contract ("emits
    # para_resolved.json only when there is work").
    if need:
        with open(os.path.join(BASE, "para_resolved.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(need, fh, ensure_ascii=False, indent=1)
    import collections
    byfile = collections.defaultdict(list)
    for r in ok:
        byfile[r["file"]].append(r)
    for fn, rs in sorted(byfile.items()):
        p = next(x for x in SEC_FILES if os.path.basename(x) == fn)
        with open(p, encoding="utf-8", newline="") as f:
            lines = f.read().split("\n")          # \r kept at line ends
        # right-to-left within a line so earlier offsets stay valid
        for r in sorted(rs, key=lambda x: (-x["line"], -x["end"])):
            i = r["line"] - 1
            tag = " ¶" + str(r["para"]) if r["para"] != "epigraph" else " epigraph"
            lines[i] = lines[i][:r["end"]] + tag + lines[i][r["end"]:]
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))
        print(f"  wrote {fn}: +{len(rs)}")
