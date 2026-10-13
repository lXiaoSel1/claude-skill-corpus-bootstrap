> FACTORY NOTE (2026-08-26): carried VERBATIM from draft-section/references/
> pipeline/PASS1_SPEC.md -- the spec the parent records/ were actually built
> under. Dispatch: shard the chapter's slices into groups of 8-16 papers,
> one agent per shard, each emitting its shard file; concatenate shards
> into records/<chapter>.md and keep the shards for provenance. Replace
> chapter/paper names with the new field's. Do not edit the rules below.
>
> FACTORY NOTE (2026-10-07): the parent files the spec names
> (`references/records/intro-read.md`, `records/_superseded/...`) do NOT
> exist in a stamped instance. The format example is
> `prompts/examples/pass1-example-intro-read-excerpt.md` (three papers,
> Chinese, read-only). The economics/pension example lines under "The
> plain-language line" illustrate STYLE only; never borrow their content.
> Paper keys are the instance's corpus keys (e.g. `P08`, `R03`) and may
> start with a digit or contain `-`; copy them exactly.

# Pass-1 record spec — copied from how the Introduction was actually built

This is not a new format. It is the format of
`references/records/intro-read.md`, which is the file the Introduction's 97 Versions were mined
from. Its own header states the rule:

> 这是「经验」本身:agent 把每篇引言从头读到尾,用白话记下每一段在干什么 + 逐字首句。
> **不用任何标签体系** —— 标签是给机器分组用的,这里不分组。
>
> (This is the experience itself: an agent read every introduction end to end and wrote down, in
> plain words, what each paragraph is doing, plus the verbatim first sentence. **No labelling
> system at all** — labels are for machine grouping, and this file does no grouping.)

There is a second, older record file (`records/_superseded/introduction-tagged.md`, 18 papers) that
DOES carry `move:` tags, sentence-level move sequences and join relations. **That is the superseded
round.** Do not imitate it.

---

## Why no labels

Labelling in pass 1 locks the induction into a taxonomy chosen before anything was read. Pass 2
reads the whole record file at once and induces the Versions from it. Pass 1's only job is to
**see accurately and record verbatim**.

---

## The format, exactly

```
### <PaperKey>  <Chapter> N paragraphs [titled `2. Data and Sample` | untitled — <where it starts and ends>]

¶1 <one plain sentence saying what this paragraph is doing — no label, no category, no jargon>
> "<the paragraph's first sentence, copied character for character>"
N sentences

¶2 <...>
> "<...>"
N sentences
```

Nothing else. No move tag. No first-sentence type. No join relation. No sentence-level sequence.

### The bracket after the paragraph count

States how the chapter was delimited, so a later reader can check the boundary:
- `[titled \`4. Empirical tests: Data and methodology\`]`
- `[untitled — starts after the abstract, ends before the heading \`3. Data\`]`
- If the slice looks wrong, say so there and keep going.

### The verbatim rule

Copy the first sentence **character for character**, including PDF-extraction damage:
dropped capitals (`"O n December 9, 1963,…"`), broken ligatures, hyphenation from line breaks,
small-caps rendered as full capitals, stray spaces (`"T rade groups…"`), mojibake.
**Nothing is tidied.** If a sentence is unreadable, quote what is there and add
`[EXTRACTION UNCLEAR]` after it.

This matters because pass 2 copies these strings into the Version files, and every one of them is
later verified by grepping the corpus. A silently repaired quote fails that check.

### The plain-language line

Write what the paragraph **does**, the way you would tell a colleague who has not read the paper.
Concrete beats abstract. Name the thing being discussed.

Good (from the Introduction records, translated):
- "opens on the 1963 Studebaker plant closure and the workers' lost pensions, and runs that
  straight through to how it produced ERISA and the PBGC"
- "switches to Bethlehem Steel's 2001 bankruptcy — same event, completely different outcome —
  and uses numbers to show how much the PBGC absorbed"
- "a roadmap, but it reports each section's conclusion as it goes"

Bad — these are labels wearing a sentence costume:
- "provides institutional background"
- "states the contribution"
- "motivates the study"

### Language

Write the record in **English**. (`intro-read.md` is in Chinese because it was written that way;
the reference layer that is built from it is English, and new records go straight to English.)

---

## Rules

1. **Every paper in the folder.** No skipping.
2. If a slice is not the chapter it claims to be, record
   `### <Key> — NOT A <CHAPTER>` and one line on what it actually is. That is a finding.
3. Count sentences per paragraph and record it. This is what the paragraph-length percentiles and
   the uniformity gate are computed from later, so it must be right.
4. Do not summarise across papers. Do not draw conclusions. Do not group.
   **Pass 2 does that, after reading everything you wrote.**
