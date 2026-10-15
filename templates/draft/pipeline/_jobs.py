#!/usr/bin/env python3
"""Taxonomy and config shim for a stamped <field>-draft instance's pipeline.

The parent build hardcoded the ten-job economics taxonomy in THREE scripts
(build_map, build_names, stage_b_slice) with no shared constant -- a documented
desync hazard.  A stamped instance has ONE source: the jobs block that Tier
2's approved taxonomy-induction wrote into references/field-config.yaml.

Parsing goes through _cfgparse (identical copy of the lit instance's), so
quoted regexes and inline comments are handled -- the 2026-08 line parser kept
quotes inside values and silently killed every quoted abstract_end_marker.

Also resolves the corpus location: the sibling <field>-lit instance's
references/corpus (declared as lit_instance in the config), replacing the
parent's hardcoded ../mimic-lit hop.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, ".."))
CONFIG = os.path.join(SKILL, "references", "field-config.yaml")
sys.path.insert(0, HERE)
import _cfgparse as cp  # noqa: E402

_DEFAULTS = {"jobs": [], "positional_jobs": [], "abstract_end_markers": [],
             "abstract_start_markers": [], "lit_instance": "", "headwords": "",
             "citation_style": "author-year"}


def _load():
    """Config as a dict with defaults filled (kept for callers that import
    _load directly: _fieldstyle, build_evidence_map)."""
    data = dict(_DEFAULTS)
    for k, v in cp.parse(CONFIG).items():
        if v is not None:
            data[k] = v
    return data


_DATA = _load()


def jobs():
    """The approved taxonomy. EMPTY before Tier 2 approval -- pipeline scripts
    must refuse to run on an empty taxonomy rather than assume economics'."""
    return cp.as_list(_DATA.get("jobs"))


def require_jobs():
    j = jobs()
    if not j:
        raise SystemExit(
            "no taxonomy in field-config.yaml -- Tier 2 step 1 "
            "(taxonomy induction + user approval) has not run.  The parent's "
            "nine chapters are economics' answer, not this field's.")
    return j


def positional_jobs():
    """Jobs sliced by position, not heading, in document order. The FIRST is
    the front block (abstract-like, ends at abstract_end_markers); later ones
    start at their positional_anchors_<job> regexes (or right after the
    previous positional job) and end at the first heading-sliced job."""
    return cp.as_list(_DATA.get("positional_jobs"))


def front_job():
    """Name of the abstract-like positional job (None if not declared)."""
    p = positional_jobs()
    return p[0] if p else None


def intro_job():
    """The job whose opening paragraphs the structure layer treats as 'the
    introduction'. Config key intro_job; else the first non-front job."""
    v = cp.as_str(_DATA.get("intro_job"))
    if v:
        return v
    fj = front_job()
    return next((j for j in jobs() if j != fj), None)


def positional_anchors(job):
    """Regex alternatives that mark where a positional job starts inside the
    running text (config key positional_anchors_<job>; the mathematics instance's
    main_results_anchors generalized). [] = start right after the previous
    positional job."""
    return cp.as_list(_DATA.get("positional_anchors_" + job))


def abstract_end_markers():
    """Regex alternatives marking the end of the front positional block
    (economics: JEL/keyword lines; medicine: Keywords, Trial registration,
    Key messages -- NOT the structured labels Background/Methods/Results,
    which occur inside the abstract)."""
    return cp.as_list(_DATA.get("abstract_end_markers"))


def abstract_start_markers():
    """Labels that may open an unlabeled-'Abstract' front block (Summary,
    Objective(s), Importance, Background, Context)."""
    return cp.as_list(_DATA.get("abstract_start_markers"))


def citation_style():
    s = cp.as_str(_DATA.get("citation_style"), "author-year")
    return s if s in ("author-year", "numeric", "mixed") else "author-year"


def corpus_dir():
    lit = cp.as_str(_DATA.get("lit_instance"))
    if lit:
        return os.path.normpath(os.path.join(SKILL, "..", lit,
                                             "references", "corpus"))
    # fallback: instance-local corpus
    return os.path.join(SKILL, "references", "corpus")


def lit_dir():
    lit = cp.as_str(_DATA.get("lit_instance"))
    return os.path.normpath(os.path.join(SKILL, "..", lit)) if lit else ""


def headwords_re():
    """Optional field-specific heading-vocabulary regex fragment (a1's recall
    booster).  Empty string = rely on title-case detection alone; the parent's
    econ list is quantitative-social-science-biased and is NOT the default."""
    return cp.as_str(_DATA.get("headwords"))


def project_root():
    """The project folder when this skill sits in <project>/.claude/skills/,
    else None (a user-level ~/.claude/skills install has no project)."""
    skills = os.path.dirname(SKILL)
    dot = os.path.dirname(skills)
    if os.path.basename(skills) == "skills" and os.path.basename(dot) == ".claude":
        return os.path.dirname(dot)
    return None


def resolve_path(p):
    """A path from field-config.yaml: absolute as written; relative only to the
    project root, and an error when there is no project to be relative to."""
    if not p:
        return ""
    p = os.path.expanduser(p)
    if os.path.isabs(p):
        return os.path.normpath(p)
    root = project_root()
    if root is None:
        sys.exit("relative path %r in field-config.yaml: this skill is not inside a project's"
                 " .claude/skills, so write the absolute path" % p)
    return os.path.normpath(os.path.join(root, p))


def manuscript_paths():
    """(manuscript_tex, manuscript_tables), resolved by resolve_path; empty
    strings before manuscript onboarding."""
    return (resolve_path(cp.as_str(_DATA.get("manuscript_tex"))),
            resolve_path(cp.as_str(_DATA.get("manuscript_tables"))))


def canon_dir():
    """Where this field's writing guides live (Tier 4): config key canon_dir,
    else this skill's own references/canon-sources."""
    v = cp.as_str(_DATA.get("canon_dir"))
    if v:
        return v
    return os.path.join(SKILL, "references", "canon-sources")
