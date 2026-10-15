# Section G of the humanizer skill: meaning a reader cannot pin down

> Step f of {{FIELD}}-polish. A copy of section G (§27 to §32) of the humanizer skill, for
> machines where humanizer is not installed or its copy has no section G (G is a local
> addition, not upstream). When humanizer with §27 is installed, its section G may be
> used instead; ask it for a list of findings, not its embedded mode, which returns only
> rewritten text. Section numbers below are humanizer's; "§8" is its dash rule.
>
> **How to apply:** read each sentence with only the sentence before it in view. If its claim
> can be stated two ways, or claims more than the source line, it fails. Fix it before the
> step ends, and re-check any changed fact against the source (step h2). A fix that would
> add a reason or a scope the author did not write is listed for the author instead
> (the polish SKILL's rule 1).

*Local addition, not from upstream.* A text can be free of AI tells and still mislead. This happens most in translated or heavily revised research prose. Each sentence must allow one reading only, and that reading must match the source. Apply this section to methods, results, and literature reviews. Read each sentence as a reader who has only that sentence and the one before it. If you can state its claim in two ways, it fails.

### 27. Scope of each, separate, and both

**Watch for:** separate X for each Y; each type, each group, or both with no antecedent in the same sentence; respectively across clauses whose lists differ in length
**Problem:** The reader cannot tell how many things there are or which ones are meant. "Separate regressions for each type" can mean several models per type.
**Before:**
> Separate regressions for each habitat adjusted for rainfall and altitude.
**After:**
> Upland and lowland sites were analyzed in two separate regression models, each adjusted for rainfall and altitude.

### 28. A verb that claims more, or something else, than the source

**Watch for:** adjusted for or controlled for when the variables were selected by the data (stepwise, LASSO); led to or caused for an association; found for argued or suggested; attributable to for related to; paid by for billed to; denied for not accepted
**Problem:** Each verb carries a claim about method or evidence. A swap that looks like a synonym changes what the study did or found. Use the source's verb, or the weakest verb the source supports.
**Before:**
> The regressions (with backward selection of variables) adjusted for soil type, rainfall, and altitude.
**After:**
> Covariates were selected by backward stepwise elimination; the final models retained soil type, rainfall, and altitude.

### 29. A difference with no stated reason

**Watch for:** "the X model also included Y"; "except in Z"; "only for women", where the text gives no reason and the reader will supply a wrong one
**Problem:** An unexplained asymmetry invites a guess. Give the reason the source gives, in a few words, or say that no reason was given.
**Before:**
> Both models adjusted for rainfall and altitude; the upland model also included grazing intensity.
**After:**
> Both final models retained rainfall and altitude; grazing intensity was retained only in the upland model.

### 30. Words with two readings

**Watch for:** years of monitoring (calendar years or duration); rate for ratio or the reverse; more than or over for an inclusive bound ("4 days or more" in the source); higher for women with no outcome named; national with no country
**Problem:** The reader picks one reading and has no way to know it is the wrong one. Choose the word whose only reading is the intended one.
**Before:**
> controlled for site and years of monitoring
**After:**
> controlled for site and length of the monitoring record

### 31. A comparison with a missing side

**Watch for:** higher, lower, more likely, or longer with no than; an odds ratio or percentage with no reference group; "burned plots had higher odds of both partial recovery and no recovery" (higher than unburned plots, or higher than full recovery?)
**Problem:** The reader supplies the comparator, often the wrong one. Name both sides. If the source does not state the comparator, do not supply one: leave it to the author and say so in the record.
**Before:**
> Compared with full recovery, burned plots had higher odds of both partial recovery and no recovery.
**After:**
> Burned plots had higher odds than unburned plots of both partial recovery and no recovery, each compared with full recovery.

### 32. A modifier attached to the wrong phrase

**Watch for:** a date, place, count, or parenthesis placed after the nearest noun but meant for an earlier one; a semicolon that cuts off an attribution ("the authors argue that A; B" makes B the reviewer's own claim)
**Problem:** The sentence attaches a fact or an attribution to the wrong thing.
**Before:**
> They surveyed 204 households that had received subsidies in 1997–1998.
**After:**
> In 1997–1998, they surveyed 204 households that had received subsidies.

**Numeric ranges.** In academic text, keep the en dash in ranges such as 1993–2005 and 95% CI 0.98–1.58. §8 applies to dashes that join clauses, not to ranges.
