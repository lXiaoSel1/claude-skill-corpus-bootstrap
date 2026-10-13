#!/usr/bin/env python3
"""Regenerate references/evidence-map.md from the live manuscript.

WHY THIS EXISTS
    evidence-map.md is workflow step 2a's cache: the claim->evidence tracer
    resolves \\ref{}/\\input{} against it instead of re-grepping main.tex every
    session.  It was hand-built once (2026-07-07) and then orphaned -- by
    2026-08-26 the manuscript had moved (Results 327->292, Conclusion 418->383,
    five Background subsections collapsed to two) and the cache's own header
    warning ("stale -> renamed tables read as ORPHAN") was live.  The output
    format existed; only this generator was missing.

RUN
    py scripts/build_evidence_map.py            # rebuild
    py scripts/build_evidence_map.py --check    # exit 1 if stale, write nothing
"""
import datetime
import glob
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
# FACTORY PARAMETERIZATION: the manuscript path is a MANUSCRIPT-ONBOARDING
# setting (references/field-config.yaml, manuscript_tex/manuscript_tables).
# Before onboarding this script reports 'no manuscript yet' and exits 0 --
# an instance without a manuscript is normal, not broken.
sys.path.insert(0, os.path.join(SKILL, 'pipeline'))
from _jobs import _load as _cfg_load  # noqa: E402
_cfg = _cfg_load()
TEX = _cfg.get('manuscript_tex', '')
TABLES = _cfg.get('manuscript_tables', '')
OUT = os.path.join(SKILL, "references", "evidence-map.md")

CAP_W = 62  # caption truncation width, matching the hand-built original


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main():
    if not TEX:
        print('no manuscript onboarded (field-config.yaml manuscript_tex unset) -- nothing to map'); sys.exit(0)
    if not os.path.exists(TEX):
        sys.exit("missing " + TEX)
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(TEX))

    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            print("evidence-map.md missing"); sys.exit(1)
        cached = read(OUT)
        m = re.search(r"mtime: (\S+ \S+)", cached)
        stamp = m.group(1) if m else "?"
        fresh = stamp == mtime.strftime("%Y-%m-%d %H:%M:%S")
        print("evidence-map %s (cache %s, main.tex %s)"
              % ("FRESH" if fresh else "STALE", stamp,
                 mtime.strftime("%Y-%m-%d %H:%M:%S")))
        sys.exit(0 if fresh else 1)

    lines = read(TEX).split("\n")
    tree, figs = [], []
    for i, l in enumerate(lines, 1):
        if re.match(r"\s*\\(?:sub)?section\{", l):
            tree.append("%d:%s" % (i, l.strip()[:88]))
        if re.search(r"\\label\{fig:", l):
            figs.append("%d:%s" % (i, l.strip()[:60]))

    rows = []
    for f in sorted(glob.glob(os.path.join(TABLES, "*.tex"))):
        t = read(f)
        lab = re.search(r"\\label\{(tab:[^}]+)\}", t)
        cap = re.search(r"\\caption\{([^}\n]*)", t)
        if lab:
            rows.append((lab.group(1), os.path.basename(f),
                         (cap.group(1) if cap else "")[:CAP_W]))
    rows.sort()

    L = ["# evidence-map.md — main.tex 证据索引(缓存,按 mtime 失效)",
         "",
         "> 生成自 field-config 指定的稿件 `main.tex` 与表格文件,由 `scripts/build_evidence_map.py` 重建。",
         "> mtime: " + mtime.strftime("%Y-%m-%d %H:%M:%S"),
         "> 用途:claim→证据追溯器第 2a 步。**过期会把改名的表读成 ORPHAN**——重跑 `py scripts/build_evidence_map.py` 即可。",
         "", "## 章节树", "", "```"]
    L += tree
    L += ["```", "", "## 表格 label → 源文件 → caption", "",
          "| label | 源文件 | caption |", "|---|---|---|"]
    for lab, f, cap in rows:
        L.append("| `%s` | `%s` | %s |" % (lab, f, cap.replace("|", "\\|")))
    L += ["", "## 图", "", "```"] + figs + ["```", ""]

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    print("wrote %s  (%d sections, %d tables, %d figures, mtime %s)"
          % (os.path.relpath(OUT, SKILL), len(tree), len(rows), len(figs),
             mtime.strftime("%Y-%m-%d %H:%M")))


if __name__ == "__main__":
    main()
