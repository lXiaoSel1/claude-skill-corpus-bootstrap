#!/usr/bin/env python3
"""Maintain references/manuscript-state.md — this skill's cross-run memory.

WHY THIS EXISTS
    Before 2026-08-26 nothing flowed back between drafting runs: which Version
    a paragraph used, which the author rejected, which source lines had already
    been pasted and ownership-adjudicated -- all of it was re-derived from
    scratch every session, and the same Version could be offered for adjacent
    paragraphs with no memory that it was just used.  This file is the
    write-path; it is the ONLY file a drafting run may write (the behavioural
    contract in SKILL.md), mirroring mimic-lit's cache.py: explicit command,
    backup before write, disk read-back after.

WHAT IT HOLDS
    §A Versions used   -- chapter ¶ · part · Version · date · accepted/placed
    §B Versions rejected -- and the author's stated reason (verbatim if given)
    §C Source-line cache -- cite-key · licensed verb · ownership verdict ·
       verbatim line (file:line), so the attribution guard's step 2 paste and
       step 3 adjudication survive between sessions.  A cached row is REUSED,
       not re-litigated; a row is invalidated only by editing this file.

RUN
    py -3 scripts/state.py use     <chapter> <part> <version-no> "<label>" [¶n]
    py -3 scripts/state.py reject  <chapter> <part> <version-no> "<reason>"
    py -3 scripts/state.py cache   <cite-key> <verb> <owner-verdict> "<verbatim line>" "<file:line>"
    py -3 scripts/state.py list    [chapter]
"""
import datetime
import os
import re
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
# DRAFT_STATE_PATH override exists ONLY so the regression suite can exercise
# the write path against a scratch file instead of the live state.
STATE = os.environ.get("DRAFT_STATE_PATH") or os.path.join(
    SKILL, "references", "manuscript-state.md")

HEADER = """# manuscript-state.md — cross-run drafting state (written ONLY by scripts/state.py)

> The one file a drafting run writes. Behavioural contract: SKILL.md's
> write-path whitelist names exactly this file; everything else stays
> read-only. Rows are appended by `py -3 scripts/state.py`; invalidate a row by
> deleting it here by hand.

## A. Versions used

| date | chapter ¶ | part | Version | label |
|---|---|---|---|---|

## B. Versions rejected (author's call, with reason)

| date | chapter ¶ | part | Version | reason |
|---|---|---|---|---|

## C. Source-line cache (paste once, reuse forever)

| cite-key | verb | ownership | source line (verbatim) | at |
|---|---|---|---|---|
"""


def load():
    if not os.path.exists(STATE):
        with open(STATE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(HEADER)
    with open(STATE, encoding="utf-8") as fh:
        return fh.read()


def safe_write(new):
    """Backup, write, read back from disk, verify."""
    if os.path.exists(STATE):
        shutil.copy2(STATE, STATE + ".bak")
    with open(STATE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    with open(STATE, encoding="utf-8") as fh:
        ondisk = fh.read()
    if ondisk != new:
        sys.exit("write-back verification FAILED -- restore from .bak")


def append_row(section_heading, row):
    text = load()
    idx = text.find(section_heading)
    if idx < 0:
        sys.exit("state file corrupt: missing " + section_heading)
    nxt = text.find("\n## ", idx + 1)
    block_end = nxt if nxt >= 0 else len(text)
    insert = text.rstrip()[:0]  # noqa (clarity)
    head, tail = text[:block_end].rstrip("\n"), text[block_end:]
    if tail.strip():
        safe_write(head + "\n" + row + "\n\n" + tail.lstrip("\n"))
    else:
        safe_write(head + "\n" + row + "\n")
    print("recorded:", row)


def esc(s):
    return s.replace("|", "\\|").replace("\n", " ").strip()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    today = datetime.date.today().isoformat()

    if cmd == "use":
        ch, part, ver, label = sys.argv[2:6]
        para = sys.argv[6] if len(sys.argv) > 6 else ""
        append_row("## A. Versions used",
                   "| %s | %s %s | %s | %s | %s |"
                   % (today, esc(ch), esc(para), esc(part), esc(ver), esc(label)))
    elif cmd == "reject":
        ch, part, ver, reason = sys.argv[2:6]
        append_row("## B. Versions rejected",
                   "| %s | %s | %s | %s | %s |"
                   % (today, esc(ch), esc(part), esc(ver), esc(reason)))
    elif cmd == "cache":
        key, verb, owner, line, at = sys.argv[2:7]
        append_row("## C. Source-line cache",
                   "| %s | %s | %s | %s | %s |"
                   % (esc(key), esc(verb), esc(owner), esc(line)[:200], esc(at)))
    elif cmd == "list":
        text = load()
        if len(sys.argv) > 2:
            pat = re.compile(re.escape(sys.argv[2]), re.I)
            for l in text.split("\n"):
                if l.startswith("|") and pat.search(l):
                    print(l)
        else:
            print(text)
    else:
        sys.exit("unknown command: " + cmd + "\n" + __doc__)


if __name__ == "__main__":
    main()
