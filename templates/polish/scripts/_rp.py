#!/usr/bin/env python3
"""Shared helpers for the {{FIELD}}-polish scripts.

Every script starts with `ctx = Ctx(sys.argv)`. Ctx finds, with no
configuration file required:
  * the sibling skills ({{FIELD}}-lit, {{FIELD}}-draft) -- from
    references/instance.json (written by stamp.py), else next to this skill;
    `--lit-dir` / `--draft-dir` override;
  * the manuscript -- `--manuscript <main.tex>`, else the lit field-config's
    `manuscript_tex` (written at onboarding);
  * optional settings -- `--config <file>`, else <manuscript dir>/.polish/
    polish.yaml, else <manuscript dir>/polish.yaml; anything absent takes the
    defaults below (the values the original workflow used).

Conventions every script shares:
  * a section's HEADER is its leading blank lines, full-line comments and a
    bare \\label{} line; it is skipped (the original scripts skipped line 1
    unconditionally, which missed prose put on line 1);
  * snapshots live in <manuscript dir>/.polish/snapshots/<name>/<key>.tex;
  * a cited paper's text comes from the PDF in .polish/library-index.json,
    else from a reading note's PDF field (notes_dir), else from the lit
    corpus (corpus keys are the citation keys after onboarding).
"""
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
FIELD = "{{FIELD}}"
sys.path.insert(0, HERE)
import manuscript as _msmod  # noqa: E402

DEFAULTS = {
    "split_level": "section",
    "max_sentences": 9,
    "uniform_run": 3,
    "max_words": "auto",
    "min_words": 3,
    "sweep_controls": ["the authors argue", "against the backdrop",
                       "must first be understood"],
    "sweep_common_df": 3,
    "sweep_very_common_df": 15,
    "sweep_min_freq": 2,
    "opener_max_lead_words": 4,
    "cohesion_section": "",
    "slice_chapters": [],
    "notes_dir": "",
    "notes_pdf_field": "pdf",
    "library_index": ".polish/library-index.json",
    "snapshot_dir": ".polish/snapshots",
    "compile_engine": "auto",
    "bib_engine": "auto",
    "expected_cited_keys": "",
    "expected_page_comments": "",
    "expected_bibitems": "",
    "page_comment_regex": r"(?<!\\)%\s*[A-Za-z][\w\-:]*\s+p\.\s?\d",
}
INT_KEYS = {"max_sentences", "uniform_run", "min_words",
            "sweep_common_df", "sweep_very_common_df", "sweep_min_freq",
            "opener_max_lead_words"}

COMMENT_RE = re.compile(r"(?<!\\)%.*$")
CITE_KEYS_RE = _msmod.CITE_KEYS_RE     # natbib and biblatex commands (manuscript.py)
CITE_ANY_RE = _msmod.CITE_ANY_RE
_LABEL_ONLY = re.compile(r"^\s*\\label\{[^}]*\}\s*$")


def die(msg, code=2):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def _pop(argv, name, default=None, flag=False):
    if name not in argv:
        return default
    i = argv.index(name)
    if flag:
        del argv[i]
        return True
    if i + 1 >= len(argv):
        die("%s needs a value" % name)
    v = argv[i + 1]
    del argv[i:i + 2]
    return v


def _abs(p, base):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def rel(p, base):
    """Path for display: relative to base when on the same drive, else absolute."""
    try:
        r = os.path.relpath(p, base)
    except ValueError:                       # Windows: another drive
        return p
    return p if r.startswith("..") else r


class Ctx(object):
    def __init__(self, argv):
        argv = list(argv[1:])
        self.manuscript_arg = _pop(argv, "--manuscript")
        lit_arg = _pop(argv, "--lit-dir")
        draft_arg = _pop(argv, "--draft-dir")
        self.config_arg = _pop(argv, "--config")
        self.args = argv
        inst = {}
        ij = os.path.join(SKILL, "references", "instance.json")
        if os.path.isfile(ij):
            with open(ij, encoding="utf-8") as fh:
                inst = json.load(fh)
        self.lit = os.path.abspath(lit_arg) if lit_arg else _abs(
            inst.get("lit_dir") or os.path.join("..", FIELD + "-lit"), SKILL)
        self.draft = os.path.abspath(draft_arg) if draft_arg else _abs(
            inst.get("draft_dir") or os.path.join("..", FIELD + "-draft"), SKILL)
        self._ms = None
        self._opts = None
        self._lit_cfg = None

    # ---- sibling instances -------------------------------------------------
    def lit_scripts(self):
        return os.path.join(self.lit, "scripts")

    def cfgparse(self):
        p = self.lit_scripts()
        if not os.path.isfile(os.path.join(p, "_cfgparse.py")):
            die("no lit skill at %s (pass --lit-dir)" % self.lit)
        if p not in sys.path:
            sys.path.insert(0, p)
        import _cfgparse
        return _cfgparse

    def lit_config(self):
        if self._lit_cfg is None:
            cp = self.cfgparse()
            path = os.path.join(self.lit, "references", "field-config.yaml")
            self._lit_cfg = cp.parse(path) if os.path.isfile(path) else {}
        return self._lit_cfg

    def lit_modules(self):
        """(attest, textseg) of the lit sibling. One lit instance per process:
        the module names are global."""
        p = self.lit_scripts()
        if p not in sys.path:
            sys.path.insert(0, p)
        try:
            import attest
            import textseg
        except SystemExit:
            die("the lit skill has no corpus manifest yet -- build Tier 0 first")
        return attest, textseg

    def split_sentences(self):
        """The lit sibling's abbreviation-aware splitter (no corpus needed);
        a plain one when the lit skill is not there."""
        p = self.lit_scripts()
        if p not in sys.path:
            sys.path.insert(0, p)
        try:
            import textseg
            return textseg.split_sentences
        except ImportError:
            return lambda t: re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", t)

    def built_tiers(self, which="lit"):
        d = self.lit if which == "lit" else self.draft
        try:
            with open(os.path.join(d, "references", "registry.json"), encoding="utf-8") as fh:
                return sorted(json.load(fh).get("built_tiers", []))
        except (OSError, ValueError):
            return []

    def run_lit(self, script, args, cwd=None):
        """Run a lit script; returns (returncode, stdout, stderr)."""
        r = subprocess.run([sys.executable, "-B", os.path.join(self.lit_scripts(), script)]
                           + list(args), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=cwd or self.lit)
        return r.returncode, r.stdout, r.stderr

    # ---- manuscript and options --------------------------------------------
    def manuscript_path(self):
        if self.manuscript_arg:
            return os.path.abspath(self.manuscript_arg)
        cp = self.cfgparse()
        v = cp.as_str(self.lit_config().get("manuscript_tex"))
        if not v:
            die("no manuscript: pass --manuscript <main.tex>, or run the onboarding\n"
                "(/corpus-bootstrap polish) which records it in the field-config.")
        # same rule as the -lit and -draft skills: absolute as written; relative
        # only to the project when this skill sits in <project>/.claude/skills
        v = os.path.expanduser(v)
        if not os.path.isabs(v):
            skills = os.path.dirname(SKILL)
            if not (os.path.basename(skills) == "skills"
                    and os.path.basename(os.path.dirname(skills)) == ".claude"):
                die("manuscript_tex %r in the field-config is relative and this skill is not"
                    " inside a project's .claude/skills: write the absolute path" % v)
            v = _abs(v, os.path.dirname(os.path.dirname(skills)))
        if os.path.isfile(v):
            return v
        die("manuscript_tex in the field-config does not exist: " + v)

    @property
    def opts(self):
        if self._opts is None:
            o = dict(DEFAULTS)
            msp = self.manuscript_path()
            d = os.path.dirname(msp)
            cands = [self.config_arg] if self.config_arg else [
                os.path.join(d, ".polish", "polish.yaml"), os.path.join(d, "polish.yaml")]
            self.config_file = next((c for c in cands if c and os.path.isfile(c)), None)
            if self.config_arg and not self.config_file:
                die("config not found: " + self.config_arg)
            if self.config_file:
                cp = self.cfgparse()
                for k, v in cp.parse(self.config_file).items():
                    if k not in DEFAULTS:
                        die("%s: unknown key %r (known: %s)"
                            % (self.config_file, k, ", ".join(sorted(DEFAULTS))))
                    o[k] = v
            for k in INT_KEYS:
                o[k] = int(o[k])
            if str(o["max_words"]).strip().lower() != "auto":
                o["max_words"] = int(o["max_words"])
            for k in ("sweep_controls", "slice_chapters"):
                if isinstance(o[k], str):
                    o[k] = [o[k]] if o[k] else []
            self._opts = o
        return self._opts

    @property
    def ms(self):
        if self._ms is None:
            path = self.manuscript_path()
            self._ms = _msmod.Manuscript(path, self.opts["split_level"])
        return self._ms

    def sections(self, names=None):
        """Sections named in `names` (keys, file names or paths); all when empty."""
        if not names:
            return list(self.ms.sections)
        try:
            return [self.ms.section(n) for n in names]
        except KeyError as e:
            die(str(e).strip('"'))

    def intro_job(self):
        cp = self.cfgparse()
        v = self.opts["cohesion_section"] or cp.as_str(self.lit_config().get("intro_job"))
        if v:
            return v
        jobs = cp.as_list(self.lit_config().get("jobs"))
        return "introduction" if not jobs or "introduction" in jobs else jobs[0]

    # ---- snapshots ---------------------------------------------------------
    def snapshot_root(self):
        return _abs(self.opts["snapshot_dir"], self.ms.dir)

    def snapshot_file(self, name, key):
        return os.path.join(self.snapshot_root(), name, key + ".tex")

    def snapshot_lines(self, name, section):
        """[(line no, text)] of a section as saved in snapshot `name`, numbered
        like the live section (so line numbers in reports line up)."""
        p = self.snapshot_file(name, section.key)
        if not os.path.isfile(p):
            have = sorted(os.listdir(self.snapshot_root())) if os.path.isdir(self.snapshot_root()) else []
            die("no snapshot %r of section %r (%s)\n  take one first: snapshot.py %s %s\n"
                "  snapshots present: %s" % (name, section.key, p, name, section.key,
                                             ", ".join(have) or "none"))
        return [(section.first + i, t) for i, t in enumerate(_read(p).splitlines())]

    # ---- cited-paper text --------------------------------------------------
    def library_index(self):
        p = _abs(self.opts["library_index"], self.ms.dir)
        if not os.path.isfile(p):
            return {}
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("keys", data)

    def note_path(self, key):
        nd = self.opts["notes_dir"] or self.library_index_meta().get("notes_dir", "")
        if not nd:
            return None
        nd = _abs(nd, self.ms.dir)
        for root, _, files in os.walk(nd):
            if key + ".md" in files:
                return os.path.join(root, key + ".md")
        return None

    def library_index_meta(self):
        p = _abs(self.opts["library_index"], self.ms.dir)
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh).get("meta", {})
        except (OSError, ValueError):
            return {}

    def pdf_for(self, key):
        """(pdf path, how it was found) or (None, reason)."""
        rec = self.library_index().get(key)
        if rec and rec.get("pdf") and os.path.isfile(rec["pdf"]):
            return rec["pdf"], "library-index (%s)" % rec.get("method", "?")
        note = self.note_path(key)
        if note:
            field = self.opts["notes_pdf_field"]
            # the configured field, or the names onboarding also accepts
            m = re.search(r"^\s*(?:%s|pdf|PDF|file|对应PDF)\s*[:：]\s*(.+)$" % re.escape(field),
                          _read(note), re.M)
            if m:
                p = m.group(1).strip().strip("'\"")
                p = _abs(p, os.path.dirname(note))
                if os.path.isfile(p):
                    return p, "note"
                return None, "note's PDF path does not exist: " + p
            return None, "note has no %s: field" % field
        return None, "no PDF in the library index and no reading note"

    def source_text(self, key):
        """(text, source label) of a cited paper, or ("", reason)."""
        pdf, how = self.pdf_for(key)
        if pdf:
            return pdf_text(pdf), "pdf via " + how
        ck = (self.library_index().get(key) or {}).get("corpus_key") or key
        corp = os.path.join(self.lit, "references", "corpus", ck + ".txt")
        if os.path.isfile(corp):
            return normalize(_read(corp)), "lit corpus txt (%s)" % how
        return "", how

    def page_label(self, key, offset):
        """"p.N" for an offset in source_text(key) when that text is the PDF's,
        else "" (the lit corpus copy has no pages)."""
        pdf, _ = self.pdf_for(key)
        return "p.%d" % pdf_page(pdf, offset) if pdf else ""


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


read = _read
_LIG = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl"}
_PDF_CACHE = {}


def normalize(text):
    """Ligatures restored, words broken across a line end re-joined, spaces collapsed."""
    for k, v in _LIG.items():
        text = text.replace(k, v)
    text = re.sub(r"(\w)-[ \t]*\r?\n[ \t]*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text)


def _pdf(path):
    if path not in _PDF_CACHE:
        try:
            import fitz
        except ImportError:
            die("PyMuPDF is needed to read PDFs: py -3 -m pip install pymupdf")
        with fitz.open(path) as d:
            pages = [p.get_text() for p in d]
        _PDF_CACHE[path] = {"pages": pages, "text": normalize("\n".join(pages)), "starts": None}
    return _PDF_CACHE[path]


def pdf_text(path):
    return _pdf(path)["text"]


def pdf_page(path, offset):
    """The page (1 = the file's first page, not the journal's printed number)
    holding `offset` of pdf_text(path). A word hyphenated across a page break
    can put the boundary a character or two off."""
    import bisect
    c = _pdf(path)
    if c["starts"] is None:
        c["starts"] = [0] + [len(normalize("\n".join(c["pages"][:k]) + "\n"))
                             for k in range(1, len(c["pages"]))]
    return bisect.bisect_right(c["starts"], offset)


def term_pattern(term):
    """Case-insensitive; words may be joined by space, hyphen or nothing (a word
    split at a line end is re-joined by normalize); the last word may inflect."""
    parts = [re.escape(w) for w in re.split(r"[\s\-]+", term.strip()) if w]
    return re.compile(r"\b" + r"[\s\-]*".join(parts) + r"\w*", re.I)


# ---- section text ----------------------------------------------------------
def is_header(text):
    s = text.strip()
    return not s or s.startswith("%") or bool(_LABEL_ONLY.match(text))


def body_lines(lines):
    """Drop the header (leading blank lines, full-line comments, bare \\label)."""
    i = 0
    while i < len(lines) and is_header(lines[i][1]):
        i += 1
    return lines[i:]


def section_body(section):
    return body_lines(section.lines())


def text_body(text, first=1):
    return body_lines([(first + i, t) for i, t in enumerate(text.splitlines())])


def paragraphs(lines, comment_breaks=False):
    """[(first line no, [raw lines])], split at blank lines (and at full-line
    comments when comment_breaks)."""
    out, buf, start = [], [], None
    for ln, t in list(lines) + [(None, "")]:
        brk = not t.strip() or (comment_breaks and t.lstrip().startswith("%"))
        if brk:
            if buf:
                out.append((start, buf))
            buf, start = [], None
            continue
        if start is None:
            start = ln
        buf.append(t)
    return out


def cite_keys(text):
    keys = set()
    for m in CITE_KEYS_RE.finditer(text):
        keys |= {k.strip() for k in m.group(1).split(",") if k.strip()}
    return keys


HEADING_LINE = re.compile(r"\s*\\(?:part|chapter|(?:sub)*section)\*?[\[{]")


# ---- prose tokens (the register sweep's measure; para_lengths shares it) ----
_TOK = re.compile(r"[a-z]+(?:'[a-z]+)?")


def toks(s):
    """Lower case; U.S. -> usa; curly apostrophes normalised; a word split at
    a line end re-joined; numbers -> num; hyphens split words."""
    s = re.sub(r"\bU\.\s?S\.", " usa ", s)
    s = re.sub("[’‘ʼ`]", "'", s.lower())
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    s = re.sub(r"\d[\d,.]*", " num ", s)
    s = s.replace("-", " ")
    return _TOK.findall(s)


def prose_words(s):
    """Words of a sentence as the length rules count them: citations
    (CITEX) are not words -- the same count para_lengths.py uses."""
    return len([t for t in toks(s) if t != "citex"])


# A statistic's label before its value ("OR 0.41", "aHR = 1.2", "RRs 0.8"):
# lower-cased it would read as the word "or". Case-sensitive on purpose.
STAT_LABEL = re.compile(r"\b(?:a?ORs?|a?HRs?|a?RRs?|IRRs?)\b(?=\s*[=:,]?\s*[-−]?\.?\d)")


def gram_toks(s):
    """Tokens for frame (n-gram) counting: a statistic label is masked as a
    citation, so no frame runs across it."""
    return toks(STAT_LABEL.sub(" CITEX ", s))


# ---- blocks: the units h2 and g compare ---------------------------------------
_COMMENT_AT_END = re.compile(r"(?<!\\)%\s*(.*)$")


def latex_sentences(text, split):
    """Split raw LaTeX; a sentence that opens with \\citet{} is still a new
    sentence (the splitter wants a capital), so citations are swapped for
    capitalised placeholders while splitting and put back after."""
    keep = []

    def hold(m):
        keep.append(m.group(0))
        return "Cite%dq" % (len(keep) - 1)
    out = split(CITE_ANY_RE.sub(hold, text))
    return [re.sub(r"Cite(\d+)q", lambda m: keep[int(m.group(1))], s).strip() for s in out]


def comment_blocks(lines):
    """OrderedDict {(comment, occurrence): text}: a block is the text up to and
    including a line ending in a comment (the `% Key p.N` page comment); text
    after the last comment is one more block, ("(no comment)", 1)."""
    from collections import OrderedDict
    out, buf, seen = OrderedDict(), [], {}
    for _, line in body_lines(lines):
        m = _COMMENT_AT_END.search(line)
        body = re.sub(r"(?<!\\)%.*$", "", line).strip()
        if body:
            buf.append(body)
        if m:
            key = m.group(1).strip()
            seen[key] = seen.get(key, 0) + 1
            out[(key, seen[key])] = " ".join(buf)
            buf = []
    if buf:
        out[("(no comment)", 1)] = " ".join(buf)
    return out


def cite_blocks(lines, split):
    """OrderedDict {(cited keys, occurrence): text}: one block per cited study.
    A block starts at a sentence whose first citation names other keys than
    the current block's; a sentence with no citation joins the current block,
    except at the start of a paragraph, where it opens a ("(no citation)", n)
    block (a topic sentence is not the previous paragraph's study)."""
    from collections import OrderedDict
    out, seen = OrderedDict(), {}
    cur, buf = "(no citation)", []

    def flush():
        if buf:
            seen[cur] = seen.get(cur, 0) + 1
            out[(cur, seen[cur])] = " ".join(buf)
    for _, pl in paragraphs(body_lines(lines)):
        text = " ".join(re.sub(r"(?<!\\)%.*$", "", t).strip() for t in pl)
        for i, s in enumerate(latex_sentences(text, split)):
            m = CITE_KEYS_RE.search(s)
            keys = ",".join(sorted(k.strip() for k in m.group(1).split(",") if k.strip())) if m else None
            if (keys and keys != cur) or (i == 0 and not keys):
                flush()
                cur, buf = keys or "(no citation)", []
            buf.append(s)
    flush()
    return out


def section_blocks(lines, split):
    """Page-comment blocks when the section has page comments, else one block
    per cited study. Returns (blocks, "comments" | "citations")."""
    if any(_COMMENT_AT_END.search(re.sub(r"\\%", "", t)) and t.split("%", 1)[0].strip()
           for _, t in body_lines(lines)):
        return comment_blocks(lines), "comments"
    return cite_blocks(lines, split), "citations"


# ---- abbreviations defined in a text ("Long Name (ABBR)") ----------------------
_ABBR_DEF = re.compile(r"((?:[A-Za-z][\w'-]*\s+){1,8}?)\(([A-Z][A-Za-z]{1,9}s?)\)")


def abbreviations(text):
    """{ABBR: long form} for every "Long Name (ABBR)" whose letters are the
    initials of the words just before it (traumatic brain injury (TBI))."""
    out = {}
    for m in _ABBR_DEF.finditer(re.sub(r"\s+", " ", text)):
        ab = m.group(2)
        letters = [c for c in ab.rstrip("s") if c.isupper()] or list(ab.rstrip("s").upper())
        words = m.group(1).split()
        for n in range(len(letters), len(words) + 1):
            cand = words[-n:]
            initials = [w[0].upper() for w in cand if w.lower() not in ("of", "and", "the", "for", "in", "on", "to")]
            if initials == letters:
                out.setdefault(ab, " ".join(cand))
                break
    return out


def term_variants(term, defs):
    """Other forms of `term` under abbreviation definitions {ABBR: long form}:
    an abbreviation in the term spelled out, a long form in the term
    abbreviated. [(variant, "ABBR=long form")]."""
    def one_step(t, why):
        res = []
        for ab, long in defs.items():
            if re.search(r"\b%s\b" % re.escape(ab), t):
                res.append((re.sub(r"\b%s\b" % re.escape(ab), long, t), why + ["%s=%s" % (ab, long)]))
            if re.search(re.escape(long), t, re.I):
                res.append((re.sub(re.escape(long), ab, t, flags=re.I), why + ["%s=%s" % (ab, long)]))
        return res
    # two rounds: "TBI Model Systems" -> "traumatic brain injury Model Systems"
    # -> "TBIMS" when the paper abbreviates the whole name
    first = one_step(term, [])
    out = [(v, " then ".join(w)) for v, w in first]
    for v, w in first:
        out += [(v2, " then ".join(w2)) for v2, w2 in one_step(v, w)]
    seen, uniq = set(), []
    for v, why in out:
        if v.lower() != term.lower() and v.lower() not in seen:
            seen.add(v.lower())
            uniq.append((v, why))
    return uniq


def split_cite_links(pdf):
    """[(page, target)] for citation links split by a page break: the last
    internal link on page p and the first on page p+1 point at the same
    target (one citation printed across the break). None without links."""
    try:
        import fitz
    except ImportError:
        return None
    hits, any_link, prev = [], False, None
    with fitz.open(pdf) as d:
        for pno in range(d.page_count):
            links = [l for l in d[pno].get_links() if l.get("kind") in (fitz.LINK_GOTO, fitz.LINK_NAMED)]
            if not links:
                prev = None
                continue
            any_link = True
            links.sort(key=lambda l: (round(l["from"].y0, 1), l["from"].x0))

            def target(l):
                return (l.get("page"), l.get("nameddest") or l.get("name"),
                        round(getattr(l.get("to"), "y", 0) or 0))
            if prev is not None and target(links[0]) == prev:
                hits.append((pno, "%s" % (links[0].get("nameddest") or links[0].get("name")
                                          or "page %s" % (links[0].get("page", -1) + 1))))
            prev = target(links[-1])
    return hits if any_link else None


def strip_line(line):
    """One LaTeX line -> prose: comments dropped, \\citet/\\citep -> CITEX,
    other commands (with their arguments) dropped."""
    line = re.sub(r"(?<!\\)%.*", "", line).replace("\\%", "%")
    line = CITE_ANY_RE.sub(" CITEX ", line)    # every natbib / biblatex citation
    line = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*", " ", line)
    line = line.replace("---", " — ").replace("--", "–")
    return re.sub(r"[{}~$\\]", " ", line)


def corpus_sentences(ctx):
    """Yield (paper id, token list) for every sentence of the style-safe corpus
    (the cleaned text attest.py searches, references excluded)."""
    attest, textseg = ctx.lit_modules()
    for pid in attest.eligible(attest.load_meta(), "style"):
        txt = attest._text(pid, False)
        if not txt:
            continue
        for sent in textseg.split_sentences(re.sub(r"\s+", " ", txt)):
            yield pid, toks(sent)


def corpus_length_stats(ctx):
    """(median, P90) words per sentence over the style corpus, sentences of
    3-150 tokens -- the yardstick of sweep L3 and para_lengths."""
    xs = sorted(len(t) for _, t in corpus_sentences(ctx) if 3 <= len(t) <= 150)
    if not xs:
        die("the style-safe corpus has no sentences")
    return xs[len(xs) // 2], xs[int(0.9 * len(xs))]


def para_sentences(lines, split, clean=strip_line, min_words=3):
    """[(line no where the sentence starts, sentence)] over the paragraphs of
    `lines`; sentences are split per paragraph (so a hard-wrapped sentence
    stays whole), and only those with >= min_words words are kept."""
    out = []
    for start, plines in paragraphs(lines):
        joined, spans, pos = [], [], 0
        for k, raw in enumerate(plines):
            c = re.sub(r"\s+", " ", clean(raw)).strip()
            if not c:
                continue
            spans.append((pos, start + k))
            joined.append(c)
            pos += len(c) + 1
        text = " ".join(joined)
        cur = 0
        for s in split(text):
            s = s.strip()
            if len(s.split()) < min_words:
                continue
            j = text.find(s[:30], cur)
            if j < 0:
                j = cur
            cur = j + 1
            ln = start
            for off, lno in spans:
                if off <= j:
                    ln = lno
            out.append((ln, s))
    return out


# ---- draft records: corpus paragraph openers -------------------------------
_REC_HEAD = re.compile(r"^###\s+([A-Za-z0-9][A-Za-z0-9_\-]*)(?=[\s(（]|$)(.*)$")
_REC_SKIP = re.compile(r"^\s*[—–-]+\s*NOT?\b")
_REC_ITEM = re.compile(r"^(¶|P|S|T)(\d+)\b")
_REC_QUOTE = re.compile(r'^>\s*"(.+?)"?\s*(?:`?\[[^\]]*\]?`?)?\s*$')


def record_openers(ctx):
    """[(paper key, chapter, first sentence)] of every corpus paragraph, read
    from the draft sibling's references/records/*.md (Tier 3 output). Only
    `### <key>` headings whose key is a corpus paper count; a `--- NOT ...`
    heading (a slice the record rejects) is skipped."""
    rec = os.path.join(ctx.draft, "references", "records")
    if not os.path.isdir(rec):
        return []
    attest, _ = ctx.lit_modules()
    known = {p.get("id") for p in attest.load_meta().get("papers", [])}
    out = []
    for f in sorted(os.listdir(rec)):
        if not f.endswith(".md"):
            continue
        chapter = f[:-3]
        paper, item = None, None
        for line in _read(os.path.join(rec, f)).splitlines():
            if line.startswith("#"):
                m = _REC_HEAD.match(line)
                paper = m.group(1) if (m and m.group(1) in known
                                       and not _REC_SKIP.match(m.group(2))) else None
                item = None
                continue
            m = _REC_ITEM.match(line)
            if m:
                item = m.group(1) if m.group(1) in "¶P" else m.group(1) + m.group(2)
                continue
            m = _REC_QUOTE.match(line)
            # a paragraph item's quote is its first sentence; in per-sentence
            # records (abstracts: S1, S2, ...) only S1 opens the paragraph
            if m and paper and item in ("¶", "P", "S1"):
                out.append((paper, chapter, m.group(1)))
                item = None
    return out
