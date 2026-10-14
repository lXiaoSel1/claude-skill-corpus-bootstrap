# structure-canon.skeleton.md -- the rule frame for {{FIELD}}'s structure-canon.md

> **What this file is.** The rule frame of the parent build's structure canon (an
> empirical economics and finance corpus, 17 writing guides), with every quotation
> removed. It is the INPUT of Tier 4's drafting pass (`prompts/structure-canon.md`),
> which writes `references/structure-canon.md` for {{FIELD}}: each rule below gets
> quotes from THIS field's guides in `canon-sources/` (pointer `` `<key>.txt:<line>` ``
> plus the words in `*"…"*`), or is marked as having no source here.
>
> Rule IDs are fixed: the -draft SKILL.md refers to Q3, Q5, Q6, Q7 and D7, and the
> router to the §5 vocabulary. `Parent source` names the guide the parent quoted:
> a lead for where to look, not a requirement. `parent-econ:` is the parent's corpus
> verdict, an illustration only; every measurable rule starts this field at
> `corpus: TO-MEASURE`. Chapter names in the parent's text (introduction parts,
> `empirical-strategy/05-assumption`, `data-sample/`) are economics' jobs: map them
> to this field's `jobs` in field-config.yaml, or say the rule has no home here.

## §1 The five pillars

1. **Punchline first, at every scale.** Put the main result up front and explain it
   afterwards; nothing comes before the main result that a reader does not need to
   understand it. Parent source: Cochrane 2005 (two passages).
   QUOTE: … · `corpus: TO-MEASURE` · parent-econ: supported (a fifth of the introduction is results).
2. **Moves are typed, not just ordered.** Each move of a section, and each step
   inside a move, is obligatory, optional or rare, not simply present or absent.
   Parent source: Swales 2004's revised move table (via Suryani et al. 2014).
   QUOTE: … · `corpus: TO-MEASURE` · parent-econ: MEASURED, no move reached 95%.
3. **Long introductions cycle; short ones don't.** In a long introduction moves
   repeat (for example 1-2-3-4-2-3-4); a short one runs once. Parent source:
   Swales' recycling arrow; a genre analysis of economics introductions.
   QUOTE: … · `corpus: TO-MEASURE` · parent-econ: CONFIRMED, length-gated.
4. **The published register is not meta-heavy.** Summary, outline, anticipation
   and announcement are a draft habit; published papers carry little of it.
   Parent source: McCloskey 1985; Cochrane 2005 on previews and recalls.
   QUOTE: … · `corpus: TO-MEASURE` · parent-econ: meta-sentence share median 1.5%, P90 2.5%.
5. **Composition rules are not revision rules.** Paragraph- and essay-level rules
   bind when drafting; sentence rules at final revision. Parent source: McCloskey 1985.
   QUOTE: … · `corpus: n/a (meta-rule)`.

## §2 Section-level rules S1–S14

**S1 · Results belong in the introduction, at scale.** Several paragraphs of the
introduction report results, so a reader can cite the paper after reading it.
Parent source: Evans (development economics introductions). QUOTE: … · `corpus: TO-MEASURE` ·
parent-econ: median 23% of introduction paragraphs.

**S2 · A roadmap paragraph is optional.** When present, it names this paper's own
landmarks, not boilerplate. Parent source: Cochrane, Bellemare, Head (they disagree; see D1).
QUOTE: … · `corpus: TO-MEASURE` · parent-econ: 48% of introductions.

**S3 · Where the question is stated.** Advice that the "this paper addresses…"
sentence comes by the second or third paragraph. Parent source: Head, "The
Introduction Formula". QUOTE: … · `corpus: TO-MEASURE` · parent-econ: refuted as a norm, kept as advice.

**S4 · How many antecedents the introduction discusses.** Parent source: Bellemare
(five to ten closest studies) against Cochrane (two or three); see D2.
QUOTE: … · `corpus: TO-MEASURE` · parent-econ: median 3, leans Cochrane.

**S5 · Previews and recalls close to zero.** Forward and backward references
("as we will see", "recall that") signal poor organisation. Parent source: Cochrane.
QUOTE: … · `corpus: TO-MEASURE` · parent-econ: median 0.74 per 10k words.

**S6 · About three contributions, late in the introduction.** Parent source: Head.
QUOTE: … · `corpus: TO-MEASURE` · parent-econ: contribution move in 89% of papers, late and fixed.

**S7 · Introduction length.** An upper limit on the introduction. Parent source:
Cochrane (pages). QUOTE: … · `corpus: TO-MEASURE (paragraphs, not pages)`.

**S8 · Conclusion: a short restatement, no rehash of the introduction.** Parent
source: Cochrane; Thomson; Bellemare. QUOTE: … · `corpus: unmeasured (judgment)`.

**S9 · Threats to the design, in a fixed order.** A drafting spine for the section
that defends the method (in the parent: reverse causality, unobserved
heterogeneity, measurement error). Parent source: Bellemare. Map to this field's
method section, or mark as not applicable. QUOTE: … · `corpus: unmeasured`.

**S10 · Data section order.** Source, collection, sample, N, attrition, missing
data before variables; variables before descriptives. Parent source: Bellemare.
QUOTE: … · `corpus: unmeasured`.

**S11 · Descriptive statistics get a few sentences of prose.** Parent source: Bellemare.
QUOTE: … · `corpus: unmeasured`.

**S12 · Define before use.** Write the body so a reader who knows only what has
been defined can follow it. Parent source: Shapiro, "Four Steps". QUOTE: … ·
`corpus: unmeasured (judgment; a review question)`.

**S13 · The abstract drafted from the introduction.** First sentences of hook,
question and contribution, polished. Parent source: Bellemare. QUOTE: … · `corpus: unmeasured`.

**S14 · Part presence lower bounds, per chapter.** Counts of papers attesting each
part, from the Versions; lower bounds, never absence evidence. No guide source,
by design (keep this rule as written; it is not `secondary`):
`corpus: TO-MEASURE (measure_structure.py)`.

## §3 Paragraph-completeness rules Q1–Q7

The claim ledger certifies every sentence is sourced; these certify that a
paragraph's argument closes.

**Q1 · Context, content, conclusion.** First sentence gives context, the body the
content, the last sentence the conclusion; a reader should never ask "why was I
told that?" or "so what?". Parent source: Mensh & Kording 2017. QUOTE: … ·
`corpus: unmeasurable mechanically; forced by the PARA output slot`.

**Q2 · A results paragraph asks a question and answers it.** Parent source: Mensh &
Kording (rule 7). QUOTE: … · `corpus: judgment`.

**Q3 · Warrant: why does this evidence license this claim.** The argument's
claim, reason, evidence, warrant and acknowledgement (Booth, Colomb & Williams;
book not fetched, so `secondary` unless a guide here states it). Enters the ledger
as a column, never a gate. QUOTE: … · `corpus: judgment`.

**Q4 · One point per paragraph; close a topic before opening the next.** Parent
source: McCloskey; Schimel (secondary). QUOTE: … · `corpus: judgment`.

**Q5 · The paragraph-string test, at every level.** Summarise each paragraph in one
sentence; the string of sentences must make sense; repeat for subsections and
sections. Parent source: Thomson 1999. QUOTE: … · `corpus: judgment (--outline)`.

**Q6 · Outline before drafting, one sentence per planned paragraph.** Parent
source: Mensh & Kording (rule 9). QUOTE: … · `corpus: device (--outline)`.

**Q7 · The promise contract.** The final introduction is a contract with the
reader; every promise in it is discharged in the body. Parent source: Shapiro,
"Four Steps" (step 4). QUOTE: … · `corpus: device (promise ledger)`.

## §4 Canon disagreements, adjudicated by the corpus D1–D7

For each, state the guides' positions with quotes from this field's guides (where
they take a position), then `corpus: TO-MEASURE` until measure_structure.py runs.

**D1 · Roadmap: never, always, or most of the time.** (Cochrane, Bellemare, Evans.)
**D2 · Antecedents: two or three, or five to ten.** (Cochrane, Bellemare.)
**D3 · A deadline for stating the question.** (Head.)
**D4 · Obligatory moves as binary presence.** (Swales.)
**D5 · One linear pass or cyclic structure.** (Swales; genre analyses.)
**D6 · Is signposting a disease or a published norm.** (McCloskey; Cochrane.)
**D7 · "Spurn the received outline" against a corpus-induced Versions system.**
(McCloskey.) The tension is recorded, not resolved: the reference layer is
descriptive (what published papers did) and the uniformity gate keeps corpus
conformity from producing uniform prose. `stance recorded; no rule emitted`.

## §5 The typing vocabulary the router reports

- **typing**: `obligatory` (≥95% presence) · `optional` (40–95%) · `rare` (<40%).
- **position**: mean normalised position with sd; `fixed` (sd < 0.25) · `mobile`.
- **cyclicity licence**: in a long introduction a re-entry into a part already
  used is allowed when the corpus shows it; in a short one it is flagged.
Thresholds are re-measured for {{FIELD}}: `corpus: TO-MEASURE`.

## §6 Sources

List the guides actually quoted, by key, with their `_manifest.md` row; name the
guides that were secondary (not on disk) and say that no hard rule rests on them.
