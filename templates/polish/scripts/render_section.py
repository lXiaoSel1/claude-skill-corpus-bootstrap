#!/usr/bin/env python3
"""Step j -- render a section as readable text, with citation labels taken from
the compiled .bbl (as the PDF prints them: et al., a/b suffixes) and the
manuscript's \\defcitealias short names. Handles \\citet, \\citep, \\citealp,
\\citetalias, \\citepalias (one key or several), \\citetext{...}, natbib's
optional notes, \\mbox{}, \\%, \\$, \\&, dashes.

RUN
    py -3 scripts/render_section.py <section> [section ...]
Needs a compiled manuscript (compile.py) for the .bbl.
"""
import os
import re
import sys

import _rp

ctx = _rp.Ctx(sys.argv)
if not ctx.args:
    _rp.die(__doc__)
ms = ctx.ms
if not os.path.isfile(ms.bbl):
    _rp.die("no %s -- compile the manuscript first (compile.py)" % ms.bbl)
lab = ms.bbl_labels()
ALIAS = ms.aliases
unknown = set()
OPT = r"((?:\[[^\]]*\]){0,2})"


def opts(o):
    parts = re.findall(r"\[([^\]]*)\]", o or "")
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", (parts[0] if parts else "")


def L(k):
    k = k.strip()
    if k not in lab:
        unknown.add(k)
        return ("[?%s]" % k, "")
    return lab[k]


def keys(s):
    return [k.strip() for k in s.split(",") if k.strip()]


def ct(o, ks):
    pre, post = opts(o)
    out = []
    for k in keys(ks):
        a, y = L(k)
        out.append("%s (%s%s)" % (a, y, ", " + post if post and k == keys(ks)[-1] else ""))
    return (pre + " " if pre else "") + "; ".join(out)


def cp(o, ks, paren=True):
    pre, post = opts(o)
    body = "; ".join("%s, %s" % L(k) for k in keys(ks))
    body = (pre + " " if pre else "") + body + (", " + post if post else "")
    return "(" + body + ")" if paren else body


def alias(k):
    k = k.strip()
    if k not in ALIAS:
        unknown.add(k)
        return "[?%s]" % k
    return ALIAS[k]


ACC = {"'": {"e": "é", "a": "á", "i": "í", "o": "ó", "u": "ú", "E": "É"},
       '"': {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"},
       "`": {"e": "è", "a": "à"}}


def render(line):
    line = re.sub(r"(?<!\\)%.*", "", line)
    line = re.sub(r"\\citet\*?" + OPT + r"\{([^}]+)\}", lambda m: ct(m.group(1), m.group(2)), line)
    line = re.sub(r"\\citepalias\{([^}]+)\}", lambda m: "(" + "; ".join(alias(k) for k in keys(m.group(1))) + ")", line)
    line = re.sub(r"\\citep\*?" + OPT + r"\{([^}]+)\}", lambda m: cp(m.group(1), m.group(2)), line)
    line = re.sub(r"\\citealp\*?" + OPT + r"\{([^}]+)\}", lambda m: cp(m.group(1), m.group(2), False), line)
    line = re.sub(r"\\citetalias\{([^}]+)\}", lambda m: "; ".join(alias(k) for k in keys(m.group(1))), line)
    line = re.sub(r"\\citetext\{([^{}]*)\}", lambda m: "(" + m.group(1) + ")", line)
    line = re.sub(r"\\mbox\{([^{}]*)\}", r"\1", line)
    line = line.replace("\\%", "%").replace("\\$", "$").replace("\\&", "&").replace("---", "—").replace("--", "–")
    line = re.sub(r"\\(['\"`])\{?(\w)\}?", lambda m: ACC[m.group(1)].get(m.group(2), m.group(2)), line)
    line = line.replace("vs.\\ ", "vs. ").replace("\\ ", " ")
    return line.rstrip()


for n, sec in enumerate(ctx.sections(ctx.args)):
    if n:
        print("\n" + "=" * 70 + "\n")
    paras = []
    for _, pl in _rp.paragraphs(_rp.section_body(sec)):
        r = [render(l) for l in pl]
        r = " ".join(x for x in r if x)
        if r:
            paras.append(r)
    print("\n\n".join(paras))
if unknown:
    sys.stderr.write("\nnot in the .bbl or the aliases (recompile?): %s\n" % ", ".join(sorted(unknown)))
    sys.exit(1)
