#!/usr/bin/env python3
"""Step a -- save the named sections before editing them. trial_diff.py and
sent_diff.py compare the live sections against a snapshot.

Snapshots go to <manuscript dir>/.polish/snapshots/<name>/<section>.tex
(polish.yaml `snapshot_dir` moves them). A section that is a heading range
of a single-file manuscript is saved as its lines; a section that is an
\\input file is saved whole. An existing snapshot is never overwritten
unless --force is given.

RUN
    py -3 scripts/snapshot.py <name> [section ...]      # all sections when none named
    py -3 scripts/snapshot.py --list
"""
import hashlib
import json
import os
import sys
import time

import _rp

ctx = _rp.Ctx(sys.argv)
force = _rp._pop(ctx.args, "--force", flag=True)
listing = _rp._pop(ctx.args, "--list", flag=True)
root = ctx.snapshot_root()

if listing:
    if not os.path.isdir(root):
        print("no snapshots yet (%s)" % root)
        sys.exit(0)
    for name in sorted(os.listdir(root)):
        mf = os.path.join(root, name, "_snapshot.json")
        info = json.load(open(mf, encoding="utf-8")) if os.path.isfile(mf) else {}
        print("%-28s %s  %s" % (name, info.get("taken", "?"),
                                ", ".join(sorted(info.get("sections", {}))) or "?"))
    sys.exit(0)

if not ctx.args:
    _rp.die(__doc__)
name = ctx.args[0]
if not name.replace("-", "").replace("_", "").replace(".", "").isalnum():
    _rp.die("snapshot name must be letters, digits, - _ . : %r" % name)
secs = ctx.sections(ctx.args[1:])
d = os.path.join(root, name)
os.makedirs(d, exist_ok=True)
mf = os.path.join(d, "_snapshot.json")
info = json.load(open(mf, encoding="utf-8")) if os.path.isfile(mf) else {"sections": {}}
clash = [s.key for s in secs if os.path.isfile(ctx.snapshot_file(name, s.key))]
if clash and not force:
    _rp.die("snapshot %r already holds %s -- choose another name, or --force to replace"
            % (name, ", ".join(clash)))
for s in secs:
    text = s.text() + "\n"
    out = ctx.snapshot_file(name, s.key)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    info["sections"][s.key] = {"source": _rp.rel(s.path, ctx.ms.dir), "kind": s.kind,
                               "first": s.first, "last": s.last,
                               "md5": hashlib.md5(text.encode("utf-8")).hexdigest()}
    print("saved %-28s -> %s" % (s.key, _rp.rel(out, ctx.ms.dir)))
info["taken"] = time.strftime("%Y-%m-%d %H:%M:%S")
info["manuscript"] = ctx.ms.path
with open(mf, "w", encoding="utf-8") as fh:
    json.dump(info, fh, ensure_ascii=False, indent=1)
print("%d section(s) in snapshot %r" % (len(secs), name))
