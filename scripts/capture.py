#!/usr/bin/env python3
"""Capture a measurement script's stdout into a Tier-acceptance artifact.

The parents' register-measurements.md / cohesion-measurements.md are framed
captures of their measurement scripts' output. This does the mechanical part
for an instance: run the script, wrap stdout in a dated fenced block, write
the artifact.

RUN
    py -3 scripts/capture.py <instance> measure_register.py register-measurements.md
    py -3 scripts/capture.py <instance> build_cohesion_norms.py cohesion-measurements.md
"""
import datetime
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    inst, script, outname = sys.argv[1:4]
    inst = os.path.abspath(inst)
    spath = os.path.join(inst, "scripts", script)
    r = subprocess.run([sys.executable, "-B", spath], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if r.returncode != 0:
        sys.exit("%s failed:\n%s" % (script, r.stderr[-800:]))
    out = os.path.join(inst, "references", outname)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# %s — GENERATED capture (%s)\n\n" % (outname,
                 datetime.date.today().isoformat()))
        fh.write("> Captured from: py -3 scripts/%s — a Tier-1 acceptance"
                 " artifact.\n> Re-run this capture whenever the corpus"
                 " changes; the numbers below are\n> this instance's corpus"
                 " truth, superseding any parent illustration.\n\n" % script)
        fh.write("```\n" + r.stdout + "\n```\n")
    print("captured -> %s (%d lines)"
          % (os.path.relpath(out, inst), len(r.stdout.split("\n"))))


if __name__ == "__main__":
    main()
