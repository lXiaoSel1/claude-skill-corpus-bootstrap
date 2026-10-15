#!/usr/bin/env python3
"""Mechanical checks over ONE drafted paragraph. Read-only; judgment stays
with the model -- this script reports facts for the output slots.

WHY THIS EXISTS
    Until 2026-08-26 every SELF-CHECK item ran by eye: sentence counts for the
    SHAPE line, the ledger<->draft diff, the ownership regex, verb legality,
    Version existence.  All of these are mechanical definitions already stated
    in SKILL.md; this script computes them so the model spends its judgment on
    C-C-C and warrants, not on counting.

RUN  (paragraph text via a file, or - for stdin)
    py -3 scripts/draftcheck.py para draft.txt          # sentences · traceable · cites · verbs
    py -3 scripts/draftcheck.py own "<pasted source line>" [...]
    py -3 scripts/draftcheck.py version results/02-estimate.md 6
    py -3 scripts/draftcheck.py numbers draft.txt tables/main.tex
    py -3 scripts/draftcheck.py section intro-draft.tex <chapter>

Manuscript and table paths come from field-config (`manuscript_tex`,
`manuscript_tables`); citations are read from LaTeX \\cite{} and
Markdown/pandoc [@key]; `section` is skipped where field-config sets
`equation_layer: off` (prose fields), because its parenthesised-number proxy
has no meaning there.
"""
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
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402
LIT = _jobs.lit_dir() or os.path.normpath(
    os.path.join(_jobs.corpus_dir(), "..", ".."))
if not os.path.exists(os.path.join(LIT, "scripts", "textseg.py")):
    sys.exit("lit instance not found at %s -- check lit_instance in"
             " field-config.yaml" % LIT)
sys.path.insert(0, os.path.join(LIT, "scripts"))
from textseg import split_sentences  # noqa: E402  (the shared splitter)

# SKILL.md's traceable-sentence predicate, verbatim mechanical form:
# numeral / percentage / comparative / directional verb.
TRACEABLE = re.compile(
    r"\d|\bpercent\b|%|\b(?:higher|lower|larger|smaller|greater|more|less|"
    r"increas\w+|decreas\w+|declin\w+|ris\w+|fall\w+|grow\w+|shrink\w+|"
    r"positive|negative|significant|insignificant)\b", re.I)

CITE = re.compile(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]*)\}")
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
import _fieldstyle
OWNER = _fieldstyle.owner_re()

NUM = re.compile(r"-?\d+(?:[.,]\d+)+|-?\d+(?:\.\d+)?%?")


def read_arg(a):
    if a == "-":
        return sys.stdin.read()
    with open(a, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def strip_tex(s):
    s = re.sub(r"%.*", "", s)
    s = re.sub(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{[^}]*\}", "CITE", s)
    s = re.sub(r"\[@[^\]]*\]", "CITE", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*", " ", s)
    return re.sub(r"[{}~]", " ", s)


def cmd_para(path):
    raw = read_arg(path)
    keys = sorted({k.strip() for m in CITE.findall(raw)
                   for k in m.split(",") if k.strip()}
                  | set(MD_CITE.findall(" ".join(re.findall(r"\[@[^\]]*\]",
                                                            raw)))))
    sents = split_sentences(strip_tex(raw))
    sents = [s for s in sents if len(s.split()) >= 3]
    traceable = [i for i, s in enumerate(sents, 1) if TRACEABLE.search(s)]
    rt = REPORT_THAT.findall(raw)
    print("sentences: %d" % len(sents))
    for i, s in enumerate(sents, 1):
        mark = "T" if i in traceable else "."
        print("  %s %2d  %s" % (mark, i, s[:100]))
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
        m = OWNER.search(l)
        if m:
            print("THIRD-PARTY  hit=%r  %s" % (m.group(0), l[:90]))
        else:
            print("clean        %s" % l[:90])


def cmd_version(part, n):
    path = os.path.join(SKILL, "references", "sections", part)
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
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "para":
        cmd_para(sys.argv[2])
    elif cmd == "own":
        cmd_own(sys.argv[2:])
    elif cmd == "version":
        cmd_version(sys.argv[2], sys.argv[3])
    elif cmd == "numbers":
        cmd_numbers(sys.argv[2], sys.argv[3])
    elif cmd == "section":
        cmd_section(sys.argv[2], sys.argv[3])
    else:
        sys.exit("unknown command: " + cmd + "\n" + __doc__)


if __name__ == "__main__":
    main()
