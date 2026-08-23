# R5.2 Web implementation review — 2026-08-21

## Scope

Repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`

Dispatch/base commit: `3c505763882330ef7f87703903619d62d9e172fb`

Task branch: `task/r5-2-web-implementation-2026-08-21`

This change implements the reviewed R5.2 HOA A6 rule in the production R5/R6 path. It does not run OpticStudio, change gate thresholds, alter WFS/RAD prescriptions, unlock R8, or enable 96-configuration production.

## Scientific contract review

The R5.2 rule is deterministic and well posed. For each active HOA zone, with R5.1 radius/conic and native A4 held fixed, the complete Binary4 outer-edge EDOF-minus-MONO sag is affine in that zone's native A6. The coefficient is non-zero, so the A6 solution is unique.

The production implementation therefore uses a direct affine solve rather than an optimizer:

1. Apply the existing R5.1 HOA conic normalization.
2. Derive the +20 D reference full-sag differences from the frozen R5.1 prescription.
3. Solve zone 1 native A6 so the zone-1 outer-edge full sag difference equals the +20 D reference.
4. Write the solved zone-1 A6 into the working prescription.
5. Solve zone 2 native A6 using that updated zone-1 state, so Binary4 automatic C0 propagation is included.
6. Leave zone 3 neutral.

No mechanism RMS, max-error result, gate output, least-squares fit, or numerical optimizer participates in the A6 calculation.

The +20 D representative radius is special-cased to return the existing R5.1 tuple unchanged, preserving the frozen HOA prescription bit-for-bit:

- zone 1 A6 = `+0.0423302736`
- zone 2 A6 = `-0.0516184660`
- zone 3 A6 = `0`

HOA requires the frozen `q_ant=0` contract. WFS and RAD delegate directly to the R5.1 function and therefore remain bit-identical to the existing R5/R5.1 path.

## Production changes

### `src/whole_eye_mvp/revision_r5_2.py`

Adds the formal `R5_2_FREEZE_ID`, a pure production prescription entry point, exact full-sag/C0 evaluation, and the sequential direct A6 solve.

### `src/whole_eye_mvp/revision_r6_zos.py`

Changes only the EDOF prescription source from R5.1 to R5.2. MONO and EDOF are still independently built from fresh analytical carriers and serialized separately as Binary4 surfaces.

### `scripts/run_model_revision_r6_r7.py`

Records the effective R5.2 freeze ID in `r5_freeze_id`, retains explicit R5.1 conic provenance, and adds the R5.2 HOA A6 rule, +20 D reference, solve order, `q_ant=0`, `optimizer_used=false`, and `gate_feedback_used=false` to evidence metadata.

No R6/R7 mechanism, RAD POWP, defocus, ray-health, audit, or progression gate value was changed.

## Unit coverage

`tests/unit/test_revision_r5_2_lock.py` covers:

- formal R5.2 freeze ID;
- +20 D R5.1/R5.2 bit identity;
- WFS/RAD bit identity;
- known A6 values for all eight supplied HOA carrier radii;
- zone-1 and zone-2 complete outer-edge sag invariants;
- proof that zone 2 uses the updated zone-1 C0 state;
- `q_ant=0` contract;
- illegal radius and non-finite input rejection;
- HOA topology, complexity, neutral zone 3, A4 and p2 preservation;
- the eight supplied 0.025 mm analytical mechanism proxy values and the unchanged 2.5% RMS / 6.25% max gates.

The independently recomputed eight A6 pairs agree with the supplied precheck values to floating-point roundoff (largest difference approximately `5e-16`). The stale-zone-1 control produces about `8.16e-4 mm` zone-2 boundary error, so the C0-order test is sensitive to the intended failure mode.

## Offline verification

A draft pull request was opened only to trigger the repository's existing `Offline quality gate` workflow against the exact dispatch base. No merge was performed.

GitHub Actions run `32556759568` on code commit `d9dacdebc2c174216344a3e6e5450d070fae10f3` passed:

- `uv run pytest tests/unit` — `340 passed in 137.95s`
- `uv run ruff check .` — PASS
- `uv run python -m compileall -q src tests scripts` — PASS
- `uv lock --check` — PASS

## Not executed on Web

OpticStudio / ZOS-API validation was intentionally not run. The following remain for local Codex, as specified in the handoff:

- fresh MONO/EDOF Binary4 serialization for the eight HOA carriers or the full 24-carrier R6/R7 gate;
- serialized mechanism fidelity;
- global defocus replay;
- minimum conic radicand;
- 3/5 mm ray health;
- selected full standard audits;
- canonical evidence/artifact hash regeneration.

R8 and 96-configuration production remain locked.

## New decision required

None identified during the Web implementation review. Any discrepancy found by local OpticStudio validation should stop the process for review rather than trigger an automatic A6 refit or gate relaxation.
