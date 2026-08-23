# Task contract: R8 direct-model entity snapshot correction

- task_id: `r8-direct-entity-snapshot-fix-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `5254a56d361bd48d3ce05717b6d74ae80f782d12`
- task branch: `delegate/r8-direct-entity-snapshot-fix-20260822`
- transport: `github_direct`

## Objective

Fix the first local R8 OpticStudio execution failure. The direct R8 adapter currently calls
the legacy `capture_entity_snapshot()` which requires a symmetric Standard biconvex carrier.
The actual R6/R7 serialized Binary4 models are valid but have `Radius=0` on the Binary4
surface and store their zone radii/conics in Binary4 parameters, so the legacy symmetry check
fails before the first pair EFFL measurement.

Implement a direct-model entity snapshot path used only by the R8 direct adapter. It must:

- accept the R6/R7 full-eye Binary4 model geometry without reapplying a residual or changing
  the serialized model;
- preserve the existing axial landmarks, surface-role checks, retina/IOL/ELP integrity checks,
  and model/entity fingerprint comparisons;
- include enough Binary4 zone structure and surface state in the fingerprint to detect an
  unintended in-memory optical mutation;
- reuse the existing R6 Binary4 readback primitives where appropriate instead of parsing ZMX
  text or inventing a second Binary4 representation;
- keep the old `capture_entity_snapshot()` behavior unchanged for the legacy Standard
  biconvex acquisition paths;
- use a finite, documented value for legacy-only `carrier_power_d` fields if direct Binary4
  geometry has no single biconvex power; this diagnostic field must not be used to substitute
  a different scientific result.

The direct snapshot may exclude the temporary physical STOP semi-diameter from the entity
fingerprint, because changing 3/5-mm pupil is an approved per-config acquisition setting and
must not be treated as carrier mutation. It must exclude OBJECT thickness for the same reason
as the existing snapshot.

Do not modify the runner, the frozen R5.2/R6/R7 source models, accepted Task015 evidence, or
manuscript files other than the R8 direct handoff if it needs the failure/fix note. Do not run
OpticStudio or any live regression in Web.

## Authorized read paths

- `src/whole_eye_mvp/analysis_zos_r8_direct.py`
- `src/whole_eye_mvp/analysis_zos.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `src/whole_eye_mvp/zos/primitives.py`
- `src/whole_eye_mvp/model_revision_zos.py`
- `tests/unit/test_analysis_zos_r8_direct.py`
- `docs/MODEL_REVISION_R8_DIRECT_MODEL_ACQUISITION_HANDOFF_2026-08-22.md`
- `.delegate/r8-direct-model-acquisition-20260822/result.json`

## Authorized write paths

- `src/whole_eye_mvp/analysis_zos_r8_direct.py`
- `tests/unit/test_analysis_zos_r8_direct.py`
- `docs/MODEL_REVISION_R8_DIRECT_MODEL_ACQUISITION_HANDOFF_2026-08-22.md`
- `.delegate/r8-direct-entity-snapshot-fix-20260822/result.json`

## Acceptance criteria

- The direct adapter no longer calls the legacy symmetric-biconvex snapshot on R6/R7 Binary4
  models.
- Pure tests cover Binary4-aware snapshot/fingerprint behavior with a fake session or equivalent
  deterministic test double, including unchanged OBJECT thickness exclusion and detection of a
  changed Binary4 zone value. Tests must not require OpticStudio.
- Run the changed tests, Ruff on changed Python files, compileall on changed Python files, and
  `uv lock --check` when available; record exact limitations rather than guessing.
- Do not run OpticStudio or modify runtime diagnostics.
- Write the handoff and result contract directly to the branch and commit them. The result
  contract must contain matching metadata, exact output refs, summary, and limitations, without
  embedding its result commit SHA.
- Reply only with a compact receipt containing task_id, repository, task_branch, result_commit,
  result_ref, summary, and limitations.
