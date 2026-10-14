#!/usr/bin/env python3
"""Tier 1, step 2: build the style layer and fill everything Tier 1 must fill,
so <field>-lit check_drift passes tiers 0-1 with no hand editing.

  1. capture.py: measure_register.py -> register-measurements.md and
     build_cohesion_norms.py -> cohesion-measurements.md (+ cohesion-norms.json);
     build_transitions.py -> transitions.md; the paragraph calibration
     (para-calibration.md) appended to register-measurements.md;
  2. registry: cohesion.{style_safe_papers, total_paragraphs, adjacent_pairs}
     from the norms JSON, transitions.{joins, papers_covered} from the
     transitions header;
  3. cohesion-canon.md: each of the 12 `corpus: TO-MEASURE (parent-econ
     verdict: ...)` slots replaced by this corpus's verdict and numbers with
     the parent verdict beside it; K10 and K11 become `corpus: UNMEASURED
     (judgment)` with the reason (K11's evidence needs Tier 2 slices); K12 is
     measured with the preview/recall phrase count. The header note says
     which numbers are this field's. The unfilled file is kept as
     cohesion-canon.parent.md, so a re-run (after a corpus change) refills;
  4. register.md: a note that this field's counts are in
     register-measurements.md, the counts printed in it being the parent's;
  5. Tier 1 added to both registries; lit check_drift run.

RUN
    py -3 scripts/tier1_fill.py <field> [--dest <skills dir>]
"""
import argparse
import json
import os
import re
import shutil
import sys

import _factory as F

PREVIEW = re.compile(r"\b(?:as (?:we|will be) (?:will )?(?:see|show|shown|discuss|discussed)|"
                     r"recall (?:from|that)|as (?:noted|discussed|shown|mentioned) "
                     r"(?:above|earlier|previously|in section)|see section|in section \d+,? we)\b", re.I)
SLOT = re.compile(r"`corpus: TO-MEASURE \(parent-econ verdict: (.*?)\)`", re.S)
EXPECT = ["MEASURED (57,271 pairs)", "confirmed", "confirmed", "confirmed",
          "confirmed, and the strict version refuted", "MEASURED", "confirmed as a norm",
          "confirmed by register practice", "gate confirmed necessary",
          "unmeasured (rare; judgment)", "confirmed as necessary by the D1", "confirmed"]


def pct(x):
    return "%.1f%%" % (100.0 * x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("field")
    ap.add_argument("--dest")
    a = ap.parse_args()
    fld = F.Field(a.field, a.dest).require()
    if 0 not in fld.built_tiers():
        F.die("Tier 0 is not accepted yet -- run tier0_accept.py first")
    ref = os.path.join(fld.lit, "references")
    cap = os.path.join(F.HERE, "capture.py")

    print("register measurements:")
    F.run([sys.executable, "-B", cap, fld.lit, "measure_register.py", "register-measurements.md"])
    print("cohesion norms:")
    F.run([sys.executable, "-B", cap, fld.lit, "build_cohesion_norms.py", "cohesion-measurements.md"])
    print("transitions:")
    fld.run("lit", "build_transitions.py", show=False)
    calib = os.path.join(ref, "para-calibration.md")
    if os.path.isfile(calib):
        with open(calib, encoding="utf-8") as fh:
            add = fh.read()
        with open(os.path.join(ref, "register-measurements.md"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n" + add)

    with open(os.path.join(ref, "cohesion-norms.json"), encoding="utf-8") as fh:
        norms = json.load(fh)
    cov, adj = norms["coverage"], norms["adjudications"]
    with open(os.path.join(ref, "transitions.md"), encoding="utf-8") as fh:
        th = re.search(r"(\d+) joins drawn from (\d+) papers", fh.read())
    if not th:
        F.die("transitions.md has no 'N joins drawn from M papers' header")
    N, P, J = cov["style_safe_papers"], cov["total_paragraphs"], adj["pairs_total"]
    if not J:
        F.die("cohesion norms recovered 0 adjacent pairs -- recalibrate para_min_chars")

    def fill(reg):
        reg["cohesion"].update(style_safe_papers=N, total_paragraphs=P, adjacent_pairs=J)
        reg["cohesion"]["_why_values"] = ("Tier 1 %s by tier1_fill.py: build_cohesion_norms over %d style-safe"
                                          " papers, para_min_chars %s" % (F.TODAY, N, norms["thresholds"]["para_min_chars"]))
        reg["transitions"].update(joins=int(th.group(1)), papers_covered=int(th.group(2)))
    fld.update_registry("lit", fill)

    # ---- the canon ------------------------------------------------------------
    canon = os.path.join(ref, "cohesion-canon.md")
    parent = os.path.join(ref, "cohesion-canon.parent.md")
    with open(canon, encoding="utf-8") as fh:
        text = fh.read()
    if SLOT.search(text):
        shutil.copyfile(canon, parent)
    elif os.path.isfile(parent):
        with open(parent, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = None
        print("cohesion-canon.md has no TO-MEASURE slot and no parent copy -- left as it is")
    if text is not None:
        text = fill_canon(fld, text, norms)
        with open(canon, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("cohesion-canon.md: 12 verdicts filled (unfilled copy: cohesion-canon.parent.md)")

    note_register(os.path.join(ref, "register.md"), N)
    fld.add_tier(1)
    r = fld.run("lit", "check_drift.py", check=False, show=False)
    print("\nbuilt tiers %s; check_drift: %s" % (fld.built_tiers(), "PASS" if r.returncode == 0 else "FAIL"))
    for l in r.stdout.splitlines():
        if "FAIL" in l:
            print("  " + l.strip())
    if r.returncode != 0:
        sys.exit(1)
    live_check(fld)


def fill_canon(fld, text, norms):
    adj, cells = norms["adjudications"], norms.get("cells", {})
    J = adj["pairs_total"]
    h = adj.get("join_grade_histogram", {})
    share = {g: h.get(g, 0) / float(J) for g in ("STRONG", "GOOD", "ACCEPTABLE", "WEAK", "BROKEN")}
    vis = 1 - share["BROKEN"]
    conn = (adj.get("connective_pairs") or 0) / float(J)
    earned = (adj.get("earned_vs_asserted") or {}).get("share")          # None: no connective pair
    d1 = (adj.get("antecedent_position_D1") or {}).get("share_stress_to_topic")   # None: no topic link
    m9 = {}
    for b in ("3-4", "5-6", "7-9", "10+"):
        s = cells.get("all|" + b, {}).get("summary", {}).get("m9_anaphoric_opener_rate")
        m9[b] = s
    meds = sorted({round(100 * s["median"]) for s in m9.values() if s and s.get("median") is not None})
    m9txt = " · ".join("%s: %s" % (b, "%d%%" % round(100 * s["p90"]) if s and s.get("p90") is not None
                                   else "n/a") for b, s in m9.items())
    hits, papers, nwords, ids = preview_counts(fld)
    mixed = d1 is not None and 0.2 < d1 < 0.8
    carrier = ("confirmed — %s of joins carry a mechanically visible carrier" % pct(vis)) if vis >= 0.5 else \
              ("not confirmed — only %s of joins carry a mechanically visible carrier" % pct(vis))
    no_d1 = "UNMEASURED (judgment) — no backward topic link was recovered in this corpus"
    new = [
        "MEASURED (%s pairs) — join grades STRONG %s · GOOD %s · ACCEPTABLE %s · WEAK %s · BROKEN %s;"
        " %s of joins carry a mechanically visible carrier" % (
            format(J, ","), pct(share["STRONG"]), pct(share["GOOD"]), pct(share["ACCEPTABLE"]),
            pct(share["WEAK"]), pct(share["BROKEN"]), pct(vis)),
        ("confirmed — %s of this corpus's adjacent pairs open with a connective" % pct(conn)) if conn > 0 else
        "UNMEASURED (judgment) — no connective-opened pair was recovered",
        carrier,
        carrier,
        no_d1 if d1 is None else
        ("confirmed, and the strict version refuted — %s of backward topic links come from the previous"
         " stress zone" % pct(d1)) if d1 < 0.5 else
        ("confirmed; the strict version holds for %s of backward topic links" % pct(d1)),
        "UNMEASURED (judgment) — no connective-opened join was recovered" if earned is None else
        "MEASURED — %s of connective-opened joins also carry a lexical link; a connective-only join is"
        " the %s minority" % (pct(earned), pct(1 - earned)),
        "confirmed as a norm — anaphoric openers: median %s and P90 by length bin %s of a paragraph's"
        " sentences; the checker reports the rate and the review resolves each antecedent"
        % ("/".join("%d%%" % m for m in meds) or "n/a", m9txt),
        "UNMEASURED (judgment) — elegant variation cannot be detected mechanically; detection is"
        " judgment plus attest.py on the suspect synonym",
        "UNMEASURED (judgment) — the gate's evidence is paragraph shape by chapter, which needs the"
        " Tier 2 slices" + ("" if d1 is None else "; corpus-wide, %s strict chaining (D1) shows %s" % (
            pct(d1), "both shapes in use" if mixed else "one shape dominating")),
        "MEASURED — preview/recall phrases occur %d times in %d of %d style-safe papers (%.2f per 10k"
        " words); a look-away is raised as a question, never asserted" % (
            hits, papers, len(ids), 10000.0 * hits / max(nwords, 1)),
        no_d1 if d1 is None else
        ("confirmed as necessary by the D1 measurement — %s strict chaining means the corpus mixes both"
         " shapes" % pct(d1)) if mixed else
        ("not confirmed — %s strict chaining: one paragraph shape dominates" % pct(d1)),
        carrier,
    ]
    slots = list(SLOT.finditer(text))
    if len(slots) != len(EXPECT) or not all(
            m.group(1).replace("\n", " ").startswith(e) for m, e in zip(slots, EXPECT)):
        F.die("cohesion-canon.md's TO-MEASURE slots are not the 12 this script knows (%d found):"
              " the template changed -- update tier1_fill.py" % len(slots))
    out, pos = [], 0
    for m, v in zip(slots, new):
        out.append(text[pos:m.start()])
        out.append("`corpus: %s; parent-econ: %s`" % (v, m.group(1)))
        pos = m.end()
    out.append(text[pos:])
    text = "".join(out)
    N = norms["coverage"]["style_safe_papers"]
    P = norms["coverage"]["total_paragraphs"]
    head = ("> **STAMPED-INSTANCE NOTE (%s).** The RULES are the cross-disciplinary\n"
            "> canon (Gopen & Swan, Williams, Pinker, Schimel, McCloskey, known-new\n"
            "> contract) and travel as-is. **Every `corpus:` verdict was measured at Tier 1\n"
            "> (%s, tier1_fill.py) on this instance's %d style-safe papers** (%s\n"
            "> recovered paragraphs, %s adjacent pairs), with the parent economics verdict\n"
            "> beside it as `parent-econ:`. Numbers in the running prose outside those\n"
            "> verdicts, including the **Corpus:** lines of the disagreements section, are\n"
            "> the PARENT corpus's (149 style-safe finance papers), kept for comparison.\n"
            "> Section-level cells (Results, Discussion, ...) arrive with the Tier 2 slices."
            % (fld.field, F.TODAY, N, format(P, ","), format(J, ",")))
    text, n = re.subn(r"> \*\*STAMPED-INSTANCE NOTE \(.*?mean exactly that\.", lambda m: head, text,
                      count=1, flags=re.S)
    if not n:
        print("  (canon header note not found; left as it is)")
    text = re.sub(r"\(149 style-safe papers, 9,821 recovered paragraphs,\s*\n> \*\*57,271 adjacent sentence pairs\*\*\)",
                  lambda m: "(%d style-safe papers, %s recovered paragraphs,\n> **%s adjacent sentence pairs**;"
                            " parent: 149 / 9,821 / 57,271)" % (N, format(P, ","), format(J, ",")), text, count=1)
    return text


def preview_counts(fld):
    sys.path.insert(0, os.path.join(fld.lit, "scripts"))
    import textseg
    ids = fld.style_safe_ids()
    hits = papers = nwords = 0
    for k in ids:
        with open(os.path.join(fld.lit, "references", "corpus", k + ".txt"), encoding="utf-8",
                  errors="replace") as fh:
            t = textseg.clean_prose(fh.read())
        h = len(PREVIEW.findall(t))
        hits += h
        papers += bool(h)
        nwords += len(t.split())
    return hits, papers, nwords, ids


MARK = "> **TIER 1 MEASURED"


def note_register(path, n):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    j = next((k for k, l in enumerate(lines) if l.startswith(MARK)), None)
    if j is not None:                       # a previous run's note: drop it whole
        e = j
        while e < len(lines) and lines[e].startswith(">"):
            e += 1
        del lines[j:e]
    note =["%s (%s).** This field's counts are in `register-measurements.md`" % (MARK, F.TODAY),
            "> (tier1_fill: %d style-safe papers). Every count printed below is the parent's" % n,
            "> illustration; where the two disagree, register-measurements.md wins."]
    # after the INSTANCE STATUS block (the first blockquote), else after the title
    i = next((k for k, l in enumerate(lines) if l.startswith("> **INSTANCE STATUS")), None)
    if i is not None:
        while i < len(lines) and lines[i].startswith(">"):
            i += 1
        lines[i:i] = [""] + note
    else:
        lines[1:1] = [""] + note
    txt = "\n".join(lines)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt)


def live_check(fld):
    cp = fld.cfgparse()
    mt = cp.as_str(fld.config().get("manuscript_tex"))
    print("\nLIVE CHECK: run /%s-lit on one manuscript paragraph and show the user its TERMS and"
          " REGISTER blocks." % fld.field)
    if not mt or not os.path.isfile(mt):
        return
    sys.path.insert(0, os.path.join(F.TEMPLATES, "polish", "scripts"))
    import manuscript as M
    ms = M.Manuscript(mt)
    for s in ms.sections:
        para = []
        for _, t in s.lines():
            if t.strip() and not t.lstrip().startswith("%"):
                para.append(t.strip())
            elif para:
                break
        body = " ".join(para)
        if body.count(". ") >= 2:
            print("  suggested: section %s, first paragraph:\n  %s" % (s.key, body[:900]))
            return


if __name__ == "__main__":
    main()
