# a2-wave.md — Tier 2 step ③: chapter-identification wave agents

> Reconstructed from the parent build's artifacts (the prompt itself was never
> saved — this file fixes that). Input format = `a2_build.py` output; output
> format = the five-column TSV that `build_map.py` merges. Parent scale:
> 4 waves × 15 papers (~420–530 headings per wave) + delta/gap/retag/zfix
> correction rounds = 8 passes for 60 papers.

## Agent prompt (fill {braces})

You are assigning chapter JOBS to candidate headings for wave {k} of {field}'s
corpus mapping. Input file: `a2_wave{k}.md` — for each paper, every candidate
heading with its level, pattern flags, verbatim text, and `FOLLOWS:` (the
~600 characters of prose after it).

The approved job taxonomy for this field (the `jobs:` items of field-config.yaml;
each item's comment is its definition):

{jobs table: job | functional definition}

Rules:

1. **Judge from FOLLOWS, never from the heading text.** A heading called
   "Background" earns its job from what the prose under it does.
2. One or more jobs per heading (comma-separated) when a chapter genuinely
   serves two; `OTHER` for a real chapter fitting no job; `NONE` for
   non-headings (captions, footnote debris, running heads).
3. Confidence column: `H` when FOLLOWS is decisive, `M` when you inferred
   from position/structure. Never guess silently — `M` is the flag.
4. Emit STRICT TSV, one row per candidate, no header, exactly:
   `paper-key<TAB>L<line><TAB>job[,job]<TAB>H|M<TAB>one-line reason`
   Write it to `pipeline/a2_out_wave{k}.tsv` in the {field}-draft skill: build_map,
   build_names and stage_b_slice read only files with these exact names, and a
   file named otherwise is silently left out of the map.
5. Every candidate in the input gets a row. No skips, no additions.
6. **Structured-abstract labels are not chapters.** A line that is only
   `BACKGROUND`, `METHODS`, `RESULTS`, `CONCLUSIONS`, `Objective(s)`,
   `Importance` etc. near the top of a paper, whose FOLLOWS is one or two
   sentences of summary, belongs to the abstract: mark it `NONE` (or the
   abstract job if the taxonomy marks the abstract as heading-sliced). Tagging
   it `results`/`methods` cuts the abstract after its first label and
   invents a one-paragraph chapter.
7. Candidates flagged `sentence-case` or `run-in` are machine rescues of
   unusual heading forms -- judge them from FOLLOWS like any other; `NONE` is a
   normal answer for a rescued prose fragment.

## Correction rounds (after build_map's first merge)

- `retag`: all OTHER-tagged headings re-examined in one pass (did a new job
  hide inside OTHER? — this is how the parents found `model`).
- `gap` / `delta`: headings the first pass missed or mis-lined.
- `zfix`: single verdicts the A3 gate (below) shows to be wrong, checked by line.
- Each round writes the same TSV format to `pipeline/a2_out_retag.tsv`,
  `a2_out_gap.tsv`, `a2_out_delta.tsv` or `a2_out_zfix.tsv` (exact names).
- Merge order matters and is enforced by build_map: waves first, corrections
  last, so later verdicts override earlier ones.

## Gate (A3)

Before slicing, an agreement check against a small hand-labeled set (the
parents used 18 papers, gate 94.4%): sample ~15% of papers, hand-assign their
chapters, compare. Every disagreement is opened and read; adjudications are
written into the BUILDER (build_map's ADJUDICATED dict), never into the
generated file.
