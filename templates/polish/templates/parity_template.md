# <section key> <title>: revision and checks (<date>)

Steps a–j of {{FIELD}}-polish. Section: `<key>` (<file>:<first>–<last>). Baseline: snapshot `<name>`.

## Metrics (before | after)

| measure | before | after |
|---|---|---|
| sentences | | |
| words per sentence, median | | |
| sentences over max_words (<N>) | | |
| sentences per paragraph | | |
| numbers / cite keys / page comments (trial_diff) | | MATCH / MATCH / MATCH |

## b. Sweep (FOCUS)

Recurring 0-paper frames, one-off frames, 0–2-paper words, long sentences, as listed. Positive controls: all CAUGHT? (paste the lines)

## e. Rare words and terms

| key | draft wording | source (quoted, with page) | verdict: source term kept / own wording replaced |
|---|---|---|---|

## c, d2. Frames and openers

Counts are from `attest.py --scope style` (N = the style-safe papers).

| candidate rejected | papers (style, N=<style_safe>) | used instead | papers (style) |
|---|---|---|---|

Rule-2 checks that could not be met (rule 2c: no attested phrase with the same sense; the sweep's FOCUS coverage line says how often to expect it), and what was done instead:

Openers (opener_check): each paragraph's opener and leading connective, its corpus count, the verdict.

## d. {{FIELD}}-lit

TERMS (scope=term, N=<terminology_safe>) and REGISTER (scope=style) blocks pasted as returned. JOINS: every join as cohesion_loop.py prints it, each WEAK / BROKEN one with its verdict; the M8 pair of each paragraph adjudicated. Terms cached with cache.py, or listed here when the lit skill is read-only.

## f. Section G

| § | sentence | problem | fix |
|---|---|---|---|

## h2. Changed meanings checked against the source

Every sentence sent_diff shows as changed in meaning: the source line it now rests on. New wording attested (papers).

## Left to the author

Line, question, the evidence for each side.

## i. Compile and counts

Pages; LaTeX warnings 0; BibTeX warnings 0; counts.py OK (cited keys / page comments / bibitems).
