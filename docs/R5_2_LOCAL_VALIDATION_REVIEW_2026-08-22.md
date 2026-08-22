# R5.2 local validation review — 2026-08-22

## Scope and lineage

Task: `r5-2-local-validation-review-20260822`

Repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`

Dispatch commit: `ffff8a13c228cc742a66032628840985cc5b7d64`

Frozen implementation base: `a1870b10b326fe96be66919cad987fbcc58f0bc3`

Task branch: `delegate/r5-2-local-validation-review-20260822`

GitHub comparison confirms the dispatch commit is exactly one commit ahead of the frozen implementation base and adds only the task contract and manifest. The production R5.2 code under review is therefore unchanged from the frozen base lineage.

This review is source/offline-evidence review only. No OpticStudio execution, sign-in, license repair, installation change, merge, force-push, branch deletion, or default-branch modification was performed.

## Reviewed sources

Successfully reviewed at the dispatch commit:

- `src/whole_eye_mvp/revision_r5_2.py`
- `src/whole_eye_mvp/revision_r5_lock.py`
- `src/whole_eye_mvp/revision_r6_zos.py`
- `scripts/run_model_revision_r6_r7.py`
- `tests/unit/test_revision_r5_2_lock.py`
- `tests/unit/test_revision_r5_1_lock.py`
- `docs/R5_2_WEB_IMPLEMENTATION_REVIEW_2026-08-21.md`

The manifest also authorizes `docs/R5_2_ANALYTICAL_PRECHECK_2026-08-21.md`, but that path is absent at the dispatch commit and GitHub returned `404 Not Found`. It was therefore not available for this review and no repository-external copy was substituted.

## Scientific and software contract findings

### Deterministic HOA A6 rule

PASS. `r5_2_zones_for_carrier()` first obtains the R5.1 carrier prescription and, for HOA only, directly solves native A6 in active zones 1 and 2. `_solve_zone_a6()` forms the boundary-sag equation at A6=0 and A6=1, derives its affine slope, and solves the unique scalar value algebraically. The R5.2 module imports no mechanism RMS/max result, gate output, optimizer, or least-squares routine; gate feedback does not participate in the prescription calculation.

### Exact sag and Binary4 automatic C0 handling

PASS within the authorized source scope. `_raw_zone_sag_mm()` uses the shared exact conic-sag function plus native A4 and A6 with the zone outer radius as the normalization radius. `r5_2_boundary_delta_z_mm()` accumulates the inter-zone C0 correction as the previous-zone raw sag minus current-zone raw sag at each boundary. This is the required cumulative C0 propagation for a piecewise Binary4 surface. The unit tests independently evaluate the resulting prescription with the shared `binary4_piecewise_sag_mm()` evaluator and verify both active-zone boundary invariants.

### Zone ordering

PASS. The active indices are fixed as `(0, 1)` and the solve loop updates the working tuple after each zone. Zone 2 is therefore solved using the already-updated zone-1 A6 state. The focused stale-zone-1 regression demonstrates that replacing the updated zone-1 state produces a material zone-2 boundary mismatch.

### `q_ant=0`

PASS. HOA rejects any non-zero `base_conic` with the explicit frozen `q_ant=0` contract. Finite/radius validity is also enforced by the R5.1 carrier construction reached before the HOA-specific solve.

### +20 D identity

PASS. When `base_radius_mm` equals `R5_REPRESENTATIVE_RADIUS_MM`, the R5.1 tuple is returned unchanged. Unit coverage requires tuple equality and the frozen HOA A6 values:

- zone 1: `+0.0423302736`
- zone 2: `-0.0516184660`
- zone 3: `0`

### WFS/RAD identity and HOA topology

PASS. WFS and RAD return the R5.1 result directly. R5.1 itself applies conic-sag scaling only for HOA, so WFS/RAD remain bit-identical to the R5 path. Tests also preserve HOA boundaries `0.90/1.10/3.00 mm`, active state `[True, True, False]`, native p2=0, A4, radius/conic terms, and neutral zone 3. Complexity remains `R+Q+A4+A6` for HOA through the frozen R5 lock.

### Production R6 path

PASS by source review. `build_and_validate_r6_carrier()` obtains `edof_prescriptions` from `r5_2_zones_for_carrier()`. MONO remains a separate degenerate prescription. Actual-eye and standard-eye MONO/EDOF models are each built through independent `_build_binary4_model()` calls from analytical source models. Binary4 serialization keeps diffraction order zero and native p2 zero, saves/reloads the model, validates serialized zone replay, checks C0 continuity, and rejects non-positive conic radicand.

### Evidence metadata

PASS. The R6/R7 runner records `R5_2_FREEZE_ID` as the effective `r5_freeze_id`, keeps the R5.1 conic-normalization provenance, and records the R5.2 HOA rule with reference power/radius, `zone_order: [1, 2]`, `gate_feedback_used: false`, and `optimizer_used: false`. The contract metadata records `r5_2_hoa_q_ant_required: 0.0` and `automatic_power_specific_refit_allowed: false`.

### Gate thresholds and R8 lock state

PASS within the authorized scope. No production code changed between the frozen implementation base and this dispatch. The R5 lock retains the `0.125 D` global-defocus tolerance. R5.2 analytical regression coverage continues to require RMS `<= 2.5%` and max `<= 6.25%`; no test or reviewed runner code relaxes those values. The R6/R7 evidence payload keeps `automatic_progression_allowed: false`, and both pass/fail next-gate messages explicitly keep R8 locked or prohibit R8 progression. No target curve, mechanism slack, RAD contract, or scientific scope was modified in this review.

## Offline verification status

The task contract supplies independent local evidence from the orchestrator at the frozen base lineage:

- `uv run pytest tests/unit`: **340 passed**
- `uv run ruff check .`: **passed**
- `uv run python -m compileall -q src tests scripts`: **passed**
- `uv lock --check`: **passed**

No production code or test file was changed during this review, so no additional offline rerun was required by the task's post-code-change criterion. This report does not convert the supplied offline evidence into OpticStudio evidence.

## OpticStudio execution blocker

The local orchestrator attempted the full R6/R7 run, but execution stopped before any carrier validation. The reported exception was exactly:

```text
whole_eye_mvp.zos.errors.ZosLicenseError:
OpticStudio license is not valid for ZOS-API: Unknown
```

The supplied read-only diagnostic was:

```text
Mode=Server
IsValidLicenseForAPI=False
LicenseStatus=Unknown
```

This is an external execution blocker. No license setting was changed or repair attempted.

Accordingly, this review does **not** claim that OpticStudio serialized mechanism validation passed, that the 24-carrier R6/R7 gate passed, or that new canonical evidence or artifact hashes were produced.

## Review disposition

**SOURCE REVIEW PASS / OPTICSTUDIO EXECUTION BLOCKED.**

No defect requiring an authorized code or test correction was identified. The deterministic R5.2 HOA A6 implementation, C0 ordering, identities, production R6 wiring, evidence metadata, unchanged gate posture, and R8 lock state conform to the reviewed contracts. The remaining validation is the blocked OpticStudio/ZOS-API execution once a valid API-capable license is available.
