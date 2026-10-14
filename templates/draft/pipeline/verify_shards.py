#!/usr/bin/env python3
"""Verify that every PASS-1 record shard was read from the CURRENT slices.

WHY THIS EXISTS
    A shard read from a superseded slice is silently wrong: the file exists, is
    well-formed, has the right headers and counts, and describes material that
    no longer exists on disk.  No mechanical assertion about files catches it.
    It happened here on 2026-08-29 -- a bug ended every chapter at the next
    candidate LINE rather than the next candidate carrying a real JOB, so
    editor and affiliation lines truncated chapters (one introduction came out
    at three lines).  Five finished shards had to be discarded, and the only
    reason anyone noticed was that a reading agent said the material looked
    truncated.

    This makes the check mechanical: PASS-1 records quote verbatim openings, so
    a shard whose quotes no longer occur in the slices was read from something
    else.  A shard is REJECTED above MAX_MISS_RATE, because the convention
    markers ("[displayed equation omitted ...]", "[EXTRACTION UNCLEAR ...]")
    legitimately never appear in a slice and must not be counted as failures.

RUN
    py -3 pipeline/verify_shards.py
    py -3 pipeline/verify_shards.py --verbose
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
SLICES = os.path.join(SKILL, "references", "slices")
SHARDS = os.path.join(SKILL, "references", "records", "_shards")

PROBE_CHARS = 60          # prefix length matched against the slice text
MIN_QUOTE_CHARS = 40      # ignore quotes too short to be diagnostic
PROBE_FP = 40             # fingerprint characters matched (alphanumerics only)


def fp(s):
    """Lowercase alphanumerics only -- the para_numbers.py fingerprint."""
    return re.sub(r"[^a-z0-9]", "", s.lower())
MAX_MISS_RATE = 0.10      # above this the shard is stale, not merely annotated

CONVENTION = re.compile(r"\[(?:displayed equation omitted|EXTRACTION UNCLEAR)")


def load_slices():
    out = {}
    if not os.path.isdir(SLICES):
        return out
    for job in sorted(os.listdir(SLICES)):
        d = os.path.join(SLICES, job)
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "*.txt")):
            key = "%s/%s" % (job, os.path.basename(f)[:-4])
            with io.open(f, encoding="utf-8", errors="replace") as fh:
                out[key] = fh.read()
    return out


def quotes_of(path):
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    found = []
    for q in re.findall(r'^>\s*"?(.{%d,180})' % MIN_QUOTE_CHARS, text, re.M):
        q = q.strip().strip('"').rstrip(".…")
        if CONVENTION.search(q):
            continue
        found.append(q[:PROBE_CHARS])
    return found


def main():
    verbose = "--verbose" in sys.argv
    pool = load_slices()
    if not pool:
        sys.exit("no slices on disk -- has Tier 2 run?")
    if not os.path.isdir(SHARDS):
        print("no shards yet"); return 0
    shards = sorted(f for f in glob.glob(os.path.join(SHARDS, "*.md")))
    if not shards:
        print("no shards yet"); return 0

    fpool = {k: fp(v) for k, v in pool.items()}
    bad = []
    for sh in shards:
        qs = quotes_of(sh)
        if not qs:
            print("  SKIP %-30s (no verbatim quotes found)"
                  % os.path.basename(sh))
            continue
        # Fingerprint match (lowercase alphanumerics only, as para_numbers.fp):
        # a slice keeps the PDF's line breaks -- 33-char median lines in
        # poppler text -- so a raw 60-char prefix spanning a wrap never matched
        # and every shard read STALE (health-policy instance, 2026-10-07).
        misses = [q for q in qs if fp(q)[:PROBE_FP] and not any(fp(q)[:PROBE_FP] in v
                                                               for v in fpool.values())]
        rate = len(misses) / len(qs)
        ok = rate <= MAX_MISS_RATE
        print("  %s %-30s %3d quotes, %2d unmatched (%.0f%%)"
              % ("ok  " if ok else "STALE", os.path.basename(sh),
                 len(qs), len(misses), rate * 100))
        if not ok:
            bad.append(os.path.basename(sh))
        if verbose:
            for m in misses[:5]:
                print("        unmatched: " + m)

    if bad:
        print("\nSTALE shards (re-read them against the current slices, and "
              "move the old ones to _shards/_stale_*/): " + "; ".join(bad))
        return 1
    print("\nall shards verified against the current slices")
    return 0


if __name__ == "__main__":
    sys.exit(main())
