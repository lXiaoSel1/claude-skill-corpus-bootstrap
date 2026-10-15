#!/usr/bin/env python3
"""Tier 0: convert the field's PDFs into an instance's references/corpus/*.txt.

MANUAL-FIRST by design: YOU obtain the PDFs --
institutional access included; this script only converts and QC-checks. No
fetching, no APIs (see references/fetch-research.md).

Sources, one of:
  * <instance>/drop/*.pdf                       (default)
  * --src DIR [--src DIR ...] [--recursive]     library folders, read in place
                                                (instead of drop/)
  * --map CSV                                   explicit key -> file rows
        columns: key,path[,group][,role][,note]
        path may be a .pdf (converted) or a .txt (copied verbatim, e.g. a
        publisher-XML body for an entry with no PDF); a relative path is
        read from the CSV's own folder; group/role are free tags carried
        into the manifest (e.g. group=econ|health|report,
        role=research|working|report|abstract_only|scan)
    With --map, ONLY the mapped files are ingested and the map's keys are the
    corpus keys (so they match your bibliography); --src cannot be added.
    Without it, keys come from file stems.

Conversion: the pinned `pdftotext` from field-config.yaml, else the first
pdftotext on PATH, else PyMuPDF. pdftotext runs in -q DEFAULT mode (the
parents' validated path -- -layout broke formatting on validation). The
converter's path and version are recorded per file, because on Windows
PowerShell and Git Bash resolve different pdftotext builds.

QC per file -> references/corpus_sources.json (the provenance manifest that
build_corpus_meta.py reads):
  words, pages, words_per_page, replacement-char density, sha256 of source and
  of the written txt, flags:
    SCAN        >= 2 pages at < 60 words/page (image-only / OCR-less scan)
    SHORT       < 1500 words but readable pages (abstract-only, brief, slides)
    REPLACEMENT > 0.5% U+FFFD characters (encoding damage)
    ERROR       conversion failed (the batch continues)
Hand-repaired txt files are protected: if a corpus txt no longer matches the
sha256 this script wrote, it is never overwritten unless named explicitly
with --force KEY.

RUN
    py -3 scripts/ingest.py <lit-instance> [--src DIR ...] [--recursive]
        [--map keys.csv] [--force KEY ...] [--force-all] [--dry-run]
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _factory as F  # noqa: E402  (UTF-8 output, launcher name, key rule)

SCAN_WPP = 60       # words per page below this: image-only / scan
SHORT_WORDS = 1500   # readable but short: abstract-only, slides, brief
BAD_SHARE = 0.005    # replacement-character share flagged as damage
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def keyify(path):
    """File stem -> corpus key (letters, digits, _ and -). Non-ASCII stems get
    a stable hash suffix instead of collapsing to 'unnamed'."""
    stem = os.path.splitext(os.path.basename(path))[0]
    key = F.safe_key(stem.replace(" ", "_"), "")
    if not key or len(key) < 3:
        key = (key + "_" if key else "doc_") + hashlib.sha1(
            stem.encode("utf-8")).hexdigest()[:8]
    return key


def load_config(inst):
    sys.path.insert(0, os.path.join(inst, "scripts"))
    try:
        import _fieldconfig
        return _fieldconfig
    except Exception as e:  # an unparseable config must not be silent
        sys.exit("cannot read %s/references/field-config.yaml: %s" % (inst, e))


def converter(cfg, choice="auto"):
    """auto: pinned pdftotext, else PATH pdftotext, else PyMuPDF.
    pymupdf: force PyMuPDF -- the remedy for an INTERLEAVED flag, since it
    follows the PDF's own text-block order instead of reading rows across
    both columns."""
    if choice == "pymupdf":
        try:
            import fitz  # PyMuPDF
        except ImportError:
            sys.exit("--converter pymupdf: PyMuPDF not installed (%s -m pip install pymupdf)" % F.PY)
        return ("pymupdf", fitz.__file__, getattr(fitz, "VersionBind", "?"))
    pinned = cfg.pdftotext_path()
    exe = pinned or shutil.which("pdftotext")
    if pinned and not os.path.exists(pinned):
        sys.exit("pinned pdftotext not found: " + pinned)
    if choice == "pdftotext" and not exe:
        sys.exit("--converter pdftotext: no pdftotext pinned or on PATH")
    if exe:
        r = subprocess.run([exe, "-v"], capture_output=True, text=True)
        ver = (r.stderr or r.stdout).strip().splitlines()
        return ("pdftotext", exe, ver[0] if ver else "?")
    try:
        import fitz  # PyMuPDF
        return ("pymupdf", fitz.__file__, getattr(fitz, "VersionBind", "?"))
    except ImportError:
        sys.exit("neither pdftotext nor PyMuPDF available"
                 "\n  fix: pin pdftotext in field-config.yaml or"
                 " %s -m pip install pymupdf" % F.PY)


def page_count(pdf, text=None):
    """Pages of a PDF: PyMuPDF, else pypdf, else the form feeds pdftotext
    writes after every page (text = its output), else 0."""
    try:
        import fitz
        with fitz.open(pdf) as doc:
            return doc.page_count
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf).pages)
    except Exception:
        pass
    return text.count("\f") if text else 0


def qc(text, pages):
    """(words, words_per_page, flags) for one corpus text."""
    import textseg
    words = len(text.split())
    wpp = round(words / pages, 1) if pages else None
    flags = []
    if pages >= 2 and wpp < SCAN_WPP:
        # one page of little text is a short document, not a scan
        flags.append("SCAN")
    elif words < SHORT_WORDS:
        flags.append("SHORT")
    if text and text.count("�") / max(len(text), 1) > BAD_SHARE:
        flags.append("REPLACEMENT")
    ratio, nl = textseg.interleave_ratio(text)
    if nl >= textseg.INTERLEAVE_MIN_LINES and ratio >= textseg.INTERLEAVE_MIN:
        flags.append("INTERLEAVED")
    return words, wpp, flags


def convert(conv, pdf, txt):
    kind, exe, _ = conv
    if kind == "pdftotext":
        r = subprocess.run([exe, "-q", "-enc", "UTF-8", pdf, txt],
                           capture_output=True)
        if r.returncode != 0 or not os.path.exists(txt):
            raise RuntimeError("pdftotext exit %s" % r.returncode)
        return
    import fitz
    # Ligatures EXPANDED (no TEXT_PRESERVE_LIGATURES): a preserved U+FB01
    # is counted by build_corpus_meta, but attest/measure queries type "fi".
    flags = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_MEDIABOX_CLIP
    with fitz.open(pdf) as doc:
        text = "\n".join(page.get_text("text", flags=flags) for page in doc)
    with open(txt, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def collect(inst, args):
    """-> list of dicts {key, path, group, role, note}"""
    items = []
    if args.map:
        if args.src:
            sys.exit("give --map or --src, not both (--map ingests only its rows)")
        cmap = F.user_path(args.map)
        base = os.path.dirname(cmap)
        with open(cmap, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                key = (row.get("key") or "").strip()
                path = (row.get("path") or "").strip()
                if not key or not path:
                    continue
                path = os.path.expanduser(path)
                items.append({"key": key, "path": os.path.normpath(os.path.join(base, path)),
                              "group": (row.get("group") or "").strip(),
                              "role": (row.get("role") or "").strip(),
                              "note": (row.get("note") or "").strip()})
        return items
    roots = args.src or [os.path.join(inst, "drop")]
    for root in roots:
        # walked, not globbed: a folder named "Papers [2024]" is not a pattern,
        # and ".PDF" counts on case-sensitive file systems too
        root = F.user_path(root)
        if args.recursive:
            found = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs]
        else:
            found = [os.path.join(root, f) for f in os.listdir(root)] if os.path.isdir(root) else []
        for p in sorted(p for p in found if p.lower().endswith(".pdf") and os.path.isfile(p)):
            items.append({"key": keyify(p), "path": os.path.abspath(p),
                          "group": "", "role": "", "note": ""})
    return items


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("instance")
    ap.add_argument("--src", action="append")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--map")
    ap.add_argument("--force", action="append", default=[],
                    help="re-convert this key even if hand-repaired")
    ap.add_argument("--force-all", action="store_true",
                    help="re-convert every key NOT hand-repaired")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--converter", choices=["auto", "pdftotext", "pymupdf"],
                    default="auto",
                    help="pymupdf re-extracts an INTERLEAVED two-column paper"
                         " (use with --force KEY)")
    args = ap.parse_args()

    inst = F.user_path(args.instance)
    corpus = os.path.join(inst, "references", "corpus")
    manifest_path = os.path.join(inst, "references", "corpus_sources.json")
    if not os.path.isdir(os.path.join(inst, "scripts")):
        sys.exit("not a stamped -lit instance: " + inst)
    cfg = load_config(inst)
    conv = converter(cfg, args.converter)
    import textseg  # instance copy (load_config put scripts/ on sys.path)
    os.makedirs(corpus, exist_ok=True)

    items = collect(inst, args)
    if not items:
        sys.exit("no sources found (drop/ empty, --src matched nothing, or"
                 " --map had no rows)")
    seen, bad_keys = {}, []
    for it in items:
        if not KEY_RE.match(it["key"]):
            bad_keys.append(it["key"])
        # ignoring case: Smith2020.txt and smith2020.txt are one file on
        # Windows and macOS
        if it["key"].lower() in seen:
            sys.exit("key collision: %s <- %s AND %s\n  fix: rename one or"
                     " give explicit keys with --map"
                     % (it["key"], seen[it["key"].lower()], it["path"]))
        seen[it["key"].lower()] = it["path"]
        if not os.path.exists(it["path"]):
            sys.exit("missing source for %s: %s" % (it["key"], it["path"]))
    if bad_keys:
        sys.exit("keys must be letters/digits/_/- : %s" % bad_keys)

    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)

    def save():
        with open(manifest_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)

    print("converter: %s  %s  (%s)" % conv)
    print("%d sources%s" % (len(items), "  [dry run]" if args.dry_run else ""))
    flagged = []
    for it in items:
        key, src = it["key"], it["path"]
        txt = os.path.join(corpus, key + ".txt")
        prev = manifest.get(key, {})
        exists = os.path.exists(txt)
        hand = exists and prev.get("txt_sha256") and \
            sha256(txt) != prev["txt_sha256"]
        explicit = key in args.force
        if exists and not explicit and (hand or not args.force_all):
            note = "kept (hand-repaired)" if hand else "kept"
            if not prev:
                # a txt with no record (a run stopped part-way, or written by
                # hand): adopt it, but with the same QC a conversion gets
                with open(txt, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                pages = 0 if src.lower().endswith(".txt") else page_count(src, text)
                words, wpp, flags = qc(text, pages)
                prev = {"source": src, "source_sha256": sha256(src),
                        "converter": "unknown (adopted)", "pages": pages, "words": words,
                        "words_per_page": wpp, "flags": flags, "txt_sha256": sha256(txt)}
                note = "adopted %s" % " ".join(flags) if flags else "adopted"
                if flags:
                    flagged.append(key)
            prev.update({k: it[k] for k in ("group", "role", "note") if it[k]})
            manifest[key] = prev
            print("%-28s %s" % (key, note))
            if not args.dry_run:
                save()
            continue
        if args.dry_run:
            print("%-28s would convert  %s" % (key, src))
            continue
        rec = {"source": src, "source_sha256": sha256(src),
               "group": it["group"], "role": it["role"], "note": it["note"],
               "ingested_at": datetime.datetime.now().isoformat(
                   timespec="seconds")}
        try:
            if src.lower().endswith(".txt"):
                shutil.copyfile(src, txt)
                rec.update(converter="copied-text", converter_path=src,
                           converter_version="-", pages=0)
            else:
                convert(conv, src, txt)
                rec.update(converter=conv[0], converter_path=conv[1],
                           converter_version=conv[2])
            with open(txt, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if "pages" not in rec:
                rec["pages"] = page_count(src, text)
            words, wpp, flags = qc(text, rec["pages"])
            rec.update(words=words, words_per_page=wpp, flags=flags,
                       txt_sha256=sha256(txt))
        except Exception as e:  # one bad file never stops the batch
            rec.update(flags=["ERROR"], error=str(e)[:200])
        manifest[key] = rec
        save()   # after every file: a run stopped part-way keeps its records
        if rec.get("flags"):
            flagged.append(key)
        print("%-28s %-12s %8s words %6s w/p  %s"
              % (key, rec.get("converter", "-"),
                 format(rec.get("words", 0), ","),
                 rec.get("words_per_page") or "-",
                 " ".join(rec.get("flags", []))))

    if args.dry_run:
        return
    save()
    print("\nmanifest: %s (%d keys)" % (manifest_path, len(manifest)))
    if flagged:
        print("flagged (review at Tier 0 acceptance; SCAN needs OCR or goes to"
              " `excluded`, SHORT usually to `terminology_only`/`excluded`,"
              " INTERLEAVED -> re-run with --force KEY --converter pymupdf):")
        for k in flagged:
            print("  %-28s %s" % (k, " ".join(manifest[k].get("flags", []))))
    field = os.path.basename(inst.rstrip("/\\"))
    field = field[:-4] if field.endswith("-lit") else field
    print("\nnext: %s %s" % (F.PY, os.path.join(inst, "scripts", "build_corpus_meta.py")))
    print("then review the manifest's four denominators -- Tier 0 acceptance:")
    print("  %s %s %s%s" % (F.PY, os.path.join(F.HERE, "tier0_accept.py"), field,
                            F.dest_arg(os.path.dirname(inst.rstrip("/\\")))))


if __name__ == "__main__":
    main()
