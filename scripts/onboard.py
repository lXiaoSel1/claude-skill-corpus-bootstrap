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
     (1.6.0) --reuse-corpus DIR: a key whose text is already DIR/<key>.txt
     (an earlier corpus, e.g. a hand-built skill's) is copied verbatim
     instead of converting its PDF again -- the PDF stays in the index for
     the polish checks; --extra-map CSV adds papers the manuscript does not
     cite (key,path[,group][,role][,note]; a path may be a .pdf or a .txt).
Next: tier0_accept.py, calibrate_paragraphs.py, tier1_fill.py, then
onboard.py --finish.

RUN
    py -3 scripts/onboard.py --manuscript <main.tex> --library <folder or .bib> [--library ...]
        [--notes <folder>] [--notes-pdf-field pdf] [--field <slug> --keywords "..."]
        [--citation-style author-year|numeric|mixed] [--dest <skills dir>]
        [--include-uncited] [--reuse-corpus <txt dir>] [--extra-map <csv>] [--dry-run]
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

# .bib types used for terminology only by default (books, manuals, data)
REPORT_TYPES = {"book", "manual", "booklet", "mvbook", "collection", "proceedings",
                "dataset", "software"}
# working papers and preprints (Zotero exports an NBER or SSRN paper as
# @techreport or @report, arXiv as @misc): research, unless SHORT at Tier 0
WORKING_TYPES = {"techreport", "report", "misc", "unpublished", "online", "electronic", "www"}
EN_FUNC = set("the of and to in is that for with as on are by this be from an which or at".split())
OTHER_FUNC = set("""de het een van niet der die das und nicht ist mit le les et des du est une pour
el los las y que por para con una il di che della sono não uma com""".split())
SCAN_VERSION = 3          # bump when what scan_pdfs records changes


def extractor():
    """The PDF text extractor pdf_head will use: pymupdf, pdftotext or none."""
    try:
        import fitz  # noqa: F401
        return "pymupdf"
    except ImportError:
        import shutil
        return "pdftotext" if shutil.which("pdftotext") else "none"


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


def scan_pdfs(folders, cache_path, flat=()):
    """folders are searched with their subfolders (the --library folders);
    flat ones only at their own level (the folders a .bib or a note points
    into, which may be a whole Documents or Downloads folder)."""
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
    for folder in flat:
        for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(folder, f)):
                pdfs.append(os.path.normpath(os.path.join(folder, f)))
    x = extractor()
    if x == "none" and pdfs:
        print("  WARNING: no PDF text extractor (PyMuPDF or pdftotext): matching by DOI, title"
              " and language is off (%s -m pip install pymupdf)" % F.PY)
    out, changed = [], False
    for p in sorted(set(pdfs)):
        st = os.stat(p)
        sig = "%d:%d" % (st.st_size, int(st.st_mtime))
        rec = cache.get(p)
        # a record made with no extractor is redone once one is installed
        if not rec or rec.get("sig") != sig or rec.get("v") != SCAN_VERSION \
                or (rec.get("x") == "none" and x != "none"):
            text, body = pdf_head(p)
            w = words(text)
            first = text[:6000]
            rec = {"sig": sig, "v": SCAN_VERSION, "x": x,
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
FRONT_KEY = re.compile(r"^\s*(?:bib_key|bibkey|citekey|cite_key|citation_key|key)\s*[:：]\s*['\"]?([^\s'\"]+)",
                       re.M | re.I)
PDF_DIR = re.compile(r"^\s*(?:PDF路径|PDF目录|pdf_dir|pdf_path|pdf_folder)\s*[:：]\s*(.+?)\s*$", re.M | re.I)


def note_key(text, fname):
    """A note's cite key: the bib_key (or citekey / key) in its front matter
    when it has one, else its file name."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        m = FRONT_KEY.search(text[:end] if end > 0 else text[:2000])
        if m:
            return m.group(1)
    return fname


def note_pdf(value, note_dir, text, names):
    """The PDF a note names: a path from the note's folder, else the file name
    in the folder a PDF-directory field gives, else a library PDF of that name."""
    v = value.strip().strip("'\"")
    cands = [v if os.path.isabs(v) else os.path.join(note_dir, v)]
    d = PDF_DIR.search(text)
    if d:
        dd = d.group(1).strip().strip("'\"")
        cands.append(os.path.join(dd if os.path.isabs(dd) else os.path.join(note_dir, dd), os.path.basename(v)))
    for c in cands:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return names.get(name_key(os.path.basename(v))) or os.path.normpath(cands[0])


def scan_notes(notes_dir, field, names=None):
    """{cite key: {"note": path, "pdf": path or None}}; names maps a lower-case
    PDF file name to its path in the library folders."""
    out = {}
    pat = re.compile(r"^\s*(?:%s|pdf|PDF|file|对应PDF)\s*[:：]\s*(.+?)\s*$" % re.escape(field), re.M)
    for root, _, files in os.walk(notes_dir):
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read(4000)
            key = note_key(text, f[:-3])
            if key in out and f[:-3] != key:         # two notes, one key: the one named after it wins
                continue
            m = pat.search(text)
            out[key] = {"note": p, "pdf": note_pdf(m.group(1), root, text, names or {}) if m else None}
    return out


def name_key(fname):
    """A file name compared without case, spaces or punctuation: a note that
    writes "Constraints Evidence" finds "Constraints  Evidence.pdf"."""
    return re.sub(r"[^0-9a-z]+", "", fname.lower())


def pdf_names(folders):
    """{name_key(file name): path} for every PDF under the library folders."""
    out = {}
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.lower().endswith(".pdf"):
                    out.setdefault(name_key(f), os.path.normpath(os.path.join(root, f)))
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
        cands = sorted(set(cands), key=ranker(e))
        if cands:
            rec.update(pdf=cands[0], method=how)
            if len(cands) > 1:
                rec["candidates"] = cands
        idx[key] = rec
    return idx


def ranker(entry):
    """Order one key's candidates: a file named after the entry (first author
    and year, or the title's first words) before one that only mentions it --
    a paper whose references cite the title is not the paper -- then rank()."""
    sur = first_author(entry) if entry else ""
    yr = (entry["fields"].get("year", "") if entry else "").strip()[:4]
    tw = words(entry["fields"].get("title", "")) if entry else []

    def key(path):
        bw = words(os.path.basename(path))
        named = bool(sur) and sur in bw and (not yr or yr in bw)
        titled = len(tw) >= 3 and contains_seq(bw, tw[:5])
        return (not (named or titled),) + rank(path)
    return key


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
        c = F.safe_key(k, "_") or "key"
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
    ap.add_argument("--notes-pdf-field", default="pdf")
    ap.add_argument("--field")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--citation-style", default="author-year", choices=F.STYLES)
    ap.add_argument("--dest")
    ap.add_argument("--include-uncited", action="store_true")
    ap.add_argument("--reuse-corpus")
    ap.add_argument("--extra-map")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--finish", action="store_true")
    a = ap.parse_args()
    if a.field:
        a.field = F.norm_field(a.field)   # the slug stamp.py writes
        if not F.SLUG.match(a.field):
            F.die("--field must be lowercase ASCII letters and digits with single hyphens"
                  " between (e.g. health-econ): %r" % a.field)
    if a.finish:
        return finish(a)
    if not a.manuscript or not a.library:
        F.die("give --manuscript <main.tex> and at least one --library <folder or .bib>")

    if not os.path.isfile(F.user_path(a.manuscript)):
        F.die("no manuscript file at %s" % F.user_path(a.manuscript))
    ms = M.Manuscript(F.user_path(a.manuscript))
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
        lib = F.user_path(lib)
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
    # the folders a library .bib or a reading note points into are searched
    # too, at their own level only
    flat = []
    for e in bib.values():
        for p in bib_files(e):
            if os.path.isfile(p) and os.path.dirname(p) not in flat:
                flat.append(os.path.dirname(p))
    notes = scan_notes(F.user_path(a.notes), a.notes_pdf_field, pdf_names(folders)) if a.notes else {}
    for n in notes.values():
        if n["pdf"] and os.path.isfile(n["pdf"]) and os.path.dirname(n["pdf"]) not in flat:
            flat.append(os.path.dirname(n["pdf"]))
    polish_dir = os.path.join(ms.dir, ".polish")
    pdfs = scan_pdfs(folders, os.path.join(polish_dir, "pdf-scan-cache.json"), flat)
    print("library: %d bib entries, %d PDFs in %d folder(s)%s"
          % (len(bib), len(pdfs), len(folders) + len(flat),
             ", %d reading notes" % len(notes) if a.notes else ""))

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
            c = F.safe_key(os.path.splitext(os.path.basename(r["path"]))[0], "_")
            c = c if c and c[0].isalnum() else "doc_" + r["md5"][:8]
            while c.lower() in taken:
                c += "_x"
            taken.add(c.lower())
            rows.append((c, r["path"], "", {"type": "", "method": "uncited"}))
    reused = 0
    if a.reuse_corpus:
        rd = F.user_path(a.reuse_corpus)
        if not os.path.isdir(rd):
            F.die("--reuse-corpus: no folder %s" % rd)
        out = []
        # a cited key the library has no PDF for still enters with its old text
        have = {r[2] for r in rows}
        rows = rows + [(rec["corpus_key"], None, k, rec) for k, rec in sorted(idx.items())
                       if k not in have and any(os.path.isfile(os.path.join(rd, n + ".txt"))
                                                for n in (rec["corpus_key"], k) if n)]
        for c, p, k, rec in rows:
            txt = next((os.path.join(rd, n + ".txt") for n in (c, k) if n
                        and os.path.isfile(os.path.join(rd, n + ".txt"))), None)
            if txt:
                reused += 1
                rec = dict(rec, method=(rec.get("method", "") + "+reused-txt"))
            out.append((c, txt or p, k, rec))
        rows = out
    extra = []
    if a.extra_map:
        em = F.user_path(a.extra_map)
        base = os.path.dirname(em)
        taken = {r[0].lower() for r in rows}
        with open(em, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                key, path = (r.get("key") or "").strip(), (r.get("path") or "").strip()
                if not key or not path:
                    continue
                if key.lower() in taken:
                    print("  --extra-map: %s is already in the map (cited); the cited row is kept" % key)
                    continue
                path = path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))
                if not os.path.isfile(path):
                    F.die("--extra-map: %s -> %s does not exist" % (key, path))
                taken.add(key.lower())
                extra.append((key, path, r.get("group", ""), r.get("role", ""), r.get("note", "") or "uncited (extra map)"))
    if not rows and not extra:
        F.die("no cited key has a PDF -- nothing to ingest")
    cmap = os.path.join(fld.lit, "references", "corpus_map.csv")
    with open(cmap, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "path", "group", "role", "note"])
        for c, p, k, rec in rows:
            t = rec.get("type") or ""
            role = ("report" if t in REPORT_TYPES else "working" if t in WORKING_TYPES
                    else "research" if t else "")
            w.writerow([c, p, "", role, "cite:%s type:%s match:%s" % (k, rec.get("type", ""), rec.get("method", ""))])
        for key, path, group, role, note in extra:
            w.writerow([key, path, group, role, note])
    print("\ncorpus map: %s (%d rows: %d cited, %d of them reused as text; %d extra)"
          % (cmap, len(rows) + len(extra), len(rows), reused, len(extra)))
    print("ingest:")
    F.run([sys.executable, "-B", os.path.join(F.HERE, "ingest.py"), fld.lit, "--map", cmap])
    print("manifest:")
    fld.run("lit", "build_corpus_meta.py")
    if notes:
        write_notes_index(fld, idx)
    print("\nNEXT: %s %s %s%s   (Tier 0 acceptance, default decisions)"
          % (F.PY, os.path.join(F.HERE, "tier0_accept.py"), fld.field, F.dest_arg(a.dest)))
    return 0


def write_notes_index(fld, idx):
    """<field>-draft/references/notes-index.md: the draft skill's step 2b map
    from a cited key to its reading note (and its corpus text)."""
    rows = sorted((k, r) for k, r in idx.items() if r.get("note_file"))
    none = sorted(k for k, r in idx.items() if not r.get("note_file"))
    L = ["# notes-index.md -- cite key -> reading note (written by onboard.py %s)" % F.TODAY, "",
         "> The -draft skill's step 2b: paste source lines from the note, else from",
         "> `../%s-lit/references/corpus/<corpus key>.txt`. Re-run onboarding to rebuild." % fld.field,
         "", "## A. Keys with a reading note", "",
         "| cite key | corpus key | note |", "|---|---|---|"]
    L += ["| `%s` | `%s` | %s |" % (k, r.get("corpus_key", k), r["note_file"].replace("\\", "/"))
          for k, r in rows]
    L += ["", "## B. Cited keys with no reading note", "",
          ", ".join("`%s`" % k for k in none) if none else "(none)", ""]
    p = os.path.join(fld.draft, "references", "notes-index.md")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    print("notes index: %s (%d with a note, %d without)" % (p, len(rows), len(none)))


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
        print("  book / manual / data entries (terminology only by default) (%d): %s" % (len(rep), ", ".join(rep)))
    wp = sorted(k for k, r in idx.items() if r["pdf"] and r["type"] in WORKING_TYPES)
    if wp:
        print("  working papers / preprints / reports (research unless short) (%d): %s" % (len(wp), ", ".join(wp)))
    # an article whose PDF says on its first page that it is a manuscript or a
    # preprint: its pages, and sometimes its tables, are not the journal's
    by_path = {r["path"]: r for r in pdfs}
    marks = (["author", "manuscript"], ["accepted", "manuscript"], ["hhs", "public", "access"], ["preprint"])
    ms_ = sorted(k for k, r in idx.items() if r["pdf"] and r["type"] not in WORKING_TYPES
                 and any(contains_seq((by_path.get(r["pdf"]) or {}).get("words", [])[:400], m) for m in marks))
    if ms_:
        print("  articles whose PDF is a manuscript or preprint, not the published version (%d): %s"
              % (len(ms_), ", ".join(ms_)))
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
