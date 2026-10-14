"""Shared by rep.py and rep_multi.py: parse a pairs file, check every pair
against its target, and write only when all of them match exactly once."""
import os
import re
import shutil
import time

import _rp

_SEP = re.compile(r"\n===[ \t]*(?:\n|$)")
_ARROW = re.compile(r"\n>>>[ \t]*\n")


def parse(text, multi):
    """{target or None: [(old, new, block no)]}."""
    text = "\n" + text.replace("\r\n", "\n").strip("\n") + "\n"
    out, cur = {}, None
    for i, chunk in enumerate(_SEP.split(text), 1):
        lines = chunk.strip("\n").split("\n")
        if multi and lines and lines[0].startswith("FILE "):
            cur = lines[0][5:].strip()
            lines = lines[1:]
        body = "\n".join(lines)
        if not body.strip():
            continue
        parts = _ARROW.split("\n" + body + "\n")
        if len(parts) != 2:
            _rp.die("pairs block %d: needs exactly one line `>>>` between OLD and NEW" % i)
        old, new = parts[0].strip("\n"), parts[1].strip("\n")
        if not old:
            _rp.die("pairs block %d: OLD text is empty" % i)
        out.setdefault(cur, []).append((old, new, i))
    return out


class Job(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.files = {}        # path -> {"nl", "orig", "segs": [[key, text]], "whole"}
        self.errors, self.done = [], []

    def _file(self, path, ranges):
        """Load a file once, cut into segments: one per heading-range section
        (so a pair is matched only inside its own section) and the rest."""
        if path in self.files:
            if self.files[path]["whole"] != (not ranges):
                _rp.die("%s: a pairs file cannot target this file both whole and by section"
                        % os.path.basename(path))
            return self.files[path]
        with open(path, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        nl = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.replace("\r\n", "\n").split("\n")
        segs, pos = [], 0
        for key, first, last in sorted(ranges, key=lambda r: r[1]):
            if first - 1 > pos:
                segs.append([None, "\n".join(lines[pos:first - 1])])
            segs.append([key, "\n".join(lines[first - 1:last])])
            pos = last
        if pos < len(lines):
            segs.append([None, "\n".join(lines[pos:])])
        self.files[path] = {"nl": nl, "orig": raw, "segs": segs, "whole": not ranges}
        return self.files[path]

    def add(self, target, pairs):
        if os.path.isfile(target):
            f = self._file(os.path.abspath(target), [])
            keys = None
        else:
            sec = self.ctx.sections([target])[0]
            ranges = []
            if sec.kind == "range":
                ranges = [(s.key, s.first, s.last) for s in self.ctx.ms.sections
                          if s.kind == "range" and s.path == sec.path]
            f = self._file(sec.path, ranges)
            keys = {sec.key} if ranges else None
        n = 0
        for old, new, i in pairs:
            segs = [s for s in f["segs"] if keys is None or s[0] in keys]
            c = sum(s[1].count(old) for s in segs)
            if c != 1:
                self.errors.append((c, "%s, block %d: %d matches for: %s"
                                    % (target, i, c, old[:70].replace("\n", " / "))))
                continue
            for s in segs:
                if old in s[1]:
                    s[1] = s[1].replace(old, new)
            n += 1
        self.done.append((target, n, len(pairs)))

    def commit(self):
        if self.errors:
            for c, e in self.errors:
                print(("NO MATCH  " if c == 0 else "AMBIGUOUS ") + e)
            print("nothing written (%d of %d pair(s) failed)"
                  % (len(self.errors), sum(t for _, _, t in self.done)))
            return 1
        try:
            base = os.path.dirname(self.ctx.manuscript_path())
        except SystemExit:
            base = os.path.dirname(next(iter(self.files)))
        root = os.path.join(base, ".polish", "rep-backup")
        stamp = first = time.strftime("%Y%m%d-%H%M%S")
        n = 2
        while os.path.exists(os.path.join(root, stamp)):     # two runs in one second
            stamp, n = "%s-%d" % (first, n), n + 1
        for path, f in self.files.items():
            text = "\n".join(s[1] for s in f["segs"]).replace("\n", f["nl"])
            if text == f["orig"]:
                continue
            try:
                rel = os.path.relpath(path, base)
            except ValueError:                         # another drive
                rel = ".."
            if rel.startswith(".."):
                rel = os.path.basename(path)
            bk = os.path.join(root, stamp, rel)
            os.makedirs(os.path.dirname(bk), exist_ok=True)
            shutil.copy2(path, bk)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        for target, n, _ in self.done:
            print("%s: %d replacement(s)" % (target, n))
        return 0
