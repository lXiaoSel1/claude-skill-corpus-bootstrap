# fetch-research.md — literature-acquisition survey (ARCHIVED, not implemented)

> Researched 2026-08-26. **User decision: corpus building is MANUAL** — you
> download the PDFs (institutional access included) into `drop/`, the factory
> converts and curates. This file archives the automation research so a future
> fetch layer can be built without re-surveying. Nothing here is wired into
> any script.

## The landscape (as of Aug 2026)

- **OpenAlex** changed 2026-02: API key required (free key = $1/day budget);
  now HOSTS full text — 50–60M OA works as PDF and as GROBID-parsed TEI XML at
  $0.01/file (`content.openalex.org/works/{id}.pdf` / `.grobid-xml`). Free key
  ≈ 100 downloads/day; a 200-paper corpus ≈ $2. Official CLI:
  `pip install openalex-official`. PDFs retain original copyright.
- **Unpaywall**: free, email param, 100k calls/day; DOI → `best_oa_location`
  (check `url_for_pdf` is non-null — landing-page-only rows exist). The
  `unpywall` lib is stale; call the REST API directly.
- **CORE** (core.ac.uk): free key; `/search` returns a `fullText` field —
  pre-extracted text from institutional repositories, skipping PDF parsing.
  Slow limits (1 batch req/10s) but irrelevant at 200 papers.
- **Europe PMC**: the best-behaved API — `rest/{PMCID}/fullTextXML` returns
  JATS XML with labeled sections, no key, sanctioned per-article OA access.
  (NCBI PMC FTP retires Aug 2026 — use Europe PMC, not the FTP.)
- **arXiv**: direct `/pdf/{id}`, 3-second courtesy delay. Near-total coverage
  for physics/CS/math/stats; near-zero for mainstream econ/finance.
- **Crossref** (`habanero`, maintained): DOI normalization from .bib, license
  determination; its TDM links are inconsistent without institutional
  entitlement.
- **Economics green OA**: EconStor OAI-PMH (cleanest automatable econ source),
  RePEc/EconPapers as resolver, Fed/IMF/World Bank/BIS/CEPR open PDFs.
  **SSRN: no API, Cloudflare + login — manual only.** NBER: 3 free
  downloads/year for general users; papers >18 months old are open.
- **Excluded outright**: Sci-Hub/LibGen paths and the tools built on them
  (PyPaperBot, scidownl, PyPaperRetriever with fallback enabled).

## Hit-rate expectations (why manual stays primary for econ/finance)

| field | OA full-text hit rate | note |
|---|---|---|
| bio/med | ~60–80% | arrives as structured JATS XML |
| physics/CS/math | ~80–95% | arXiv-native |
| econ/finance | ~40–60% | carried by green/working-paper versions — often NOT the version of record (different tables/sections) |
| humanities/law | lowest | monograph-heavy |

Highly-cited seed lists gain +20–40 points over random DOI lists.

**Version hygiene if a fetch layer is ever built**: store `oa_status`,
`license`, and `best_oa_location.version` (submitted/accepted/published) per
item — a working-paper copy silently substituting for the journal version is
a misattribution machine.

## PDF → text (this part IS implemented, in scripts/ingest.py)

- `pdftotext -q` (poppler/MiKTeX) — the parents' validated path; default mode,
  never `-layout`.
- **PyMuPDF** (`pip install pymupdf`) — the pip-only fallback with no external
  binary; top-tier accuracy benchmarks, ~10× faster than pdfplumber.
- All extractors return nothing on scanned/image-only PDFs — ingest flags
  word-count outliers instead of pretending.
- GROBID (structure-aware TEI) is NOT required: Docker/Java cost outweighs the
  benefit at this scale, and slicing is done downstream from headings anyway.
