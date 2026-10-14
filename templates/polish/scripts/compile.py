#!/usr/bin/env python3
"""Step i -- compile the manuscript where it lives (engine, bibliography,
engine, engine) and report the page count and every LaTeX / BibTeX warning.

Engine: polish.yaml `compile_engine` (pdflatex | xelatex | lualatex), else
xelatex when the preamble loads fontspec / xeCJK / unicode-math, else
pdflatex. Bibliography: `bib_engine` (bibtex | biber | none), else biber
for biblatex, bibtex for \\bibliography{}, none otherwise.

RUN
    py -3 scripts/compile.py
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
ms = ctx.ms
pre = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in ms.preamble.splitlines())
eng = str(ctx.opts["compile_engine"]).lower()
if eng == "auto":
    eng = "xelatex" if re.search(r"\\usepackage(\[[^\]]*\])?\{[^}]*\b(fontspec|xeCJK|unicode-math)\b", pre) else "pdflatex"
bib = str(ctx.opts["bib_engine"]).lower()
if bib == "auto":
    if re.search(r"\\usepackage(\[[^\]]*\])?\{biblatex\}", pre):
        bib = "biber"
    elif ms.bib_files:
        bib = "bibtex"
    else:
        bib = "none"
for tool in [eng] + ([bib] if bib != "none" else []):
    if not shutil.which(tool):
        _rp.die("%s is not on PATH" % tool)


def run(cmd):
    r = subprocess.run(cmd, cwd=ms.dir, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    return r.returncode, r.stdout


tex = [eng, "-interaction=nonstopmode", "-file-line-error", os.path.basename(ms.path)]
steps = [tex] + ([[bib, ms.stem]] if bib != "none" else []) + [tex, tex]
print("compiling %s with %s%s" % (ms.path, eng, "" if bib == "none" else " + " + bib))
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
sys.exit(1 if (errors or warn or bw or not pages) else 0)
