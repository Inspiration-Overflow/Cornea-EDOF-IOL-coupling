# Task contract: direct serialized-model R8 acquisition adapter

- task_id: `r8-direct-model-acquisition-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `bbc2ab5983862b94cdba5d4c2796e6c3ff332b4b`
- task branch: `delegate/r8-direct-model-acquisition-20260822`
- transport: `github_direct`

## Objective

Implement the missing, narrowly scoped production adapter that lets the existing R8
96-configuration runner consume the immutable R5.2/R6/R7 serialized model files and perform
the approved OpticStudio acquisition when executed later by the local orchestrator.

This is a code implementation task only. Do not run OpticStudio, do not inspect or alter
credentials, do not perform license operations, and do not create or claim R8 runtime evidence.
The local orchestrator will run the adapter after independently validating this branch.

The adapter must use the existing R6/R7 files directly:

- `diagnostics/model_revision/r6_r7/validated/<carrier_id>/ACTUAL_BINARY4_MONO.zmx`
- `diagnostics/model_revision/r6_r7/validated/<carrier_id>/ACTUAL_BINARY4_EDOF.zmx`

It must verify every input SHA-256 against `MODEL_REVISION_R6_R7_EVIDENCE.json` before opening
the production acquisition path. The serialized models are immutable inputs. If a working copy
is required by OpticStudio, use copy-on-write and record the source path and source SHA; never
reapply a legacy residual, refit the IOL, rebuild the carrier, change zone topology, or use an
old TASK-013/TASK-014 model as a substitute.

## Frozen scientific contract

Preserve the existing R8 plan and accepted TASK-009 semantics exactly:

- 24 carriers = 2 base eyes × 4 corneas (N0/A0/B0/C0) × 3 mechanisms (WFS/RAD/HOA);
- 96 configurations = 24 carriers × MONO/EDOF × 3/5-mm physical pupils;
- 48 exact MONO–EDOF matched pairs;
- 15 retina-anchored defocus planes, +0.50 D through −3.00 D in −0.25-D steps;
- 1440 through-focus rows;
- actual physical STOP semi-diameter: 1.5 mm for a 3-mm pupil and 2.5 mm for a 5-mm pupil;
- production MFE `MTFA`, Grid=1, Data Type=0, Wave=1, Field=1, sampling=128;
- one residual-free MONO EFFL per matched pair establishes the common angular scale;
- the same pair scale is used for MONO, EDOF, every focus plane, and every production frequency;
- no per-state EFFL replacement of the pair scale;
- no MTF-driven mechanism fit and no automatic progression after local PASS;
- existing DOF50, distance-peak, MTFa, HOA, footprint/vignetting, and entity-integrity rules
  remain the source of truth. Do not silently relax censoring, thresholds, or focus range.

## Required implementation shape

Use the existing tested primitives and domain types where they fit, especially the ZOS session,
MFE EFFL, MFE MTFA Grid=1, MFE HOA, defocus, metrics, and artifact/provenance helpers. Add a
small direct-model adapter rather than modifying the old carrier+residual backend into a second
ambiguous mode. The adapter may be a new module under `src/whole_eye_mvp/` and may update the R8
runner to call it.

The execution path must:

1. build and validate the exact R8 plan already defined in `scripts/run_model_revision_r8_96.py`;
2. run the existing R6/R7 evidence and 48-model hash preflight before any production acquisition;
3. load each immutable serialized MONO/EDOF model directly, set only the requested physical STOP
   aperture for that config, and capture the existing entity/ray-health diagnostics without
   changing model identity;
4. measure each pair's MONO nominal-distance EFFL once, convert the frozen 0–60 cpd grid to
   cycles/mm with that pair scale, and run the 15-plane MTFA acquisition for both states;
5. restore temporary OBJECT thickness/MFE changes in `finally` blocks and leave source model files
   untouched;
6. construct complete config, through-focus, paired-delta, and formal evidence outputs under the
   runtime directory `diagnostics/model_revision/r8_96/` only. Runtime outputs are not authorized
   Git writes for this Web task;
7. fail closed on missing files, SHA mismatch, non-finite values, incomplete MFE results, pair
   scale failure, model/entity mutation, unexpected vignetting, config failure, or row-count drift.

`--plan-only` and `--preflight` must remain offline and must not open OpticStudio. `--execute`
must retain the explicit `--authorization-id r8-96-production-runner-20260822` requirement and
must call the direct adapter only after preflight succeeds. The runner must not claim a formal
PASS unless all 96 configs, 48 pairs, 1440 through-focus rows, required artifacts, and hashes
are complete and finite. It must retain `manual_web_review_required=true` and
`automatic_progression_allowed=false` in formal evidence.

The formal evidence and CSV schema should be compatible with existing `ConfigResult`,
`through_focus_rows`, `paired_delta_row`, and the accepted 96-config offline analysis where
possible. If a new field is needed, document it in the handoff and test the pure transformation.
Do not overwrite accepted Task015 evidence or manuscript files.

## Authorized read paths

- all repository source, tests, and documentation needed to understand the existing tested
  acquisition primitives;
- `scripts/run_model_revision_r8_96.py`;
- `src/whole_eye_mvp/analysis_zos_pair_scale.py`;
- `src/whole_eye_mvp/analysis_zos.py`;
- `src/whole_eye_mvp/zos.py`;
- `src/whole_eye_mvp/model_revision_zos.py`;
- `src/whole_eye_mvp/revision_r6_zos.py`;
- `src/whole_eye_mvp/metrics.py`;
- `src/whole_eye_mvp/analysis.py`;
- `src/whole_eye_mvp/extension96_analysis.py`;
- `tests/unit/` relevant to these modules;
- the R8 planning handoff and R6/R7 implementation handoff;
- no credentials, browser data, or authentication material.

## Authorized write paths

- `src/whole_eye_mvp/analysis_zos_r8_direct.py`;
- `scripts/run_model_revision_r8_96.py`;
- `tests/unit/test_model_revision_r8.py`;
- `tests/unit/test_analysis_zos_r8_direct.py`;
- `docs/MODEL_REVISION_R8_DIRECT_MODEL_ACQUISITION_HANDOFF_2026-08-22.md`;
- `.delegate/r8-direct-model-acquisition-20260822/result.json`.

Do not modify accepted manuscript drafts, accepted Task015 evidence, R6/R7 evidence, default
branch, preceding task branches, lock files, dependency declarations, or generated runtime
diagnostics in this task.

## Acceptance criteria

- The direct adapter is implemented; a mere planning or gap report is not sufficient.
- `--execute` no longer stops solely because `DIRECT_R5_2_SERIALIZED_MODEL_PAIR_SCALE_BACKEND`
  is absent; it is still fail-closed on every preflight/acquisition failure.
- Pure unit tests cover plan-to-model path mapping, physical pupil aperture selection, pair
  grouping, pair-scale invariants, output row counts/schema, and failure on missing/hash-drifted
  models. Tests must not require OpticStudio.
- Run repository-local checks in the available environment: the changed unit tests, Ruff on
  changed Python files, compileall on changed Python files, and `uv lock --check`. Do not claim
  an unavailable check passed; record limitations in result.json.
- Do not run OpticStudio or any live regression in Web.
- Write the handoff and result contract directly to this branch and commit all substantive output.
- `result.json` must contain the matching task metadata, exact output refs, summary, and limitations;
  do not embed the result commit SHA in `result.json`.
- Reply only with a compact receipt containing task_id, repository, task_branch, result_commit,
  result_ref, summary, and limitations.
