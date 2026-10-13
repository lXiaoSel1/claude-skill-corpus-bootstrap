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


def manuscript_tex():
    return cp.as_str(_DATA.get("manuscript_tex"))


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
