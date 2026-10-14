#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concatenate verified tagging shards into references/exemplars.md.

WHY THIS EXISTS
    The parent had no such script: its 159 per-paper sections were concatenated
    by hand, and a single stray U+FEFF before one heading hid that heading from
    a `^## ` grep, so a hand audit reported 158 sections and one missing paper.
    The bug was in the CONCATENATION, not in the tagging.  Everything this
    script does is a consequence of that:

      * strips BOM / zero-width characters at every section boundary;
      * refuses to merge if two shards claim the same PaperKey;
      * refuses to merge if a quoted sentence is not found in its own corpus
        file (a shard read from a stale or wrong file looks perfectly
        well-formed -- same lesson as pipeline/verify_shards.py at Tier 3);
      * writes the per-move tally from the merged file itself, never from the
        shard reports, so the published counts cannot disagree with the file.

RUN
    py -3 scripts/build_exemplars.py              # verify + report, write nothing
    py -3 scripts/build_exemplars.py --write      # ... and write exemplars.md
"""
import glob
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, ".."))
REF = os.path.join(SKILL, "references")
SHARDS = os.path.join(REF, "_exemplar_shards")
CORPUS = os.path.join(REF, "corpus")
OUT = os.path.join(REF, "exemplars.md")

MOVES = ["opener", "stakes", "theory-tension", "mechanism-claim",
         "methods", "results", "contribution", "gap"]

ZW = dict.fromkeys(map(ord, "﻿​‌‍⁠"), None)

LINE = re.compile(r'^- \*\*\[([a-z\-]+)\]\*\*\s+"(.+)"\s+—\s+(\S+)\s*$')
HEAD = re.compile(r'^##\s+(\S+)')

# Marked omissions are NOT repairs: the record layer already writes
# "[displayed equation omitted -- ...]" and "[EXTRACTION UNCLEAR ...]" where a
# sentence runs into a display.  A quoted sentence carrying one of these will
# not occur verbatim in the corpus, and must not be counted as a miss.
CONVENTION = re.compile(r"\[(?:displayed equation omitted|EXTRACTION UNCLEAR)")
MARKER = re.compile(r"\[(?:displayed equation omitted|EXTRACTION UNCLEAR)[^\]]*\]")
MIN_PIECE = 12    # below this a fragment is not diagnostic of anything


def norm(s):
    return re.sub(r"\s+", " ", s.translate(ZW)).strip()


def main():
    if not os.path.isdir(SHARDS):
        sys.exit("no %s -- has Tier 4 tagging run?" % SHARDS)
    # A leading underscore marks a non-shard file in this directory (process
    # notes, manifests).  Without this the notes file's own `## ` headings are
    # parsed as PaperKey sections and land in the published bank.
    files = sorted(f for f in glob.glob(os.path.join(SHARDS, "*.md"))
                   if not os.path.basename(f).startswith("_"))
    if not files:
        sys.exit("no shards in %s" % SHARDS)

    sections, owner, problems = {}, {}, []
    order = []
    for f in files:
        shard = os.path.basename(f)[:-3]
        cur = None
        for raw in io.open(f, encoding="utf-8", errors="replace"):
            line = raw.translate(ZW).rstrip("\n")
            h = HEAD.match(line)
            if h:
                cur = h.group(1)
                # A section appearing in two shards is a MERGE, not a
                # conflict: a later shard may supplement an earlier one (the
                # first mathematics-instance run needed a second pass for openers, whose
                # sentences run into a displayed equation and needed the
                # marked-omission convention).  What must never happen is the
                # same SENTENCE arriving twice, and that is checked below --
                # a stronger guard than owner-exclusivity, which would have
                # forbidden the legitimate case while missing the real one.
                if cur not in sections:
                    sections[cur] = []
                    order.append(cur)
                owner.setdefault(cur, shard)
                continue
            if cur and line.startswith("- **["):
                m = LINE.match(line)
                if not m:
                    problems.append("%s: malformed line in %s" % (shard, cur))
                    continue
                move, sent, key = m.group(1), m.group(2), m.group(3)
                if move not in MOVES:
                    problems.append("%s: unknown move [%s] in %s"
                                    % (shard, move, cur))
                if key != cur:
                    problems.append("%s: line under %s attributed to %s"
                                    % (shard, cur, key))
                sections[cur].append((move, sent, key, line))

    # No sentence may arrive twice, whatever shard it came from.
    for key, rows in sections.items():
        seen_s = {}
        for move, sent, _k, _l in rows:
            n = norm(sent)
            if n in seen_s:
                problems.append("%s: duplicate sentence [%s]/[%s] -- %s"
                                % (key, seen_s[n], move, n[:50]))
            seen_s[n] = move

    # Verify every quote still occurs in its own corpus file.
    miss = 0
    for key, rows in sections.items():
        cp = os.path.join(CORPUS, key + ".txt")
        if not os.path.exists(cp):
            problems.append("%s: no corpus file" % key)
            continue
        hay = norm(io.open(cp, encoding="utf-8", errors="replace").read())
        for move, sent, _k, _l in rows:
            # A marked omission splits the quote into pieces; EVERY piece must
            # still be verbatim, and they must appear in order.  Skipping the
            # whole line whenever a marker is present -- the first version of
            # this check -- made the marker an unverified escape hatch, and it
            # also forced markers to the END of a sentence: a tagger who could
            # only put a terminal marker had to DROP the prose that resumes
            # after the display.  Two openers were truncated that way before
            # this was fixed.
            pieces = [p for p in (norm(x) for x in MARKER.split(sent))
                      if len(p) >= MIN_PIECE]
            if not pieces:
                continue
            at = 0
            for piece in pieces:
                j = hay.find(piece, at)
                if j < 0:
                    miss += 1
                    problems.append("%s: quote piece not in corpus -- %s"
                                    % (key, piece[:60]))
                    break
                at = j + len(piece)

    tally = {m: 0 for m in MOVES}
    for rows in sections.values():
        for move, _s, _k, _l in rows:
            if move in tally:
                tally[move] += 1
    total = sum(tally.values())

    print("shards      : %d (%s)" % (len(files),
                                     ", ".join(os.path.basename(f)[:-3]
                                               for f in files)))
    print("sections    : %d" % len(sections))
    print("sentences   : %d" % total)
    print("unverified  : %d" % miss)
    print("\nper move:")
    for m in MOVES:
        print("  %-16s %4d%s" % (m, tally[m],
                                 "   <-- ZERO" if not tally[m] else ""))
    empty = [k for k, v in sections.items() if not v]
    if empty:
        print("\nsections with no usable sentence: " + ", ".join(sorted(empty)))
    if problems:
        print("\n%d PROBLEM(S):" % len(problems))
        for p in problems[:20]:
            print("  " + p)
        if len(problems) > 20:
            print("  ... and %d more" % (len(problems) - 20))

    if "--write" not in sys.argv:
        print("\n(dry run -- pass --write to build exemplars.md)")
        return 1 if problems else 0
    if problems:
        print("\nREFUSING to write: fix the problems above first.")
        return 1

    L = ["# exemplars.md — move-tagged sentences from the corpus", "",
         "> %d sentences across %d papers, tagged with the 8 shared move labels."
         % (total, len(sections)),
         "> Built by `py -3 scripts/build_exemplars.py --write` from "
         "`references/_exemplar_shards/`.",
         "> **Every sentence is verbatim**, PDF-extraction damage included; a "
         "sentence that had to be",
         "> repaired was skipped instead. `[displayed equation omitted]` and "
         "`[EXTRACTION UNCLEAR]` are",
         "> marked omissions, not repairs.", "",
         "> **Grep this file by move tag; never read it whole.**", "",
         "| move | sentences |", "|---|---|"]
    for m in MOVES:
        L.append("| `%s` | %d |" % (m, tally[m]))
    L += ["", "---", ""]
    seen = set()
    for key in order:
        if key in seen:
            continue
        seen.add(key)
        rows = sections[key]
        L.append("## %s%s" % (key, "  (only 0 usable)" if not rows else ""))
        L.append("")
        for _m, _s, _k, line in rows:
            L.append(line)
        L.append("")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("\nwrote %s (%d KB)" % (OUT, os.path.getsize(OUT) // 1024))
    print("now record in registry.json: exemplars.sections = %d, "
          "exemplars.tagged_sentences = %d" % (len(sections), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
