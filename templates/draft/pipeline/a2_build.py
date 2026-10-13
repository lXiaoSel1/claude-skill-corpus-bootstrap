"""Build A2 input: every A1 candidate + the prose that FOLLOWS it.
A2 assigns jobs by reading that prose. Titles are advisory only."""
import json, os, re

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


SAMPLE = os.path.join(REF, "sample.md")
FOLLOW = 600          # chars of following prose per candidate

d = json.load(open(os.path.join(BASE, "a1_candidates.json"), encoding='utf-8'))

# wave assignment straight from sample.md (word-count balanced; written by
# pipeline/make_sample.py). FACTORY FIX 2026-10-07: the pattern accepted only
# waves 1-4, so papers placed in wave 5+ silently received no A2 input.
wave = {}
for ln in open(SAMPLE, encoding='utf-8'):
    m = re.match(r'^\|\s*(\d{1,2})\s*\|\s*`([^`]+)`', ln)
    if m:
        wave[m.group(2)] = int(m.group(1))
unwaved = sorted(k for k in d if k not in wave)
if unwaved:
    sys.exit("papers in a1_candidates.json with no wave in sample.md: %s"
             "\n  fix: py -3 pipeline/make_sample.py" % ", ".join(unwaved[:10]))

def body_after(lines, cand):
    """Text following the heading. For glued headings the body continues on the
    SAME line right after the title; for bare headings it starts on the next."""
    i = cand['line'] - 1
    buf = ""
    if any(f.startswith('glued') for f in cand.get('flags', [])):
        same = lines[i]
        pos = same.find(cand['title'])
        if pos >= 0:
            buf = same[pos + len(cand['title']):]
    j = i + 1
    while len(buf) < FOLLOW and j < len(lines) and j < i + 40:
        buf += " " + lines[j]
        j += 1
    return re.sub(r'\s+', ' ', buf).strip()[:FOLLOW]

for w in sorted(set(wave.values())):
    keys = [k for k in d if wave.get(k) == w]
    out = [f"# A2 input - wave {w} ({len(keys)} papers)\n"]
    n = 0
    for k in keys:
        r = d[k]
        out.append(f"\n## {k}   [format {r['format']} | {r['total_lines']} lines | "
                   f"refs cut at {r['ref_cutoff']}]\n")
        # One read per PAPER.  Until 2026-08-26 the open+decode sat inside the
        # per-candidate loop below: 20-40x redundant I/O per paper, plus a
        # leaked handle per candidate.
        with open(os.path.join(CORPUS, k + '.txt'), 'rb') as fh:
            body_lines = fh.read().decode('utf-8', 'replace').split(chr(10))
        for c in r['candidates']:
            n += 1
            fl = ('  flags=' + ','.join(c['flags'])) if c.get('flags') else ''
            out.append(f"\n### L{c['line']} | lvl{c['level']} | {c['pattern']}{fl}")
            out.append(f"HEADING: {c['verbatim']}")
            out.append(f"FOLLOWS: {body_after(body_lines, c)}")
    p = os.path.join(BASE, f"a2_wave{w}.md")
    open(p, 'w', encoding='utf-8').write("\n".join(out))
    print(f"wave {w}: {len(keys):2d} papers, {n:4d} candidates, {os.path.getsize(p)//1024:4d} KB -> {p}")
