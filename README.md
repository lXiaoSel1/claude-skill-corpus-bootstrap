# corpus-bootstrap

English | [简体中文](README.zh-CN.md)

A [Claude Code](https://claude.com/claude-code) skill that turns the papers you have collected for a research field into two writing skills for that field:

- **`<field>-lit`** reviews a passage you wrote and reports whether it reads like your field's literature: terminology checked against your corpus, register rules, and sentence-to-sentence cohesion. It returns your text with the style fixed and leaves your argument, citations and numbers alone.
- **`<field>-draft`** drafts one paragraph at a time. Each paragraph follows a structure (a "Version") observed in at least two papers of your corpus, and every claim needs a ledger row with a pasted source line before the sentence is written. It can also reverse-outline a finished section (`--outline`) and trace introduction or abstract claims to the tables that support them (`--trace`).

Nothing is inherited from another field. Term counts, paragraph lengths, cohesion norms, the chapter taxonomy and the verb ladder for attributing claims are all measured on your own corpus.

## How it works

The build runs in five tiers. Each tier ends with an acceptance gate: a `check_drift` script plus something you check by eye. The skill stops after every tier and waits for you.

| Tier | What it builds | Cost | Acceptance |
|---|---|---|---|
| **0 Corpus** | Text files from your PDFs; a provenance manifest (source hash, converter and version, flags for scans, short documents and encoding damage); a corpus manifest with four denominators | scripts, minutes | you review the manifest; lit `check_drift` tier 0 passes |
| **1 Style layer** | Register measurements, cohesion norms, a transitions bank. **`<field>-lit` is usable from here** | scripts only | lit `check_drift` tier 1 passes; you read one live review |
| **2 Chapter map** | Headings from every paper, a chapter taxonomy induced from your papers (**you approve it**), a labelled chapter map, chapter slices | 1 induction pass + about 4–8 labelling passes | ≥ 90 % agreement with a hand-checked sample; you read the taxonomy and three slices |
| **3 Records + Versions** | Paragraph-by-paragraph reading records; per chapter, paragraph patterns attested in ≥ 2 papers. **`<field>-draft` is usable from here** | about 27 × (papers / 60) reading passes + 1 per chapter, run chapter by chapter | draft `check_drift` tier 3 passes; you read one chapter; the first paragraph is drafted |
| **4 Exemplars** | A sentence bank tagged with 8 rhetorical moves, a verb ladder, a structure canon | about 1 pass per 10 papers | both `check_drift` scripts pass in full |

The reading passes run as Claude Code subagents with the prompts in `templates/prompts/`. The taxonomy is induced from your papers rather than assumed, because a wrong taxonomy spoils everything downstream; that is why Tier 2 stops for your approval.

## Requirements

- Claude Code (the reading passes use subagents)
- Python 3.8 or later
- **PyMuPDF** (`pip install pymupdf`). Treat it as required: without it (or pypdf) page counts are 0 and scanned PDFs are not flagged.
- **`pdftotext`** from Poppler, on your PATH or set in `field-config.yaml`
- Optional: PyYAML, pypdf

The documentation uses the Windows launcher `py -3`. On macOS or Linux, use `python3`.

## Install

```bash
git clone https://github.com/lXiaoSel1/claude-skill-corpus-bootstrap ~/.claude/skills/corpus-bootstrap
```

The folder must be named `corpus-bootstrap`. Stamped skills are created next to it, in the same `skills/` folder, unless you pass `--dest`. A project-level `.claude/skills/` folder works as well.

## Quick start

Run these from the skill folder. The example field is `ecology`.

```bash
cd ~/.claude/skills/corpus-bootstrap

# 1. Create the two skills for the field
py -3 scripts/stamp.py ecology --citation-style author-year --keywords "population ecology, habitat loss"

# 2. Convert your PDFs: put them in ../ecology-lit/drop/, or read them in place from your library
py -3 scripts/ingest.py ../ecology-lit --src "/path/to/your/pdfs" --recursive

# 3. Build the corpus manifest, then review it
py -3 ../ecology-lit/scripts/build_corpus_meta.py

# 4. See which tiers are built and what the next one costs
py -3 scripts/tier_status.py ecology
```

Then ask Claude Code for the next tier, for example `/corpus-bootstrap tier 1`. Tiers can be resumed at any point; `tier_status.py` reads the ledger.

`--citation-style` accepts `author-year`, `numeric` or `mixed`. `--keywords` goes into the trigger description of the two new skills.

**You download the papers yourself.** The skill does not fetch, scrape or call any API. Keep your PDFs and corpus text out of any public repository.

## Writing guides used in Tier 4

Tier 4's structure canon quotes published writing guides, among them McCloskey, Cochrane, Thomson, and Gopen & Swan. Their texts are copyrighted and are **not included**. `references/canon-sources/_manifest.md` lists every source. Save the ones you can obtain as UTF-8 text in that folder, named `<key>.txt`, and Tier 4's check will find them.

## Self-test

```bash
py -3 tests/run_selftest.py
```

The self-test runs 65 checks in two parts:

1. Unit tests of the template scripts.
2. An integration run in a temporary folder. It stamps a throwaway field and builds a fixture corpus with planted defects: curly apostrophes, a phrase wrapped across lines, superscript citations, an image-only scan and a one-paragraph brief. It then runs Tiers 0 and 1, which must catch every defect.

It needs PyMuPDF and `pdftotext`, and it writes nothing outside the temporary folder.

## Known limitations

- **Tier 4 is incomplete as shipped.** Tiers 0–3 run without anything else, but Tier 4 also needs a `structure-canon.md`, which has no template in this repository, plus the writing guides you obtain yourself.
- **English corpora only.** The sentence splitter, word lists and corpus measurements assume English.
- **Windows first.** Documentation and printed hints assume `py -3`. The scripts themselves are cross-platform.
- **Manuscript paths.** Use absolute paths for `manuscript_tex` and `manuscript_tables` in `field-config.yaml`, because two scripts resolve relative paths differently.
- **Optional modes need agents that are not included.** `<field>-lit --audit` calls a `humanize-auditor` agent, and `<field>-draft` can fork a `claim-verifier` agent. Both are off by default.
- **"The parent" in the files.** The recipe was first built by hand as a pair of skills for empirical finance writing. Those skills are not part of this repository, and the factory does not need them. Where the files say "the parent", they mean that original pair, and its numbers appear only as illustrations.

## Repository layout

```
SKILL.md                    the skill Claude Code loads
scripts/                    stamp, ingest, capture, tier_status
templates/lit/              skeleton of <field>-lit
templates/draft/            skeleton of <field>-draft
templates/field-config.yaml the single per-field config both skills read
templates/prompts/          prompts for the reading passes, with format examples
references/                 build provenance, an archived (unimplemented) fetch survey, the writing-guide manifest
tests/run_selftest.py       the self-test
```

## License

MIT. See [LICENSE](LICENSE). Version 1.1.0 (2026-10-07).
