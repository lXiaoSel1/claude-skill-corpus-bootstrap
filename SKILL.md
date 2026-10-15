---
name: corpus-bootstrap
description: "Bootstrap a new research field's writing infrastructure from the user's own downloaded papers. Stamps three skill instances — <field>-lit (style/terminology reviewer against the field's corpus), <field>-draft (paragraph drafting with evidence ledgers) and <field>-polish (section-by-section revision of the user's manuscript against the literature and the cited PDFs) — then builds their reference layers in five acceptance-gated tiers (corpus → style measurements → chapter taxonomy+map → records+Versions → exemplars). One-step onboarding takes a manuscript and a library (PDF folder, Zotero/JabRef .bib, or PDFs plus reading notes), matches every citation to its PDF, and builds Tiers 0-1 with no configuration file. Use when user says \"我要研究一个新领域\", \"把文献建成语料库\", \"用我的文献库改这篇论文\", \"bootstrap a corpus for X\", \"onboard my manuscript and library\", \"给这个领域盖一套 lit/draft skill\", \"新领域的文献库\". The user downloads the PDFs; nothing is fetched."
author: Xuan Tang
version: 1.4.0
argument-hint: "[polish <main.tex> <library> | stamp <field> | ingest | tier <n> | status <field>]"
disable-model-invocation: false
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Write", "Edit", "Task"]
---

# `/corpus-bootstrap` — 给任意领域盖一套 lit + draft + polish 基础设施

You replay, on a new field's corpus, the recipe that built an original
economics/finance pair of skills (called "the parent" in these files; it is
not part of this skill and is never needed). The recipe is measured, not
invented — `references/provenance.md` records how the parent was built (which
artifacts are script-replayable, which needed model reading passes, and how
many). **The acceptance law: each tier ends with both instances'
`check_drift` green for that tier** — the templates carry the parent's file
inventory, slots and registry discipline — with every number re-measured on
the NEW field's corpus, never inherited from economics.

| `/corpus-bootstrap …` | section below |
|---|---|
| `polish <main.tex> <library>` | One-step onboarding |
| `stamp <field>` | The five tiers, Tier 0 (`stamp.py`) |
| `ingest` | The five tiers, Tier 0 (`ingest.py`) |
| `tier <n>` | The five tiers, the row for tier n |
| `status <field>` | Resume (`tier_status.py`) |

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
5. **The parent is read-only.** Templates are frozen, parameterized copies of
   it; where a machine still has the parent skills, this skill never edits them.
6. **One exception to rule 4:** one-step
   onboarding runs Tier 0 and Tier 1 back to back without stopping, because
   both are scripts with default decisions the user can change afterwards.
   Every decision is printed as a table. Tiers 2–4 still stop: print
   `tier_status.py`'s token and time estimate and ASK first.

## One-step onboarding (`/corpus-bootstrap polish`)

For "use my library to revise this paper": the user gives a manuscript
(`main.tex`) and a library — a PDF folder, a Zotero / JabRef / Mendeley `.bib`
export with `file` fields, or PDFs plus reading notes. No configuration file.

| # | run | what it does |
|---|---|---|
| 1 | `py -3 scripts/onboard.py --manuscript <main.tex> --library <folder or .bib> [--library …] [--notes <folder>]` | reads the manuscript; builds `<manuscript dir>/.polish/library-index.json`, matching each cited key to a PDF by the .bib `file` field, a note's PDF field, a PDF named after the key, the DOI, the title, then first author + year; reports unmatched keys, several candidates, duplicate versions, non-English PDFs. `--dry-run` stops here. Without `--field` it exits 3: **ask the user for a field name (and, for a new field, topic keywords)**, then re-run with `--field <slug> --keywords "…"`. It reuses an existing field (stamping only a missing polish) or stamps all three, writes `manuscript_tex`, writes `corpus_map.csv` (corpus key = cite key), runs `ingest.py --map` and `build_corpus_meta.py` |
| 2 | `py -3 scripts/tier0_accept.py <field>` | default decisions: SCAN / ERROR → excluded; INTERLEAVED → re-extracted with PyMuPDF (excluded when still interleaved or PyMuPDF is missing); book / manual / data entries → terminology_only; working papers and preprints (@techreport, @report, @misc, @unpublished, @online) → research, terminology_only only when SHORT; SHORT research entries → excluded, SHORT entries with no .bib type → terminology_only; non-English → excluded. Writes both configs (read back), rebuilds the manifest, fills `corpus.*`, adds Tier 0, runs check_drift. A re-run that changes the style-safe papers drops Tier 1 (re-run steps 3–4). `--keep-config` after a hand edit |
| 3 | `py -3 scripts/calibrate_paragraphs.py <field>` | sweeps `para_min_chars` 80–400; most paragraphs with no paper at zero (`--set N` overrides); both configs; sweep table in `para-calibration.md` |
| 4 | `py -3 scripts/tier1_fill.py <field>` | the two captures and the transitions bank; registry `cohesion.*` and `transitions.*`; the 12 `corpus: TO-MEASURE` verdicts in cohesion-canon.md filled with this corpus's numbers beside the parent's (K10, K11 → `UNMEASURED (judgment)` with the reason); a note in register.md; Tier 1; check_drift |
| 5 | model | live check: `/<field>-lit` on the manuscript paragraph tier1_fill suggests; show the user its TERMS and REGISTER blocks |
| 6 | `py -3 scripts/onboard.py --finish --field <field>` | check_drift, the polish doctor (which steps are ready), and tier_status's estimate for Tiers 2–4; **ask before building them** |

Every script is re-runnable. Each refuses to go on when a check fails.

## `<field>-polish`

The third instance (`templates/polish/`): steps a–j of section-by-section
revision (snapshot, whole-manuscript register sweep, frames, `/<field>-lit`
and cohesion, paragraph openers, rare words checked in the cited PDFs,
section G, mechanical diffs, changed claims against their source, compile and
counts, render). It reads the manuscript structure from `main.tex` itself
(`\input` files, or headings in a single file) and the PDFs from the library
index; an optional `.polish/polish.yaml` only overrides thresholds. Steps need
lit Tier 0–1 (most), draft Tier 3 (paragraph openers) or Tier 2 (an optional
length comparison); the polish instance's `doctor.py` says which are ready.
Fields stamped before 1.2.0 get it with `py -3 scripts/stamp.py <field> --add polish`
(`--lit-dir` / `--draft-dir` when the siblings live elsewhere).

## The five tiers

All commands use `py -3` on Windows (where `python` may be the Store stub); on
macOS and Linux run them with `python3`. Paths in `<lit>`/`<draft>` are the
stamped instances; a field stamped with `--dest` needs the same `--dest` on
every factory script.

**Before Tier 0:** PyMuPDF is effectively required (`py -3 -m pip install
pymupdf`): without it or pypdf, page counts come only from pdftotext and
interleaved papers cannot be re-extracted. `pdftotext` (Poppler) is the
preferred converter; the self-test needs it.

**Long runs:** `onboard.py` and `ingest.py` convert every PDF and can take
longer than the Bash tool's default 2-minute timeout. Run them with
`timeout: 600000`, or in the background. A stopped ingest keeps what it
wrote: the manifest is saved after every file, and a re-run converts only
what is missing.

| Tier | command | builds | cost | acceptance |
|---|---|---|---|---|
| **0 corpus** | `py -3 scripts/stamp.py <field> [--citation-style author-year\|numeric\|mixed] [--keywords "..."] [--dest <skills-dir>]` → `py -3 scripts/ingest.py <lit> [--src <pdf-folder> --recursive \| --map keys.csv]` (PDFs may stay in the user's library; `drop/` is the default source) → `py -3 <lit>/scripts/build_corpus_meta.py` | corpus/*.txt · `corpus_sources.json` (source, converter + version, sha256, SCAN/SHORT flags) · four-denominator manifest with per-paper role, group and citation culture | scripts, minutes | `py -3 scripts/tier0_accept.py <field>` does all of this with default decisions; by hand: manifest reviewed, SCAN/SHORT/excluded/terminology_only decided in BOTH field-config copies, build_corpus_meta's four denominators copied into the lit registry's `corpus.*`, lit check_drift tier-0 green → append 0 to both registries' built_tiers |
| **1 style layer** | calibrate `para_min_chars` in field-config → `py -3 scripts/capture.py <lit> measure_register.py register-measurements.md` · `py -3 scripts/capture.py <lit> build_cohesion_norms.py cohesion-measurements.md` · `py -3 <lit>/scripts/build_transitions.py`; fill registry numbers (each builder prints them); replace every `corpus: TO-MEASURE` in cohesion-canon.md and the parent counts in register.md | register measurements · cohesion norms (coarse) · transitions bank | scripts, zero agents | lit check_drift tier-1 green; **live-scan one paragraph of the new field's prose with `/<field>-lit`** — TERMS and REGISTER slots print; user reads the scan |
| **2 chapter map** | `py -3 <draft>/pipeline/make_sample.py` → `a1_headings.py` → hand-build `groundtruth.json` (~10 papers) → `recall.py` gate → `build_windows.py` → taxonomy induction (prompts/taxonomy-induction.md, reads a1_windows.md) → **USER APPROVES; jobs (each with its definition as the item comment), positional_jobs, start/end markers land in BOTH field-config copies** → `a2_build.py` → A2 waves (prompts/a2-wave.md) → hand `a3_groundtruth.json` → `build_map.py` (adjudications into its ADJUDICATED dict) → `stage_b_slice.py --dry-run`, then real → `build_names.py` | approved taxonomy · chapter-map · chapter-names · slices + manifest + fingerprint | 1 induction pass + ~4-8 wave/correction passes + A3 gate reads | A3 agreement ≥90% recorded in registry; user reads the taxonomy table and 3 slices; draft check_drift tier-2 green (incl. no tier-2 PARENT-BLOCK left in SKILL.md) |
| **3 records + Versions** | PASS1 shards (prompts/pass1-reading-SPEC.md, ~8-16 papers/agent/chapter) → `verify_shards.py` → PASS2 per chapter (prompts/pass2-induction-SPEC.md) → `para_numbers.py <chapter>` audit, then `--write` → `recount.py` (uniformity calibration → registry+SKILL.md) → `measure_structure.py` + typing appendices → rewrite the tier-3 PARENT-BLOCKs of SKILL.md | records/ · sections/ (skeletons+parts, four-field Versions ≥2-attested) · uniformity gate numbers | ~27×(n/60) PASS1 + 1 PASS2/chapter — **run chapter by chapter, accept each** | draft check_drift tier-3 green (Version counts, four fields, ≥2 attestation — mechanical); user reads one full chapter; `/<field>-draft` drafts its first paragraph |
| **4 exemplars** | tagging shards (prompts/exemplar-tagging.md, ~10 papers/agent) → `py -3 <lit>/scripts/build_exemplars.py` → registry counts + move_tags → `py -3 <draft>/scripts/measure_verbs.py` → verb-ladder.md + registry `verb_ladder_counts` → **writing canon**: the user collects the field's writing guides; `py -3 scripts/canon_ingest.py <field> --src <folder or .bib>` converts them into `canon-sources/`, writes `_manifest.md`, sets `canon_dir` in both configs and fills registry `canon_sources` (or do these by hand, as the README describes) → ASK (print the estimate), then one agent drafts structure-canon.md with `prompts/structure-canon.md` from `references/structure-canon.skeleton.md` → `py -3 <draft>/scripts/check_canon_quotes.py` exits 0 → rewrite the tier-4 PARENT-BLOCK | exemplars bank (8 move labels) · verb-ladder · structure canon | ~1 pass per 10 papers | both instances' check_drift FULL green = the parent-parity end state |

**Resume**: `py -3 scripts/tier_status.py <field> [--dest <skills-dir>]`
reports built tiers and the next tier's cost scaled by the style-safe sample.
Registries' `built_tiers` is the ledger; tiers are idempotent to re-enter.
`stage_b_slice.py` computes every slice and checks every corpus file BEFORE
it moves the old slices to `references/_slice_backups/<stamp>/` — still run
`--dry-run` first.

**Manuscript onboarding (outside the tiers).** When the field gets a
manuscript: `onboard.py` writes `manuscript_tex` into both instances'
field-config.yaml (set `manuscript_tables` by hand if there are table files),
run `build_evidence_map.py` (`state.py` creates `manuscript-state.md` on its
first write), fill the register §3/§5 and
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
- **Not a refactor of the parent.** The parent skills stay untouched; this
  factory carries frozen parameterized copies.
- **Not a one-command pipeline.** Tier gates exist because a wrong taxonomy
  poisons everything downstream and 40 agent passes deserve checkpoints.

## References

| file | what |
|---|---|
| `references/provenance.md` | The parents' build recipe, archaeologically reconstructed — pass counts, order of operations, known traps. The cost model quotes it |
| `references/fetch-research.md` | Archived literature-acquisition survey (not implemented) |
| `templates/field-config.yaml` | The single per-field config both instances read |
| `templates/lit/` · `templates/draft/` | The instance skeletons: parameterized parent scripts, tier-aware check_drift, registry templates, stamped SKILL.md preambles |
| `templates/polish/` | The polish instance: SKILL.md (steps a–j, rules, lessons), scripts, `polish.example.yaml`, the per-section record template, pairs examples, `references/humanizer-G.md` |
| `scripts/onboard.py` · `tier0_accept.py` · `calibrate_paragraphs.py` · `tier1_fill.py` · `_factory.py` | One-step onboarding (above) |
| `templates/prompts/` | The six model-pass prompt files (PASS1/PASS2 rules verbatim, three reconstructed, and the 1.3.0 structure-canon prompt) and `examples/` (the parent's format examples the specs point to) |
| `scripts/stamp.py` · `ingest.py` · `capture.py` · `tier_status.py` · `canon_ingest.py` | Stamping, Tier 0 conversion, Tier 1 captures, progress and cost, Tier 4 writing guides |
| `tests/` | The factory's self-test: unit checks, a stamp → Tier 0–1 run on a fixture corpus with planted defects, (1.2.0) onboarding from a fixture library through Tier 1 plus the polish scripts, and (1.3.0) the Tier 4 writing-guide scripts. Run `py -3 tests/run_selftest.py` after editing any template |

## Changelog

See `CHANGELOG.md` (version 1.4.0).
