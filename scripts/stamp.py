#!/usr/bin/env python3
"""Stamp a new field's skill instances from the templates.

Creates <dest>/<field>-lit/ and <dest>/<field>-draft/ (dest defaults to the
skills directory holding this factory), copies the templates, substitutes
{{FIELD}} / {{FIELD_KEYWORDS}} / {{CITATION_STYLE}} / {{CANON_DIR}} tokens (prompts included),
writes field-config.yaml into BOTH instances' references/, creates the working
directories every tier writes into, and initializes each registry with
built_tiers=[].

Refuses to overwrite an existing instance (delete it yourself first -- a
stamped instance accumulates measured state that a re-stamp would destroy).

RUN
    py -3 scripts/stamp.py <field-slug> [--citation-style author-year|numeric|mixed] [--dest <skills-dir>] [--keywords "..."]
    e.g.  py -3 scripts/stamp.py ecology --citation-style mixed --dest ~/.claude/skills
"""
import argparse
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TEMPLATES = os.path.join(SKILL, "templates")
CANON = os.path.join(SKILL, "references", "canon-sources")
TEXT_EXT = {".md", ".tmpl", ".yaml", ".json", ".py", ".txt"}
STYLES = ("author-year", "numeric", "mixed")


KEYWORDS = [""]   # set from --keywords in main(); module-level so copy_tree sees it


def stamp_text(text, field, style):
    return (text.replace("{{FIELD_KEYWORDS}}", KEYWORDS[0] or field)
                .replace("{{FIELD}}", field)
                .replace("{{CITATION_STYLE}}", style)
                .replace("{{CANON_DIR}}", CANON.replace("\\", "/")))


def copy_tree(src, dst, field, style):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, src)
        out_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(out_dir, exist_ok=True)
        for f in files:
            src_f = os.path.join(root, f)
            out_name = f[:-5] if f.endswith(".tmpl") else f
            dst_f = os.path.join(out_dir, out_name)
            ext = os.path.splitext(f)[1]
            if ext in TEXT_EXT:
                with open(src_f, encoding="utf-8") as fh:
                    text = fh.read()
                with open(dst_f, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(stamp_text(text, field, style))
            else:
                shutil.copy2(src_f, dst_f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field", help="kebab-case field slug, e.g. ecology")
    ap.add_argument("--citation-style", choices=STYLES, default="author-year")
    ap.add_argument("--dest", default=os.path.dirname(SKILL),
                    help="skills directory (default: this skill's parent)")
    ap.add_argument("--keywords", default="",
                    help="topic words for the SKILL.md descriptions, so this pair"
                         " does not collide with sibling instances' triggers"
                         " (e.g. \"population ecology, habitat loss\")")
    args = ap.parse_args()
    KEYWORDS[0] = args.keywords.strip()
    field = args.field.strip().lower()
    if not field.replace("-", "").isalnum():
        sys.exit("field slug must be kebab-case alphanumeric")
    dest = os.path.abspath(args.dest)
    if not os.path.isdir(dest):
        sys.exit("--dest is not an existing directory: " + dest)

    lit = os.path.join(dest, field + "-lit")
    draft = os.path.join(dest, field + "-draft")
    for d in (lit, draft):
        if os.path.exists(d):
            sys.exit("refusing to overwrite existing instance: " + d
                     + "\n  (a stamped instance holds measured state; delete"
                       " it yourself if you mean it)")

    copy_tree(os.path.join(TEMPLATES, "lit"), lit, field, args.citation_style)
    copy_tree(os.path.join(TEMPLATES, "draft"), draft, field,
              args.citation_style)

    # field-config.yaml into both instances (same content; edits at tier
    # gates go to BOTH, and each instance's check_drift asserts the copies
    # agree on every key)
    with open(os.path.join(TEMPLATES, "field-config.yaml"),
              encoding="utf-8") as fh:
        cfg = stamp_text(fh.read(), field, args.citation_style)
    for d in (lit, draft):
        os.makedirs(os.path.join(d, "references"), exist_ok=True)
        with open(os.path.join(d, "references", "field-config.yaml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(cfg)

    # working dirs every tier writes into
    for sub in (("references", "corpus"), ("drop",),
                ("references", "_exemplar_shards")):
        os.makedirs(os.path.join(lit, *sub), exist_ok=True)
    for sub in (("references", "records", "_shards"),
                ("references", "sections"), ("references", "slices")):
        os.makedirs(os.path.join(draft, *sub), exist_ok=True)

    # prompts travel with the draft instance (Tier 2-4 dispatch reads them);
    # tokens substituted like every other text file
    copy_tree(os.path.join(TEMPLATES, "prompts"),
              os.path.join(draft, "prompts"), field, args.citation_style)

    print("stamped:")
    print("  " + lit)
    print("  " + draft)
    print("next (Tier 0): convert PDFs, either from drop/ or straight from a"
          " library folder:")
    print("  py -3 %s %s [--src <pdf-folder> --recursive --map <keys.csv>]"
          % (os.path.join(SKILL, "scripts", "ingest.py"), lit))
    print("  py -3 %s" % os.path.join(lit, "scripts", "build_corpus_meta.py"))


if __name__ == "__main__":
    main()
