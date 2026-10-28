# Changelog — corpus-bootstrap

- **2026-10-28 (1.6.3)** — the front block no longer swallows an introduction
  that opens with no blank line, end marker or heading line. `stage_b_slice.py`
  `front_end`: once FRONT_MIN_CHARS are in and the line before ends a sentence,
  a run-in introduction heading (`1. Introduction * It is ...`, `Introduction
  The phrase ...`, `i. Introduction`; not `Introduction of the rule ...`) or a
  journal's small-caps lead-in (three or more capitalised words running into
  lowercase prose: `IN SEPTEMBER 2008, SHORTLY AFTER THE default ...`) ends
  the abstract and opens the introduction. On a finance corpus (re-sliced in
  a scratch copy, the instance's own slices untouched) it restores the
  introduction's opening for 12 of the 21 papers whose abstract slice had
  taken it, and changes no other paper's abstract or introduction slice. Not
  covered: three papers from venues that print no abstract (the abstract slice
  IS the introduction's start; mark them `NOT A ABSTRACT`), five
  paragraph-per-line texts whose introduction opens with an ordinary sentence,
  and one abstract shorter than FRONT_MIN_CHARS (Tepper1981, 305 characters).
  Selftest: 1 check (fails on 1.6.2).
- **2026-10-28 (1.6.2)** — two fixes from a finance build's Tier 3 acceptance.
  `recount.py`: a paragraph's count line may carry a reader's note after it
  (`9 sentences  [cut by a page break ...]`); the pattern required the count
  to end the line, so a finance build's uniformity calibration skipped 541
  of 8,190 paragraphs (triples 150/6322 → 165/6853, both 2.4%; pairs 14.8% →
  14.7%). `check_drift.py`: "registry sections.chapters recorded" prints the
  chapter count when it passes; it printed its failure text either way.
  `measure_verbs.py --write` crashed (NameError `_field`, left behind when the
  corpus path moved to `lit_instance`); the header's source line now prints
  the corpus path relative to the -draft skill. Selftest part 10 (3 checks;
  all three fail on 1.6.1 — the selftest had imported measure_verbs but never
  run `--write`).
- **2026-10-27 (1.6.1)** — fixes from a finance build's Tier 1 acceptance
  and Tier 2 start, and `scripts/seed_from.py`.
  `_src.py`: a stretch shared with a cited paper that is mostly a proper name
  ("the Retirement Funding Relief Act of 2021", fewer than `NAME_PROSE` = 3 words
  outside names) prints as a `NAME` line and is not counted as COPIED, in
  `draftcheck src` and `para_check`; `draftcheck src` no longer carries the
  previous sentence's citations into a "This paper / We / Our" sentence.
  `a1_headings.numbered_ok`: a numbered line opening with a stopword ("2.
  Prior literature and hypothesis development") is a heading when it is short,
  carries a field headword and no auxiliary verb (GarmanKubick2025 was lost).
  `seed_from.py <field> --from <old draft> --tier 2` imports an older build's
  A2 verdicts for papers whose corpus text is byte-identical, line by line
  (IMPORT / PARTIAL / REREAD in `seed_report.md`); one old job the approved
  taxonomy lacks stops the import unless `--job-map` names it. `a2_build.py`
  leaves the imported lines out of the wave files. `--tier 3 --chapter <job>`
  imports an older build's PASS1 record block for a paper whose corpus text is
  byte-identical, whose slice has the same text lines (or only added heading
  lines), and every one of whose quoted first sentences is in the new slice
  (verify_shards.py's fingerprint): `_shards/<chapter>-00.md`, plus
  `<chapter>-reread.txt` for PASS1. Slicer (`stage_b_slice.py`): a JSTOR cover page
  ("JSTOR is a not-for-profit service ...", `Author(s):`, `Stable URL`) is
  banner matter, not the abstract; a bare carriage return inside a line is
  written as a space; new config `positional_skip` (`job:Key` items) names
  papers whose text lost a positional block (a CAR text runs from the author
  lines to "1. Introduction"), so no slice of author lines is written while
  the next positional job still starts after it. `short_paras.py` drops a footnote kept as a paragraph ('4 Existing pension laws ...': 24 of 154 literature candidates in a finance build). New config `paragraph_targets` (`chapter:LO-HI:CITES`): `para_check.py --chapter <job>` without `--band` / `--cites` checks the manuscript's own target for that chapter. Slicer: prose between a trimmed front block and the next positional job's first heading (no other job in between) opens that job (SundaramYermack2007's introduction L11-158 sat in no slice). Known, not fixed: a positional abstract with no end marker can run on into the introduction's first page (about 19 of 107 papers in a finance build); the records recover those openings from the abstract slice. `draftcheck version-card --full` matches the bank by part and number. Self-test 213 checks.
- **2026-10-27 (1.6.0)** — the parent's fast lane in the templates, and a
  paragraph's shape measured. The draft instance gets the
  parent's evidence cards (`cards.py`, a second whitelisted write path), the
  one-call paragraph check (`para_check.py`: MAP, NUMBERS, COPIED, LENGTH,
  STRENGTH, WORDING, FRAMES, CITATIONS) and `draftcheck.py src / router /
  version-card` with `_src.py`, `_tiers.py` and `_ngram.py`, parameterized: the
  corpus is the lit instance's, a key's PDF and note come from the onboarding
  index, and the cards' design words are generic plus the field's
  `design_terms`. Two parent bugs are not carried over: a name such as MAP-21 is
  kept in a pasted line (it was deleted, so the line read NOT-VERBATIM) and
  dropped only where numbers are read, and the ownership markers ("Consistent
  with", "Following") match in any case. The lit instance gets rule B (a
  replacement inside an attributed clause must be in that paper's own text,
  `src --find`) and the copy check after FIX (4b). New layer F in
  `measure_structure.py`: words, sentences and distinct citations per paragraph
  for every chapter, style-safe papers only; `para_check.py --band LO-HI
  --cites N` makes an author's target must-pass and prints the paragraph's
  percentiles in its chapter; `short_paras.py` lists a chapter's short corpus
  paragraphs for a short-paragraph bank and checks the bank verbatim;
  `version-card --full` prints the whole paragraph behind each example and the
  bank's entries. Review and survey articles (`reviews:` in field-config) stay
  for terminology and leave the style sample, the cohesion norms and the
  chapter sample; tier0_accept takes a map role `review` and lists papers that
  call themselves a review. `measure_register.py --section <job>` measures one
  chapter's register from its slices (capture.py passes arguments through);
  `cohesion.py` marks the tails of a 3-4-sentence paragraph advisory. Onboarding
  takes `--reuse-corpus <dir>` (a key with an earlier text is copied, not
  converted again) and `--extra-map <csv>` (uncited papers). Instance trigger
  phrases name the field. Self-test 198 checks (15 new).
- **2026-10-17 (1.5.0)** — facts checked against the PDF, and a real
  library's layout. New polish script
  `num_check.py`: every number of every cited sentence of a section is looked
  up in the cited papers' texts (TOGETHER / FOUND / APART / ELSEWHERE /
  MISSING, with the page), so a number the draft copied wrong is caught even
  in a sentence no edit touched; a number is looked up in the paper its
  citation is attached to. New `copy_check.py`: every unquoted stretch of 7 or
  more words a cited sentence shares with its paper (rule 2(a)'s six-word
  exemption made measurable), with its page. `sent_diff.py` lists each change
  of claim strength in a changed block (STRONGER? / HEDGE LOST?, three tiers
  from hedges to causal claims; "result in" only as a verb, not "the results
  in this paper") for h2, and step c keeps a replaced frame's
  strength: a test rerun had replaced the 0-paper "evidence pointed to moral
  hazard" with the attested "studies support the moral hazard hypothesis",
  and no check saw it. pdf_ctx, source_term_check and num_check give the printed page
  beside the file page (from the PDF's page labels, the page headers or the
  .bib pages field), name a PDF that is a manuscript or working paper, and
  name pages with no text layer, which were not searched; onboarding lists
  articles whose PDF is a manuscript or preprint. Rule 1: a reading note is a
  pointer, and a number or quotation from it counts only once it is found in
  the PDF (draft: in the corpus file). A main file with prose of its own that
  \input's only tables is split by its headings (a manuscript that wrote its
  sections in main.tex was cut into its table files before), and
  render_section.py prints a subsection heading inside such a section as its
  title, not as LaTeX. Notes are
  matched by the bib_key / citekey in their front matter as well as by file
  name, and a note's PDF may be a bare file name with its folder in another
  field (PDF路径 / pdf_dir); file names compare without spacing or
  punctuation. When several PDFs match a key by title, the one named after
  the entry (first author and year, or the title) comes first: a paper whose
  references cite the title is not the paper. On a finance manuscript:
  seven prose sections instead of 19 tables, 62 keys matched through their
  notes (60 before the file-name fix, 47 by file name alone), Rauh (2006) on
  its own PDF instead of a paper citing it. The draft's draftcheck.py now
  reads citations with the shared natbib/biblatex pattern too (1.3.1 had
  missed it: \citealp, \parencite and the rest went unlisted). Self-test:
  172 checks unchanged, 11 added.
- **2026-10-14 (1.4.1)** — the two gaps the polish rerun left.
  `sweep.py <section> --since <snapshot>` marks each FOCUS frame NEW (not in
  that snapshot of the section) or +k (used k more times) and lists the
  0-paper frames that are gone, so the rule-4 re-run after step f shows what
  the edits brought in. `scan_appositive.py` also lists with-absolutes and
  participle phrases that end a sentence after a main clause, each labelled
  with its kind, and skips prepositions such as "including" and "during"; on
  the rerun's input it finds the two ", with …" tails the rerun had to catch
  by hand, and all 17 of its new candidates there are real tails. Rule 5 covers
  with-tails and says when a participle tail stays. Self-test: 170 checks
  unchanged, 2 added.
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
