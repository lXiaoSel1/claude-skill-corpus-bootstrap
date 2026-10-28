#!/usr/bin/env python3
"""Citation-style shim for a stamped <field>-draft instance.

The parent's ownership test assumes Author (Year) citation culture. Numeric
fields (IEEE/Vancouver [12], or superscripts that pdftotext flattens into
"reform.12,13 However") can't detect third-party ownership from the marker
alone: a bracket or superscript says nothing about WHOSE claim the sentence
is. There the mechanical test is a marker-detector plus discourse markers,
and SKILL.md tells the drafter ownership is judgment-first.

citation_style: author-year | numeric | mixed. "mixed" (e.g. economics +
medicine corpora) unions both detectors.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "pipeline"))
import _jobs  # noqa: E402

_STYLE = _jobs.citation_style()

# Discourse markers of a third party's claim, matched in ANY case (1.6.0): the
# case-sensitive 1.5.0 form missed a sentence-initial "Consistent with" or
# "Following", and as whole words ("the following table" is no marker
# boundary problem: \b keeps "followings" out, judgment handles the rest).
_DISCOURSE = r"(?i:\bet al\.|\bfollowing\b|\bconsistent with\b|\bas in\b|\bbuilding on\b)"
# (Smith, 2019) (Smith and Jones 2019a) (Smith et al., 2019; Lee, 2020) and
# narrative Smith (2019) / Smith et al. (2019)
AUTHOR_YEAR = (r"\([^()]{0,120}?(?:1[89]|20)\d{2}[a-z]?\)"
               r"|[A-Z][A-Za-z'\-]+(?: et al\.)?\s\((?:1[89]|20)\d{2}[a-z]?")
# [12] [3, 4] [5-7] and flattened superscripts: "costs.12,13 " "costs12 "
NUMERIC = (r"\[\d{1,3}(?:[,–\-]\s*\d{1,3})*\]"
           r"|(?<=[a-z\)])[.,;]?\d{1,3}(?:[,–\-]\d{1,3})*(?=[\s.,;]|$)")

_PATTERNS = {
    "author-year": AUTHOR_YEAR,
    "numeric": NUMERIC,
    "mixed": AUTHOR_YEAR + "|" + NUMERIC,
}


def style():
    return _STYLE


def owner_re():
    return re.compile(_PATTERNS.get(_STYLE, AUTHOR_YEAR) + "|" + _DISCOURSE)


def citation_re():
    """Citation markers only (no discourse words) -- for counting/stripping."""
    return re.compile(_PATTERNS.get(_STYLE, AUTHOR_YEAR))
