#!/usr/bin/env python3
"""Tier 4, writing canon, steps 1-2 done for you: turn the writing guides you
collected into the canon-sources folder the field's -draft skill reads.

What it does:
  * converts each guide to UTF-8 text <key>.txt -- PDF through the same
    converter as ingest.py (pinned pdftotext, else PyMuPDF), saved web pages
    (.html/.htm) through the standard library, .txt/.md copied; ligatures and
    curly quotes are normalised so ASCII grep finds them, line breaks are kept
    (structure-canon.md cites guides by line number);
  * skips image-only scans (fewer than 60 words per page) and reports them;
  * writes canon_sources.json (provenance) and a fresh _manifest.md;
  * points canon_dir in BOTH field-configs at the folder;
  * fills the -draft registry's canon_sources: count, location and 3-4
    verbatim spot quotes that check_drift greps.
Step 3 (structure-canon.md) is a model pass: see the NEXT line it prints.
You collect the guides yourself; nothing is fetched.

Keys: the .bib key when the guide comes from a .bib, else a slug of the file
name. A text you repaired by hand is never overwritten (--force KEY does).

RUN
    py -3 scripts/canon_ingest.py <field> --src <folder or .bib> [--src ...] [--map keys.csv]
        [--canon-dir <dir>] [--dest <skills dir>] [--force KEY] [--dry-run]
    keys.csv columns: key,path[,title][,url]
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser

import _factory as F

sys.path.insert(0, F.HERE)
import ingest  # noqa: E402  (converter, convert, page_count, sha256)

EXT = (".pdf", ".html", ".htm", ".txt", ".md")
NORM = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
        "‘": "'", "’": "'", "“": '"', "”": '"', "­": "", " ": " "}
SCAN_WPP = 60


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(name))[0].lower()).strip("-")
    return (s[:40].rstrip("-") or "guide")


def clean_key(k):
    k = re.sub(r"[^A-Za-z0-9_\-]+", "-", k).strip("-_")
    return k if k and k[0].isalnum() else "g-" + k


class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section",
             "article", "blockquote", "pre", "ul", "ol", "table", "header", "footer", "dd", "dt"}
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.out, self.skip, self.title, self._in_title = [], 0, "", False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.out.append(data)


def read_any(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def normalize(text):
    for k, v in NORM.items():
        text = text.replace(k, v)
    # every line kept, in place: structure-canon.md cites guides by line number
    lines = [l.rstrip() for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def to_text(path, conv, tmp):
    """(text, pages, title, converter label)"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        ingest.convert(conv, path, tmp)
        with open(tmp, encoding="utf-8", errors="replace") as fh:
            t = fh.read()
        os.remove(tmp)
        return t, ingest.page_count(path), "", conv[0]
    if ext in (".html", ".htm"):
        p = _Text()
        p.feed(read_any(path))
        t = "".join(p.out)
        t = re.sub(r"[ \t]+", " ", t)
        return t, 0, re.sub(r"\s+", " ", p.title).strip(), "html"
    return read_any(path), 0, "", "copied-text"


def collect(a):
    """[{key, path, title, url}]"""
    sys.path.insert(0, F.HERE)
    import onboard
    items = []
    if a.map:
        with open(a.map, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("key") or "").strip() and (r.get("path") or "").strip():
                    items.append({"key": clean_key(r["key"].strip()), "path": os.path.abspath(r["path"].strip()),
                                  "title": (r.get("title") or "").strip(), "url": (r.get("url") or "").strip()})
    for src in a.src or []:
        if os.path.isdir(src):
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in sorted(files):
                    if f.lower().endswith(EXT) and not f.startswith("_"):
                        items.append({"key": slug(f), "path": os.path.abspath(os.path.join(root, f)),
                                      "title": "", "url": ""})
        elif src.lower().endswith(".bib") and os.path.isfile(src):
            for k, e in onboard.parse_bib(src).items():
                fs = [p for p in onboard.bib_files(e) if os.path.isfile(p) and p.lower().endswith(EXT)]
                if not fs:
                    continue
                doi = onboard.norm_doi(e["fields"].get("doi"))
                url = e["fields"].get("url", "") or ("https://doi.org/" + doi if doi else "")
                items.append({"key": clean_key(k), "path": fs[0], "title": onboard.plain(e["fields"].get("title", "")),
                              "url": url.strip()})
        else:
            F.die("--src must be a folder or a .bib file: " + src)
    seen, out = set(), []
    for it in items:
        base, n = it["key"], 2
        while it["key"].lower() in seen:
            it["key"], n = "%s-%d" % (base, n), n + 1
        seen.add(it["key"].lower())
        out.append(it)
    return out


def spot_quotes(canon, keys, want=4):
    """One verbatim line-substring from each of the longest guides."""
    sizes = []
    for k in keys:
        with open(os.path.join(canon, k + ".txt"), encoding="utf-8", errors="replace") as fh:
            t = fh.read()
        sizes.append((len(t.split()), k, t))
    out = {}
    for _, k, t in sorted(sizes, reverse=True):
        lines = t.split("\n")
        for l in lines[len(lines) // 5:] + lines[:len(lines) // 5]:
            s = re.sub(r"\s{2,}.*$", "", l.strip())      # left column only, if two columns
            letters = sum(c.isalpha() or c == " " for c in s)
            prose = re.search(r"[a-z]{2,} [a-z]{2,} [a-z]{2,} [a-z]{2,}", s) and not re.search(r"\d\s*$", s) \
                and not re.match(r"(Figure|Fig\.|Table|Source)\b", s)
            if 60 <= len(s) and letters >= 0.9 * len(s) and "http" not in s and prose:
                q = s[:140].rsplit(" ", 1)[0] if len(s) > 140 else s
                if t.count(q) == 1:
                    out[k + ".txt"] = q
                    break
        if len(out) >= want:
            break
    return out


def write_manifest(canon, field, rec, failed):
    L = ["# canon-sources/_manifest.md -- the writing guides for %s, on disk" % field, "",
         "> Written by corpus-bootstrap's canon_ingest.py on %s. RULE: every non-secondary" % F.TODAY,
         "> rule in structure-canon.md quotes one of these files by <key>.txt:line, verbatim;",
         "> `py -3 scripts/check_canon_quotes.py` (in the -draft skill) checks every quote.",
         "> Ligatures and curly quotes are normalised so ASCII grep finds them.",
         "> The texts are copyrighted: keep this folder out of public repositories.", "",
         "| key | source | words | integrity |", "|---|---|---|---|"]
    on_disk = sorted(f[:-4] for f in os.listdir(canon) if f.endswith(".txt"))
    for k in on_disk:
        r = rec.get(k)
        if r:
            src = r.get("title") or os.path.basename(r["source"])
            integ = "complete" if not r.get("flags") else ", ".join(r["flags"])
            if r.get("pages"):
                integ += " (%d pp)" % r["pages"]
            L.append("| `%s` | %s | %s | %s |" % (k, src.replace("|", "/"), format(r["words"], ","), integ))
        else:
            with open(os.path.join(canon, k + ".txt"), encoding="utf-8", errors="replace") as fh:
                w = len(fh.read().split())
            L.append("| `%s` | (added by hand) | %s | not checked |" % (k, format(w, ",")))
    if failed:
        L += ["", "## Not converted", ""] + ["- `%s` -- %s" % (os.path.basename(p), why) for p, why in failed]
    urls = [(k, rec[k]["url"]) for k in on_disk if rec.get(k, {}).get("url")]
    if urls:
        L += ["", "## URLs", ""] + ["- `%s` -- %s" % kv for kv in urls]
    with open(os.path.join(canon, "_manifest.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    return on_disk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field")
    ap.add_argument("--src", action="append")
    ap.add_argument("--map")
    ap.add_argument("--canon-dir")
    ap.add_argument("--dest")
    ap.add_argument("--force", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.src and not a.map:
        F.die("give the guides with --src <folder or .bib> (or --map keys.csv)")
    fld = F.Field(a.field, a.dest).require()
    canon = os.path.abspath(a.canon_dir or os.path.join(fld.draft, "references", "canon-sources"))
    items = collect(a)
    if not items:
        F.die("no guides found (.pdf, .html, .htm, .txt or .md)")
    print("%d guide(s) -> %s%s" % (len(items), canon, "  [dry run]" if a.dry_run else ""))
    if a.dry_run:
        for it in items:
            print("  %-32s %s" % (it["key"], it["path"]))
        return 0
    os.makedirs(canon, exist_ok=True)
    pj = os.path.join(canon, "canon_sources.json")
    rec = json.load(open(pj, encoding="utf-8")) if os.path.isfile(pj) else {}
    conv = ingest.converter(ingest.load_config(fld.lit))
    failed = []
    for it in items:
        k, src = it["key"], it["path"]
        out = os.path.join(canon, k + ".txt")
        prev = rec.get(k, {})
        if os.path.exists(out) and k not in a.force and prev.get("txt_sha256") \
                and ingest.sha256(out) != prev["txt_sha256"]:
            print("  %-32s kept (edited by hand)" % k)
            continue
        try:
            text, pages, title, how = to_text(src, conv, out + ".tmp")
        except Exception as e:  # one bad file never stops the batch
            failed.append((src, "conversion failed: %s" % str(e)[:120]))
            print("  %-32s FAILED %s" % (k, str(e)[:80]))
            continue
        text = normalize(text)
        words = len(text.split())
        flags = []
        if pages >= 2 and words / float(pages) < SCAN_WPP:
            failed.append((src, "image-only scan (%d words on %d pages): OCR it first" % (words, pages)))
            print("  %-32s SKIPPED scan (%d words / %d pages)" % (k, words, pages))
            continue
        if words < 300:
            flags.append("short (%d words)" % words)
        if "�" in text:
            flags.append("%d damaged characters (U+FFFD)" % text.count("�"))
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        rec[k] = {"source": src, "source_sha256": ingest.sha256(src), "txt_sha256": ingest.sha256(out),
                  "converter": how, "pages": pages, "words": words, "flags": flags,
                  "title": it["title"] or title, "url": it["url"],
                  "ingested_at": datetime.datetime.now().isoformat(timespec="seconds")}
        print("  %-32s %-12s %7s words  %s" % (k, how, format(words, ","), " ".join(flags)))
    with open(pj, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, sort_keys=True)
    keys = write_manifest(canon, a.field, rec, failed)
    if not keys:
        F.die("no guide text was written")
    fld.set_scalar("canon_dir", canon.replace("\\", "/"))
    quotes = spot_quotes(canon, keys)

    def fill(reg):
        cs = reg.setdefault("canon_sources", {})
        cs.update(count=len(keys), location=canon.replace("\\", "/"), spot_quotes=quotes)
    fld.update_registry("draft", fill)
    words = sum(r["words"] for k, r in rec.items() if k in keys)
    print("\ncanon-sources: %d guide(s), %s words; _manifest.md written; canon_dir set in both"
          " field-configs; registry canon_sources: count %d, %d spot quotes"
          % (len(keys), format(words, ","), len(keys), len(quotes)))
    if failed:
        print("not converted: %d (listed in _manifest.md)" % len(failed))
    print("\nNEXT (step 3, a model pass -- ask the user first): Claude drafts structure-canon.md"
          " following %s,\n  then: py -3 %s"
          % (os.path.join(fld.draft, "prompts", "structure-canon.md"),
             os.path.join(fld.draft, "scripts", "check_canon_quotes.py")))
    print("  estimate: %s" % canon_estimate(words))
    return 0


# Drafting structure-canon.md, measured once (2026-10-14): 17 guides, 151,547
# words, 35 rules -> one agent, 101 tool calls, 14 min, 10.1 million tokens
# processed (97% prompt-cache reads, 0.28 million new input and output). The
# work is mostly per rule (searches and reads for each), so half the cost is
# taken as fixed and half as growing with the guides' length -- an assumption
# until a second run is measured.
CANON_REF_WORDS = 151547
CANON_REF_M = 10.1
CANON_REF_MIN = 14


def _canon_scale(words):
    return 0.5 + 0.5 * words / float(CANON_REF_WORDS)


def canon_tokens(words):
    """Millions of tokens the drafting pass processes, from the guides' total length."""
    return CANON_REF_M * _canon_scale(words)


def canon_estimate(words):
    return ("about %.0f million tokens processed (about 97%% prompt-cache reads), about %.0f min;"
            " scaled from one measured run" % (canon_tokens(words), CANON_REF_MIN * _canon_scale(words)))


if __name__ == "__main__":
    sys.exit(main())
