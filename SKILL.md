---
name: corpus-bootstrap
description: Bootstrap a new research field's writing infrastructure from the user's own downloaded papers. Stamps two skill instances — <field>-lit (style/terminology reviewer against the field's corpus) and <field>-draft (paragraph drafting with evidence ledgers) — structurally identical to the proven mimic-lit/draft-section pair, then builds their reference layers in five acceptance-gated tiers (corpus → style measurements → chapter taxonomy+map → records+Versions → exemplars). Use when user says "我要研究一个新领域", "把文献建成语料库", "bootstrap a corpus for X", "给这个领域盖一套 lit/draft skill", "新领域的文献库". Manual-first: the USER downloads the PDFs (no fetching, no APIs); this skill converts, measures, and orchestrates the model reading passes.
author: Claude Code Academic Workflow
version: 1.1.0
argument-hint: "[stamp <field> | ingest | tier <n> | status <field>]"
disable-model-invocation: false
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Write", "Edit", "Task"]
---

# `/corpus-bootstrap` — 给任意领域盖一套 lit + draft 基础设施

You replay, on a new field's corpus, the exact recipe that built the
economics/finance pair (`mimic-lit` + `draft-section`). The recipe is
measured, not invented — `references/provenance.md` records how the parents
were actually built (which artifacts are script-replayable, which needed
model reading passes, and how many). **The acceptance law: a finished
instance is structurally identical to its parent** — same file inventory,
same slots, same registry+check_drift discipline — with every number
re-measured on the NEW field's corpus, never inherited from economics.

## Rules

1. **Manual-first corpus.** The user downloads the PDFs (institutional access
   included) — into `<field>-lit/drop/`, or ingest reads them in place from
   the user's library (`--src`/`--map`). No fetching, no APIs, no paywall
   circumvention — the automation survey is archived in
   `references/fetch-research.md` and deliberately NOT implemented.
   Instances are **English-only** (splitter, word lists, corpus).
2. **The corpus is the only authority, from day one.** Parent numbers travel
   as illustrations only; instance files say so in their stamped preambles,
   and TO-MEASURE tags mark every parent verdict awaiting re-measurement.
3. **Taxonomy is induced, never assumed.** The parents' nine chapters are
   economics' answer. Tier 2 step ① induces THIS field's jobs from its own
   papers and **stops for user approval** before anything downstream runs.
4. **One tier at a time, acceptance-gated.** Each tier ends with its checklist
   plus the instance's `check_drift` (tier-aware) — then STOP and wait. Print
   the next tier's agent-pass forecast before starting it.
5. **Parents are read-only.** This skill never modifies `mimic-lit` or
   `draft-section`; templates are frozen copies, parameterized.

## The five tiers

All commands use `py -3` (on Windows `python` may be the Store stub). Paths
in `<lit>`/`<draft>` are the stamped instances.

| Tier | command | builds | cost | acceptance |
|---|---|---|---|---|
| **0 corpus** | `py -3 scripts/stamp.py <field> [--citation-style author-year\|numeric\|mixed] [--keywords "..."] [--dest <skills-dir>]` → `py -3 scripts/ingest.py <lit> [--src <pdf-folder> --recursive \| --map keys.csv]` (PDFs may stay in the user's library; `drop/` is the default source) → `py -3 <lit>/scripts/build_corpus_meta.py` | corpus/*.txt · `corpus_sources.json` (source, converter + version, sha256, SCAN/SHORT flags) · four-denominator manifest with per-paper role, group and citation culture | scripts, minutes | manifest reviewed: SCAN/SHORT/excluded/terminology_only decided in BOTH field-config copies; lit check_drift tier-0 green → append 0 to both registries' built_tiers |
| **1 style layer** | calibrate `para_min_chars` in field-config → `py -3 scripts/capture.py <lit> measure_register.py register-measurements.md` · `py -3 scripts/capture.py <lit> build_cohesion_norms.py cohesion-measurements.md` · `py -3 <lit>/scripts/build_transitions.py`; fill registry numbers (each builder prints them); replace every `corpus: TO-MEASURE` in cohesion-canon.md and the parent counts in register.md | register measurements · cohesion norms (coarse) · transitions bank | scripts, zero agents | lit check_drift tier-1 green; **live-scan one paragraph of the new field's prose with `/<field>-lit`** — TERMS and REGISTER slots print; user reads the scan |
| **2 chapter map** | `py -3 <draft>/pipeline/make_sample.py` → `a1_headings.py` → hand-build `groundtruth.json` (~10 papers) → `recall.py` gate → `build_windows.py` → taxonomy induction (prompts/taxonomy-induction.md, reads a1_windows.md) → **USER APPROVES; jobs, positional_jobs, start/end markers land in BOTH field-config copies** → `a2_build.py` → A2 waves (prompts/a2-wave.md) → hand `a3_groundtruth.json` → `build_map.py` (adjudications into its ADJUDICATED dict) → `stage_b_slice.py --dry-run`, then real → `build_names.py` | approved taxonomy · chapter-map · chapter-names · slices + manifest + fingerprint | 1 induction pass + ~4-8 wave/correction passes + A3 gate reads | A3 agreement ≥90% recorded in registry; user reads the taxonomy table and 3 slices; draft check_drift tier-2 green (incl. no tier-2 PARENT-BLOCK left in SKILL.md) |
| **3 records + Versions** | PASS1 shards (prompts/pass1-reading-SPEC.md, ~8-16 papers/agent/chapter) → `verify_shards.py` → PASS2 per chapter (prompts/pass2-induction-SPEC.md) → `para_numbers.py <chapter>` audit, then `--write` → `recount.py` (uniformity calibration → registry+SKILL.md) → `measure_structure.py` + typing appendices → rewrite the tier-3 PARENT-BLOCKs of SKILL.md | records/ · sections/ (skeletons+parts, four-field Versions ≥2-attested) · uniformity gate numbers | ~27×(n/60) PASS1 + 1 PASS2/chapter — **run chapter by chapter, accept each** | draft check_drift tier-3 green (Version counts, four fields, ≥2 attestation — mechanical); user reads one full chapter; `/<field>-draft` drafts its first paragraph |
| **4 exemplars** | tagging shards (prompts/exemplar-tagging.md, ~10 papers/agent) → `py -3 <lit>/scripts/build_exemplars.py` → registry counts + move_tags → `py -3 <draft>/scripts/measure_verbs.py` → verb-ladder.md + registry `verb_ladder_counts` → structure-canon.md with registry `canon_sources` → rewrite the tier-4 PARENT-BLOCK | exemplars bank (8 move labels) · verb-ladder · structure canon | ~1 pass per 10 papers | both instances' check_drift FULL green = the parent-parity end state |

**Resume**: `py -3 scripts/tier_status.py <field> [--dest <skills-dir>]`
reports built tiers and the next tier's cost scaled by the style-safe sample.
Registries' `built_tiers` is the ledger; tiers are idempotent to re-enter.
`stage_b_slice.py` computes every slice and checks every corpus file BEFORE
it moves the old slices to `references/_slice_backups/<stamp>/` — still run
`--dry-run` first.

**Manuscript onboarding (outside the tiers).** When the field gets a
manuscript: set `manuscript_tex`/`manuscript_tables` in both instances'
field-config.yaml, run `build_evidence_map.py`, initialize
`manuscript-state.md` via `state.py`, fill the register §3/§5 and
"For this manuscript" slots. Until then those slots stay explicitly empty —
an instance without a manuscript is normal, not broken.

## What the model passes look like (dispatch discipline)

- Every pass reads its prompt file from `<draft-instance>/prompts/` — the
  RULES of PASS1 and PASS2 are the parents' specs verbatim (they were the
  actual build documents); their FACTORY NOTE headers carry the substitutions
  a stamped instance needs (format examples in `prompts/examples/`, no parent
  manuscript, digit-initial keys). taxonomy-induction / a2-wave /
  exemplar-tagging were reconstructed from the build's artifacts.
- Shard outputs are kept (`records/_shards/`) — provenance, and one shard's
  failure never hides another's (concatenate only verified shards).
- Adjudications (A3 gate mismatches) are written into the BUILDER scripts,
  never hand-edited into generated files — the parent lost a hand-written
  block to a regeneration once; the lesson is baked in.

## What this is NOT

- **Not a paper fetcher.** No APIs, no scraping, no Sci-Hub-class tools
  (explicitly excluded — see fetch-research.md). You download; it builds.
- **Not a refactor of the parents.** mimic-lit and draft-section stay
  untouched; this factory carries frozen parameterized copies.
- **Not a one-command pipeline.** Tier gates exist because a wrong taxonomy
  poisons everything downstream and 40 agent passes deserve checkpoints.

## References

| file | what |
|---|---|
| `references/provenance.md` | The parents' build recipe, archaeologically reconstructed — pass counts, order of operations, known traps. The cost model quotes it |
| `references/fetch-research.md` | Archived literature-acquisition survey (not implemented) |
| `templates/field-config.yaml` | The single per-field config both instances read |
| `templates/lit/` · `templates/draft/` | The instance skeletons: parameterized parent scripts, tier-aware check_drift, registry templates, stamped SKILL.md preambles |
| `templates/prompts/` | The five model-pass prompt files (PASS1/PASS2 rules verbatim + three reconstructed) and `examples/` (the parent's format examples the specs point to) |
| `tests/` | The factory's self-test: unit checks for the 2026-10-07 fixes plus a stamp → Tier 0–1 run on a fixture corpus with planted defects. Run `py -3 tests/run_selftest.py` after editing any template |

## Changelog

- **2026-10-07** — review-driven upgrade after an external two-reviewer
  audit of the factory and its first stamped instance. Shared
  config parser (quotes/comments), ingest from library folders with
  provenance and scan detection, `citation_style: mixed`, prose cleaning
  (reference lists, captions), attest variant union + apostrophes, superscript
  sentence boundaries, single paragraph threshold, cache move/partial/stale,
  null-is-FAIL drift checks, generic positional jobs, IMRaD headings, safe
  re-slicing, para_numbers repaired, PARENT-BLOCK markers in the draft
  SKILL template, back-ports from a mathematics instance (build_windows,
  run-in headings, T-series, single-file chapters).
