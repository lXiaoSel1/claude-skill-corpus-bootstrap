#!/usr/bin/env python3
"""Step i -- compile the manuscript where it lives (engine, bibliography,
engine, engine) and report the page count and every LaTeX / BibTeX warning.

Engine, first that applies: polish.yaml `compile_engine` (pdflatex |
xelatex | lualatex); a `% !TEX program = ...` line, or a comment such as
"% Compiles with pdfLaTeX" in the first five lines of the main file; xelatex
when the preamble loads fontspec / xeCJK / unicode-math outside an engine
test (`\\ifPDFTeX ... \\else ... \\fi` and the like: such a manuscript runs
on either engine); else pdflatex. Bibliography: `bib_engine` (bibtex |
biber | none), else biber for biblatex, bibtex for \\bibliography{}, none
otherwise.

After compiling it lists citations that a page break splits (one link on two
pages, which puts part of the citation on the next page); without hyperref
links, check the page breaks by eye.

RUN
    py -3 scripts/compile.py [--dry-run]     # --dry-run: print the engine and why, compile nothing
Exit code 1 on a compile error or any warning (Overfull / Underfull boxes
included); the target is 0.
"""
import os
import re
import shutil
import subprocess
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
dry = _rp._pop(ctx.args, "--dry-run", flag=True)
ms = ctx.ms
pre = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in ms.preamble.splitlines())
ENGINES = ("pdflatex", "xelatex", "lualatex")
MAGIC = re.compile(r"^\s*%\s*!\s*TE?X\s+(?:TS-)?program\s*=\s*(pdflatex|xelatex|lualatex)", re.I)
SAYS = re.compile(r"^\s*%.*?\bcompiles?\s+with\s+(pdf|xe|lua)latex", re.I)
ENGINE_IF = re.compile(r"\\if(?:PDFTeX|pdftex|pdf|xetex|XeTeX|luatex|LuaTeX|tutex|TUTeX)$")
UNICODE_PKG = re.compile(r"\\usepackage(\[[^\]]*\])?\{[^}]*\b(fontspec|xeCJK|unicode-math)\b")


def outside_engine_tests(text):
    """The preamble without its engine tests (\\ifPDFTeX ... \\fi, nested \\if
    counted), so packages loaded for one engine only are not read as a
    requirement."""
    out, depth = [], 0
    for t in re.split(r"(\\if[A-Za-z]*|\\fi\b)", text):
        if depth == 0:
            if ENGINE_IF.match(t):
                depth = 1
            else:
                out.append(t)
        elif t.startswith("\\if"):
            depth += 1
        elif t == "\\fi":
            depth -= 1
    return "".join(out)


def choose_engine():
    e = str(ctx.opts["compile_engine"]).lower()
    if e in ENGINES:
        return e, "polish.yaml compile_engine"
    for i, line in enumerate(ms.lines[:5], 1):
        m = MAGIC.match(line)
        if m:
            return m.group(1).lower(), "%s line %d (%% !TEX program)" % (os.path.basename(ms.path), i)
        m = SAYS.match(line)
        if m:
            return m.group(1).lower() + "latex", "%s line %d says so" % (os.path.basename(ms.path), i)
    if UNICODE_PKG.search(outside_engine_tests(pre)):
        return "xelatex", "the preamble loads fontspec / xeCJK / unicode-math"
    return "pdflatex", "default"


eng, why = choose_engine()
bib = str(ctx.opts["bib_engine"]).lower()
if bib == "auto":
    if re.search(r"\\usepackage(\[[^\]]*\])?\{biblatex\}", pre):
        bib = "biber"
    elif ms.bib_files:
        bib = "bibtex"
    else:
        bib = "none"
if dry:
    print("engine %s (%s); bibliography %s" % (eng, why, bib))
    sys.exit(0)
for tool in [eng] + ([bib] if bib != "none" else []):
    if not shutil.which(tool):
        _rp.die("%s is not on PATH" % tool)


def run(cmd):
    r = subprocess.run(cmd, cwd=ms.dir, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    return r.returncode, r.stdout


tex = [eng, "-interaction=nonstopmode", "-file-line-error", os.path.basename(ms.path)]
steps = [tex] + ([[bib, ms.stem]] if bib != "none" else []) + [tex, tex]
print("compiling %s with %s (%s)%s" % (ms.path, eng, why, "" if bib == "none" else " + " + bib))
for cmd in steps:
    code, out = run(cmd)
    print("  %-8s exit %d" % (cmd[0], code))

log = os.path.join(ms.dir, ms.stem + ".log")
RERUN = re.compile(r"Rerun to get|Label\(s\) may have changed|Rerun LaTeX")
for _ in range(2):                    # as latexmk does: rerun while the log asks
    text = _rp.read(log) if os.path.isfile(log) else ""
    if not RERUN.search(text):
        break
    code, out = run(tex)
    print("  %-8s exit %d  (rerun: the log asked for one)" % (eng, code))
text = _rp.read(log) if os.path.isfile(log) else ""
errors = re.findall(r"^(?:! |.*:\d+: ).*$", text, re.M)
warn = [l for l in text.splitlines() if re.search(r"Warning|Overfull|Underfull", l)]
pages = re.search(r"Output written on .*?\((\d+) pages?", text)
print("pages: %s" % (pages.group(1) if pages else "?"))
print("LaTeX errors: %d" % len(errors))
for l in errors[:10]:
    print("  " + l)
print("LaTeX warnings (Warning / Overfull / Underfull lines): %d" % len(warn))
for l in warn[:20]:
    print("  " + l)
bw = 0
if bib == "bibtex":
    blg = os.path.join(ms.dir, ms.stem + ".blg")
    b = _rp.read(blg) if os.path.isfile(blg) else ""
    m = re.search(r"\(There (?:was|were) (\d+) warnings?\)", b)
    bw = int(m.group(1)) if m else 0
    print("BibTeX warnings: %d" % bw)
    for l in [l for l in b.splitlines() if l.startswith("Warning--")][:20]:
        print("  " + l)
elif bib == "biber":
    blg = os.path.join(ms.dir, ms.stem + ".blg")
    b = _rp.read(blg) if os.path.isfile(blg) else ""
    ws = [l for l in b.splitlines() if "WARN" in l or "ERROR" in l]
    bw = len(ws)
    print("biber warnings/errors: %d" % bw)
    for l in ws[:20]:
        print("  " + l)
pdf = os.path.join(ms.dir, ms.stem + ".pdf")
split = _rp.split_cite_links(pdf) if os.path.isfile(pdf) else None
if split is None:
    print("citations split across pages: no citation links (hyperref not loaded) -- check page breaks by eye")
else:
    print("citations split across pages: %d%s" % (len(split), "".join(
        "\n  page %d: %s (reword, or \\mbox{} the citation)" % (p, t) for p, t in split)))
sys.exit(1 if (errors or warn or bw or not pages) else 0)
