# structure-canon.md — Tier 4: draft the field's structure canon from its writing guides

> The parent's canon was written by hand from 17 guides. This prompt lets one
> agent draft it for a new field from the guides the user collected
> (`canon_ingest.py` put them in `canon-sources/`). The output is checked by a
> script, not by trust: every quotation must be found at its line pointer.

## Before you start (the session that dispatches the agent)

- Ask the user first: this pass reads the guides and costs tokens. One measured
  run (17 guides, 151,547 words) took one agent 101 tool calls and 14 minutes and
  processed about 10 million tokens, 97% of them prompt-cache reads;
  `tier_status.py` prints the estimate for this field's guides. Run it once per field.
- Fill the braces: `{field}` the field slug, `{draft}` the {field}-draft skill's
  folder, `{canon_dir}` the `canon_dir` in its field-config.yaml, `{jobs}` the
  `jobs` there. If `jobs` is empty (Tier 2 not built), pass the jobs you expect
  and tell the agent the mapping is provisional.
- Inputs, all in the {field}-draft skill:
  - `references/structure-canon.skeleton.md`: the rule frame (pillars 1–5, S1–S14,
    Q1–Q7, D1–D7, §5, §6), with the parent's guide named as a lead for each rule;
  - `references/field-config.yaml`: `canon_dir` (the guides) and `jobs` (this
    field's chapter names);
  - `<canon_dir>/_manifest.md`: one row per guide, key and title.
- Output: `references/structure-canon.md` in the {field}-draft skill.

## Agent prompt (fill {braces})

You are drafting `structure-canon.md` for the field {field}. The guides are the
text files in {canon_dir}, listed in its `_manifest.md`. The rule frame is
{draft}/references/structure-canon.skeleton.md. The field's chapter jobs are:
{jobs}.

Work rule by rule through the skeleton, in its order, keeping every rule ID.

1. **Search, do not read whole.** For each rule, search the guides with Grep for
   its idea (two to four searches with different wording; the skeleton's
   `Parent source` says where the parent found it, if that guide is here). Open
   only the lines around a hit.
2. **Quote verbatim, with a line pointer.** Write the pointer as
   `` `<key>.txt:<line>` `` or `` `<key>.txt:<first>-<last>` ``, then the words in
   `*"…"*`. Copy the characters exactly, including the guide's extraction damage.
   A word the guide breaks across two lines with a hyphen is written joined,
   with or without the hyphen (`announce-ment` or `announcement`), never with a
   space. You may leave words out with ` … ` (also to bridge a damaged character
   such as `�`) and mark a jump between the two columns of a page with ` / `; you
   may not change, add or reorder words. At most 40 words per quotation, and at
   least one piece of three or more characters. Put the pointer just before its
   quotation, in the same paragraph.
3. **One rule, one claim.** State the rule in your own words in one or two
   sentences, then the quotation that grounds it. If a guide says something the
   rule does not, write what the guide says, not the parent's version.
4. **No source here, say so.** If none of this field's guides states the rule,
   keep the ID and the rule text and mark it
   `secondary — no source among {field}'s guides`; no hard rule may rest on it.
   S14 is the exception: it is a measurement with no guide source by design, so
   keep it as the skeleton writes it.
   If the rule does not fit the field at all, write `not used in {field}` and why
   in one line. Never quote a guide that is not in {canon_dir}, and never quote
   from memory.
5. **Map the parent's chapters.** Where the rule names an economics chapter or
   part (introduction parts, `empirical-strategy`, `data-sample`), name the
   matching job of this field, or say there is none.
6. **Corpus status.** Every rule keeps a status tag. Measurable rules (S1–S7, S14,
   pillars 1–4, D1–D6, §5) are `corpus: TO-MEASURE` until `measure_structure.py`
   measures this field; judgment rules keep `corpus: unmeasured` or `judgment`.
   Leave the skeleton's `Parent source` and `parent-econ:` notes out of the
   output: they are leads for you, not this field's content.
7. **New rules.** If the guides state a structural rule the skeleton lacks,
   add it at the end of its section with the next free ID (S15, Q8, D8), with a
   quotation like every other rule. Tag it `corpus: TO-MEASURE` when it is about
   presence, position, order or length (things a script can count), else
   `judgment`.
8. **Header and sources.** Start the file with a short note: the date, the number
   of guides, that every non-secondary rule quotes `canon-sources/<key>.txt:line`
   verbatim, and that `py -3 scripts/check_canon_quotes.py` checks them. End with
   §6: the guides quoted (by key), and the secondary sources.
9. **Check, then fix.** Run `py -3 scripts/check_canon_quotes.py` from the
   {field}-draft skill. Fix every NOT-FOUND (wrong, reordered or recalled words,
   or the wrong file), every FOUND-ELSEWHERE and UNPOINTED (use the location it
   prints) and every TOO-SHORT, until the script exits 0. A quotation you cannot
   make pass is removed, and its rule marked `secondary`.

Report: how many rules are grounded, how many `secondary`, how many `not used`,
the new rules added, and the script's last summary line.

## After the pass

- `py -3 scripts/check_canon_quotes.py` exits 0.
- The draft `check_drift` Tier 4 canon lines pass (the file names `canon-sources`,
  carries `TO-MEASURE`, and every quote is found at its pointer). check_drift runs
  them only once Tier 4 is recorded in the registry's `built_tiers`; before that,
  the checker above is the test.
- A human reads the file: the rules should describe how this field writes, and a
  quoted guide should say what the rule says it says.
