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
          "check_canon_quotes.py",
          # 1.6.0: the fast lane (evidence cards, one-call paragraph check)
          "_src.py", "_tiers.py", "_ngram.py", "cards.py", "para_check.py",
          "short_paras.py"):
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


def parent_markers(paths):
    """(stale tiers, unbalanced files). The template wraps the parent's
    chapters, denominators, paragraph statistics and verb ladder in
    PARENT-BLOCK tier=N markers, and its kept worked examples in
    PARENT-EXAMPLE. A PARENT-BLOCK still present at a built tier means the
    instance is quoting the parent's numbers as its own."""
    stale, bad = set(), []
    for path in paths:
        text = read(path)
        stale |= {int(n) for n in re.findall(r"<!-- PARENT-BLOCK tier=(\d) -->", text)} & TIERS
        depth = 0
        for m in re.finditer(r"<!-- (/?)PARENT-(?:BLOCK(?: tier=\d)?|EXAMPLE) -->", text):
            depth += -1 if m.group(1) else 1
            if depth not in (0, 1):
                break
        if depth != 0:
            bad.append(os.path.basename(path))
    return sorted(stale), bad


_pm = [p for p in [sk_path] + sorted(os.path.join(REF, f) for f in os.listdir(REF)
                                      if f.endswith(".md") and not f.endswith(".parent.md"))
       if os.path.exists(p)]
stale, unbalanced = parent_markers(_pm)
check("no PARENT-BLOCK left for a built tier", not stale,
      "tiers %s still carry parent text" % stale if stale else "")
check("PARENT-BLOCK / PARENT-EXAMPLE markers paired", not unbalanced, ", ".join(unbalanced))

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
    chs = REG["sections"].get("chapters") or {}
    check("registry sections.chapters recorded", bool(chs),
          "%d chapters" % len(chs) if chs else "no chapter recorded: Tier 3 has nothing to check")
    total_v = 0
    total_f = 0
    bad_fields, thin = [], []
    # An attesting paper is "— <key>" followed by ¶, S<n>, T<n> or "(", with an
    # optional "§6" between. Keys may start with a digit (07_GengQP2022) and
    # contain '-' (AGENCY-2019); T<n> numbers set-off statements, S<n> abstract
    # sentences.
    key_re = re.compile(r"—\s+([A-Za-z0-9][A-Za-z0-9_\-]+)"
                        r"(?:\s+§[^¶]*)?\s*(?:¶|S\d|T\d|\()")
    FIELDS = REG["sections"]["fields"]
    for ch, meta in REG["sections"]["chapters"].items():
        d = os.path.join(SEC, ch)
        # A chapter may be deliberately not drafted: a job whose paragraphs are
        # not prose (chains of displayed equations, say) has records and slices
        # but no paragraph shape to induce. That is a DECLARATION in the registry
        # (sections_built: false), never a tolerated failure: such a chapter is
        # asserted ABSENT, and a directory appearing there later fails.
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
        # The PASS2 size rule keeps a chapter under 25 KB as a single
        # <chapter>.md, so only a SPLIT chapter must carry a skeleton.
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
    # The Example quotes themselves, not just their count: a paraphrased or
    # invented example passes every check above.
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
    # the structure norms the canon and the router typing appendices quote
    sn_path = os.path.join(REF, "structure-norms.json")
    layers = (REG.get("structure_norms") or {}).get("layers") or []
    try:
        with open(sn_path, encoding="utf-8") as fh:
            norms = json.load(fh)
    except (OSError, ValueError):
        norms = {}
    check("structure-norms.json carries every layer (measure_structure.py)",
          bool(layers) and all(l in norms for l in layers),
          "missing: %s" % [l for l in layers if l not in norms] if norms
          else "no references/structure-norms.json -- py -3 scripts/measure_structure.py")

# ---- Tier 4: writing canon --------------------------------------------------
# SKILL.md cites structure-canon.md as the authority behind several drafting
# gates (Q3, Q5/Q6, Q7, D5, D7). The canon SOURCES (the writing guides) are
# wherever field-config's canon_dir points -- canon_ingest.py puts a field's
# own guides in references/canon-sources; the canon FILE is per instance,
# because every rule's corpus status must be re-measured. Both are asserted.
if 4 in TIERS:
    print("")
    print("tier 4 (writing canon)")
    sc = os.path.join(REF, "structure-canon.md")
    check("structure-canon.md exists", os.path.exists(sc))
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
        # A quotation whose pointer has rotted is worse than no quotation (the
        # parent's own canon once carried five, one aimed at a blank line).
        sq = cs.get("spot_quotes") or {}
        bad = [f for f, q in sq.items()
               if not (os.path.exists(os.path.join(canon, f))
                       and q in read(os.path.join(canon, f)))]
        need = min(3, n_txt)
        check("canon spot-quotes greppable verbatim", not bad and len(sq) >= need,
              "missing in: " + ", ".join(bad) if bad else "%d spot quotes (need %d)" % (len(sq), need))
    else:
        check("canon-sources reachable at canon_dir", False,
              "%s -- py -3 <corpus-bootstrap>/scripts/canon_ingest.py <field> --src <guides>" % canon)
    if os.path.exists(sc):
        t = read(sc)
        check("canon file cites canon-sources",
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
# The verb ladder must be this field's, generated by a script: a ladder
# inherited from the parent can be badly wrong elsewhere (the parent's
# headline phrase `consistent with` occurs zero times in a mathematics corpus).
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
