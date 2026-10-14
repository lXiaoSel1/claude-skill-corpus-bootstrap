#!/usr/bin/env python3
"""Tier-aware consistency check for a stamped <field>-draft instance.

Same doctrine as the parents: invariants in references/registry.json (with
_why), re-derived from disk, PASS/FAIL per line, exit 0 only if clean.
Sections gate on registry.built_tiers.

RUN
    py -3 scripts/check_drift.py
"""
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REF = os.path.join(SKILL, "references")
SEC = os.path.join(REF, "sections")

with open(os.path.join(REF, "registry.json"), encoding="utf-8") as fh:
    REG = json.load(fh)
TIERS = set(int(t) for t in REG.get("built_tiers", []))

failures = []
n_checks = 0


def check(name, ok, detail=""):
    global n_checks
    n_checks += 1
    print("  %s %-56s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        failures.append(name)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


print("%s-draft drift check (built tiers: %s)\n"
      % (REG.get("field", "?"), sorted(TIERS) or "none"))

# ---- always-on skeleton ----------------------------------------------------
print("skeleton")
for s in ("draftcheck.py", "state.py", "build_evidence_map.py",
          "measure_structure.py", "measure_verbs.py", "_fieldstyle.py",
          "check_canon_quotes.py"):
    check("scripts/%s exists" % s, os.path.exists(os.path.join(HERE, s)))
for p in ("_jobs.py", "_cfgparse.py", "a1_headings.py", "a2_build.py",
          "build_map.py", "build_names.py", "build_windows.py",
          "stage_b_slice.py", "recall.py", "recount.py", "para_numbers.py",
          "verify_shards.py"):
    check("pipeline/%s exists" % p,
          os.path.exists(os.path.join(SKILL, "pipeline", p)))
check("field-config.yaml exists",
      os.path.exists(os.path.join(REF, "field-config.yaml")))
sk_path = os.path.join(SKILL, "SKILL.md")
if os.path.exists(sk_path):
    sk = read(sk_path)
    _TOKEN = "{{" + "FIELD" + "}}"   # concatenated so stamping can't eat it
    check("no unstamped field tokens in SKILL.md", _TOKEN not in sk)
    # 2026-10-07: the template wraps the parent's chapters, denominators,
    # paragraph statistics and verb ladder in PARENT-BLOCK tier=N markers. A
    # block still present at a built tier means this instance is quoting
    # economics' numbers as its own (a mathematics instance shipped "all nine" chapters under
    # a twelve-job table and the parent's verb ladder this way).
    stale = sorted(int(n) for n in re.findall(r"<!-- PARENT-BLOCK tier=(\d)",
                                               sk) if int(n) in TIERS)
    check("no PARENT-BLOCK left for a built tier", not stale,
          "tiers %s still carry parent text" % stale if stale else "")

# ---- Tier 2: chapter map ---------------------------------------------------
if 2 in TIERS:
    print("\ntier 2 (chapter map)")
    sys.path.insert(0, os.path.join(SKILL, "pipeline"))
    import _jobs
    jobs = _jobs.jobs()
    check("taxonomy approved (jobs in config)", bool(jobs),
          ", ".join(jobs[:6]))
    check("registry chapters match config jobs",
          set(REG["sections"]["chapters"].keys()) <= set(jobs)
          if jobs else False)
    for f in ("chapter-map.md", "chapter-names.md"):
        check("references/%s exists" % f,
              os.path.exists(os.path.join(REF, f)))
    slices = os.path.join(REF, "slices")
    check("slices/ + _manifest.md exist",
          os.path.isdir(slices)
          and os.path.exists(os.path.join(slices, "_manifest.md")))
    ga = REG["chapter_map"].get("gate_agreement")
    check("A3 gate agreement recorded and >= 0.9",
          ga is not None and float(ga) >= 0.9, str(ga))
    if os.path.isdir(slices):
        dirs = {d for d in os.listdir(slices)
                if os.path.isdir(os.path.join(slices, d))}
        retired = sorted(dirs - set(jobs))
        check("no slice folders for retired jobs", not retired,
              ", ".join(retired))
        # The fingerprint stage_b_slice wrote must still describe the slices
        # on disk -- a records/ shard read from a superseded slice looks
        # complete while describing material that no longer exists.
        fpp = os.path.join(slices, "_fingerprint.json")
        if os.path.exists(fpp):
            import hashlib
            fp = json.load(open(fpp, encoding="utf-8")).get(
                "per_job_sha256_16", {})
            stale = []
            for j, want in fp.items():
                d = os.path.join(slices, j)
                h = hashlib.sha256()
                for f in sorted(x for x in os.listdir(d) if x.endswith(".txt")) \
                        if os.path.isdir(d) else []:
                    with open(os.path.join(d, f), "rb") as fh:
                        h.update(f.encode())
                        h.update(fh.read())
                if h.hexdigest()[:16] != want:
                    stale.append(j)
            check("slices on disk match _fingerprint.json", not stale,
                  "changed since slicing: " + ", ".join(stale))
            # 2026-10-07: CRLF corpus lines written in Windows text mode came
            # out '\r\r\n' -- universal-newline readers saw every line twice.
            import glob
            cr = [os.path.relpath(p, slices) for p in glob.glob(
                  os.path.join(slices, "*", "*.txt"))
                  if b"\r" in open(p, "rb").read()]
            check("slices are LF-only (no carriage returns)", not cr,
                  "%d files, e.g. %s" % (len(cr), ", ".join(cr[:2])) if cr else "")
        else:
            check("slices/_fingerprint.json exists", False,
                  "rerun pipeline/stage_b_slice.py")

# ---- Tier 3: records + sections -------------------------------------------
if 3 in TIERS:
    print("\ntier 3 (records + Versions)")
    records = os.path.join(REF, "records")
    nrec = len([f for f in os.listdir(records) if f.endswith(".md")]) \
        if os.path.isdir(records) else 0
    check("records/ non-empty", nrec > 0, "%d files" % nrec)
    # an empty or unfilled registry must not pass by skipping every check below
    check("registry sections.chapters recorded", bool(REG["sections"].get("chapters")),
          "no chapter recorded: Tier 3 has nothing to check")
    total_v = 0
    total_f = 0
    bad_fields, thin = [], []
    # FACTORY: two ways this regex was wrong for a stamped instance.
    # (1) [A-Za-z] first: the parent's keys are AuthorYear, so a leading letter was
    #     safe; an instance whose keys are numbered (07_GengQP2022) matched NOTHING,
    #     and every Version in such a chapter read "attested by <2 papers".
    # (2) A paper contributing several sections to one chapter is attributed
    #     "— Key §6 ¶1", a shape the parent never produced. Both must match.
    # (3) BACK-PORTED 2026-10-07 from a mathematics instance (2026-09-08): a chapter may number
    #     entries in a SECOND series -- `Tn` for set-off statements, `Sn` for
    #     abstract sentences. Without `T` every such Version read "<2 papers".
    # (4) 2026-10-07: keys may contain '-' (AGENCY-2019); the class stopped at
    #     the hyphen, so the key never reached the ¶ that the regex requires.
    key_re = re.compile(r"—\s+([A-Za-z0-9][A-Za-z0-9_\-]+)"
                        r"(?:\s+§[^¶]*)?\s*(?:¶|S\d|T\d|\()")
    FIELDS = REG["sections"]["fields"]
    for ch, meta in REG["sections"]["chapters"].items():
        d = os.path.join(SEC, ch)
        # FACTORY: a chapter may be deliberately not drafted -- a field can have a
        # job whose paragraphs are not prose at all.  In this instance `proof` and
        # `machinery` are chains of displayed equations: the records exist, the
        # slices exist, and there is no paragraph shape to induce.  That must be a
        # DECLARATION in the registry, never a tolerated failure, so a chapter with
        # sections_built:false is asserted ABSENT and a directory appearing there
        # later fails the check.
        if meta.get("sections_built") is False:
            check("sections/%s declared not-drafted, and absent" % ch,
                  not os.path.isdir(d),
                  "directory exists but registry says it should not")
            continue
        if not os.path.isdir(d):
            check("sections/%s exists" % ch, False)
            continue
        files = [f for f in os.listdir(d) if f.endswith(".md")]
        total_f += len(files)
        count = 0
        for f in files:
            if f == "00-skeleton.md":
                continue
            text = read(os.path.join(d, f))
            heads = list(re.finditer(r"(?m)^### Version \d+", text))
            count += len(heads)
            for i, m in enumerate(heads):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
                b = text[m.start():end]
                if not all(re.search(r"(?m)^%s\s" % re.escape(fl), b)
                           for fl in FIELDS):
                    bad_fields.append("%s/%s" % (ch, f))
                if len(set(key_re.findall(b))) < REG["sections"]["min_attesting_papers"]:
                    thin.append("%s/%s" % (ch, f))
        total_v += count
        check("%s: %s Versions" % (ch, meta.get("versions")),
              meta.get("versions") is not None and count == meta["versions"],
              "found %d%s" % (count, "" if meta.get("versions") is not None
                              else "; registry count not recorded"))
        # BACK-PORTED 2026-10-07 from a mathematics instance (2026-09-08): the PASS2 size rule
        # keeps a chapter under 25 KB as a single <chapter>.md, so only a SPLIT
        # chapter must carry a skeleton.
        single = [f for f in files if f == "%s.md" % ch]
        if len(files) == 1 and single:
            check("%s is single-file (under the 25 KB split rule)" % ch,
                  os.path.getsize(os.path.join(d, single[0])) <= 25600,
                  "%d B" % os.path.getsize(os.path.join(d, single[0])))
        else:
            check("%s has 00-skeleton.md" % ch, "00-skeleton.md" in files)
    check("total Versions == registry",
          REG["sections"].get("total_versions") is not None
          and total_v == REG["sections"]["total_versions"],
          "found %d; registry %s" % (total_v, REG["sections"].get("total_versions")))
    check("every Version carries all four fields", not bad_fields,
          "; ".join(bad_fields[:3]))
    check("every Version attested by >=%d papers"
          % REG["sections"]["min_attesting_papers"], not thin,
          "; ".join(thin[:3]))
    # 2026-10-07: the Example quotes themselves, not just their count -- a
    # paraphrased or invented example passed every check above.
    import subprocess
    vv = subprocess.run([sys.executable, os.path.join(SKILL, "pipeline", "verify_versions.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("every Example quote found in its paper's slices (verify_versions.py)",
          vv.returncode == 0, (vv.stdout.strip().splitlines() or ["no output"])[-1]
          + ("" if vv.returncode == 0 else "  -> py -3 pipeline/verify_versions.py --verbose"))
    check("uniformity calibration recorded",
          bool(REG["uniformity_gate"].get("paragraphs") and REG["uniformity_gate"].get("triples")
               and REG["uniformity_gate"].get("pairs")),
          "uniformity_gate paragraphs/triples/pairs (py -3 pipeline/recount.py)")

# ---- Tier 4: writing canon --------------------------------------------------
# FACTORY GAP CLOSED 2026-08-29: SKILL.md cites structure-canon.md as the
# authority behind several drafting gates (Q3, Q5/Q6, Q7, D5, D7), and the
# template shipped neither the file nor any assertion about it -- so every
# stamped instance cited an authority that did not exist.  The canon SOURCES
# are field-invariant published guides and live once, at factory level; the
# canon FILE is per-instance, because every rule's corpus status must be
# re-measured.  Both are asserted here.
if 4 in TIERS:
    print("")
    print("tier 4 (writing canon)")
    sc = os.path.join(REF, "structure-canon.md")
    check("structure-canon.md exists", os.path.exists(sc))
    # FACTORY FIX 2026-10-07: was SKILL/../corpus-bootstrap/..., which only
    # exists when the instance is stamped next to the factory; `--dest`
    # instances failed Tier 4 by construction. stamp.py now writes the
    # absolute canon_dir into field-config.yaml.
    sys.path.insert(0, os.path.join(SKILL, "pipeline"))
    import _jobs
    canon = _jobs.canon_dir()
    cs = REG.get("canon_sources") or {}
    if os.path.isdir(canon):
        n_txt = len([f for f in os.listdir(canon) if f.endswith(".txt")])
        check("canon-sources: %s txt + manifest" % cs.get("count", "?"),
              n_txt == cs.get("count")
              and os.path.exists(os.path.join(canon, "_manifest.md")),
              "found %d" % n_txt)
        # A quotation whose pointer has rotted is worse than no quotation:
        # building this instance found FIVE such pointers in the parent's own
        # canon file, one of them aimed at a blank line.
        sq = cs.get("spot_quotes") or {}
        bad = [f for f, q in sq.items()
               if not (os.path.exists(os.path.join(canon, f))
                       and q in read(os.path.join(canon, f)))]
        need = min(3, n_txt)
        check("canon spot-quotes greppable verbatim", not bad and len(sq) >= need,
              "missing in: " + ", ".join(bad) if bad else "%d spot quotes (need %d)" % (len(sq), need))
    else:
        check("canon-sources reachable at the factory path", False, canon)
    if os.path.exists(sc):
        t = read(sc)
        check("canon file points at the shared source store",
              "canon-sources" in t)
        # An instance that inherited the parent's verdicts wholesale would have
        # no TO-MEASURE tags at all; that is the signature to catch.
        check("canon carries TO-MEASURE tags for unmeasured rules",
              "TO-MEASURE" in t,
              "every rule claims a measurement -- inherited verdicts?")
        if os.path.isdir(canon):
            sys.path.insert(0, HERE)
            import check_canon_quotes as ccq
            res = ccq.verify(t, canon)
            bad = ccq.failing(res)
            check("canon quotes verbatim at their pointers", not bad,
                  "%d of %d failing (py -3 scripts/check_canon_quotes.py)"
                  % (len(bad), len(res["quotes"])) if bad else "%d quotes" % len(res["quotes"]))

# ---- Tier 4: verb ladder ---------------------------------------------------
# FACTORY GAP CLOSED 2026-08-29: the parent asserts its verb-ladder counts and
# that the ladder's recompute command is a script rather than a hand grep, but
# no tier-4 block was carried into the template -- so a stamped instance could
# ship a ladder inherited wholesale from the parent's field and nothing would
# fail.  In a mathematics corpus the parent's headline phrase (`consistent
# with`, 996 hits there) occurs ZERO times; an unasserted ladder is not a
# small drift.
if 4 in TIERS:
    print("")
    print("tier 4 (verb ladder)")
    vlp = os.path.join(REF, "verb-ladder.md")
    check("verb-ladder.md exists", os.path.exists(vlp))
    if os.path.exists(vlp):
        vl = read(vlp)
        check("verb-ladder is generated, not hand-written",
              "scripts/measure_verbs.py" in vl,
              "no generator command named in the file")
        counts = REG.get("verb_ladder_counts") or {}
        check("verb-ladder counts recorded in registry", bool(counts))
        missing = [k for k, v in counts.items()
                   if ("| `%s` | %d |" % (k, v)) not in vl]
        check("registry counts match the ladder on disk", not missing,
              "stale: " + ", ".join(missing[:4]))
        check("hand-written reading preserved",
              "HAND-WRITTEN BELOW" in vl,
              "the field's reading of the numbers is gone")


print("\n%d checks, %d failed" % (n_checks, len(failures)))
if failures:
    print("FAILED: " + "; ".join(failures))
sys.exit(1 if failures else 0)
