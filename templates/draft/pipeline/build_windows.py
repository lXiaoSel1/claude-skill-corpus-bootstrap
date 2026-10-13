# -*- coding: utf-8 -*-
"""Tier 2 step 1 input: every a1_candidates.json heading candidate plus the
~600 characters of prose that follow it -> pipeline/a1_windows.md.

taxonomy-induction.md rule 2 requires the inducer to read prose windows, not
heading strings; this builds exactly that input. BACK-PORTED 2026-10-07 from
a mathematics -draft instance (it was created there 2026-09-07 and never reached the
template), with the sample size computed instead of the hardcoded "45".

    py -3 pipeline/build_windows.py
"""
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import _jobs  # noqa: E402

CORPUS = _jobs.corpus_dir()
WIN = 600            # characters of prose after each heading (rule 2)
FOLLOW_LINES = 40    # lines scanned to fill the window


def main():
    cand = json.load(io.open(os.path.join(BASE, "a1_candidates.json"),
                             encoding="utf-8"))
    out_path = os.path.join(BASE, "a1_windows.md")
    n = 0
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as out:
        out.write("# A1 heading candidates + %d-character prose windows —"
                  " Tier 2 step 1 induction input\n" % WIN)
        out.write("# %d papers (pipeline/sample-keys.txt)\n\n" % len(cand))
        for key in sorted(cand):
            rec = cand[key]
            lines = io.open(os.path.join(CORPUS, key + ".txt"), encoding="utf-8",
                            errors="replace").read().split("\n")
            out.write("\n%s\n## %s  (format=%s, %d candidates)\n%s\n"
                      % ("=" * 70, key, rec.get("format"),
                         len(rec["candidates"]), "=" * 70))
            for c in rec["candidates"]:
                ln = c["line"]
                body = re.sub(r"\s+", " ",
                              " ".join(lines[ln:ln + FOLLOW_LINES])).strip()[:WIN]
                flags = ",".join(c.get("flags") or []) or "-"
                out.write("\n### [%s L%d] num=%s lvl=%s pat=%s flags=%s\n"
                          % (key, ln, c["num"] or "-", c["level"], c["pattern"],
                             flags))
                out.write("HEADING: %s\n" % c["verbatim"])
                out.write("WINDOW : %s\n" % body)
                n += 1
    print("wrote a1_windows.md — %d candidate windows, %d papers" % (n, len(cand)))
    print("size: %d bytes" % os.path.getsize(out_path))


if __name__ == "__main__":
    main()
