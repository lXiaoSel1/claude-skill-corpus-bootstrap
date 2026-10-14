#!/usr/bin/env python3
"""Read a LaTeX manuscript's structure from its main .tex file -- no configuration.

A section (the unit every polish step works on) is either
  * a file the main file pulls in with \\input{} / \\include{} (one file = one
    section; key = the file stem), or
  * in a single-file manuscript, the stretch between two headings at the split
    level (default \\section; polish.yaml `split_level: subsection` changes it;
    key = the heading's \\label without its prefix, else a slug of the title).

Also read from the main file: citation aliases (\\defcitealias), the
bibliography files (\\bibliography / \\addbibresource) and the compiled .bbl
(next to the main file).

Standalone on purpose (standard library only): the factory's onboard.py
imports it before any instance exists.

RUN
    py -3 scripts/manuscript.py <main.tex> [--split-level section|subsection]
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LEVELS = ["part", "chapter", "section", "subsection", "subsubsection"]
_COMMENT = re.compile(r"(?<!\\)%.*$")
_HEAD = re.compile(r"\\(part|chapter|section|subsection|subsubsection)\*?"
                   r"(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}")
_LABEL = re.compile(r"\\label\{([^}]+)\}")
_INPUT = re.compile(r"\\(?:input|include)\{([^}]+)\}")
_ALIAS = re.compile(r"\\defcitealias\{([^}]+)\}\{((?:[^{}]|\{[^{}]*\})*)\}")
# Every citation command: natbib (\cite \citet \citep \citealt \citeauthor
# \citepalias \Citet ...) and biblatex (\parencite \textcite \autocite
# \footcite \smartcite \supercite \fullcite and capitalised forms), with a
# star and up to two optional arguments. \nocite cites nothing in the text,
# and \citetext holds free text, not keys. The one copy the polish scripts use.
CITE_CMD = r"\\(?!nocite\b|citetext\b)[A-Za-z]*[Cc]ite[A-Za-z]*\*?(?:\[[^\]]*\]){0,2}"
CITE_KEYS_RE = re.compile(CITE_CMD + r"\{([^}]+)\}")
CITE_ANY_RE = re.compile(r"\\citetext\{(?:[^{}]|\{[^{}]*\})*\}|" + CITE_CMD + r"\{[^}]*\}")
_BIB = re.compile(r"\\bibliography\{([^}]+)\}")
_BIBRES = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]+)\}")
_END_BODY = re.compile(r"\\(?:bibliography|printbibliography|appendix|end\{document\})")
_SEPARATOR = re.compile(r"^\s*(?:%[\s\-=*#~_.%]*)?$")


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _slug(title):
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", title)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "section"


class Section(object):
    """One editing unit. `path` is the file that holds it (the input file, or
    the main file for a heading range); `first`..`last` are 1-based line
    numbers of its text in that file (the heading line itself excluded)."""

    def __init__(self, key, title, path, first, last, chapter="", kind="file"):
        self.key, self.title, self.path = key, title, path
        self.first, self.last, self.chapter, self.kind = first, last, chapter, kind

    def lines(self):
        """[(line_no, text)] of the section, read fresh from disk."""
        all_lines = _read(self.path).splitlines()
        last = self.last if self.kind == "range" else len(all_lines)
        return [(i, all_lines[i - 1]) for i in range(self.first, last + 1)
                if i - 1 < len(all_lines)]

    def text(self):
        return "\n".join(t for _, t in self.lines())

    def __repr__(self):
        return "Section(%s, %s:%d-%d)" % (self.key, os.path.basename(self.path),
                                          self.first, self.last)


class Manuscript(object):
    def __init__(self, path, split_level="section"):
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            raise FileNotFoundError("manuscript not found: " + self.path)
        self.dir = os.path.dirname(self.path)
        self.stem = os.path.splitext(os.path.basename(self.path))[0]
        self.split_level = split_level
        self.raw = _read(self.path)
        self.lines = self.raw.splitlines()
        b = self.raw.find("\\begin{document}")
        self.preamble = self.raw[:b] if b >= 0 else ""
        self.body_first = self.raw[:b].count("\n") + 2 if b >= 0 else 1
        self.aliases = self._aliases()
        self.bib_files = self._bibs()
        self.bbl = os.path.join(self.dir, self.stem + ".bbl")
        self.sections = self._sections()

    # ---- metadata ----------------------------------------------------------
    def _uncommented(self, text):
        return "\n".join(_COMMENT.sub("", ln) for ln in text.splitlines())

    def _aliases(self):
        out = {}
        for m in _ALIAS.finditer(self._uncommented(self.raw)):
            out[m.group(1).strip()] = re.sub(r"[{}]", "", m.group(2)).strip()
        return out

    def _bibs(self):
        t = self._uncommented(self.raw)
        out = []
        for m in _BIB.finditer(t):
            for b in m.group(1).split(","):
                b = b.strip()
                out.append(os.path.join(self.dir, b if b.endswith(".bib") else b + ".bib"))
        for m in _BIBRES.finditer(t):
            out.append(os.path.join(self.dir, m.group(1).strip()))
        return out

    # ---- sections ----------------------------------------------------------
    def _resolve_input(self, name):
        name = name.strip()
        cand = os.path.join(self.dir, name)
        if not os.path.splitext(cand)[1]:
            cand += ".tex"
        return os.path.normpath(cand)

    def _sections(self):
        heads, inputs = [], []          # (line_no, level, title, label) / (line_no, path)
        in_body = False
        for i, ln in enumerate(self.lines, 1):
            code = _COMMENT.sub("", ln)
            if "\\begin{document}" in code:
                in_body = True
            if not in_body:
                continue
            if _END_BODY.search(code) and "\\end{document}" in code:
                break
            for m in _HEAD.finditer(code):
                lab = _LABEL.search(code[m.end():])
                if not lab and i < len(self.lines):
                    lab = _LABEL.match(_COMMENT.sub("", self.lines[i]).strip())
                heads.append((i, m.group(1), m.group(2).strip(),
                              lab.group(1) if lab else ""))
            for m in _INPUT.finditer(code):
                inputs.append((i, self._resolve_input(m.group(1))))
        if inputs:
            return self._file_sections(heads, inputs)
        return self._range_sections(heads)

    def _file_sections(self, heads, inputs):
        out, seen = [], set()
        for ln, path in inputs:
            before = [h for h in heads if h[0] <= ln]
            title = before[-1][2] if before else ""
            lvl = LEVELS.index(before[-1][1]) if before else 99
            chapter = next((h[2] for h in reversed(before)
                            if LEVELS.index(h[1]) < lvl), "")
            key = os.path.splitext(os.path.basename(path))[0]
            if key in seen:
                key = "%s-%d" % (key, ln)
            seen.add(key)
            n = len(_read(path).splitlines()) if os.path.isfile(path) else 0
            out.append(Section(key, title, path, 1, n, chapter, "file"))
        return out

    def _range_sections(self, heads):
        lvl = self.split_level
        if lvl not in LEVELS:
            raise ValueError("split_level must be one of " + ", ".join(LEVELS))
        top = LEVELS.index(lvl)
        # the body ends at the bibliography / appendix / \end{document}
        end = len(self.lines)
        for i, ln in enumerate(self.lines, 1):
            if i >= self.body_first and _END_BODY.search(_COMMENT.sub("", ln)):
                end = i - 1
                break
        cuts = [h for h in heads if LEVELS.index(h[1]) <= top and h[0] <= end]
        out, seen = [], set()
        for j, (ln, level, title, label) in enumerate(cuts):
            if level != lvl:
                continue
            nxt = cuts[j + 1][0] - 1 if j + 1 < len(cuts) else end
            chapter = next((h[2] for h in reversed(cuts[:j])
                            if LEVELS.index(h[1]) < top), "")
            # trailing blank lines and separator comments (% ---- before the
            # next heading) belong to no section
            while nxt > ln + 1 and _SEPARATOR.match(self.lines[nxt - 1]):
                nxt -= 1
            key = re.sub(r"^(sec|ch|subsec|ssec)[:\-_]", "", label) if label else _slug(title)
            base, k = key, 2
            while key in seen:
                key, k = "%s-%d" % (base, k), k + 1
            seen.add(key)
            out.append(Section(key, title, self.path, ln + 1, nxt, chapter, "range"))
        return out

    def section(self, key_or_path):
        """Look a section up by key, file name, or path."""
        k = key_or_path
        for s in self.sections:
            if k in (s.key, os.path.basename(s.path)) or (
                    s.kind == "file" and os.path.abspath(k) == os.path.abspath(s.path)):
                return s
        keys = ", ".join(s.key for s in self.sections)
        raise KeyError("no section %r in %s (sections: %s)" % (k, os.path.basename(self.path), keys))

    # ---- whole document ----------------------------------------------------
    def expanded_body(self):
        """Body text (\\begin{document} .. before the bibliography) with every
        \\input/\\include replaced by the file's text -- the whole manuscript as
        one string, for document-wide statistics."""
        body = self.raw.split("\\begin{document}", 1)[-1]
        cut = re.search(r"\\(?:bibliography|printbibliography)\b", body)
        if cut:
            body = body[:cut.start()]

        def sub(m):
            p = self._resolve_input(m.group(1))
            return _read(p) if os.path.isfile(p) else ""
        out = []
        for ln in body.splitlines():
            if _INPUT.search(_COMMENT.sub("", ln)):
                out.append(_INPUT.sub(lambda m: sub(m), _COMMENT.sub("", ln)))
            else:
                out.append(ln)
        return "\n".join(out)

    def cited_keys(self):
        keys = set()
        text = "\n".join(_COMMENT.sub("", ln) for ln in self.expanded_body().splitlines())
        for m in CITE_KEYS_RE.finditer(text):
            keys |= {k.strip() for k in m.group(1).split(",") if k.strip()}
        return keys

    def bbl_labels(self):
        """{key: (author label, year with a/b suffix)} from the compiled .bbl
        (natbib author-year styles such as plainnat); {} when not compiled."""
        if not os.path.isfile(self.bbl):
            return {}
        lab = {}
        for m in re.finditer(r"\\bibitem\[(.*?)\]\{([^}]+)\}\s*$", _read(self.bbl), re.S | re.M):
            raw = re.sub(r"\s+", " ", m.group(1)).replace("~", " ")
            raw = re.sub(r"\{\\natexlab\{(\w)\}\}", r"\1", raw).replace("{", "").replace("}", "")
            mm = re.match(r"(.*?)\(([^()]*?\d{4}\w?)\)", raw)
            if mm:
                lab[m.group(2).strip()] = (mm.group(1).strip(), mm.group(2))
        return lab


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    lvl = sys.argv[sys.argv.index("--split-level") + 1] if "--split-level" in sys.argv else "section"
    ms = Manuscript(sys.argv[1], lvl)
    print("manuscript: %s" % ms.path)
    print("sections (%d, %s):" % (len(ms.sections),
                                  "input files" if ms.sections and ms.sections[0].kind == "file"
                                  else "split at \\" + lvl))
    for s in ms.sections:
        print("  %-28s %-40s %s:%d-%d" % (s.key, (s.title or "")[:40],
                                          os.path.relpath(s.path, ms.dir), s.first, s.last))
    print("aliases: %s" % (", ".join("%s=%s" % kv for kv in sorted(ms.aliases.items())) or "none"))
    print("bibliography: %s" % (", ".join(ms.bib_files) or "none"))
    print("bbl: %s (%s)" % (ms.bbl, "present" if os.path.isfile(ms.bbl) else "not compiled yet"))
    print("cited keys: %d" % len(ms.cited_keys()))


if __name__ == "__main__":
    main()
