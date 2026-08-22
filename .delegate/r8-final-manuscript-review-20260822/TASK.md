# Task contract: final R8 manuscript scientific review

- task_id: `r8-final-manuscript-review-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `fbe2d9c970b0334d788dc0886580cedc43b8359c`
- task branch: `delegate/r8-final-manuscript-review-20260822`
- transport: `github_direct`

## Objective

Perform the final Web scientific review of the R8 manuscript against the committed R8 production
and offline evidence. Check numerical identity, censoring semantics, provenance, figure/table
traceability, wording scope, and the explicit R8 manual-review gate. If and only if a discrepancy
is found, correct it within the declared document paths and commit the correction. If no correction
is needed, leave the manuscript documents unchanged and write only the result contract.

Do not change production evidence, offline CSV/JSON evidence, source code, accepted Task015
evidence, the default branch, or any runtime diagnostic. Do not run OpticStudio. Do not claim
clinical validation or formal scientific lock when the evidence says otherwise.

## Authorized read paths

- `docs/MANUSCRIPT_FINAL_R8_2026-08-22.md`
- `docs/MANUSCRIPT_R8_SCIENTIFIC_QC_2026-08-22.md`
- `docs/MANUSCRIPT_R8_FIGURE_TABLE_PLAN_2026-08-22.md`
- `docs/evidence/r8_96/MODEL_REVISION_R8_96_OFFLINE_ANALYSIS_EVIDENCE.json`
- `docs/evidence/r8_96/MODEL_REVISION_R8_96_PAIR_ANALYSIS.csv`
- `docs/evidence/r8_96/MODEL_REVISION_R8_96_COUPLING_MATRIX.csv`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_EVIDENCE.json`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_CONFIG_RESULTS.csv`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_THROUGH_FOCUS.csv`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_PAIRED_DELTAS.csv`
- `docs/evidence/r8_96/figures`

## Authorized write paths

- `docs/MANUSCRIPT_FINAL_R8_2026-08-22.md`
- `docs/MANUSCRIPT_R8_SCIENTIFIC_QC_2026-08-22.md`
- `docs/MANUSCRIPT_R8_FIGURE_TABLE_PLAN_2026-08-22.md`
- `.delegate/r8-final-manuscript-review-20260822/result.json`

## Expected outputs

- `.delegate/r8-final-manuscript-review-20260822/result.json`

The result contract must state whether the three manuscript documents required correction, list any
verified residual limitations, and contain no result commit SHA inside itself.
