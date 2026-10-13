# provenance.md — how mimic-lit and draft-section were actually built (the recipe this factory replays)

> Reconstructed 2026-08-26 by archaeology over the two parent skills' pipeline
> specs, file headers, shard directories and session logs. Every number below
> was read off disk, not recalled. This file is the factory's ground truth for
> per-tier cost forecasts and for what "done" looks like at each tier.

## The one-line summary

Both skills sit on ONE corpus (165 txt / 159 distinct papers, 2.61M words,
`pdftotext -q`). Everything above the corpus is one of three kinds:

1. **Script-replayable** — has a rebuild command, runs in seconds:
   corpus_meta · register-measurements · cohesion-norms · transitions ·
   chapter-map synthesis · slices · chapter-names · verb-ladder counts ·
   structure-norms · evidence-map · para_numbers.
2. **Model passes** — agents reading under a written spec; the expensive part:
   A2 chapter identification · records (PASS1) · sections/Versions (PASS2) ·
   exemplar tagging.
3. **Hand/canon** — written once, largely field-portable: SKILL.md prose,
   cohesion-canon, structure-canon, registry _why blocks, PASS1/PASS2 specs.

## Measured pass counts (the cost model for Tiers 2–4)

For the parent build (60-paper working sample out of 165 files):

| stage | model passes | granularity | evidence |
|---|---|---|---|
| A2 chapter identification | **8** | 4 waves × 15 papers (~420–530 headings each) + delta/gap/retag/zfix correction rounds | the 8 `a2_out_*.tsv` (473/526/422/430 + 41/9/169/2 rows) |
| A3 adjudication | 5 reads | one per gate mismatch (gate 85 agree / 5 disagree = 94.4%) | chapter-map.md §2 |
| records (PASS1) | **~27** | shards of 8–22 papers per agent per chapter (results 3×16 · intro 7×7 · data 2×~22 · …) | `records/_shards/` file counts + intro G1–G7 groups |
| sections (PASS2) | **≥9** | one whole-record induction pass per chapter → 58 files / 306 Versions | skeleton headers ("Mined from …") |
| exemplar tagging | **~159** | ~20 sentences per paper, three rounds (45→86→165 papers, 266→536→3,266 sentences) | exemplars.md header + 2026-07-31 log |

Scale linearly-ish with corpus size: a 40-paper field ≈ 2/3 of these numbers.

## The two specs that ARE the recipe (carried verbatim into templates/prompts/)

- **PASS1_SPEC.md** (95 lines): plain-language line per paragraph + verbatim
  first sentence, character-for-character including PDF damage; NO tagging
  ("labelling in pass 1 locks the induction into a taxonomy chosen before
  anything was read"); sentence counts must be right (percentiles and the
  uniformity gate are computed from them); `NOT A <CHAPTER>` is a finding.
- **PASS2_SPEC.md** (145 lines): four-field Version blocks (Pattern / Example /
  Use it when / Not this when), attribution `— PaperKey ¶n`, **≥2-paper
  attestation or it is a prose note, not a Version**; nothing tidied, nothing
  invented; optional sections evidence-gated; >25 KB → split into skeleton +
  part files; denominators from the record's own header.

What was NEVER saved and had to be rewritten for this factory (see
templates/prompts/): the A2 wave agent prompt, the taxonomy-induction step
(the parents' "ten jobs" were induced during reading, not pre-declared), and
the exemplar-tagging prompt.

## Order of operations (what depends on what)

```
drop/*.pdf
  └─ ingest → corpus/*.txt
       └─ build_corpus_meta → corpus_meta.yaml (4 denominators, aliases, damage)   [Tier 0]
            ├─ measure_register / build_cohesion_norms / build_transitions        [Tier 1]
            │    └─ register.md numbers · cohesion norms · transitions bank
            ├─ taxonomy induction (MODEL, user approves) → config.jobs             [Tier 2]
            │    └─ a1_headings → a2 waves (MODEL) → build_map → stage_b_slice
            │         └─ slices/<job>/                                             
            │              ├─ PASS1 shards (MODEL) → records/                      [Tier 3]
            │              │    └─ PASS2 per chapter (MODEL) → sections/Versions
            │              │         └─ para_numbers · recount (uniformity) ·
            │              │           measure_structure → typing appendices
            │              └─ build_cohesion_norms (per-section cells, automatic once slices exist)
            └─ exemplar tagging (MODEL) → exemplars.md · verb-ladder counts        [Tier 4]
```

Manuscript onboarding (evidence-map, notes-index, manuscript-state, register
§3/§5, "For this manuscript" slots) is OUTSIDE the tiers — it happens when the
new field gets a manuscript, not when it gets a corpus.

## Known traps, learned the hard way (assert these in every instance)

- pdftotext: use `-q` DEFAULT mode; `-layout` broke formatting on validation,
  a `-raw` repair attempt made one paper worse and was rolled back.
- Extraction damage is a corpus fact, not noise: dropped ligatures (fi/fl),
  lost inter-word spaces, scanned-only files — detect and demote to
  terminology-only/excluded, never silently keep (four-denominator manifest).
  NOTE 2026-10-07: until this date scans were NOT detected (every damage test
  needed >2000 words, and a scan has almost none); ingest's words-per-page
  SCAN flag and build_corpus_meta's `scan_or_empty` verdict now do it.
- Duplicate files: byte-identical pairs exist in real libraries; alias groups
  with a canonical key, never delete (grep-ability of examples depends on it).
- Hand-edits inside generated files get erased by regeneration — anything
  hand-written must live in the GENERATOR (the CurrieGruber alias lesson).
- One shard's crash must not hide later shards; suites assert true negatives
  alongside true positives.
- The corpus stores one paragraph per line; line-anchored regexes undercount
  sentence-initial phenomena 2–9× (the Moreover 26→92 lesson) — always split
  sentences with the shared textseg splitter.
