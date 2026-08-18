# Code Review Hardening — 2026-08-17

## Scope

This revision implements the findings from the independent post-RMD code review. It does **not** change the URD scientific model, optical thresholds, B0 ranking rule, carrier SA targets, or nominal 72-configuration experiment.

The objective is narrower: make the already-approved MDD/TDD contracts fail closed so malformed, inconsistent, or merely self-declared data cannot become a formal scientific lock or a completed result.

## Remediations

### 1. Carrier and residual scientific gates

- All carrier numeric fields used by formal validation must be finite; NaN/Inf can no longer pass tolerance comparisons.
- Residual readiness now requires an explicit, versioned `ResidualValidationPolicy` supplied by the scientific validation stage. The implementation does not invent the piston/global-defocus tolerances that remain part of `TDD-TEST-999`.
- A formal residual must carry measured piston/global-defocus values, payload hash, validation-evidence hash, and exactly three passing low/median/high calibration records.
- Low/median/high calibration records are bound to the actual carrier IDs and actual carrier powers selected from the current 18-carrier set.
- Duplicate residual platforms are rejected instead of being silently overwritten.
- The policy content itself is hashed, so reusing a policy ID with changed numeric tolerances changes the formal lock identity.

### 2. B0 completeness

- A0 and all five B candidates must use the exact frozen 17-plane `CORNEA_LOCK_B0_555_v1` defocus grid.
- Candidate curves must be finite and non-negative.
- Candidate IDs must be unique and canonical for the target ΔC4 value.
- Each candidate carries its achieved ΔC4 and must satisfy the existing ±0.01 µm oracle before the five-point scan can be complete.
- The scan hash now includes the frozen B0 analysis settings.

### 3. Formal carrier/manifests

- Formal carrier locks include residual payload identity and residual validation-policy identity/hash.
- Lock hashes are recomputed from their actual contents before a manifest can be built.
- EDOF nominal rows carry residual provenance; MONO rows must not carry EDOF residual provenance.
- Manifest CSVs now include `schema_version`; project schema is version 2.
- A stable lock-set hash is derived from the 18 formal lock hashes.

### 4. Analysis result identity and numerical validity

- `AnalysisBackend.run_config` receives the run ID allocated by orchestration.
- A returned result must match the requested config and run ID exactly.
- All through-focus, aberration, footprint and position values required for a completed result must be finite.
- The stored distance peak is recomputed from the VSOTF curve and must agree with the result.
- Every shape-recentered row must satisfy `defocus_shape_d = defocus_retina_d - distance_peak_retina_d`.
- Retina position, IOL position and ELP must remain unchanged during through-focus analysis.
- Unintended vignetting is an explicit failed condition.
- Required artifacts include the `.zos`, through-focus CSV/plot, MTF plot and three PSF images.

### 5. ProjectStore provenance

- Project metadata records a hash of the complete frozen `ScientificBaseline`, not only its ID.
- Reopening a project with the same baseline ID but different baseline content fails.
- `RunEnvironment` records are create-once: identical replay is a no-op, different content under the same environment ID is a conflict.
- Formal analysis checks that the RunEnvironment baseline/settings/manifest/lock-set identifiers match the actual objects used.
- Completed-result metadata and mandatory artifacts are indexed in ProjectStore so restart/recovery has durable references.
- Formal output paths must remain inside the selected project/target directory.

### 6. ZOS analysis lifecycle

`SystemAnalysisRunner` no longer returns a live ZOS result object after closing its analysis. A parser/callback must copy the required data into a pure-Python value while the analysis is open; only then is the ZOS analysis closed.

Analysis-specific Huygens/Zernike settings are still intentionally deferred to the installed OpticStudio API and are not guessed here.

### 7. GUI orchestration

- All seven MVP actions have an explicit composition boundary.
- GUI long-action execution strategy is injected. Thread-owned ZOS operation remains contingent on `TDD-TEST-401`; the code does not assume that gate has passed.
- Worker progress is queued and drained on the Tk main thread; worker code does not mutate Tk widgets directly.
- B0 lock requests can carry candidate ID and selection reason.

### 8. Final acceptance

The 72/36/1080 acceptance oracle is now bound to the actual formal `ManifestBundle`. A synthetic set of 72 unrelated config IDs can no longer satisfy nominal acceptance merely by matching counts.

## Verification

Offline verification after the hardening revision:

```text
69 passed, 2 skipped
python -m compileall -q src tests  -> PASS
```

The two skipped tests are the real OpticStudio worker/session gates because `WHOLE_EYE_ZOS_INSTALL_DIR` is not configured in this environment.

`ruff` is declared as a development dependency but is not installed in the current execution environment, so `python -m ruff check .` could not be run here. It remains part of the target Windows workstation validation.

## Gates deliberately not cleared

This revision does **not** clear:

- `TDD-TEST-401` — real worker-thread ZOS-API lifecycle;
- `TDD-TEST-999` — actual WFS/RAD/HOA residual scientific payload, versioned numeric tolerance policy, and real low/median/high calibration evidence;
- the representative three-configuration Huygens sampling / independent MTF cross-check;
- the real GUI display smoke test;
- the real nominal Run72 acceptance run.

No synthetic test fixture produced by this revision is a formal scientific lock, manifest, or study result.
