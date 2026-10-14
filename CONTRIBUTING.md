# Contributing

Thank you for trying corpus-bootstrap. Reports of what broke on your field and
your machine are the most useful contribution.

## Reporting a problem

Open an issue with the **Bug report** form. Please include:

- your operating system and shell (Windows PowerShell, Git Bash, macOS Terminal, ...);
- `py -3 --version` (or `python3 --version`), and whether PyMuPDF and `pdftotext` are installed;
- the command you ran and its full output;
- the output of `py -3 scripts/tier_status.py <field>` if the field is already stamped.

For questions about how to use a tier or a skill, use the **Usage question** form.

## Keep your papers out of issues and pull requests

Corpus texts, PDFs, writing guides and manuscripts are usually copyrighted or
unpublished. Do not attach them. If an example is needed, quote one or two
sentences, or describe the layout (two columns, a scan, a reference list in
the middle). The repository's `.gitignore` already keeps `references/corpus/`,
`drop/`, `*.pdf` and the writing-guide texts out of commits.

## Changing the code

1. Run the self-test before and after your change:

   ```bash
   py -3 tests/run_selftest.py
   ```

   It stamps throwaway fields in a temporary folder and must end with
   `0 failed`. It needs PyMuPDF and `pdftotext`.
2. If you fix a bug, add a check to `tests/run_selftest.py` that fails without
   your fix.
3. Keep the scripts on the Python standard library plus PyMuPDF (PyYAML and
   pypdf stay optional), and keep them working on Python 3.8.
4. Templates under `templates/` are copied into every stamped skill. A
   change there reaches users only when they stamp a new field, so say in the
   pull request whether existing fields need anything.
5. Add a line to `CHANGELOG.md`.
