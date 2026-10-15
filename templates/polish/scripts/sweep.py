#!/usr/bin/env python3
"""Step b -- whole-manuscript register sweep against the {{FIELD}}-lit style-safe corpus.

Does not rely on a reviewer choosing what to query. Layers:
  L1  vocabulary -- words (>= 4 letters) in the draft found in 0 corpus papers
  L1b thin       -- words found in only 1-2 corpus papers
  L2  frames     -- 2-4-grams used >= sweep_min_freq times whose words are all
                    attested (each in >= sweep_common_df papers) but whose
                    combination is in 0 corpus papers
  L2b one-offs   -- 3-4-grams used once whose words are all very common (each
                    in >= sweep_very_common_df papers), combination in 0 papers;
                    "core" when a word pair inside is itself in 0 papers (read
                    these), "compositional" when every pair is attested
                    (usually ordinary grammar; only the first 20 print)
  L3  length     -- sentences longer than the corpus words-per-sentence P90
                    (citations are not words, as in para_lengths.py)
Frames never run across a citation or a statistic label ("OR 0.41").
FOCUS lists what falls inside the named sections: the step's to-do list, and
how well the corpus covers the section (cited papers in the style corpus,
the section's key words in >= 3 papers; LOW = rule 2 often cannot be met).
With --since <snapshot> (step a's), FOCUS marks each frame NEW (not in that
snapshot of the section) or +k (used k more times than there), and lists the
0-paper frames the snapshot had that the section no longer has: the rule-4
re-run after an edit shows what the edit brought in.
POSITIVE CONTROLS are phrases a reviewer knows should be flagged; each is
tested against the corpus index itself, so it is judged whether or not the
draft still contains it. A MISSED control means the sweep is not qualified.

RUN
    py -3 scripts/sweep.py [section ...] [--since <snapshot>] [--min-freq N] [--manuscript main.tex]
Exit code 1 when a positive control is MISSED.
"""
import re
import sys
from collections import Counter, defaultdict

import _rp
from _rp import toks, gram_toks, prose_words, strip_line, HEADING_LINE

ctx = _rp.Ctx(sys.argv)
opts = ctx.opts
args = ctx.args
MIN_FREQ = int(_rp._pop(args, "--min-freq", opts["sweep_min_freq"]))
COMMON = opts["sweep_common_df"]
VERY_COMMON = opts["sweep_very_common_df"]
CONTROLS = opts["sweep_controls"]
SINCE = _rp._pop(args, "--since")
split_sentences = ctx.split_sentences()
focus = ctx.sections(args) if args else []
if SINCE and not focus:
    _rp.die("--since compares sections with a snapshot: sweep.py <section> --since <snapshot>")


def grams(ts, n):
    return (" ".join(ts[i:i + n]) for i in range(len(ts) - n + 1))


# ---- corpus index (style-safe, the same cleaned text attest.py searches) ----
attest, _ = ctx.lit_modules()
papers = attest.eligible(attest.load_meta(), "style")
word_df = defaultdict(set)
gram_df = {n: defaultdict(set) for n in (2, 3, 4)}
corpus_sent_words = []
for pid, t in _rp.corpus_sentences(ctx):
    if 3 <= len(t) <= 150:
        corpus_sent_words.append(len(t))
    for w in t:
        word_df[w].add(pid)
    for n in (2, 3, 4):
        for g in grams(t, n):
            gram_df[n][g].add(pid)
if not corpus_sent_words:
    _rp.die("the style-safe corpus has no sentences -- is Tier 0 built?")
corpus_sent_words.sort()
P90 = corpus_sent_words[int(0.9 * len(corpus_sent_words))]
MED = corpus_sent_words[len(corpus_sent_words) // 2]

# ---- the whole manuscript ----
raw = ctx.ms.expanded_body()
prose = "\n".join(strip_line(l) for l in raw.splitlines() if not HEADING_LINE.match(l))
sents = [s.strip() for s in split_sentences(re.sub(r"\s+", " ", prose)) if len(s.split()) >= 3]

draft_words = Counter()
draft_grams = {n: Counter() for n in (2, 3, 4)}
for s in sents:
    for w in toks(s):
        draft_words[w] += 1
    t = gram_toks(s)
    for n in (2, 3, 4):
        for g in grams(t, n):
            if "citex" not in g.split():
                draft_grams[n][g] += 1

print("corpus: %d style-safe papers · %d sentences · words/sentence median %d, P90 %d"
      % (len(papers), len(corpus_sent_words), MED, P90))
print("draft: %d sentences (%s)\n" % (len(sents), ctx.ms.path))

# L1
l1 = sorted(((c, w) for w, c in draft_words.items()
             if w != "citex" and len(w) >= 4 and not word_df.get(w)), reverse=True)
print("L1 VOCABULARY — words in 0 corpus papers: %d distinct" % len(l1))
print("  " + ", ".join("%s×%d" % (w, c) for c, w in l1[:60]))
l1b = sorted(((c, w, len(word_df[w])) for w, c in draft_words.items()
              if w not in ("citex", "num") and len(w) >= 3 and 1 <= len(word_df.get(w, ())) <= 2),
             reverse=True)
print("\nL1b THIN VOCABULARY — words in only 1-2 corpus papers: %d distinct" % len(l1b))
print("  " + ", ".join("%s×%d(df%d)" % (w, c, d) for c, w, d in l1b[:60]))

# L2
rows = []
for n in (4, 3, 2):
    for g, c in draft_grams[n].items():
        if c < MIN_FREQ:
            continue
        ws = g.split()
        if not all(len(word_df.get(w, ())) >= COMMON for w in ws):
            continue
        if not gram_df[n].get(g):
            rows.append((c, n, g))
# drop shorter grams fully covered by a flagged longer gram with the same count
flagged = []
for c, n, g in sorted(rows, key=lambda r: (-r[0], -r[1])):
    if any((" " + g + " ") in (" " + g2 + " ") and c == c2 for c2, n2, g2 in flagged if n2 > n):
        continue
    flagged.append((c, n, g))
print("\nL2 FRAMES — attested words, combination in 0 corpus papers, draft freq >= %d: %d"
      % (MIN_FREQ, len(flagged)))
for c, n, g in flagged[:80]:
    print("  %3d×  %s" % (c, g))

one = []
for n in (4, 3):
    for g, c in draft_grams[n].items():
        if c != 1:
            continue
        ws = g.split()
        if "num" in ws or not all(len(word_df.get(w, ())) >= VERY_COMMON for w in ws):
            continue
        if not gram_df[n].get(g):
            one.append((min(len(word_df[w]) for w in ws), n, g))
one_f = []
for d, n, g in sorted(one, key=lambda r: (-r[1], -r[0])):
    if n == 3 and any((" " + g + " ") in (" " + g4 + " ") for _, n4, g4 in one_f if n4 == 4):
        continue
    one_f.append((d, n, g))


def is_core(g):
    """A one-off frame with a word pair the corpus never uses is worth reading;
    one whose every pair is attested is usually compositional grammar."""
    return any(not gram_df[2].get(b) for b in grams(g.split(), 2))


core_n = sum(1 for _, _, g in one_f if is_core(g))
print("\nL2b ONE-OFF FRAMES — very common words (each >= %d papers), combination in 0 papers: %d"
      " (%d core, %d compositional)" % (VERY_COMMON, len(one_f), core_n, len(one_f) - core_n))
for d, n, g in sorted(one_f, key=lambda r: (not is_core(r[2]), -r[0]))[:60]:
    print("  %-4s min-df %2d  %s" % ("core" if is_core(g) else "", d, g))

# L3
long_s = [s for s in sents if prose_words(s) > P90]
print("\nL3 LENGTH — sentences over corpus P90 (%d words): %d of %d" % (P90, len(long_s), len(sents)))
dw = sorted(prose_words(s) for s in sents)
if dw:
    print("  draft words/sentence median %d, P90 %d" % (dw[len(dw) // 2], dw[int(0.9 * len(dw))]))


# ---- focus: only what falls inside the named sections ----
def present(fs, gram_set):
    hits, where = Counter(), defaultdict(list)
    for ln, s in fs:
        t = gram_toks(s)
        for n in (4, 3, 2):
            for g in grams(t, n):
                if g in gram_set:
                    hits[g] += 1
                    where[g].append(ln)
    kept = []
    for g, c in sorted(hits.items(), key=lambda x: (-x[1], -len(x[0]))):
        if any((" " + g + " ") in (" " + k + " ") and c == hits[k] for k in kept):
            continue
        kept.append(g)
    return kept, hits, where


def coverage(sec, fs):
    """How well the style corpus covers this section's topic."""
    idx = ctx.library_index()
    keys = sorted(_rp.cite_keys(sec.text()))
    style = set(papers)
    in_style = [k for k in keys if ((idx.get(k) or {}).get("corpus_key") or k) in style]
    widespread = {w for w, _ in sorted(word_df.items(), key=lambda x: -len(x[1]))[:300]}
    cw = Counter(w for _, s in fs for w in toks(s)
                 if len(w) >= 4 and w not in ("citex", "num") and w not in widespread)
    top = [w for w, _ in cw.most_common(15)]
    dfs = sorted(len(word_df.get(w, ())) for w in top)
    good = sum(1 for d in dfs if d >= 3)
    # LOW: under half the key words are in >= 3 papers, or the corpus holds
    # none of the section's three or more cited papers (their topic's
    # reporting frames are then rarely attested)
    why = []
    if top and good * 2 < len(top):
        why.append("key words")
    if len(keys) >= 3 and not in_style:
        why.append("cited papers")
    print("  coverage %s: cited papers in the style corpus %d of %d; key words in >= 3 papers %d of %d"
          " (median df %s of %d)%s"
          % ("LOW" if why else "OK", len(in_style), len(keys), good, len(top),
             dfs[len(dfs) // 2] if dfs else "-", len(papers),
             "  LOW (%s): rule 2 will often not be met; record it (rule 2c)" % " and ".join(why) if why else ""))


def gram_counts(fs):
    c = Counter()
    for _, s in fs:
        t = gram_toks(s)
        for n in (2, 3, 4):
            c.update(grams(t, n))
    return c


def zero_frames(c):
    """The counted grams whose words are attested (each in >= COMMON papers)
    and whose combination is in 0 papers."""
    return {g for g in c if "citex" not in g.split()
            and all(len(word_df.get(w, ())) >= COMMON for w in g.split())
            and not gram_df[len(g.split())].get(g)}


def since_mark(g, hits, old):
    """NEW / +k against the --since snapshot of the section ("" without one)."""
    if old is None:
        return ""
    if not old[g]:
        return "  NEW"
    return "  +%d" % (hits[g] - old[g]) if hits[g] > old[g] else ""


recurring = {g for c, n, g in flagged}
oneoff = {g for _, n, g in one_f}
for sec in focus:
    fs = _rp.para_sentences(_rp.section_body(sec), split_sentences)
    wc = sorted(prose_words(s) for _, s in fs)
    print("\n" + "=" * 70)
    if not wc:
        print("FOCUS %s: 0 sentences" % sec.key)
        continue
    print("FOCUS %s (%s): %d sentences · words/sentence median %d · over P90 (%d): %d"
          % (sec.key, sec.path, len(fs), wc[len(wc) // 2], P90, sum(1 for x in wc if x > P90)))
    coverage(sec, fs)
    old = (gram_counts(_rp.para_sentences(_rp.body_lines(ctx.snapshot_lines(SINCE, sec)), split_sentences))
           if SINCE else None)
    marked = 0
    kept, hits, where = present(fs, recurring)
    print("  recurring 0-hit frames present (L2): %d" % len(kept))
    for g in kept:
        m = since_mark(g, hits, old)
        marked += bool(m)
        print("    %d×  %s   (doc-wide ×%d; lines %s)%s"
              % (hits[g], g, draft_grams[len(g.split())][g], where[g], m))
    kept, hits, where = present(fs, oneoff)
    core = [g for g in kept if is_core(g)]
    comp = [g for g in kept if not is_core(g)]
    if old is not None:                        # the frames an edit brought in print first
        comp.sort(key=lambda g: not since_mark(g, hits, old))
    print("  one-off 0-hit frames present (L2b): %d — core %d (read each), compositional %d"
          % (len(kept), len(core), len(comp)))
    for g in core:
        m = since_mark(g, hits, old)
        marked += bool(m)
        print("    core  %s   (lines %s)%s" % (g, where[g], m))
    for k, g in enumerate(comp):
        m = since_mark(g, hits, old)
        marked += bool(m)
        if k < 20:
            print("          %s   (lines %s)%s" % (g, where[g], m))
    if len(comp) > 20:
        print("          ... %d more compositional frames (ordinary grammar unless idiomatic)" % (len(comp) - 20))
    if old is not None:
        now = gram_counts(fs)
        gone = [g for g in zero_frames(old) if not now[g]]
        gone = sorted(g for g in gone if not any(g != h and (" " + g + " ") in (" " + h + " ") for h in gone))
        print("  since snapshot %s: %d frame(s) above marked NEW or +k (brought in or used more by the edits);"
              " %d 0-paper frame(s) of the snapshot gone" % (SINCE, marked, len(gone)))
        for g in gone[:20]:
            print("    gone  %s" % g)
        if len(gone) > 20:
            print("    ... %d more gone" % (len(gone) - 20))
    vv = Counter(w for _, s in fs for w in toks(s) if w not in ("citex", "num")
                 and len(word_df.get(w, ())) <= 2 and len(w) >= 3)
    print("  vocabulary at 0-2 corpus papers: " + ", ".join(
        "%s×%d(df%d)" % (w, c, len(word_df.get(w, ()))) for w, c in vv.most_common()))
    print("  sentences over P90:")
    for ln, s in fs:
        n = prose_words(s)
        if n > P90:
            print("    L%d %dw  %s…" % (ln, n, s[:90]))


# ---- positive controls: is each phrase flagged wherever it appears? ----
def control(phrase):
    t = toks(phrase)
    rare = [w for w in t if len(word_df.get(w, ())) <= 2]
    if rare:
        return "CAUGHT", "L1 " + ",".join(rare)
    l2 = l2b = None
    for n in (4, 3, 2):
        for i in range(len(t) - n + 1):
            ws = t[i:i + n]
            g = " ".join(ws)
            if gram_df[n].get(g):
                continue
            if all(len(word_df.get(w, ())) >= COMMON for w in ws):
                l2 = l2 or g
            if n >= 3 and "num" not in ws and all(len(word_df.get(w, ())) >= VERY_COMMON for w in ws):
                l2b = l2b or g
    if l2 and l2b:
        return "CAUGHT", "L2/L2b %r" % l2b
    if l2:
        return "PARTIAL", "L2 %r only when used >= %d times; one use passes" % (l2, MIN_FREQ)
    return "MISSED", "every 2-4-word window is in the corpus"


print("\nPOSITIVE CONTROLS (phrases that must be flagged):")
missed = 0
for ctl in CONTROLS:
    t = toks(ctl)
    n = len(t)
    g = " ".join(t)
    c = draft_grams[n].get(g, 0) if n in (2, 3, 4) else sum(1 for s in sents if g in " ".join(toks(s)))
    df = len(gram_df[n].get(g, ())) if n in (2, 3, 4) else -1
    verdict, how = control(ctl)
    missed += verdict == "MISSED"
    print("  %-7s %-28r draft×%d corpus papers=%s  %s" % (verdict, ctl, c, df if df >= 0 else "-", how))
if not CONTROLS:
    print("  none set (polish.yaml sweep_controls) -- the sweep is unqualified")
if missed:
    print("\n%d control(s) MISSED: the sweep would not flag them; do not rely on it." % missed)
    sys.exit(1)
