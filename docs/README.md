# Reference Documents

This folder holds Markdown conversions of the reference documents for FDO
Hospital MIS, kept in-repo so they're greppable alongside the code they
describe.

| Document | Source | Status |
|---|---|---|
| [SolutionSpec.md](SolutionSpec.md) | `FDO_Hospital_MIS_SolutionSpec.docx` | Converted, in repo |
| [TRD.md](TRD.md) | `FDO_Hospital_MIS_TRD.docx` | Converted, in repo |
| [DataDictionary.md](DataDictionary.md) | `FDO_Hospital_MIS_Phase1_DataDictionary.docx` | Converted, in repo |
| Business Requirements Document (BRD) | — | **Missing** |

## Missing BRD

CLAUDE.md names the BRD as a primary reference — every module, permission code,
and user journey is expected to trace back to it. It was not attached alongside
the other three documents. The Solution Spec, TRD, and Data Dictionary all cite
BRD section numbers extensively (module scope, edge cases, and — most
importantly — the full role → permission matrix), which means:

- The **Phase 1 data model** (Core, Patients, Appointments, OPD, Laboratory,
  Pharmacy, Billing) is fully specified by the Data Dictionary and buildable
  with confidence.
- The **complete permission matrix** (which of the BRD's roles get which
  `module.resource.action` codes) is only partially visible — the documents
  above give concrete examples (e.g. `lab.result.verify`, `lab.result.enter`,
  the privileged-role list for MFA) but not the exhaustive matrix.

Add the BRD `.docx`/`.md` to this folder when available. Until then, any
permission-matrix decision not resolvable from the documents above is flagged
explicitly in the relevant module's PR description rather than guessed.

## Conversion note

These `.md` files were generated from the source `.docx` files using a small
stdlib-only (`zipfile` + `xml.etree`) extractor, since neither `pandoc` nor
`python-docx` was available in the build environment. Table structure was
flattened to one line per cell/paragraph during extraction — treat these as a
faithful text extraction for search/reference, not a pixel-exact re-render of
the original tables. The original `.docx` files remain in the repository root.
