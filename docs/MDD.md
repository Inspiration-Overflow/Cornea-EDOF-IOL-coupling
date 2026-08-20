# MDD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Module Design Document。将 `ADD-0001 v1.6` 落实为模块、接口、数据结构和失败契约；科学数值由 `URD-0001 v1.6` 提供。

## Metadata

- document_id: `MDD-0001`
- version: `1.5`
- status: `active`
- source_urd: `URD-0001 v1.6`
- source_add: `ADD-0001 v1.6`
- last_updated: `2026-08-19`
- stack: Python + ZOS-API + CustomTkinter
- persistence: local filesystem + CSV/JSON + canonical `.zmx`
- optical_oracle: OpticStudio
- active_analysis_settings: `NOMINAL_MAIN_FFT_MTF_555_v2`
- active_analysis_settings_sha256: `0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc`
- active_mtf_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_mtf_acquisition_sha256: `f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d`
- active_frequency_scale_mode: `paired_residual_free_MONO_EFFL`
- active_production_sampling: `128`
- active_hoa_settings: `TASK009_MFE_ZERN_HOA_555_v1`

---

# 1. Architecture

```text
DesktopAppShell
      |
      v
Workflow dispatch
      |
      +--> ScientificAssetWorkflow
      +--> B0Workflow
      +--> CarrierWorkflow
      +--> ManifestBuilder / ManifestLoader
      +--> AnalysisWorkflow
                    |
                    +--> pair MONO EFFL reference
                    +--> ZosMtfaPairScaleAnalysisBackend
                    |       +--> MFE MTFA Grid=1 production acquisition
                    |       +--> full-HOA readback
                    |       +--> real-ray footprint/vignetting
                    |       +--> entity fingerprint
                    |
                    +--> run_analysis_batch
                    |       +--> RunEnvironment/backend provenance gate
                    +--> MTFa/DOF50 post-processing
                    +--> matched-pair delta
      |
      v
ProjectStore / immutable provenance / run history
```

原则：GUI 不持有 raw ZOSAPI object；ProjectStore 不做光学计算；scientific workflows 不根据下游结果回调上游 lock；72-config Run 只消费 TASK-008 frozen manifest；representative integration 与 Run72 复用同一个真实 backend/batch contract；一个配置失败不影响其他已成功配置。

`AS_FftMtf` production path 已退休。`NOMINAL_MAIN_FFT_MTF_555_v2` 与 `fft_mtf_*` 字段名仅保留历史 hash 兼容，不代表实际 production acquisition。

---

# 2. Modules

| ID | Module | Responsibility | Non-responsibility |
| --- | --- | --- | --- |
| MDD-MOD-001 | `ZosSessionAdapter` | ZOS runtime/license/session lifecycle | 不建模型、不保存科学结果 |
| MDD-MOD-002 | `ProjectStore` | baseline、artifact、hash、lock、run/environment persistence | 不解释光学 |
| MDD-MOD-003 | `ScientificAssetWorkflow` | bases、standard eye、REF/A/B/C build/validate | 不选 B0、不建 carrier |
| MDD-MOD-004 | `B0Workflow` | five-candidate scan、rank、morphology review、B0 lock | 不做复杂优化 |
| MDD-MOD-005 | `CarrierWorkflow` | P→Q(P)、residual gate、18 carrier readiness | 不修改 cornea |
| MDD-MOD-006 | `ManifestBuilder/Loader` | build exact18/72；strict reload/rebuild/hash verification | 不调用 OpticStudio |
| MDD-MOD-007 | `AnalysisWorkflow` | pair-reference + manifest-driven production analysis + result/run state | 不修改 carrier/manifest |
| MDD-MOD-008 | `MetricEngine` | cpd映射、MTFa、distance peak、DOF50、TF mean、paired delta | 不传播光学场 |
| MDD-MOD-009 | `Acceptance` | 72/36/1080 completeness、repeatability、rerun eligibility | 不改变科学设置 |
| MDD-MOD-010 | `DesktopAppShell` | 极简 UI 与 action dispatch | 不持有 scientific truth |

---

# 3. Public interfaces

| ID | Interface | Inputs | Outputs / side effects |
| --- | --- | --- | --- |
| MDD-API-001 | `open_zos_session` | install dir | context-managed ZOS session；显式 close |
| MDD-API-002 | `open_project_store` | project dir + baseline | verified ProjectStore |
| MDD-API-003 | `record_artifact` | source + ArtifactRecord + lock flag | copied/hashed ArtifactRef |
| MDD-API-004 | `build_scientific_assets` | session/store/baseline | core `.zmx` + validation |
| MDD-API-005 | `run_b0_scan` / `lock_b0` | frozen B0 settings + review decisions | scan evidence / immutable B0 lock |
| MDD-API-006 | carrier build/finalize | frozen scientific assets + residual definitions | 18 formal locks after gates |
| MDD-API-007 | `build_manifests` / `load_formal_manifest_bundle` | locks or frozen TASK-008 files | exact verified `ManifestBundle` |
| MDD-API-008 | `measure_pair_mono_reference` / `ZosMtfaPairScaleAnalysisBackend.run_config` | formal MONO pair + `NominalConfig` | pair scale / complete `ConfigResult` |
| MDD-API-009 | `MfeEfflRunner.run` | loaded residual-free MONO or diagnostic state | EFL mm |
| MDD-API-010 | `MfeFullHoaRunner.run` | loaded system + versioned HOA settings | C4/C6/HOA RMS + settings provenance |
| MDD-API-011 | `run_analysis_batch` / `rerun_failed` | backend + manifest + RunEnvironment + selection | per-config outcomes + artifacts/run records |
| MDD-API-012 | `matched_pair_delta` | completed MONO + EDOF results | EDOF−MONO scalar deltas |
| MDD-API-013 | GUI dispatch | ActionRequest + EventSink | serialized long action + progress events |

---

# 4. Core data structures

## 4.1 `AnalysisSettings`

active instance：`NOMINAL_MAIN_FFT_MTF_555_V2`。

字段：

```text
settings_id
wavelength_nm
pupils_mm
defocus_start_d / stop / step
fft_mtf_sampling
fft_mtf_convergence_samplings
fft_mtf_use_polarization
mtf_frequency_step_cpd
mtfa_max_cpd
mtf_sample_frequencies_cpd
```

`fft_mtf_*` 为历史字段名；其数值语义是主 MTF sampling/convergence/polarization。继续保留是为了保持 `NOMINAL_MAIN_FFT_MTF_555_v2` hash，不得据名称恢复已退休的 FFT-MTF Analysis path。

## 4.2 `CarrierLock`

包含 carrier P/Q/R/CT/material/IOL position/achieved SA 与 residual ID/SHA/policy ID/hash；不含 residual-induced best-focus shift。

## 4.3 `NominalConfig`

包含 config/carrier/base/cornea/platform/state/pupil、carrier lock hash、EDOF-only residual provenance、555nm/field0/centered invariants。TASK-009/Run72 必须由 frozen manifest loader 返回，不允许自行重建。

## 4.4 `ThroughFocusRow`

```text
defocus_retina_d
defocus_shape_d
mtfa
mtf10
mtf20
mtf30
mtf40
mtf50
mtf60
```

## 4.5 `ConfigResult`

至少保存 config/run identity、15 rows、distance-peak/MTFa/DOF50/TF mean、C4/C6/HOA RMS、main settings hash、HOA settings ID/hash、footprints、model/entity invariants、retina/IOL/ELP、required artifacts、completed。

Acquisition contract 与 frequency-scale mode 属于 run-level provenance，并由 `RunEnvironment` 与 backend 一致性 gate 强制；每 config 的 runtime diagnostic 仍记录实际 pair reference EFFL、state diagnostic EFFL、target cycles/mm 与 MFE runtime metadata。

## 4.6 `EntitySnapshot`

fingerprint 输入覆盖 surfaces1..IMAGE 的 role/type/R/Q/thickness/material/STOP、carrier first-order power、retina、IOL position/ELP、surface count。OBJECT thickness 不进入 fingerprint，因为它是贯焦分析变量；运行结束必须恢复。

## 4.7 `MatchedPairDelta`

keys：distance peak、distance peak MTFa、MTFa at zero、DOF50 width、TF mean、C4、C6、HOA RMS。`DeltaF_residual` 等价于 `distance_peak_retina_d` 的 EDOF−MONO delta。

## 4.8 `RunEnvironment`

必须包含非空：

```text
program_version
opticstudio_version
baseline_id
analysis_settings_id
manifest_hash
lock_set_hash
acquisition_contract_id
acquisition_contract_hash
frequency_scale_mode
```

其中正式 Run72 必须使用：

```text
acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_hash = f7f1551e...
frequency_scale_mode = paired_residual_free_MONO_EFFL
```

---

# 5. Frozen manifest contract

`load_formal_manifest_bundle()` 读取：

```text
manifests/physical_carriers.csv
manifests/nominal_72.csv
manifests/manifest.sha256
```

完成 exact schema、18/72 row count、reconstruct18 locks、rebuild72 configs、loaded==rebuilt、manifest hash、TASK-008 evidence SHA、lock-set hash。任何差异在 optical acquisition 前 fail。

---

# 6. Production MTF acquisition contract

## 6.1 Preconditions

- formal TASK-008 manifest/hash/lock-set 有效；
- carrier/residual SHA 与 evidence/`NominalConfig` 一致；
- wavelength=555nm；EPD∈{3,5}；field0；centered；MTF units=cycles/mm；
- `TASK009_PRODUCTION_SAMPLING_LOCK_v1` 已锁 sampling=128；
- RunEnvironment acquisition provenance 与 backend 完全一致。

## 6.2 Pair scale

每个 `pair_key` 先由 residual-free MONO formal carrier 在 nominal distance 读取一次 EFFL：

\[
mm/degree=EFL_{MONO}\tan(1^\circ)
\]

同一 scale 用于 MONO、EDOF、全部 defocus 和 sampling。EDOF/state EFFL 只记录诊断，不改变生产频率坐标。

## 6.3 MTFA Grid=1

0..60 cpd / 1-cpd grid 直接映射为 cycles/mm query targets。每个 defocus plane 使用：

```text
MFE MTFA
Grid=1
Data Type=0
Wave=1
Field=1
```

sampling：64→Samp2，128→Samp3，256→Samp4。正式生产=128。

MFE `MTFT/MTFS` 只作 limited diagnostic，不构成 production path。

---

# 7. Frequency / metric contract

\[
MTFa=\frac1{60}\int_0^{60}MTFA(f)df
\]

1-cpd grid + trapezoidal integration。15 planes +0.50→−3.00D。Distance peak 在±0.50D；DOF50=distance-peak MTFa的50%连续区间；TF mean为完整3.5D span积分均值。

不做 native MTF curve interpolation，不允许 per-state EFFL 改变 matched-pair cpd 坐标。

---

# 8. Real backend / production workflow

`ZosMtfaPairScaleAnalysisBackend`：

1. 校验 formal carrier/residual SHA；
2. MONO 复制 carrier；EDOF 只附加 manifest residual；
3. capture entity before；
4. footprint/vignetting；
5. 读取 state diagnostic EFFL，但 production frequency 使用预先冻结 pair MONO EFFL；
6. 15-plane MFE MTFA Grid=1；
7. 恢复 OBJECT vergence；
8. full-HOA readback；
9. capture entity after；
10. 导出 working `.zmx`、through-focus CSV、图；
11. 返回 `ConfigResult`。

`run_analysis_batch()` 在运行前检查 environment baseline/settings/manifest/lock-set，并检查 backend 的 acquisition ID/hash/scale 与环境完全一致；随后负责 running/completed/failed、artifact recording 与配置级失败隔离。

---

# 9. TASK-009 representative contract

代表 pair：LB+A0+WFS+EPD3、ATC+B0+RAD+EPD5、ATC+C0+HOA+EPD5。

128→256 gate：peak MTFa rel≤2%、TF mean rel≤2%、peak shift≤0.25D、DOF50 width change≤0.25D。repeat128：peak sample same、peak MTFa rel≤0.1%、TF mean rel≤0.1%、C4/C6≤0.001µm。

Corrected pair-MONO-scale evidence 已全部 PASS；6-config real production integration 6/6；limited 20/40/60 cpd diagnostic PASS；Web formal sampling lock=128；256→512 escalation inactive。

---

# 10. Persistence / rerun contract

ProjectStore 保持 `models/locks/manifests/results/logs/environments`。正式 scientific assets immutable；analysis results 按 run ID 追加。每 completed config 的 `config_result.json` 与 required artifacts 注册 artifact index。failed 不注册 completed；`rerun_failed` 只选择失败 IDs 并生成新 run ID。

---

# 11. Failure behavior

| Failure | Behavior |
| --- | --- |
| ZOS path/license/session | typed failure，显式 close，不记 completed |
| frozen manifest/schema/hash mismatch | acquisition 前 fail |
| carrier/residual SHA mismatch | acquisition 前 fail |
| pair MONO EFFL non-finite | fail |
| backend acquisition ID/hash/scale 与 RunEnvironment 不同 | acquisition 前 fail |
| MFE MTFA operand/header/sampling mapping mismatch | fail |
| Zernike/MTF non-finite | fail |
| entity fingerprint / retina / IOL / ELP changed | config fail |
| unintended vignette | config fail |
| export incomplete | config fail；不得 completed |
| Run72 incomplete | overall acceptance fail；允许 failed-only rerun |

---

# 12. Current architectural boundary

TASK-005–008 scientific assets 已冻结只读；TASK-009 corrected pair-MONO analysis gate 已 PASS，sampling=128 已 formal lock。后续可实现/执行 Run72 和必要 GUI smoke，但不得改变 A0/B0.20/C0、carrier P/R/Q/SA、residual payload/policy、18 lock set、72-config manifest、pair-MONO frequency-scale definition 或已锁 sampling。