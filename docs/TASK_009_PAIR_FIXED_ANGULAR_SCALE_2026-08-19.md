# TASK-009 angular-frequency scale correction：paired-MONO fixed scale

日期：2026-08-19  
状态：Web scientific-method correction frozen；local revalidation pending

## 1. Trigger

TASK-009 `MTFA Grid=1` evidence commit `e508a83f41a63bc74a4a4ae1fc1bf060f0de4ea9` showed that the HOA EDOF representative had:

```text
EFFL = 9.633329064114418 mm
mm/degree = 0.16815038428900272
60 cpd -> 356.82 cycles/mm
```

while the WFS/RAD representatives were approximately 16.5–17.2 mm EFL / 0.288–0.300 mm per degree.

The HOA residual is a high-order central phase/sag mechanism with global low-order defocus removed. A ~44% change in angular image scale is not an acceptable implicit consequence of the MTF coordinate conversion without explicit magnification validation.

OpticStudio defines EFFL as a paraxial first-order quantity. For a highly structured residual surface, the EDOF-state paraxial EFFL can be dominated by local vertex/parabasal behavior and therefore is not a robust definition of the object-space spatial-frequency coordinate for a matched MONO/EDOF comparison.

## 2. Scientific decision

The external angular-frequency coordinate must be common within each matched MONO/EDOF pair.

For every frozen `pair_key`, define one reference scale from the **residual-free MONO carrier** at nominal distance:

```text
pair_reference_effl_mm = EFFL(formal MONO carrier, no residual)
pair_mm_per_degree = pair_reference_effl_mm * tan(1 degree)
```

Use the same `pair_mm_per_degree` for:

- MONO and EDOF;
- every retina-anchored defocus plane;
- every sampling size;
- production MTF10/20/.../60 and MTFa.

Then:

```text
f_cycles_per_mm = f_cpd / pair_mm_per_degree
```

The EDOF-state EFFL may still be recorded as a diagnostic, but it MUST NOT redefine the cpd axis.

This preserves the matched-pair experiment on a common object-space spatial-frequency coordinate and prevents the residual under study from changing the coordinate system used to judge its own MTF effect.

## 3. Acquisition contract revision

Supersede:

```text
TASK009_MFE_MTFA_GRID1_v1
frequency_axis = direct_0_to_60_cpd_via_nominal_EFL
```

with:

```text
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

production_operand = MTFA
grid = 1
data_type = 0
wavelength_number = 1
field_number = 1
frequency_axis = direct_0_to_60_cpd_via_paired_MONO_EFFL
```

MFE sampling mapping remains:

```text
64 -> Samp 2
128 -> Samp 3
256 -> Samp 4
512 -> Samp 5
```

## 4. Main numerical settings

Do NOT promote sampling to 256 yet.

Keep the currently tested candidate while the coordinate correction is revalidated:

```text
NOMINAL_MAIN_FFT_MTF_555_v2
production sampling candidate = 128
convergence = 64 / 128 / 256
```

All existing numerical gates remain unchanged.

The previously proposed `NOMINAL_MAIN_FFT_MTF_555_v3` / 256 escalation is placed on HOLD until the corrected paired-MONO frequency scale is tested.

## 5. What remains valid from evidence e508a83f

Still valid and reusable as implementation evidence:

- MFE MTFA/MTFT/MTFS Grid=1 availability;
- operand headers;
- `64->2 / 128->3 / 256->4` Samp mapping;
- MTFA repeatability at identical settings;
- exact `MTFA = (MTFT+MTFS)/2` diagnostic at 20/40/60 cpd for the frequencies that were requested;
- formal manifest reload;
- `ZosMtfaGridAnalysisBackend -> run_analysis_batch` workflow mechanics;
- entity fingerprint invariants;
- ray-health / vignette behavior;
- artifact/environment/run-history plumbing;
- retirement of the `AS_FftMtf` path.

Not acceptable as final science output without revalidation:

- cpd-based HOA MTF values;
- HOA MTFa/DOF50/TF_MTFa_mean;
- HOA 128->256 convergence decision;
- any matched-pair comparison that used different MONO and EDOF EFFL-derived angular scales.

For consistency, all three representative pairs will be rerun with paired-MONO fixed scales rather than correcting HOA alone.

## 6. Corrected validation batch

One local batch should perform:

1. strict TASK-008 manifest preflight;
2. for each of the 3 representative pair keys, read the formal residual-free MONO carrier EFFL once and freeze `pair_reference_effl_mm` / `pair_mm_per_degree` for that run;
3. record both MONO-reference EFFL and EDOF diagnostic EFFL so the scale difference is explicit;
4. run three EDOF representatives at 64/128/256 using the common pair scale;
5. run independent repeat128 for the same three EDOF;
6. run all 6 MONO/EDOF configs at production candidate 128 through `run_analysis_batch`, with each pair sharing one frequency scale;
7. repeat the MTFA-vs-(MTFT+MTFS)/2 diagnostic at 20/40/60 cpd using the paired-MONO scale;
8. write sanitized evidence and STOP.

No TASK-005–008 asset is changed.

## 7. Decision after corrected evidence

If all three 128->256 convergence gates pass under the paired-MONO scale, Web may retain 128 as production candidate and proceed to formal sampling lock.

If any 128->256 convergence gate still fails, then and only then activate the 256-candidate escalation and validate 256->512 without changing the 2%/0.25D gates.

## 8. Supersession note

`docs/TASK_009_SAMPLING_ESCALATION_256_2026-08-19.md` was created before the anomalous HOA angular scale was reviewed. It is therefore **HOLD / not executable** until this paired-MONO scale correction has been tested. It remains in Git history as decision provenance, not active execution authority.
