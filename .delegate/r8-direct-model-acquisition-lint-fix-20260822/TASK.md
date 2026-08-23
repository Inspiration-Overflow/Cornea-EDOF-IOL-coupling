# Task contract: direct R8 adapter Ruff correction

- task_id: `r8-direct-model-acquisition-lint-fix-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `0cbf24c0fdd1c1709d8109c2334cb43c02a8925d`
- task branch: `delegate/r8-direct-model-acquisition-lint-fix-20260822`
- transport: `github_direct`

## Objective

Correct only the independently observed Ruff B009 findings in
`src/whole_eye_mvp/analysis_zos_r8_direct.py`. Replace `getattr(row, "constant")` calls
with direct attribute access for the typed R8 plan rows. Preserve every runtime behavior,
scientific value, output schema, and failure condition.

Do not run OpticStudio, change license settings, modify diagnostics, alter the R8 runner,
tests, handoff, default branch, or preceding branch. Do not perform any unrelated cleanup.

## Authorized read paths

- `src/whole_eye_mvp/analysis_zos_r8_direct.py`
- `scripts/run_model_revision_r8_96.py`
- `tests/unit/test_analysis_zos_r8_direct.py`
- `.delegate/r8-direct-model-acquisition-20260822/result.json`

## Authorized write paths

- `src/whole_eye_mvp/analysis_zos_r8_direct.py`
- `.delegate/r8-direct-model-acquisition-lint-fix-20260822/result.json`

## Acceptance criteria

- The diff from the frozen base contains only the B009 correction in the adapter and the
  task-local result contract.
- Run the changed direct-adapter tests, Ruff on the changed adapter and R8 runner, Python
  compileall on changed Python files, and `uv lock --check` when available. Do not claim a
  check passed if the environment cannot run it; record the exact limitation.
- Do not run OpticStudio or any live regression.
- Write result.json with matching metadata, the exact two output refs, summary, and limitations;
  do not embed the result commit SHA.
- Reply only with a compact receipt containing task_id, repository, task_branch, result_commit,
  result_ref, summary, and limitations.
