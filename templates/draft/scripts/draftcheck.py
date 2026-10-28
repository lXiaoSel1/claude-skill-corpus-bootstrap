#!/usr/bin/env python3
"""Mechanical checks over ONE drafted paragraph. Read-only; judgment stays
with the model -- this script reports facts for the output slots.

WHY THIS EXISTS
    Until 2026-08-26 every SELF-CHECK item ran by eye: sentence counts for the
    SHAPE line, the ledger<->draft diff, the ownership regex, verb legality,
    Version existence.  All of these are mechanical definitions already stated
    in SKILL.md; this script computes them so the model spends its judgment on
    C-C-C and warrants, not on counting.  `src` checks the cited papers
    themselves: numbers and copied stretches against the corpus file or the
    PDF (factory 1.6.0, ported from the parent's fast lane with `router` and
    `version-card`).

RUN  (a paragraph is a file, - for stdin, or the paragraph text itself)
    py -3 scripts/draftcheck.py para draft.txt [--chapter <job>]
                                    # sentences · length vs the chapter's P90 · traceable · cites · verbs
    py -3 scripts/draftcheck.py own "<pasted source line>" [...]
    py -3 scripts/draftcheck.py version results/02-estimate.md 6
    py -3 scripts/draftcheck.py version-card <job>/03-evidence.md 12 [--full]   # fast lane
    py -3 scripts/draftcheck.py router <job>                                    # fast lane
    py -3 scripts/draftcheck.py numbers draft.txt tables/main.tex
    py -3 scripts/draftcheck.py section intro-draft.tex <chapter>
    py -3 scripts/draftcheck.py src draft.txt       # numbers and copied stretches vs the cited papers
    py -3 scripts/draftcheck.py src --line KEY "<pasted source line>"
    py -3 scripts/draftcheck.py src --find KEY "<phrase or number>" [KEY "<phrase>" ...]
                                    # is it in THAT paper's own text? exit 1 if any pair has no hit

Manuscript and table paths come from field-config (`manuscript_tex`,
`manuscript_tables`); citations are read from LaTeX \\cite{} and
Markdown/pandoc [@key]; `section` is skipped where field-config sets
`equation_layer: off` (prose fields), because its parenthesised-number proxy
has no meaning there. `version-card --full` prints, for each Example, the
whole corpus paragraph it comes from (from the chapter's slices), and the
chapter's short-paragraph bank entries for that Version when
references/sections/<job>/short-exemplars.md exists.
"""
import glob
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REF = os.path.join(SKILL, "references")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402
LIT = _jobs.lit_dir() or os.path.normpath(
    os.path.join(_jobs.corpus_dir(), "..", ".."))
if not os.path.exists(os.path.join(LIT, "scripts", "textseg.py")):
    sys.exit("lit instance not found at %s -- check lit_instance in"
             " field-config.yaml" % LIT)
sys.path.insert(0, os.path.join(LIT, "scripts"))
from textseg import split_sentences, paragraph_texts  # noqa: E402  (the shared splitter)
import _src  # noqa: E402

# SKILL.md's traceable-sentence predicate, verbatim mechanical form:
# numeral / percentage / comparative / directional verb. Word forms are
# listed, so "risk" is not "rise" and "significantly" is "significant".
TRACEABLE = re.compile(
    r"\d|\bpercent\b|%|\b(?:higher|lower|larger|smaller|greater|more|less|"
    r"increas(?:e|es|ed|ing)|decreas(?:e|es|ed|ing)|declin(?:e|es|ed|ing)|"
    r"ris(?:e|es|en|ing)|rose|fall(?:s|en|ing)?|fell|grow(?:s|n|ing|th)?|grew|"
    r"shr(?:ink|inks|ank|unk|inking)|positive|negative|"
    r"(?:in)?significant(?:ly)?)\b", re.I)

# every citation command, natbib and biblatex, not \nocite (the pattern polish's
# manuscript.py and lit's build_corpus_meta.py use)
CITE_CMD = _src.CITE_CMD
CITE = _src.CITE
MD_CITE = re.compile(r"@([A-Za-z0-9][A-Za-z0-9_:\-]*)")   # pandoc [@key; @k2]

# Attribution-verb legality (verb-ladder.md).  `report ... that` is flagged
# outright in the parent (economics: 4% that-rate, it points at your own
# tables); this instance's own rate is in verb-ladder.md after Tier 4.
REPORT_THAT = re.compile(r"\breports?\s+that\b", re.I)
LADDER = {"find", "finds", "show", "shows", "suggest", "suggests", "argue",
          "argues", "note", "notes", "document", "documents", "attribute",
          "attributes"}

# The ownership regex, exactly as SKILL.md prints it.
# FACTORY PARAMETERIZATION: the author-year ownership regex assumes
# Author (Year) citation culture.  Numeric-citation fields (IEEE [12])
# get a bracket-detector instead, and ownership drops to judgment.
import _fieldstyle  # noqa: E402
OWNER = _fieldstyle.owner_re()

NUM = re.compile(r"-?\d+(?:[.,]\d+)+|-?\d+(?:\.\d+)?%?")


def read_arg(a):
    """A file, - for stdin, or the paragraph text itself."""
    if a == "-":
        return sys.stdin.read()
    if os.path.isfile(a):
        with open(a, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if len(a.split()) >= 3:
        return a
    sys.exit("not a file, and too short to be a paragraph: %r" % a)


def strip_tex(s):
    s = re.sub(r"(?<!\\)%.*", "", s)
    s = re.sub(CITE_CMD + r"\{[^}]*\}", "CITE", s)
    s = re.sub(r"\[@[^\]]*\]", "CITE", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*", " ", s)
    return re.sub(r"[{}~]", " ", s)


def chapter_p90(chapter):
    """Words-per-sentence P90 of the chapter's corpus slices (all chapters
    when none is named), split by the shared splitter; None without slices."""
    root = os.path.join(REF, "slices")
    paths = glob.glob(os.path.join(root, chapter, "*.txt")) if chapter else glob.glob(os.path.join(root, "*", "*.txt"))
    lens = []
    for p in paths:
        if os.path.basename(p).startswith("_"):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            for para in paragraph_texts(fh.read(), min_chars=200):
                lens += [n for n in (len(s.split()) for s in split_sentences(para)) if 3 <= n <= 150]
    if not lens:
        return None, 0
    lens.sort()
    return lens[int(0.9 * (len(lens) - 1))], len(lens)


def cmd_para(arg, chapter):
    raw = read_arg(arg)
    keys = sorted({k.strip() for m in CITE.findall(raw)
                   for k in m.split(",") if k.strip()}
                  | set(MD_CITE.findall(" ".join(re.findall(r"\[@[^\]]*\]",
                                                            raw)))))
    sents = split_sentences(strip_tex(raw))
    sents = [s for s in sents if len(s.split()) >= 3]
    traceable = [i for i, s in enumerate(sents, 1) if TRACEABLE.search(s)]
    rt = REPORT_THAT.findall(raw)
    p90, n = chapter_p90(chapter)
    words = [len([w for w in s.split() if w != "CITE"]) for s in sents]
    print("sentences: %d" % len(sents))
    for i, s in enumerate(sents, 1):
        mark = "T" if i in traceable else "."
        over = "  OVER P90" if p90 and words[i - 1] > p90 else ""
        print("  %s %2d  %3dw%s  %s" % (mark, i, words[i - 1], over, s[:100]))
    if p90:
        long_ = [i for i, w in enumerate(words, 1) if w > p90]
        print("length: corpus P90 %d words (%s, %d sentences); over it: %s"
              % (p90, chapter or "all chapters", n, long_ or "none"))
    print("traceable (need a ledger row): %d of %d -- %s"
          % (len(traceable), len(sents), traceable or "none"))
    print("cite keys (each needs a ledger row): %s" % (", ".join(keys) or "none"))
    used = sorted({w.lower() for w in re.findall(r"[A-Za-z]+", raw)}
                  & LADDER)
    print("attribution verbs used: %s  (strength: verb-ladder.md)"
          % (", ".join(used) or "none"))
    if rt:
        print("VERB FLAG: 'report(s) that' x%d -- report is NOT an attribution"
              " verb (verb-ladder.md)" % len(rt))
    else:
        print("verb flags: 0")


def cmd_own(lines):
    for l in lines:
        hits = [m.group(0) for m in OWNER.finditer(l)]
        if hits:
            print("THIRD-PARTY  hits=%r  %s" % (hits, l[:90]))
        else:
            print("clean        %s" % l[:90])


def cmd_version(part, n):
    path = os.path.join(REF, "sections", part)
    if not os.path.exists(path):
        print("NO SUCH PART FILE:", part); sys.exit(1)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    m = re.search(r"(?m)^### Version %s\b.*$" % re.escape(n), text)
    if m:
        print("EXISTS:", m.group(0).strip())
    else:
        have = re.findall(r"(?m)^### Version (\d+)", text)
        print("NO Version %s in %s -- it has: %s" % (n, part, ", ".join(have)))
        sys.exit(1)


FIELD = re.compile(r"^(Pattern|Example|Use it when|Not this when)\b\s*(.*)$")
EXAMPLE = re.compile(r"[\"“](.+?)[\"”]\s*(?:—|--|-)\s*([A-Za-z0-9_][\w\-]*)(?:\s*¶\s*(\d+))?")
_AY = re.compile(r"\b[A-Z][A-Za-z'’\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z'’\-]+)?(?:\s+et\s+al\.?)?"
                 r"[\s,]*\(?\s*(?:19|20)\d{2}[a-z]?")


def _norm(s):
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def slice_paragraph(chapter, key, quote):
    """The slice paragraph of `key` in `chapter` that holds `quote` (or None)."""
    p = os.path.join(REF, "slices", chapter, key + ".txt")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        paras = paragraph_texts(fh.read(), min_chars=40)
    want = _norm(quote)[:80]
    for para in paras:
        if want and want in _norm(para):
            return para
    return None


def describe(para):
    n_w = len(para.split())
    n_c = len({m.group(0).lower() for m in _AY.finditer(para)})
    return "%d words · %d sentences · %d author-year citations" % (n_w, len(split_sentences(para)), n_c)


def resolve_part(part):
    path = os.path.join(REF, "sections", part)
    if not os.path.exists(path):              # "03-evidence" or "03-evidence.md" without its chapter
        name = os.path.basename(part)
        hits = glob.glob(os.path.join(REF, "sections", "*", name))
        hits += glob.glob(os.path.join(REF, "sections", "*", name + ".md"))
        if len(hits) == 1:
            path = hits[0]
            part = os.path.relpath(path, os.path.join(REF, "sections")).replace(os.sep, "/")
    return path, part


def cmd_version_card(part, n, full=False):
    """One Version's Pattern, Use it when, Not this when and two examples -- what
    the fast lane reads instead of the whole part file. --full adds the whole
    corpus paragraph behind each example and the chapter's short-paragraph bank
    entries for the Version."""
    path, part = resolve_part(part)
    if not os.path.exists(path):
        print("NO SUCH PART FILE:", part)
        sys.exit(1)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    m = re.search(r"(?m)^### Version %s\b.*$" % re.escape(n), text)
    if not m:
        print("NO Version %s in %s -- it has: %s" % (n, part, ", ".join(re.findall(r"(?m)^### Version (\d+)", text))))
        sys.exit(1)
    end = re.search(r"(?m)^(?:### |## |---\s*$)", text[m.end():])
    block = text[m.end():m.end() + end.start()] if end else text[m.end():]
    fields, cur = {}, None
    for l in block.split("\n"):
        f = FIELD.match(l)
        if f:
            cur = f.group(1)
            fields.setdefault(cur, []).append(f.group(2).strip())
        elif cur and l.startswith("  ") and l.strip():
            if cur == "Example":
                fields[cur].append(l.strip())
            else:
                fields[cur][-1] += " " + l.strip()
        elif not l.strip():
            cur = None
    print(m.group(0).strip() + "   (" + part + ")")
    for name in ("Pattern", "Use it when", "Not this when"):
        for v in fields.get(name, []):
            print("%-14s %s" % (name, v))
    examples = fields.get("Example", [])
    for v in examples[:2]:
        print("%-14s %s" % ("Example", v))
    if not full:
        return
    chapter = part.split("/")[0] if "/" in part else ""
    print("\nFULL PARAGRAPHS behind the examples (chapter slices: %s)" % (chapter or "?"))
    shown = 0
    for v in examples:
        e = EXAMPLE.search(v)
        if not e:
            continue
        para = slice_paragraph(chapter, e.group(2), e.group(1)) if chapter else None
        if para:
            shown += 1
            print("\n-- %s%s · %s" % (e.group(2), (" ¶" + e.group(3)) if e.group(3) else "", describe(para)))
            print(para)
    if not shown:
        print("  (no example could be found in the slices)")
    bank = os.path.join(REF, "sections", chapter, "short-exemplars.md") if chapter else ""
    if bank and os.path.isfile(bank):
        with open(bank, encoding="utf-8", errors="replace") as fh:
            btxt = fh.read()
        # Version numbers restart in every part file, so a split chapter's
        # bank heading names its part -- '## Version 6 (03-evidence)' -- and
        # matching the number alone printed 02-mechanism's Version 6 for
        # 03-evidence's (a finance build, 2026-10-27). Number alone only when the bank
        # names no parts (a single-file chapter).
        stem = os.path.splitext(os.path.basename(path))[0]
        b = re.search(r"(?m)^## Version %s \(%s\)\s*$" % (re.escape(n), re.escape(stem)), btxt)
        if not b and not re.search(r"(?m)^## Version \d+ \(", btxt):
            b = re.search(r"(?m)^## Version %s\b.*$" % re.escape(n), btxt)
        if b:
            bend = re.search(r"(?m)^## ", btxt[b.end():])
            print("\nSHORT-PARAGRAPH BANK (%s):" % os.path.relpath(bank, SKILL).replace(os.sep, "/"))
            print(btxt[b.end():b.end() + bend.start()].strip() if bend else btxt[b.end():].strip())
        else:
            print("\nshort-paragraph bank: no entry for Version %s" % n)


def cmd_router(chapter):
    """The chapter's Version router (its skeleton's table rows), nothing else."""
    path = os.path.join(REF, "sections", chapter, "00-skeleton.md")
    if not os.path.exists(path):
        print("NO SKELETON for chapter %s" % chapter)
        sys.exit(1)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    m = re.search(r"(?m)^## \d+\. The Version router.*$", text) or re.search(r"(?m)^## .*[Rr]outer.*$", text)
    if not m:
        print("no router section in %s" % path)
        sys.exit(1)
    end = re.search(r"(?m)^(?:## |---\s*$)", text[m.end():])
    block = text[m.end():m.end() + end.start()] if end else text[m.end():]
    print(m.group(0).strip())
    for l in block.split("\n"):
        if l.startswith("|") and not re.match(r"^\|[\s|:-]+\|$", l):
            print(l)


def cmd_numbers(draft, table):
    d = strip_tex(read_arg(draft))
    tables_dir = _jobs.manuscript_paths()[1]   # resolved: absolute or project-relative
    if os.path.isabs(table) or os.path.exists(table):
        tpath = table
    elif tables_dir:
        tpath = os.path.join(tables_dir, table)
    else:
        sys.exit("relative table path and no manuscript_tables in"
                 " field-config.yaml -- give an absolute path")
    t = read_arg(tpath)
    dn = set(NUM.findall(d))
    tn = set(NUM.findall(t))
    # a draft "8.82%" should match a table "8.82"
    tn |= {x + "%" for x in tn} | {x.rstrip("%") for x in tn}
    missing = sorted(x for x in dn if x not in tn and len(x.rstrip("%")) > 1)
    print("draft numerals: %s" % (", ".join(sorted(dn)) or "none"))
    if missing:
        print("NOT IN TABLE (MISMATCH candidates -- read the table before"
              " judging): %s" % ", ".join(missing))
        sys.exit(1)
    print("all multi-digit draft numerals appear in %s" % os.path.basename(tpath))


# ---- section-level: displayed equations vs the corpus norm -----------------
# WHY THIS EXISTS.  On 2026-08-29 a whole introduction was drafted with one
# displayed equation where the corpus median is ten and NOT ONE of 22 papers
# has zero.  The cause was a misread: the skeleton's "do not run Versions 22-26
# here" bars displayed THEOREMS, and the drafter dropped displayed EQUATIONS
# too.  Nothing failed, because every existing check is per-paragraph and
# equation density is a chapter-level fact -- there was no slot in which the
# absence could show up.  This is that slot.
DISPLAY = re.compile(
    r"\\begin\{(equation|align|gather|multline|eqnarray)\*?\}"
    r"|\\\[|\$\$")


def cmd_section(path, chapter):
    from _cfgparse import as_str
    if as_str(_jobs._DATA.get("equation_layer"), "on") == "off":
        print("equation_layer: off in field-config.yaml -- this field's prose"
              " carries no displayed-equation norm; nothing to check")
        return
    raw = read_arg(path)
    n_draft = len(DISPLAY.findall(raw))
    norms_path = os.path.join(REF, "structure-norms.json")
    if not os.path.exists(norms_path):
        sys.exit("no structure-norms.json -- run scripts/measure_structure.py")
    with open(norms_path, encoding="utf-8") as fh:
        norms = json.load(fh)
    e = (norms.get("E_equation_density") or {}).get(chapter)
    print("displayed equations in draft: %d" % n_draft)
    if not e:
        print("corpus norm for %r: NOT MEASURED (no slices for this chapter)"
              % chapter)
        print("verdict: unjudgeable -- report the count, claim nothing")
        return
    print("corpus norm (%s, n=%d): median %d · P25 %d · P75 %d · max %d"
          % (chapter, e["papers"], e["median"], e["p25"], e["p75"], e["max"]))
    print("papers in the corpus with ZERO displayed equations here: %d of %d"
          % (e["papers_with_zero"], e["papers"]))
    # The only mechanical verdict worth printing. Everything else is judgment:
    # the proxy counts numbered labels, so it cannot support a range test.
    if n_draft == 0 and e["papers_with_zero"] == 0:
        print("\nFLAG: your draft displays no equation, and NO paper in this"
              " corpus writes this chapter without one.")
        sys.exit(1)
    if n_draft < e["p25"]:
        print("\nQUESTION (not a defect): the draft is below the corpus P25"
              " (%d). Is a derivation step being asserted in prose that the"
              " literature displays?" % e["p25"])
    else:
        print("\nwithin the corpus range -- no flag")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "para":
        chapter = a[a.index("--chapter") + 1] if "--chapter" in a else None
        cmd_para(a[1], chapter)
    elif cmd == "own":
        cmd_own(a[1:])
    elif cmd == "version":
        cmd_version(a[1], a[2])
    elif cmd == "version-card":
        cmd_version_card(a[1], a[2], "--full" in a)
    elif cmd == "router":
        cmd_router(a[1])
    elif cmd == "numbers":
        cmd_numbers(a[1], a[2])
    elif cmd == "section":
        cmd_section(a[1], a[2])
    elif cmd == "src":
        if a[1] == "--line":
            sys.exit(_src.cmd_line(a[2], a[3]))
        if a[1] == "--find":
            pairs = a[2:]
            if not pairs or len(pairs) % 2:
                sys.exit("src --find takes KEY \"<phrase>\" pairs\n" + __doc__)
            # every pair is looked up; the exit code says whether all were found
            sys.exit(max(_src.cmd_find(k, w) for k, w in zip(pairs[::2], pairs[1::2])))
        sys.exit(_src.cmd_src(read_arg(a[1]), split_sentences))
    else:
        sys.exit("unknown command: " + cmd + "\n" + __doc__)


if __name__ == "__main__":
    main()
