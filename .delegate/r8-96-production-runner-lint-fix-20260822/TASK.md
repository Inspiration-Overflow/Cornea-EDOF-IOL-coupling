# Task contract: R8 runner lint correction

- task_id: `r8-96-production-runner-lint-fix-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `37159094998dcf1e501f0938b6096bef3e5a9c82`
- task branch: `delegate/r8-96-production-runner-lint-fix-20260822`
- transport: `github_direct`

## Objective

Correct the independently observed Ruff `PIE810` finding in the R8 runner unit test. This is a
test-only mechanical correction. Preserve all scientific logic, the R8 implementation-gap
disposition, the runner, the handoff, and the preceding branch.

## Authorized read paths

- `tests/unit/test_model_revision_r8.py`
- `scripts/run_model_revision_r8_96.py`
- `docs/MODEL_REVISION_R8_IMPLEMENTATION_AND_LOCAL_HANDOFF_2026-08-22.md`
- `.delegate/r8-96-production-runner-20260822/result.json`

## Authorized write paths

- `tests/unit/test_model_revision_r8.py`
- `.delegate/r8-96-production-runner-lint-fix-20260822/result.json`

## Acceptance criteria

- Change only the test expression required to satisfy Ruff `PIE810`; no scientific value or runtime
  behavior changes.
- Run the test file, Ruff on the changed files, compileall on the changed Python files, and
  `uv lock --check`.
- Do not run OpticStudio, modify diagnostics, merge, force-push, delete branches, or modify the
  default/preceding branch.
- Write result.json with matching task metadata, the exact output refs, summary, and limitations;
  do not embed the result commit SHA.
