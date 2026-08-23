# Task contract: R8 96-config production runner

## Identity

- task_id: `r8-96-production-runner-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `a1870b10b326fe96be66919cad987fbcc58f0bc3`
- task branch: `delegate/r8-96-production-runner-20260822`
- transport: `github_direct`

## Objective

Design and implement the smallest auditable production runner needed to execute the approved R8
96-configuration experiment after the R5.2/R6/R7 model revision. The local Codex will execute the
runner later with a valid OpticStudio license; ChatGPT Web must not run OpticStudio.

The runner must preserve the accepted study design:

```text
2 base eyes × 4 cornea conditions (N0/A0/B0/C0)
× 3 mechanisms (WFS/RAD/HOA)
× 2 optical states (MONO/EDOF)
× 2 physical pupils (3/5 mm)
= 96 configurations, 48 matched pairs, 1440 through-focus rows
```

R5.2 is the active prescription rule. Do not silently fall back to R5/R5.1. Do not refit from
MTF or gate output. Do not change the frozen focus window, MTFA contract, angular-frequency
scale, censoring rules, carrier identity, zone topology, mechanism gates, or R8 factor matrix.

## Authorized read paths

- `src/whole_eye_mvp/revision_r5_lock.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `src/whole_eye_mvp/revision_r6_native.py`
- `src/whole_eye_mvp/revision_carrier_zos.py`
- `src/whole_eye_mvp/revision_base_zos.py`
- `src/whole_eye_mvp/revision_r4_zos.py`
- `src/whole_eye_mvp/revision_r5_2.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `scripts/run_model_revision_r6_r7.py`
- `scripts/run_task_011_run72.py`
- `scripts/run_task_013_native_reference.py`
- `scripts/run_task_014_vertex_corrected_cornea.py`
- `src/whole_eye_mvp/run72.py`
- `src/whole_eye_mvp/run72_analysis.py`
- `src/whole_eye_mvp/extension96_analysis.py`
- `docs/MODEL_REVISION_R6_R7_IMPLEMENTATION_AND_LOCAL_HANDOFF_2026-08-21.md`
- `docs/TASK_015_96_CONFIG_INTEGRATION.md`
- `docs/MANUSCRIPT_ABSTRACT_METHODS_DRAFT_2026-08-20.md`
- `docs/MANUSCRIPT_DRAFT_96_CONFIG_2026-08-20.md`
- `docs/MANUSCRIPT_FIGURE_TABLE_PLAN_2026-08-20.md`
- `pyproject.toml`
- `tests/unit/test_revision_r5_2.py`
- `tests/unit/test_revision_r6.py`
- `tests/unit/test_run72.py`
- `tests/unit/test_task015_extension96.py`

## Authorized write paths

- `scripts/run_model_revision_r8_96.py`
- `tests/unit/test_model_revision_r8.py`
- `docs/MODEL_REVISION_R8_IMPLEMENTATION_AND_LOCAL_HANDOFF_2026-08-22.md`
- `.delegate/r8-96-production-runner-20260822/result.json`

No other path may be changed.

## Required outputs

1. A production runner or a precise, evidence-backed implementation-gap report in the handoff
   document. If the current repository lacks a safe prerequisite, stop rather than inventing a
   substitute or copying old evidence into a new R8 result.
2. Pure/unit-testable planning and validation logic covering exact 96-config factor coverage,
   48 matched pairs, 15 focus planes, R5.2 freeze identity, and fail-closed authorization.
3. A local execution handoff with exact command shape, expected artifacts, acceptance gates, and
   explicit STOP conditions. It must state that OpticStudio execution and formal R8 evidence are
   still pending.
4. Tests for the new pure logic. Do not claim OpticStudio or R8 production completion.
5. `result.json` with the matching task metadata, output refs, summary, and limitations. Do not put
   the result commit SHA inside `result.json`.

## Constraints

- Verify GitHub read/write capability before working.
- Do not run OpticStudio, change license settings, modify project diagnostics, merge, force-push,
  delete branches, modify the default branch, or change the preceding R5.2 implementation.
- Do not create ZIPs or attachments and do not paste substantive files into chat.
- Keep the implementation functional/data-oriented and fail closed on incomplete input.
- Do not add an optimizer, MTF-driven refit, new scientific constants, or a second source of truth
  for the accepted factor matrix.

## Acceptance criteria

- The changed-path set is exactly the four authorized write paths above.
- The runner/handoff either provides a safe, test-covered R8 execution path or documents a concrete
  implementation gap with the exact missing prerequisite.
- Unit tests, ruff, compileall, and `uv lock --check` pass for the changed code.
- The result is independently verifiable from the task branch and contains no R8 production claim.
