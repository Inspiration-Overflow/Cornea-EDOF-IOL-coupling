# Model Revision R8 — 96-config production runner implementation handoff

> Date: 2026-08-22  
> Task: `r8-96-production-runner-20260822`  
> Dispatch commit: `1967dddcd3c1f71dbc22056ca8136ecbc69d9bc2`  
> Status: **planning/preflight implemented; OpticStudio execution intentionally blocked by one concrete implementation gap**

## 1. Scope

This task is limited to the approved R8 experiment shape after the R5.2/R6/R7 model revision:

```text
2 base eyes × 4 corneas (N0/A0/B0/C0)
× 3 mechanisms (WFS/RAD/HOA)
× 2 optical states (MONO/EDOF)
× 2 physical pupils (3/5 mm)
= 96 configurations
= 48 matched MONO–EDOF pairs
= 1440 through-focus rows at 15 planes/config
```

R5.2 remains the active prescription identity:

`MODEL-REVISION-R5.2-HOA-BOUNDARY-SAG-INVARIANT-2026-08-21`

This Web task did **not** run OpticStudio, modify a license, refit a mechanism, create R8 evidence, or change any R5.2/R6/R7 source file.

## 2. What was implemented

`scripts/run_model_revision_r8_96.py` provides a bounded, fail-closed R8 planning/preflight layer.

It deterministically derives the 24 physical-carrier key space from the existing R6 source of truth (`expected_r6_carrier_keys()`), then expands each carrier over the accepted two optical states and the accepted 3/5-mm physical pupils. The accepted 15-plane focus grid and pupil set are imported from the existing 96-config analysis definition rather than redefined.

The runner validates all of the following before any future production acquisition could be allowed:

- exactly 24 R6 carrier identities;
- exactly 96 unique configuration identities;
- exactly 48 matched pairs;
- each pair contains one MONO and one EDOF state on the same exact carrier and pupil;
- exactly 15 focus planes per configuration and 1440 planned through-focus rows;
- exactly 48 immutable serialized model inputs (`ACTUAL_BINARY4_MONO.zmx` / `ACTUAL_BINARY4_EDOF.zmx`);
- R6/R7 evidence identity, R5.2 freeze ID, and all nine required local checks;
- R5.2 HOA zone order `[1, 2]`, `q_ant=0`, no gate-feedback selection, no optimizer, no automatic power-specific refit, and no MTF-driven mechanism fit;
- exact presence and SHA-256 match of all 48 serialized R6/R7 model inputs.

Execution also requires an explicit local operational acknowledgement:

```text
--authorization-id r8-96-production-runner-20260822
```

Absence or mismatch fails closed. This acknowledgement is only an anti-accidental-execution control; it does not manufacture a scientific result or override a failed preflight.

## 3. Why OpticStudio execution is intentionally blocked

The authorized repository surface does not expose a safe production acquisition adapter for the new R5.2 input form.

The relevant code paths establish the following:

1. `revision_r6_zos.py` creates the accepted R5.2 state models as independent, serialized files under each validated carrier:
   - `ACTUAL_BINARY4_MONO.zmx`
   - `ACTUAL_BINARY4_EDOF.zmx`
2. `run_model_revision_r6_r7.py` hashes those files in `MODEL_REVISION_R6_R7_EVIDENCE.json` and stops before R8.
3. `run_task_011_run72.py` is tied to the frozen 72-config manifest and a carrier+residual acquisition path; it is not a direct immutable-model runner for the R5.2 Binary4 state files.
4. `run_task_013_native_reference.py` and `run_task_014_vertex_corrected_cornea.py` are separate legacy extensions (N0 and A0V12/B0V12/C0V12) with their own carrier/residual provenance; they are not the current R6/R7 N0/A0/B0/C0 R5.2 carrier set.
5. `extension96_analysis.py` is a post-acquisition integration layer frozen to specific TASK-013/TASK-014 source blob identities and V12 cornea IDs. Reusing it as the R8 acquisition layer would silently substitute old evidence.
6. `revision_r4_zos.audit_r4_model()` provides a standard-eye audit at best focus with cycles/mm MTF series; it does not implement the accepted main-study 15-plane paired-MONO angular-frequency acquisition contract.

Therefore, implementing the missing acquisition inside this script would require reconstructing scientific acquisition logic from scratch or reusing a legacy residual pathway. Either choice would violate the task instruction to avoid a second source of truth and to stop rather than invent a substitute.

The exact missing prerequisite is:

`DIRECT_R5_2_SERIALIZED_MODEL_PAIR_SCALE_BACKEND`

Required capability:

> A production analysis adapter that accepts immutable pre-serialized R6/R7 `ACTUAL_BINARY4_MONO/EDOF` model paths plus expected SHA-256 values, then runs the existing paired-MONO angular-scale, MFE MTFA Grid=1, 15-plane through-focus contract without reapplying any residual, refitting the IOL, or rebuilding the physical carrier.

A follow-up implementation task should explicitly authorize either the existing pair-scale analysis backend source or a new narrowly scoped R8 ZOS adapter module. Until then, `--execute` stops before an OpticStudio session can be opened.

## 4. Current command shapes

### Pure plan inspection

```text
uv run python scripts/run_model_revision_r8_96.py --plan-only
```

Expected: a JSON summary stating 24 carriers, 96 configs, 48 pairs, 15 focus planes/config, 1440 rows, R5.2 freeze identity, and the blocking prerequisite ID. No project artifacts are created.

### Local input preflight only

```text
uv run python scripts/run_model_revision_r8_96.py \
  --project-dir "<PROJECT_DIR>" \
  --preflight
```

Expected: validates `diagnostics/model_revision/r6_r7/MODEL_REVISION_R6_R7_EVIDENCE.json` plus the 48 serialized model hashes. It does not open OpticStudio and does not write R8 evidence.

### Deliberate production execution request

```text
uv run python scripts/run_model_revision_r8_96.py \
  --project-dir "<PROJECT_DIR>" \
  --execute \
  --authorization-id r8-96-production-runner-20260822
```

Current expected result: input preflight runs, then the script emits a hard `STOP` for `DIRECT_R5_2_SERIALIZED_MODEL_PAIR_SCALE_BACKEND`. No OpticStudio session is opened.

## 5. Expected structured R8 artifacts after the prerequisite is resolved

The future direct-model production adapter must write, at minimum:

```text
project_mvp_2026_v2_zmx/
  diagnostics/model_revision/r8_96/
    MODEL_REVISION_R8_96_EVIDENCE.json
    MODEL_REVISION_R8_96_CONFIG_RESULTS.csv
    MODEL_REVISION_R8_96_THROUGH_FOCUS.csv
    MODEL_REVISION_R8_96_PAIRED_DELTAS.csv
```

No file above exists or is claimed by this Web task. The future implementation may add per-config working or archive files only under an explicitly reviewed runtime artifact policy; this task does not invent one.

## 6. Future production acceptance gates

After the direct-model acquisition adapter exists, R8 must still fail closed unless all of the following are true:

1. R6/R7 evidence identity and all nine local checks pass exactly.
2. The R5.2 freeze identity matches and the serialized-model SHA-256 values match all 48 input files.
3. The factor plan is exactly 24 carriers / 96 configs / 48 matched pairs / 2 physical pupils.
4. Each MONO–EDOF pair shares the exact same physical carrier identity.
5. The production acquisition remains MFE `MTFA Grid=1`, the accepted production sampling, and the paired residual-free MONO angular-frequency scale.
6. The through-focus grid remains exactly +0.50 to −3.00 D in 0.25-D steps (15 planes); no window extension is allowed to resolve censoring.
7. Exactly 96 completed config results, 1440 through-focus rows, and 48 paired deltas are reconstructed with zero failed configs.
8. DOF50 and distance-peak censoring use the already accepted rules; boundary values are not silently promoted to exact results.
9. No optimizer, MTF-driven refit, independent EDOF P/Q callback, IOL translation, retina tuning, zone-topology change, new A8+ term, or gate/slack relaxation is introduced.
10. Input serialized models remain immutable; any analysis working copy must be copy-on-write and traceable to the verified input SHA-256.
11. The completed R8 evidence must require manual review; no subsequent stage may be entered automatically from a local PASS.

## 7. STOP conditions

Stop immediately if any of the following occurs:

- R6/R7 evidence is missing, malformed, or does not identify R5.2;
- any required R6/R7 local check is not `true`;
- any of the 48 serialized state models is missing or hash-mismatched;
- the 24/96/48/1440 factorial identity changes;
- the physical pupil set or 15-plane focus grid changes;
- explicit execution acknowledgement is missing or incorrect;
- a production path would need to reapply an old residual to an already serialized R5.2 state model;
- a production path would need to use TASK-013/014 evidence as a substitute for new R8 acquisition;
- the direct immutable-model pair-scale acquisition adapter is still unavailable;
- any future acquisition changes the frozen MTFA/angular-scale/censoring contract;
- any config fails or any matched pair becomes incomplete;
- continuing would require a scientific refit or threshold relaxation.

## 8. Unit-test coverage added

`tests/unit/test_model_revision_r8.py` covers:

- exact 96-config / 48-pair / 1440-row planning;
- exact matched-carrier identity within every pair;
- use of only the 48 R6/R7 serialized MONO/EDOF state models;
- R5.2 freeze identity and fail-closed execution authorization;
- R6/R7 evidence contract validation;
- rejection of freeze drift and missing model hashes;
- local serialized-model SHA-256 verification;
- explicit implementation-gap state and expected future structured outputs.

## 9. Local verification commands

Run before accepting any follow-up code commit for execution:

```text
uv run pytest tests/unit/test_model_revision_r8.py
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

ChatGPT Web did not execute the repository test suite or OpticStudio in this task. The new files were syntax-checked in an isolated local checker; a local/CI pass is still required before the missing acquisition adapter is implemented or any R8 production execution is attempted.

## 10. Disposition

**R8 96-config planning/preflight layer: IMPLEMENTED.**

**R8 OpticStudio production acquisition: NOT IMPLEMENTED / BLOCKED by `DIRECT_R5_2_SERIALIZED_MODEL_PAIR_SCALE_BACKEND`.**

**Formal R8 evidence: PENDING.**

This is the required fail-closed outcome under the current authorized write surface; it avoids silently falling back to the old residual pipeline or recycling previous 96-config evidence as a new R8 result.
