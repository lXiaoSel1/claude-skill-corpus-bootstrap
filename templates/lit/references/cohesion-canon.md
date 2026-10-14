# cohesion-canon.md — the writing canon on sentence-to-sentence flow, distilled and corpus-adjudicated

> **STAMPED-INSTANCE NOTE ({{FIELD}}).** This file is carried from the parent
> economics/finance build. The RULES are the cross-disciplinary canon
> (Gopen & Swan, Williams, Pinker, Schimel, McCloskey, known-new contract) and
> travel as-is. **Every number and every corpus verdict below is the PARENT
> corpus's** (149 style-safe finance papers) — a reference value, not this
> field's. Tier 1 re-measurement (build_cohesion_norms + measure_register)
> replaces them; until then, statuses tagged TO-MEASURE mean exactly that.

> Distilled 2026-08-25 from two survey passes: the scientific-writing canon
> (Gopen & Swan 1990 · Gopen's *Litigation* series · Williams *Style* · Pinker
> *Sense of Style* ch.5 · Schimel *Writing Science* · Alley · the known-new
> contract literature) and economics' own guides (McCloskey *Economical
> Writing* · Cochrane 2005 · Thomson JEL 1999 · Dudenhefer · Bellemare ·
> Nikolov · the RFS/JF/JFE joint editorial).
>
> **Every rule below carries a corpus status.** This skill's iron law does not
> exempt authorities: a canon rule the corpus contradicts is recorded here as
> `refuted` and stays out of the checker. The adjudication numbers come from
> `cohesion-norms.json` (149 style-safe papers, 9,821 recovered paragraphs,
> **57,271 adjacent sentence pairs**); rebuild with
> `py -3 scripts/build_cohesion_norms.py`.
>
> Tags: **[M]** mechanical (scripts/cohesion.py computes it) · **[P]**
> positional (script supplies the zones, the review judges) · **[S]** semantic
> (the review judges; R9/R10 force the judgment to be recorded).

## Contents

- §1 The five pillars (both traditions converge)
- §2 Join-level rules K1–K15
- §3 Paragraph-level rules P1–P6
- §4 Canon disagreements, adjudicated by the corpus (D1–D6)
- §5 The verdict vocabulary
- §6 Sources

---

## §1 The five pillars (both traditions converge — highest confidence)

1. **Tail-to-head linkage.** Gopen (*Litigation* #18, "To Move Forward, Link
   Backward"): announce, *as soon as possible*, how the new sentence connects
   backward. McCloskey §17 states the same schema as **(AB)(BC)(CD)** —
   "transitive writing" — against the failure form (ABZYX)(MNOP), which is
   "probably nonsense". `corpus: TO-MEASURE (parent-econ verdict: MEASURED (57,271 pairs))` — the join-grade
   histogram: STRONG 20.9% · GOOD 27.3% · ACCEPTABLE 36.0% · WEAK 2.4% ·
   BROKEN 13.4%. So **86.6% of corpus joins carry a mechanically visible
   carrier** — the rule describes real practice — but BROKEN is a minority,
   not a "rare tail": the K1 three-carrier test is a FLOOR, and part of that
   13.4% is legitimate semantic linkage (synonymy, inference) the mechanical
   layer cannot see. This is why a BROKEN? grade is a candidate for the
   review, never an automatic verdict. (An earlier version of this entry
   claimed the distribution showed something before the distribution existed;
   the histogram in cohesion-norms.json now backs every word.)

2. **Three licit carriers of the backward link** (known-new contract):
   (a) lexical repetition or a derived form; (b) a relation-signalling
   transitional phrase; (c) a pronoun or summary noun phrase. A pure overlap
   metric false-negatives on (b) — which is why every JOINS row records
   *which* carrier it found. `corpus: TO-MEASURE (parent-econ verdict: confirmed)` — 17.3% of corpus pairs open
   with a connective, and those are real joins.

3. **Repetition is the carrier, not a defect.** McCloskey: "you *must* repeat
   them to link sentences"; "English achieves coherence by repetition." Alley
   and Schimel agree for scientific prose; elegant variation is the defect.
   **Never flag a repeated key term across a join.** `corpus: TO-MEASURE (parent-econ verdict: confirmed)` —
   and this is also what licenses lexical overlap as a valid metric in this
   register (it would not be in literary prose).

4. **Two-tier verdict.** Williams/Dudenhefer: pairwise cohesion can pass while
   the paragraph rambles (the Sayner-snowmobile passage: every sentence linked,
   topic drifting throughout). So: N−1 join verdicts **plus** one paragraph
   verdict, and a paragraph failure is never charged to an individual join.
   `corpus: unmeasurable (design principle)`.

5. **Principles, not rules.** Gopen & Swan's own caveat: mechanical
   application produces bad prose "much like the pedant who never split an
   infinitive." Every verdict is advisory with a severity; no hard gates.
   Reinforced by the validity literature: local cohesion indices do not
   predict expert judgments, and the reverse cohesion effect makes
   "maximise overlap" empirically wrong. `corpus: n/a (meta-rule)`.

---

## §2 Join-level rules (K1–K15)

**K1 · Old information opens the sentence** [M+P]
S₂'s topic zone (first ≤7 tokens) must carry one of the three §1.2 carriers.
All three absent = candidate `no-carrier`. (G&S principles 4 & 6; Williams
"begin sentences with information familiar to your readers"; Gopen REA;
McCloskey E1.) `corpus: TO-MEASURE (parent-econ verdict: confirmed)` — the checker computes this as the join
grade in every JOINS row.

**K2 · Grade by antecedent distance, never binary** [M]
STRONG = antecedent in S₁'s stress zone · GOOD = anywhere in S₁ · ACCEPTABLE
= elsewhere in the paragraph · WEAK = earlier in the document · BROKEN? =
nowhere. **Do not fail an ACCEPTABLE join for not being STRONG.**
`corpus: TO-MEASURE (parent-econ verdict: confirmed, and the strict version refuted)` — only **46.8%** of
backward topic links come from the previous stress zone (D1 below).

**K3 · The link must arrive early** [P]
First backward-referring token before the main verb; later = "late link",
weak pass. (Gopen #18: the reader has already committed and spent energy.)
`corpus: unmeasurable without a parser — review judges from the zone split`.

**K4 · S₁ must end on something worth picking up** [P+S]
A stress zone holding a hedge, a bare citation, a date, or only-given
material wastes the position the next sentence should launch from. (G&S
principle 2; Gopen calls the wasted stress position the single greatest cause
of ineffective professional writing; Schimel "endings are always power
positions"; McCloskey p.211 "dump less important things in the middle".)
`corpus: unmeasurable (semantic)`.

**K5 · S₂ must end on something new** [M+P]
Stress zone that is all given = no payload, "cohesive but inert". (Williams
"end sentences with information your readers cannot anticipate"; Pinker
"given always precedes new".) `corpus: unmeasurable mechanically — flagged by
the review when a JOINS row shows total overlap`.

**K6 · Name the relation — one of eighteen** [S]
Pinker's fourteen: similarity · contrast · elaboration · exemplification ·
generalization · exception-after · exception-before · sequence(before-after)
· sequence(after-before) · result · explanation · violated-expectation ·
failed-prevention · attribution. Economics adds four: **instantiation /
generalization-move** (Thomson's general↔particular alternation) ·
**premise→inference** (Thomson p.176) · **operation→justification**
(Cochrane: describe first, explain second) · **parallel-item** (Thomson:
same-job sentences share a frame). Pinker's definition makes the list a
verdict: "a coherent text is one in which the reader always knows which
coherence relation holds between one sentence and the next." **No relation
fits, or several fit equally → that is the finding.**
`corpus: unmeasurable (the review's central judgment, forced by R9)`.

**K7 · Connective necessity** [S]
If the K6 relation is not recoverable without a connective, one is required
(Pinker: "when in doubt, connect"). `corpus: context-dependent`.

**K8 · Connective accuracy — the fake-join detector** [M+S]
A sentence-initial connective must (a) match the K6 relation that actually
holds and (b) ride on a real carrier. Connective with neither = McCloskey's
"clanking machinery", verdict `asserted-not-earned`. (Williams' illusory
cohesion; Alley's "transitions that make no transition".)
`corpus: TO-MEASURE (parent-econ verdict: MEASURED — 82.1% of connective-opened corpus joins also carry a
lexical link. A connective-only join is the 17.9% minority: legitimate,
but the below-median pattern; three in a row is not this literature.)`

**K9 · Demonstrative presupposition** [M]
Sentence-initial `This/These/Those/Such` (and `The` + noun) presupposing an
antecedent that does not exist. Cochrane: "'This' should always have
something following it" — and the noun that follows must have a referent.
(Pinker: articles are given/new markers.) `corpus: TO-MEASURE (parent-econ verdict: confirmed as a norm —
anaphoric openers run at ~0–25% of sentences (P90 by bin); the checker
reports the rate and the review resolves each antecedent.)`

**K10 · Elegant variation across the join** [M]
S₂ renaming S₁'s entity with a synonym instead of repeating the term. In this
register the repeat is correct (§1.3); the synonym is the defect. McCloskey
§19: "use one word to mean one thing." Polyptoton (same root, different
form) is a *valid* link, not variation — the stemmer treats it as identity.
`corpus: TO-MEASURE (parent-econ verdict: confirmed by register practice; detection is judgment plus attest.py
on the suspect synonym)`.

**K11 · Linked but not advancing** [M+P]
Topic-to-topic recurrence that ignores every stress position, in a
chain-shaped paragraph = Schimel's "list of ideas that don't flow". **Gated
by K15**: in a TS-D paragraph, hub-linking to S₁ is correct.
`corpus: TO-MEASURE (parent-econ verdict: gate confirmed necessary)` — finance Results paragraphs are
predominantly TS-D-shaped; ungated K11 would mass-flag them.

**K12 · No preview, no recall** [P]
"As we will see in Table 6", "Recall from section 2" across a join =
ordering failure, not a transition (Cochrane: "previews and recalls are a
good sign of poor organization"; McCloskey §12; Thomson's no-look-back).
Verdict `look-away`. `corpus: TO-MEASURE (parent-econ verdict: unmeasured (rare; judgment))`.

**K13 · No mugging** [S]
S₂ may not land "Therefore…"/"These results suggest…" whose premises are not
on the table (Thomson: "I feel as if I have been mugged"). Verdict
`mugging`. `corpus: unmeasurable (semantic)`.

**K14 · Delete-test for throat-clearing** [S]
Delete S₁ and re-read; if the paragraph loses nothing, S₁ was
throat-clearing and the S₁→S₂ join is spurious (Cochrane's own worked
example). Verdict `throat-clearing`. `corpus: unmeasurable (semantic)`.

**K15 · Structure gate — classify before judging** [S]
TS-D/LD paragraph (point stated, then developed): sentences legitimately
hub-link back to S₁. OCAR/LDR paragraph (builds to its point): sentences
chain stress→topic. Apply K2's STRONG preference and K11 only in the chain
case. (Schimel.) `corpus: TO-MEASURE (parent-econ verdict: confirmed as necessary by the D1 measurement —
46.8% strict-chaining means the corpus mixes both shapes)`.

---

## §3 Paragraph-level rules (P1–P6)

**P1 · One point per paragraph** [S] — McCloskey §14: "The paragraph should
have a single point." State it in one sentence; every sentence must map to
it. Two points = a disguised paragraph break at one of the joins.

**P2 · Topic-string narrowness** [M+P] — Williams' underline-the-first-seven
diagnostic, Dudenhefer P6: the N topic zones must name a small related set.
The licensed escape: an opening outside the set is legal **iff** it picks up
the previous sentence's stress zone (Williams' two-stage test — this is the
join-table grade doing double duty).

**P3 · The sentence-string test** [S] — Thomson p.159: summarize each
sentence in a clause; the string must read as an argument. (The recursive
version of his paragraph-string test.)

**P4 · Anti-listy** [M+S] — Bellemare: descriptive statistics must tell a
story, not enumerate means; Cochrane: "'Table 5 shows summary statistics'
(period) is not ok." Three-plus consecutive joins carrying only
"and another number" = verdict `enumeration`. **This is the user-goal rule:
a paragraph of disconnected sentences is exactly an enumeration.**

**P5 · The M8 pair is a mandatory adjudication** [M→S] — the script names the
highest-overlap non-adjacent pair and its shared stems; the review MUST read
that pair and answer: same argument restated, or legitimate term recurrence?
Lexical overlap cannot tell these apart in a register where repeating terms
is the norm (§1.3) — only reading can. **Measured on the motivating case:**
the redundant pair (S1↔S6, sharing state-level/panel/counties/risk) sat at
P23 — *typical* overlap for a conclusion paragraph — so percentile alone
would never flag it. The slot exists because the number cannot.

**P6 · Frame persistence** [S] — McCloskey's cub-reporter rule: "the third
damn well better follow from the first and second." Tense, person, register
and metaphor set at join 1 hold through the paragraph; verdict `frame-break`.

---

## §4 Canon disagreements, adjudicated by the corpus (D1–D6)

**D1 · Strict stress→topic vs any-prior antecedent.**
Schimel demands the chain; Wilke/G&S/Williams allow any prior. **Corpus:
46.8% of backward topic links come from the previous stress zone.** The
strict rule would flag the majority of real joins in this literature →
Schimel's version `refuted` as a requirement, kept as the STRONG grade.

**D2 · Is repeating the topic good (Williams) or a list (Schimel)?**
Both, depending on paragraph shape → K15 gate. No corpus number can settle a
question that is structure-conditional; the gate is the adjudication.

**D3 · Connectives: "when in doubt, connect" (Pinker) vs "clanking
machinery" (McCloskey).**
They answer different questions — recoverability vs substitution. Merged
rule = K7 + K8. **Corpus: 17.3% of joins open with a connective, and 82.1%
of those also carry a lexical link.** So this literature uses connectives
sparingly and almost always *on top of* a carrier — McCloskey describes the
practice, Pinker describes the floor. Word-list bans stay refuted
(`Moreover` 26 papers, `not only…but also` 47 — register-measurements.md).

**D4 · Repetition vs variation.** Vary *structure*, never *terminology*.
`corpus: TO-MEASURE (parent-econ verdict: confirmed)` (§1.3). Bonus: this is what makes overlap a valid metric
here.

**D5 · What is the topic — grammatical subject or first words?**
Operationalized as tokens 1..min(7, main-verb−1); post-colon/semicolon
clauses count as their own topic/stress pairs. (Williams' psychological
subject wins over the grammatical one; no parser needed.)

**D6 · Scope.** Williams' clean split: cohesion is pairwise, coherence is
passage-level. N−1 join rows + 1 paragraph row; neither substitutes for the
other. `design principle, adopted as R9/R10`.

---

## §5 The verdict vocabulary (used by the JOINS table and R9/R10)

**Relations (K6):** similarity · contrast · elaboration · exemplification ·
generalization · exception-after · exception-before · sequence ·
result · explanation · violated-expectation · failed-prevention ·
attribution · instantiation · premise→inference · operation→justification ·
parallel-item · topic-chain

**Failure labels:** `no-carrier` · `asserted-not-earned` ·
`elegant-variation` · `naked-demonstrative` · `inverted-pair` · `look-away`
· `mugging` · `enumeration` · `throat-clearing` · `linked-but-not-advancing`
· `frame-break` · `cohesive-but-incoherent` · `same-argument-twice` (the P5
verdict)

---

## §6 Sources

Gopen & Swan, "The Science of Scientific Writing", *American Scientist* 78
(1990) — Tufts mirror `cs.tufts.edu/comp/105-2015s/readings/sci.html` ·
Gopen, *Litigation* #18 "The Progress of Thought: To Move Forward, Link
Backward" · Williams, *Style: Toward Clarity and Grace*, Lesson 5 · Pinker,
*The Sense of Style*, ch. 5 "Arcs of Coherence" · Schimel, *Writing Science*
(OUP 2012) · Alley, *The Craft of Scientific Writing*, "Being Fluid" ·
known-new contract: GMU/UNR/LAVC writing-center formulations after Vande
Kopple and Clark & Haviland · McCloskey, "Economical Writing", *Economic
Inquiry* 23 (1985) 187–222 · Cochrane, "Writing Tips for PhD Students"
(2005) · Thomson, "The Young Person's Guide to Writing Economic Theory",
*JEL* 37 (1999) 157–183 · Dudenhefer, *A Guide to Writing in Economics*
(Duke EcoTeach) §4 · Bellemare, "How to Write Applied Papers in Economics"
(2020) · Nikolov, IZA DP 15057 · Green, O'Hara & Schwert, "Joint Editorial:
Advice for Authors", *RFS* 15 (2002) — the economic price of unpolished
prose, cited as this checker's reason to exist.
