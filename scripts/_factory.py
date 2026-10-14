"""Shared by the onboarding scripts (onboard.py, tier0_accept.py,
calibrate_paragraphs.py, tier1_fill.py): find a field's instances, run their
scripts, edit both field-configs (and prove the edit parses), update the
registries. Standard library only."""
import datetime
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
TEMPLATES = os.path.join(SKILL, "templates")
DEFAULT_DEST = os.path.dirname(SKILL)
TODAY = datetime.date.today().isoformat()
# the launcher the printed hints name: Windows has the py launcher, macOS and
# Linux have python3
PY = "py -3" if os.name == "nt" else "python3"
# a field slug: lowercase ASCII letters and digits, single hyphens between
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def die(msg, code=2):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def norm_field(field):
    """The slug stamp.py writes: trimmed and lowercased."""
    return (field or "").strip().lower()


def user_path(p):
    """A path argument as the user typed it: ~ expanded (PowerShell and cmd do not)."""
    return os.path.abspath(os.path.expanduser(p)) if p else p


def dest_arg(dest):
    """' --dest "<dest>"' for a printed next command, or '' for the default."""
    if not dest or os.path.normcase(user_path(dest)) == os.path.normcase(DEFAULT_DEST):
        return ""
    return ' --dest "%s"' % user_path(dest)


class Field(object):
    """A stamped field: <dest>/<field>-lit, -draft, -polish."""

    def __init__(self, field, dest=None):
        field = norm_field(field)
        self.field = field
        self.dest = user_path(dest or DEFAULT_DEST)
        self.lit = os.path.join(self.dest, field + "-lit")
        self.draft = os.path.join(self.dest, field + "-draft")
        self.polish = os.path.join(self.dest, field + "-polish")

    def exists(self):
        return os.path.isfile(os.path.join(self.lit, "references", "registry.json"))

    def require(self):
        if not self.exists():
            die("no stamped field %r under %s (onboard.py stamps it)" % (self.field, self.dest))
        return self

    # ---- configs -----------------------------------------------------------
    def configs(self):
        return [os.path.join(d, "references", "field-config.yaml") for d in (self.lit, self.draft)
                if os.path.isdir(d)]

    def cfgparse(self):
        p = os.path.join(self.lit, "scripts")
        if p not in sys.path:
            sys.path.insert(0, p)
        import _cfgparse
        return _cfgparse

    def config(self):
        return self.cfgparse().parse(self.configs()[0])

    def set_scalar(self, key, value, comment=""):
        for path in self.configs():
            set_scalar(path, key, value, comment)
        self.verify(key, value)

    def set_list(self, key, items, header=""):
        """items: [(value, reason)]; replaces the whole block in BOTH configs."""
        for path in self.configs():
            set_list(path, key, items, header)
        self.verify(key, [v for v, _ in items])

    def verify(self, key, want):
        cp = self.cfgparse()
        for path in self.configs():
            del cp.WARNINGS[:]
            got = cp.parse(path).get(key)
            if isinstance(want, list):
                ok = sorted(cp.as_list(got)) == sorted(str(w) for w in want)
            else:
                ok = cp.as_str(got) == str(want)
            if not ok or cp.WARNINGS:
                die("%s: %s did not read back as written (got %r; %s)"
                    % (path, key, got, "; ".join(cp.WARNINGS)))

    # ---- registries ----------------------------------------------------------
    def registry(self, which):
        return os.path.join(self.lit if which == "lit" else self.draft, "references", "registry.json")

    def update_registry(self, which, fn):
        p = self.registry(which)
        with open(p, encoding="utf-8") as fh:
            reg = json.load(fh)
        fn(reg)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(reg, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        return reg

    def add_tier(self, tier):
        for which in ("lit", "draft"):
            if os.path.isfile(self.registry(which)):
                self.update_registry(which, lambda r: r.__setitem__(
                    "built_tiers", sorted(set(int(t) for t in r.get("built_tiers", [])) | {tier})))

    def drop_tier(self, tier):
        for which in ("lit", "draft"):
            if os.path.isfile(self.registry(which)):
                self.update_registry(which, lambda r: r.__setitem__(
                    "built_tiers", sorted(set(int(t) for t in r.get("built_tiers", [])) - {tier})))

    def built_tiers(self):
        try:
            with open(self.registry("lit"), encoding="utf-8") as fh:
                return sorted(int(t) for t in json.load(fh).get("built_tiers", []))
        except (OSError, ValueError):
            return []

    # ---- running instance scripts ----------------------------------------------
    def run(self, which, script, args=(), check=True, show=True):
        d = {"lit": self.lit, "draft": self.draft, "polish": self.polish}[which]
        return run([sys.executable, "-B", os.path.join(d, "scripts", script)] + list(args),
                   cwd=d, check=check, show=show)

    def denominators(self):
        meta = os.path.join(self.lit, "references", "corpus_meta.yaml")
        with open(meta, encoding="utf-8") as fh:
            m = fh.read()
        out = {}
        for k in ("files", "distinct", "terminology_safe", "style_safe"):
            g = re.search(r"^\s+%s:\s*(\d+)" % k, m, re.M)
            out[k] = int(g.group(1)) if g else None
        return out

    def style_safe_ids(self):
        meta = os.path.join(self.lit, "references", "corpus_meta.yaml")
        with open(meta, encoding="utf-8") as fh:
            m = fh.read()
        return [b.split("\n", 1)[0].strip() for b in re.split(r"(?m)^  - id:\s*", m)[1:]
                if re.search(r"^\s+style_safe:\s*true", b, re.M)]


def run(cmd, cwd=None, check=True, show=True):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if show and r.stdout.strip():
        print("\n".join("    | " + l for l in r.stdout.rstrip().splitlines()))
    if check and r.returncode != 0:
        shown = [c for c in cmd[1:] if c != "-B"][:2]
        die("FAILED (exit %d): %s\n%s" % (r.returncode, " ".join(os.path.basename(c) for c in shown),
                                          (r.stderr or r.stdout)[-1500:]))
    return r


# ---- field-config editing (the _cfgparse subset) ------------------------------
_KEYLINE = re.compile(r"^([a-z][a-z0-9_\-]*):")


def _block(lines, key):
    """(start, end) of key's block: its line plus the item / comment lines
    that follow it up to a blank line or the next key."""
    for i, ln in enumerate(lines):
        if re.match(r"^%s:(\s|$)" % re.escape(key), ln):
            j = i + 1
            while j < len(lines) and lines[j].strip() and not _KEYLINE.match(lines[j]):
                j += 1
            return i, j
    return None, None


def _rewrite(path, key, new_lines):
    with open(path, encoding="utf-8-sig") as fh:
        lines = fh.read().split("\n")
    i, j = _block(lines, key)
    if i is None:
        if lines and lines[-1] == "":
            lines = lines[:-1]
        lines += [""] + new_lines + [""]
    else:
        lines[i:j] = new_lines
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def _q(v):
    v = str(v)
    if v == "" or re.search(r"[#:'\"\[\]{},]|^\s|\s$|^-", v):
        return "'" + v.replace("'", "''") + "'"
    return v


def set_scalar(path, key, value, comment=""):
    _rewrite(path, key, ["%s: %s%s" % (key, _q(value), "   # " + comment if comment else "")])


def set_list(path, key, items, header=""):
    new = ["%s:" % key]
    if header:
        new += ["  # " + h for h in header.splitlines()]
    for v, why in items:
        new.append("  - %s%s" % (_q(v), "   # " + why.replace("\n", " ") if why else ""))
    _rewrite(path, key, new)
