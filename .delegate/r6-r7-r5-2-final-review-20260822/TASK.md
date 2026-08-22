# Final R5.2 / R6-R7 evidence review

- task_id: `r6-r7-r5-2-final-review-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `34c1ca21093ab35479d568a3e4579f6d38dc10d6`
- task branch: `delegate/r6-r7-r5-2-final-review-20260822`
- result contract: `.delegate/r6-r7-r5-2-final-review-20260822/result.json`

## Instruction

Use the supplied GitHub input evidence and the authorized source files to write the final R5.2
OpticStudio validation review and a manuscript-ready results addendum. Do not run OpticStudio,
change code, change license settings, merge branches, modify the default branch, or enter R8 or
96-config production. This task is documentation and source/evidence review only.

The local orchestrator has independently completed the full R6/R7 run with the R5.2 implementation.
The evidence JSON is the authoritative input for numerical claims:

- input: `.delegate/r6-r7-r5-2-final-review-20260822/inputs/MODEL_REVISION_R6_R7_EVIDENCE.json`
- evidence SHA256: `1ebf5d025d447e929af103106c946148bfcf1b9885aaa1c15e70869f084f99a9`
- code commit recorded by the run: `a1870b10b326fe96be66919cad987fbcc58f0bc3`
- R5.2 freeze ID: `MODEL-REVISION-R5.2-HOA-BOUNDARY-SAG-INVARIANT-2026-08-21`
- 24 carriers, 9/9 local checks passed, 340 artifact hashes listed and independently matched
  against the local output directory.

The top-level evidence records `local_checks` for: all 24 carriers, standard-eye SA, WFS/HOA
serialized mechanism, real RAD POWP identity, global defocus, actual-eye 3/5 mm ray health,
Binary4 geometry, selected low/median/high full standard audits, and the aggregate R6/R7 result.
It also records `automatic_progression_allowed=false`, `manual_web_review_required=true`, and
the R5.2 rule metadata (`zone_order=[1,2]`, `q_ant=0`, `optimizer_used=false`,
`gate_feedback_used=false`).

## Authorized read paths

- `.delegate/r6-r7-r5-2-final-review-20260822/inputs/MODEL_REVISION_R6_R7_EVIDENCE.json`
- `.delegate/r5-2-local-validation-review-20260822/result.json`
- `docs/R5_2_LOCAL_VALIDATION_REVIEW_2026-08-22.md`
- `docs/R5_2_WEB_IMPLEMENTATION_REVIEW_2026-08-21.md`
- `src/whole_eye_mvp/revision_r5_2.py`
- `src/whole_eye_mvp/revision_r5_lock.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `scripts/run_model_revision_r6_r7.py`
- `tests/unit/test_revision_r5_2_lock.py`
- `docs/MANUSCRIPT_WORKING_DRAFT_2026-08-20.md`
- `docs/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT_2026-08-20.md`
- `docs/MANUSCRIPT_SCIENTIFIC_QC.md`

## Authorized write paths

- `.delegate/r6-r7-r5-2-final-review-20260822/`
- `docs/R6_R7_R5_2_FINAL_VALIDATION_REVIEW_2026-08-22.md`
- `docs/MANUSCRIPT_R5_2_RESULTS_ADDENDUM_2026-08-22.md`

## Acceptance criteria

1. Write the final validation review with exact evidence-backed results, including the 24-carrier
   count, all 9 local checks, R5.2 freeze/rule metadata, platform power ranges, artifact-hash
   count and evidence SHA256.
2. State clearly that the successful result is a local OpticStudio serialized R6/R7 validation;
   do not call it an R8 or 96-config production result.
3. State the remaining scope accurately: no automatic progression, no default-branch merge, and
   no change to gate thresholds, mechanism slack, RAD contract, or scientific scope.
4. Write a manuscript-ready results addendum that reports only evidence-supported findings and
   preserves the distinction between R5.2 analytical precheck and serialized R6/R7 validation.
5. Do not invent numerical uncertainty, clinical conclusions, or comparisons not present in the
   authorized sources.
6. Write `result.json` with matching task ID, dispatch commit, output refs, summary, and
   limitations. Do not put the result commit SHA inside `result.json`.

When complete, reply only with a compact receipt containing `task_id`, `repository`,
`task_branch`, `result_commit`, `result_ref`, `summary`, and `limitations`.
