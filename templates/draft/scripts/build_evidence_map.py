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
    py -3 scripts/build_evidence_map.py            # rebuild
    py -3 scripts/build_evidence_map.py --check    # exit 1 if stale, write nothing
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
import _jobs  # noqa: E402
TEX, TABLES = _jobs.manuscript_paths()   # absolute, or project-relative resolved
OUT = os.path.join(SKILL, "references", "evidence-map.md")

CAP_W = 62  # caption truncation width, matching the hand-built original
_INPUT = re.compile(r"\\(?:input|include)\{([^}]+)\}")
_COMMENT = re.compile(r"(?<!\\)%.*$")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def walk(tex):
    """The section tree and figure labels in reading order, following
    \\input / \\include (paths relative to main.tex's folder, as LaTeX reads
    them), and every file read. Lines of main.tex print as N:..., lines of
    an input file as <file>:N:..."""
    base = os.path.dirname(os.path.abspath(tex))
    tree, figs, files = [], [], []

    def scan(p, top):
        p = os.path.normpath(p)
        if p in files or not os.path.isfile(p):
            return
        files.append(p)
        tag = "" if top else os.path.basename(p) + ":"
        for i, l in enumerate(read(p).split("\n"), 1):
            body = _COMMENT.sub("", l)
            if re.match(r"\s*\\(?:sub)?section\{", body):
                tree.append("%s%d:%s" % (tag, i, l.strip()[:88]))
            if re.search(r"\\label\{fig:", body):
                figs.append("%s%d:%s" % (tag, i, l.strip()[:60]))
            for m in _INPUT.finditer(body):
                f = m.group(1).strip()
                scan(os.path.join(base, f if f.endswith(".tex") else f + ".tex"), False)
    scan(tex, True)
    return tree, figs, files


def main():
    if not TEX:
        print('no manuscript onboarded (field-config.yaml manuscript_tex unset) -- nothing to map'); sys.exit(0)
    if not os.path.exists(TEX):
        sys.exit("missing " + TEX)
    tree, figs, files = walk(TEX)
    # the newest of main.tex and its input files: editing a section file makes the map stale
    mtime = datetime.datetime.fromtimestamp(max(os.path.getmtime(f) for f in files))

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

    rows = []
    # no manuscript_tables: no table index (never a glob of the working folder)
    for f in sorted(glob.glob(os.path.join(TABLES, "*.tex"))) if TABLES else []:
        t = read(f)
        lab = re.search(r"\\label\{(tab:[^}]+)\}", t)
        cap = re.search(r"\\caption\{([^}\n]*)", t)
        if lab:
            rows.append((lab.group(1), os.path.basename(f),
                         (cap.group(1) if cap else "")[:CAP_W]))
    rows.sort()

    L = ["# evidence-map.md — main.tex 证据索引(缓存,按 mtime 失效)",
         "",
         "> 生成自 `%s`(及其 %d 个 \\input 文件)与 `%s`,由 `scripts/build_evidence_map.py` 重建。"
         % (os.path.basename(TEX), len(files) - 1,
            os.path.join(os.path.basename(TABLES), "*.tex") if TABLES else "无表格目录"),
         "> mtime: " + mtime.strftime("%Y-%m-%d %H:%M:%S"),
         "> 用途:claim→证据追溯器第 2a 步。**过期会把改名的表读成 ORPHAN**——重跑 `py -3 scripts/build_evidence_map.py` 即可。",
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
