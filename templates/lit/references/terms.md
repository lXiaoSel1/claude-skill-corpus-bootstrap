# terms.md — the term cache ({{FIELD}} instance; empty at stamp time)

> Denominator: quote `corpus_meta.yaml`'s terminology_safe, never the raw file
> count. Rows are written ONLY via `py scripts/cache.py add` -> candidates.md
> -> human review -> `cache.py promote`. The three-test rule (word-bounded ·
> standalone · same sense in running prose) gates every promotion.

## Section A — corpus-attested (safe to keep)

(empty — grows from reviewed candidates)

## Section B — paper-only or different sense (surface every time)

(empty — fills during manuscript onboarding)

## Section C — negative cache (refuse instantly, with reasons)

(empty — every refusal records its evidence: w:, range:, and why the hits fail
the three tests)
