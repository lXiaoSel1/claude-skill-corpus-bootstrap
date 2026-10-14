#!/usr/bin/env python3
"""Check everything {{FIELD}}-polish needs, and say which steps can run now.

Reports: Python and PyMuPDF; the TeX tools; the sibling skills and the tiers
they have built; the manuscript (sections, bibliography, .bbl, aliases); the
library index (how many cited keys have a PDF); reading notes; the humanizer
G section; then one row per step a-j.

RUN
    py -3 scripts/doctor.py [--manuscript main.tex]
Exit code 1 when the manuscript or the lit skill cannot be found.
"""
import os
import shutil
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
rows = []


def say(ok, what, detail=""):
    print("  %s %-26s %s" % ("✅" if ok else ("⚠️" if ok is None else "⛔"), what, detail))


print("environment")
say(sys.version_info >= (3, 8), "python", sys.version.split()[0] + ("" if sys.version_info >= (3, 8)
                                                                    else "  (3.8 or later needed)"))
try:
    import fitz
    say(True, "PyMuPDF", getattr(fitz, "VersionBind", "?"))
    has_fitz = True
except ImportError:
    say(False, "PyMuPDF", "py -3 -m pip install pymupdf  (needed to read PDFs)")
    has_fitz = False
tex = {t: shutil.which(t) for t in ("pdflatex", "xelatex", "bibtex", "biber")}
say(bool(tex["pdflatex"] or tex["xelatex"]), "TeX", ", ".join(t for t, p in tex.items() if p) or "none on PATH")

print("\nsibling skills")
lit_ok = os.path.isfile(os.path.join(ctx.lit, "scripts", "attest.py"))
say(lit_ok, "%s-lit" % _rp.FIELD, ctx.lit)
lt, dt = ctx.built_tiers("lit"), ctx.built_tiers("draft")
draft_ok = os.path.isdir(ctx.draft)
say(draft_ok or None, "%s-draft" % _rp.FIELD, ctx.draft)
say(bool(lt) or None, "built tiers", "lit %s · draft %s" % (lt or "none", dt or "none"))

print("\nmanuscript")
try:
    ms = ctx.ms
except SystemExit:
    ms = None
    say(False, "main .tex", "not found -- pass --manuscript, or finish onboarding")
if ms:
    say(True, "main .tex", ms.path)
    say(bool(ms.sections), "sections", "%d (%s): %s" % (len(ms.sections),
        "input files" if ms.sections and ms.sections[0].kind == "file" else "split at \\" + ms.split_level,
        ", ".join(s.key for s in ms.sections[:15]) + (" ..." if len(ms.sections) > 15 else "")))
    say(all(os.path.isfile(b) for b in ms.bib_files) if ms.bib_files else None,
        "bibliography", ", ".join(os.path.basename(b) for b in ms.bib_files) or "none declared")
    say(os.path.isfile(ms.bbl) or None, ".bbl", "present" if os.path.isfile(ms.bbl) else "not compiled yet (compile.py)")
    say(True, "citation aliases", "%d" % len(ms.aliases))
    keys = ms.cited_keys()
    idx = ctx.library_index()
    have = [k for k in keys if (idx.get(k) or {}).get("pdf") and os.path.isfile(idx[k]["pdf"])]
    corp = [k for k in keys if k not in have and os.path.isfile(
        os.path.join(ctx.lit, "references", "corpus", k + ".txt"))]
    say(bool(idx) or None, "library index",
        "%d of %d cited keys have a PDF; %d more only a corpus text" % (len(have), len(keys), len(corp))
        if idx else "none (.polish/library-index.json) -- run onboarding")
    notes = ctx.opts["notes_dir"] or ctx.library_index_meta().get("notes_dir")
    say(bool(notes) or None, "reading notes", notes or "none (note_terms.py unavailable)")
    if ctx.config_file:
        say(True, "polish.yaml", ctx.config_file)

# the user's skills, or the project's own .claude/skills next to this instance
hzs = [os.path.join(os.path.expanduser("~"), ".claude", "skills", "humanizer", "SKILL.md"),
       os.path.join(os.path.dirname(_rp.SKILL), "humanizer", "SKILL.md")]
hz = next((p for p in hzs if os.path.isfile(p) and "§27" in _rp.read(p)), hzs[0])
hz_g = os.path.isfile(hz) and "§27" in _rp.read(hz)
say(True, "humanizer section G", hz if hz_g else "use references/humanizer-G.md (installed humanizer has no §27-§32)")

print("\nsteps")
t0, t1, t2, t3 = 0 in lt, 1 in lt, 2 in dt, 3 in dt
steps = [
    ("a", "snapshot.py", bool(ms), ""),
    ("b", "sweep.py", bool(ms) and t0, "" if t0 else "lit Tier 0"),
    ("c", "rewrite + attest.py", t0, "" if t0 else "lit Tier 0"),
    ("d", "/%s-lit + cohesion_loop.py" % _rp.FIELD, t1, "" if t1 else "lit Tier 1"),
    ("d2", "opener_check.py", t3, "" if t3 else "draft Tier 3 (records)"),
    ("e", "source_term_check / pdf_ctx", bool(ms) and (has_fitz or t0), ""),
    ("e", "note_terms.py", bool(ms) and bool(ms and (ctx.opts["notes_dir"] or ctx.library_index_meta().get("notes_dir"))), "reading notes"),
    ("f", "humanizer section G", True, ""),
    ("g", "trial_diff / para_lengths / scan_appositive", bool(ms) and t0, "" if t0 else "lit Tier 0"),
    ("g", "words_compare.py (optional)", t2, "" if t2 else "draft Tier 2 (slices)"),
    ("h2", "sent_diff.py", bool(ms), ""),
    ("i", "compile.py / counts.py", bool(ms) and bool(tex["pdflatex"] or tex["xelatex"]), "TeX"),
    ("j", "render_section.py", bool(ms) and os.path.isfile(ms.bbl) if ms else False, "a compiled .bbl"),
]
for step, what, ok, need in steps:
    print("  %-3s %-44s %s" % (step, what, "ready" if ok else "needs " + (need or "the manuscript")))
sys.exit(0 if (ms and lit_ok) else 1)
