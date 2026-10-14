# Changelog — corpus-bootstrap

- **2026-10-14 (1.3.1)** — fixes from a full review of the published copy.
  Citations: one shared pattern for natbib and biblatex commands (`\parencite`,
  `\textcite`, `\autocite`, `\footcite`, capitalised forms; not `\nocite`).
  Launcher: printed hints name `py -3` on Windows and `python3` elsewhere, and
  each SKILL says so. Tier 0: no crash when an interleaved paper meets a machine
  without PyMuPDF; working papers and preprints (@techreport, @misc, ...) stay
  research unless short; a re-run that changes the style-safe set drops Tier 1.
  ingest: manifest written after every file, unrecorded texts adopted with QC,
  folders with brackets, `.PDF`, case-only key collisions, page counts from
  pdftotext form feeds. onboard: .bib and note folders searched at their own
  level only; the PDF scan cache redone once an extractor is installed; a
  missing manuscript and odd field names reported. stamp: field slug rule,
  `--keywords` checked, `~` expanded; every description a quoted YAML string.
  draft: check_drift Tier 3 fails on an empty registry, Tier 4 on too few spot
  quotes; evidence map follows `\input`; relative manuscript paths resolve
  against the project or fail; drafting before Tier 4 uses the floor verbs.
  Prompts name their output files. canon_ingest needs no PDF converter for web
  pages and text, and keeps hand-added texts.
- **2026-10-14 (1.3.0)** — Tier 4's writing canon done for the user. `canon_ingest.py`
  turns the guides the user collected (PDF, saved web pages, text, or a `.bib`
  with file fields) into `canon-sources/`, writes `_manifest.md`, sets
  `canon_dir` in both configs and fills registry `canon_sources`;
  `structure-canon.skeleton.md` (the parent's rule frame, no quotations) and
  `prompts/structure-canon.md` let one agent draft the field's canon;
  `check_canon_quotes.py` checks every quotation at its line pointer (pieces in
  order, two-column text, hyphens, trailing punctuation and quote marks handled;
  any quote not OK fails) and is a Tier 4 check_drift line. Doing the steps by
  hand still works. Measured drafting run (17 economics guides, 151,547 words):
  one agent, 101 tool calls, 14 min, 10.1 million tokens processed (97% cache
  reads); 108 quotes, all at their pointers on the first check; 32 of 33 rules
  grounded, S15-S17 added. The run's ten prompt questions and five checker gaps
  were fixed afterwards.
- **2026-10-14 (1.2.0)** — one-step onboarding and a third instance,
  `<field>-polish`. `onboard.py` matches a
  manuscript's citations to the user's library (bib file field, notes, file
  name, DOI, title, author + year) and drives Tiers 0–1 through
  `tier0_accept.py`, `calibrate_paragraphs.py` and `tier1_fill.py` with
  default decisions; `stamp.py` stamps polish (`--add polish`, `--lit-dir`,
  `--draft-dir`); `tier_status.py` prints token and time estimates for Tiers
  2–4 and which polish steps are ready. The polish scripts port the
  section-revision workflow of a health-services literature review with its paths
  and project content removed and these fixes: header lines skipped instead
  of line 1; snapshots beside the manuscript; PDF text with ligatures restored
  and line-end hyphens joined; sweep controls judged on the phrase itself,
  frames compared on token boundaries, L2b in FOCUS; cohesion via `--json`;
  records parsed for every instance format, citations replaced by a
  placeholder the splitter does not read as an initial; sentence diffs matched
  by source comment and split before `\citet`; exit code 1 on every failed
  check, replacements all-or-nothing; citation rendering for spaced keys and
  several aliases; the user's own main.tex compiled with reruns. Self-test:
  65 checks unchanged, 41 added.
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
