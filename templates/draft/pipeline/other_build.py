"""Pull every OTHER-tagged heading with its following prose, so one agent can
split them into the new `model` job vs a genuine residual."""
import json, os, re, glob

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
# LAYOUT: the parent kept pipeline/ INSIDE references/, so "BASE/.." was
# references/.  A stamped instance puts pipeline/ at the skill root, so
# references/ is BASE/../references.  Caught 2026-08-28 when a2_build
# looked for <skill>/sample.md instead of <skill>/references/sample.md.
REF = os.path.normpath(os.path.join(BASE, "..", "references"))            # references/
SKILLS = os.path.normpath(os.path.join(REF, "..", ".."))    # .claude/skills/
import _jobs
CORPUS = _jobs.corpus_dir()

FOLLOW = 500
cand = json.load(open(os.path.join(BASE, "a1_candidates.json"), encoding='utf-8'))
assign = {}
# CAVEAT: this is the ONLY script using the broad a2_out_*.tsv glob;
# build_map/build_names/stage_b_slice use a2_out_wave* plus an explicit
# four-name list.  A newly added a2_out_x.tsv is picked up HERE and
# silently ignored by the other three -- keep the lists in sync by hand.
for p in sorted(glob.glob(os.path.join(BASE, "a2_out_*.tsv"))):
    for ln in open(p, encoding='utf-8'):
        f = ln.rstrip('\n').split('\t')
        if len(f) >= 3:
            try:
                assign[(f[0].strip(), int(f[1].strip().lstrip('Ll')))] = (
                    f[2].strip(), f[4].strip() if len(f) > 4 else '')
            except ValueError:
                pass

def body(lines, c):
    i = c['line'] - 1
    buf = ""
    if any(f.startswith('glued') for f in c.get('flags', [])):
        pos = lines[i].find(c['title'])
        if pos >= 0:
            buf = lines[i][pos + len(c['title']):]
    j = i + 1
    while len(buf) < FOLLOW and j < len(lines) and j < i + 30:
        buf += " " + lines[j]; j += 1
    return re.sub(r'\s+', ' ', buf).strip()[:FOLLOW]

out, n = ["# OTHER re-tag: split into `model` vs genuine residual\n"], 0
for k in sorted(cand):
    hits = [c for c in cand[k]['candidates']
            if 'OTHER' in assign.get((k, c['line']), ('', ''))[0].split(',')]
    if not hits:
        continue
    with open(os.path.join(CORPUS, k + '.txt'), 'rb') as fh:
        lines = fh.read().decode('utf-8', 'replace').split('\n')
    out.append(f"\n## {k}\n")
    for c in hits:
        n += 1
        out.append(f"\n### L{c['line']} | lvl{c['level']}")
        out.append(f"HEADING: {c['verbatim']}")
        out.append(f"PRIOR NOTE: {assign[(k, c['line'])][1]}")
        out.append(f"FOLLOWS: {body(lines, c)}")
p = os.path.join(BASE, "other_retag.md")
with open(p, 'w', encoding='utf-8') as _fh:
    _fh.write("\n".join(out))
print(f"{n} OTHER entries, {os.path.getsize(p)//1024} KB -> {p}")
