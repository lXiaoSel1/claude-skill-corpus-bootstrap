#!/usr/bin/env python3
"""One-off: give every terms.md section A row the cite-key it should have had.

WHY
    SKILL.md's output format requires corpus evidence to be "reported with the
    paper that attests them".  38 of the 41 section A rows shipped without one,
    so those rows could be quoted but not checked.

    The keys are not invented and not recalled -- each is resolved by running
    scripts/attest.py on the row's own term and taking the paper that supplies
    the concordance line.  A row whose term no longer attests is left alone and
    reported, never guessed at.

SAFETY
    Same three protections as scripts/cache.py, reusing its code rather than
    reimplementing it: timestamped backup, then a survival check that every
    pre-existing w: count, cite-key and ctx: line is still present afterwards,
    with automatic rollback if any went missing.

    Idempotent: rows that already carry a key are skipped.

RUN
    py -3 scripts/backfill_cite_keys.py --dry-run
    py -3 scripts/backfill_cite_keys.py
"""
import argparse
import os
import re
import sys

# Console-safety: a Windows console may not be UTF-8 (e.g. cp936/GBK), and the corpus
# carries U+FFFD in 140 of 165 files (errors="replace" artefacts).  Without
# this, printing a concordance line kills the script mid-report -- measured:
# attest.py died on almost every term, and cohesion.py died AT the M8 line,
# before the JOINS table ever printed.  Never remove.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cache  # noqa: E402  -- reuse safe_write / run_attest, never re-implement

TERMS = cache.TERMS
CITE_RE = re.compile(cache.KEY_IN_BRACKETS)
# shared with cache.py (2026-10-07): keys may start with a digit or contain
# '-' (P08, 01_PaperX1993, AGENCY-2019); the old letter-first author-year
# pattern treated such rows as key-less and re-attested them every run
ROW_RE = re.compile(r"^(\s*-\s+\*\*(.+?)\*\*)(.*)$")


def section_a_bounds(lines):
    """Index range of section A.  Returns (start, end) exclusive of the heading."""
    start = end = None
    for i, l in enumerate(lines):
        if re.match(r"^##\s*(?:Section\s*)?A\b", l, re.I):
            start = i + 1
        elif start is not None and re.match(r"^##\s", l):
            end = i
            break
    return start, (end if end is not None else len(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    old = open(TERMS, encoding="utf-8").read()
    lines = old.split("\n")
    a0, a1 = section_a_bounds(lines)
    if a0 is None:
        sys.exit("could not locate section A in terms.md")

    filled = skipped = unresolved = 0
    for i in range(a0, a1):
        m = ROW_RE.match(lines[i])
        if not m:
            continue
        if CITE_RE.search(lines[i]):
            skipped += 1
            continue
        term = m.group(2).strip()
        r = cache.run_attest(term)
        key = r.get("sample_paper") or (r["papers"][0] if r["papers"] else "")
        if not key:
            print("  unresolved (no longer attests): %s" % term)
            unresolved += 1
            continue
        # Append the key at the end of the row, leaving every existing field
        # byte-identical.  Append-only, per the write contract.
        lines[i] = lines[i].rstrip() + " [%s]" % key
        filled += 1
        print("  %-38s -> [%s]  (w:%d range:%d)"
              % (term[:38], key, r["hits"], r["range"]))

    new = "\n".join(lines)
    print("\nfilled %d · already had one %d · unresolved %d"
          % (filled, skipped, unresolved))

    if args.dry_run:
        print("dry run -- nothing written")
        return
    if not filled:
        print("nothing to do")
        return

    backup = cache.safe_write(TERMS, new, old)
    print("wrote terms.md")
    print("  backup: " + os.path.basename(backup))
    print("  survival check: passed")
    print("\nnow lower terms_md.known_missing_cite_keys in references/registry.json to %d"
          % unresolved)


if __name__ == "__main__":
    main()
