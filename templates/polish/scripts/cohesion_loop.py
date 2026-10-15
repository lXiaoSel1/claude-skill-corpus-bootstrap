#!/usr/bin/env python3
"""Step d -- run {{FIELD}}-lit's cohesion.py on every paragraph of >= 3 sentences
in the named sections and print a compact digest: every join with its grade,
overlap and carriers (the rows the -lit JOINS table needs; WEAK/BROKEN marked
!), the percentile tails, and the M8 pair the review must adjudicate.

The norm cell is the lit field-config's `intro_job` (override with
polish.yaml `cohesion_section`).

RUN
    py -3 scripts/cohesion_loop.py <section> [section ...]
"""
import json
import os
import re
import subprocess
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
if not ctx.args:
    _rp.die(__doc__)
split_sentences = ctx.split_sentences()
JOB = ctx.intro_job()
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")   # the paragraph goes in on stdin
LABELS = [("m6b_singleton_rate", "M6b singleton rate"),
          ("m4_centroid_overlap", "M4 centroid overlap"),
          ("m5_orphan_rate", "M5' orphan rate"),
          ("m3_two_span_binary", "M3 two-span overlap"),
          ("m1_adjacent_binary", "M1 adjacent binary"),
          ("m8_max_nonadj_overlap", "M8 max non-adj overlap"),
          ("m9_anaphoric_opener_rate", "M9 anaphoric openers")]


def clean(line):
    line = re.sub(r"(?<!\\)%.*", "", line).replace("\\%", "%").replace("\\$", "$").replace("\\&", "&")
    line = re.sub(r"\\(?:citet|textcite|Citet|Textcite)\*?(?:\[[^\]]*\]){0,2}\{([A-Za-z]+)[^}]*\}",
                  r"\1 et al.", line)
    line = _rp.CITE_ANY_RE.sub("", line)
    line = re.sub(r"\\'\{(\w)\}", r"\1", line)
    line = re.sub(r"\\[a-zA-Z]+\*?", " ", line)
    return re.sub(r"[{}~]", "", line).replace("---", " — ").replace("--", "–")


failed = 0
for sec in ctx.sections(ctx.args):
    paras = [" ".join(clean(l) for l in pl).strip()
             for _, pl in _rp.paragraphs(_rp.section_body(sec))]
    paras = [p for p in paras if p]
    print("===== %s: %d paragraphs (norm cell: %s)" % (sec.key, len(paras), JOB))
    for i, p in enumerate(paras, 1):
        n = len([s for s in split_sentences(p) if len(s.split()) >= 3])
        if n < 3:
            print("P%d: %d sentences — R9–R11 n/a (<3 sentences)" % (i, n))
            continue
        r = subprocess.run([sys.executable, "-B", "scripts/cohesion.py", "--section", JOB, "--json"],
                           input=p, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=ctx.lit, env=ENV)
        try:
            out = json.loads(r.stdout)
        except ValueError:
            failed += 1
            print("P%d: cohesion.py FAILED (exit %d)" % (i, r.returncode))
            for l in (r.stderr or r.stdout or "(no output)").strip().splitlines()[-8:]:
                print("     | " + l)
            continue
        m, joins = out.get("metrics", {}), out.get("joins", [])
        print("P%d: paragraph: %d sentences · length bin %s · section %s"
              % (i, len(joins) + 1, out.get("length_bin"), JOB))
        print("     joins: " + " ".join(j["grade"] for j in joins))
        for j in joins:
            print("     %s %-8s %-11s overlap %.2f  %s"
                  % ("!" if j["grade"] in ("WEAK", "BROKEN", "BROKEN?") else " ", j["pair"],
                     j["grade"], j["overlap_prop"], " · ".join(j.get("carriers", [])) or "-"))
        for key, label in LABELS:
            pct = m.get(key + "_pct")
            if pct is not None and (pct <= 10 or pct >= 90):
                print("     %-24s %.3f   P%02d  ⚠ %s tail"
                      % (label, m[key], pct, "low" if pct <= 10 else "high"))
        if m.get("m8_pair"):
            print("     M8 pair: %s share {%s}" % (m["m8_pair"], ", ".join(m.get("m8_shared_stems", []))))
if failed:
    sys.exit(2)
