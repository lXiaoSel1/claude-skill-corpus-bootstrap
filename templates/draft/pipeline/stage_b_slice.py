"""Stage B - slicing. Purely mechanical: the map says which lines carry which
job, so those lines get written out verbatim. Re-runnable: fix a row in the map,
re-run this, done.

Positional jobs (field-config `positional_jobs`, in document order) are NOT
sliced from headings when no heading carries them:
    the FIRST one (front block, abstract-like)
        = labelled start ("Abstract", or an `abstract_start_markers` label such
          as Summary/Objective) or the first real prose run after the
          title/author/banner matter -> `abstract_end_markers` or the first
          heading, capped at ABS_MAX_CHARS
    each LATER one
        = its `positional_anchors_<job>` match (searched after the previous
          positional block) or, without anchors, right after the previous
          positional block -> the next positional start or the first heading
          carrying a non-positional job

SAFE RE-RUN (2026-10-07): every slice is computed in memory first and every
corpus file is checked to exist; only then are the old slices moved to
references/_slice_backups/<stamp>/ (retired-job folders included) and the new
ones written. The 2026-08 version deleted first and could crash half-way on a
missing corpus file. `--dry-run` prints what would be written and touches
nothing.

    py -3 pipeline/stage_b_slice.py [--dry-run]
"""
import collections
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys

# Console-safety (cp936/GBK consoles + U+FFFD in decoded corpus text). Never
# remove.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
# LAYOUT: a stamped instance puts pipeline/ at the skill root, so references/
# is BASE/../references (the parent kept pipeline/ inside references/).
REF = os.path.normpath(os.path.join(BASE, "..", "references"))
sys.path.insert(0, BASE)
import _jobs  # noqa: E402

CORPUS = _jobs.corpus_dir()
OUT = os.path.join(REF, "slices")
BACKUPS = os.path.join(REF, "_slice_backups")
OPEN_LINES = 25          # how much of each block goes into _openings.md

JOBS = _jobs.require_jobs()
POSITIONAL = [j for j in _jobs.positional_jobs() if j in JOBS]
FRONT = POSITIONAL[0] if POSITIONAL else None

ABS_LABEL = re.compile(r'^\s*(abstract|r[eé]sum[eé])\b\s*[:.]?\s*(.*)$', re.I)
_starts = _jobs.abstract_start_markers()
START_LABEL = re.compile(r'^\s*(?:%s)\b\s*[:.]?\s*(.*)$' % "|".join(_starts),
                         re.I) if _starts else None
# End of the front block. Economics: JEL/keyword lines (the parent's rule, kept
# as the default). A field declares its own in field-config.yaml; quoted
# regexes now parse correctly (the 2026-08 config parser kept the quotes, so
# the mathematics instance's four end markers never matched and 17/38 abstracts over-ran).
_aem = _jobs.abstract_end_markers()
ABS_END = (re.compile("|".join("(?:%s)" % m for m in _aem), re.I) if _aem else
           re.compile(r'^\s*\(?\s*(jel|keywords?|key words|classification)\b',
                      re.I))
BANNER = re.compile(r'(downloaded from|https?://|www\.|electronic copy available|'
                    r'^\s*page\s+\d|©|\bdoi\b|copyright|all rights reserved|'
                    r'received\b|accepted\b|correspond)', re.I)
ABS_MAX_CHARS = 3500      # cap by CHARACTERS, not lines: one reflowed "line"
                          # can be 2000 chars, so a 60-line cap ran to 120k.
PROSE_RUN_LINES = 3       # line-per-line text: a prose run is >=3 lines ...
PROSE_LINE_MIN = 40       # ... each >=40 chars ...
PROSE_RUN_CHARS = 300     # ... totalling >=300 chars (pdftotext default mode
                          # wraps at 38-108 chars, so the old single-line
                          # >150-char test never fired on it)


def load_assignments():
    """(paper, line) -> jobs; later files win (retag overrides waves)."""
    assign = {}
    order = (sorted(glob.glob(os.path.join(BASE, "a2_out_wave*.tsv")))
             + [os.path.join(BASE, n) for n in ("a2_out_delta.tsv",
                                                "a2_out_gap.tsv",
                                                "a2_out_retag.tsv",
                                                "a2_out_zfix.tsv")])
    for p in order:
        if not os.path.exists(p):
            continue
        for ln in open(p, encoding='utf-8'):
            f = ln.rstrip('\n').split('\t')
            if len(f) >= 3:
                try:
                    assign[(f[0].strip(), int(f[1].strip().lstrip('Ll')))] = [
                        j.strip() for j in f[2].strip().split(',') if j.strip()]
                except ValueError:
                    pass
    return assign


def front_span(lines, stop_before):
    """(start, end) 1-indexed, or None. Used only when no heading carries the
    front job."""
    head = min(60, len(lines), max(1, stop_before - 1))
    start = None
    for i in range(head):
        s = lines[i].rstrip()
        m = ABS_LABEL.match(s) or (START_LABEL.match(s) if START_LABEL else None)
        if m:
            rest = m.group(m.lastindex).strip() if m.lastindex else ""
            start = i + 1 if rest else i + 2
            break
    if start is None:
        # No label: the first real prose run after title/author/banner matter.
        for i in range(head):
            s = lines[i].strip()
            if len(s) > 150 and not BANNER.search(s):
                start = i + 1
                break
            run = lines[i:i + PROSE_RUN_LINES]
            if (len(run) == PROSE_RUN_LINES
                    and all(len(x.strip()) >= PROSE_LINE_MIN
                            and not BANNER.search(x) for x in run)
                    and sum(len(x) for x in run) >= PROSE_RUN_CHARS):
                start = i + 1
                break
    if start is None or start >= stop_before:
        return None
    end = front_end(lines, start, stop_before - 1)
    return (start, end) if end >= start else None


# Front-block END without an end marker (health-policy corpus, 2026-10-07): one paper's
# structured abstract is followed by a blank line and the introduction's drop
# cap; another (PMC, one paragraph per line) by its Conclusions paragraph and then
# the introduction. With no Keywords/JEL line both ran to ABS_MAX_CHARS and
# swallowed the whole introduction.
_STRUCT_LABEL = re.compile(
    r'^\s*(?:background|objectives?|purpose|aims?|methods?|design|setting|'
    r'participants|results?|findings|conclusions?|interpretation|implications|'
    r'importance|context)\b', re.I)
_LABEL_ALONE = re.compile(
    r'^\s*(?:background|objectives?|purpose|aims?|methods?|design|setting|'
    r'participants|results?|findings|conclusions?|interpretation|implications|'
    r'importance|context)\s*[:.]?\s*$', re.I)
_CONCL_LABEL = re.compile(r'^\s*(?:conclusions?|interpretation|implications)\s*[:.]?\s*$',
                          re.I)
# Run-in form, label and text on one line: 'Conclusion—Our national estimates
# showed ...' (P08). Its paragraph ends at the first SHORT line ending a
# sentence -- there may be no blank line before the introduction starts.
_CONCL_RUNIN = re.compile(r'^\s*(?:conclusions?|interpretation|implications)\s*[:.—–-]\s*\S',
                          re.I)
# Furniture skipped when deciding what follows a paragraph break: PMC author
# manuscripts print 'Author Manuscript' between every page block (P08's
# Conclusion sat behind one and was lost, 2026-10-07).
_FURNITURE = re.compile(r'^\s*(?:author manuscript|\d{1,4})\s*$', re.I)
FRONT_MIN_CHARS = 400     # a paragraph break before this is title/label debris
PARA_LINE_CHARS = 250     # a line this long is a whole paragraph (PMC/XML text)
RESUME_LOOKAHEAD = 30     # lines searched for the abstract resuming after a break
_EMAIL_ONLY = re.compile(r'^\s*\S+@\S+\.[A-Za-z]{2,}\s*$')
# WEAK end markers: page furniture whose position in the extracted text says
# nothing about where the abstract ends -- an e-mail-only author line, and the
# first-page open-access footnote (P05's sits after the introduction's opening
# lines; as a strong marker it swallowed them, 2026-10-07).
_WEAK_END = re.compile(r'^\s*(?:\S+@\S+\.[A-Za-z]{2,}\s*$|this\s+is\s+an\s+open[- ]access\s+article)',
                       re.I)


def _resumes(lines, i, stop):
    """0-based index of an end-marker line within RESUME_LOOKAHEAD lines after
    line i, provided the abstract's own prose resumes before it (a lowercase-
    initial prose line). Springer prints the author/affiliation block INSIDE the
    abstract: P02 breaks off at L36, lists affiliations, resumes 'and claim
    related factors ...' at L51 and ends at 'Keywords' L55. None otherwise --
    an NBER author block has no lowercase prose (its e-mails are excluded)."""
    cont = False
    for j in range(i + 1, min(stop, len(lines), i + 1 + RESUME_LOOKAHEAD)):
        st = lines[j].strip()
        if not st:
            continue
        # only a STRONG marker closes a resumed abstract: lowercase prose after
        # a drop cap followed by the open-access footnote is the introduction
        if cont and ABS_END.search(lines[j].rstrip()) and not _WEAK_END.match(lines[j]):
            return j
        if (st[0].islower() and len(st) >= 30 and ' ' in st
                and '@' not in st and 'http' not in st):
            cont = True
    return None


LABEL_LOOKAHEAD = 60      # lines searched for a structured label resuming the abstract
_LABEL_START = re.compile(
    r'^\s*(?:methods?|design|setting|participants|results?|findings|conclusions?|'
    r'interpretation|implications)\s*(?:[:.—–]|$)', re.I)


def _label_resumes(lines, i, stop):
    """0-based index of a structured-abstract label (`Methods—`, `Results:`,
    `Conclusions—`, or one standing alone) within LABEL_LOOKAHEAD lines after
    line i and before `stop`. PMC author manuscripts print the correspondence /
    acknowledgment footnote block INSIDE the abstract: P40 breaks after its
    Objectives and resumes with `Methods—` at L71, P12 resumes with
    `Conclusions—` at L87 (2026-10-07). None otherwise."""
    for j in range(i + 1, min(stop, len(lines), i + 1 + LABEL_LOOKAHEAD)):
        if _LABEL_START.match(lines[j]):
            return j
    return None


def front_end(lines, s, e):
    """Last line (1-indexed) of a front block starting at line s, at most e.
    Stops at an `abstract_end_markers` line, at ABS_MAX_CHARS, or at a
    paragraph break once FRONT_MIN_CHARS are in -- unless the text resumes in
    lowercase (the same sentence, broken by an affiliation block or a page:
    P26), resumes before an end marker a little further on (_resumes: P02), or
    continues with another structured-abstract label. A label standing alone on
    its line waits for its paragraph (P69: 'Results:', blank, paragraph). In
    paragraph-per-line text the paragraph after a Conclusions label is the last
    one (P70). Interruptions jumped over (footnote / affiliation blocks) stay
    in the block but do not count toward ABS_MAX_CHARS -- counted, they cut
    P40's abstract at its Conclusions label."""
    stop = min(e, len(lines))
    # A STRONG end marker (Keywords, JEL, Learning Objectives ...; not the weak
    # e-mail-only line) inside the block decides the end outright: everything
    # before it is the abstract, interruptions included. The paragraph-break
    # rules below cut Springer/PMC abstracts short wherever a footnote or
    # affiliation block sat inside them (P02, P40, P67, 2026-10-07); they now
    # apply only when no strong marker is in reach.
    hard = next((j for j in range(s, stop)
                 if ABS_END.search(lines[j].rstrip()) and not _WEAK_END.match(lines[j])),
                None)
    if hard is not None and sum(len(lines[q]) + 1 for q in range(s - 1, hard)) <= 2 * ABS_MAX_CHARS:
        ne = hard                 # 0-based hard is the marker; 1-based hard is the line before
        while ne > s and not lines[ne - 1].strip():
            ne -= 1
        return ne
    chars, ne, after_concl, waiting = 0, s, False, False
    runin, width = False, 0
    i = s - 1
    while i < stop:
        ln = lines[i]
        st = ln.strip()
        if i > s - 1 and ABS_END.search(ln.rstrip()):
            # only a WEAK marker (an e-mail-only line) may be an interruption;
            # Keywords/JEL/Key messages end the block outright
            weak = bool(_WEAK_END.match(ln))
            j = _resumes(lines, i, stop) if weak else None
            if j is None:
                k = _label_resumes(lines, i, stop) if weak else None
                if k is None:
                    break
                i = k             # the abstract resumes at a later label
                continue
            ne, i = j, j          # include the interruption; stop at the marker
            continue
        if not st:
            if chars >= FRONT_MIN_CHARS and not waiting:
                nxt = next((lines[j].strip() for j in range(i + 1, stop)
                            if lines[j].strip() and not _FURNITURE.match(lines[j])), "")
                if nxt and not nxt[0].islower() and not _STRUCT_LABEL.match(nxt):
                    j = _resumes(lines, i, stop)
                    if j is None:
                        k = _label_resumes(lines, i, stop)
                        if k is None:
                            break
                        i = k     # the abstract resumes at a later label
                        continue
                    ne, i = j, j
                    continue
            i += 1
            continue
        chars += len(ln) + 1
        ne = i + 1
        waiting = False
        if after_concl and len(st) >= PARA_LINE_CHARS:
            break
        if _LABEL_ALONE.match(st):
            waiting = True
        if _CONCL_LABEL.match(st):
            after_concl = True
        if _CONCL_RUNIN.match(st):
            runin = True
        if not _FURNITURE.match(st):
            width = max(width, len(st))
        if runin and re.search(r'[.!?]["”’)]?$', st) and (
                len(st) < 0.75 * width or len(st) >= PARA_LINE_CHARS):
            break                 # the run-in Conclusion paragraph has ended
        if chars >= ABS_MAX_CHARS:
            break
        i += 1
    return ne


def anchor_line(lines, job, lo, hi):
    """1-indexed line of the first positional anchor for `job` in [lo, hi)."""
    pats = _jobs.positional_anchors(job)
    if not pats:
        return None
    rx = re.compile("|".join("(?:%s)" % p for p in pats), re.I)
    for i in range(max(0, lo - 1), min(len(lines), hi - 1)):
        if rx.search(lines[i]):
            return i + 1
    return None


def blocks_for(k, lines, cand, assign):
    """(job -> list of (start,end,head)) for this paper, 1-indexed inclusive."""
    r = cand[k]
    cs = sorted(r['candidates'], key=lambda c: c['line'])
    # Assign EVERY candidate's jobs FIRST (doing it inside the range loop left
    # later candidates jobless, and every first chapter swallowed the paper).
    for c in cs:
        c['jobs'] = assign.get((k, c['line']), [])
    for i, c in enumerate(cs):
        # A block ends at the next candidate CARRYING A REAL JOB, not the next
        # candidate of any kind (editor/affiliation lines are NONE).
        # build_map.py carries the identical rule -- change both together.
        # OTHER is a REAL chapter that fits no job: it ends the previous block
        # too (excluding it let two health-policy papers' introductions run
        # through their OTHER chapters to 71-75% of the paper, 2026-10-07).
        _nxt = next((cs[j]['line'] for j in range(i + 1, len(cs))
                     if any(x and x != 'NONE'
                            for x in cs[j].get('jobs', []))), None)
        c['end'] = (_nxt - 1) if _nxt else r['ref_cutoff']
    out = collections.defaultdict(list)
    for c in cs:
        for j in c['jobs']:
            if j in JOBS:
                out[j].append((c['line'], c['end'], c['verbatim']))

    if not FRONT:
        return out
    # The front block stops at the first heading carrying ANY other job --
    # leaving a positional job out of the stop set let an abstract run through
    # the Introduction heading and swallow the chapter (parent: 14.5 KB).
    # An OTHER chapter stops positional blocks too (see the block-end rule above).
    after_front = [c for c in cs
                   if any((j in JOBS and j != FRONT) or j == 'OTHER' for j in c['jobs'])]
    stop_front = after_front[0]['line'] if after_front else r['ref_cutoff']
    after_pos = [c for c in cs
                 if any((j in JOBS and j not in POSITIONAL) or j == 'OTHER'
                        for j in c['jobs'])]
    stop_pos = after_pos[0]['line'] if after_pos else r['ref_cutoff']

    if FRONT not in out:
        sp = front_span(lines, stop_front)
        if sp:
            out[FRONT].append((sp[0], sp[1],
                               '[POSITIONAL: label/first prose -> end marker'
                               ' or first heading]'))
    # Trim EVERY front block, however it was found (a heading-derived abstract
    # once ran to 19 KB having eaten the introduction).
    trimmed = []
    for s, e, head in out.get(FRONT, []):
        # a positional block was already ended by front_end inside front_span;
        # re-trimming it with its own end as the bound cut the look-ahead short
        # (P02 fell back from L54 to L36, 2026-10-07)
        trimmed.append((s, e if head.startswith('[POSITIONAL') else front_end(lines, s, e),
                        head))
    if trimmed:
        out[FRONT] = trimmed

    # Later positional jobs, in order, each after the previous one.
    prev_end = max((e for _, e, _ in out.get(FRONT, [])), default=0)
    later = POSITIONAL[1:]
    starts, how = {}, {}
    for job in later:
        if job in out:
            prev_end = max(e for _, e, _ in out[job])
            continue
        a = anchor_line(lines, job, prev_end + 1, stop_pos)
        starts[job] = a if a else prev_end + 1
        how[job] = "anchor" if a else "after previous positional block"
        prev_end = starts[job]
    for n, job in enumerate(later):
        if job not in starts:
            continue
        nxt = next((starts[j] for j in later[n + 1:] if j in starts), None)
        end = (nxt - 1) if nxt else stop_pos - 1
        if end > starts[job]:
            out[job].append((starts[job], end,
                             '[POSITIONAL: %s -> first non-positional heading]'
                             % how[job]))
    return out


def main():
    dry = "--dry-run" in sys.argv
    cand = json.load(open(os.path.join(BASE, "a1_candidates.json"),
                          encoding='utf-8'))
    assign = load_assignments()

    # ---- preflight: every corpus file present, every slice computed --------
    missing = [k for k in cand
               if not os.path.exists(os.path.join(CORPUS, k + '.txt'))]
    if missing:
        sys.exit("preflight: %d corpus files missing (%s) -- nothing touched"
                 % (len(missing), ", ".join(missing[:8])))
    plan = {}
    for k in sorted(cand):
        with open(os.path.join(CORPUS, k + '.txt'), 'rb') as fh:
            lines = fh.read().decode('utf-8', 'replace').split('\n')
        plan[k] = (lines, blocks_for(k, lines, cand, assign))

    stats = collections.Counter()
    for k, (_, blocks) in plan.items():
        for job in blocks:
            stats[job] += 1
    if dry:
        print("dry run: %d papers" % len(plan))
        for j in JOBS:
            print("  %-28s %d" % (j, stats[j]))
        return

    # ---- back up the old slices (incl. retired-job folders), then clear ----
    if os.path.isdir(OUT) and os.listdir(OUT):
        bak = os.path.join(BACKUPS, datetime.datetime.now().strftime(
            "%Y%m%d-%H%M%S"))
        shutil.copytree(OUT, bak)
        print("previous slices backed up to " + os.path.relpath(bak, REF))
        for name in os.listdir(OUT):
            p = os.path.join(OUT, name)
            if os.path.isdir(p):
                if name in JOBS:
                    for f in os.listdir(p):
                        if f.endswith('.txt') or f == '_openings.md':
                            os.remove(os.path.join(p, f))
                else:
                    shutil.rmtree(p)       # retired job: lives on in the backup
                    print("removed retired job folder slices/%s" % name)
    os.makedirs(OUT, exist_ok=True)

    openings = collections.defaultdict(list)
    manifest = ["# slices/_manifest.md — what Stage B wrote", "",
                "> Generated mechanically from `../chapter-map.md`. No judgement"
                " here: the map says which",
                "> lines carry which job, these are those lines, verbatim."
                " Re-runnable — fix the map, re-slice.",
                "", "| paper | job | blocks | lines | source |",
                "|---|---|---|---|---|"]
    for k, (lines, blocks) in plan.items():
        for job, blks in sorted(blocks.items()):
            d = os.path.join(OUT, job)
            os.makedirs(d, exist_ok=True)
            body, total = [], 0
            for s, e, head in blks:
                # CRLF corpus lines keep their '\r' after split('\n'); writing
                # them through Windows text mode produced '\r\r\n' and doubled
                # every line count for universal-newline readers (2026-10-07).
                seg = [x.rstrip('\r') for x in lines[s - 1:e]]
                total += len(seg)
                body.append(f"===== {k} | L{s}-{e} | {head}")
                body.extend(seg)
                openings[job].append(f"\n## {k}  (L{s}-{e})\n{head}\n" +
                                     "\n".join(seg[:OPEN_LINES]))
            with open(os.path.join(d, k + '.txt'), 'w', encoding='utf-8', newline='\n') as fh:
                fh.write("\n".join(body))
            src = ('POSITIONAL' if any('POSITIONAL' in h for _, _, h in blks)
                   else 'heading')
            manifest.append(f"| {k} | `{job}` | {len(blks)} | {total} | {src} |")

    for job, chunks in openings.items():
        with open(os.path.join(OUT, job, "_openings.md"), 'w',
                  encoding='utf-8', newline='\n') as fh:
            fh.write(f"# {job} — opening {OPEN_LINES} lines of every block,"
                     f" all papers\n" + "\n".join(chunks))

    n = len(cand)
    manifest += ["", "---", "", "## Denominators — use these, not the corpus"
                 " size", "", "| job | papers with a slice |", "|---|---|"]
    for j in JOBS:
        manifest.append(f"| `{j}` | {stats[j]}/{n} |")
    manifest += ["", "### Papers with NO slice for a job", ""]
    for j in JOBS:
        gaps = sorted(k for k in cand if k not in {
            f[:-4] for f in (os.listdir(os.path.join(OUT, j))
                             if os.path.isdir(os.path.join(OUT, j)) else [])})
        if gaps and len(gaps) <= 12:
            manifest.append(f"- **`{j}`** ({len(gaps)}): " + ", ".join(gaps))
        elif gaps:
            manifest.append(f"- **`{j}`** ({len(gaps)} papers — record at the"
                            " A3 gate whether the job is genuinely absent)")
    if FRONT:
        manifest += ["", f"Papers with no `{FRONT}` slice are usually extraction"
                     " damage (the front text fused to an author or masthead"
                     " line) — check each against the corpus file before"
                     " calling it a rule failure.", ""]
    with open(os.path.join(OUT, "_manifest.md"), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write("\n".join(manifest))

    print(f"{'job':28s} {'papers':>7s} {'slice KB':>9s} {'openings KB':>12s}")
    for j in JOBS:
        d = os.path.join(OUT, j)
        if not os.path.isdir(d):
            print(f"{j:28s} {0:7d}")
            continue
        kb = sum(os.path.getsize(os.path.join(d, f))
                 for f in os.listdir(d) if f.endswith('.txt')) // 1024
        op = os.path.join(d, "_openings.md")
        ok = os.path.getsize(op) // 1024 if os.path.exists(op) else 0
        print(f"{j:28s} {stats[j]:7d} {kb:9d} {ok:12d}")

    # Slice fingerprint: records/ shards are read BY AGENTS from these files,
    # and a shard read from a superseded slice is silently wrong. check_drift
    # compares this fingerprint with the slices on disk and with the
    # fingerprint each records/ shard header quotes.
    fp = {}
    for j in JOBS:
        d = os.path.join(OUT, j)
        if not os.path.isdir(d):
            continue
        h = hashlib.sha256()
        for f in sorted(x for x in os.listdir(d) if x.endswith(".txt")):
            with open(os.path.join(d, f), "rb") as fh:
                h.update(f.encode())
                h.update(fh.read())
        fp[j] = h.hexdigest()[:16]
    with open(os.path.join(OUT, "_fingerprint.json"), "w", encoding="utf-8") as fh:
        json.dump({"built": datetime.date.today().isoformat(),
                   "per_job_sha256_16": fp}, fh, indent=1)
    print("slice fingerprint written for %d jobs" % len(fp))


if __name__ == "__main__":
    main()
