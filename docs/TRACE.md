# TRACE — Project Map / Traceability

> Current authority map for `URD-0001 v1.6` / `ADD-0001 v1.6` / `MDD-0001 v1.5` / `TDD-0001 v1.6`.  
> Historical IDs from older document versions are intentionally not carried forward here; Git history remains their provenance.

## 1. URD requirements → ADD functional requirements

| Source | Relation | Target | Current meaning |
| --- | --- | --- | --- |
| URD-REQ-001 | refines_to | FR-001 | Python + ZOS-API / OpticStudio lifecycle |
| URD-REQ-002 | refines_to | FR-002 | baseline/settings/hash/immutable provenance |
| URD-REQ-003 | refines_to | FR-003 | LB/ATC bases |
| URD-REQ-004 | refines_to | FR-003 | `STD_IOL_EYE_2024` EPD6 calibration asset |
| URD-REQ-005 | refines_to | FR-003, FR-004 | A0/B0.20/C0 freeze and B0 lock |
| URD-REQ-006 | refines_to | FR-005 | platform SA targets + power-specific Q(P) |
| URD-REQ-007 | refines_to | FR-005 | 18 independent physical carriers |
| URD-REQ-008 | refines_to | FR-005, FR-008 | matched MONO/EDOF identity; residual-only difference |
| URD-REQ-009 | refines_to | FR-005 | residual payload / low-order / calibration gate |
| URD-REQ-010 | refines_to | FR-006 | exact 18/72 immutable manifests and strict reload |
| URD-REQ-011 | refines_to | FR-007 | frozen main numerical settings + MFE MTFA Grid=1 acquisition + paired residual-free MONO EFFL angular scale |
| URD-REQ-012 | refines_to | FR-007 | retina/carrier/IOL/ELP/entity invariants |
| URD-REQ-013 | refines_to | FR-007 | per-config MTFa/MTF/aberration/footprint/settings/provenance |
| URD-REQ-014 | refines_to | FR-008 | 36 EDOF−MONO matched deltas |
| URD-REQ-015 | refines_to | FR-009 | failed-target isolation and rerun |
| URD-REQ-016 | refines_to | FR-007, FR-009 | repeatability under identical frozen inputs |
| URD-REQ-017 | refines_to | FR-010 | minimal desktop workflow shell |
| URD-REQ-018 | refines_to | FR-002, FR-007, FR-009 | structured results and auditable artifacts |

## 2. ADD FR → DP

| Source | Relation | Target |
| --- | --- | --- |
| FR-001 | satisfied_by | DP-001 |
| FR-002 | satisfied_by | DP-002 |
| FR-003 | satisfied_by | DP-003 |
| FR-004 | satisfied_by | DP-004 |
| FR-005 | satisfied_by | DP-005 |
| FR-006 | satisfied_by | DP-006 |
| FR-007 | satisfied_by | DP-007 |
| FR-008 | satisfied_by | DP-008 |
| FR-009 | satisfied_by | DP-009 |
| FR-010 | satisfied_by | DP-010 |

## 3. ADD DP → MDD modules / public APIs

| Source | Relation | Target |
| --- | --- | --- |
| DP-001 | implemented_by | MDD-MOD-001 / MDD-API-001 |
| DP-002 | implemented_by | MDD-MOD-002 / MDD-API-002 / MDD-API-003 |
| DP-003 | implemented_by | MDD-MOD-003 / MDD-API-004 |
| DP-004 | implemented_by | MDD-MOD-004 / MDD-API-005 |
| DP-005 | implemented_by | MDD-MOD-005 / MDD-API-006 |
| DP-006 | implemented_by | MDD-MOD-006 / MDD-API-007 |
| DP-007 | implemented_by | MDD-MOD-007 / MDD-API-008 / MDD-API-009 / MDD-API-010 / MDD-API-011 |
| DP-008 | implemented_by | MDD-MOD-008 / MDD-API-012 |
| DP-009 | implemented_by | MDD-MOD-009 / MDD-API-011 |
| DP-010 | implemented_by | MDD-MOD-010 / MDD-API-013 |

## 4. URD acceptance → TDD oracle

| Source | Relation | Target |
| --- | --- | --- |
| URD-AC-001 | verified_by | TDD-TEST-001 |
| URD-AC-002 | verified_by | TDD-TEST-002 |
| URD-AC-003 | verified_by | TDD-TEST-003 |
| URD-AC-004 | verified_by | TDD-TEST-004 / TDD-TEST-005 |
| URD-AC-005 | verified_by | TDD-TEST-006 / TDD-TEST-008 / TDD-TEST-109 |
| URD-AC-006 | verified_by | TDD-TEST-108 / TDD-TEST-999 |
| URD-AC-007 | verified_by | TDD-TEST-109 / TDD-TEST-110 |
| URD-AC-008 | verified_by | TDD-TEST-201 / TDD-TEST-202 / TDD-TEST-203 / TDD-TEST-204 / TDD-TEST-205 / TDD-TEST-206 / TDD-TEST-207 |
| URD-AC-009 | verified_by | TDD-TEST-401 / TDD-TEST-402 / TDD-TEST-403 |
| URD-AC-010 | verified_by | TDD-TEST-301 / TDD-TEST-302 / TDD-TEST-303 / TDD-TEST-401 |

## 5. Main-analysis implementation trace

| Requirement / test | Implemented or exercised by |
| --- | --- |
| URD-REQ-010 / TDD-TEST-110 | `src/whole_eye_mvp/manifest_io.py` |
| URD-REQ-011 / TDD-TEST-201 | `src/whole_eye_mvp/zos/mfe_mtfa.py`, `src/whole_eye_mvp/zos/mfe_mtf_grid.py`, `src/whole_eye_mvp/analysis_zos_pair_scale.py` |
| TDD-TEST-202 | `src/whole_eye_mvp/zos/mfe_effl.py` + `measure_pair_mono_reference()` in `analysis_zos_pair_scale.py` |
| TDD-TEST-203 | `frequencies_for_pair_reference()` + `paired_residual_free_MONO_EFFL` contract in `analysis_zos_pair_scale.py` |
| URD-REQ-013 aberrations | `src/whole_eye_mvp/zos/mfe_hoa_full.py` |
| URD-REQ-011 metrics | `src/whole_eye_mvp/metrics.py` |
| URD-REQ-012 / TDD-TEST-302 | `capture_entity_snapshot` in `src/whole_eye_mvp/analysis_zos.py` |
| URD-REQ-013 / TDD-TEST-301 | `ConfigResult` + `ZosMtfaPairScaleAnalysisBackend` |
| URD-REQ-014 / TDD-TEST-303 | `matched_pair_delta` |
| URD-REQ-015 | `run_analysis_batch` / failed-only TASK-011 resume path |
| TDD-TEST-204/205 | corrected paired-MONO-scale TASK-009 representative batch |
| TDD-TEST-206 | frozen-manifest selection + `ZosMtfaPairScaleAnalysisBackend` + `run_analysis_batch` |
| TDD-TEST-207 | limited independent MFE extraction diagnostic in TASK-009 evidence |
| URD-AC-009 | Run72 acceptance in `src/whole_eye_mvp/acceptance.py`, `src/whole_eye_mvp/run72.py`, `scripts/run_task_011_run72.py` |
| TASK-011 formal matrix | 72 configs / 36 matched pairs / 1080 through-focus rows in `docs/evidence/task011/` |
| TASK-012 analysis | frozen plan in `docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md`; implementation pending |

## 6. Versioned settings / acquisition trace

| Identity | SHA-256 | Scope |
| --- | --- | --- |
| `NOMINAL_MAIN_FFT_MTF_555_v2` | `0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc` | historical settings ID retained for hash continuity; current Run72 numerical grid/settings |
| `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2` | `f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d` | active production MFE MTFA Grid=1 acquisition with paired residual-free MONO EFFL scale |
| `TASK009_MFE_ZERN_HOA_555_v1` | `7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2` | whole-eye C4/C6/HOA RMS readback |
| `CORNEA_LOCK_B0_555_v2` | `aee210e884aa59f74e2963efddca9fc789f2b4e85de521606348d1e586790b8e` | historical frozen B0 selection acquisition |

Active frequency-scale mode:

```text
paired_residual_free_MONO_EFFL
```

Formal Run72 pair-reference set:

```text
pair_reference_count = 36
pair_reference_set_sha256 = a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
```

## 7. Frozen provenance

- TASK-007 reviewed evidence: `docs/evidence/task007/consolidated_review/TASK_007_CONSOLIDATED_REVIEW.json`.
- TASK-008 formal evidence: `docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json`.
- TASK-009 corrected representative evidence commit: `47f901dad36fb9d407826a6da8baceeef4c2edfd`.
- TASK-009 active production acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2` with `paired_residual_free_MONO_EFFL`, sampling 128.
- TASK-011 formal Run72 code baseline: `01f13b768cf1eca361703469b2fdce3d21f3376d`.
- TASK-011 formal evidence commit: `f28b3032136aa28f54abb5fe5129765a125d3926`.
- TASK-011 formal evidence: `docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json` plus config, through-focus and paired-delta CSVs.
- TASK-012 frozen analysis plan: `docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md`.
- TASK-005–009 scientific/method locks remain read-only during TASK-011/TASK-012.
