# -*- coding: utf-8 -*-
"""Reuse an older draft skill's reading for the papers both builds share.

    py -3 scripts/seed_from.py <field> --from <old draft skill> --tier 2
        [--old-corpus <dir>] [--job-map old=new,...] [--dest <skills dir>] [--dry-run]
    py -3 scripts/seed_from.py <field> --from <old draft skill> --tier 3 --chapter <job>
        [--old-corpus <dir>] [--old-records <file>] [--dest <skills dir>] [--dry-run]

Tier 2 (after the taxonomy is approved and written to field-config `jobs:`):
the old build's A2 verdicts (`a2_out_*.tsv`, read in the old build_map's
order: waves, then the correction files alphabetically; the last verdict for a
line wins) are imported for a sample paper only when its corpus text is
byte-identical (sha256) in the old and new corpus, and then only at the A1
candidate lines the old build gave a verdict. Candidates the new A1 adds
(PARTIAL) stay for the A2 waves; a paper with no imported line is REREAD.

Every old job label must be a new job, NONE or OTHER, or be mapped with
--job-map; one unmapped label abandons the whole import (a different taxonomy
means everything is re-read). Writes, in <draft>/pipeline/:

  a2_out_wave0_seed.tsv   the imported verdicts (build_map reads it first, so a
                          re-read in a later wave file overrides it)
  a2_seeded.json          {key: {sha256, lines, from}}; a2_build.py leaves those
                          lines out of the wave files
  seed_report.md          every sample paper: IMPORT, PARTIAL or REREAD, and why

The A3 gate still runs on the whole map, and its sample must include re-read
papers.

Tier 3 (one chapter at a time, after Tier 2): a paper's PASS1 record block is
imported only when its corpus text is byte-identical, its slice for the
chapter has the same text lines as the old build's slice, and every quoted
first sentence is found in the new slice (verify_shards.py's fingerprint).
The rest are listed for PASS1; PASS2 then induces the Versions from all of
them. See tier3() for the files it writes.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _factory as F  # noqa: E402

KEEP = {"NONE", "OTHER"}


def sha(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def old_pipeline(old):
    for p in (os.path.join(old, "pipeline"), os.path.join(old, "references", "pipeline")):
        if glob.glob(os.path.join(p, "a2_out_*.tsv")):
            return p
    F.die("no a2_out_*.tsv under %s/pipeline or %s/references/pipeline" % (old, old))


def old_corpus(old, given):
    if given:
        if not os.path.isdir(given):
            F.die("--old-corpus %s is not a folder" % given)
        return given
    cfg = os.path.join(old, "references", "field-config.yaml")
    if os.path.isfile(cfg):
        for line in open(cfg, encoding="utf-8"):
            if line.startswith("lit_instance:"):
                lit = line.split(":", 1)[1].split("#")[0].strip().strip("'\"")
                p = os.path.join(lit, "references", "corpus")
                if os.path.isdir(p):
                    return p
    F.die("cannot tell which corpus the old build read: pass --old-corpus <dir>")


def read_verdicts(pipe):
    """{(key, line): (jobs, conf, note, file)}, last file wins."""
    waves = sorted(glob.glob(os.path.join(pipe, "a2_out_wave*.tsv")))
    rest = sorted(p for p in glob.glob(os.path.join(pipe, "a2_out_*.tsv")) if p not in waves)
    out = {}
    for p in waves + rest:
        for ln in open(p, encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) < 3:
                continue
            try:
                key = (f[0].strip(), int(f[1].strip().lstrip("Ll")))
            except ValueError:
                continue
            jobs = [j.strip() for j in f[2].split(",") if j.strip()]
            out[key] = (jobs, f[3].strip() if len(f) > 3 else "", f[4].strip() if len(f) > 4 else "",
                        os.path.basename(p))
    return out


def tier2(a, fld):
    cp = fld.cfgparse()
    jobs = cp.as_list(fld.config().get("jobs"))
    if not jobs:
        F.die("no jobs: in the field-config -- the taxonomy must be approved and written first")
    pipe = os.path.join(fld.draft, "pipeline")
    cand_p = os.path.join(pipe, "a1_candidates.json")
    keys_p = os.path.join(pipe, "sample-keys.txt")
    for p in (cand_p, keys_p):
        if not os.path.isfile(p):
            F.die("missing %s -- run make_sample.py and a1_headings.py first" % p)
    cand = json.load(open(cand_p, encoding="utf-8"))
    sample = [k.strip() for k in open(keys_p, encoding="utf-8") if k.strip()]
    old = F.user_path(getattr(a, "from"))
    opipe = old_pipeline(old)
    ocorpus = old_corpus(old, a.old_corpus)
    ncorpus = os.path.join(fld.lit, "references", "corpus")
    verdicts = read_verdicts(opipe)

    jmap = {}
    for pair in (a.job_map or "").split(","):
        if "=" in pair:
            o, n = (x.strip() for x in pair.split("=", 1))
            if n not in jobs and n not in KEEP:
                F.die("--job-map %s=%s: %s is not a job of the approved taxonomy" % (o, n, n))
            jmap[o] = n
    labels = sorted({j for v in verdicts.values() for j in v[0]})
    unmapped = [l for l in labels if l not in jobs and l not in KEEP and l not in jmap]
    if unmapped:
        F.die("the old taxonomy has jobs the new one lacks: %s\n  map them with --job-map old=new, or"
              " import nothing and re-read every paper (the taxonomy differs)" % ", ".join(unmapped))

    by_paper = {}
    for (k, line), v in verdicts.items():
        by_paper.setdefault(k, {})[line] = v
    rows, seeded, report = [], {}, []
    for k in sample:
        if k not in by_paper:
            report.append((k, "REREAD", "not in the old build"))
            continue
        h_new, h_old = sha(os.path.join(ncorpus, k + ".txt")), sha(os.path.join(ocorpus, k + ".txt"))
        if not h_old or h_new != h_old:
            report.append((k, "REREAD", "corpus text differs from the old build's" if h_old else "no old corpus text"))
            continue
        # one verdict per line: a chapter+subsection double heading is two candidates on one line
        lines = sorted({c["line"] for c in cand.get(k, {}).get("candidates", [])})
        have = [l for l in lines if l in by_paper[k]]
        missing = [l for l in lines if l not in by_paper[k]]
        if not have:
            report.append((k, "REREAD", "none of %d A1 candidates has an old verdict" % len(lines)))
            continue
        for l in have:
            js, conf, note, src = by_paper[k][l]
            js = [jmap.get(j, j) for j in js]
            rows.append("%s\t%d\t%s\t%s\tseed %s: %s" % (k, l, ",".join(js), conf, src, note))
        seeded[k] = {"sha256": h_new, "lines": have, "from": opipe.replace("\\", "/")}
        if missing:
            report.append((k, "PARTIAL", "%d verdicts imported; %d of %d A1 candidates re-read (first: L%d)"
                           % (len(have), len(missing), len(lines), missing[0])))
        else:
            report.append((k, "IMPORT", "%d verdicts" % len(lines)))

    n = {w: sum(1 for _, x, _ in report if x == w) for w in ("IMPORT", "PARTIAL", "REREAD")}
    print("sample %d papers: IMPORT %d · PARTIAL %d · REREAD %d   (old verdicts: %d lines in %d papers;"
          " job map: %s)" % (len(sample), n["IMPORT"], n["PARTIAL"], n["REREAD"], len(verdicts), len(by_paper),
                             ", ".join("%s=%s" % kv for kv in sorted(jmap.items())) or "identity"))
    for k, what, why in report:
        if what != "IMPORT":
            print("  %-7s %-40s %s" % (what, k, why))
    if a.dry_run:
        print("(dry run: nothing written)")
        return 0
    with open(os.path.join(pipe, "a2_out_wave0_seed.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rows) + ("\n" if rows else ""))
    with open(os.path.join(pipe, "a2_seeded.json"), "w", encoding="utf-8") as fh:
        json.dump(seeded, fh, indent=1, sort_keys=True)
    with open(os.path.join(pipe, "seed_report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# seed_report.md -- Tier 2 verdicts imported from %s (%s)\n\n" % (opipe.replace("\\", "/"), F.TODAY))
        fh.write("IMPORT %d · PARTIAL %d · REREAD %d of %d sample papers\n\n| paper | | why |\n|---|---|---|\n"
                 % (n["IMPORT"], n["PARTIAL"], n["REREAD"], len(sample)))
        for k, what, why in report:
            fh.write("| `%s` | %s | %s |\n" % (k, what, why))
    print("wrote a2_out_wave0_seed.tsv (%d rows), a2_seeded.json, seed_report.md in %s" % (len(rows), pipe))
    return 0


def slice_lines(path):
    """A slice's text lines: CRs dropped, block headers ('=====') and blanks out."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        t = fh.read().replace("\r", "").split("\n")
    return [l.strip() for l in t if l.strip() and not l.startswith("=====")]


HEADING_MAX = 120


def added_headings(old, new):
    """[] when the slices have the same lines; the new lines when the old slice
    is the new one minus heading-like lines (an extra chapter-heading block such
    as '2. Prior literature and hypothesis development': short, not ending a
    sentence); None otherwise -- a sentence-ending line ('H2: ... .') may be a
    paragraph the old record never saw."""
    i, extra = 0, []
    for line in new:
        if i < len(old) and line == old[i]:
            i += 1
        elif len(line) <= HEADING_MAX and not re.search(r"[.?!;:,]\s*$", line):
            extra.append(line)
        else:
            return None
    return extra if i == len(old) else None


def fingerprint(s):
    """Lowercase alphanumerics only -- verify_shards.py's (and para_numbers.py's) fp."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def record_blocks(path):
    """{paper key: block text} of a PASS1 record file ('### <Key> ...' blocks)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    out = {}
    for part in re.split(r"(?m)^(?=### )", text):
        if not part.startswith("### "):
            continue
        key = part[4:].split()[0] if part[4:].split() else ""
        body = re.sub(r"(?s)\n-{3,}\s*$", "\n", part.rstrip() + "\n")
        if key:
            out[key] = body.rstrip() + "\n"
    return out


def tier3(a, fld):
    """Import an older build's PASS1 records for one chapter, paper by paper,
    when the paper's corpus text is byte-identical, its slice for this chapter
    has the same lines, and every quoted first sentence of the old record is in
    the new slice (verify_shards.py's fingerprint). Writes
    references/records/_shards/<chapter>-00.md (the imported blocks; PASS1
    shards for the re-read papers are -01, -02, ...), <chapter>-reread.txt (the
    papers PASS1 must read) and pipeline/seed_report_<chapter>.md."""
    cp = fld.cfgparse()
    jobs = cp.as_list(fld.config().get("jobs"))
    if not a.chapter or a.chapter not in jobs:
        F.die("--tier 3 needs --chapter <job> of the approved taxonomy (%s)" % ", ".join(jobs))
    old = F.user_path(getattr(a, "from"))
    ocorpus = old_corpus(old, a.old_corpus)
    ncorpus = os.path.join(fld.lit, "references", "corpus")
    rec = F.user_path(a.old_records) if a.old_records else os.path.join(old, "references", "records",
                                                                          a.chapter + ".md")
    if not os.path.isfile(rec):
        F.die("no old record file %s (pass --old-records)" % rec)
    nsl = os.path.join(fld.draft, "references", "slices", a.chapter)
    osl = os.path.join(old, "references", "slices", a.chapter)
    if not os.path.isdir(nsl):
        F.die("no slices for %s in %s -- Tier 2 first" % (a.chapter, nsl))
    blocks = record_blocks(rec)
    keys = sorted(f[:-4] for f in os.listdir(nsl) if f.endswith(".txt"))
    imported, report = [], []
    for k in keys:
        if k not in blocks:
            report.append((k, "REREAD", "no old record"))
            continue
        h_new, h_old = sha(os.path.join(ncorpus, k + ".txt")), sha(os.path.join(ocorpus, k + ".txt"))
        if not h_old or h_new != h_old:
            report.append((k, "REREAD", "corpus text differs from the old build's" if h_old else "no old corpus text"))
            continue
        op = os.path.join(osl, k + ".txt")
        if not os.path.isfile(op):
            report.append((k, "REREAD", "no old slice"))
            continue
        new_lines = slice_lines(os.path.join(nsl, k + ".txt"))
        old_lines = slice_lines(op)
        extra = added_headings(old_lines, new_lines)
        if extra is None:
            report.append((k, "REREAD", "the slice changed (old %d lines, new %d)" % (len(old_lines),
                                                                                    len(new_lines))))
            continue
        pool = fingerprint(" ".join(new_lines))
        qs = [q.strip().strip('"').rstrip(".…") for q in re.findall(r'(?m)^>\s*"?(.{20,})', blocks[k])]
        qs = [q for q in qs if not re.search(r"\[(?:displayed equation omitted|EXTRACTION UNCLEAR)", q)]
        miss = [q for q in qs if fingerprint(q)[:40] not in pool]
        if not qs or miss:
            report.append((k, "REREAD", "%d of %d quoted first sentences not in the new slice"
                           % (len(miss), len(qs)) if qs else "the old record quotes nothing"))
            continue
        imported.append(blocks[k])
        report.append((k, "IMPORT", "%d quotes found%s" % (len(qs), "; the new slice adds %d heading line(s): %s"
                                                          % (len(extra), " | ".join(e[:50] for e in extra))
                                                          if extra else "")))
    n_imp = len(imported)
    reread = [k for k, w, _ in report if w == "REREAD"]
    print("%s: %d papers with a slice: IMPORT %d · REREAD %d   (old record file: %d papers)"
          % (a.chapter, len(keys), n_imp, len(reread), len(blocks)))
    for k, w, why in report:
        if w == "REREAD" or "heading line" in why:
            print("  %-6s %-40s %s" % (w, k, why))
    if a.dry_run:
        print("(dry run: nothing written)")
        return 0
    shards = os.path.join(fld.draft, "references", "records", "_shards")
    os.makedirs(shards, exist_ok=True)
    with open(os.path.join(shards, a.chapter + "-00.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("<!-- imported by corpus-bootstrap seed_from.py --tier 3 on %s from %s: %d papers whose corpus "
                 "text, slice lines and every quoted first sentence match this build -->\n\n"
                 % (F.TODAY, rec.replace("\\", "/"), n_imp))
        fh.write("\n---\n\n".join(imported))
    with open(os.path.join(shards, a.chapter + "-reread.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(reread) + ("\n" if reread else ""))
    with open(os.path.join(fld.draft, "pipeline", "seed_report_%s.md" % a.chapter), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write("# seed_report_%s.md -- Tier 3 records imported from %s (%s)\n\nIMPORT %d · REREAD %d of %d\n\n"
                 "| paper | | why |\n|---|---|---|\n" % (a.chapter, rec.replace("\\", "/"), F.TODAY, n_imp,
                                                      len(reread), len(keys)))
        for k, w, why in report:
            fh.write("| `%s` | %s | %s |\n" % (k, w, why))
    print("wrote _shards/%s-00.md (%d papers), _shards/%s-reread.txt (%d), pipeline/seed_report_%s.md"
          % (a.chapter, n_imp, a.chapter, len(reread), a.chapter))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field")
    ap.add_argument("--from", required=True, help="the old draft skill's folder")
    ap.add_argument("--tier", type=int, choices=[2, 3], required=True)
    ap.add_argument("--old-corpus")
    ap.add_argument("--job-map", help="old=new,old=new for renamed jobs")
    ap.add_argument("--dest")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--chapter", help="--tier 3: the job whose records to import")
    ap.add_argument("--old-records", help="--tier 3: the old record file (default "
                                          "<old>/references/records/<chapter>.md)")
    a = ap.parse_args()
    fld = F.Field(F.norm_field(a.field), a.dest).require()
    if a.tier == 3:
        return tier3(a, fld)
    return tier2(a, fld)


if __name__ == "__main__":
    sys.exit(main())
