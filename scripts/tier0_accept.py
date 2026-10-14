#!/usr/bin/env python3
"""Tier 0 acceptance with default decisions, for onboarding (or any field
ingested through a corpus_map.csv).

Decisions, each printed with its reason (the user may change any of them:
edit both field-configs' lists and re-run with --keep-config):
  * ERROR (conversion failed)            -> excluded
  * SCAN (image-only, < 60 words/page)   -> excluded (OCR it and re-ingest to keep it)
  * INTERLEAVED (two columns read across) -> re-extracted with PyMuPDF; still
                                           interleaved -> excluded
  * a report / book / misc entry (the map's role, from the .bib type)
                                         -> terminology_only
  * SHORT (< 1,500 words): a report or a key with no .bib type -> terminology_only;
    a research article -> excluded (abstract-only or a landing page)
  * not English by its first pages (the onboarding index) -> excluded
Then: both field-configs written (and read back), the manifest rebuilt, the
lit registry's corpus denominators filled, Tier 0 added to both registries,
and the lit check_drift run.

RUN
    py -3 scripts/tier0_accept.py <field> [--dest <skills dir>] [--keep-config] [--no-reextract]
"""
import argparse
import csv
import json
import os
import sys

import _factory as F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field")
    ap.add_argument("--dest")
    ap.add_argument("--keep-config", action="store_true",
                    help="use the lists already in field-config (after a hand edit)")
    ap.add_argument("--no-reextract", action="store_true")
    a = ap.parse_args()
    fld = F.Field(a.field, a.dest).require()
    ref = os.path.join(fld.lit, "references")
    src_path = os.path.join(ref, "corpus_sources.json")
    if not os.path.isfile(src_path):
        F.die("no corpus_sources.json -- ingest first (onboard.py or ingest.py)")
    cmap = os.path.join(ref, "corpus_map.csv")
    rows = {}
    if os.path.isfile(cmap):
        with open(cmap, encoding="utf-8-sig", newline="") as fh:
            rows = {r["key"]: r for r in csv.DictReader(fh)}

    def sources():
        with open(src_path, encoding="utf-8") as fh:
            return json.load(fh)

    src = sources()
    inter = sorted(k for k, r in src.items() if "INTERLEAVED" in r.get("flags", []))
    if inter and not a.no_reextract and not a.keep_config:
        if os.path.isfile(cmap):
            print("re-extracting %d interleaved paper(s) with PyMuPDF: %s" % (len(inter), ", ".join(inter)))
            args = [sys.executable, "-B", os.path.join(F.HERE, "ingest.py"), fld.lit, "--map", cmap,
                    "--converter", "pymupdf"]
            for k in inter:
                args += ["--force", k]
            F.run(args, show=False)
            src = sources()
        else:
            print("interleaved papers found but no corpus_map.csv to re-extract from: %s" % ", ".join(inter))

    lang = {}
    for idx_path in index_paths(fld):
        with open(idx_path, encoding="utf-8") as fh:
            for k, r in json.load(fh).get("keys", {}).items():
                lang[r.get("corpus_key", k)] = r.get("lang", "")

    if a.keep_config:
        cfg = fld.config()
        cp = fld.cfgparse()
        term = [(k, "kept from field-config") for k in cp.as_list(cfg.get("terminology_only"))]
        excl = [(k, "kept from field-config") for k in cp.as_list(cfg.get("excluded"))]
    else:
        term, excl = [], []
        for k in sorted(src):
            r = src[k]
            flags = r.get("flags", [])
            role = (r.get("role") or rows.get(k, {}).get("role") or "").strip()
            if "ERROR" in flags:
                excl.append((k, "conversion failed"))
            elif "SCAN" in flags:
                excl.append((k, "image-only scan (%s words/page); OCR it and re-ingest to keep it"
                             % r.get("words_per_page")))
            elif "INTERLEAVED" in flags:
                excl.append((k, "columns still interleaved after PyMuPDF re-extraction"))
            elif lang.get(k) == "non-en":
                excl.append((k, "not English by its first pages"))
            elif role == "abstract_only":
                excl.append((k, "abstract only (corpus map role)"))
            elif role in ("report", "reference"):
                term.append((k, "report / book / misc entry (%s)"
                             % (rows.get(k, {}).get("note", "") or "role " + role)))
            elif "SHORT" in flags and role == "research":
                excl.append((k, "research entry but only %s words: abstract-only or landing page"
                             % r.get("words")))
            elif "SHORT" in flags:
                term.append((k, "%s words, no .bib type: short document, kept for terms only"
                             % r.get("words")))
        hdr = "tier0_accept.py %s defaults; edit both configs and re-run with --keep-config to change" % F.TODAY
        fld.set_list("terminology_only", term, hdr)
        fld.set_list("excluded", excl, hdr)

    print("\nTier 0 decisions (%d terminology_only, %d excluded):" % (len(term), len(excl)))
    for k, why in excl:
        print("  excluded          %-28s %s" % (k, why))
    for k, why in term:
        print("  terminology_only  %-28s %s" % (k, why))
    rep = sorted(k for k, r in src.items() if "REPLACEMENT" in r.get("flags", []))
    if rep:
        print("  (encoding damage, judged by the manifest's extraction check: %s)" % ", ".join(rep))

    print("\nmanifest:")
    fld.run("lit", "build_corpus_meta.py")
    den = fld.denominators()
    if None in den.values() or not den["style_safe"]:
        F.die("the manifest has no style-safe paper (%s) -- nothing to measure style on" % den)

    def fill(reg):
        reg["corpus"].update(den)
        reg["corpus"]["_why_values"] = (
            "Tier 0 accepted %s by tier0_accept.py: %d files, %d distinct, %d terminology-safe "
            "(%d excluded), %d style-safe (%d terminology-only)" % (
                F.TODAY, den["files"], den["distinct"], den["terminology_safe"], len(excl),
                den["style_safe"], len(term)))
    fld.update_registry("lit", fill)
    fld.add_tier(0)
    print("\nregistry: corpus %s; built_tiers %s" % (den, fld.built_tiers()))
    r = fld.run("lit", "check_drift.py", check=False, show=False)
    bad = [l for l in r.stdout.splitlines() if "FAIL" in l]
    print("check_drift: %s" % ("PASS" if r.returncode == 0 else "FAIL"))
    for l in bad:
        print("  " + l.strip())
    if r.returncode != 0:
        sys.exit(1)
    print("\nNEXT: py -3 %s %s" % (os.path.join(F.HERE, "calibrate_paragraphs.py"), a.field))


def index_paths(fld):
    """library-index.json next to the manuscript (manuscript_tex)."""
    cp = fld.cfgparse()
    mt = cp.as_str(fld.config().get("manuscript_tex"))
    if not mt:
        return []
    p = os.path.join(os.path.dirname(mt), ".polish", "library-index.json")
    return [p] if os.path.isfile(p) else []


if __name__ == "__main__":
    main()
