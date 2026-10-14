# corpus-bootstrap

English | [简体中文](README.zh-CN.md)

**Write papers that read like your field.**

A [Claude Code](https://claude.com/claude-code) skill that learns how a research field writes from the papers you collect, and turns that into three writing assistants for the field:

- **`<field>-lit`** reviews a passage you wrote and reports whether it reads like your field's literature: terminology checked against your corpus, register rules, and sentence-to-sentence cohesion. It returns your text with the style fixed and leaves your argument, citations and numbers alone.
- **`<field>-draft`** drafts one paragraph at a time. Each paragraph follows a structure (a "Version") observed in at least two papers of your corpus, and every claim needs a ledger row with a pasted source line before the sentence is written. It can also reverse-outline a finished section (`--outline`) and trace introduction or abstract claims to the tables that support them (`--trace`).
- **`<field>-polish`** revises your manuscript one section at a time, in your own `main.tex`. It scans the whole text against the corpus, checks rare words in the cited papers' own PDFs, checks every changed claim against its source, then compiles the manuscript and renders the section. It finds the sections and each citation's PDF by itself, so there is no configuration file to fill in.

**One-step onboarding** builds a field from a manuscript and a library: a PDF folder, a Zotero or JabRef `.bib` export, or PDFs with reading notes. It matches every citation to its PDF and runs Tiers 0 and 1 without stopping.

Nothing is inherited from another field. Term counts, paragraph lengths, cohesion norms, the chapter taxonomy and the verb ladder for attributing claims are all measured on your own corpus.

> **Note: building the reference set uses a lot of tokens.** For a corpus of about 60 papers, expect several hundred million tokens and most of a day of agent time. See [Token use](#token-use) before you start.

## Why we built this

Most of us learn to write in a field the slow way: by reading hundreds of its papers until we know which terms people use, how a paragraph usually opens, and which verb fits when we report someone else's finding. Grammar checkers and general-purpose AI assistants cannot give you that knowledge. Their prose is fluent but generic. They use terms that no one in your field uses, they sound like AI, and they can turn what one paper reports about another study into that paper's own finding.

This project is meant to help everyone write better by making the papers of your own field the standard. You collect the papers; the skill measures how they are written and checks your text against them. Every suggestion comes with its evidence: how many papers in your corpus use a wording, and the sentence where it appears. You can see why a change was made and decide for yourself whether to accept it.

## Who it is for

- **Graduate students and early-career researchers.** Learn how your field writes from its own papers, through counts and example sentences.
- **Authors who write in English as a second language.** The grammar may be fine while the word choice and sentence shapes still give the text away. Each suggestion shows the papers that use the wording, so you can see the idiom behind the correction.
- **Researchers moving into a new field.** Build the reference set from that field's papers, and its terms and paragraph conventions are spelled out from the start.
- **Anyone who writes with an AI assistant.** AI prose tends to be fluent and generic, and it may introduce terms or attributions that are not in the sources. `-lit` flags wording your field does not use, and every claim in a `-draft` paragraph has a ledger row with its source line, or a flag telling you to check it.

## What it does for you

**`<field>-lit`, a reviewer that shows its evidence**

- Checks every domain term against your corpus and reports how many papers use it, with a quoted line from one of them.
- Replaces vague nouns with the precise term your field uses.
- Flags a phrase as "AI voice" only when your corpus also rarely uses it; a phrase that appears in three or more of your papers is treated as your field's normal register.
- Grades how each sentence connects to the one before it.
- Gives a reason for every change and lists open questions under "leave to author".
- Never changes your argument, citations or numbers.

**`<field>-draft`, a drafter that works from a source ledger**

- Picks a paragraph structure that at least two papers in your corpus use for the same job.
- Builds a claim ledger before writing: each claim gets a row with the attribution verb and the source line pasted from the paper, and anything it cannot source is flagged with `!!`.
- Limits attribution verbs to what the source supports, using a verb ladder measured on your corpus ("find that" for results, "note that" when the source is thin).
- Reverse-outlines a finished section and traces claims in the introduction or abstract to the tables that support them.

**`<field>-polish`, section-by-section revision checked against the sources**

- Scans the whole manuscript against your corpus: words and multi-word frames that no paper uses, and sentences longer than the corpus 90th percentile.
- Looks up rare words and every domain term in the cited paper's own PDF. A term the paper uses is kept; a term of your own is replaced by one the corpus uses.
- Reads each sentence for meaning (unclear scope, a comparison with a missing side, a verb stronger than the source) and checks every changed claim against its source.
- Confirms that numbers, citation keys and source comments did not change, compiles your manuscript, and renders the section with citations as the PDF prints them.
- Writes to your files only after a snapshot, through exact one-occurrence replacements, and keeps a backup.

## Examples from a real literature review

The excerpts below come from a draft literature review on workers' compensation and medical bills, checked against a corpus of 66 papers in that area (51 of them are used for style checks). The excerpts are trimmed to a few lines, and corpus keys are shown as author and year.

How to read the counts: `w:62` means 62 occurrences in total; `range:10/66` means the wording appears in 10 of the 66 papers.

### 1. Terms checked against the corpus (`-lit`)

Three phrases from the draft:

> …medical costs paid through workers' compensation are higher than those paid through **general health insurance**…
>
> …fractures, lacerations, and other **clear-cut traumas** showed no such effect.
>
> …after the 2006 increase in the **weekly benefit ceiling**, affected workers' benefit duration increased by 11.1%…

What `-lit` changed, and why (excerpt):

```
CHANGED (3)

  1. "general health insurance" → "health insurance"
     R7/§3 — vague modifier; "health insurance" is the corpus standard (range:29/66);
     "general health insurance" appears in only 1 paper

  2. "clear-cut traumas" → "traumatic injuries"
     §3 — "clear-cut traumas" w:0 range:0/66; "traumatic injuries" w:62 range:10/66;
     Fomenko & Gruber (the paper being described) uses "traumatic injuries" 22 times

  3. "weekly benefit ceiling" → "maximum weekly benefit"
     §3 — "weekly benefit ceiling" w:0 range:0/66; "maximum weekly benefit" w:18 range:2/66;
     Cabral & Dillender (the paper being described) uses "maximum weekly benefit" 9 times
```

### 2. A claim ledger before the prose (`-draft`)

For a paragraph on Graves et al. (2012), `-draft` chose Version 3 (study by study, single study) and filled the ledger before writing. Three of its rows:

| cite-key | verb | claim | source | flag |
|---|---|---|---|---|
| Graves2012 | find that | Followed 1,830 workers identified from July 2002 to April 2004 | "From July 2002 to April 2004, 4354 workers were identified" (p.5); "the final study sample consisted of 1830 workers." (p.5) | |
| Graves2012 | find that | Male workers were 43% more likely to receive an early MRI within 42 days of injury than female workers | "Multivariable regression showed that male workers were 43% more likely to receive an early MRI than female workers (IRR: 1.43, 95% CI: 1.12--1.82)" (p.6) | |
| Graves2012 | find that | In Model 2, male IRR dropped to 1.24 (95% CI 0.98--1.58), no longer significant | Table 2 in the published journal version (not available in the PDF used for the note) | !! |

One of the sentences it drafted:

```latex
Male workers were 43\% more likely than female workers to receive an MRI within 42 days of injury (IRR 1.43, 95\% CI 1.12--1.82); after excluding self-report variables that could have been affected by interview timing, the authors stated that the overall pattern of associations was similar to the main model, but the male-to-female ratio dropped to 1.24 (95\% CI 0.98--1.58) and was no longer statistically significant.
```

`-draft` could not find a source line for the 1.24 figure, so it marked that row `!!` for checking instead of treating the figure as confirmed. When the author checked, the number was in Table 2 (p. 16) of the paper.

### 3. Phrases checked with both skills

One paragraph opened with **"Regarding costs,"**. `-lit` passed it, because "Regarding" appears in 25 of the 51 papers. `-draft` keeps a record of how every paragraph in the corpus opens, and that record showed a different picture: only 2 of the corpus's 2,702 paragraph openings start with "Regarding"; the 25 papers use it mid-sentence. The paragraph was rewritten to open with its subject.

More rewrites from the same review, each backed by a corpus count:

| Draft wording | In the corpus | Revised wording |
|---|---|---|
| a longer time to return to work | 0/66 | delayed return to work (4/51) |
| mostly indicate | 0/51 | mostly suggest ("suggest": 33/51) |
| Industry composition can also alter aggregate results. | 0/51 | Aggregate results also depend on industry composition. ("depend on": 8/51) |
| Studies controlling for … find similar results. | 0/51 | Results from studies that control for injury type in regression models are consistent with these findings. ("results from": 20/51; "consistent with": 31/51) |

### 4. The same paragraph, written directly and revised with `-polish`

This is the second paragraph of section 2.2 (return to work) in the same review. The first version is the draft Claude wrote without this workflow. The second is what `<field>-polish` produced from it after steps a–j. Citations are shown as the PDF prints them.

**Written directly, without the workflow**

> The clearest evidence on racial/ethnic disparities comes from the U.S. Traumatic Brain Injury (TBI) and Spinal Cord Injury (SCI) Model Systems databases. Arango-Lasprilla et al. (2008) use data on patients with moderate-to-severe TBI from 16 TBI Model Systems centers during 1989–2005 and, after controlling for pre-injury employment, discharge functional scores, and demographic factors, find that the odds of being unemployed one year post-injury for minorities are 2.17 times those of Whites. Gary et al. (2009) use patients injured during 1989–2001 from the same database and find that the odds of not being competitively employed for Blacks are 2.61, 2.10, and 3.15 times those of Whites at 1, 2, and 5 years post-injury, respectively, with no narrowing of the gap over time. The pattern holds for spinal cord injury: Arango-Lasprilla et al. (2010) use follow-up data from the SCI Model Systems spanning 1973–2006 and find that at 10 years post-injury, the odds of competitive employment for Whites are 3.02 times those for Blacks and 1.71 times those for Hispanics. Meade et al. (2004) use national SCI data on individuals injured during 1972–2002 and find that the one-year post-injury employment rate is 16.4% for Whites but only 5.9% for Blacks, with race remaining significant after controlling for education and injury characteristics.

**Revised with `-polish`**

> The strongest evidence on racial/ethnic disparities comes from the U.S. Traumatic Brain Injury (TBI) and Spinal Cord Injury (SCI) Model Systems databases. Arango-Lasprilla et al. (2008) used data on patients with primarily moderate-to-severe TBI from 16 TBI Model Systems centers during 1989–2005. After controlling for pre-injury employment, Disability Rating Scale scores at discharge, and demographic factors, minorities with TBI had 2.17 times the odds of being unemployed one year post-injury compared with Whites. Gary et al. (2009) used data from the same TBI Model Systems database on patients injured between 1989 and 2001. Blacks had 2.61, 2.10, and 3.15 times the odds of not being competitively employed compared with Whites at 1, 2, and 5 years post-injury, respectively, and this difference did not change significantly over time. A similar pattern is observed for spinal cord injury. Arango-Lasprilla et al. (2010) used SCI Model Systems data on patients interviewed at one-year follow-up during 1973–2006 and found that, at 10 years post-injury, Whites had 3.02 times the odds of competitive employment compared with Blacks and 1.71 times the odds compared with Hispanics. Meade et al. (2004) used U.S. national SCI data on individuals injured between 1972 and 2002 and found that the one-year post-injury employment rate was 16.4% for Whites but only 5.9% for Blacks; after controlling for education and injury characteristics, the difference remained statistically significant.

We pasted both versions into GPTZero (model 4.1o, advanced scan):

| | Written directly | Revised with `-polish` |
|---|---|---|
| Length | 209 words | 225 words |
| Verdict | "We are uncertain about this document. If we had to classify it, it would likely be considered human" | "We are highly confident this text is entirely human" |
| AI / Mixed / Human | 43% / 0% / 57% | 0% / 0% / 100% |

In the first version GPTZero marked the opening sentence ("The clearest evidence…") and the Meade et al. (2004) sentence as the most AI-like.

![GPTZero on the version written directly: 43% AI, with the first and last sentences highlighted](docs/images/gptzero-before.png)

![GPTZero on the version revised with -polish: 0% AI, 100% human](docs/images/gptzero-after.png)

Four of the changes come from the cited papers, and each was checked against the PDF:

| Written directly | Revised | The paper |
|---|---|---|
| patients with moderate-to-severe TBI | patients with **primarily** moderate-to-severe TBI | "Subjects with primarily moderate to severe TBI" (Arango-Lasprilla et al. 2008, p. 1) |
| discharge functional scores | **Disability Rating Scale** scores at discharge | "after adjusting for preinjury employment status, sex, Disability Rating Scale at discharge, …" (same paper, p. 1) |
| with no narrowing of the gap over time | this difference **did not change significantly** over time | "for blacks as compared with whites did not change significantly over time" (Gary et al. 2009, p. 6) |
| follow-up data from the SCI Model Systems spanning 1973–2006 | data on patients **interviewed at one-year follow-up** during 1973–2006 | "who were interviewed during their scheduled 1-year post-injury, follow-up evaluation between 1973 and 2006" (Arango-Lasprilla et al. 2010, p. 3) |

In the third row, "no narrowing" was wrong: the odds ratio falls from 2.61 to 2.10 between years 1 and 2, and what the paper tested was whether the change over time was significant. The other edits are style. The Arango-Lasprilla et al. (2008) and Gary et al. (2009) sentences were each split into a design sentence and a result sentence. The verbs moved to the past tense. "Clearest" (in 0 of the 51 style papers) became "strongest" (in 7), and "minorities with TBI" links back to the sentence before it. All 43 numbers and 9 citation keys of the section are unchanged.

This is one paragraph scanned once by one detector. Detector scores change between tools and versions, and they do not show who wrote a text. The workflow is built to make a section read like your field's papers and say what its sources say; it has no step aimed at detectors.

## What it can miss

The same review also turned up these problems:

- **`-lit` checks wording, not facts.** Another draft of the paragraph above, written without a ledger, called the 1.24 figure an "odds ratio"; Graves et al. report an incidence rate ratio. `-lit` made no changes to that section, because the wording was fine. The error was caught only when each statement was checked against the paper.
- **A first pass can be too lenient.** In the first round, all 13 section reviews passed, yet the text still used "the authors argue" 12 times (0 of the 51 papers use it), and its median sentence was 44 words long against 25 in the corpus. The review was then redone section by section under stricter rules: a full-text scan, long sentences split, and every term and framing phrase checked again.
- **"Paper-specific, keep" needs a human check.** `-lit` kept "acute low back sprains" as Graves et al.'s own term. The paper actually says "back sprain/strain", and the final text follows the paper.
- **Some changes remove meaning.** `-lit` once changed "fairly consistent" to "consistent" and deleted "the resulting"; both words carried meaning, and both changes were reverted.
- **A phrase the corpus uses can still be wrong in your sentence.** In the section of Example 4, `-polish` kept "After controlling for injury severity and other factors, women were more likely than men…", because 9 papers in the corpus use "after controlling for". In this sentence it is a dangling modifier: the women did not do the controlling.

Check numbers and findings against the source, use the `-draft` ledger to see where each claim comes from, and read every change before you accept it.

## Design principles

- The tools never change your argument, citations or numbers.
- The corpus is the only authority: every verdict cites a count and a line from your own papers.
- Every claim in a drafted paragraph has a source line or a visible flag.
- You supply the papers. The skill does not fetch, scrape or call any API.
- The build stops after every tier (one-step onboarding runs Tiers 0 and 1 together), and the chapter taxonomy waits for your approval.

## How it works

The build runs in five tiers. Each tier ends with an acceptance gate: a `check_drift` script plus something you check by eye. The skill stops after every tier and waits for you, except during one-step onboarding (see below).

| Tier | What it builds | Cost | Acceptance |
|---|---|---|---|
| **0 Corpus** | Text files from your PDFs; a provenance manifest (source hash, converter and version, flags for scans, short documents and encoding damage); a corpus manifest with four denominators | scripts, minutes | you review the manifest; lit `check_drift` tier 0 passes |
| **1 Style layer** | Register measurements, cohesion norms, a transitions bank. **`<field>-lit` is usable from here** | scripts only | lit `check_drift` tier 1 passes; you read one live review |
| **2 Chapter map** | Headings from every paper, a chapter taxonomy induced from your papers (**you approve it**), a labelled chapter map, chapter slices | 1 induction pass + about 4–8 labelling passes | ≥ 90 % agreement with a hand-checked sample; you read the taxonomy and three slices |
| **3 Records + Versions** | Paragraph-by-paragraph reading records; per chapter, paragraph patterns attested in ≥ 2 papers. **`<field>-draft` is usable from here** | about 27 × (papers / 60) reading passes + 1 per chapter, run chapter by chapter | draft `check_drift` tier 3 passes; you read one chapter; the first paragraph is drafted |
| **4 Exemplars** | A sentence bank tagged with 8 rhetorical moves, a verb ladder, a structure canon | about 1 pass per 10 papers | both `check_drift` scripts pass in full |

The reading passes run as Claude Code subagents with the prompts in `templates/prompts/`. The taxonomy is induced from your papers rather than assumed, because a wrong taxonomy spoils everything downstream; that is why Tier 2 stops for your approval.

### One-step onboarding

When you start from a manuscript, `/corpus-bootstrap polish` runs these scripts in order. Each script prints its default decisions as a table; you can change any of them and run the script again.

| Step | Script | What it does |
|---|---|---|
| 1 | `onboard.py` | Reads the manuscript (sections, citation keys, `.bib`, citation aliases) and matches each cited key to a PDF: the `.bib` `file` field, a reading note's PDF field, a PDF named after the key, then the DOI, the title, or first author and year. Reports keys with no PDF, keys with several candidates, duplicate versions and PDFs that are not in English. Creates the field's skills (it asks you for a name and keywords) or reuses them, and ingests the matched PDFs |
| 2 | `tier0_accept.py` | Tier 0 with default decisions: scans and failed conversions are excluded, reports and books are used for terminology only, short research entries are excluded |
| 3 | `calibrate_paragraphs.py` | Chooses the paragraph-length threshold for the corpus by a sweep from 80 to 400 characters |
| 4 | `tier1_fill.py` | Builds the style layer and fills every Tier 1 number and verdict, so `check_drift` passes with no hand editing |
| 5 | (Claude) | Reviews one paragraph of your manuscript with `<field>-lit` and shows you the result |
| 6 | `onboard.py --finish` | Lists which `<field>-polish` steps are ready and estimates the tokens and time for Tiers 2–4, then asks before building them |

### `<field>-polish`, section by section

| Step | What happens | Needs |
|---|---|---|
| a | Snapshot the section | the manuscript |
| b | Scan the whole manuscript against the corpus; the section's findings become the to-do list | Tier 0 |
| c | Split long sentences; replace framing phrases with ones found in at least 3 papers | Tier 0 |
| d | Review with `<field>-lit` and grade sentence-to-sentence cohesion | Tier 1 |
| d2 | Check paragraph openers against how the corpus opens its paragraphs | Tier 3 |
| e | Look up rare words and domain terms in the cited papers' PDFs | the PDFs |
| f | Read each sentence for meaning (scope, comparisons, verb strength) | |
| g | Confirm numbers, citation keys and source comments are unchanged; check paragraph and sentence lengths | Tier 0 |
| h2 | Check every changed sentence against its source | the PDFs |
| i | Compile the manuscript (0 warnings) and recount citations | TeX |
| j | Render the section as readable text for you | a compiled `.bbl` |

## Token use

Tiers 0 and 1 are scripts and use almost no tokens. Tiers 2 to 4 are reading passes run by Claude subagents, and they are expensive.

The figures below come from the transcripts of one real build: the instance used in the examples above, with 66 papers (51 used for style). Tiers 2 to 4 took 69 subagent runs and about 10 hours. They include the passes that had to be rerun during the build, and the main session that coordinated them.

| Step | Subagent runs | Tokens processed | Of which output |
|---|---|---|---|
| Tier 2: taxonomy induction and heading labelling | 9 | about 21 million | about 96,000 |
| Tier 3: PASS-1 reading | 43 | about 79 million | about 700,000 |
| Tier 3: PASS-2 induction | 11 | about 172 million | about 77,000 |
| Tier 4: exemplar tagging | 6 | about 44 million | about 7,000 |
| Main session over the same hours | | about 172 million | about 390,000 |
| **Total** | **69** | **about 490 million** | **about 1.3 million** |

About 96% of the tokens processed were re-read from the prompt cache; new input was about 18 million tokens. As a rough guide, budget about 7 million tokens per paper and scale with the size of your corpus.

To keep the cost under control:

- Run `tier_status.py` before each tier; it prints the number of agent passes the next tier needs.
- Build Tier 3 one chapter at a time, as the tier table says, and check your usage between chapters.
- If you only need the reviewer, you can stop after Tier 1: `<field>-lit` works from there.

**`<field>-polish` costs tokens per section, too.** Revising the 15-sentence section of Example 4 with steps a–j took one subagent 108 tool calls and about 34 minutes. It processed about 30 million tokens, 98% of them re-read from the prompt cache (about 0.5 million tokens of new input and output). Most of the work was corpus lookups for about 160 candidate phrases and checking each changed sentence against the PDFs. One-step onboarding itself runs Tiers 0 and 1 as scripts.

## Requirements

- Claude Code (the reading passes use subagents)
- Python 3.8 or later
- **PyMuPDF** (`pip install pymupdf`). Treat it as required: without it (or pypdf) page counts are 0 and scanned PDFs are not flagged.
- **`pdftotext`** from Poppler, on your PATH or set in `field-config.yaml`
- For `<field>-polish` step i: a TeX distribution with `pdflatex` or `xelatex`, and `bibtex` or `biber`
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

# 1. Create the three skills for the field
py -3 scripts/stamp.py ecology --citation-style author-year --keywords "population ecology, habitat loss"

# 2. Convert your PDFs: put them in ../ecology-lit/drop/, or read them in place from your library
py -3 scripts/ingest.py ../ecology-lit --src "/path/to/your/pdfs" --recursive

# 3. Build the corpus manifest, then review it
py -3 ../ecology-lit/scripts/build_corpus_meta.py

# 4. See which tiers are built and what the next one costs
py -3 scripts/tier_status.py ecology
```

Then ask Claude Code for the next tier, for example `/corpus-bootstrap tier 1`. Tiers can be resumed at any point; `tier_status.py` reads the ledger.

`--citation-style` accepts `author-year`, `numeric` or `mixed`. `--keywords` goes into the trigger descriptions of the new skills.

**Or start from a manuscript and your library.** In Claude Code, say `/corpus-bootstrap polish` and give the paths; Claude runs these steps and asks before Tier 2. By hand:

```bash
# 1. Match every citation to its PDF, stamp the field and ingest
#    (without --field it stops and asks for a name; --dry-run only builds the index)
py -3 scripts/onboard.py --manuscript /path/to/paper/main.tex --library /path/to/pdfs \
    --library /path/to/library.bib --field ecology --keywords "population ecology, habitat loss"

# 2. Tier 0 acceptance, the paragraph threshold, Tier 1
py -3 scripts/tier0_accept.py ecology
py -3 scripts/calibrate_paragraphs.py ecology
py -3 scripts/tier1_fill.py ecology

# 3. What works now, and what Tiers 2-4 would cost
py -3 scripts/onboard.py --finish --field ecology
```

Then revise a section with `/ecology-polish <section>`. `py -3 ../ecology-polish/scripts/doctor.py` lists the manuscript's sections and the steps that are ready. To add the third skill to a field stamped with version 1.1.0, run `py -3 scripts/stamp.py ecology --add polish`.

**You download the papers yourself.** The skill does not fetch, scrape or call any API. Keep your PDFs and corpus text out of any public repository.

## Writing guides for Tier 4

Tier 4 builds a structure canon (`structure-canon.md`): rules on how sections and paragraphs are organized, each quoting a published writing guide verbatim (`<key>.txt:line`) and each checked again against your corpus. **You need to find these guides for your own field.** Look for texts that teach how papers in your field are written, for example:

- articles or book chapters on how to write a paper in your discipline;
- genre analyses of research articles in your field, such as studies of how their introductions are structured;
- writing guides from journals, societies or departments in your field;
- general guides to scientific writing that your field relies on.

The original build used 17 guides written mostly for empirical economics and finance, among them McCloskey, Cochrane, Thomson, and Gopen & Swan. `references/canon-sources/_manifest.md` lists them with their sources, as a reference for the kind of text to look for. Their texts are copyrighted and are **not included**. A few of them are general enough to reuse in other fields.

Once you have the guides:

1. Save each one as UTF-8 text named `<key>.txt` in one folder, and list it in that folder's `_manifest.md`. The default folder is `references/canon-sources/`. To keep a separate set for each field, set `canon_dir` to another folder in both of the field's `field-config.yaml` files (the `-lit` and the `-draft` copy).
2. At Tier 4, record the number of guide files (`count`) and three or four verbatim spot quotes (`spot_quotes`) under `canon_sources` in the `-draft` skill's `references/registry.json`. `check_drift` searches for each quote in the files.
3. Write the field's `structure-canon.md`, quoting the guides by `<key>.txt:line`. No template is provided for it (see Known limitations).

## Self-test

```bash
py -3 tests/run_selftest.py
```

The self-test runs 106 checks in three parts:

1. Unit tests of the template scripts.
2. An integration run in a temporary folder. It stamps a throwaway field and builds a fixture corpus with planted defects: curly apostrophes, a phrase wrapped across lines, superscript citations, an image-only scan and a one-paragraph brief. It then runs Tiers 0 and 1, which must catch every defect.
3. An onboarding run. A fixture library (PDFs, a `.bib` with `file` fields, reading notes) and a manuscript that `\input`s two sections go through onboarding to Tier 1. Then every `<field>-polish` script runs on the manuscript; the checks include a word broken across a PDF line and a single-file manuscript.

It needs PyMuPDF and `pdftotext`, and it writes nothing outside the temporary folder.

## Known limitations

- **Tier 4 needs material you provide.** Tiers 0–3 run without anything else. Tier 4 also needs writing guides for your field (see [Writing guides for Tier 4](#writing-guides-for-tier-4)) and a `structure-canon.md` distilled from them, which has no template in this repository.
- **English corpora only.** The sentence splitter, word lists and corpus measurements assume English.
- **Windows first.** Documentation and printed hints assume `py -3`. The scripts themselves are cross-platform.
- **Manuscript paths.** Use absolute paths for `manuscript_tex` and `manuscript_tables` in `field-config.yaml`, because two scripts resolve relative paths differently.
- **Optional modes need agents that are not included.** `<field>-lit --audit` calls a `humanize-auditor` agent, and `<field>-draft` can fork a `claim-verifier` agent. Both are off by default.
- **`<field>-polish` has known gaps.** Its first end-to-end run (2026-10-14) completed every step and passed every check, and it also found problems that are not fixed yet:
  - step c needs step e's verdicts on source terms, and the edits from step c must be written before steps d and d2 read the file;
  - the list of one-off frames (L2b) is long and is mostly ordinary grammar;
  - when the corpus barely covers a section's topic, the "at least 3 papers" rule cannot be met, and the skill gives no fallback;
  - `attest.py` reports a multi-word phrase as attested when only a variant of it matched;
  - the scan counts each citation as a word of sentence length, and reads "OR" (odds ratio) as "or".
- **"The parent" in the files.** The recipe was first built by hand as a pair of skills for empirical finance writing. Those skills are not part of this repository, and the factory does not need them. Where the files say "the parent", they mean that original pair, and its numbers appear only as illustrations.

## Repository layout

```
SKILL.md                    the skill Claude Code loads
scripts/                    stamp, ingest, capture, tier_status; onboard, tier0_accept,
                            calibrate_paragraphs, tier1_fill (one-step onboarding)
templates/lit/              skeleton of <field>-lit
templates/draft/            skeleton of <field>-draft
templates/polish/           skeleton of <field>-polish: steps a-j, scripts, an optional settings example
templates/field-config.yaml the single per-field config both skills read
templates/prompts/          prompts for the reading passes, with format examples
references/                 build provenance, an archived (unimplemented) fetch survey, the writing-guide manifest
tests/run_selftest.py       the self-test
docs/images/                screenshots used in this README
```

## License

MIT. See [LICENSE](LICENSE). Version 1.2.0 (2026-10-14).

Written by Xuan Tang, in a project built on Pedro Sant'Anna's [claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow) template for academic work with Claude Code.
