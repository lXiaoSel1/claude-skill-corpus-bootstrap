#!/usr/bin/env python3
"""Field configuration shim for a stamped instance.

Loads references/field-config.yaml (written by corpus-bootstrap's stamp.py)
through _cfgparse (quotes and inline comments handled; see its docstring) and
exposes the values the parent scripts hardcoded for economics/finance.

Every accessor falls back to a sane default when a key is absent -- an
instance at Tier 0-1 has no jobs yet (taxonomy arrives at Tier 2), and that is
normal, not an error.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CONFIG = os.path.join(SKILL, "references", "field-config.yaml")
sys.path.insert(0, HERE)
import _cfgparse as cp  # noqa: E402

_DATA = cp.parse(CONFIG)

CITATION_STYLES = ("author-year", "numeric", "mixed")


def raw():
    return dict(_DATA)


def field():
    return cp.as_str(_DATA.get("field"), "unnamed-field")


def citation_style():
    s = cp.as_str(_DATA.get("citation_style"), "author-year")
    return s if s in CITATION_STYLES else "author-year"


def terminology_only():
    return set(cp.as_list(_DATA.get("terminology_only")))


def excluded():
    """Keys kept out of BOTH style and terminology samples (e.g. abstract-only
    or unreadable scans the user chose not to OCR)."""
    return set(cp.as_list(_DATA.get("excluded")))


def reviews():
    """Review and survey articles (1.6.0): searched for terminology, kept out of
    the style sample -- a review essay's paragraphs are not the field's
    research-paper paragraphs (the parent's literature chapter took 30% of
    its paragraphs from one)."""
    return set(cp.as_list(_DATA.get("reviews")))


def jobs():
    """The field's chapter taxonomy. Empty until Tier 2's approved induction
    writes it -- callers must treat [] as 'coarse mode', never as an error."""
    return cp.as_list(_DATA.get("jobs"))


def para_min_chars():
    """The ONE paragraph-length threshold every measurement uses (textseg,
    cohesion norms, register). Calibrated at Tier 1; default 150 suits
    pdftotext line-per-paragraph-ish output."""
    try:
        return int(cp.as_str(_DATA.get("para_min_chars"), "150"))
    except ValueError:
        return 150


def project_root():
    """The project folder when this skill sits in <project>/.claude/skills/,
    else None (a user-level ~/.claude/skills install has no project)."""
    skills = os.path.dirname(SKILL)
    dot = os.path.dirname(skills)
    if os.path.basename(skills) == "skills" and os.path.basename(dot) == ".claude":
        return os.path.dirname(dot)
    return None


def manuscript_tex():
    """manuscript_tex: absolute as written; relative only to the project root,
    and an error when there is no project (same rule as the -draft skill)."""
    p = os.path.expanduser(cp.as_str(_DATA.get("manuscript_tex")))
    if not p or os.path.isabs(p):
        return os.path.normpath(p) if p else ""
    root = project_root()
    if root is None:
        sys.exit("relative manuscript_tex %r in field-config.yaml: this skill is not inside a"
                 " project's .claude/skills, so write the absolute path" % p)
    return os.path.normpath(os.path.join(root, p))


def pdftotext_path():
    """Pinned converter (Tier 0 reproducibility: PowerShell and Git Bash
    resolve different pdftotext builds on Windows)."""
    return cp.as_str(_DATA.get("pdftotext"))


def draft_slices_dir():
    """The sibling draft instance's slices dir, for fine cohesion cells.
    Empty string when no draft instance exists yet (Tier < 2)."""
    name = cp.as_str(_DATA.get("draft_instance"))
    if not name:
        return ""
    return os.path.normpath(os.path.join(SKILL, "..", name,
                                         "references", "slices"))
