#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure this field's attribution-verb ladder, and write verb-ladder.md.

WHY THIS EXISTS
    The parent's ladder was measured by hand -- a sequence of `grep -owih` and
    `grep -oihE` calls, with the numbers typed into the file.  That is how its
    three published frequencies came to be wrong, and how `consistent with`
    came to be counted as 1,034 by silently including `inconsistent with`:
    the measurement and the document were two separate acts.  Here they are
    one act.  Re-run it and the file is rebuilt from the corpus.

WHAT IS MEASURED
    Per verb: word-bounded hits over all its inflections; hits of
    `<verb> that`; the complementation RATE; and the RANGE (how many papers
    it occurs in, per Gries 2008 -- a verb concentrated in one paper is not
    this literature's verb).  Tier assignment is derived from those numbers,
    never asserted: a verb below MIN_RANGE papers is reported UNATTESTED
    whatever its raw count.

    Per verb also: how many hits sit in a NOUN context (a determiner,
    possessive or preposition on the left: `the claims`, `of reports`) versus
    a VERB context (subject pronoun, auxiliary, modal, `to`, or a citation
    closing just before it: `we find`, `(2019) reported`, `al.12 showed`).  A
    verb whose cued hits are mostly the noun is reported HOMOGRAPH: its count
    and complementation rate are not verb measurements.

HISTORY (factory, health-policy instance Tier 4, 2026-10-07)
    * Counted the raw corpus files, reference lists included, while attest.py
      and every Tier 1 measurement cut them (textseg.clean_prose).  Health-policy corpus:
      549,099 words raw vs 471,197 measured; `note` 384 -> 168 (table notes).
      Now the same clean_prose cut as attest.py's default.
    * No homograph guard: in a health-policy corpus `claim` was
      2,273 hits at 51/51 papers -- the noun (insurance `claims`),
      92% of its cued hits -- and read as the field's most attested verb.
    * `--write` now records the counts in registry.json (verb_ladder_counts)
      in the same act, since check_drift asserts the two agree.

RUN
    py -3 scripts/measure_verbs.py            # print the table
    py -3 scripts/measure_verbs.py --write    # ... rewrite verb-ladder.md + registry
"""
import glob
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, ".."))

# The corpus lives in the -lit sibling (field-config's lit_instance, like
# every other draft script); the ladder lives in -draft.
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402
LIT = os.path.normpath(_jobs.lit_dir())
CORPUS = os.path.join(LIT, "references", "corpus")
META = os.path.join(LIT, "references", "corpus_meta.yaml")
OUT = os.path.join(SKILL, "references", "verb-ladder.md")
REG = os.path.join(SKILL, "references", "registry.json")

# Same prose cut as attest.py (reference lists, captions, boilerplate).
sys.path.insert(0, os.path.join(LIT, "scripts"))
try:
    import textseg  # noqa: E402
except ImportError:  # checked when the corpus is read (the module stays importable)
    textseg = None

MIN_RANGE = 3      # a verb in fewer papers than this is not this field's verb

# Homograph guard: the token just left of a hit says noun or verb context.
# Closed-class words only, so the lists are field-invariant.
NOUN_LEFT = frozenset(
    "the a an this these those its their our his her your my of per each "
    "every any no such all some many several few fewer more most other "
    "another for in on with from by among between about against without "
    "within".split())
VERB_LEFT = frozenset(
    "we they he she it i you who which that is are was were be been being "
    "has have had do does did will would may might can could should must "
    "shall to not also authors author studies study paper papers "
    "researchers investigators others previously further first".split())
_LEFT_TOKEN = re.compile(r"([a-z0-9.)\]'’]+)\W*$")
# a citation just closed: `(2019)`, `[3]`, `et al.`/`al.12`, or a flattened
# superscript glued to a word, with or without its period (`costs.12,13`)
_CITE_LEFT = re.compile(
    r"(?:[)\]]|\bal\.?\d*,?|[a-z][.,;:]?\d+(?:[,–-]\d+)*)\s*$")
HOMOGRAPH_SHARE = 0.50   # noun share of cued hits at/above which ...
HOMOGRAPH_MIN = 10       # ... with at least this many noun-cued hits

# Anything from this marker down is preserved when the file is regenerated.
HAND_MARKER = "<!-- HAND-WRITTEN BELOW: preserved across regenerations -->"

# Candidate verbs.  Deliberately WIDER than any one field needs: the counts
# decide which survive, and a zero here is a finding about the field.
VERBS = [
    ("show",        ["show", "shows", "showed", "shown"]),
    ("prove",       ["prove", "proves", "proved", "proven"]),
    ("find",        ["find", "finds", "found"]),
    ("establish",   ["establish", "establishes", "established"]),
    ("obtain",      ["obtain", "obtains", "obtained"]),
    ("note",        ["note", "notes", "noted"]),
    ("remark",      ["remark", "remarks", "remarked"]),
    ("observe",     ["observe", "observes", "observed"]),
    ("suggest",     ["suggest", "suggests", "suggested"]),
    ("argue",       ["argue", "argues", "argued"]),
    ("conclude",    ["conclude", "concludes", "concluded"]),
    ("report",      ["report", "reports", "reported"]),
    ("demonstrate", ["demonstrate", "demonstrates", "demonstrated"]),
    ("derive",      ["derive", "derives", "derived"]),
    ("construct",   ["construct", "constructs", "constructed"]),
    ("extend",      ["extend", "extends", "extended"]),
    ("generalize",  ["generalize", "generalizes", "generalized",
                     "generalise", "generalises", "generalised"]),
    ("conjecture",  ["conjecture", "conjectures", "conjectured"]),
    ("claim",       ["claim", "claims", "claimed"]),
    ("assume",      ["assume", "assumes", "assumed"]),
    ("recall",      ["recall", "recalls", "recalled"]),
    ("document",    ["document", "documents", "documented"]),
    ("attribute",   ["attribute", "attributes", "attributed"]),
]

# Fixed phrases -- alignment and re-attribution, not verbs taking `that`.
PHRASES = [
    "consistent with", "inconsistent with", "due to", "following",
    "as in", "building on", "in the spirit of", "adapted from",
    "we refer to", "see also",
]


def style_safe_ids():
    """Read the style-safe list from corpus_meta.yaml without needing PyYAML."""
    if not os.path.exists(META):
        return None
    ids, cur = [], None
    for line in io.open(META, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*-?\s*id:\s*(\S+)", line)
        if m:
            cur = m.group(1).strip("'\"")
        elif cur and re.match(r"\s*style_safe:\s*(?:true|True)\s*$", line):
            ids.append(cur)
            cur = None
    return ids or None


def load():
    if textseg is None:   # without it reference lists would be counted as prose
        sys.exit("measure_verbs: cannot import textseg from %s/scripts -- check lit_instance"
                 " in field-config.yaml" % LIT)
    ids = style_safe_ids()
    out = {}
    for f in sorted(glob.glob(os.path.join(CORPUS, "*.txt"))):
        k = os.path.basename(f)[:-4]
        if ids is not None and k not in ids:
            continue
        s = io.open(f, encoding="utf-8", errors="replace").read()
        out[k] = textseg.clean_prose(s).lower()
    return out


def context(left):
    """'noun', 'verb' or None, from the text just left of a hit."""
    m = _LEFT_TOKEN.search(left)
    tok = m.group(1).strip(".'’") if m else ""
    if tok in NOUN_LEFT:
        return "noun"
    if tok in VERB_LEFT or _CITE_LEFT.search(left):
        return "verb"
    return None


def cues(texts, pattern):
    rx = re.compile(pattern)
    noun = verb = 0
    for t in texts.values():
        for m in rx.finditer(t):
            c = context(t[max(0, m.start() - 30):m.start()])
            noun += c == "noun"
            verb += c == "verb"
    return noun, verb


def homograph(noun, verb):
    return (noun >= HOMOGRAPH_MIN and noun + verb > 0
            and noun / float(noun + verb) >= HOMOGRAPH_SHARE)


def count(texts, pattern):
    rx = re.compile(pattern)
    total, rng = 0, 0
    for t in texts.values():
        n = len(rx.findall(t))
        total += n
        rng += 1 if n else 0
    return total, rng


def measure(texts):
    rows = []
    for name, forms in VERBS:
        alt = "|".join(sorted(forms, key=len, reverse=True))
        w, rng = count(texts, r"\b(?:%s)\b" % alt)
        t, _ = count(texts, r"\b(?:%s)\s+that\b" % alt)
        noun, verb = cues(texts, r"\b(?:%s)\b" % alt)
        rows.append((name, w, rng, t, (t / w) if w else 0.0, noun, verb))
    prows = []
    for p in PHRASES:
        w, rng = count(texts, r"\b%s\b" % re.escape(p))
        prows.append((p, w, rng))
    return rows, prows


def write(rows, prows, n_papers, words):
    L = ["# verb-ladder.md — 归因动词阶梯"
         "（**全部实测，无一条是"
         "设计出来的**）", "",
         "> 来源：`../%s-lit/references/corpus/`，"
         "**%d 篇 style-safe**，{:,} 词。".format(words)
         % (_field, n_papers),
         "> 生成：`py -3 scripts/measure_verbs.py --write`。"
         "**这个文件不手写**——"
         "母本的阶梯是手工 grep 出来的，",
         "> 三处词频因此写错，其中 "
         "`consistent with` 把 `inconsistent with` "
         "一并算进了赞同统计。",
         "> 测量与成文在这里是同一"
         "个动作。", "",
         "> **口径**：与 `attest.py` 默认相同——"
         "参考文献表、图表说明和出版"
         "商样板行先剔除（`textseg.clean_prose`），"
         "所以书目标题里的 `reported` 不算数。", "",
         "> **`名词语境`** 是有左侧提示的"
         "命中里名词用法所占的份额"
         "（左边是冠词、物主词或介词"
         " vs 主语代词、助动词、`to` 或"
         "引文标记）。≥%.0f%% 且名词命中 ≥%d "
         "的标 **HOMOGRAPH**：它的词频和"
         "补足率量的主要是名词，"
         "不是动词。" % (HOMOGRAPH_SHARE * 100, HOMOGRAPH_MIN), "",
         "> **用法**：归因动词的强度"
         "不得超过来源逐字行所支"
         "持的程度。", "",
         "> **`range` 是防语料倾斜的那一"
         "列**（Gries 2008）。只出现在少"
         "于 %d 篇里的动词标 `UNATTESTED`，"
         % MIN_RANGE,
         "> 无论词频多高——它是某"
         "一位作者的习惯，不是这"
         "个文献的。", "",
         "---", "", "## 实测底数", "",
         "| 动词 | 词频 | range | 接 `that` | "
         "补足率 | 名词语境 | 归类 |",
         "|---|---|---|---|---|---|---|"]
    for name, w, rng, t, r, noun, verb in sorted(rows, key=lambda x: -x[1]):
        if not w:
            cls = "**词频 0 —— 本文献不用这个词**"
        elif rng < MIN_RANGE:
            cls = "**UNATTESTED**（只在 %d 篇里）" % rng
        elif homograph(noun, verb):
            cls = ("**HOMOGRAPH** —— 主要是名词；"
                   "词频、range、补足率都不是"
                   "动词的测量（`that` 多为"
                   "关系从句）。用作归因动词前"
                   "先读 `attest.py` 的语境行")
        elif r >= 0.60:
            cls = "从句为主 —— 归因用"
        elif r >= 0.30:
            cls = "结果 + 从句"
        elif t == 0:
            cls = ("**从不接 `that`** —— "
                   "指向对象，非归因")
        else:
            cls = "接名词宾语为主（%.0f%%）" % (r * 100)
        share = ("%.0f%%（%d/%d）" % (100.0 * noun / (noun + verb), noun,
                                     noun + verb) if noun + verb else "—")
        L.append("| `%s` | %d | %d/%d | %d | %.0f%% | %s | %s |"
                 % (name, w, rng, n_papers, t, r * 100, share, cls))
    L += ["", "## 固定表述（对齐与再"
          "归属，不接 `that`）", "",
          "| 表述 | 词频 | range |", "|---|---|---|"]
    for p, w, rng in sorted(prows, key=lambda x: -x[1]):
        L.append("| `%s` | %d | %d/%d%s |"
                 % (p, w, rng, n_papers,
                    " — **UNATTESTED**" if rng < MIN_RANGE else ""))
    L += ["", "---", "", "## 怎么用这张表", "",
          "1. **补足率 ≥60% 的动词才是"
          "归因动词。** 它后面接的"
          "是一个命题，所以它在替"
          "被引论文说话。",
          "2. **补足率接近 0 而词频很"
          "高的动词指向对象，不指"
          "向命题**——在这个文献"
          "里它多半在说“我们得到"
          "了某个东西”，不是“某"
          "人主张某事”。",
          "   把它当归因动词用，等"
          "于把自己的结果写成别人"
          "的。",
          "3. **`UNATTESTED` 一律不用。** 不是"
          "它错，是这个语料没有证"
          "据说它是本行的说法。",
          "   **`HOMOGRAPH` 不按这张表判断**——"
          "它的数字大半属于同形名词，"
          "要读语境行才知道动词用法"
          "有多少。",
          "4. 复算：`py -3 scripts/measure_verbs.py`。"
          "数字变了就重写这个文件"
          "，不要手改。", ""]

    # Everything after the marker is field-specific reading of the numbers
    # above -- written by a person, preserved across regenerations.  The
    # lesson from the parent is that MEASUREMENTS must not be hand-typed;
    # the interpretation of them still has to be, and it must survive the
    # rebuild or it will be silently lost the first time anyone re-runs this.
    kept = ""
    if os.path.exists(OUT):
        old = io.open(OUT, encoding="utf-8").read()
        if HAND_MARKER in old:
            kept = "\n" + old[old.index(HAND_MARKER):]
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as _fh:
        _fh.write("\n".join(L) + kept)
    print("\nwrote %s%s" % (OUT, "  (hand-written tail preserved)"
                            if kept else ""))
    record(rows, prows, n_papers, words)


def record(rows, prows, n_papers, words):
    """Registry counts in the same act as the file: check_drift asserts that
    every registry count appears as `| `k` | v |` in the ladder on disk."""
    if not os.path.exists(REG):
        print("no registry.json -- counts not recorded")
        return
    reg = json.load(io.open(REG, encoding="utf-8"))
    counts = dict((name, w) for name, w, *_ in rows if w)
    counts.update((p, w) for p, w, _ in prows if w)
    reg["verb_ladder_counts"] = counts
    reg["_why_verb_ladder_counts"] = (
        "Generated by scripts/measure_verbs.py --write: word-bounded hits over "
        "all inflections, %d style-safe papers, %s words after the "
        "textseg.clean_prose cut (attest.py's default). Zero-hit verbs and "
        "phrases are omitted; HOMOGRAPH verbs are counted but their numbers "
        "are mostly the noun." % (n_papers, "{:,}".format(words)))
    with io.open(REG, "w", encoding="utf-8", newline="\n") as _fh:
        _fh.write(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    print("recorded %d counts in %s" % (len(counts), REG))


def main():
    texts = load()
    if not texts:
        sys.exit("no corpus files -- has Tier 0 run?")
    n_papers = len(texts)
    words = sum(len(t.split()) for t in texts.values())
    rows, prows = measure(texts)

    print("corpus: %d style-safe papers, %d words\n" % (n_papers, words))
    print("%-13s %7s %7s %7s %7s %6s  %s"
          % ("verb", "hits", "range", "+that", "rate", "noun%", "status"))
    for name, w, rng, t, r, noun, verb in sorted(rows, key=lambda x: -x[1]):
        st = ("UNATTESTED" if rng < MIN_RANGE
              else "HOMOGRAPH" if homograph(noun, verb)
              else "clause" if r >= 0.30 else "object")
        print("%-13s %7d %6d/%-2d %7d %6.0f%% %5.0f%%  %s"
              % (name, w, rng, n_papers, t, r * 100,
                 100.0 * noun / (noun + verb) if noun + verb else 0, st))
    print()
    for p, w, rng in sorted(prows, key=lambda x: -x[1]):
        print("%-20s %6d  range %d/%d%s"
              % (p, w, rng, n_papers,
                 "   UNATTESTED" if rng < MIN_RANGE else ""))
    if "--write" in sys.argv:
        write(rows, prows, n_papers, words)
    return 0


if __name__ == "__main__":
    sys.exit(main())
