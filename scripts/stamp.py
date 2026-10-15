#!/usr/bin/env python3
"""Stamp a new field's skill instances from the templates.

Creates <dest>/<field>-lit/, <dest>/<field>-draft/ and <dest>/<field>-polish/
(dest defaults to the skills directory holding this factory), copies the
templates, substitutes {{FIELD}} / {{FIELD_KEYWORDS}} / {{CITATION_STYLE}} /
{{CANON_DIR}} tokens (prompts included), writes field-config.yaml into the
lit and draft instances' references/, creates the working directories every
tier writes into, and initializes each registry with built_tiers=[]. The
polish instance gets references/instance.json naming its two siblings.
canon_dir (Tier 4's writing guides) is the field's own, empty
<draft>/references/canon-sources/; canon_ingest.py fills it.

--add polish stamps only <field>-polish, next to an existing field (fields
stamped before 1.2.0). --lit-dir / --draft-dir point it at siblings that live
somewhere else.

Refuses to overwrite an existing instance (delete it yourself first -- a
stamped instance accumulates measured state that a re-stamp would destroy).

RUN
    py -3 scripts/stamp.py <field-slug> [--citation-style author-year|numeric|mixed] [--dest <skills-dir>] [--keywords "..."]
    py -3 scripts/stamp.py <field-slug> --add polish [--dest <skills-dir>] [--lit-dir D --draft-dir D]
    e.g.  py -3 scripts/stamp.py ecology --citation-style mixed --dest ~/.claude/skills
"""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _factory as F  # noqa: E402  (paths, slug rule, ~ expansion, launcher, styles)
TEXT_EXT = {".md", ".tmpl", ".yaml", ".json", ".py", ".txt"}
DESC_MAX = 1024   # Claude Code's limit on a skill description


class Tokens(object):
    """The {{...}} substitutions for one field."""

    def __init__(self, field, style, keywords, canon):
        self.field, self.style, self.keywords, self.canon = field, style, keywords, canon

    def apply(self, text):
        return (text.replace("{{FIELD_KEYWORDS}}", self.keywords or self.field)
                    .replace("{{FIELD}}", self.field)
                    .replace("{{CITATION_STYLE}}", self.style)
                    .replace("{{CANON_DIR}}", self.canon.replace("\\", "/")))


def check_descriptions(tok, which):
    """Every stamped description must stay a valid double-quoted YAML string
    under DESC_MAX characters; --keywords is pasted into it unescaped."""
    if re.search(r'["\\\r\n]', tok.keywords):
        sys.exit('--keywords may not contain double quotes, backslashes or line breaks')
    for w in which:
        with open(os.path.join(F.TEMPLATES, w, "SKILL.md.tmpl"), encoding="utf-8") as fh:
            m = re.search(r'^description: "(.*)"$', fh.read(), re.M)
        n = len(tok.apply(m.group(1)).replace('\\"', '"').replace("\\\\", "\\"))
        if n > DESC_MAX:
            sys.exit("the %s-%s description would be %d characters (limit %d): shorten --keywords"
                     % (tok.field, w, n, DESC_MAX))


def copy_tree(src, dst, tok):
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
                    fh.write(tok.apply(text))
            else:
                shutil.copy2(src_f, dst_f)


def stamp_polish(polish, field, args, lit, draft, tok):
    """<field>-polish: the templates, plus references/instance.json naming the
    siblings -- relative when they sit next to it, absolute when given."""
    copy_tree(os.path.join(F.TEMPLATES, "polish"), polish, tok)
    inst = {"field": field,
            "lit_dir": os.path.abspath(args.lit_dir) if args.lit_dir
            else os.path.relpath(lit, polish).replace("\\", "/"),
            "draft_dir": os.path.abspath(args.draft_dir) if args.draft_dir
            else os.path.relpath(draft, polish).replace("\\", "/")}
    os.makedirs(os.path.join(polish, "references"), exist_ok=True)
    with open(os.path.join(polish, "references", "instance.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(inst, fh, indent=1)
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field", help="kebab-case field slug, e.g. ecology")
    ap.add_argument("--citation-style", choices=F.STYLES, default="author-year")
    ap.add_argument("--dest", default=F.DEFAULT_DEST,
                    help="skills directory (default: this skill's parent)")
    ap.add_argument("--keywords", default="",
                    help="topic words for the SKILL.md descriptions, so this pair"
                         " does not collide with sibling instances' triggers"
                         " (e.g. \"population ecology, habitat loss\")")
    ap.add_argument("--add", choices=["polish"],
                    help="stamp only this instance next to an existing field")
    ap.add_argument("--lit-dir", help="the <field>-lit the polish instance uses"
                    " (default: <dest>/<field>-lit)")
    ap.add_argument("--draft-dir", help="the <field>-draft the polish instance uses"
                    " (default: <dest>/<field>-draft)")
    args = ap.parse_args()
    field = F.norm_field(args.field)
    if not F.SLUG.match(field):
        sys.exit("field slug must be lowercase ASCII letters and digits, with single hyphens"
                 " between (e.g. health-econ): %r" % args.field)
    dest = F.user_path(args.dest)
    if not os.path.isdir(dest):
        sys.exit("--dest is not an existing directory: " + dest)
    args.lit_dir, args.draft_dir = F.user_path(args.lit_dir), F.user_path(args.draft_dir)
    lit = os.path.join(dest, field + "-lit")
    draft = os.path.join(dest, field + "-draft")
    polish = os.path.join(dest, field + "-polish")
    # Tier 4 writing guides: the field's own folder (canon_ingest.py fills it)
    canon = os.path.join(draft, "references", "canon-sources")
    tok = Tokens(field, args.citation_style, args.keywords.strip(), canon)
    check_descriptions(tok, ["polish"] if args.add == "polish" else ["lit", "draft", "polish"])
    if args.add == "polish":
        lit_dir = os.path.abspath(args.lit_dir) if args.lit_dir else lit
        if not os.path.isfile(os.path.join(lit_dir, "references", "registry.json")):
            sys.exit("--add polish: no <field>-lit at %s (stamp the field first, or"
                     " pass --lit-dir)" % lit_dir)
        if os.path.exists(polish):
            sys.exit("refusing to overwrite existing instance: " + polish)
        stamp_polish(polish, field, args, lit, draft, tok)
        print("stamped:\n  " + polish)
        return
    for d in (lit, draft, polish):
        if os.path.exists(d):
            sys.exit("refusing to overwrite existing instance: " + d
                     + "\n  (a stamped instance holds measured state; delete"
                       " it yourself if you mean it)")

    copy_tree(os.path.join(F.TEMPLATES, "lit"), lit, tok)
    copy_tree(os.path.join(F.TEMPLATES, "draft"), draft, tok)

    # field-config.yaml into both instances (same content; edits at tier
    # gates go to BOTH, and each instance's check_drift asserts the copies
    # agree on every key)
    with open(os.path.join(F.TEMPLATES, "field-config.yaml"),
              encoding="utf-8") as fh:
        cfg = tok.apply(fh.read())
    for d in (lit, draft):
        os.makedirs(os.path.join(d, "references"), exist_ok=True)
        with open(os.path.join(d, "references", "field-config.yaml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(cfg)

    # working dirs every tier writes into
    for sub in (("references", "corpus"), ("drop",),
                ("references", "_exemplar_shards")):
        os.makedirs(os.path.join(lit, *sub), exist_ok=True)
    for sub in (("references", "records", "_shards"), ("references", "sections"),
                ("references", "slices"), ("references", "canon-sources")):
        os.makedirs(os.path.join(draft, *sub), exist_ok=True)

    # prompts travel with the draft instance (Tier 2-4 dispatch reads them);
    # tokens substituted like every other text file
    copy_tree(os.path.join(F.TEMPLATES, "prompts"), os.path.join(draft, "prompts"), tok)
    stamp_polish(polish, field, args, lit, draft, tok)

    print("stamped:")
    print("  " + lit)
    print("  " + draft)
    print("  " + polish)
    print("next (Tier 0): convert PDFs, either from drop/ or straight from a"
          " library folder:")
    print("  %s %s %s [--src <pdf-folder> --recursive | --map <keys.csv>]"
          % (F.PY, os.path.join(F.HERE, "ingest.py"), lit))
    print("  %s %s" % (F.PY, os.path.join(lit, "scripts", "build_corpus_meta.py")))
    print("  %s %s %s%s   # Tier 0 acceptance" % (F.PY, os.path.join(F.HERE, "tier0_accept.py"),
                                                   field, F.dest_arg(dest)))


if __name__ == "__main__":
    main()
