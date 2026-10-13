#!/usr/bin/env python3
"""corpus-bootstrap factory self-test (added 2026-10-07).

Part 1 — unit checks for every 2026-10-07 fix, run against the TEMPLATE
scripts (no stamping needed).
Part 2 — integration: stamp a throwaway instance into a temp directory,
generate a 4-PDF fixture corpus with PLANTED defects, run Tier 0-1, and
assert each defect is caught:
    A  author-year paper: curly apostrophe "workers’ compensation", a phrase
       wrapped across a line, a reference list that also mentions the term
    B  numeric/superscript health paper: "reform.12,13 However, ..."
    C  image-only "scan" (no text layer)          -> must NOT be style-safe
    D  one-paragraph agency brief                  -> flagged SHORT
Exit 0 only if every check passes. Writes nothing outside the temp dir.

    py -3 tests/run_selftest.py [--keep]
"""
import glob
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY = os.path.dirname(HERE)
T_LIT = os.path.join(FACTORY, "templates", "lit", "scripts")
T_DRAFT = os.path.join(FACTORY, "templates", "draft")
PY = sys.executable

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print("  %s %-62s %s" % ("PASS" if ok else "FAIL", name, detail))


def fresh_import(name, path):
    if path not in sys.path:
        sys.path.insert(0, path)
    if name in sys.modules:
        del sys.modules[name]
    return importlib.import_module(name)


# ---------------------------------------------------------------- part 1
def unit_tests(tmp):
    print("part 1: unit checks against the templates")
    cp = fresh_import("_cfgparse", T_LIT)
    y = os.path.join(tmp, "cfg.yaml")
    with open(y, "w", encoding="utf-8") as fh:
        fh.write("a: [x, 'y, z', \"w\"]  # flow\n"
                 "b: 'Key\\s*words'  # comment\n"
                 "c:\n  - AGENCY2023  # report\n  - 'it''s'\n"
                 "d:\n# 中文注释\ne: plain # tail\n")
    d = cp.parse(y)
    check("config: quotes/comments/flow lists parsed",
          d == {"a": ["x", "y, z", "w"], "b": "Key\\s*words",
                "c": ["AGENCY2023", "it's"], "d": None, "e": "plain"}, str(d)[:60])
    check("config: quoted regex matches (a mathematics instance's dead markers)",
          re.search(d["b"], "Key words: workers' compensation") is not None)
    same = open(os.path.join(T_LIT, "_cfgparse.py"), encoding="utf-8").read() == \
        open(os.path.join(T_DRAFT, "pipeline", "_cfgparse.py"), encoding="utf-8").read()
    check("config: _cfgparse identical in lit and draft templates", same)

    ts = fresh_import("textseg", T_LIT)
    r = subprocess.run([PY, "-B", os.path.join(T_LIT, "textseg.py")],
                       capture_output=True, text=True)
    check("textseg built-in selftest", r.returncode == 0, r.stdout.strip()[:60])
    s = ts.split_sentences("Costs fell after the reform.12,13 However, use rose. "
                           "Claims declined.4 Moreover, denials grew.")
    check("superscript citations end sentences (4 sentences)", len(s) == 4, str(len(s)))
    check("decimal is not a citation ('0.05 The')",
          len(ts.split_sentences("The effect is significant at 0.05 The rest.")) == 1)
    c = ts.clean_prose("Body.\n" * 8 + "Table 2. Stats\nRESULTS\nTail body.\n"
                       "References\nSmith J. Workers compensation. 2019;12:3.")
    check("clean_prose drops captions, abstract labels, reference list",
          "Table 2" not in c and "RESULTS" not in c and "Smith J." not in c
          and "Tail body" in c)
    c2 = ts.clean_prose("Body.\n" * 8 + "RE F ER EN CES\nSmith J. Workers compensation. 2019;12:3.")
    check("clean_prose cuts a letter-spaced 'RE F ER EN CES' list", "Smith J." not in c2)
    col = "the workers in this sample were followed for %d months and"
    inter = "\n".join((col % i) + "\n" for i in range(150))              # mid-sentence line + blank
    normal = "\n".join((col % i) + ("." if i % 8 == 7 else "") + ("\n" if i % 8 == 7 else "")
                       for i in range(150))                              # blanks only after a stop
    caps = "\n".join("Analysis based on sample data provided by carriers %d\n" % i for i in range(150))
    ri, rn, rc = (ts.interleave_ratio(x)[0] for x in (inter, normal, caps))
    check("interleave_ratio: interleaved >= MIN; ordinary prose and captions+blank stay low",
          ri >= ts.INTERLEAVE_MIN and rn < 0.20 and rc < 0.20, "%.2f / %.2f / %.2f" % (ri, rn, rc))
    c3 = ts.clean_prose("Body.\n" * 20 + "References\nSmith J. 2019.\nTable 1. Stats\n"
                        "Appendix A\nAppendix prose stays here.")
    check("clean_prose cuts only the reference BLOCK (tables/appendix after it)",
          "Smith J." not in c3 and "Appendix prose stays here." in c3)
    ctrl = [os.path.relpath(p, FACTORY) for p in glob.glob(os.path.join(FACTORY, "templates", "**", "*.py"),
                                                             recursive=True)
            if any(ord(ch) < 32 and ch not in "\n\t\r" for ch in open(p, encoding="utf-8").read())]
    check("no control characters in any template script (a '\\b' became U+0008 twice)",
          not ctrl, ", ".join(ctrl))
    check("two-letter capital acronyms are content words",
          ts.stem("wc") in ts.content("WC claims rose"))

    sys.path.insert(0, os.path.join(T_DRAFT, "pipeline"))
    fs_src = open(os.path.join(T_DRAFT, "scripts", "_fieldstyle.py"),
                  encoding="utf-8").read()
    ay = re.search(r'AUTHOR_YEAR = \((.*?)\)\n', fs_src, re.S).group(1)
    num = re.search(r'NUMERIC = \((.*?)\)\n', fs_src, re.S).group(1)
    AY = re.compile(eval("(" + ay + ")"))
    NUM = re.compile(eval("(" + num + ")"))
    check("ownership: parenthetical author-year", bool(AY.search("(Smith and Jones, 2019)")))
    check("ownership: narrative author-year", bool(AY.search("Smith et al. (2019) show")))
    check("ownership: flattened superscript", bool(NUM.search("costs rose.12,13 However")))
    check("ownership: bracket numeric", bool(NUM.search("as shown [3, 5-7].")))
    check("ownership: 'COVID-19' is not a citation", not NUM.search("COVID-19 claims"))

    at = fresh_import("attest", T_LIT)
    fam = lambda term: [p for p, lab in at.variants(term) if lab.startswith("suffix")]
    need = fam("clinical need")
    check("attest: 'clinical need' gets no suffix family (was 'clinical ne' -> Neuropsychologist)",
          not need and not any(re.search(p, "Clinical Neuropsychologist", re.I)
                               for p, _ in at.variants("clinical need")), str(need))
    check("attest: short last-word stems refused, real ones kept",
          not fam("funding rates") and fam("medical bills") and fam("monotonically")
          and not fam("costs"), "")

    ms = open(os.path.join(T_DRAFT, "scripts", "measure_structure.py"),
              encoding="utf-8").read()
    check("measure_structure: no control characters",
          not any(ord(ch) < 32 and ch not in "\n\t" for ch in ms))
    eq = re.search(r'EQ_LABEL = re\.compile\((r".*?")\)\n', ms).group(1)
    EQ = re.compile(eval(eq))
    check("equation proxy ignores '(2019)', keeps '(2.4)'",
          not EQ.findall("Smith (2019) and (2019a)") and EQ.findall("in (2.4)") == ["2.4"])

    a1 = open(os.path.join(T_DRAFT, "pipeline", "a1_headings.py"), encoding="utf-8").read()
    gs = re.search(r"GENERIC_SECTION = re\.compile\(\n(.*?), re\.I\)", a1, re.S).group(1)
    G = re.compile(eval("(" + gs + ")"), re.I)
    check("IMRaD: 'Methods', 'Results', 'Study population and data' recognised",
          all(G.match(x) for x in ("Methods", "RESULTS", "Study population and data"))
          and not G.match("We find that"))

    mv = fresh_import("measure_verbs", os.path.join(T_DRAFT, "scripts"))
    ctx = [mv.context(x) for x in ("the number of ", "these ", "we ", "Smith (2019) ",
                                   "jones et al.12 ", "costs.12,13 ", "medical ",
                                   "workers' compensation ")]
    check("verb ladder: noun/verb context cues ('medical ' is no citation cue)",
          ctx == ["noun", "noun", "verb", "verb", "verb", "verb", None, None], str(ctx))
    qm = re.search(r'Q_MARKERS = re\.compile\(\n(.*?), re\.I\)', ms, re.S).group(1)
    Q = re.compile(eval("(" + qm + ")"), re.I)
    flat = lambda s: re.sub(r"\s+", " ", s)
    aims = ["Therefore, the purpose of this\nstudy was to review the literature",
            "The current study aimed to determine the factors",
            "This population-based cohort study evaluates utilization",
            "Study objectives were to: (1) describe",
            "In this paper, we ask whether"]
    check("structure layer B: IMRaD aim statements are question markers (after unwrap)",
          all(Q.search(flat(a)) for a in aims) and not Q.search("Costs rose after 2010."),
          str([bool(Q.search(flat(a))) for a in aims]))
    check("verb ladder: HOMOGRAPH needs both share and count",
          mv.homograph(92, 8) and not mv.homograph(6, 6) and not mv.homograph(40, 60))


# ---------------------------------------------------------------- part 2
# Every fixture contains "fi" words: synthetic text with none would trip the
# ligature-damage test (>2000 words, zero fi) -- real papers never lack them.
# PDF fixtures use the Base-14 Helvetica font, which cannot encode U+2019: the
# curly-apostrophe case is tested with a .txt fixture (E) ingested through the
# --map copied-text path -- the same path entries without a PDF use.
_PARA_A = ("Prior work studies how insurers manage medical care after a work injury "
           "(Smith and Jones, 2019). However, medical spending rises with benefit "
           "generosity. Moreover, the effect is larger for back injuries. Thus the "
           "design of the benefit schedule matters for costs. ")
_PARA_R = ("Results show that utilization increases after the reform. Consistent with "
           "prior evidence, costs rise in the treated states. The estimate is precise "
           "and stable across specifications. ")
FIX_A = ("Introduction\n\n" + _PARA_A * 30 + "\n\nResults\n\n" + _PARA_R * 40
         + "\n\nReferences\n\nSmith A, Jones B (2019) Workers' compensation and medical"
         " care. J Health Econ 12:3-4.\n")
_PARA_B = ("Medical costs fell after the reform.12,13 However, utilization rose in "
           "some groups of injured workers.4 Moreover, denial rates increased in the "
           "second year.5 Treatment delays were common among older claimants, the "
           "first finding.6 ")
FIX_B = ("Background\n\n" + _PARA_B * 35 + "\n\nMethods\n\n"
         + ("We linked claims to medical bills from the state agency.7 The sample "
            "included injured workers with accepted claims. Outcomes were measured "
            "at 12 months after the injury. ") * 35
         + "\n\nReferences\n\n1. Lee K. Workers compensation reform. AJIM. 2019;12:3-4.\n")
FIX_D = "Agency brief. Workers compensation medical benefits grew 2.3% in 2024.\n"
FIX_E = ("Workers’ compensation insurers pay for medical care after a work injury, "
         "and the workers’ compensation\nsystem shifts costs when claims are denied; "
         "we find significant effects. "
         * 120 + "\n\nReferences\n\nDoe J. Workers’ compensation costs. AJIM. 2020.\n")


def make_pdf(path, text, scan=False):
    import fitz
    doc = fitz.open()
    pages = [text[i:i + 2200] for i in range(0, len(text), 2200)] or [""]
    for chunk in pages:
        page = doc.new_page()
        if scan:
            page.draw_rect(fitz.Rect(50, 50, 500, 700), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
        else:
            page.insert_textbox(fitz.Rect(50, 50, 550, 800), chunk, fontsize=9,
                                fontname="helv")
    if scan:
        for _ in range(3):
            p = doc.new_page()
            p.draw_rect(fitz.Rect(50, 50, 500, 700), color=(0, 0, 0), fill=(0.7, 0.7, 0.7))
    doc.save(path)


def run(args, **kw):
    r = subprocess.run([PY, "-B"] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    return r.returncode, r.stdout + r.stderr


def integration(tmp):
    print("\npart 2: stamp -> Tier 0-1 on a fixture corpus with planted defects")
    skills = os.path.join(tmp, "skills")
    os.makedirs(skills)
    rc, out = run([os.path.join(FACTORY, "scripts", "stamp.py"), "fixture",
                   "--citation-style", "mixed", "--keywords", "workers' compensation",
                   "--dest", skills])
    check("stamp into a foreign --dest", rc == 0, out.strip().splitlines()[0][:50] if out else "")
    lit = os.path.join(skills, "fixture-lit")
    draft = os.path.join(skills, "fixture-draft")

    a1 = fresh_import("a1_headings", os.path.join(draft, "pipeline"))
    body = "This sentence is ordinary running prose and it ends with a period."
    fx = ["A Title", "", "1 | INTRODUCTION", body, "", "2 | M E TH O D S", body, "",
          "M ETHODS", "In-Depth Interviews", body, "",
          "Part I: Group Health and Employer Insurance: Parallel Health Care Reimbursement",
          body, "", "DATA AND METHODS", body, "", "3", "| RESULTS", body,
          "", "V Survey Evidence", body, "", "5", "", "Estimation", "", body,
          "", "Description of the Plan Members’", body,
          "", "I was told that the program changed", body,
          "", "30.9", "Male", "41 008"]
    got = {c["line"]: c["verbatim"] for c in a1.extract(fx)[0]}
    check("A1: 'V Survey Evidence' (roman, no period); 'I was told ...' is not a heading",
          got.get(23) == "V Survey Evidence" and 35 not in got, "%s / %s" % (got.get(23), got.get(35)))
    check("A1: '5' / '' / 'Estimation' / '' -> '5 Estimation'; table cell '30.9' / 'Male' is not",
          got.get(28) == "5 Estimation" and 39 not in got, "%s / %s" % (got.get(28), got.get(39)))
    check("A1: curly apostrophe in a bare heading", got.get(32, "").startswith("Description of"),
          str(got.get(32)))

    # stage_b_slice.front_end on four real layouts (a copy of the draft with a
    # taxonomy, so the slicer can be imported; _jobs must be re-imported there)
    d2 = os.path.join(skills, "fixture-draft-slice")
    shutil.copytree(draft, d2)
    p = os.path.join(d2, "references", "field-config.yaml")
    t = open(p, encoding="utf-8").read()
    t = t.replace("\njobs:\n", "\njobs:\n  - abstract\n  - introduction\n  - methods\n", 1)
    t = t.replace("\npositional_jobs:\n", "\npositional_jobs:\n  - abstract\n  - introduction\n", 1)
    t = t.replace("\nabstract_end_markers:\n", "\nabstract_end_markers:\n"
                  + r"  - '^\s*key\s*words?\b'" + "\n" + r"  - '^\s*\S+@\S+\.[a-z]{2,}\s*$'" + "\n"
                  + r"  - '^\s*this\s+is\s+an\s+open[- ]access\s+article'" + "\n", 1)
    open(p, "w", encoding="utf-8").write(t)
    for mod in ("_jobs", "_cfgparse"):
        sys.modules.pop(mod, None)
    sb = fresh_import("stage_b_slice", os.path.join(d2, "pipeline"))
    sent = "The injured workers in this cohort had longer claims than expected and"
    p79 = ["Background: " + sent] + [sent] * 9 + ["", "T", "", "he Academy produces estimates", sent]
    p26 = ["Abstract Purpose " + sent] + [sent] * 5 + ["J. Q. Public", "Example State University",
           "", "costs were modeled using linear regression. Results " + sent, sent,
           "Keywords Injury severity", "Introduction"]
    para = "Injured workers were more likely than noninjured workers to be treated. " * 4
    p70 = ["Abstract", "Objectives", sent, "Results", sent, "Conclusions", para, "Occupational " + para]
    p69 = ["Abstract", "Objectives", sent * 3, "Results", sent * 3, "Conclusions", "", para, "Intro " + para]
    ends = (sb.front_end(p79, 1, len(p79)), sb.front_end(p26, 1, len(p26)),
            sb.front_end(p70, 1, len(p70)), sb.front_end(p69, 1, len(p69)))
    check("slicer: abstract ends before the drop-cap intro (P79), runs through an affiliation "
          "break to Keywords (P26), ends after the Conclusions paragraph (P70, P69)",
          ends == (10, 11, 7, 8), str(ends))
    p02 = (["Abstract Purpose " + sent] + [sent] * 5
           + ["& Pat B. Author", "pat.author@example.edu", "1", "",
              "Institute for Example Studies, Springfield", "",
              "and claim related factors were supported by some evidence.", "Keywords Disability"])
    p69b = ["Abstract", "Objectives:", "", sent * 3, "", "Results:", "", sent * 3, "",
            "Conclusions:", "", para, "", "Intro " + para]
    nber = (["ABSTRACT", ""] + [sent] * 6 + ["", "Alex Example", "Department of Economics",
            "and NBER", "alex.example@example.edu", "", "Public insurance programs are widespread.",
            "insurance programs are ubiquitous in most developed economies today"])
    ends2 = (sb.front_end(p02, 1, len(p02)), sb.front_end(p69b, 1, len(p69b)),
             sb.front_end(nber, 1, len(nber)))
    check("slicer: e-mail interruption resumes to Keywords (P02); label+blank waits for its "
          "paragraph (P69); NBER abstract stops before the author block",
          ends2 == (13, 12, 8), str(ends2))
    two = sent + " " + sent
    p08 = ["Abstract", "Objective—" + two, two, "Results—" + two, "The increases were highest.",
           "", "Author Manuscript", "", "Conclusion—Our estimates showed that low-cost claims could cost the",
           "program $150 million per year.",
           "Occupational injuries impose high costs on the US health care system and the burden falls",
           "on employers and workers alike in every state of the country today"]
    e08 = sb.front_end(p08, 1, len(p08))
    check("slicer: PMC 'Author Manuscript' break + run-in Conclusion paragraph, no Keywords (P08)",
          e08 == 10, str(e08))
    p40 = ["Abstract", "Objectives—" + two + " " + two, two, "", "Author Manuscript", "",
           "Corresponding author: Jane Doe, Example State University, Springfield.",
           "Author contributions: all authors designed the study.", "",
           "Methods—" + two, two + ".", "Results—" + two, two + ".",
           "Conclusions—Injuries severe enough to need time off raise the risk.", "",
           "Opioid deaths rose sharply in the United States over the past two decades and"]
    p05 = ["Objective: " + two, two, two, "", "W", "",
           "orkers' compensation claims rose sharply in many states over the last decade and", two,
           "This is an open-access article distributed under the terms of the license.", two]
    ends3 = (sb.front_end(p40, 1, len(p40)), sb.front_end(p05, 1, len(p05)))
    check("slicer: PMC footnote block inside the abstract resumes at `Methods—` (P40); the "
          "open-access footnote never extends an abstract into a drop-cap intro (P05)",
          ends3 == (14, 3), str(ends3))
    blk = sb.blocks_for("X", p02 + ["Background", sent], {"X": {"candidates": [],
                        "ref_cutoff": len(p02) + 2}}, {}).get("abstract")
    check("slicer: a positional abstract is not re-trimmed short (P02 fell back to L36)",
          bool(blk) and blk[0][1] == 13, str(blk and [(s, e) for s, e, _ in blk]))

    # Tier 3 verifiers on the fixture copy: a quote that spans a PDF line wrap
    # must verify; a paraphrased one must not.
    sl = os.path.join(d2, "references", "slices", "introduction")
    os.makedirs(sl, exist_ok=True)
    open(os.path.join(sl, "P01.txt"), "w", encoding="utf-8").write(
        "===== P01 | L10-20 | Introduction\nWorkers' compensation insurance pays for the medi-\n"
        "cal care of injured workers in every state.\nSecond paragraph here.\n")
    sh = os.path.join(d2, "references", "records", "_shards")
    os.makedirs(sh, exist_ok=True)
    open(os.path.join(sh, "introduction-01.md"), "w", encoding="utf-8").write(
        "### P01  introduction 1 paragraphs [titled `Introduction`]\n\n¶1 opens on what WC pays for\n"
        "> \"Workers' compensation insurance pays for the medi- cal care of injured workers in every state.\"\n"
        "1 sentences\n")
    rc, out = run([os.path.join(d2, "pipeline", "verify_shards.py")])
    check("verify_shards: a quote spanning a line wrap verifies (fingerprint match)",
          rc == 0 and "ok" in out, out.strip().splitlines()[0][:60] if out else "")
    sec = os.path.join(d2, "references", "sections", "introduction")
    os.makedirs(sec, exist_ok=True)
    good = ('### Version 1 · Name the payer\nPattern        `<x>`\n'
            'Example        "Workers\' compensation insurance pays for the medi- cal care of injured\n'
            '               workers in every state."   — P01 ¶1\n'
            'Use it when    a\nNot this when  b\n')
    open(os.path.join(sec, "introduction.md"), "w", encoding="utf-8").write(good)
    rc1, out1 = run([os.path.join(d2, "pipeline", "verify_versions.py")])
    open(os.path.join(sec, "introduction.md"), "w", encoding="utf-8").write(
        good.replace("pays for the medi- cal care of", "covers the medical treatment of"))
    rc2, out2 = run([os.path.join(d2, "pipeline", "verify_versions.py")])
    check("verify_versions: verbatim Example passes, a paraphrased one is MISSING",
          rc1 == 0 and rc2 == 1 and "MISSING" in out2, "%s / %s" % (rc1, rc2))
    check("A1: PyMuPDF layout '3' then '| RESULTS' -> '3 RESULTS'",
          got.get(20) == "3 RESULTS", str(got.get(20)))
    check("A1: Wiley '1 | INTRODUCTION' numbering", got.get(3) == "1 INTRODUCTION", str(got.get(3)))
    check("A1: letter-spaced caps collapse ('M E TH O D S', 'M ETHODS')",
          got.get(6) == "2 METHODS" and got.get(9) == "METHODS", "%s / %s" % (got.get(6), got.get(9)))
    check("A1: 'Part I: <11-word title>' is a chapter",
          str(got.get(13, "")).startswith("Part I Group Health"), str(got.get(13)))
    check("A1: 'DATA AND METHODS' not collapsed", got.get(16) == "DATA AND METHODS", str(got.get(16)))
    sk = open(os.path.join(lit, "SKILL.md"), encoding="utf-8").read()
    check("no unstamped tokens in lit SKILL.md", "{{" not in sk)
    check("keywords stamped into the description", "workers' compensation" in sk.split("\n")[2])
    cfg = open(os.path.join(draft, "references", "field-config.yaml"), encoding="utf-8").read()
    check("canon_dir stamped as an absolute path",
          re.search(r"^canon_dir: \S+canon-sources", cfg, re.M) is not None)
    check("prompts carry their format examples",
          os.path.exists(os.path.join(draft, "prompts", "examples",
                                      "pass2-example-introduction-04-design.md")))

    lib = os.path.join(tmp, "library", "sub")
    os.makedirs(lib)
    for name, text, scan in (("A", FIX_A, False), ("B", FIX_B, False),
                             ("C", "", True), ("D", FIX_D, False)):
        make_pdf(os.path.join(lib, name + ".pdf"), text, scan)
    with open(os.path.join(lib, "E.txt"), "w", encoding="utf-8") as fh:
        fh.write(FIX_E)
    mp = os.path.join(tmp, "keys.csv")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write("key,path,group,role\n")
        for k, f, g, r in (("P01", "A.pdf", "econ", "research"),
                           ("P02", "B.pdf", "health", "research"),
                           ("P03", "C.pdf", "health", "scan"),
                           ("R01", "D.pdf", "report", "report"),
                           ("P04", "E.txt", "health", "research")):
            fh.write("%s,%s,%s,%s\n" % (k, os.path.join(lib, f), g, r))
    rc, out = run([os.path.join(FACTORY, "scripts", "ingest.py"), lit, "--map", mp])
    check("ingest from a library folder via --map", rc == 0, "")
    src = json.load(open(os.path.join(lit, "references", "corpus_sources.json"), encoding="utf-8"))
    check("planted scan flagged SCAN", "SCAN" in src["P03"].get("flags", []),
          str(src["P03"].get("flags")))
    check("planted brief flagged SHORT", "SHORT" in src["R01"].get("flags", []))
    check("converter + version recorded", bool(src["P01"].get("converter_version")))
    rc, out = run([os.path.join(FACTORY, "scripts", "ingest.py"), lit, "--map", mp,
                   "--force", "P01", "--converter", "pymupdf"])
    src = json.load(open(os.path.join(lit, "references", "corpus_sources.json"), encoding="utf-8"))
    check("ingest --force KEY --converter pymupdf re-extracts one paper",
          rc == 0 and src["P01"].get("converter") == "pymupdf"
          and src["P02"].get("converter") == "pdftotext", out.strip()[-60:])
    # terminology_only for the report, written into BOTH configs
    for inst in (lit, draft):
        p = os.path.join(inst, "references", "field-config.yaml")
        t = open(p, encoding="utf-8").read().replace(
            "terminology_only:\n", "terminology_only:\n  - R01   # agency brief\n")
        open(p, "w", encoding="utf-8").write(t)
    rc, out = run([os.path.join(lit, "scripts", "build_corpus_meta.py")])
    check("build_corpus_meta runs", rc == 0, out.strip().splitlines()[-1][:50] if out else "")
    meta = open(os.path.join(lit, "references", "corpus_meta.yaml"), encoding="utf-8").read()
    blk = lambda k: re.search(r"- id: %s\n(.*?)(?=\n  - id:|\Z)" % k, meta, re.S).group(1)
    check("scan is NOT style-safe (was 'clean' before 2026-10-07)",
          "style_safe: false" in blk("P03") and "scan_or_empty" in blk("P03"))
    check("commented terminology_only key honoured",
          "role: terminology_reference" in blk("R01") and "style_safe: false" in blk("R01"))
    check("per-paper citation culture recorded",
          "citation_style: author-year" in blk("P01") and "citation_style: numeric" in blk("P02"),
          "")
    check("copied-text entry ingested (no-PDF path)",
          src.get("P04", {}).get("converter") == "copied-text")
    rc, out = run([os.path.join(lit, "scripts", "attest.py"), "--json", "workers' compensation"])
    a = json.loads(out[out.find("["):]) if "[" in out else [{}]
    check("attest: straight apostrophe finds curly + wrapped phrase (240 in E)",
          a[0].get("per_paper", {}).get("P04", 0) == 240,
          "P04 hits=%s" % a[0].get("per_paper", {}).get("P04"))
    rc, out2 = run([os.path.join(lit, "scripts", "attest.py"), "--json", "--include-refs",
                    "workers' compensation"])
    b = json.loads(out2[out2.find("["):]) if "[" in out2 else [{}]
    check("attest: reference-list hits excluded by default",
          b[0].get("hits", 0) > a[0].get("hits", 0),
          "%s vs %s" % (a[0].get("hits"), b[0].get("hits")))
    for script, art in (("measure_register.py", "register-measurements.md"),
                        ("build_cohesion_norms.py", "cohesion-measurements.md")):
        rc, out = run([os.path.join(FACTORY, "scripts", "capture.py"), lit, script, art])
        check("Tier 1: %s runs" % script, rc == 0, out.strip()[-50:])
    rc, out = run([os.path.join(lit, "scripts", "build_transitions.py")])
    check("Tier 1: build_transitions runs", rc == 0)
    norms = json.load(open(os.path.join(lit, "references", "cohesion-norms.json"), encoding="utf-8"))
    check("norms record the configured paragraph threshold",
          norms["thresholds"]["para_min_chars"] == 150)
    # check_drift: built_tiers=[0] with null registry -> must FAIL (null is not a pass)
    reg_p = os.path.join(lit, "references", "registry.json")
    reg = json.load(open(reg_p, encoding="utf-8"))
    reg["built_tiers"] = [0]
    json.dump(reg, open(reg_p, "w", encoding="utf-8"), indent=1)
    rc, out = run([os.path.join(lit, "scripts", "check_drift.py")])
    check("check_drift FAILS while tier-0 registry values are null", rc != 0)
    m = re.search(r"files: (\d+).*?distinct: (\d+).*?terminology_safe: (\d+).*?style_safe: (\d+)",
                  meta, re.S)
    reg["corpus"].update(files=int(m.group(1)), distinct=int(m.group(2)),
                         terminology_safe=int(m.group(3)), style_safe=int(m.group(4)))
    json.dump(reg, open(reg_p, "w", encoding="utf-8"), indent=1)
    rc, out = run([os.path.join(lit, "scripts", "check_drift.py")])
    check("check_drift tier 0 green once filled", rc == 0,
          out.strip().splitlines()[-1][:50])
    rc, out = run([os.path.join(draft, "scripts", "check_drift.py")])
    check("draft check_drift skeleton green", rc == 0, out.strip().splitlines()[-1][:50])
    rc, out = run([os.path.join(FACTORY, "scripts", "tier_status.py"), "fixture", "--dest", skills])
    check("tier_status with --dest", rc == 0 and "NEXT" in out)


def main():
    keep = "--keep" in sys.argv
    tmp = tempfile.mkdtemp(prefix="cb-selftest-")
    try:
        # a crash is a FAIL, never an abort -- run against an OLD factory the
        # suite must still report every check it can (qualification run)
        for part in (unit_tests, integration):
            try:
                part(tmp)
            except Exception as e:  # noqa: BLE001
                check("%s completed without crashing" % part.__name__, False,
                      "%s: %s" % (type(e).__name__, str(e)[:60]))
    finally:
        if keep:
            print("\nkept: " + tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    n_fail = sum(1 for _, ok in results if not ok)
    print("\n%d checks, %d failed" % (len(results), n_fail))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
