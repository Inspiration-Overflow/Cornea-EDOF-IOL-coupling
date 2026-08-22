# R5.2 local validation review

- task_id: `r5-2-local-validation-review-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `a1870b10b326fe96be66919cad987fbcc58f0bc3`
- task branch: `delegate/r5-2-local-validation-review-20260822`
- result contract: `.delegate/r5-2-local-validation-review-20260822/result.json`

## Instruction

Review the R5.2 implementation on this branch against the repository's scientific and software
contracts, then write a concise local-validation review report. The local Codex orchestrator is
responsible for OpticStudio; ChatGPT Web must not attempt to run OpticStudio, sign in, repair a
license, or change any installation or license setting.

The review must cover the deterministic R5.2 HOA A6 rule, exact Binary4 sag and automatic C0
offset handling, zone 1 then zone 2 ordering, `q_ant=0`, +20 D identity, WFS/RAD identity,
preservation of gate thresholds and R8 lock state, and whether the implementation reads gate
outputs or uses an optimizer. Check the production R6 path and the evidence metadata as well as
the unit tests. If a defect is found, make only the smallest necessary correction within the
authorized write paths and add focused offline regression coverage.

## Independent local evidence

The local orchestrator independently verified the web implementation at the frozen base lineage:

- `uv run pytest tests/unit`: **340 passed**.
- `uv run ruff check .`: **passed**.
- `uv run python -m compileall -q src tests scripts`: **passed**.
- `uv lock --check`: **passed**.

The orchestrator then attempted the requested full R6/R7 OpticStudio run with:

```text
uv run python scripts/run_model_revision_r6_r7.py --project-dir
C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx
--overwrite --install-dir C:/Program Files/Ansys Zemax OpticStudio 2026 R1.00
```

The run stopped before any carrier validation because the installed ZOS-API reported:

```text
whole_eye_mvp.zos.errors.ZosLicenseError:
OpticStudio license is not valid for ZOS-API: Unknown
```

A direct read-only diagnostic confirmed `Mode=Server`, `IsValidLicenseForAPI=False`, and
`LicenseStatus=Unknown`. This is an external execution blocker. Do not describe serialized
OpticStudio gates as passed, and do not propose changing the scientific thresholds to compensate.

## Authorized read paths

- `src/whole_eye_mvp/revision_r5_2.py`
- `src/whole_eye_mvp/revision_r5_lock.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `scripts/run_model_revision_r6_r7.py`
- `tests/unit/test_revision_r5_2_lock.py`
- `tests/unit/test_revision_r5_1_lock.py`
- `docs/R5_2_WEB_IMPLEMENTATION_REVIEW_2026-08-21.md`
- `docs/R5_2_ANALYTICAL_PRECHECK_2026-08-21.md`

## Authorized write paths

- `.delegate/r5-2-local-validation-review-20260822/`
- `docs/R5_2_LOCAL_VALIDATION_REVIEW_2026-08-22.md`
- `src/whole_eye_mvp/revision_r5_2.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `scripts/run_model_revision_r6_r7.py`
- `tests/unit/test_revision_r5_2_lock.py`

## Acceptance criteria

1. Write `docs/R5_2_LOCAL_VALIDATION_REVIEW_2026-08-22.md` with the reviewed files, scientific
   contract findings, offline verification status, and the exact OpticStudio license blocker.
2. Do not claim OpticStudio serialized validation, 24-carrier gates, canonical evidence, or
   artifact hashes were produced in this run.
3. If code is changed, keep the change minimal, explain it in the report, and add or update
   focused tests. Do not alter gate values, target curves, mechanism slack, R8 state, or the
   scientific scope.
4. Run the relevant offline checks after any code change.
5. Write `.delegate/r5-2-local-validation-review-20260822/result.json` with the matching task ID,
   dispatch commit, output refs, summary, and limitations. Do not put the result commit SHA in
   `result.json`.

When complete, reply only with a compact receipt containing `task_id`, `repository`,
`task_branch`, `result_commit`, `result_ref`, `summary`, and `limitations`.
