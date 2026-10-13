#!/usr/bin/env python3
"""Verify every Example quote in references/sections/ against the corpus slices.

WHY THIS EXISTS
    PASS2_SPEC says every quoted Example "is later verified by grepping the
    corpus" -- but no script did it; check_drift counted fields and attesting
    papers only. A Version whose example was paraphrased, merged from two
    sentences, or invented passed every mechanical check. (Factory addition,
    health-policy instance, Tier 3, 2026-10-07.)

WHAT COUNTS AS FOUND
    An Example line pairs a straight-quoted sentence with `— <Key> ¶<n>` (or
    S<n> / T<n> / `§...`). The quote's fingerprint -- lowercase alphanumerics
    only, the para_numbers.py fp(), so line wraps, hyphenation breaks and
    punctuation damage do not matter -- must occur in that paper's slice for
    THIS chapter. Elided quotes ("... " / "…" / "[...]") are split and every
    fragment of >= 20 fingerprint characters must occur, in order. A quote found
    only in another chapter's slice of the same paper is reported as ELSEWHERE
    (the slicer put that paragraph in a neighbouring chapter -- read it, it is
    not a fabrication); a quote found in no slice of that paper is MISSING.

    py -3 pipeline/verify_versions.py [chapter ...] [--verbose]

Exit 1 when any quote is MISSING.
"""
import glob
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "references"))
SEC = os.path.join(REF, "sections")
SLI = os.path.join(REF, "slices")
FIELD = re.compile(r"^(Pattern|Example|Use it when|Not this when)\b")
# "quoted sentence"   — Key ¶3   (an optional parenthetical may sit between)
PAIR = re.compile(r'"([^"]{8,}?)"\s*(?:\([^)]*\)\s*)?—\s*([A-Za-z0-9][A-Za-z0-9_\-]*)')
ELIDE = re.compile(r"\s*(?:\.\.\.|…|\[\s*\.\.\.\s*\]|\[…\])\s*")
MIN_FRAG = 20


def fp(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def example_blocks(text):
    """Joined text of every Example field (continuation lines included)."""
    out, cur = [], None
    for line in text.split("\n"):
        if FIELD.match(line) or line.startswith("#"):
            if cur is not None:
                out.append(" ".join(cur))
            cur = [line[len("Example"):]] if line.startswith("Example") else None
            continue
        if cur is not None:
            if line.strip():
                cur.append(line.strip())
            else:
                out.append(" ".join(cur))
                cur = None
    if cur is not None:
        out.append(" ".join(cur))
    return out


def found_in(quote, hay):
    pos = 0
    frags = [fp(f) for f in ELIDE.split(quote)]
    frags = [f for f in frags if len(f) >= MIN_FRAG] or [fp(quote)]
    for f in frags:
        i = hay.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def main():
    verbose = "--verbose" in sys.argv
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    # `_`-prefixed directories are not chapters (e.g. `_unvetted/`, Versions
    # withheld pending the owner's sign-off) -- their quotes have no slice job.
    chapters = want or sorted(d for d in os.listdir(SEC)
                              if os.path.isdir(os.path.join(SEC, d)) and not d.startswith("_"))
    slice_fp = {}
    for p in glob.glob(os.path.join(SLI, "*", "*.txt")):
        job, key = os.path.basename(os.path.dirname(p)), os.path.basename(p)[:-4]
        slice_fp[(job, key)] = fp(open(p, encoding="utf-8", errors="replace").read())
    total = missing = elsewhere = 0
    for ch in chapters:
        n = m = e = 0
        for f in sorted(glob.glob(os.path.join(SEC, ch, "*.md"))):
            for block in example_blocks(open(f, encoding="utf-8").read()):
                for quote, key in PAIR.findall(block):
                    n += 1
                    if found_in(quote, slice_fp.get((ch, key), "")):
                        continue
                    others = [j for (j, k), v in slice_fp.items() if k == key and found_in(quote, v)]
                    if others:
                        e += 1
                        if verbose:
                            print("  ELSEWHERE %s/%s %s (in %s): %s" % (ch, os.path.basename(f), key,
                                                                    ",".join(others), quote[:70]))
                    else:
                        m += 1
                        print("  MISSING   %s/%s %s: %s" % (ch, os.path.basename(f), key, quote[:90]))
        print("%-26s %4d quotes · %d missing · %d elsewhere" % (ch, n, m, e))
        total, missing, elsewhere = total + n, missing + m, elsewhere + e
    print("TOTAL %d quotes · %d missing · %d elsewhere" % (total, missing, elsewhere))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
