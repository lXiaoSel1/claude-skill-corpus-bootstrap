# Introduction — Part 04: DESIGN

> PUBLIC COPY: verbatim example sentences are replaced by placeholders, paper keys by
> PaperA... stand-ins, and the parent manuscript's `For this manuscript` section by an
> empty skeleton. The Pattern / Use it when / Not this when fields are unchanged.

The paragraphs that say what we did: the setting, the identification strategy, the data, the measurement.

This is the only part of the introduction that regularly runs **five or six consecutive paragraphs**. In this corpus it is never one paragraph. The shortest real instance is one sentence (PaperA); the longest unbroken run is six paragraphs (PaperB ¶6–¶11), and one paper spends roughly half of a twenty-paragraph introduction on measurement and estimation alone.

Organise it **by the job each paragraph does**, one job per paragraph. Below are the jobs, then the usual order, then the paragraph budget.

---

## The Versions

### Version 1 · The setting carries the identification — naming the features of the policy that make it usable
Pattern        `<Policy/event> has several <attractive features / advantages> that allow us to <examine the question>.` — or — `<Policy> provides an ideal setting for <identification> by introducing <kind of variation> at a time when <the condition that makes the variation informative>.`
Example        "[verbatim sentence from the paper]"   — PaperC ¶4
               "[verbatim sentence from the paper]"   — PaperB ¶6
               "[verbatim sentence from the paper]"   — PaperD ¶2
               "[verbatim sentence from the paper]"   — PaperE ¶5
Use it when    You can list at least two features **of the statute itself** — not of your data — that a referee could verify by reading the statute: what it changed, when it was written, who it applied to automatically. If your two "features" are both facts about your sample, you are writing Version 6, not this.
Not this when  Version 3 is the confusable neighbour. Test: a Version 1 sentence would still be true if you had collected no data at all. A Version 3 sentence names which of *your* units moved and by how much.

---

### Version 2 · Naming the identification problem before naming the fix
Pattern        `<Identifying / Establishing> <the causal object> is <challenging / a difficult task>, <as / because> <the specific confound>.`
Example        "[verbatim sentence from the paper]"   — PaperB ¶5
               "[verbatim sentence from the paper]"   — PaperF ¶2
               "[verbatim sentence from the paper]"   — PaperG ¶3
               "[verbatim sentence from the paper]"   — PaperH ¶4
Use it when    You can name one variable that plausibly moves both your treatment status and your outcome, and you can point to the paragraph that follows as the thing that breaks the link. This paragraph is a promissory note; do not write it unless the next paragraph pays it.
Not this when  Version 11 is the confusable neighbour. Test: Version 2 sits **before** the design and motivates it — the reader does not yet know what you did. Version 11 sits **after** the design and defends it — the reader already knows what you did and is now being told why an obvious objection fails.

---

### Version 3 · Where the variation actually comes from
Pattern        `Crucially, <policy>'s impact on <running variable> was heterogeneous across <units>, reflecting predetermined differences in <a pre-existing characteristic>.` — or — `To address the identification challenge, we exploit the fact that <the rule> is set differently depending on <an observable>.`
Example        "[verbatim sentence from the paper]"   — PaperB ¶8
               "[verbatim sentence from the paper]"   — PaperE ¶8
               "[verbatim sentence from the paper]"   — PaperG ¶4
               "[verbatim sentence from the paper]"   — PaperI ¶4
Use it when    You can point to a **pre-treatment variable in your own data** that determines exposure and was fixed before the statute passed. If the exposure variable is measured after passage, you are not writing this paragraph, you are writing Version 11.
Not this when  Version 1. Test: Version 1's subject is the statute; Version 3's subject is the cross-sectional or time variation the statute produced in your panel.

A sub-move that lives in this Version: **legislative history deployed as exogeneity evidence** — a dated fact about how the provision got into the bill, used to argue that nobody could have anticipated or lobbied for it.
               "[verbatim sentence from the paper]"   — PaperB

---

### Version 4 · The estimator and the estimation sample, chosen and defended
Pattern        `To bring <the prediction> to the data, we adopt a <estimator> framework and focus on <the restricted sample>.` followed by `<Restricting to> this group offers several important advantages.`
Example        "[verbatim sentence from the paper]"   — PaperB ¶9
               "[verbatim sentence from the paper]"   — PaperB ¶10
               "[verbatim sentence from the paper]"   — PaperE ¶9
               "[verbatim sentence from the paper]"   — PaperJ ¶8
               "[verbatim sentence from the paper]"   — PaperK ¶10
Use it when    Your estimation sample is **narrower than the sample in your data section**, and you can state the restriction rule in one clause that a reader could execute on your panel. If estimation sample equals data sample, put the estimator name in a clause inside the first results sentence (as PaperE does) and skip the standalone paragraph.
Not this when  Version 5. Test: Version 4 says which observations enter the regression at all; Version 5 says, among those observations, which are treated and which are the comparison.

Note the shape of the corpus here. Only **PaperK ¶10** spends a whole paragraph justifying an estimator switch, and its argument is measurement error (Erickson–Jiang–Whited cumulant estimator), not treatment-effect heterogeneity. Every other paper names the estimator in one clause and moves on.

---

### Version 5 · Who is treated, who is control, and why
Pattern        `For our baseline <design>, we compare <treated units, defined by a rule> with <control units, defined by the complement>.` — or — `We utilize <subset> as our <treatment/control> group for two reasons.`
Example        "[verbatim sentence from the paper]"   — PaperB ¶11
               "[verbatim sentence from the paper]"   — PaperC ¶5
               "[verbatim sentence from the paper]"   — PaperL ¶6
               "[verbatim sentence from the paper]"   — PaperM ¶7
Use it when    A reader could reconstruct your treatment indicator from one column of your data plus one threshold. If defining your treatment group requires two conditions and a judgement call, that is a Data-and-Sample section table, not an introduction sentence.
Not this when  Version 4. Test: if you deleted the sentence, would the reader still know how many observations are in the regression (Version 4's job) or would they only lose the contrast (Version 5's job)?

---

### Version 6 · Data, window, and final N — with the window's start defended
Pattern        `Our <investigation/sample> relies on <N units> from <source> during <window>.` plus a clause or sentence giving **why the window starts where it does** — usually a disclosure rule or a data series that begins that year.
Example        "[verbatim sentence from the paper]"   — PaperN ¶4
               "[verbatim sentence from the paper]"   — PaperC ¶8
               "[verbatim sentence from the paper]"   — PaperO ¶5
               "[verbatim sentence from the paper]"   — PaperA ¶3
Use it when    Your window start is set by something **external** — a disclosure rule, a form redesign, a statute — rather than by convenience. PaperN starts in 2003 because FAS 132(R) first required the disclosure; PaperA stops in 1999 because of the filing series. If the start year is arbitrary, give the window without defending it and let the Data section carry the justification.
Not this when  Version 12. Test: Version 6 gives counts and dates; Version 12 gives a numbered list of analyses with no counts.

Note where this paragraph goes. **PaperC puts the sample size in the same paragraph as the first result**, not in a standalone data paragraph — the sentence above is the opening of a five-sentence results block. PaperJ ("[verbatim sentence]") opens its design block with the sample instead.

---

### Version 7 · The variable does not exist in the data, so the paper builds it
Pattern        `<Filers> are not required to disclose <the quantity>.` → `To <purpose>, I/we <hand-collect / construct / calculate> <the measure> using <the raw source and the rule applied>.`
Example        "[verbatim sentence from the paper]"   — PaperP ¶5
               "[verbatim sentence from the paper]"   — PaperF ¶5
               "[verbatim sentence from the paper]"   — PaperQ ¶5
               "[verbatim sentence from the paper]"   — PaperR ¶5
Use it when    The variable on the left-hand or right-hand side of your key regression has **no line item in any filing** and you had to derive it from a rule. The corpus's most economical opening for this is the bare institutional constraint — PaperP states the disclosure gap in a seven-word sentence and lets the construction follow as consequence.
Not this when  Version 8. Test: Version 7's problem is *absence* (the number is not reported anywhere); Version 8's problem is *choice* (the number is reported, and you used a different one).

---

### Version 8 · Defending the measure against the one the reader expects
Pattern        `Unlike earlier researchers who used <the standard measure>, we <the alternative>.` — or — `We choose to investigate <X> rather than <the standard Y>, because doing so allows us to <property 1, property 2, property 3>.`
Example        "[verbatim sentence from the paper]"   — PaperQ ¶4
               "[verbatim sentence from the paper]"   — PaperI ¶3
               "[verbatim sentence from the paper]"   — PaperM ¶4
               "[verbatim sentence from the paper]"   — PaperH ¶8
Use it when    A referee could name the measure you did *not* use, and you can give the property that made you switch — observability, exogeneity, or the fact that the standard measure mixes two things your theory separates. PaperQ and PaperH both decompose a total into a mandatory/mechanical part and a discretionary part; that decomposition is the single most common form this Version takes in the pension literature.
Not this when  Version 9. Test: Version 8 argues your measure is **better**; Version 9 concedes it is **worse than ideal** and argues it beats the alternative of doing nothing.

The same move is also used to defend a **data source** rather than a variable, and the corpus contains one instance aimed squarely at Form 5500:
               "[verbatim sentence from the paper]"   — PaperS

---

### Version 9 · The measure is imperfect and used anyway
Pattern        `While our <measure> has limitations, we believe <hedge> that <an imperfect proxy> is better than <the null alternative>.` — or — `We acknowledge that <source> <disclosures/data> are not without limitations.` — or — `There are important caveats to note about using <the method>.`
Example        "[verbatim sentence from the paper]"   — PaperK ¶6
               "[verbatim sentence from the paper]"   — PaperT ¶5
               "[verbatim sentence from the paper]"   — PaperU ¶9
               "[verbatim sentence from the paper]"   — PaperV ¶15
Use it when    You already have the robustness table showing the result survives the alternative measure, **and** the limitation is one a referee would raise on page one. PaperT spends eight sentences on this; PaperK does it in three and adds where to download the data. Do not open this door without the table behind it.
Not this when  Version 11. Test: Version 9's objection is about **the variable** — it mismeasures the concept. Version 11's objection is about **the comparison** — the estimate would be biased even with a perfect variable.

This is a modern habit. PaperW and PaperX contain no such paragraph; PaperU, PaperK, PaperT and PaperC all do, and PaperU adds a second one listing what the paper deliberately does not cover ("[verbatim sentence]").

---

### Version 10 · Validating the measure or the setting before using it
Pattern        `Our measure of <X> is correlated with <a list of observables> in a manner that is consistent with <the model / the name of the concept>.` — or — `To confirm <the premise the design rests on>, we examined <the raw source> and observed that <the confirming fact>.`
Example        "[verbatim sentence from the paper]"   — PaperR ¶6
               "[verbatim sentence from the paper]"   — PaperE ¶6
               "[verbatim sentence from the paper]"   — PaperY ¶6
Use it when    You have a table whose **only** job is to show the measure behaves the way its name implies — high-value units look the way the concept says they should, or the premise the design rests on is true in the raw source. PaperR lists five such correlates (productivity, size, Q, executive pay, 10-K risk-factor language) in one five-sentence paragraph.
Not this when  Version 9. Test: Version 10 **corroborates** and is followed by results; Version 9 **concedes** and is followed by a robustness promise. They can both appear, but never as the same paragraph.

---

### Version 11 · Endogeneity and self-raised objections, each in its own paragraph
Pattern        `<A number of tests / Our empirical methodology> address<es> potential endogeneity concerns.` — or — `One concern with <our initial tests> is that <the alternative story>.` — or — `An alternative explanation for <the test> is that <a mechanical story>.`
Example        "[verbatim sentence from the paper]"   — PaperN ¶6
               "[verbatim sentence from the paper]"   — PaperE ¶10
               "[verbatim sentence from the paper]"   — PaperC ¶10
               "[verbatim sentence from the paper]"   — PaperQ ¶6
               "[verbatim sentence from the paper]"   — PaperL ¶5
Use it when    You have a **specific table** that answers the objection, and you can name the objection in one clause. The corpus writes this two ways: as an announced battery (PaperN lists fixed effects, controls for operating risk and investment opportunities, an instrument, and sample selection in five sentences; PaperQ names 3SLS in three) or as one objection per paragraph (PaperC uses three consecutive paragraphs — macro conditions, passive rebalancing, and eligibility predetermination).
Not this when  Version 2. Test: could the sentence be moved to before your design statement and still make sense? If yes it is Version 2; if it presupposes the design, it is Version 11.

PaperL shows the strongest form: two sentences that raise the concern and then **write the identifying assumption out** rather than gesture at it. If you can state your assumption in a sentence a reader could disagree with, this is where it goes.

---

### Version 12 · The enumerated inventory of what the paper does
Pattern        `In this paper, we examine <the object>.` followed by `<First / Second / Third / Finally>, we <do X>.` — or — `We extend <prior work> in two ways.`
Example        "[verbatim sentence from the paper]"   — PaperD ¶5
               "[verbatim sentence from the paper]"   — PaperZ ¶3
               "[verbatim sentence from the paper]"   — PaperS ¶5
               "[verbatim sentence from the paper]"   — PaperAA ¶3
Use it when    The number of items you list equals the number of results subsections you actually have. PaperD lists four things and delivers four; PaperZ says "in two ways" and delivers two. A list whose count does not match the paper's structure is worse than no list.
Not this when  Version 4. Test: Version 12 tells the reader what questions get asked; Version 4 tells the reader what regression gets run. If your enumeration includes an estimator name, split it — put the estimator in Version 4.

---

### Version 13 · Walking the reader through the estimation
Pattern        `Measuring <the object> requires <step 1> as well as <step 2>.` → `We first calculate <quantity> under the assumption that <assumption A>.` → `The second main measure we present is <the same quantity under assumption B>.`
Example        "[verbatim sentence from the paper]"   — PaperL ¶4
               "[verbatim sentence from the paper]"   — PaperU ¶4
               "[verbatim sentence from the paper]"   — PaperU ¶8
               "[verbatim sentence from the paper]"   — PaperAB ¶4
Use it when    Your headline number is the **output of a calculation** the reader cannot picture without being told the steps, and there is no separate methods section carrying it. PaperU needs this because the paper *is* a valuation exercise; PaperAB needs it because the "data" are hand-read annual-report passages and the reader will not believe the classification otherwise.
Not this when  Version 7. Test: Version 7 builds **one variable** in one paragraph and moves on. Version 13 runs **across paragraphs**, each one adding an assumption or a counterfactual, and the reader is expected to follow the arithmetic. If you have a Data section and an Empirical Strategy section, you almost certainly want Version 7, not this.

PaperAC shows a compact two-paragraph form of the same job — "[verbatim sentence]" then "[verbatim sentence]"

---

## The usual order

The policy-shock papers in this corpus converge on one sequence. Read PaperB ¶5–¶11 as the canonical run:

1. **Version 2** — the identification problem (¶5)
2. **Version 1** — the setting solves it (¶6)
3. **Version 3** — the specific variation, plus legislative history as evidence it was unanticipated (¶7, ¶8)
4. **Version 4** — estimator and estimation sample, then why that sample (¶9, ¶10)
5. **Version 5** — treatment and control (¶11)
→ then the first result (¶12).

PaperC runs the same spine with the data paragraph folded into the first result: Version 1 (¶4) → Version 5 (¶5) → test battery (¶6, ¶7) → Version 6 fused with results (¶8) → three Version 11 paragraphs after the results (¶10, ¶11, ¶12).

PaperF compresses it to four: Version 2 (¶2) → Version 3 (¶3) → an ex-ante-indeterminacy paragraph (¶4, which belongs to the hypothesis part, not this one) → Version 7 (¶5) → results (¶6).

PaperT orders it around the measure rather than the design: what we do (¶2) → the prediction (¶3) → Version 8 (¶4) → Version 9 (¶5) → indeterminacy (¶6) → results (¶7).

PaperE, the corpus's one staggered-adoption paper, splits the block: Version 3-as-identification-statement (¶4) → Version 1 (¶5) → Version 10 (¶6) → the prediction (¶7) → Version 3 again, now naming staggering (¶8) → estimator named inside the headline result (¶9) → Version 11 (¶10).

**Two ordering facts worth internalising.** First, the measurement Versions (7, 8, 9, 10) always come *after* the identification Versions (1, 2, 3) when both are present — no paper in the corpus defines its variables before it has told the reader what the experiment is. Second, Version 11 is the only design Version that regularly appears **after** the first result: PaperN, PaperE and PaperC all state a finding first and then defend it.

## Paragraph budget

Four to six paragraphs is the working range for a policy-shock empirical paper: PaperF four, PaperT four, PaperC five, PaperB six, PaperE six (split by an intervening prediction paragraph).

Papers whose contribution *is* the measurement spend far more — PaperU roughly ten of twenty, PaperK roughly six of nineteen, PaperL five of fourteen. Papers with a strong separate methods section spend far less — PaperA does the whole job in one sentence, PaperAD in two ("[verbatim sentence]"), PaperY in one paragraph that mostly distinguishes itself from prior work ("[verbatim sentence]").

## A note on the dominant opener

Across every Version above, the single most common way a design paragraph begins is a **purpose infinitive**: "To bring this key prediction to the data…", "To address the identification challenge…", "To capture pension funding relief under MAP-21…", "To increase our confidence that…", "To study the empirical relation between…", "To identify the relative incentive to…", "To confirm the importance of…", "To examine whether the decision to freeze…", "To calculate present values under different assumptions…", "To shed further light on this question…", "In order to compare practical hedge portfolios…". If a design paragraph is not working, the first thing to try is putting the purpose in front of the verb.

---

## Not defaults for a reduced-form empirical paper: the theory and pricing papers

The pricing papers and the theory papers do this part differently, and the difference is not cosmetic. **A pricing paper walks the entire modelling path inside the introduction** — the model, the calibration source, the numerical method — because there is no reduced-form design to describe and the model *is* the contribution. Do not copy these into an empirical manuscript.

               "[verbatim sentence from the paper]"   — PaperAE
               "[verbatim sentence from the paper]"   — PaperAF
               "[verbatim sentence from the paper]"   — PaperAG
               "[verbatim sentence from the paper]"   — PaperAH
               "[verbatim sentence from the paper]"   — PaperAH
               "[verbatim sentence from the paper]"   — PaperW
               "[verbatim sentence from the paper]"   — PaperW

Three habits here that an empirical introduction should not import: (i) the modelling path is walked end to end in the introduction, so the reader meets Lee–Carter, the gap option and the Monte Carlo before any section heading; (ii) the roadmap and the design description fuse — PaperAI spends a fourteen-sentence final paragraph that reports section numbers and their conclusions at the same time, and PaperW splits the roadmap into two paragraphs each of which spoils its section's result; (iii) paragraph length balloons — PaperAI ¶4 is sixteen sentences, PaperAF ¶4 is seventeen.

The one hybrid worth noting is **PaperG**, which is a reduced-form paper in an insurance journal and follows the empirical spine exactly (Version 2 → Version 3 → results → three contributions → roadmap). It is the closest structural cousin in the pricing set to a corporate-finance introduction.

**PaperAJ** is an econometrics paper and is the only document in the corpus that argues about a DiD estimator's properties in its introduction. That is because the estimator *is* the paper. Its presence in the corpus is not licence to import the argument.

---

## For this manuscript

*[One italic paragraph restating what our manuscript is -- its question, design, data and
hypotheses. In the parent this section was written for its own unpublished manuscript; that
content is omitted from this public copy. The PASS2 spec, section 2, lists the required parts.]*

**Spend N paragraphs.** [Why N: the corpus count for papers like ours, naming the nearest
neighbour on topic and design.]

**Use, in this order:**

- **Version k**, one paragraph. [What this paragraph must say for our manuscript, and the test
  that decides whether it stays.]
- ...

**Rule out:**

- **Version k.** [Why the corpus says a paper like ours should not use it.]
- ...

**What waits for the later sections:**

| Belongs in the introduction | Waits for `Data and Sample` | Waits for `Empirical Strategy` |
|---|---|---|
| ... | ... | ... |
