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


# ---------------------------------------------------------------- part 3
# One-step onboarding and <field>-polish (1.2.0). A library of six research
# PDFs, an agency brief, a scan and a missing paper; a .bib whose entries
# reach their PDFs by every matching rule; reading notes; a manuscript that
# \input's two sections. Onboarding runs Tier 0-1 with no hand editing, then
# every polish script runs on the manuscript.
_ADJ = ["detailed", "regional", "national", "careful", "longitudinal", "matched", "pooled",
        "quarterly", "annual", "broad", "narrow", "simple"]
_TOPIC = ["medical spending", "claim duration", "return to work", "benefit generosity",
          "provider payment", "treatment delay", "claim denial", "insurer behaviour",
          "fee schedules", "wage replacement", "case management", "utilization review"]
_ORD = ["first", "second", "third", "fourth", "fifth"]


def _paper(seed, lead="", hyphen=False):
    """~1,900 words in 28 four-sentence paragraphs; distinct per seed; 'fi'
    words throughout (the ligature-damage test needs them)."""
    paras = [lead] if lead else []
    for i in range(28):
        a, t = _ADJ[(seed + i) % 12], _TOPIC[(seed * 5 + i) % 12]
        t2 = _TOPIC[(seed + 3 * i + 1) % 12]
        s = ["The %s analysis of %s finds significant effects in the %s year of the panel."
             % (a, t, _ORD[i % 5]),
             "These effects on %s are larger for back injuries than for fractures in state %d."
             % (t, seed * 31 + i),
             "Workers with longer claims file more appeals, and the %s pattern holds for %s."
             % (_ORD[(i + seed) % 5], t2),
             "Our estimate for %s is stable across the %s specifications we fit to sample %d."
             % (t2, a, i + seed)]
        if hyphen and i == 3:
            s[1] = "The occupa-\ntional injury rate rose in the %s year of the study." % _ORD[i % 5]
        paras.append(" ".join(s))
    return "\n\n".join(paras) + "\n\nReferences\n\nAuthor A (2001) A title. J Econ 1:2-3.\n"


_BIB3 = r"""@article{Smith2019,
  author = {Smith, Ann},
  title = {Injury and spending},
  year = {2019},
  journal = {J Health Econ}
}
@article{Lee2020,
  author = {Lee, Kim and Park, Joon},
  title = {Reform effects on utilization},
  year = 2020
}
@article{Garcia2018,
  author = {Garcia, Luis and Lopez, Ana and Diaz, Rosa},
  title = {Medical Spending After Workplace Injuries},
  year = {2018}
}
@article{Brown2015,
  author = {Brown, Ed},
  title = {Claims and courts},
  year = {2015},
  doi = {10.5555/brown.2015.7}
}
@techreport{Agency2021,
  author = {{State Agency}},
  title = {Medical benefits brief},
  year = {2021},
  file = {:pdfs/Agency2021.pdf:PDF}
}
@article{Scan2017,
  author = {Old, Pat},
  title = {Scanned paper},
  year = {2017},
  file = {Full Text:pdfs/Scan2017.pdf:application/pdf}
}
@article{Note2016,
  author = {Noted, Ida},
  title = {Spending after reform},
  year = {2016}
}
@article{Wu:2019,
  author = {Wu, Li},
  title = {Payment rules},
  year = {2019},
  file = {pdfs/Wu2019.pdf}
}
@article{Missing2000,
  author = {Gone, Al},
  title = {A paper nobody has},
  year = {2000}
}
"""
_INTRO3 = r"""% section header comment
Prior work studies medical care after workplace injuries \citep{Smith2019,Lee2020}. However, costs rise with benefit generosity \citep{Garcia2018}. The authors argue that claim duration matters for costs \citep{Brown2015}. Spending fell, a difference attributed to fee schedules \citep{Wu:2019}.

\citet{Smith2019} find that the occupational injury rate rose by 12 percent. % Smith2019 p.3
The agency reports that spending grew 2.3 percent \citepalias{Agency2021}. % Agency2021 p.1
"""
_RES3 = r"""% results
Spending rose after the reform \citep{Note2016,Scan2017}. The authors argue that this pattern is general \citep{Missing2000}. We find similar effects in every state.
"""
_MAIN3 = r"""\documentclass{article}
\usepackage{natbib}
\defcitealias{Agency2021}{State Agency, 2021}
\begin{document}
\section{Introduction}\label{sec:intro}
\input{sections/intro}
\section{Results}\label{sec:results}
\input{sections/results}
\bibliographystyle{plainnat}
\bibliography{refs}
\end{document}
"""
_BBL3 = r"""\begin{thebibliography}{9}
\bibitem[Smith(2019)]{Smith2019}
Smith.
\bibitem[Lee and Park(2020)]{Lee2020}
Lee.
\bibitem[Garcia et~al.(2018)Garcia, Lopez, and Diaz]{Garcia2018}
Garcia.
\bibitem[Brown(2015)]{Brown2015}
Brown.
\bibitem[{State Agency}(2021)]{Agency2021}
Agency.
\bibitem[Old(2017)]{Scan2017}
Old.
\bibitem[Noted(2016)]{Note2016}
Noted.
\bibitem[Wu(2019)]{Wu:2019}
Wu.
\bibitem[Gone(2000)]{Missing2000}
Gone.
\end{thebibliography}
"""


def onboard_polish(tmp):
    print("\npart 3: one-step onboarding -> Tier 0-1 -> every <field>-polish script")
    sc = os.path.join(FACTORY, "scripts")
    root = os.path.join(tmp, "p3")
    lib, other, notes = (os.path.join(root, "library", "pdfs"), os.path.join(root, "library", "other"),
                         os.path.join(root, "notes"))
    ms_dir = os.path.join(root, "paper")
    skills = os.path.join(root, "skills")
    for d in (lib, other, notes, os.path.join(ms_dir, "sections"), skills):
        os.makedirs(d)
    make_pdf(os.path.join(lib, "Smith2019.pdf"), _paper(1, hyphen=True))
    make_pdf(os.path.join(lib, "lee_2020_reform.pdf"), _paper(2))
    make_pdf(os.path.join(lib, "paper3.pdf"), _paper(3, lead="Medical Spending After Workplace Injuries"))
    make_pdf(os.path.join(lib, "download (1).pdf"), _paper(4, lead="https://doi.org/10.5555/brown.2015.7"))
    make_pdf(os.path.join(lib, "Agency2021.pdf"), FIX_D)
    make_pdf(os.path.join(lib, "Scan2017.pdf"), "", scan=True)
    make_pdf(os.path.join(lib, "Wu2019.pdf"), _paper(6))
    make_pdf(os.path.join(other, "n16.pdf"), _paper(5))
    with open(os.path.join(notes, "Note2016.md"), "w", encoding="utf-8") as fh:
        fh.write("---\n对应PDF: ../library/other/n16.pdf\n---\n"
                 "- \"medical spending rose sharply after the reform\" (p.4)\n")
    with open(os.path.join(root, "library", "refs.bib"), "w", encoding="utf-8") as fh:
        fh.write(_BIB3)
    shutil.copy(os.path.join(root, "library", "refs.bib"), os.path.join(ms_dir, "refs.bib"))
    for name, text in (("main.tex", _MAIN3), ("sections/intro.tex", _INTRO3),
                       ("sections/results.tex", _RES3)):
        with open(os.path.join(ms_dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)
    main_tex = os.path.join(ms_dir, "main.tex")

    ob = fresh_import("onboard", sc)
    ck = ob.corpus_keys({"abc", "ABC", "Wu:2019"})
    check("onboard: corpus keys sanitised and unique ignoring case",
          ck["Wu:2019"] == "Wu_2019" and ck["abc"].lower() != ck["ABC"].lower(), str(ck))
    e = {"fields": {"file": r":C\:\\lib\\x.pdf:PDF;Supp:sub/s.pdf:application/pdf"}, "bib": "/b/refs.bib"}
    fs = [p.replace("\\", "/") for p in ob.bib_files(e)]
    check("onboard: JabRef escaped drive + Zotero relative file fields parsed",
          len(fs) == 2 and fs[0].lower().startswith("c:") and fs[1].endswith("sub/s.pdf"), str(fs))

    lib_bib = os.path.join(root, "library", "refs.bib")
    base = [os.path.join(sc, "onboard.py"), "--manuscript", main_tex, "--library", lib,
            "--library", lib_bib, "--notes", notes, "--dest", skills]
    rc, out = run(base + ["--dry-run"])
    idx = json.load(open(os.path.join(ms_dir, ".polish", "library-index.json"), encoding="utf-8"))["keys"]
    meth = {k: v["method"] for k, v in idx.items()}
    want = {"Smith2019": "filename", "Lee2020": "author-year", "Garcia2018": "title",
            "Brown2015": "doi", "Agency2021": "bib-file", "Scan2017": "bib-file",
            "Note2016": "note", "Wu:2019": "bib-file", "Missing2000": "unmatched"}
    check("onboard --dry-run: every matching rule hit as planted (9 keys)", rc == 0 and meth == want,
          str({k: v for k, v in meth.items() if want.get(k) != v}))
    check("onboard --dry-run: stamps nothing", not os.listdir(skills))
    rc, out = run(base)
    check("onboard without --field asks for a name (exit 3)", rc == 3 and "--field" in out, str(rc))
    rc, out = run(base + ["--field", "fx3"])
    check("onboard for a new field asks for keywords (exit 3)", rc == 3, str(rc))
    rc, out = run(base + ["--field", "fx3", "--keywords", "workplace injury"])
    lit, draft, pol = (os.path.join(skills, "fx3-" + s) for s in ("lit", "draft", "polish"))
    check("onboard stamps lit, draft and polish and ingests the matched PDFs",
          rc == 0 and os.path.isdir(pol) and os.path.isfile(os.path.join(lit, "references", "corpus", "Wu_2019.txt"))
          and os.path.isfile(os.path.join(lit, "references", "corpus_meta.yaml")), out.strip()[-80:])
    inst = json.load(open(os.path.join(pol, "references", "instance.json"), encoding="utf-8"))
    check("polish instance.json names its siblings", inst.get("lit_dir") == "../fx3-lit", str(inst))
    psk = open(os.path.join(pol, "SKILL.md"), encoding="utf-8").read()
    left = [f for f in glob.glob(os.path.join(pol, "**", "*"), recursive=True)
            if os.path.isfile(f) and "{{" in open(f, encoding="utf-8", errors="replace").read()]
    check("polish SKILL.md stamped (name fx3-polish, keywords), no {{tokens}} left anywhere",
          psk.startswith("---\nname: fx3-polish\n") and "workplace injury" in psk and not left, str(left[:2]))
    cp = fresh_import("_cfgparse", os.path.join(lit, "scripts"))
    mts = [cp.parse(os.path.join(d, "references", "field-config.yaml")).get("manuscript_tex") for d in (lit, draft)]
    check("manuscript_tex written into both field-configs",
          mts == [main_tex.replace("\\", "/")] * 2, str(mts))

    rc, out = run([os.path.join(sc, "tier0_accept.py"), "fx3", "--dest", skills])
    cfg = [open(os.path.join(d, "references", "field-config.yaml"), encoding="utf-8").read() for d in (lit, draft)]
    parsed = [cp.parse(os.path.join(d, "references", "field-config.yaml")) for d in (lit, draft)]
    check("tier0_accept: scan excluded, report terminology-only, in BOTH configs",
          rc == 0 and all(p.get("excluded") == ["Scan2017"] and p.get("terminology_only") == ["Agency2021"]
                          for p in parsed), "%s %s" % (rc, [(p.get("excluded"), p.get("terminology_only")) for p in parsed]))
    reg = json.load(open(os.path.join(lit, "references", "registry.json"), encoding="utf-8"))
    check("tier0_accept: denominators filled, Tier 0 in both registries",
          reg["corpus"]["style_safe"] == 6 and 0 in reg["built_tiers"]
          and 0 in json.load(open(os.path.join(draft, "references", "registry.json"), encoding="utf-8"))["built_tiers"],
          str(reg["corpus"]))
    rc, out = run([os.path.join(sc, "tier0_accept.py"), "fx3", "--dest", skills, "--keep-config"])
    after = [open(os.path.join(d, "references", "field-config.yaml"), encoding="utf-8").read() for d in (lit, draft)]
    check("tier0_accept --keep-config is idempotent", rc == 0 and after == cfg)

    rc, out = run([os.path.join(sc, "calibrate_paragraphs.py"), "fx3", "--dest", skills])
    vals = [cp.parse(os.path.join(d, "references", "field-config.yaml")).get("para_min_chars") for d in (lit, draft)]
    check("calibrate_paragraphs: a value chosen with no paper at zero, both configs agree",
          rc == 0 and vals[0] == vals[1] and "no paper at zero" in out, "%s %s" % (vals, out.strip()[-70:]))
    rc, out = run([os.path.join(sc, "tier1_fill.py"), "fx3", "--dest", skills])
    canon = open(os.path.join(lit, "references", "cohesion-canon.md"), encoding="utf-8").read()
    check("tier1_fill: check_drift tiers 0-1 green, no TO-MEASURE left",
          rc == 0 and "TO-MEASURE" not in canon and canon.count("; parent-econ: ") == 12,
          out.strip().splitlines()[-1][:70] if out.strip() else "")
    rc2, out2 = run([os.path.join(sc, "tier1_fill.py"), "fx3", "--dest", skills])
    canon2 = open(os.path.join(lit, "references", "cohesion-canon.md"), encoding="utf-8").read()
    regmd = open(os.path.join(lit, "references", "register.md"), encoding="utf-8").read()
    check("tier1_fill re-run refills from the parent copy; one register note",
          rc2 == 0 and canon2 == canon and regmd.count("TIER 1 MEASURED") == 1)
    rc, out = run([os.path.join(lit, "scripts", "check_drift.py")])
    check("lit check_drift green at tiers 0-1", rc == 0, out.strip().splitlines()[-1][:60])
    rc, out = run([os.path.join(sc, "onboard.py"), "--finish", "--field", "fx3", "--dest", skills])
    check("onboard --finish: doctor + token estimate, asks before Tier 2-4",
          rc == 0 and "ASK THE USER" in out and "million tokens" in out, out.strip()[-60:])

    # ---- polish scripts on the onboarded manuscript ----------------------------
    ps = os.path.join(pol, "scripts")

    def prun(script, *args):
        return run([os.path.join(ps, script)] + list(args), cwd=root)
    with open(os.path.join(ms_dir, "main.bbl"), "w", encoding="utf-8") as fh:
        fh.write(_BBL3)
    os.makedirs(os.path.join(ms_dir, ".polish"), exist_ok=True)
    yml = os.path.join(ms_dir, ".polish", "polish.yaml")
    with open(yml, "w", encoding="utf-8") as fh:
        fh.write("sweep_controls:\n  - the authors argue\n  - against the backdrop\n")
    rc, out = prun("doctor.py")
    check("polish doctor: manuscript found, steps listed", rc == 0 and "snapshot.py" in out and "ready" in out)
    rc, out = prun("snapshot.py", "base")
    check("polish snapshot: both sections saved",
          rc == 0 and os.path.isfile(os.path.join(ms_dir, ".polish", "snapshots", "base", "intro.tex")))
    rc, out = prun("snapshot.py", "base")
    check("polish snapshot refuses to overwrite", rc != 0)
    rc, out = prun("sweep.py", "intro")
    check("polish sweep: FOCUS listed; a control absent from the draft still CAUGHT",
          "FOCUS intro" in out and "CAUGHT  'against the backdrop'" in out,
          out.strip()[-90:])
    with open(yml, "w", encoding="utf-8") as fh:
        fh.write("sweep_controls:\n  - the authors argue\n  - in the first year\n")
    rc, out = prun("sweep.py")
    check("polish sweep: a control the corpus attests is MISSED -> exit 1", rc == 1 and "MISSED" in out)
    os.remove(yml)
    rc, out = prun("cohesion_loop.py", "intro")
    check("polish cohesion_loop: --json digest per paragraph", rc == 0 and "joins:" in out, out.strip()[-60:])
    rc, out = prun("source_term_check.py", "Smith2019", "occupational injury")
    hits = re.search(r"Smith2019\s+occupational injury\s+(\d+)", out)
    check("polish source_term_check: a word broken at a line end matches (occupa-/tional)",
          hits and int(hits.group(1)) >= 1, hits.group(0) if hits else out[:60])
    rc, out = prun("source_term_check.py", "Missing2000", "spending")
    check("polish source_term_check: no PDF -> NO PDF TEXT, exit 1", rc == 1 and "NO PDF TEXT" in out)
    rc, out = prun("pdf_ctx.py", "Wu:2019", "fee schedules", "40")
    m = re.search(r"Wu:2019: (\d+) match", out)
    check("polish pdf_ctx: a colon key reaches its PDF", rc == 0 and m and int(m.group(1)) >= 1,
          out.strip().splitlines()[-1][:60])
    rc, out = prun("note_terms.py", "Note2016", "spending")
    check("polish note_terms: quote with its page", rc == 0 and "p.4" in out)
    rc, out = prun("scan_appositive.py", "intro")
    check("polish scan_appositive: ', a difference attributed' found", "a difference attributed" in out)
    rc, out = prun("para_lengths.py")
    check("polish para_lengths runs (paragraphs, distribution)", "paragraphs:" in out and "distribution" in out,
          out.strip()[:60])
    rc, out = prun("words_compare.py")
    check("polish words_compare: no slices -> skipped, not a crash", rc == 0 and "skipped" in out)
    rc, out = prun("render_section.py", "intro")
    check("polish render_section: labels from the .bbl and the alias",
          rc == 0 and "(Smith, 2019; Lee and Park, 2020)" in out and "Smith (2019) find" in out
          and "(State Agency, 2021)" in out, out[:80])
    rc, out = prun("counts.py")
    rc2, out2 = prun("counts.py")
    check("polish counts: baseline recorded, then OK", rc == 0 and rc2 == 0 and "baseline recorded" in out
          and "page_comments" in out2)
    pairs = os.path.join(root, "pairs.txt")
    with open(pairs, "w", encoding="utf-8") as fh:
        fh.write("The authors argue that claim duration matters for costs \\citep{Brown2015}\n>>>\n"
                 "\\citet{Brown2015} suggest that claim duration matters for costs\n")
    rc, out = prun("rep.py", "intro", pairs)
    intro_now = open(os.path.join(ms_dir, "sections", "intro.tex"), encoding="utf-8").read()
    check("polish rep: one exact replacement, LaTeX intact", rc == 0 and "\\citet{Brown2015} suggest" in intro_now)
    rc, out = prun("trial_diff.py", "base")
    check("polish trial_diff: numbers, comments, keys MATCH -> exit 0", rc == 0 and "DIFF" not in out, out.strip()[-60:])
    rc, out = prun("sent_diff.py", "base", "intro")
    check("polish sent_diff: the changed sentence as - / +",
          rc == 0 and "- The authors argue" in out and "+ \\citet{Brown2015} suggest" in out)
    with open(pairs, "w", encoding="utf-8") as fh:
        fh.write("FILE intro\nrose by 12 percent\n>>>\nrose by 13 percent\n===\nFILE results\n"
                 "no such text\n>>>\nanything\n")
    rc, out = prun("rep_multi.py", pairs)
    check("polish rep_multi: one bad pair -> exit 1, nothing written",
          rc == 1 and open(os.path.join(ms_dir, "sections", "intro.tex"), encoding="utf-8").read() == intro_now)
    with open(pairs, "w", encoding="utf-8") as fh:
        fh.write("FILE intro\nrose by 12 percent\n>>>\nrose by 13 percent\n")
    prun("rep_multi.py", pairs)
    rc, out = prun("trial_diff.py", "base", "intro")
    check("polish trial_diff: a changed number -> DIFF, exit 1", rc == 1 and "new-only {'13': 1}" in out,
          out.strip()[-60:])
    reg_d = os.path.join(draft, "references", "registry.json")
    d = json.load(open(reg_d, encoding="utf-8"))
    d["built_tiers"] = sorted(set(d["built_tiers"]) | {3})
    json.dump(d, open(reg_d, "w", encoding="utf-8"), indent=1)
    with open(os.path.join(draft, "references", "records", "introduction.md"), "w", encoding="utf-8") as fh:
        fh.write("# introduction - record\n\n### Smith2019  introduction 1 paragraphs\n\n"
                 "¶1 opens on costs\n> \"However, costs rise with benefit generosity in most states.\"\n"
                 "1 sentences\n\n### NotAPaper  stray heading\n\n¶1 x\n> \"However, this must not count.\"\n")
    rc, out = prun("opener_check.py", "intro")
    check("polish opener_check: corpus openers from records; 'However' 1/1",
          rc == 0 and "'However'" in out and "->  1/1" in out, out.strip()[-60:])

    # single-file manuscript: sections cut at \section, edits stay inside a section
    single = os.path.join(ms_dir, "single.tex")
    body = open(main_tex, encoding="utf-8").read()
    body = body.replace("\\input{sections/intro}", open(os.path.join(ms_dir, "sections", "intro.tex"),
                                                        encoding="utf-8").read()
                        + "We find similar effects in every state.\n")
    body = body.replace("\\input{sections/results}", _RES3)
    with open(single, "w", encoding="utf-8") as fh:
        fh.write(body)
    rc, out = prun("snapshot.py", "s1", "--manuscript", single)
    rc2, out2 = prun("trial_diff.py", "s1", "--manuscript", single)
    check("polish single-file: sections cut at \\section (intro, results); snapshot + trial_diff",
          rc == 0 and rc2 == 0 and "== intro" in out2 and "== results" in out2, out2.strip()[-60:])
    with open(pairs, "w", encoding="utf-8") as fh:
        fh.write("We find similar effects in every state.\n>>>\nWe find the same effects in every state.\n")
    rc, out = prun("rep.py", "results", pairs, "--manuscript", single)
    t = open(single, encoding="utf-8").read()
    check("polish rep on a heading range: text in two sections, replaced only in the one named",
          rc == 0 and t.count("We find similar effects in every state.") == 1
          and t.index("We find similar effects") < t.index("\\section{Results}")
          and t.count("We find the same effects in every state.") == 1, out.strip()[-60:])


def main():
    keep = "--keep" in sys.argv
    tmp = tempfile.mkdtemp(prefix="cb-selftest-")
    try:
        # a crash is a FAIL, never an abort -- run against an OLD factory the
        # suite must still report every check it can (qualification run)
        for part in (unit_tests, integration, onboard_polish):
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
