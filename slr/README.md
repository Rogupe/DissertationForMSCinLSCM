# Systematic literature review (PRISMA 2020)

Systematic literature review supporting the MSc dissertation on the integration of artificial intelligence in supply chain digital twins and the role of human-in-the-loop (HITL) involvement. The review is reported following PRISMA 2020 and coded with the SCOR process structure (Plan, Source, Make, Deliver, Return). This folder holds the record of the review: the screening workbook, the decision exports, the full-text coding records, the protocols and the scripts that produced each stage.

## Review question and sources

The review asks how far AI/ML methods are integrated into digital twins of supply chains and logistics systems, which role the AI plays in the twin (forecasting, optimisation, anomaly detection, control, decision support), and what role the human keeps as the integration deepens.

| Item | Value |
|---|---|
| Databases | Scopus (TITLE-ABS-KEY) and Web of Science Core Collection (TS) |
| Search string | `("digital twin*" OR "digital model*") AND ("supply chain" OR "logistics") AND ("artificial intelligence" OR "machine learning")` |
| Period | 2010 to 2026 (search executed 17 to 18 August 2026) |
| Language and types | English; articles, reviews, conference papers |
| Inclusion | All three required: (1) a digital twin or synchronised digital model of an operational system, asset or process; (2) a supply chain or logistics setting, including intra-plant logistics and supply chain planning; (3) an AI/ML method used in, or constitutively designed into, the twin |

## PRISMA 2020 flow

| Stage | n |
|---|---|
| Records identified (Scopus 662, Web of Science 379) | 1,041 |
| Duplicates removed | 329 |
| Records screened on title and abstract | 712 |
| Records excluded at title and abstract | 595 |
| Reports sought for full-text retrieval | 117 |
| Reports not retrievable | 42 |
| Reports assessed for eligibility (full text) | 75 |
| Reports excluded at full text | 13 |
| Studies included in the review | 62 |

Exclusions at title and abstract by code: E1 148, E2 88, E3 38, E4 314, E5 5, E6 2. Exclusions at full text by reason: no AI/ML component 5 (R0012, R0050, R0081, R0184, R0664); no digital twin or digital model 5 (R0013, R0066, R0150, R0289, R0347); review or other 2 (R0024, R0146); not peer-reviewed or low-quality venue 1 (R0321).

The 42 reports not retrievable are 31 IEEE Xplore conference papers not covered by the University of Hull or the Tecnológico de Monterrey subscriptions and without an open copy (OpenAlex, Semantic Scholar, OpenAIRE, Crossref, Google Scholar and Bing were searched), 8 Springer book chapters (R0076, R0089, R0162, R0233, R0253, R0295, R0500, R0643; R0233 and R0253 exist on HAL under embargo until January 2027), and three paywalled articles (R0026 Emerald, R0064 SPIE, R0324 ASCE). The full list with the retrieval trail is in the `Fulltext_eligibility` sheet and in table O of the `Synthesis` sheet.

## Screening codes

| Code | Meaning | Exclusion reason recorded |
|---|---|---|
| I | Include for full text | |
| E1 | No digital twin or digital model of the study | No digital twin/model |
| E2 | No supply chain or logistics framing, or an out-of-scope domain (clinical twins, cyber-defence, teaching tools) | No supply chain scope |
| E3 | No AI/ML method used or proposed | No AI/ML component |
| E4 | Review, survey, bibliometric study, perspective, editorial or literature-based framework; retained for backward snowballing with a value alto/medio/bajo | Wrong publication type |
| E5 | Out of range, not in English, or grey literature | Not in English / Not peer-reviewed / Wrong publication type |
| E6 | Companion report of an included study (second appearance of the same study) or undetected duplicate | Duplicate |
| DUDA | No rule applies; resolved jointly and the new rule dated in the Codebook | |

E3 records whose twin is implemented or concretely designed and whose supply chain setting is central keep code E3 but carry the tag `Antecedente C8: alto|medio` (32 records: 18 alto, 14 medio) and are listed in `Antecedentes_C8` as background for the literature review. The 314 E4 records are listed in `Snowballing_E4` ordered by their value (alto 33, medio 89, bajo 192). Production or shop-floor twins are included only when the paper itself frames them in supply chain or intra-plant logistics terms; those includes carry the annotation `Make` (25 at title and abstract).

## Title and abstract screening: batches with a final audit

The dissertation author was the screener of record; Claude (Anthropic) acted as the proposing screener. The 712 records were screened in 14 batches of about 50, ordered by an automatic pre-flag (345 strong candidates, 137 to check, 109 reviews, 76 likely exclusions, 45 without pre-flag). For every record Claude proposed a decision, a code and a one-line justification quoting the abstract verbatim (Screening columns P to T); a script checked that every quoted fragment existed in the title, abstract or keywords; an independent second screener (a separate model instance) re-screened each batch adversarially before the proposal was sent; and the screener of record confirmed or overruled each batch before the final values were written to columns K, L, N and O and the `PRISMA_log` counters were updated. Rulings taken during the process were dated in the `Codebook` sheet as conventions C1 to C8 (threshold, primary code order, reviews, adoption studies, Make rule, twin of operations, agents count as AI, and the three rulings on AI mentioned versus AI used).

After the fourteenth batch the whole set of 712 decisions was audited: six independent re-screenings covered the final decisions in six groups, the adjudication was checked by a seventh independent screener, and 30 recodes, 16 kept-with-flag includes, 10 snowballing values and 1 pool value were applied as dated entries (`Recodificado 2026-09-06 en la auditoría final`), each keeping the original note. The audit also applied the companion-report rule requested by the screener of record: when two records report the same study, the second appearance is coded E6 (R0155 companion of R0152; R0315 companion of R0298). The workbook went from 129 to 117 includes; the closure and the audit totals are recorded in the Codebook (rows 62 to 69).

## Full-text stage

The 117 includes were sought in full text through the screener's own browser session (University of Hull EZproxy; Tecnológico de Monterrey sign-in for IEEE Xplore journals), from open copies located in repositories (Aalto, HAL, ResearchGate author copies, the INFORMS Winter Simulation Conference archive, SGEM) or from PDFs supplied by the screener. Each retrieved text was saved verbatim in the session workspace and read by a coding agent following `protocol/ft_protocol.md`: the three criteria were re-checked in the body, and for every included study the 17 extraction fields of the `Coding` sheet were filled (evidence type, sector, SCOR coverage, AI technique and role, integration extent 1 to 5, HITL role and function, conditions under which the human role changes, key finding, citation locator, usability in the typology) together with three to six verbatim quotes with their section. A script verified every quote against the saved text (`FT_quotes` sheet, column `Verified`). The screener of record confirmed all full-text decisions on 6 September 2026 (`Fulltext_eligibility`, column `Confirmed by screener`).

Of the 62 included studies, 53 give a legible AI-role plus human-role configuration and form the typology subset; the nine outside it and the reason for each are listed in table P of the `Synthesis` sheet.

## Contents

```
slr/
  README.md                          this file
  protocol/
    ft_protocol.md                   full-text retrieval, eligibility and coding protocol given to the coding agents
    ta_screening_conventions.md      consolidated title/abstract conventions (C1 to C8, precedents, final-audit clarifications)
  workbook/
    SLR_PRISMA_workbook_screening.xlsx   the review workbook (sheets below); the Abstract column of Screening is removed in this copy
  data/
    screening_decisions.csv          712 records: id, title, authors, year, source, doi, code, exclusion_reason, snowballing_value, background_pool_c8, make
    included_studies.csv             the 62 included studies with their coded fields
    prisma_log.csv                   the PRISMA_log sheet with formulas evaluated
  coding/ftcodes/                    117 JSON coding records (one per report sought), incl. the 42 not-retrieved trails
  scripts/                           the scripts that produced each stage (see below)
```

Workbook sheets: `PRISMA_log` (flow counts and progress blocks), `Screening` (712 records, final decisions in K/L/N/O, proposals in P to T), `Coding` (extraction form, 117 rows, filled for the 62 includes), `Codebook` (definitions and every dated decision rule), `Snowballing_E4`, `Antecedentes_C8`, `Includes_fulltext`, `Fulltext_eligibility` (retrieval and full-text decisions with confirmation), `FT_quotes` (verbatim evidence with verification flag), `Synthesis` (descriptive tables A to I, cross-tabs J to N, reconciliation tables O to Q) and `Included_studies`.

The abstracts were removed from the repository copy of the workbook and are not in the CSV exports; they can be re-attached by ID from the original Scopus and Web of Science exports, which are not distributed. The saved full texts (`fulltext/`), the pre-audit backup of the workbook and the raw database exports are excluded through `.gitignore`.

## Reproducing each stage with the scripts

All scripts take the workbook path as the first argument and run with Python 3.10+ and `openpyxl`. Scripts that read the `Screening` sheet locate columns by header name (`scripts/screening_cols.py`), so they work on the repository copy without the Abstract column; the two scripts that verify quoted abstract fragments (`verify_batch.py`, `audit_apply.py`) need the working copy with abstracts and the keyword file derived from the raw exports, and are kept as the record of the procedure.

1. **Batch screening** (`confirm_batch.py`, `verify_batch.py`, `pools.py`). Each batch had a proposals module `batchN_proposals.py` defining `P = {id: (decision, code, justification, make)}`; `verify_batch.py <module>` checked codes and quoted fragments, `confirm_batch.py <workbook> <module> <batch> <date> [overrides]` wrote the confirmed decisions, refreshed `PRISMA_log` and rebuilt the pool sheets through `pools.rebuild(wb)`. The proposal modules are not in the repository; their content is preserved in Screening columns P to T and in the Notes.
2. **Final audit** (`audit_recodes.py`, `audit_apply.py`, `audit_codebook.py`). `audit_recodes.py` holds the adjudication (recodes `R`, value changes `V`, pool changes `POOLV`, cross-links `LINKS`); `python3 audit_apply.py <workbook>` applies it, recomputes `PRISMA_log` and rebuilds the pools; `python3 audit_codebook.py <workbook>` appends the audit rows to the Codebook. Re-running requires the pre-audit workbook (not distributed).
3. **Full-text preparation** (`prefill_coding.py`, `build_fulltext_sheet.py`). `python3 prefill_coding.py <workbook>` fills the Coding sheet with the includes (Harvard author strings, year, venue, DOI, screening hints); `python3 build_fulltext_sheet.py <workbook>` creates `Fulltext_eligibility` with the DOI links and the summary formulas that feed `PRISMA_log` rows 12 to 22.
4. **Full-text coding** (`consolidate_ft.py`). Coding agents wrote one JSON per report to `coding/ftcodes/` following `protocol/ft_protocol.md`; `python3 consolidate_ft.py <workbook>` writes them into `Fulltext_eligibility`, `Coding` and `FT_quotes`, verifying each quote against `fulltext/<ID>.txt` when that folder is present (set `SLR_FULLTEXT`; without it the verification column reads `n/a`). The confirmation column of `Fulltext_eligibility` and the final values of `PRISMA_log` rows 12 to 22 were written after the screener of record confirmed the decisions.
5. **Synthesis** (`build_synthesis.py`). `python3 build_synthesis.py <workbook>` regenerates the `Synthesis` sheet (tables A to Q) and `Included_studies` from the Coding sheet and the JSON records.

To rebuild the derived sheets from the committed workbook and records:

```bash
cd slr
python3 scripts/prefill_coding.py workbook/SLR_PRISMA_workbook_screening.xlsx
python3 scripts/build_fulltext_sheet.py workbook/SLR_PRISMA_workbook_screening.xlsx
python3 scripts/consolidate_ft.py workbook/SLR_PRISMA_workbook_screening.xlsx
python3 scripts/build_synthesis.py workbook/SLR_PRISMA_workbook_screening.xlsx
```

`pools.rebuild(wb)` (imported from `scripts/pools.py`) regenerates `Snowballing_E4`, `Antecedentes_C8` and `Includes_fulltext` from the Screening sheet. A report retrieved later is processed with the same protocol: add its JSON record to `coding/ftcodes/`, run `consolidate_ft.py` and `build_synthesis.py`, and update `PRISMA_log` rows 12 to 22.

## Provenance

Screening and coding were carried out between 5 and 6 September 2026. Every decision was proposed with a verbatim justification and confirmed by the screener of record; every rule change is dated in the Codebook with the record that triggered it. The full-text coding records state, for each report, the source that was read (URL or supplied PDF) and, for the reports not retrieved, the retrieval attempts made.
