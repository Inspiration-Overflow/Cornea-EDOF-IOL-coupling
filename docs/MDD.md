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
                    +--> ZosFftMtfAnalysisBackend
                    |       +--> FFT MTF acquisition
                    |       +--> EFFL acquisition
                    |       +--> full-HOA readback
                    |       +--> real-ray footprint/vignetting
                    |       +--> entity fingerprint
                    |
                    +--> run_analysis_batch
                    +--> MTFa/DOF50 post-processing
                    +--> matched-pair delta
      |
      v
ProjectStore / immutable provenance / run history
```

原则：

- GUI 不持有 raw ZOSAPI object；
- ProjectStore 不做光学计算；
- scientific workflows 不根据下游结果回调上游 lock；
- 72-config Run 只消费 TASK-008 frozen manifest；
- representative integration 与 Run72 复用同一个真实 backend/batch contract；
- 一个配置失败不影响其他已成功配置，但 failed 不能伪装 completed。

---

# 2. Modules

| ID | Module | Responsibility | Non-responsibility |
| --- | --- | --- | --- |
| MDD-MOD-001 | `ZosSessionAdapter` | ZOS runtime/license/session lifecycle | 不建模型、不保存科学结果 |
| MDD-MOD-002 | `ProjectStore` | baseline、artifact、hash、lock、run/environment persistence | 不解释光学 |
| MDD-MOD-003 | `ScientificAssetWorkflow` | bases、standard eye、REF/A/B/C build/validate | 不选 B0、不建 carrier |
| MDD-MOD-004 | `B0Workflow` | five-candidate scan、rank、morphology review、B0 lock | 不做复杂优化 |
| MDD-MOD-005 | `CarrierWorkflow` | P→Q(P)、residual gate、18 carrier readiness | 不修改 cornea |
| MDD-MOD-006 | `ManifestBuilder/Loader` | build exact 18/72；strict reload/rebuild/hash verification | 不调用 OpticStudio |
| MDD-MOD-007 | `AnalysisWorkflow` | manifest-driven production analysis、result export、run state | 不修改 carrier/manifest |
| MDD-MOD-008 | `MetricEngine` | unit conversion、MTFa、distance peak、DOF50、TF mean、paired delta | 不传播光学场 |
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
| MDD-API-008 | `FftMtfRunner.run` / `ZosFftMtfAnalysisBackend.run_config` | loaded system or `NominalConfig` | FFT data / complete `ConfigResult` |
| MDD-API-009 | `MfeEfflRunner.run` | loaded system | EFL mm |
| MDD-API-010 | `MfeFullHoaRunner.run` | loaded system + versioned HOA settings | C4/C6/HOA RMS + settings provenance |
| MDD-API-011 | `run_analysis_batch` / `rerun_failed` | backend + manifest + environment + selection | per-config outcomes + artifacts/run records |
| MDD-API-012 | `matched_pair_delta` | completed MONO + EDOF results | EDOF−MONO scalar deltas |
| MDD-API-013 | GUI dispatch | ActionRequest + EventSink | serialized long action + progress events |

---

# 4. Core data structures

## 4.1 `AnalysisSettings`

active instance：`NOMINAL_MAIN_FFT_MTF_555_V2`。

只包含真正影响主 FFT-MTF/MTFa 结果的字段：

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

DOF50 的 50% 是指标定义，不是可调字段。B0 和 HOA readback 使用独立 settings identity。

## 4.2 `CarrierLock`

包含 carrier P/Q/R/CT/material/IOL position/achieved SA 与 residual ID/SHA/policy ID/hash；不把 residual-induced best-focus shift 写入实体 lock identity。

## 4.3 `NominalConfig`

包含 config/carrier/base/cornea/platform/state/pupil、carrier lock hash、EDOF-only residual provenance、555 nm/field0/centered invariants。

TASK-009/Run72 不允许自行重建这些身份；必须由 frozen manifest loader 返回。

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

至少：

```text
config/run identity
15 ThroughFocusRow
distance-peak / MTFa / DOF50 / TF_MTFa_mean
C4/C6/HOA RMS
main-analysis settings hash
HOA settings ID/hash
cornea/STOP/IOL footprints
IOL optical diameter
working model hash before/after
entity fingerprint before/after
retina/IOL/ELP before/after
unintended_vignetting
required artifacts
completed
```

## 4.6 `EntitySnapshot`

in-memory fingerprint 输入至少覆盖 surfaces1..IMAGE 的 role/type/R/Q/thickness/material/STOP、carrier first-order power、retina、IOL position/ELP、surface count。OBJECT thickness 不进入 fingerprint，因为它是冻结的贯焦分析变量；运行结束必须恢复。

## 4.7 `MatchedPairDelta`

主 keys：distance peak、distance peak MTFa、MTFa at zero、DOF50 width、TF mean、C4、C6、HOA RMS。`DeltaF_residual` 等价于 `distance_peak_retina_d` 的 EDOF−MONO delta。

---

# 5. Frozen manifest contract

`load_formal_manifest_bundle()` 必须读取：

```text
manifests/physical_carriers.csv
manifests/nominal_72.csv
manifests/manifest.sha256
```

并完成：

- exact CSV schema；
- 18/72 row count；
- reconstruct 18 locks；
- `build_manifests()` 重新生成 canonical config set；
- loaded 72 rows 与 rebuilt configs 全等；
- `manifest.sha256` 一致；
- TASK-008 evidence 中的 physical/nominal CSV SHA 与 manifest hash 一致；
- 上层重新计算 lock-set hash。

任何差异必须在启动 optical acquisition 前失败。

---

# 6. FFT MTF acquisition contract

## 6.1 Preconditions

- formal TASK-008 manifest/hash/lock-set 有效；
- carrier/residual asset hash 与 evidence / `NominalConfig` 一致；
- wavelength=555 nm；EPD∈{3,5}；field=0；centered；MTF units=cycles/mm。

## 6.2 Settings and runtime metadata

`FftMtfRunner` 显式设置 sampling、maximum frequency、modulation、Wave1、Field1、image surface、no polarization。

结果除频率与 sagittal/tangential modulation 外，必须记录真实：

- analysis API name；
- settings implementation type；
- sample-size enum name；
- modulation enum name；
- DataSeries count/runtime type；
- selected series runtime type；
- SeriesLabels / XLabel。

无法唯一解析列或结果结构即 fail-closed，不得按数组位置猜测。

---

# 7. Frequency / metric contract

EFL 使用临时 MFE `EFFL`，运行后删除。frequency 使用真实 EFL 把 cycles/mm 转 cpd，只在 acquisition support 内插值。

\[
MTF_{avg}=\frac{MTF_{sag}+MTF_{tan}}2
\]

\[
MTFa=\frac1{60}\int_0^{60}MTF_{avg}df
\]

15 planes +0.50→−3.00 D。Distance peak 在 ±0.50D；DOF50=distance-peak MTFa 的 50% 连续区间；TF mean 为完整 3.5D span 的梯形积分均值。

---

# 8. Real backend / production workflow

`ZosFftMtfAnalysisBackend`：

1. 根据 `NominalConfig` 读取/校验 formal carrier；
2. MONO 复制 carrier 为工作模型；EDOF 只附加 manifest 指定 residual；
3. capture entity before；
4. real-ray footprint/vignetting；
5. EFL + 15-plane FFT MTF；
6. 恢复 OBJECT vergence；
7. versioned full-HOA readback；
8. capture entity after；
9. 导出 working `.zmx`、through-focus CSV 与 MTF 图；
10. 返回完整 `ConfigResult`。

`run_analysis_batch` 校验 ConfigResult，并负责 RunEnvironment、running/completed/failed、artifact recording 与配置级失败隔离。

---

# 9. TASK-009 representative contract

代表 pair 由 frozen manifest 选取：

```text
LB+A0+WFS+EPD3
ATC+B0+RAD+EPD5
ATC+C0+HOA+EPD5
```

一次 local task：

1. real FFT-MTF/EFFL/runtime API capability；
2. 3 EDOF × 64/128/256；
3. 3 EDOF × independent repeat128；
4. **6 configs 经 `run_analysis_batch` 正式 production-contract integration**；
5. matched-pair deltas；
6. limited `MTFA Grid=1` diagnostic；
7. sanitized GitHub evidence。

128→256 gate：peak MTFa rel≤2%、TF mean rel≤2%、peak shift≤0.25D、DOF50 width change≤0.25D。

repeatability：peak sample same、peak MTFa rel≤0.1%、TF mean rel≤0.1%、C4/C6 delta≤0.001µm。

本地只能产生 `production_sampling_candidate_passed`；`production_sampling_locked` 在 Web review 前必须保持 false。

---

# 10. Persistence / rerun contract

ProjectStore 保持 `models/locks/manifests/results/logs/environments`。正式 scientific assets immutable；analysis results 可按 run ID 追加。

每 completed config 的 `config_result.json` 与 required artifacts 都注册到 project artifact index。failed config 不注册为 completed；`rerun_failed` 只选择前一批 failed IDs 并生成新 run ID。

---

# 11. Failure behavior

| Failure | Behavior |
| --- | --- |
| ZOS path/license/session | typed failure，显式 close，不记 completed |
| frozen manifest CSV/schema/hash mismatch | optical acquisition 前 fail |
| missing/tampered carrier/residual | optical acquisition 前 fail |
| FFT MTF setting/API/column mismatch | fail with actual runtime metadata；允许机械适配后重试 |
| insufficient 60-cpd support | fail；不得外推 |
| EFL/Zernike/MTF non-finite | fail |
| entity fingerprint / retina / IOL / ELP changed | config fail |
| unintended vignette | config fail |
| export incomplete | config fail；不得 completed |
| convergence/repeatability/6-config integration fail | STOP before Run72 |

---

# 12. Current architectural boundary

TASK-007/008 已完成并冻结。TASK-009 只能改变尚未正式运行的分析层 settings/implementation；不得改变 A0/B0.20/C0、carrier P/R/Q/SA、residual payload/policy、18 lock set 或 72-config manifest identity。
