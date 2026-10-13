# taxonomy-induction.md — Tier 2 step ①: induce the field's chapter jobs (then STOP for user approval)

> The parents' ten jobs (abstract … conclusion, model) were INDUCED during
> reading, not pre-declared — four independent passes each refused to fold
> formal-derivation chapters into literature-hypotheses, which is how `model`
> was born. A new field gets the same treatment: the taxonomy comes from its
> own papers, never from economics'. **The user approves the job list before
> anything downstream runs** — a wrong taxonomy poisons the map, the slices,
> the records and the Versions.

## Agent prompt (fill {braces})

You are inducing the chapter taxonomy of a research field from its papers'
own structure. Input: `pipeline/a1_windows.md` (built by
`py -3 pipeline/build_windows.py` from `a1_candidates.json`): every heading
candidate plus the first ~600 characters after it, for {N} papers in {field}.
Candidates are machine-extracted and include non-headings (running headers,
table fragments, structured-abstract labels such as "RESULTS" on their own
line) — those are `NONE`, and structured-abstract labels belong to the
abstract, never to a results/methods job.

Rules — the same discipline the parent build used:

1. **Name jobs by FUNCTION, never by heading text.** Headings are unstable
   ("Background" serves institutional description and literature review in
   equal measure in economics; your field will have its own traps). A job is
   what the prose under the heading DOES.
2. Read the ~600-character prose windows, not the heading strings, before
   assigning any function.
3. Propose the SMALLEST set of jobs that covers ≥90% of heading blocks;
   everything else is `OTHER` (a real chapter that fits no job) or `NONE`
   (not a chapter heading at all). The parents needed 10 for economics;
   IMRaD fields may need 6; CS may need related-work / system-design /
   evaluation splits. Do not aim for the parents' count.
4. For each proposed job: a one-line functional definition, 3 verbatim example
   headings with paper keys, and a rough share of papers carrying it.
5. **Flag positional jobs**: any job usually present WITHOUT a heading
   (abstract in most fields; introduction in some) must be marked
   `positional` with the anchor evidence (what text marks its start/end —
   e.g. structured-abstract labels, keyword lines, "1 Introduction").
6. If a job seems field-defining but rare (<15% of papers), propose it
   anyway and say so — the parents' `model` job covered 14/60 and refusing
   to merge it was correct.
7. Output: a table `job | definition | example headings (3, verbatim, keyed)
   | approx share | positional?` plus a list of headings you could not
   assign. No prose conclusions beyond that.

## After the agent returns

The factory presents the table to the user. On approval, the job list, the
positional anchors and their definitions are written into
`field-config.yaml` (`jobs:` block) — the single source the pipeline scripts
read. Nothing in Tier 2 steps ②–④ runs before that write.
