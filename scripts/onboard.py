#!/usr/bin/env python3
"""One-step onboarding: from a manuscript and the user's library to a field
whose corpus is ingested and whose <field>-polish knows where every cited
paper's PDF is. No configuration file to fill in.

What it does, in order:
  1. reads the manuscript (manuscript.py): sections, cited keys, its .bib;
  2. builds <manuscript dir>/.polish/library-index.json, matching every cited
     key to a PDF, first by the .bib `file` field (Zotero / JabRef / Mendeley
     exports), then a reading note's PDF field (--notes), then a PDF named
     after the key, then the DOI, the title, and first author + year found in
     the library folder; it reports keys with no PDF, keys with several
     candidates, duplicate versions, and PDFs that do not look English;
  3. reuses the field's instances when they exist (stamping only a missing
     <field>-polish), else stamps all three (needs --field and --keywords:
     the model asks the user for them first);
  4. writes manuscript_tex into both field-configs;
  5. writes <field>-lit/references/corpus_map.csv (corpus key = cite key,
     sanitised where needed, the crosswalk kept in the index) and runs
     ingest.py --map and build_corpus_meta.py -- unless Tier 0 is already
     built, in which case the corpus is left as it is.
Next: tier0_accept.py, calibrate_paragraphs.py, tier1_fill.py, then
onboard.py --finish.

RUN
    py -3 scripts/onboard.py --manuscript <main.tex> --library <folder or .bib> [--library ...]
        [--notes <folder>] [--notes-pdf-field 对应PDF] [--field <slug> --keywords "..."]
        [--citation-style author-year|numeric|mixed] [--dest <skills dir>]
        [--include-uncited] [--dry-run]
    py -3 scripts/onboard.py --finish --field <slug> [--manuscript <main.tex>] [--dest <skills dir>]
--dry-run builds and reports the index only: no stamping, no config, no ingest.
Exit code 3 when the field must be named first; 2 on an error.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata

import _factory as F

sys.path.insert(0, os.path.join(F.TEMPLATES, "polish", "scripts"))
import manuscript as M  # noqa: E402

REPORT_TYPES = {"techreport", "report", "misc", "book", "manual", "booklet", "unpublished",
                "online", "electronic", "www", "mvbook", "collection", "proceedings",
                "dataset", "software"}
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
STOP = set("""a an the of and or in on for to with by from at as is are was were be been this that
these those its their our we it into over under between among than via per not no""".split())
EN_FUNC = set("the of and to in is that for with as on are by this be from an which or at".split())
OTHER_FUNC = set("""de het een van niet der die das und nicht ist mit le les et des du est une pour
el los las y que por para con una il di che della sono não uma com""".split())
SCAN_VERSION = 2          # bump when what scan_pdfs records changes


# ---- BibTeX -------------------------------------------------------------------
def _braced(s, i):
    """s[i] is '{' or '"'; return (value, index after it)."""
    if s[i] == '"':
        j = i + 1
        depth = 0
        while j < len(s):
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
            elif s[j] == '"' and depth == 0 and s[j - 1] != "\\":
                return s[i + 1:j], j + 1
            j += 1
        return s[i + 1:], len(s)
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{" and (j == 0 or s[j - 1] != "\\"):
            depth += 1
        elif s[j] == "}" and s[j - 1] != "\\":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def parse_bib(path):
    """{key: {"type", "fields": {name: value}, "bib": path}}"""
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        s = fh.read()
    out = {}
    for m in re.finditer(r"@([A-Za-z]+)\s*([{(])", s):
        typ = m.group(1).lower()
        if typ in ("comment", "preamble", "string"):
            continue
        i = m.end()
        km = re.match(r"\s*([^,\s]+)\s*,", s[i:])
        if not km:
            continue
        key = km.group(1)
        i += km.end()
        fields = {}
        while i < len(s):
            fm = re.match(r"\s*([A-Za-z][\w\-]*)\s*=\s*", s[i:])
            if not fm:
                break
            name = fm.group(1).lower()
            i += fm.end()
            if i < len(s) and s[i] in '{"':
                val, i = _braced(s, i)
            else:
                vm = re.match(r"[^,}\n]*", s[i:])
                val = vm.group(0).strip()
                i += vm.end()
            fields[name] = val
            cm = re.match(r"\s*(,|[})])", s[i:])
            if not cm or cm.group(1) != ",":
                break
            i += cm.end()
        out[key] = {"type": typ, "fields": fields, "bib": path}
    return out


def bib_files(entry):
    """PDF paths in a `file` field: Zotero 'Desc:path:mime', JabRef ':path:PDF',
    Mendeley ':C$\\backslash$:/x.pdf:pdf', or a bare path; ';'-separated."""
    raw = entry["fields"].get("file", "")
    if not raw:
        return []
    raw = raw.replace("$\\backslash$", "\\").replace("{\\textbackslash}", "\\")
    base = os.path.dirname(entry["bib"])
    out = []
    for part in re.split(r"(?<!\\);", raw):
        bits = re.split(r"(?<!\\):", part)
        bits = [b.replace("\\:", ":") for b in bits]
        # a Windows drive letter was split off: 'C' + '/Users/...'
        merged = []
        for b in bits:
            if merged and len(merged[-1]) == 1 and merged[-1].isalpha() and b[:1] in "/\\":
                merged[-1] += ":" + b
            else:
                merged.append(b)
        cands = [b for b in merged if b.lower().endswith(".pdf")] or \
                ([merged[0]] if len(merged) == 1 else [])
        for c in cands:
            c = c.strip().replace("\\\\", "\\")
            p = c if os.path.isabs(c) else os.path.join(base, c)
            out.append(os.path.normpath(p))
    return out


def plain(s):
    s = re.sub(r"\\[a-zA-Z]+\s*", " ", s or "")
    s = unicodedata.normalize("NFKD", s.replace("{", "").replace("}", ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def words(s):
    s = plain(s).lower()
    for k, v in {"\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff", "\ufb03": "ffi", "\ufb04": "ffl"}.items():
        s = s.replace(k, v)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    return re.findall(r"[a-z0-9]+", s)


def norm_doi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d)
    return d.rstrip(".,;)")


def first_author(entry):
    a = plain(entry["fields"].get("author", "")).split(" and ")[0].strip()
    if not a:
        return ""
    sur = a.split(",")[0] if "," in a else a.split()[-1]
    return re.sub(r"[^a-z]", "", sur.lower())


# ---- PDFs -------------------------------------------------------------------------
def pdf_head(path):
    """(text of the first two pages, text of pages 2-6 for the language
    guess) -- PyMuPDF, else pdftotext."""
    try:
        import fitz
        with fitz.open(path) as d:
            pages = [d[i].get_text() for i in range(min(6, d.page_count))]
        return "\n".join(pages[:2]), "\n".join(pages[1:] if len(pages) > 2 else pages)
    except ImportError:
        pass
    except Exception:
        return "", ""
    import shutil
    import subprocess
    exe = shutil.which("pdftotext")
    if not exe:
        return "", ""
    r = subprocess.run([exe, "-q", "-l", "6", "-enc", "UTF-8", path, "-"], capture_output=True)
    pages = r.stdout.decode("utf-8", "replace").split("\f")
    return "\n".join(pages[:2]), "\n".join(pages[1:] if len(pages) > 2 else pages)


def scan_pdfs(folders, cache_path):
    cache = {}
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as fh:
                cache = json.load(fh)
        except ValueError:
            cache = {}
    pdfs = []
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in sorted(files):
                if f.lower().endswith(".pdf"):
                    pdfs.append(os.path.normpath(os.path.join(root, f)))
    out, changed = [], False
    for p in sorted(set(pdfs)):
        st = os.stat(p)
        sig = "%d:%d" % (st.st_size, int(st.st_mtime))
        rec = cache.get(p)
        if not rec or rec.get("sig") != sig or rec.get("v") != SCAN_VERSION:
            text, body = pdf_head(p)
            w = words(text)
            first = text[:6000]
            rec = {"sig": sig, "v": SCAN_VERSION,
                   "dois": sorted({norm_doi(d) for d in re.findall(r"10\.\d{4,9}/[^\s\"<>]+", first)}),
                   "words": w[:2500], "lang": lang_guess(body), "md5": md5(p)}
            cache[p] = rec
            changed = True
        rec = dict(rec, path=p)
        out.append(rec)
    if changed:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
    return out


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lang_guess(text):
    """English function words against the commonest ones of Dutch, German,
    French, Spanish, Italian and Portuguese. A share threshold alone flags
    English cover pages (a report title page, a Cochrane front page)."""
    if not text.strip():
        return "?"
    cjk = sum(1 for c in text if "\u3040" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7af")
    if cjk > 0.2 * len(text.replace(" ", "")):
        return "non-en"
    w = re.findall(r"[A-Za-z\u00c0-\u017f]+", text.lower())
    if len(w) < 150:
        return "?"
    en = sum(1 for x in w if x in EN_FUNC)
    other = sum(1 for x in w if x in OTHER_FUNC)
    return "non-en" if other > en else "en"


def contains_seq(hay, needle):
    if not needle or len(needle) > len(hay):
        return False
    n = len(needle)
    first = needle[0]
    for i in range(len(hay) - n + 1):
        if hay[i] == first and hay[i:i + n] == needle:
            return True
    return False


# ---- notes ------------------------------------------------------------------------
def scan_notes(notes_dir, field):
    out = {}
    pat = re.compile(r"^\s*(?:%s|pdf|PDF|file)\s*[:：]\s*(.+?)\s*$" % re.escape(field), re.M)
    for root, _, files in os.walk(notes_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            with open(p, encoding="utf-8", errors="replace") as fh:
                m = pat.search(fh.read(4000))
            pdf = None
            if m:
                v = m.group(1).strip().strip("'\"")
                pdf = os.path.normpath(v if os.path.isabs(v) else os.path.join(root, v))
            out[f[:-3]] = {"note": p, "pdf": pdf}
    return out


# ---- matching ------------------------------------------------------------------------
def match(keys, bib, notes, pdfs):
    by_doi, by_stem = {}, {}
    for r in pdfs:
        for d in r["dois"]:
            by_doi.setdefault(d, []).append(r)
        by_stem.setdefault(os.path.splitext(os.path.basename(r["path"]))[0].lower(), []).append(r)
    idx = {}
    for key in sorted(keys):
        e = bib.get(key)
        rec = {"pdf": None, "method": "unmatched", "type": e["type"] if e else "",
               "title": plain(e["fields"].get("title", "")) if e else "",
               "year": (e["fields"].get("year", "") if e else "").strip()}
        cands, how = [], ""
        if e:
            fs = [p for p in bib_files(e) if os.path.isfile(p)]
            if fs:
                cands, how = fs, "bib-file"
            elif bib_files(e):
                rec["problem"] = "bib file field points to a missing file: " + bib_files(e)[0]
        if not cands and key in notes and notes[key]["pdf"]:
            if os.path.isfile(notes[key]["pdf"]):
                cands, how = [notes[key]["pdf"]], "note"
            else:
                rec["problem"] = "note's PDF path does not exist: " + notes[key]["pdf"]
        if not cands and key.lower() in by_stem:
            cands, how = [r["path"] for r in by_stem[key.lower()]], "filename"
        if not cands and e and norm_doi(e["fields"].get("doi")):
            hits = by_doi.get(norm_doi(e["fields"]["doi"]), [])
            if hits:
                cands, how = [r["path"] for r in hits], "doi"
        if not cands and e and rec["title"]:
            tw = words(rec["title"])
            if len(tw) >= 3:
                hits = [r["path"] for r in pdfs if contains_seq(r["words"], tw)
                        or contains_seq(words(os.path.basename(r["path"])), tw[:5])]
                if hits:
                    cands, how = hits, "title"
        if not cands and e:
            sur, yr = first_author(e), re.sub(r"\D", "", rec["year"])[:4]
            if sur and yr:
                hits = [r["path"] for r in pdfs if sur in words(os.path.basename(r["path"]))
                        and yr in os.path.basename(r["path"])]
                if hits:
                    cands, how = hits, "author-year"
        cands = sorted(set(cands), key=rank)
        if cands:
            rec.update(pdf=cands[0], method=how)
            if len(cands) > 1:
                rec["candidates"] = cands
        idx[key] = rec
    return idx


def rank(path):
    """Order candidates: the article before a supplement, then the larger file."""
    supp = bool(re.search(r"supp|appendix|online[ _-]?app|(?<![A-Za-z])si(?![A-Za-z])", os.path.basename(path), re.I))
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    return (supp, -size, path)


def corpus_keys(keys):
    """cite key -> corpus key: letters, digits, _ and -; unique ignoring case
    (NTFS and macOS file names are case-insensitive)."""
    out, taken = {}, set()
    for k in sorted(keys):
        c = re.sub(r"[^A-Za-z0-9_\-]+", "_", k).strip("_-") or "key"
        if not c[0].isalnum():
            c = "k" + c
        base, n = c, 2
        while c.lower() in taken:
            c, n = "%s_%d" % (base, n), n + 1
        taken.add(c.lower())
        out[k] = c
    return out


# ---- main ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manuscript")
    ap.add_argument("--library", action="append", default=[])
    ap.add_argument("--notes")
    ap.add_argument("--notes-pdf-field", default="对应PDF")
    ap.add_argument("--field")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--citation-style", default="author-year", choices=["author-year", "numeric", "mixed"])
    ap.add_argument("--dest")
    ap.add_argument("--include-uncited", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--finish", action="store_true")
    a = ap.parse_args()
    if a.finish:
        return finish(a)
    if not a.manuscript or not a.library:
        F.die("give --manuscript <main.tex> and at least one --library <folder or .bib>")

    ms = M.Manuscript(a.manuscript)
    keys = ms.cited_keys()
    print("manuscript: %s" % ms.path)
    print("  %d sections, %d cited keys, bibliography: %s"
          % (len(ms.sections), len(keys), ", ".join(os.path.basename(b) for b in ms.bib_files) or "none"))
    if not keys:
        F.die("the manuscript cites nothing (no \\cite commands found)")

    bib, folders = {}, []
    for b in ms.bib_files:
        if os.path.isfile(b):
            bib.update(parse_bib(b))
    for lib in a.library:
        lib = os.path.abspath(lib)
        if os.path.isdir(lib):
            folders.append(lib)
        elif lib.lower().endswith(".bib") and os.path.isfile(lib):
            for k, e in parse_bib(lib).items():
                # the library export is the authority on where files are: a
                # manuscript .bib copied elsewhere carries the same file field
                # with paths that no longer resolve
                have = k in bib and any(os.path.isfile(p) for p in bib_files(bib[k]))
                if k in bib and not have and any(os.path.isfile(p) for p in bib_files(e)):
                    bib[k]["fields"]["file"] = e["fields"]["file"]
                    bib[k]["bib"] = e["bib"]
                bib.setdefault(k, e)
        else:
            F.die("--library must be a folder or a .bib file: " + lib)
    # PDFs a library .bib points at also form a folder to search
    for e in bib.values():
        for p in bib_files(e):
            if os.path.isfile(p) and os.path.dirname(p) not in folders:
                folders.append(os.path.dirname(p))
    notes = scan_notes(os.path.abspath(a.notes), a.notes_pdf_field) if a.notes else {}
    for n in notes.values():
        if n["pdf"] and os.path.isfile(n["pdf"]) and os.path.dirname(n["pdf"]) not in folders:
            folders.append(os.path.dirname(n["pdf"]))
    polish_dir = os.path.join(ms.dir, ".polish")
    pdfs = scan_pdfs(folders, os.path.join(polish_dir, "pdf-scan-cache.json"))
    print("library: %d bib entries, %d PDFs in %d folder(s)%s"
          % (len(bib), len(pdfs), len(folders), ", %d reading notes" % len(notes) if a.notes else ""))

    idx = match(keys, bib, notes, pdfs)
    ck = corpus_keys(keys)
    by_path = {r["path"]: r for r in pdfs}
    for k, rec in idx.items():
        rec["corpus_key"] = ck[k]
        r = by_path.get(rec["pdf"]) if rec["pdf"] else None
        rec["lang"] = r["lang"] if r else ("?" if rec["pdf"] else "")
        if k in notes:
            rec["note_file"] = notes[k]["note"]

    report(idx, pdfs, keys)
    index = {"meta": {"built": F.TODAY, "manuscript": ms.path, "library": [os.path.abspath(x) for x in a.library],
                      "notes_dir": os.path.abspath(a.notes) if a.notes else "",
                      "notes_pdf_field": a.notes_pdf_field},
             "keys": idx}
    os.makedirs(polish_dir, exist_ok=True)
    with open(os.path.join(polish_dir, "library-index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    print("\nwrote %s" % os.path.join(polish_dir, "library-index.json"))
    if a.dry_run:
        print("[dry run] no stamping, no config, no ingest.")
        return 0

    # ---- the field ------------------------------------------------------------
    if not a.field:
        print("\nNEXT: ask the user for a field name (kebab-case, e.g. health-econ) and a few"
              " topic keywords, then re-run with --field <name> --keywords \"...\".")
        return 3
    fld = F.Field(a.field, a.dest)
    if fld.exists():
        print("\nfield %r exists (built tiers %s)" % (a.field, fld.built_tiers() or "none"))
        if not os.path.isdir(fld.polish):
            F.run([sys.executable, "-B", os.path.join(F.HERE, "stamp.py"), a.field, "--add", "polish",
                   "--dest", fld.dest])
    else:
        if not a.keywords.strip():
            print("\nNEXT: new field %r -- ask the user for topic keywords, then re-run with"
                  " --keywords \"...\"." % a.field)
            return 3
        F.run([sys.executable, "-B", os.path.join(F.HERE, "stamp.py"), a.field, "--keywords", a.keywords,
               "--citation-style", a.citation_style, "--dest", fld.dest])
    fld.set_scalar("manuscript_tex", ms.path.replace("\\", "/"))
    print("manuscript_tex -> both field-configs")

    if 0 in fld.built_tiers():
        n = sum(1 for k in idx if os.path.isfile(os.path.join(fld.lit, "references", "corpus",
                                                              idx[k]["corpus_key"] + ".txt")))
        print("\nTier 0 is already built: the corpus is left as it is (%d of %d cited keys have"
              " a corpus text). Next: onboard.py --finish --field %s" % (n, len(idx), a.field))
        return 0

    rows = [(rec["corpus_key"], rec["pdf"], k, rec) for k, rec in sorted(idx.items()) if rec["pdf"]]
    if a.include_uncited:
        used = {rec["pdf"] for rec in idx.values() if rec["pdf"]}
        taken = {r[0].lower() for r in rows}
        for r in pdfs:
            if r["path"] in used:
                continue
            c = re.sub(r"[^A-Za-z0-9_\-]+", "_", os.path.splitext(os.path.basename(r["path"]))[0]).strip("_-")
            c = c if c and c[0].isalnum() else "doc_" + r["md5"][:8]
            while c.lower() in taken:
                c += "_x"
            taken.add(c.lower())
            rows.append((c, r["path"], "", {"type": "", "method": "uncited"}))
    if not rows:
        F.die("no cited key has a PDF -- nothing to ingest")
    cmap = os.path.join(fld.lit, "references", "corpus_map.csv")
    with open(cmap, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "path", "group", "role", "note"])
        for c, p, k, rec in rows:
            t = rec.get("type") or ""
            role = "report" if t in REPORT_TYPES else ("research" if t else "")
            w.writerow([c, p, "", role, "cite:%s type:%s match:%s" % (k, rec.get("type", ""), rec.get("method", ""))])
    print("\ncorpus map: %s (%d rows)" % (cmap, len(rows)))
    print("ingest:")
    F.run([sys.executable, "-B", os.path.join(F.HERE, "ingest.py"), fld.lit, "--map", cmap])
    print("manifest:")
    fld.run("lit", "build_corpus_meta.py")
    print("\nNEXT: py -3 %s %s   (Tier 0 acceptance, default decisions)"
          % (os.path.join(F.HERE, "tier0_accept.py"), a.field))
    return 0


def report(idx, pdfs, keys):
    from collections import Counter
    by = Counter(r["method"] for r in idx.values())
    print("\nINDEX: %d of %d cited keys matched to a PDF" % (len(idx) - by["unmatched"], len(idx)))
    for m in ("bib-file", "note", "filename", "doi", "title", "author-year"):
        if by[m]:
            print("  %-12s %d" % (m, by[m]))
    un = sorted(k for k, r in idx.items() if r["method"] == "unmatched")
    if un:
        print("  unmatched (%d):" % len(un))
        for k in un:
            r = idx[k]
            why = r.get("problem") or ("not in any .bib" if not r["type"] else "no PDF found by any rule")
            print("    %-28s %-12s %s" % (k, r["type"] or "-", why))
    amb = sorted(k for k, r in idx.items() if r.get("candidates"))
    if amb:
        print("  several candidates (first taken; check) (%d):" % len(amb))
        for k in amb:
            print("    %-28s %s: %s" % (k, idx[k]["method"], " | ".join(os.path.basename(p) for p in idx[k]["candidates"])))
    used = {}
    for k, r in idx.items():
        if r["pdf"]:
            used.setdefault(r["pdf"], []).append(k)
    shared = {p: ks for p, ks in used.items() if len(ks) > 1}
    if shared:
        print("  one PDF matched to several keys (%d):" % len(shared))
        for p, ks in sorted(shared.items()):
            print("    %s <- %s" % (os.path.basename(p), ", ".join(sorted(ks))))
    dup = {}
    for r in pdfs:
        for d in r["dois"][:1]:
            dup.setdefault(d, []).append(r["path"])
        h = dup.setdefault("md5:" + r["md5"], [])
        h.append(r["path"])
    dups = {d: ps for d, ps in dup.items() if len(set(ps)) > 1}
    if dups:
        print("  duplicate versions in the library (same DOI or identical file) (%d):" % len(dups))
        for d, ps in sorted(dups.items())[:30]:
            print("    %s: %s" % (d, " | ".join(sorted(os.path.basename(p) for p in set(ps)))))
    ne = sorted(k for k, r in idx.items() if r.get("lang") == "non-en")
    if ne:
        print("  not English by its first pages (%d): %s" % (len(ne), ", ".join(ne)))
    rep = sorted(k for k, r in idx.items() if r["pdf"] and r["type"] in REPORT_TYPES)
    if rep:
        print("  report / book / misc entries (terminology only by default) (%d): %s" % (len(rep), ", ".join(rep)))
    uncited = len({r["path"] for r in pdfs} - {r["pdf"] for r in idx.values() if r["pdf"]})
    print("  library PDFs not cited by the manuscript: %d (--include-uncited adds them to the corpus)" % uncited)


def finish(a):
    if not a.field:
        F.die("--finish needs --field")
    fld = F.Field(a.field, a.dest).require()
    cfg = fld.config()
    cp = fld.cfgparse()
    if a.manuscript:
        fld.set_scalar("manuscript_tex", os.path.abspath(a.manuscript).replace("\\", "/"))
    mt = cp.as_str(cfg.get("manuscript_tex")) if not a.manuscript else os.path.abspath(a.manuscript)
    if not mt:
        F.die("no manuscript_tex in the field-config: pass --manuscript")
    print("manuscript_tex: %s" % mt)
    print("\nlit check_drift:")
    r = fld.run("lit", "check_drift.py", check=False, show=False)
    tail = [l for l in r.stdout.splitlines() if l.strip()][-3:]
    print("\n".join("    | " + l for l in tail))
    if not os.path.isdir(fld.polish):
        F.run([sys.executable, "-B", os.path.join(F.HERE, "stamp.py"), a.field, "--add", "polish",
               "--dest", fld.dest])
    print("\n%s-polish doctor:" % a.field)
    fld.run("polish", "doctor.py", ["--manuscript", mt], check=False)
    print("\nwhat building further would cost:")
    F.run([sys.executable, "-B", os.path.join(F.HERE, "tier_status.py"), a.field, "--dest", fld.dest], check=False)
    print("\nASK THE USER before Tier 2-4: they are model reading passes and use many tokens"
          " (estimate above). Tier 0-1 are done; <field>-lit and the polish steps marked ready work now.")
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
