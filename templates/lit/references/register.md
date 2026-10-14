# register.md — the review checklist for `/{{FIELD}}-lit`
<!-- STAMPED INSTANCE: {{FIELD}} -->

> **INSTANCE STATUS.** Rule ARCHITECTURE (R1-R11, the gate logic, the slots)
> is field-invariant and live from day one. Every COUNT below is the parent
> finance corpus's until `py -3 scripts/measure_register.py` runs on this field's
> corpus at Tier 1 — treat parent counts as illustrations, never as this
> field's verdicts. §3 (precise nouns) and §5 (theory frame) are
> MANUSCRIPT-ONBOARDING slots: they fill when this field's manuscript exists,
> not at corpus time. The refuted-list (§6 R5) is the parent corpus's; a
> phrase refuted there may be an AI tell HERE — the R4 gate (ask the corpus
> first) is what actually protects you, and it works from Tier 1.


> The distilled DO/DON'T of how our cited literature actually writes, turned into a checklist.
> `/{{FIELD}}-lit` loads this on every run and checks the author's passage against **§1, §3, §6 and §8**,
> with **§5** as the domain guard and **§4** as the vocabulary to replace flagged wording with.
> Flag only what a section here — or verbatim corpus evidence — supports. No reason, no change.

---


## Contents

- 1. Assert, don't explain (the register's iron law)
  - R1 · Use the corpus's plain verbs — ATTESTED, this is the positive target
  - R2 · Personifying verbs — JUDGMENT, never asserted as a defect
  - R3 · Explanatory glue — JUDGMENT, and the word list is REFUTED
- 2. Lifted phrasing (flag, don't rewrite silently)
- 3. Terminology = the corpus, only
- 4. Field vocabulary — moved to `terms.md` §A
- 5. This paper's theory frame (get it right)
- 6. AI-voice — corpus-refuted only
  - R4 · The gate: nothing is flagged as AI voice until the corpus has been asked
  - R5 · What this section used to ban, and what measuring it did
  - R6 · What survived — measured rare, safe to flag
  - R7 · Still in scope, because they are not lexical
  - R8 · Demotion rule
- 7. Out of scope for this skill
- 8. Sentence-to-sentence connection (cohesion) — rules R9–R11
  - R9 · The join table — N−1 rows, no exceptions
  - R10 · The paragraph verdict — coherence ≠ cohesion
  - R11 · Measurement discipline
  - What survives from the old §8


## 1. Assert, don't explain (the register's iron law)
Scholars ASSERT an established mechanism; they do not re-derive it with connective glue.

**Every rule below carries its measurement.** Counts are from `register-measurements.md`
(149 style-safe papers, 2,308,511 words); rerun `py -3 scripts/measure_register.py` to reproduce
any figure. A rule with no count is a rule nobody can check, and this section used to be all
of those.

### R1 · Use the corpus's plain verbs — ATTESTED, this is the positive target
Make the mechanism or incentive the **SUBJECT**, use **one PLAIN verb**, and let the
**citation** carry the "why." "Plain" ≠ "strong/vivid." The corpus verbs are dry and
repetitive, and the counts are why we call them the register:

`increases` **133 papers** · `reduces` 94 · `affects` 82 · `holds` 71 · `limits` 59 ·
`creates` 51 · `raises` 47 · `lowers` 26 · `induces` 22

`increases` alone is in 133 of 149 papers. Reuse these. If a finance paper would just say
"increases," say "increases."

- ✅ "a corporation can increase its current market value by increasing the risk of the assets in the fund." [Sharpe1976]
- ✅ "The system of required contributions creates an incentive to limit risk taking in pension plans." [Rauh2009]
- ✅ "underpriced pension insurance induces greater risk-taking on the part of the firm." [LoveSmithWilcox2011]

### R2 · Personifying verbs — JUDGMENT, never asserted as a defect
Any verb that personifies or metaphorises a mechanism, policy or quantity is worth
questioning: a mechanism does not *court*, *invite*, *reshape*, *tilt*, *loosen*, *lift*,
*climb*, *retreat* or *strip* anything.

**This check may not be mechanised, and the reason is measured.** English plural nouns are
homographs of third-person verbs, so a pattern over `courts|rewards|loads|strips` counts
nouns. Sampled: `court` has **zero verb uses** in 149 papers — every hit is "bankruptcy
**courts**"; `load` is "**loading** and unloading of property on aircraft" and
"front-**loaded** plans"; `tilt` is "**tilted** toward bonds" and "inverse probability
**tilting**", an estimator; `reward` is the noun in "risks and **rewards**". This is the
same failure `draft-section/references/verb-ladder.md` recorded for `(in)?consistent with`,
where a pattern swallowed the negation and the statistic measured its own opposite.

So: **raise it as a question, with evidence attached.** Run
`py -3 scripts/attest.py "<verb>"` and read the concordance. Test per verb — would Rauh2009 or
AnHuangZhang2013 use this exact verb in this slot? Absent as a verb → offer a R1 whitelist
verb. Present as a technical term → leave it alone.

Only one candidate survived measurement as a genuine absence: **`adjudicate`, 0 hits in 149
papers.** It is in R6 with the other measured-rare items.

- ❌ Purple verb: "the guarantee is a put option whose value **climbs** with the risk a sponsor **loads into** the fund."
  (say: "the value of the put **increases** with the risk of the assets" — flat, like the corpus.)

### R3 · Explanatory glue — JUDGMENT, and the word list is REFUTED
The old rule banned `so`, `since`, `thereby`, `in order to`, `as a result` outright.
Measured, they are ordinary in this literature:

`as a result` **91 papers** · `in order to` **80** · `thereby` **54**

The distinction §1 actually wants is about *whose* logic is being strung together — a real
`because` inside a source-attested clause is fine; the problem is us re-deriving an
established mechanism with our own connectives. That is not decidable by pattern matching,
and the words themselves are not the tell. **Ask whether the sentence is re-deriving
something the citation already carries. Do not flag the connective.**

- ❌ AI padding: "…its gains staying private while its losses fall on the insurer." (restates the
  obvious; a scholar just names the put / the moral hazard and cites.)

## 2. Lifted phrasing (flag, don't rewrite silently)
If the passage reproduces a source's distinctive multi-word signature with only the nouns swapped —
"remains an important, albeit unsettled, empirical question", "is a setting where both X and Y incentives
are likely to be present" — flag it as a plagiarism risk and say which paper it echoes. **Shared field terms**
(risk shifting, risk management, asset allocation, put option, moral hazard) and generic connectives are fine
near-verbatim; do not flag those.

## 3. Terminology = the corpus, only
- Every domain term must survive the **three-test rule** (SKILL.md): word boundary (`\b`), standalone rather
  than a compound prefix, and the same sense in running prose — not a bibliography line.
- Paper-only institutional terms live only in the manuscript → **surface each use** for the author,
  never auto-clear and never silently cut. *This instance's list: manuscript-onboarding slot, empty until
  a manuscript exists. (parent example: segment rate, Schedule SB, prefunding balance.)*
- Flag the vague stand-in and give the precise term the corpus uses — attested, never assumed.
  *(parent examples, pensions — shape only: "the PBGC" not "the insurer"; "mandatory contributions" not
  "required payments"; "sponsors with underfunded plans" not "poorly funded sponsors".)*

## 4. Field vocabulary — moved to `terms.md` §A

**Removed 2026-08-25.** This section was a bare word list covering the same ground as
`terms.md` §A, minus §A's evidence: §A carries `de-risking — w:610` and a verbatim corpus
line; §4 carried `de-risking` and nothing. Two copies of one list, and the copy a reader
was likelier to quote was the one that could not be checked.

**Use `terms.md` §A.** It is the same vocabulary with `w:` counts, `range:` paper counts,
a `ctx:` corpus line, and a cite-key on every row.

Why it drifted is worth recording, because the mechanism is general: Anthropic's skill
guidance notes that a reference reached through *another* reference may be previewed with
`head -100` rather than read whole, "resulting in incomplete information," and requires
references to stay **one level deep from SKILL.md**. §4 pointed at §A, §A carried the
counts, and the counts are what went missing. Keep every reference file one hop from
`SKILL.md`.

## 5. This paper's theory frame (get it right)

**Manuscript-onboarding slot — empty until this field's manuscript exists.** When it does, write
the paper's mechanisms and the confusable neighbours to keep apart, each with a corpus anchor.
The parent's frame is kept below as a SHAPE example only; none of it applies to this field.

*(parent example, pensions:)*
- The conflict is **risk shifting vs risk management** (An-Huang-Zhang: opposite sign on the funding ratio —
  lower funding → MORE risk under shifting [AHZ L62]; lower funding → LESS risk under management [AHZ L79]).
- Risk-shifting mechanism: PBGC put / underpriced guarantee; mandatory contributions are the constraint
  (Rauh2009). Risk-management mechanism: a shortfall must be met from the firm's own cash → distress → safe
  assets (Rauh2009, Smith-Stulz, Froot-Scharfstein-Stein).
- **LDI (Bodie/Treynor duration-matching) is a SEPARATE third mechanism — keep it OUT of the
  risk-shifting-vs-risk-management tension.**

## 6. AI-voice — corpus-refuted only

### R4 · The gate: nothing is flagged as AI voice until the corpus has been asked
**Run `py -3 scripts/attest.py "<phrase>"` BEFORE forming the judgment, not after.** A phrase
carried by **≥3 distinct papers is this literature's register, not an AI tell**, and flagging
it moves the author's prose *away* from the corpus — which inverts the purpose of this skill.

The order matters. This is a gate, not a post-filter: a phrase cleared by the corpus never
becomes a finding in the first place. When the corpus and the instinct disagree, **surface
the disagreement and do not edit.**

### R5 · What this section used to ban, and what measuring it did
Almost the entire old blacklist was refuted by our own corpus:

| was banned as an AI tell | actually in |
|---|---|
| `it is important to note that` | **24 papers** |
| `not only X … but also Y` | **47 papers** |
| `In this paper, we …` | **55 papers** |
| `Moreover,` sentence-initial | **92 papers** |
| `Furthermore,` sentence-initial | **76 papers** |
| `Additionally,` / `Notably,` / `Importantly,` | 37 / 18 / 31 papers |
| `it is worth noting that` | 8 papers |

**Do not re-add any of these from memory.** Full table and method in
`register-measurements.md`; §8 of this file is corrected to match.

This is not a local quirk. `avoid-ai-writing` built a corpus of guaranteed-human prose and
measured its own 112-entry AI-vocabulary table at **0.9× lift** — it fires slightly *more*
often on human writing than on machine writing — with the em-dash rule **inverted** (9.9% of
human documents against 1.9% of machine). Liang et al. (2023), *Patterns* 4(7), gives the
mechanism: detectors flag low-perplexity prose, and over half of non-native-authored TOEFL
essays were misclassified as AI-generated. Constrained, conventional, formulaic phrasing *is*
the definition of a disciplinary register. A "sounds formulaic" heuristic therefore misfires
hardest on exactly the writing this skill exists to imitate.

### R6 · What survived — measured rare, safe to flag
Below the 3-paper threshold with room to spare, across 149 papers:

| item | w: | papers |
|---|---|---|
| `adjudicate` (any form) | 0 | **0** |
| `might potentially` (hedging stack) | 1 | 1 |
| `loosen` (verb forms) | 1 | 1 |
| `retreat` (verb forms) | 2 | 1 |
| `surface` (as `surfaced`/`surfacing`) | 0 | **0** |

These are the only items from the original §1/§6 lists the corpus supports banning.

### R7 · Still in scope, because they are not lexical
These are not word-list items and the measurement above says nothing about them:
- Vague stand-ins for precise nouns (§3) — attested replacements only. *(parent: `the insurer` →
  the PBGC; `funds` → pension assets.)*
- Restating-the-obvious appositives that a citation already carries (§1 R3).
- Bare `This` / `These` with no antecedent — **handled by R9/K9 (`naked-demonstrative`),
  not charged again here**; R7 flags only the vague institutional stand-ins above.

### R8 · Demotion rule
**Any check that has ever produced a false positive against the corpus is demoted from
assertion to question, permanently.** It is raised with its evidence and left to the author;
it is never reported as a defect. Tuning a pattern that fired on real literature just moves
where it misfires — `avoid-ai-writing` reverted three such rules pre-release rather than
tune them, and recorded why.

## 7. Out of scope for this skill
Numbers, claims, and whether a cited paper supports what the passage attributes to it are **not** reviewed
here. Those belong to `/verify-claims` (attribution) and the author (numbers → the manuscript's `main.tex`).
Attribution errors are the ones that sink a paper; say so in the output footer, but do not try to check them
from a style pass.

## 8. Sentence-to-sentence connection (cohesion) — rules R9–R11

**The evidence changed under this section on 2026-08-25 and the numbers here are current.**
Old text cited "126 real joins" from "45 of 165 papers" with topic-chaining defended as a
sampling artefact. All three claims are superseded: `transitions.md` now carries **735 joins
from 144 of 149 style-safe papers (97%)**, and `cohesion-norms.json` measures **57,271
adjacent pairs** across 9,821 recovered paragraphs. What was an assertion is now a number:

- **Topic-chaining IS the default — measured at last: 82.7% of adjacent pairs have no
  sentence-initial connective.** (`cohesion-measurements.md` §B1.)
- **Connectives ride on carriers: 82.1% of connective-opened joins also carry a lexical
  link.** A connective substituting for a carrier is the 1-in-5 minority. (§B2.)
- **Strict stress→topic chaining is NOT the norm: only 46.8% of backward topic links come
  from the previous stress zone.** Grade joins, never binarise them. (§B3.)

The full distilled rule set (the writing canon of Gopen & Swan, Williams, Pinker, Schimel,
Alley, McCloskey, Cochrane, Thomson, Dudenhefer — merged, deduplicated and
corpus-adjudicated) lives in `cohesion-canon.md`: pillars, K1–K15 join rules, P1–P6
paragraph rules, D1–D6 disagreement adjudications, and the verdict vocabulary. **If this
section and the canon file disagree, the canon file wins.** What follows is the operative
compression.

### R9 · The join table — N−1 rows, no exceptions [the cohesion check itself]
A paragraph of N sentences produces **N−1 JOINS rows**. Run
`py -3 scripts/cohesion.py --section <sec> "<paragraph>"` first; it supplies the mechanical
half of every row (grade by antecedent distance, overlap, carrier candidates, connective
openers). The review supplies the semantic half, per row:

- **the relation** — one label from the canon vocabulary (Pinker's fourteen + the four
  economics relations + topic-chain). No label fits, or several fit equally → that IS the
  finding; use the failure vocabulary (`no-carrier`, `asserted-not-earned`,
  `naked-demonstrative`, `mugging`, `enumeration`, `throat-clearing`, …).
- **the carrier** — lexical repetition / transitional phrase / pronoun-or-summary-noun
  (the known-new contract's three; a relation-signalling connective with no other carrier
  is legitimate in ~1 of 5 **connective-opened** joins — which is roughly 3% of ALL joins,
  since only a minority of joins open with a connective at all — but a run of them is not
  this register).
- **the falsifiability test** — "a transition is functional only when removing it would
  hide a real logical relation."

Grades are a ladder, not a bar: STRONG (stress→topic) > GOOD (anywhere in S₁) >
ACCEPTABLE (in-paragraph) > WEAK (earlier in document) > BROKEN. **Never fail an
ACCEPTABLE join for not being STRONG** — the corpus itself chains strictly only 46.8% of
the time. **Structure-gate first** (canon K15): in a TS-D paragraph (point stated, then
developed — the dominant Results shape), hub-links back to S₁ are correct, not a defect.

### R10 · The paragraph verdict — one row, after the join rows [coherence ≠ cohesion]
Pairwise links can all pass while the paragraph rambles (Williams/Dudenhefer). After the
JOINS rows, one PARAGRAPH row answers:
- **topic-string narrowness** — do the N topic zones name a small related set?
- **one point** — state the paragraph's point in one clause; every sentence maps to it or
  the paragraph is two paragraphs.
- **the M8 pair, mandatorily** — cohesion.py names the highest-overlap non-adjacent pair
  and its shared stems. **Read that pair and answer: same argument restated, or
  legitimate term recurrence?** Lexical overlap cannot tell these apart in a register
  built on repetition; only reading can. The percentile does not exempt — the motivating
  failure case sat at P23 and was still a genuine restatement (`same-argument-twice`).

### R11 · Measurement discipline [what the numbers may say]
Percentiles come from `cohesion-norms.json` (section × length-bin cell, coarse fallback;
the output names its cell and n). **Both tails are reportable**: low = candidate break,
high = candidate redundancy/over-smoothness. The numbers PRIORITISE the review's
attention; they never judge. Say "unusual relative to the corpus" — never "less
coherent", "poorly written", or any quality verdict. Grounds: local cohesion indices do
not predict expert coherence judgments (TAACO validation; Crossley & McNamara 2010), the
reverse cohesion effect (McNamara et al. 1996), and over-smoothness being itself an AI
tell. Never recommend adding connectives to raise a number.

### What survives from the old §8 (all consistent with the canon)
- **Every "This / That / These / Such" must attach to a specific prior noun** — a bare
  demonstrative with no antecedent is canon K9 (`naked-demonstrative`), Cochrane's
  "'This' should always have something following it".
- **Two-sided theory contrasts take parallel openers**: "Under risk shifting, … . Under
  risk management, … ." (canon K6 `parallel-item`; attested Bodie, Rauh2009, Treynor,
  HsiehChenFerris).
- **Vary structure, never terminology** (canon D4). Don't cycle
  `However → Nevertheless → Yet` for variety's sake — elegant variation is the defect,
  repetition is the carrier (McCloskey §17/§19).
- The 2026-08-25 correction stands, twice over: the first pass counted these
  line-initial (Moreover 26 papers); the corrected sentence-initial counts are
  `Moreover,` (**92 papers**), `Furthermore,` (**76**), `Additionally,` (**37**),
  `Notably,` (**18**), `Importantly,` (**31**) — **not AI tells in this literature and
  must not be flagged as such** (§6 R4/R5; errata trail in `register-measurements.md`).
