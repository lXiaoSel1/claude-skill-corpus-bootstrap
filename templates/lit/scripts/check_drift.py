#!/usr/bin/env python3
"""Tier-aware consistency check for a stamped <field>-lit instance.

Same doctrine as the parent skills' check_drift: declared invariants live in
references/registry.json (with _why), this script re-derives them from disk,
PASS/FAIL per line, exit 0 only if clean.  TIER-AWARE: sections gate on
registry.built_tiers, so an instance at Tier 1 is judged as a Tier-1 instance,
not failed for lacking Tier-4 artifacts.

Rules learned from a version that reported 36/36 PASS while three corpus
defects were live:
  * a registry value still null at a BUILT tier is a FAIL (it used to skip
    the check silently, which is a pass that measured nothing);
  * Tier 0 asserts no SCAN/ERROR-flagged or near-empty text is style-safe,
    every terminology_only/excluded key exists on disk, the config parses
    without warnings, and the lit/draft copies of _cfgparse.py and of
    field-config.yaml agree;
  * Tier 1 asserts the ONE paragraph threshold agrees between config and the
    norms JSON (the parent's check that would have caught the mathematics instance's 150/400
    split), the transitions header quotes the exact join count (was a
    substring test), and no `corpus: TO-MEASURE` is left in cohesion-canon.md;
  * every FAIL prints the command that fixes it.

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
sys.path.insert(0, HERE)
import _cfgparse as cp  # noqa: E402
import _fieldconfig  # noqa: E402

with open(os.path.join(REF, "registry.json"), encoding="utf-8") as fh:
    REG = json.load(fh)
TIERS = set(int(t) for t in REG.get("built_tiers", []))

failures = []
n_checks = 0


def check(name, ok, detail="", fix=""):
    global n_checks
    n_checks += 1
    print("  %s %-60s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        failures.append(name)
        if fix:
            print("       fix: " + fix)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def reg_value(section, key, tier):
    """A registry number required at `tier`: FAIL (not skip) while null."""
    v = REG.get(section, {}).get(key)
    if v is None:
        check("registry %s.%s filled (tier %d built)" % (section, key, tier),
              False, "still null",
              "fill it from the tier-%d builder's printed output" % tier)
    return v


print("%s-lit drift check (built tiers: %s)\n"
      % (REG.get("field", "?"), sorted(TIERS) or "none"))

# ---- always-on: the stamped skeleton itself --------------------------------
print("skeleton")
for f in ("register.md", "cohesion-canon.md", "terms.md", "candidates.md",
          "field-config.yaml"):
    check("references/%s exists" % f,
          os.path.exists(os.path.join(REF, f)))
for s in ("attest.py", "cache.py", "textseg.py", "cohesion.py",
          "build_corpus_meta.py", "build_cohesion_norms.py",
          "build_transitions.py", "measure_register.py", "_fieldconfig.py",
          "_cfgparse.py", "build_exemplars.py", "backfill_cite_keys.py"):
    check("scripts/%s exists" % s, os.path.exists(os.path.join(HERE, s)))
# token built by concatenation so stamp.py's substitution cannot eat the
# check itself (it did, once -- the check searched for the stamped field name
# and failed on its own preambles).
_TOKEN = "{{" + "FIELD" + "}}"
check("no unstamped field tokens outside registry",
      all(_TOKEN not in read(os.path.join(REF, f))
          for f in ("register.md", "terms.md", "candidates.md",
                    "cohesion-canon.md", "field-config.yaml")
          if os.path.exists(os.path.join(REF, f))))
# Parent text: a PARENT-BLOCK tier=N must be rewritten from this field's own
# measurements once tier N is built; PARENT-EXAMPLE blocks are kept worked
# examples. Markers must pair. (*.parent.md are tier1_fill's unfilled copies.)
_pm = [os.path.join(SKILL, "SKILL.md")] + sorted(
    os.path.join(REF, f) for f in os.listdir(REF) if f.endswith(".md") and not f.endswith(".parent.md"))
_stale, _unpaired = set(), []
for _p in [p for p in _pm if os.path.exists(p)]:
    _t = read(_p)
    _stale |= {int(n) for n in re.findall(r"<!-- PARENT-BLOCK tier=(\d) -->", _t)} & TIERS
    _d = 0
    for _m in re.finditer(r"<!-- (/?)PARENT-(?:BLOCK(?: tier=\d)?|EXAMPLE) -->", _t):
        _d += -1 if _m.group(1) else 1
        if _d not in (0, 1):
            break
    if _d != 0:
        _unpaired.append(os.path.basename(_p))
check("no PARENT-BLOCK left for a built tier", not _stale,
      "tiers %s still carry parent text" % sorted(_stale) if _stale else "",
      "rewrite those blocks from this field's measurements and delete their markers")
check("PARENT-BLOCK / PARENT-EXAMPLE markers paired", not _unpaired, ", ".join(_unpaired))
cfg_path = os.path.join(REF, "field-config.yaml")
del cp.WARNINGS[:]
cfg = cp.parse(cfg_path)
check("field-config.yaml parses without warnings", not cp.WARNINGS,
      "; ".join(cp.WARNINGS)[:120],
      "fix the listed lines (see _cfgparse.py docstring for the syntax)")
draft = cp.as_str(cfg.get("draft_instance"))
draft_dir = os.path.normpath(os.path.join(SKILL, "..", draft)) if draft else ""
if draft_dir and os.path.isdir(draft_dir):
    other = os.path.join(draft_dir, "pipeline", "_cfgparse.py")
    check("_cfgparse.py identical in lit and draft instances",
          os.path.exists(other) and read(other) == read(
              os.path.join(HERE, "_cfgparse.py")),
          fix="copy one over the other (they must not diverge)")
    dcfg = cp.parse(os.path.join(draft_dir, "references", "field-config.yaml"))
    diff = sorted(k for k in set(cfg) | set(dcfg) if cfg.get(k) != dcfg.get(k))
    check("field-config.yaml agrees between lit and draft", not diff,
          ", ".join(diff)[:80],
          "edits at tier gates go to BOTH copies")

# ---- Tier 0: corpus + manifest --------------------------------------------
if 0 in TIERS:
    print("\ntier 0 (corpus)")
    corpus = os.path.join(REF, "corpus")
    on_disk = {f[:-4] for f in os.listdir(corpus) if f.endswith(".txt")} \
        if os.path.isdir(corpus) else set()
    check("corpus/ non-empty", bool(on_disk), "%d txt" % len(on_disk))
    meta = os.path.join(REF, "corpus_meta.yaml")
    check("corpus_meta.yaml exists", os.path.exists(meta),
          fix="py -3 scripts/build_corpus_meta.py")
    if os.path.exists(meta):
        m = read(meta)
        for den in ("files", "distinct", "terminology_safe", "style_safe"):
            reg_v = reg_value("corpus", den, 0)
            got = re.search(r"^\s+%s:\s*(\d+)" % den, m, re.M)
            if reg_v is not None:
                check("denominator %s: registry == manifest" % den,
                      got is not None and int(got.group(1)) == reg_v,
                      "reg=%s manifest=%s" % (reg_v,
                                              got.group(1) if got else "?"),
                      "rerun build_corpus_meta.py, then copy its numbers")
        check("registry files == disk txt count",
              REG["corpus"].get("files") == len(on_disk),
              "reg=%s disk=%d" % (REG["corpus"].get("files"), len(on_disk)))
        # papers block -> per-paper style_safe + extraction verdicts
        papers = {}
        for blk in re.split(r"(?m)^  - id:\s*", m)[1:]:
            pid = blk.split("\n", 1)[0].strip()
            papers[pid] = blk
        bad_style = sorted(
            p for p, b in papers.items()
            if re.search(r"style_safe:\s*true", b)
            and (re.search(r"extraction:\s*(scan_or_empty|conversion_failed)", b)
                 or re.search(r"ingest_flags:\s*\[[^\]]*(SCAN|ERROR)", b)))
        check("no scan/empty/failed extraction is style-safe", not bad_style,
              ", ".join(bad_style)[:80],
              "rerun build_corpus_meta.py (scans are classified since 2026-10-07)")
    listed = _fieldconfig.terminology_only() | _fieldconfig.excluded()
    missing = sorted(listed - on_disk)
    check("terminology_only/excluded keys exist in corpus/", not missing,
          ", ".join(missing)[:80],
          "a typo or a comment kept inside a key -- correct field-config.yaml")

# ---- Tier 1: style layer ---------------------------------------------------
if 1 in TIERS:
    print("\ntier 1 (style layer)")
    for f in ("register-measurements.md", "cohesion-norms.json",
              "cohesion-measurements.md", "transitions.md"):
        check("references/%s exists" % f,
              os.path.exists(os.path.join(REF, f)))
    try:
        with open(os.path.join(REF, "cohesion-norms.json"),
                  encoding="utf-8") as fh:
            norms = json.load(fh)
        ok = True
    except Exception:
        norms, ok = {}, False
    check("cohesion-norms.json valid JSON", ok,
          fix="py -3 scripts/build_cohesion_norms.py")
    th = norms.get("thresholds", {}).get("para_min_chars")
    check("para_min_chars: field-config == norms JSON",
          th == _fieldconfig.para_min_chars(),
          "config=%s norms=%s" % (_fieldconfig.para_min_chars(), th),
          "rerun build_cohesion_norms.py after changing para_min_chars")
    pairs_reg = reg_value("cohesion", "adjacent_pairs", 1)
    paras_reg = reg_value("cohesion", "total_paragraphs", 1)
    if ok and pairs_reg is not None:
        pairs = norms.get("adjudications", {}).get("pairs_total")
        check("adjacent_pairs: registry == norms", pairs == pairs_reg,
              "reg=%s norms=%s" % (pairs_reg, pairs))
    if ok and paras_reg is not None:
        paras = norms.get("coverage", {}).get("total_paragraphs")
        check("total_paragraphs: registry == norms", paras == paras_reg,
              "reg=%s norms=%s" % (paras_reg, paras))
    t = read(os.path.join(REF, "transitions.md")) \
        if os.path.exists(os.path.join(REF, "transitions.md")) else ""
    joins = reg_value("transitions", "joins", 1)
    if joins is not None:
        got = re.search(r"(\d+) joins drawn from (\d+) papers", t)
        check("transitions header join count == registry",
              bool(got) and int(got.group(1)) == joins,
              "reg=%s header=%s" % (joins, got.group(1) if got else "?"),
              "py -3 scripts/build_transitions.py, then copy its numbers")
    left = len(re.findall(r"corpus:\s*TO-MEASURE",
                          read(os.path.join(REF, "cohesion-canon.md"))))
    check("cohesion-canon.md: no `corpus: TO-MEASURE` left", left == 0,
          "%d left" % left,
          "replace each with this corpus's verdict from cohesion-norms.json"
          " (or `corpus: UNMEASURED (judgment)` with a reason)")
    check("attest threshold agrees across scripts",
          read(os.path.join(HERE, "attest.py")).count(
              "ATTESTED_MIN_PAPERS = %d"
              % REG["thresholds"]["attested_min_papers"]) == 1
          and read(os.path.join(HERE, "measure_register.py")).count(
              "ATTESTED_MIN_PAPERS = %d"
              % REG["thresholds"]["attested_min_papers"]) == 1)

# ---- Tier 4: exemplars -----------------------------------------------------
if 4 in TIERS:
    print("\ntier 4 (exemplars)")
    ex = os.path.join(REF, "exemplars.md")
    check("exemplars.md exists", os.path.exists(ex),
          fix="py -3 scripts/build_exemplars.py")
    n_reg = reg_value("exemplars", "tagged_sentences", 4)
    if os.path.exists(ex) and n_reg is not None:
        t = read(ex)
        n_tagged = len(re.findall(r"(?m)^- \*\*\[", t))
        check("tagged sentences: registry == disk", n_tagged == n_reg,
              "reg=%s disk=%d" % (n_reg, n_tagged))
        check("no BOM/zero-width at section boundaries",
              "\ufeff" not in t and "\u200b" not in t)
        # The parent asserted the SECTION count too, and that assertion is
        # what caught its stray U+FEFF (159 sections read as 158).
        meta = set(REG["exemplars"].get("meta_headings", []))
        secs = [h for h in re.findall(r"(?m)^##\s+(\S+)", t) if h not in meta]
        n_secs = reg_value("exemplars", "sections", 4)
        if n_secs is not None:
            check("exemplar sections: registry == disk", len(secs) == n_secs,
                  "reg=%s disk=%d" % (n_secs, len(secs)))
        check("no duplicate paper section", len(secs) == len(set(secs)),
              "repeated: " + ", ".join(sorted(
                  {h for h in secs if secs.count(h) > 1}))[:60])
        vocab = set(REG["exemplars"].get("move_tags", []))
        check("registry declares the move-tag vocabulary", bool(vocab),
              fix="copy the 8 labels from prompts/exemplar-tagging.md into"
                  " registry.exemplars.move_tags")
        if vocab:
            used = set(re.findall(r"(?m)^- \*\*\[([a-z\-]+)\]", t))
            check("move tags all from the declared vocabulary",
                  used <= vocab, "unknown: " + ", ".join(sorted(used - vocab)))
            check("every declared move tag is used at least once",
                  vocab <= used, "unused: " + ", ".join(sorted(vocab - used)))

print("\n%d checks, %d failed" % (n_checks, len(failures)))
if failures:
    print("FAILED: " + "; ".join(failures))
sys.exit(1 if failures else 0)
