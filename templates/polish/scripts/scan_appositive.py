#!/usr/bin/env python3
"""Step g -- list tails tacked on after a comma that have no finite verb of
their own (rule 5). Each candidate prints with its kind:
  noun  a noun phrase (", a difference ...", ", a gap that ...",
        ", one ... and the other ...", ", the lowest ...");
  with  a with-absolute that ends the sentence (", with no change over time.");
  -ing  a participle phrase that ends the sentence (", suggesting that ...",
        ", covering ..."). Prepositions ending in -ing ("including", "during",
        "according to") are skipped.
with and -ing tails are listed only after a main clause (five or more words
before the comma), not after an opening adverbial. Rewrite the real ones as
clauses. List items, a subject after an opening adverbial, and a participle
whose subject is the main clause's also match: read each.

RUN
    py -3 scripts/scan_appositive.py [section ...] [--first N]   # N: only each section's first N paragraphs
"""
import re
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
first = _rp._pop(ctx.args, "--first")
CITE = _rp.CITE_ANY_RE
CITETEXT = re.compile(r"\\citetext\{((?:[^{}]|\{[^{}]*\})*)\}")
COMMENT = re.compile(r"(?<!\\)%.*$", re.M)
PAT = re.compile(r",\s+((?:a|an|the|one|both|each|this|these|which)\s+[^,;.]{0,90})")
# a tail that runs to the end of its sentence: no comma or semicolon in it,
# and a period only inside a number (2.17)
TAIL = r"(?:[^,;.]|(?<=\d)\.(?=\d)){0,140}(?=\.(?:\s|$)|;|$)"
NOT_PARTICIPLE = ("including", "excluding", "during", "regarding", "concerning", "according",
                  "following", "notwithstanding", "pending", "barring", "considering",
                  "nothing", "something", "anything", "everything", "thing", "morning",
                  "evening", "spring", "string")
WITH = re.compile(r",\s+(with\s" + TAIL + ")")
ING = re.compile(r",\s+((?!(?:%s)\b)[a-z]{2,}ing\b" % "|".join(NOT_PARTICIPLE) + TAIL + ")")


def strip_cites(s):
    s = CITETEXT.sub("", s)
    s = CITE.sub("", s)
    return COMMENT.sub("", s)


def after_main_clause(t, pos):
    """Five or more words between the sentence start and the comma at pos."""
    start = max(t.rfind(". ", 0, pos), t.rfind("? ", 0, pos), t.rfind("! ", 0, pos))
    return len(t[start + 1:pos].split()) >= 5


n = 0
for sec in ctx.sections(ctx.args):
    paras = ["\n".join(pl) for _, pl in _rp.paragraphs(_rp.section_body(sec))]
    if first:
        paras = paras[:int(first)]
    for i, p in enumerate(paras, 1):
        t = re.sub(r"\s+", " ", strip_cites(p))
        found = [(m.start(), "noun", m) for m in PAT.finditer(t)]
        found += [(m.start(), kind, m) for kind, rx in (("with", WITH), ("-ing", ING))
                  for m in rx.finditer(t) if after_main_clause(t, m.start())]
        for _, kind, m in sorted(found, key=lambda x: x[0]):
            n += 1
            print("%s p%d [%s]: ...%s" % (sec.key, i, kind, t[max(0, m.start() - 60):m.end()]))
print("%d candidate(s)" % n)
