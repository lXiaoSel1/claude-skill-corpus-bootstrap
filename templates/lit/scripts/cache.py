#!/usr/bin/env python3
"""Write attestation results back into the term cache -- safely.

WHY THIS EXISTS
    terms.md calls itself "a real cache, not a hint", but nothing in the skill
    ever wrote to it.  Every verdict was thrown away at the end of the run.
    Measured cost: a single session established that "monotonically" is in 14
    papers, "play an important role" in 13, and "amplifies moral hazard" in
    exactly one (DambraQuinnWertz2023).  None of the three was in terms.md
    afterwards, so the next run would have re-litigated all three.

THE THREE WRITE PROTECTIONS
    This skill directory is NOT tracked by git.  A bad write has no undo, so
    every write goes through all three of these:

    1. APPEND-ONLY.  Existing lines are never rewritten or reordered.  New rows
       are inserted at the end of their section.
    2. TIMESTAMPED BACKUP.  cp terms.md terms.md.bak-<stamp> before touching it.
    3. SURVIVAL CHECK.  Every `w:` count and every cite-key present before the
       write must still be present after.  If any went missing the backup is
       restored automatically and the run fails.  This is the guard that would
       have caught register.md section 4 silently losing terms.md's counts.

THE FRICTION VALVE
    `add` does NOT write to terms.md.  It writes to references/candidates.md.
    Promotion into the cache proper is a separate, explicit `promote` step.
    anti-slop states the reason plainly: candidates go to a candidates file,
    "never straight into the corpus or patterns" -- a cache that auto-promotes
    drifts, and a drifting cache is worse than no cache because it is trusted.

FACTORY FIXES 2026-10-07
    * promote moves rows: promoted blocks leave candidates.md (backup kept),
      so a second `promote --all` no longer duplicates them in terms.md;
    * promote is partial: ready rows go in, BLOCKED and STALE rows are listed
      and stay behind (the mathematics instance's 166 unreviewed rows blocked 600+ good ones);
    * STALE rows -- recorded against a different corpus denominator than the
      current corpus_meta -- are flagged by `list` and refreshed with
      `add --refresh` (156 rows of a mathematics instance still said range:x/27 at 50 papers);
    * cite-keys may start with a digit or contain '-' (P08, 01_PaperX1993,
      AGENCY-2019); the survival check protects them too;
    * REFERENCE-ONLY verdicts (attest.py) route to Section B like THIN.

RUN
    py -3 scripts/cache.py add "monotonically" "play an important role"
    py -3 scripts/cache.py add --refresh            # re-attest every candidate
    py -3 scripts/cache.py list
    py -3 scripts/cache.py promote --all
    py -3 scripts/cache.py promote "monotonically"
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
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
SKILL = os.path.dirname(HERE)
TERMS = os.path.join(SKILL, "references", "terms.md")
CANDIDATES = os.path.join(SKILL, "references", "candidates.md")
ATTEST = os.path.join(HERE, "attest.py")

# A negative row must say WHY, and the reason must come from this closed set.
# An open-ended reason field fills up with "looked wrong to me", which is not a
# refutation anybody can re-check.  terms.md section C already carries two rows
# whose stated reason is a style opinion rather than a corpus result; those are
# exactly the rows nobody can revisit.
REFUSAL_REASONS = {
    "attested-variant-exists": "a different wording IS attested; name it",
    "corpus-contradicts": "the corpus uses the term in another sense",
    "out-of-corpus-domain": "real term, but outside what the terminology-safe papers cover",
}

META = os.path.join(SKILL, "references", "corpus_meta.yaml")
KEY_IN_BRACKETS = r"\[([A-Za-z0-9][A-Za-z0-9_\-]*[A-Za-z][A-Za-z0-9_\-]*)\]"
# at least one letter: numeric citations like [12] in a ctx line are not keys


def current_denominator():
    """terminology_safe from corpus_meta.yaml (the attest default scope)."""
    try:
        with open(META, encoding="utf-8") as fh:
            m = re.search(r"^\s+terminology_safe:\s*(\d+)", fh.read(), re.M)
        return int(m.group(1)) if m else None
    except OSError:
        return None


def is_stale(block, denom):
    m = re.search(r"range:\d+/(\d+)", block)
    return bool(denom and m and int(m.group(1)) != denom)

CANDIDATES_HEADER = """# candidates.md — attestation results awaiting review

> Written by `scripts/cache.py add`. **Nothing here is authoritative yet.**
>
> This file is a friction valve. Attestation results land here first and enter
> `terms.md` only through an explicit `py scripts/cache.py promote`. A cache
> that promotes itself drifts, and a drifting cache is worse than no cache
> because it is trusted.
>
> Review a row, then promote it:
>
> ```
> py scripts/cache.py list
> py scripts/cache.py promote "funding ratio"
> py scripts/cache.py promote --all
> ```
>
> Promotion runs a backup and a survival check over `terms.md` first; see the
> docstring in `scripts/cache.py`.

---

"""


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def run_attest(term):
    """Ask attest.py, so the cache and the reviewer see identical numbers."""
    proc = subprocess.run(
        [sys.executable, ATTEST, "--json", term],
        capture_output=True, text=True, encoding="utf-8",
    )
    if not proc.stdout.strip():
        sys.exit("attest.py produced no output for %r\n%s" % (term, proc.stderr))
    import json
    return json.loads(proc.stdout)[0]


def fingerprint(text):
    """The facts a write must not destroy: every count and every cite-key."""
    counts = set(re.findall(r"\bw:\d+", text))
    keys = set(re.findall(KEY_IN_BRACKETS, text))
    ctx = set(re.findall(r"ctx:\s*\"[^\"]{0,40}", text))
    return counts, keys, ctx


def survival_check(before, after):
    """Return a list of things that vanished.  Empty list means the write was safe."""
    lost = []
    for label, b, a in zip(
        ("w: count", "cite-key", "ctx: line"), fingerprint(before), fingerprint(after)
    ):
        for item in sorted(b - a):
            lost.append("%s %s" % (label, item))
    return lost


def safe_write(path, new_text, old_text):
    """Backup, check BEFORE writing, write, then verify FROM DISK.

    HISTORY -- the first version of this function was a placebo.  It compared
    the two in-memory strings AFTER the file was already written, and its one
    caller constructed new_text as old_text + suffix, so the fingerprint of
    old was a subset of new BY CONSTRUCTION and the check could never fail.
    The advertised third write-protection was a tautology running after the
    destructive write.  Order now: (1) string check pre-write, (2) backup,
    (3) write, (4) re-read the file from disk and verify the disk copy --
    which also catches a torn or truncated write, the case an in-memory
    comparison can never see.
    """
    lost = survival_check(old_text, new_text)
    if lost:
        print("SURVIVAL CHECK FAILED -- nothing written")
        for item in lost[:20]:
            print("  lost: " + item)
        sys.exit(1)
    backup = path + ".bak-" + stamp()
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_text)
    with open(path, encoding="utf-8") as fh:
        on_disk = fh.read()
    lost = survival_check(old_text, on_disk)
    if lost or on_disk != new_text:
        shutil.copy2(backup, path)
        print("DISK VERIFY FAILED -- rolled back from " + os.path.basename(backup))
        for item in lost[:20]:
            print("  lost: " + item)
        sys.exit(1)
    return backup


def insert_into_section(text, section_letter, block):
    """Insert a row block at the END of Section A/B/C, never past it.

    HISTORY -- the first promote appended to end-of-file, which is physically
    inside/after Section C, the negative cache whose header says "refuse
    instantly".  Three ATTESTED/THIN rows landed there: a reviewer following
    the header contract would have instantly refused `monotonically` and
    `play an important role` -- the two original errors this cache exists to
    stop refusing.  Routing is therefore by section, located by heading:
    end of A = just before the Section B heading, end of B = before C,
    end of C = end of file.
    """
    next_heading = {"A": r"(?m)^##\s*Section\s*B\b", "B": r"(?m)^##\s*Section\s*C\b",
                    "C": None}[section_letter]
    if next_heading is None:
        return text.rstrip("\n") + "\n" + block + "\n"
    m = re.search(next_heading, text)
    if not m:
        sys.exit("terms.md has no Section %s boundary heading -- refusing to guess"
                 % {"A": "B", "B": "C"}[section_letter])
    ins = m.start()
    return text[:ins].rstrip("\n") + "\n\n" + block + "\n\n" + text[ins:]


def candidate_row(term, r):
    if r["hits"]:
        # cite-key and ctx: are filled from the attestation itself, never
        # left for a human to remember.  This is the whole fix for the 38
        # of 41 section A rows that shipped without a cite-key: the row
        # cannot be constructed apart from its evidence.
        src = r.get("sample_paper") or (r["papers"][0] if r["papers"] else "?")
        ctx = (r.get("sample") or "").strip().replace("\n", " ").replace('"', "'")
        return ("- **%s** — w:%d · range:%d/%d · research:%d · %.2f/10k · [%s]\n"
                "    verdict: %s · via %s · added %s\n"
                "    ctx: \"%s\"\n"
                % (term, r["hits"], r["range"], r["eligible"],
                   r.get("range_research", r["range"]), r["per_10k"], src,
                   r.get("verdict") or ("ATTESTED" if r["attested"] else "THIN"),
                   "; ".join(r.get("contributions") or [str(r["matched_via"])]),
                   datetime.date.today(), ctx))
    return ("- **%s** — w:0 · range:0/%d · NOT ATTESTED\n"
            "    variants tried: %s\n"
            "    reason: REQUIRED — one of %s\n"
            "    added %s\n"
            % (term, r["eligible"], ", ".join(r["variants_tried"]),
               " | ".join(sorted(REFUSAL_REASONS)), datetime.date.today()))


def cmd_add(args):
    if not os.path.exists(CANDIDATES):
        with open(CANDIDATES, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(CANDIDATES_HEADER)

    with open(CANDIDATES, encoding="utf-8") as fh:
        existing = fh.read()

    if args.refresh:
        # re-attest existing candidates in place (candidates.md is not
        # authoritative, so rewriting it is allowed; a backup is kept)
        targets = set(args.terms) if args.terms else None
        new, n = existing, 0
        for c in parse_candidates():
            if targets is not None and c["term"] not in targets:
                continue
            if "REQUIRED" not in c["block"] and "reason:" in c["block"] \
                    and "NOT ATTESTED" in c["block"]:
                continue          # a reviewed negative keeps its reason
            row = candidate_row(c["term"], run_attest(c["term"])).rstrip("\n")
            new = new.replace(c["block"], row, 1)
            n += 1
        if n:
            shutil.copy2(CANDIDATES, CANDIDATES + ".bak-" + stamp())
            with open(CANDIDATES, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new)
        print("refreshed %d candidate(s) against the current corpus" % n)
        return

    rows = []
    for term in args.terms:
        if re.search(r"^- \*\*%s\*\*" % re.escape(term), existing, re.M):
            print("already a candidate, skipped: " + term
                  + "  (re-attest with: add --refresh \"%s\")" % term)
            continue
        r = run_attest(term)
        row = candidate_row(term, r)
        rows.append(row)
        print("candidate: %s  (w:%d range:%d)" % (term, r["hits"], r["range"]))

    if rows:
        with open(CANDIDATES, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(rows))
        print("\nwrote %d candidate(s) to references/candidates.md" % len(rows))
        print("review, fill every REQUIRED slot, then: py scripts/cache.py promote --all")


def parse_candidates():
    if not os.path.exists(CANDIDATES):
        return []
    with open(CANDIDATES, encoding="utf-8") as fh:
        text = fh.read()
    out = []
    blocks = re.split(r"(?m)^(?=- \*\*)", text)
    for b in blocks:
        m = re.match(r"- \*\*(.+?)\*\*", b)
        if m:
            out.append({"term": m.group(1), "block": b.rstrip("\n")})
    return out


def cmd_list(args):
    cands = parse_candidates()
    if not cands:
        print("no candidates. run: py scripts/cache.py add \"<term>\"")
        return
    denom = current_denominator()
    print("%d candidate(s) in references/candidates.md (corpus denominator now"
          " %s)\n" % (len(cands), denom))
    for c in cands:
        blocked = "REQUIRED" in c["block"]
        stale = is_stale(c["block"], denom)
        state = "BLOCKED" if blocked else ("STALE" if stale else "ready")
        print("  [%s] %s" % (state, c["term"]))
        if blocked:
            for line in c["block"].split("\n"):
                if "REQUIRED" in line:
                    print("      " + line.strip())
    print("\nBLOCKED rows have an unfilled REQUIRED slot; STALE rows were"
          " attested against a different corpus (refresh: add --refresh)."
          " Neither promotes; ready rows do.")


def cmd_promote(args):
    cands = parse_candidates()
    if not cands:
        sys.exit("no candidates to promote")
    wanted = [c for c in cands
              if args.all or c["term"] in args.terms]
    if not wanted:
        sys.exit("no matching candidate; run: py scripts/cache.py list")

    denom = current_denominator()
    blocked = [c for c in wanted if "REQUIRED" in c["block"]]
    stale = [c for c in wanted if c not in blocked and is_stale(c["block"], denom)]
    if blocked or stale:
        print("held back: %d BLOCKED (unfilled REQUIRED slot), %d STALE"
              " (different corpus denominator)" % (len(blocked), len(stale)))
        for c in blocked:
            print("  BLOCKED " + c["term"])
        for c in stale:
            print("  STALE   " + c["term"])
        print("A cache row without its evidence, or with another corpus's"
              " counts, cannot be audited later.\n")
    wanted = [c for c in wanted if c not in blocked and c not in stale]
    if not wanted:
        print("nothing ready to promote. Nothing was written.")
        sys.exit(1)

    with open(TERMS, encoding="utf-8") as fh:
        old = fh.read()

    # Route each row by its verdict: ATTESTED -> Section A (clears with no
    # grep), THIN -> Section B (surface every time -- exactly THIN's
    # semantics: attested by 1-2 papers, never auto-clear), reviewed
    # negatives -> Section C.  No batch markers: each row already carries its
    # own `added YYYY-MM-DD` field, and stacked <!-- promoted --> comments
    # were write-noise.
    new_text = old
    routed = {"A": 0, "B": 0, "C": 0}
    for c in wanted:
        if "verdict: ATTESTED" in c["block"]:
            sec = "A"
        elif ("verdict: THIN" in c["block"]
              or "verdict: REFERENCE-ONLY" in c["block"]):
            sec = "B"
        else:
            sec = "C"
        new_text = insert_into_section(new_text, sec, c["block"])
        routed[sec] += 1
    backup = safe_write(TERMS, new_text, old)

    # move, don't copy: the promoted blocks leave candidates.md, so a second
    # `promote --all` cannot duplicate them into terms.md
    with open(CANDIDATES, encoding="utf-8") as fh:
        cand_text = fh.read()
    shutil.copy2(CANDIDATES, CANDIDATES + ".bak-" + stamp())
    for c in wanted:
        cand_text = cand_text.replace(c["block"] + "\n", "", 1) \
            if c["block"] + "\n" in cand_text else cand_text.replace(c["block"], "", 1)
    with open(CANDIDATES, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(cand_text)

    print("promoted %d row(s) into terms.md  (A:%d  B:%d  C:%d)"
          % (len(wanted), routed["A"], routed["B"], routed["C"]))
    print("  backup: " + os.path.basename(backup))
    print("  survival check: passed pre-write; disk copy verified after")
    print("  removed the promoted rows from candidates.md (backup kept)")
    if blocked or stale:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="attest terms and record them as candidates")
    a.add_argument("terms", nargs="*")
    a.add_argument("--refresh", action="store_true",
                   help="re-attest existing candidates (all, or the named ones)")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="show candidates and what is blocking them")
    l.set_defaults(func=cmd_list)

    p = sub.add_parser("promote", help="move reviewed candidates into terms.md")
    p.add_argument("terms", nargs="*")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_promote)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
