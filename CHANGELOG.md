# Changelog — corpus-bootstrap

- **2026-10-14 (1.4.0)** — the rest of the review, the polish workflow's
  first-run problems, and parent text kept apart.
  **Polish:** steps run a → b → e → c → d → d2 → f → g, with each step's edits
  written before the next step reads the file and a re-check after f; counts.py
  takes its baseline at step a; the sweep's FOCUS reports how well the corpus
  covers the section, splits one-off frames into core and compositional, and
  no longer counts citations as words or reads "OR 0.41" as "or";
  cohesion_loop prints every join; opener_check counts repeated first-three-word
  lead-ins; sent_diff and trial_diff split a section without page comments by
  cited study, and trial_diff flags numbers that moved between studies;
  source_term_check and pdf_ctx try abbreviations both ways; compile.py says why
  it chose its engine (`--dry-run`) and lists citations split across pages; rep
  writes a session log; rule 2's fallbacks, the lit budget inside polish, a
  literature-review section's chapter, the missing comparator, the source's
  verb, `--batch` and the record's corpus scopes are written down.
  **-lit:** attest.py rates a multi-word phrase found only through other forms
  of its last word THIN, not ATTESTED.
  **Parent text:** kept worked examples sit in PARENT-EXAMPLE blocks or carry a
  "parent" label; text a tier replaces sits in PARENT-BLOCK tier=N, now with
  markers on their own lines and outside tables; lit and draft check_drift check
  that markers pair and that no PARENT-BLOCK survives its tier; the self-test
  checks that no parent name or number is left unlabelled in the templates.
  **Configuration:** canon_dir is the field's own `<draft>/references/canon-sources`
  from the start; `equation_layer` is declared; job definitions are the `jobs:`
  item comments; onboarding with `--notes` writes `notes-index.md`; Tier 3
  checks the structure-norms layers; `--map` paths are read from the CSV's
  folder and `--map` cannot be combined with `--src`.
  **Code:** one key function, one place for the cost models, no module-level
  state in stamp.py, every file closed, internal dated notes removed.
  **Measured rerun** of the polish workflow on the same section (one agent,
  batch mode): 114 tool calls, 36.5 min, 32.0 million tokens processed (98.3%
  cache reads); numbers, cite keys and counts unchanged, 0 LaTeX warnings. Of
  the 23 problems the first run found, 20 were solved and 3 only in part; its
  18 new findings were fixed here except two left as known limits (", with …"
  tails in scan_appositive, frames an edit added in the rule-4 re-run):
  note_terms takes the page written before a quote (`p.6："…"`); pdf_ctx and
  source_term_check print each context's PDF page; a paragraph that opens
  without a citation starts its own sent_diff block; the coverage line always
  says OK or LOW and counts cited papers missing from the corpus; the session
  log names the pairs file; rule 2 caps the source-wording exemption at about
  six words (longer stretches are quoted or rebuilt, as lit's lifted-phrasing
  rule asks), keeps the author's wording when no attested phrase has the same
  sense, and gives an uncited sentence its paragraph's sources; rule 1 says
  which additions are fixes; step c keeps "the authors" with the source's verb
  instead of adding `\citet`; step f asks for section G findings, not
  humanizer's embedded mode; steps are written in run order; lit's rule 8, the
  cohesion norm cell, attest.py's exit code and split citations outside the
  section are explained.
  Self-test: 135 checks unchanged, 35 added.
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
