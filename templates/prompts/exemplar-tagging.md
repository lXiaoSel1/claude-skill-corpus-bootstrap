# exemplar-tagging.md — Tier 4: sentence-level move tagging

> Reconstructed from exemplars.md's own header and quota discipline (the
> prompt was never saved). Parent scale: ~20 sentences/paper, 3,266 sentences
> across 159 papers, three rounds. One agent per ~10 papers is a comfortable
> shard.

## The 8 move labels (shared vocabulary — keep EXACTLY these)

`opener · stakes · theory-tension · mechanism-claim · methods · results ·
contribution · gap`

These are the sentence-level rhetorical moves, shared between the -lit
instance's exemplars and the -draft instance's TAGGED measurement layer. They
are deliberately coarser than the chapter taxonomy and are field-invariant in
name; what changes by field is which sentences instantiate them.

## Agent prompt (fill {braces})

You are building the move-tagged exemplar bank for {field}. Input: the corpus
files for papers {list}.

For each paper, select up to ~20 sentences that are clean, representative
instances of the 8 moves, spread across moves (not 20 openers). Rules:

1. **Verbatim.** Copy character-for-character, including PDF damage. A
   sentence you had to repair is a sentence you skip. Three repairs that do
   NOT look like repairs, all caught by `build_exemplars.py` on the first
   field this factory was run on:
   - **Dropping a bracketed citation** from mid-sentence (`the Mountain Pass
     Theorem [7] except possibly` copied as `the Mountain Pass Theorem
     except possibly`). The citation is part of the sentence.
   - **Unicode normalisation.** One corpus wrote `=` followed by a combining
     solidus (U+0338); the tagger copied the precomposed `≠` (U+2260). It
     renders identically and is a different string — and where the extractor
     has LOST the slash, "fixing" it inverts the claim.
   - **De-hyphenating a line break** (`ap-
proaches` → `approaches`).
     Rejoining wrapped lines at a word boundary with one space changes no
     characters and is fine; removing the hyphen is repair.

1a. **Marked omission is not repair.** Where a sentence runs into a displayed
   equation, quote the prose and close with `[displayed equation omitted]`,
   the same convention the Tier-3 records use; `[EXTRACTION UNCLEAR]` where
   the extraction is unreadable. Without this rule a field whose sentences
   habitually end in a display loses that move almost entirely — measured:
   the first mathematics-instance shard returned **4 openers from 8 papers** because in
   that literature the opening sentence's grammatical object *is* the
   displayed equation. That is a fact about the tagging rule, not about the
   literature, and it is the kind of artefact that later reads as evidence.
2. Quota discipline: if a paper genuinely yields fewer than 20 usable
   sentences, take what is real and mark the section `(only N usable)` —
   quality over quota, and the shortfall is a recorded fact.
3. Skip: bibliography lines, table debris, footnotes, sentences broken by
   extraction (unless the break is trivial and marked).
4. Format, one line per sentence:
   `- **[move]** "verbatim sentence" — PaperKey`
5. One `## PaperKey` section per paper, in input order. A paper with zero
   usable sentences still gets its section header plus `(only 0 usable)` —
   absence must be visible, not silent.

## After all shards return

Concatenate into `references/exemplars.md` with the standard header (count
tally per move, per-paper section count), record the totals in
`registry.json` (`exemplars.sections`, `tagged_sentences`), and let
check_drift assert them from then on. Watch for BOM/zero-width characters at
section boundaries — a U+FEFF once made 159 sections count as 158.
