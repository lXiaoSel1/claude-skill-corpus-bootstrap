# PARAMETERIZATION.md — what was changed from the parent, and what to watch

> The scripts in this template started as frozen copies of draft-section's
> (2026-08-26 state, post its 65/65 drift-clean build), patched where the
> portability audit flagged them, then upgraded on 2026-10-07 after a
> two-reviewer audit of the factory and of its first instance (a mathematics field).
> This file is the honest ledger of those patches and their known limits.

## The single config source

`references/field-config.yaml`, parsed by `pipeline/_cfgparse.py` (an
identical copy lives in the lit instance; check_drift asserts the two agree)
and exposed through `pipeline/_jobs.py` (taxonomy, positional jobs and
anchors, corpus location, headwords, citation style, manuscript paths, canon
directory) and `scripts/_fieldstyle.py` (citation regexes). The parent's three
duplicated JOBS lists, the ../mimic-lit corpus hop and the hardcoded
manuscript paths all collapse into it.

**2026-10-07:** the 2026-08 line parser kept YAML quotes and inline comments
inside values. The mathematics instance's four quoted `abstract_end_markers`
therefore never matched any line — the true cause of its 17/38 abstract over-runs.

## Patch inventory

| file | patch | limit to watch |
|---|---|---|
| `pipeline/_cfgparse.py` | NEW 2026-10-07: quotes, comments, flow lists, utf-8-sig | only the subset stamp.py emits; unknown lines are reported, not guessed |
| `pipeline/make_sample.py` | NEW 2026-10-07: sample-keys.txt + sample.md from the lit corpus's style_safe list, word-balanced waves | `--include/--exclude` for deliberate deviations; record why |
| `pipeline/build_windows.py` | back-ported from the mathematics instance; sample size computed | — |
| `pipeline/build_map.py` | JOBS from config; ADJUDICATED and PAPER_NOTES dicts for this instance's verdicts and notes; all counts computed | fill ADJUDICATED as the A3 gate reads happen — never hand-edit chapter-map.md |
| `pipeline/build_names.py` | JOBS from config | its prose is regenerated per instance |
| `pipeline/stage_b_slice.py` | positional jobs generic (front block + anchored later jobs); start/end markers from config; prose-run fallback for line-per-line text; compute-all-then-backup-then-write; retired job folders cleared; `--dry-run` | the block-end rule is duplicated in build_map.py — change both together |
| `pipeline/a1_headings.py` | HEADWORDS from config; back-ports from the mathematics instance (run-in headings, plural bound numbers, appendix exemption); generic IMRaD vocabulary for single-word and sentence-case headings | run `recall.py` against a hand ground truth before trusting it |
| `pipeline/a2_build.py` | any number of waves (was 1-4 only); refuses papers with no wave | — |
| `pipeline/recall.py` | reads `groundtruth.json` only | hand-build it at the Tier 2 gate |
| `pipeline/recount.py` | scans all records/*.md for the PASS1 `N sentences` format | parent's two legacy formats not supported |
| `pipeline/para_numbers.py` | 2026-10-07: references/ path fixed (it pointed at the skill root and found nothing); one records/<chapter>.md per chapter; digit-initial and hyphenated keys; single-file chapters | — |
| `scripts/measure_structure.py` | 1.6.0: layer F (paragraph shape per chapter, style-safe papers only); DENOMS from registry; intro_job documented; citation counting for author-year, numeric, superscript and mixed (a stray BACKSPACE character had disabled the author-year regex); year-in-parentheses no longer an equation label; `equation_layer: off` for prose fields | layer A exists only with a tagged round |
| `scripts/draftcheck.py` | ownership regex by citation_style (1.6.0: discourse markers in any case); manuscript tables from config; LaTeX and pandoc citations; `section` skipped when `equation_layer: off`; 1.6.0: `src`, `router`, `version-card [--full]`, `para --chapter` P90, a paragraph passed as text | numeric-citation ownership is judgment-first |
| `scripts/check_drift.py` | canon path from config; T-series and hyphenated keys; single-file chapters; slice fingerprint; retired job folders; PARENT-BLOCK markers in SKILL.md and references/*.md fail at their tier; PARENT-BLOCK and PARENT-EXAMPLE markers must pair | — |
| `scripts/build_evidence_map.py` | manuscript paths from config; exits 0 with a message before onboarding | LaTeX-shaped: a Markdown manuscript needs its parser written at onboarding |
| `scripts/state.py` | parameterized via DRAFT_STATE_PATH; 1.6.0: `cache --from` (many rows, one write) | — |
| `scripts/_src.py` | NEW 1.6.0, ported from the parent's fast lane: corpus from `lit_instance`, a key's corpus key / PDF / note from the onboarding index then notes-index.md; MAP-21-style names kept in words, dropped only where numbers are read | a key with no corpus text and no indexed PDF has NO TEXT |
| `scripts/cards.py` · `_tiers.py` · `_ngram.py` | NEW 1.6.0, ported: design words generic + `design_terms`; `_ngram` reads the lit instance's style-safe set through attest.py | card R/D patterns are English empirical prose |
| `scripts/para_check.py` | NEW 1.6.0, ported; `.bbl` from `manuscript_tex`; `--band` / `--cites` must-pass; layer-F percentiles | the STOP list and TERM_TIE are the parent's calibration |
| `scripts/short_paras.py` | NEW 1.6.0: a chapter's short corpus paragraphs; `--check` verifies a short-paragraph bank verbatim | ¶n counts textseg paragraphs, not PASS1 records |

## Still parent-calibrated (documented, re-measure in the instance)

- `draftcheck.py` TRACEABLE / LADDER word lists: generic empirical English.
- `a2_build.py` FOLLOW=600 chars, `stage_b_slice.py` OPEN_LINES=25 and
  ABS_MAX_CHARS=3500: layout constants from the parent corpus.
- SKILL.md.tmpl blocks marked `PARENT-BLOCK tier=N`: the parent's chapters,
  denominators, paragraph statistics and verb ladder. check_drift fails at
  tier N while any remains.
