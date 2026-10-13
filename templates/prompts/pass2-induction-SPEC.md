> FACTORY NOTE (2026-08-26): carried VERBATIM from draft-section/references/
> pipeline/PASS2_SPEC.md. Dispatch: one agent per chapter, reading that
> chapter's records/ file WHOLE, emitting 00-skeleton.md + part files under
> the >25 KB split rule. The >=2-paper attestation rule is asserted
> mechanically by the instance's check_drift afterwards. Do not edit the
> rules below.
>
> FACTORY NOTE (2026-10-07), substitutions that apply to the rules below:
> 1. "Read `references/sections/introduction/04-design.md`" means the
>    copy at `prompts/examples/pass2-example-introduction-04-design.md`
>    (economics; copy its SHAPE, never its part names or content).
> 2. "Our manuscript" is the instance's manuscript (field-config
>    `manuscript_tex`), NOT the parent's own manuscript. If no
>    manuscript is onboarded, `## For this manuscript` contains exactly one
>    line: "No manuscript onboarded yet -- recommendations deferred to
>    onboarding." Do not invent a manuscript to argue for.
> 3. Corpus counts in the examples (165 papers, 60 introductions, a mathematics
>    `frame`) are the parents'; use this instance's record headers.
> 4. Paper keys may start with a digit or contain `-` (e.g. `P08`,
>    `AGENCY-2019`); attribution is `— <Key> ¶<n>` with the key copied exactly.

# Pass-2 spec — induce the Versions, in the shape the Introduction actually has

Pass 1 read the corpus and wrote down what it saw, with no labels. **Your job is the grouping
pass 1 deliberately refused to do:** read the whole record file, see which ways of doing this
chapter recur, and write each one down as a Version.

The Introduction's eight part files are the specification. Read one before you start —
`references/sections/introduction/04-design.md` is the cleanest example — and copy its shape.

---

## The two things every file must have

### 1. A header block

Says what this part does, where it was mined from (which record, how many papers), and carries
this sentence verbatim:

> Every sentence below is copied verbatim from those records, including PDF-extraction artefacts,
> small-caps renderings, broken drop-caps, stray spaces, and mojibake. **Nothing has been tidied
> and nothing has been invented.**

### 2. `## For this manuscript` — always the LAST section

Three parts, in this order:

1. *One italic paragraph restating what our manuscript is* — its research question, design,
   data and hypotheses in two or three sentences, taken from the manuscript named by
   field-config `manuscript_tex`.
2. **A bold recommendation naming specific Version numbers and where each goes.**

   **If the recommendation defers a class of material to another chapter, name the class and say
   what is NOT deferred.** A rule of the shape *"follow X's placement, not Y's"* reads, to whoever
   drafts from it later, as covering every kind of display in the chapter — and that is how it was
   in fact misread. A mathematics instance's `frame` skeleton carried "follow PaperX1993's placement" meaning
   *defer the displayed theorems*; an introduction came back with its displayed **equations**
   stripped too, because the sentence never said which object it governed. Write the boundary as a
   pair — what moves out, what stays — and back the "stays" half with the layer-E count from
   `structure-norms.json`, so the next reader has a number rather than an inference.
3. **An argument** for why that Version rather than the obvious alternative — grounded in what our
   paper actually contains, quoting one corpus sentence and showing it transposes almost clause for
   clause. Not "use Version 6". An argument a referee could disagree with.

---

## The Version block — exact format

```
### Version 1 · Short label naming the JOB this version does
Pattern        `<Slot> <alternative / alternative / ...>, with <slot> in <slot> (<slot>).`
               — an optional second line refining the pattern in italics.
Example        "First quoted sentence, verbatim, wrapping onto continuation lines indented to
               column 16 if it is long."   — PaperKey ¶3
               "Second example."   — OtherPaper ¶1
Use it when    A precondition the writer can CHECK against their own manuscript.
Not this when  The sibling Version most confusable with this one, and the test that separates them.
```

- Field names left-aligned, content starts at **column 16**.
- **Attribution carries the paragraph number**: `— <PaperKey> ¶<n>` (for the abstract, `S<n>`).
  This is what makes a Version traceable back to the record.
- Version numbers **contiguous from 1**, no gaps, no duplicates.
- 2–4 examples per Version is the norm; one is acceptable only if the corpus genuinely has one.

### What `Use it when` must be

A condition the writer can check. Real ones from the Introduction:

- "You can list at least two features **of the statute itself** — not of your data — that a referee
  could verify by reading the statute."
- "Your estimation sample is **narrower than the sample in your data section**, and you can state the
  restriction rule in one clause that a reader could execute on your panel."
- "You already have the robustness table showing the result survives the alternative measure, **and**
  the limitation is one a referee would raise on page one."

Not "when you want to emphasise the contribution." That is unfalsifiable.

### What `Not this when` must be

Names the confusable sibling **by number** and gives the discriminating test:

- "Version 3 is the confusable neighbour. Test: a Version 1 sentence would still be true if you had
  collected no data at all. A Version 3 sentence names which of *your* units moved and by how much."
- "Version 9. Test: Version 8 argues your measure is **better**; Version 9 concedes it is **worse than
  ideal** and argues it beats the alternative of doing nothing."

---

## Sections between and after the Versions — only if the corpus supports them

These are **not a template to fill**. In the Introduction each appears only where the reading found
something. Include one only if you can point at the evidence.

| Section | Include when | **Which file it goes in** |
|---|---|---|
| `## The split that comes first: <binary>` | The corpus genuinely divides two ways before any Version applies — e.g. whether to preview results at all. Put it FIRST, before the Versions. | **The part file it governs.** Chapter-wide splits go in `00-skeleton.md`. |
| `## The usual order` / `## Where it sits` | Papers converge on a sequence. Give it as a numbered spine traced through one named paper. | **The part file.** |
| `## Paragraph budget` | There is a defensible range. Name papers at each end. | **The part file.** |
| `## Not defaults for an empirical manuscript: <the theory / pricing papers>` | Non-empirical papers do this part differently. Quote them, then say plainly not to import them. | The part file, or `00-skeleton.md` if it is chapter-wide. |
| **A negative-findings section** | **You measured a zero.** See below — this is the highest-value section in the file. | Either; `00-skeleton.md` if the zero is chapter-wide. |

### Where a section goes is not cosmetic — it is the read contract

`SKILL.md` promises: **drafting one paragraph costs `00-skeleton.md` plus exactly one part file.**
So a part file has to be **self-sufficient for writing that part**. Ordering, budget and the
which-Version-first split all answer questions you have *while writing that part*, so they belong
beside the Versions they govern, not in the skeleton.

Measured on the Introduction, which is the specification:

```
## The usual order / Where it sits    in 6 of 8 PART files, 0 in 00-skeleton.md
## Paragraph budget                   in 1 of 8 PART files, 0 in 00-skeleton.md
## The split that comes first         in 4 of 8 PART files
```

`00-skeleton.md` carries only what is true **across** the parts: the arc, the router, the
chapter-wide length distribution, corpus-wide disagreements, chapter-wide zeros, and
`For this manuscript`.

**Test before you place a section:** *if someone opened only this part file and wrote the part, would
this section have been needed?* Yes → part file. Only useful when comparing parts → skeleton.

### The negative-findings section

Not "we did not find X". Three parts:

1. **The zero, counted.** "The machine-learning formula `we make the following contributions` appears
   **zero times** in the 165-paper corpus and zero times across the 60 introductions read here."
2. **What the corpus writes instead, by axis.** The Introduction's version lists three: the grammatical
   subject is a paper-noun not a bare "we"; the quantifier is vague not cataloguing; the contribution is
   always *to* something named.
3. **The nearest real form**, and why the absence is systematic rather than accidental.

---

## Hard rules

1. **Nothing invented.** Every Version must be attestable in **≥2 papers** in the record file. One-paper
   observations go in a prose note, not a Version.
2. **Quotes are copied from the record, character for character.** The records preserve extraction
   damage on purpose; preserve it again. A tidied quote fails the corpus grep that verifies this file.
3. **Do not import the Introduction's part names.** `opening`/`tension`/`handoff` are introduction
   vocabulary. Name the jobs this chapter actually does, from what you read.
4. **Denominators come from the record file's own header**, never 60.
5. Write **pure English**. No CJK characters anywhere in the output.

## Size

If the finished file exceeds **25 KB**, split it into `<chapter>/00-skeleton.md` (arc, a position table
routing to the parts, measurements) plus `<chapter>/01-<part>.md …`, exactly as the Introduction is
split. Under 25 KB, keep it as a single `<chapter>.md`. **Measure, do not predict.**
