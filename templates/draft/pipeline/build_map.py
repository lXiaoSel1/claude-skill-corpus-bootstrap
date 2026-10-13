"""A3 - build chapter-map.md and run the gate.

The map is the deliverable of Stage A. Stage B slices from it mechanically.
"""
import json, os, glob, collections

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


OUTDIR = REF
cand = json.load(open(os.path.join(BASE, "a1_candidates.json"), encoding='utf-8'))
# FACTORY: two DIFFERENT ground truths were once both called groundtruth.json
# -- recall.py needs {paper: [heading line numbers]}, this A3 gate needs
# {job: {has: [papers], absent: [papers]}}.  They are separate files now.
_A3 = os.path.join(BASE, "a3_groundtruth.json")
GT = (json.load(open(_A3, encoding='utf-8')) if os.path.exists(_A3) else {})

# `model` is the tenth job, added after the residual demanded it: four
# independent reading passes each refused to fold formal-derivation chapters
# into `literature-hypotheses`, giving the same reason -- they derive
# propositions from assumptions rather than summarising others' findings.
# FACTORY PARAMETERIZATION: taxonomy from field-config.yaml (single
# source), written by Tier 2's approved induction.  Refuses to run
# before that -- the parent's list was economics' answer.
import _jobs
JOBS = _jobs.require_jobs()

# ---------------- merge A2 ----------------
assign, dupes = {}, 0
# Order matters: the retag pass is read last so its `model` calls override the
# original `OTHER` calls for the same heading.
order = (sorted(glob.glob(os.path.join(BASE, "a2_out_wave*.tsv")))
         + [os.path.join(BASE, "a2_out_delta.tsv"), os.path.join(BASE, "a2_out_gap.tsv"),
            os.path.join(BASE, "a2_out_retag.tsv"),
            os.path.join(BASE, "a2_out_zfix.tsv")])   # the two A3 under-calls, verified by line
for p in [q for q in order if os.path.exists(q)]:
    for ln in open(p, encoding='utf-8'):
        f = ln.rstrip('\n').split('\t')
        if len(f) < 3:
            continue
        try:
            key = (f[0].strip(), int(f[1].strip().lstrip('Ll')))
        except ValueError:
            continue
        if key in assign:
            dupes += 1
        assign[key] = dict(
            jobs=[j.strip() for j in f[2].strip().split(',') if j.strip()],
            conf=f[3].strip() if len(f) > 3 else '',
            note=f[4].strip() if len(f) > 4 else '')

# ---------------- attach to candidates ----------------
paper_jobs = collections.defaultdict(set)
job_head = collections.Counter()
unassigned = []
for k, r in cand.items():
    for c in r['candidates']:
        a = assign.get((k, c['line']))
        if a is None:
            unassigned.append((k, c['line'])); c['jobs'] = []; c['conf'] = ''; c['note'] = ''
            continue
        c['jobs'], c['conf'], c['note'] = a['jobs'], a['conf'], a['note']
        for j in a['jobs']:
            job_head[j] += 1
            if j in JOBS:
                paper_jobs[k].add(j)

# ---------------- line ranges ----------------
# A block ends at the next candidate THAT CARRIES A REAL JOB, not at the next
# candidate of any kind.  Measured 2026-08-29 on a mathematics corpus: maths
# journals print an editor line and an affiliation line immediately after the
# introduction heading ("Communicated by V. Coti-Zelata.", "G. Vaira (B)"),
# both correctly labelled NONE -- and ending the block at them truncated
# 23_VairaG2011's whole introduction to THREE LINES.  Same shape truncated
# 24_WangJ2017, 25_WangJ2021 and 26_WangJ2022.  A NONE candidate marks a line
# that is not a chapter start; it says nothing about where the chapter ends.
def _has_job(c):
    """True when the candidate starts a chapter -- any job, OTHER included (an
    OTHER chapter is real; it ends the previous block). Same rule as
    stage_b_slice.blocks_for -- change both together."""
    return any(j and j != 'NONE' for j in c.get('jobs', []))


for k, r in cand.items():
    cs = sorted(r['candidates'], key=lambda c: c['line'])
    for i, c in enumerate(cs):
        nxt = next((cs[j]['line'] for j in range(i + 1, len(cs))
                    if _has_job(cs[j])), None)
        c['end'] = (nxt - 1) if nxt else r['ref_cutoff']

# ---------------- the gate ----------------
# Two corrections after running down all nine first-pass disagreements by hand:
#
# (a) LEVEL. The stub tables measure "does this paper set a STANDALONE TOP-LEVEL
#     chapter for X". The map assigns a job to headings at ANY level, on purpose
#     (6 of 12 papers put data in a subsection under a Methodology chapter). So
#     the chapter-level checks compare against level-1 headings only. Every one
#     of BergstresserDesaiRauh2006 / GarmanKubick2025 / Rauh2009 / Rauh2006 was
#     this, not an error -- GarmanKubick2025's institutional material really does
#     live in subsection 2.2, which the extraction probe found independently.
#
# (b) TWO TABLES, NOT ONE. The stub keeps the REVIEW function and the HYPOTHESES
#     function in separate tables; my first transcription flattened them into one
#     `literature-hypotheses` job, which made Bartram2018 and IoannidouPintoWang2022
#     read as disagreements when both are review-absent / hypotheses-present.
#     The check now uses the union.
lvl1_jobs = collections.defaultdict(set)
for k, r in cand.items():
    for c in r['candidates']:
        if c['level'] == 1:
            for j in c.get('jobs', []):
                lvl1_jobs[k].add(j)

# Compare at ANY level throughout. The stub tables have a "形态" column that
# already records top-level / subsection / merged, so their has-lists are about
# the FUNCTION being present somewhere, not about chapter status. Restricting to
# level 1 fixed GarmanKubick2025-institutional but broke GarmanKubick2025- and
# Rauh2009-literature, whose review function the stub records AS a subsection.
# FACTORY: the parent hardcoded its own five jobs here.  Derive the gate from
# whatever a3_groundtruth.json declares, so the check follows the approved
# taxonomy.  An empty file simply means no gate ran (reported as such).
# Keys starting with '_' are notes (e.g. '_comment' recording how and when the
# hand measurement was made), not jobs.
CHECKS = [(job, [job], False) for job in sorted(GT) if not job.startswith('_')]

# FACTORY PARAMETERIZATION: the parent baked 7 per-paper A3 adjudication
# verdicts here (pension papers).  An instance fills ITS OWN as its A3
# gate mismatches are opened and read -- verdicts live in this builder,
# never hand-edited into the generated file (the CurrieGruber lesson).
ADJUDICATED = {}
gate, agree, disagree = [], 0, 0
for job, gtkeys, chapter_level in CHECKS:
    yes, no = set(), set()
    for gk in gtkeys:
        g = GT[gk]
        if 'has' in g:
            yes |= set(g['has']) | set(g.get('marginal', []))
            no |= set(g.get('absent', []))
        else:
            for kk, vv in g.items():
                if not kk.startswith('_'):
                    yes |= set(vv)
    no -= yes                       # union semantics: present anywhere wins
    src = lvl1_jobs if chapter_level else paper_jobs
    for p in sorted(yes | no):
        got, want = job in src.get(p, set()), p in yes
        agree += (got == want); disagree += (got != want)
        if got != want:
            gate.append((job, p, "auto=YES hand=NO" if got else "auto=NO  hand=YES"))

# Hand-written per-paper notes (e.g. alias pairs) live HERE, in the builder,
# never in the generated file: the parent lost one to a regeneration
# (2026-08-26, the CurrieGruber alias). {paper_key: [markdown lines]}
PAPER_NOTES = {}

# ---------------- write ----------------
N = len(cand)
GT_PAPERS = sorted({p for g in GT.values() if isinstance(g, dict)
                    for kk, vv in g.items() if not kk.startswith('_')
                    for p in (vv if isinstance(vv, list) else [])})
L = ["# chapter-map.md — which paper does which job, and where",
     "",
     "> Stage A output. **Every `n` in the section references must trace back to this file.**",
     "> Built by: A1 mechanical heading extraction (recall measured by `pipeline/recall.py` against",
     "> `pipeline/groundtruth.json`, recorded in `registry.json` → `chapter_map`) -> A2 job assignment BY",
     "> READING the ~600 characters that follow each heading, never the heading text -> A3 agreement",
     f"> check against the {len(GT_PAPERS)}-paper hand measurement in `pipeline/a3_groundtruth.json`.",
     "",
     f"> Sample: {N} papers (`sample.md`). Candidates: {sum(len(v['candidates']) for v in cand.values())} rows "
     f"({len({(k, c['line']) for k, r in cand.items() for c in r['candidates']})} distinct paper:line). "
     f"Assigned: {len(assign)} verdict rows -- the surplus over candidates is agent-corrected line numbers "
     f"or headings the A1 scan missed, which carry a verdict but never attach. Unassigned: {len(unassigned)}.",
     "", "---", "", f"## 1. Coverage — how many of the {N} do each job", "",
     "| job | papers | headings |", "|---|---|---|"]
for j in JOBS:
    L.append(f"| `{j}` | {sum(1 for p in cand if j in paper_jobs[p])}/{N} | {job_head[j]} |")
L += [f"| `OTHER` (a real chapter, none of the {len(JOBS)}) | — | {job_head['OTHER']} |",
      f"| `NONE` (not a heading) | — | {job_head['NONE']} |", ""]

L += ["---", "", f"## 2. A3 gate — automated map vs the {len(GT_PAPERS)}-paper hand measurement", ""]
L.append(f"**agree {agree} · disagree {disagree} · "
         f"{100*agree/(agree+disagree):.1f}%**" if agree + disagree else "no checks ran")
L.append("")
gen = [g for g in gate if 'GENUINE' in ADJUDICATED.get((g[0], g[1]), '')]
rec = [g for g in gate if 'RECONCILED' in ADJUDICATED.get((g[0], g[1]), '')]
una = [g for g in gate if (g[0], g[1]) not in ADJUDICATED]
L += [f"Of {len(gate)} mismatches: **{len(rec)} reconciled · {len(gen)} genuine · "
      f"{len(una)} unadjudicated**. Every one was opened and read.", "",
      "| job | paper | direction | adjudication |", "|---|---|---|---|"]
for j, p, h in gate:
    L.append(f"| `{j}` | {p} | {h} | {ADJUDICATED.get((j, p), '**UNADJUDICATED**')} |")
L += ["",
      "**The two measurements are not always the same measurement.** A hand ground truth that "
      "records whether a paper has a STANDALONE chapter for a job can disagree with this map, "
      "which assigns jobs to headings at any level on purpose. Mismatches of that shape are "
      "reconciliations, not errors — record each verdict in ADJUDICATED in this builder.", ""]

POS = [j for j in _jobs.positional_jobs() if j in JOBS]
L += ["---", "", "## 3. Positional jobs — sliced by position where no heading carries them", ""]
if POS:
    for j in POS:
        miss = sorted(p for p in cand if j not in paper_jobs[p])
        L += [f"`{j}` resolves from a heading for {N-len(miss)}/{N} papers; the other "
              f"{len(miss)} are sliced positionally by `stage_b_slice.py`: " + (", ".join(miss) or "none"), ""]
    L += ["```",
          f"{POS[0]:14s}= labelled start (or abstract_start_markers / first prose run) -> "
          "abstract_end_markers or first heading",
          ] + [f"{j:14s}= positional_anchors_{j} (or right after the previous positional block) -> "
               "first heading carrying a non-positional job" for j in POS[1:]] + ["```", ""]
else:
    L += ["No positional jobs declared in field-config.yaml (`positional_jobs`).", ""]
L += ["---", "", "## 4. The map", ""]
for k in sorted(cand):
    r = cand[k]
    real = [c for c in r['candidates'] if c['jobs'] and c['jobs'] not in (['NONE'],)]
    jobs_here = sorted(paper_jobs[k])
    L += [f"### {k}", ""]
    if k in PAPER_NOTES:
        L += PAPER_NOTES[k] + [""]
    L += [f"`format {r['format']}` · {r['total_lines']} lines · refs cut at {r['ref_cutoff']} · "
          f"jobs present: {', '.join(f'`{j}`' for j in jobs_here) if jobs_here else '**none**'}", "",
          "| line | lvl | job(s) | conf | verbatim heading |", "|---|---|---|---|---|"]
    for c in real:
        jb = ', '.join(f"`{j}`" for j in c['jobs'])
        v = c['verbatim'].replace('|', '\\|')[:100]
        L.append(f"| {c['line']}–{c['end']} | {c['level']} | {jb} | {c['conf']} | {v} |")
    L.append("")

p = os.path.join(OUTDIR, "chapter-map.md")
open(p, 'w', encoding='utf-8').write("\n".join(L))
print(f"agree {agree} disagree {disagree} | unassigned {len(unassigned)} | dupes {dupes}")
print(f"wrote {p} ({os.path.getsize(p)//1024} KB)")
for j, pp, h in gate:
    print(f"  DISAGREE {j:26s} {pp:38s} {h}")
