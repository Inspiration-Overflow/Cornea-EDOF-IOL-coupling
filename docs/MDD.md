# MDD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Module Design Document。将 `ADD-0001 v1.5` 落实为模块、接口、数据结构和失败契约；科学数值由 `URD-0001 v1.5` 提供。

## Metadata

- document_id: `MDD-0001`
- version: `1.4`
- status: `active`
- source_urd: `URD-0001 v1.5`
- source_add: `ADD-0001 v1.5`
- last_updated: `2026-08-19`
- stack: Python + ZOS-API + CustomTkinter
- persistence: local filesystem + CSV/JSON + canonical `.zmx`
- optical_oracle: OpticStudio
- active_analysis_settings: `NOMINAL_MAIN_FFT_MTF_555_v2`

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
      +--> ManifestBuilder
      +--> AnalysisWorkflow
                    |
                    +--> FFT MTF acquisition
                    +--> EFFL acquisition
                    +--> Zernike acquisition
                    +--> MTFa/DOF50 post-processing
      |
      v
ProjectStore / immutable provenance
```

原则：

- GUI 不持有 raw ZOSAPI object；
- ProjectStore 不做光学计算；
- scientific workflows 不根据下游结果回调上游 lock；
- FFT MTF acquisition 与 pure-Python metric engine 分层；
- 72-config Run 只消费 TASK-008 frozen manifest；
- 一个配置失败不影响其他已成功配置，但 failed 不能伪装 completed。

---

# 2. Modules

| ID | Module | Responsibility | Non-responsibility |
| --- | --- | --- | --- |
| MDD-MOD-001 | `ZosSessionAdapter` | ZOS runtime/license/session lifecycle | 不建模型、不保存科学结果 |
| MDD-MOD-002 | `ProjectStore` | baseline、artifact、hash、lock、run/environment persistence | 不解释光学 |
| MDD-MOD-003 | `ScientificAssetWorkflow` | bases、standard eye、REF/A/B/C build/validate | 不选 B0、不建 carrier |
| MDD-MOD-004 | `B0Workflow` | five-candidate scan、rank、morphology review、B0 lock | 不做复杂优化 |
| MDD-MOD-005 | `CarrierWorkflow` | P→Q(P)、residual gate、18 carrier/pair readiness | 不修改 cornea |
| MDD-MOD-006 | `ManifestBuilder` | pure-data 18 carrier / 72 config manifest | 不调用 OpticStudio |
| MDD-MOD-007 | `AnalysisWorkflow` | FFT MTF through-focus、Zernike、footprint、result export | 不修改 carrier/manifest |
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
| MDD-API-007 | `build_manifests` | 18 CarrierLock | exact 18 physical + 72 nominal configs |
| MDD-API-008 | `FftMtfRunner.run` | loaded system + explicit FFT MTF settings | frequency cyc/mm + tangential/sagittal modulation |
| MDD-API-009 | `MfeEfflRunner.run` | loaded system | EFL mm |
| MDD-API-010 | full-HOA Zernike readback | loaded system | C4/C6/HOA RMS source coefficients |
| MDD-API-011 | `run_analysis_batch` | backend + manifest + environment + selection | per-config outcomes + artifacts/run records |
| MDD-API-012 | `matched_pair_delta` | completed MONO + EDOF results | EDOF−MONO scalar deltas |
| MDD-API-013 | GUI dispatch | ActionRequest + EventSink | serialized long action + progress events |

---

# 4. Core data structures

## 4.1 `AnalysisSettings`

active instance：`NOMINAL_MAIN_FFT_MTF_555_V2`。

字段至少包括：

```text
settings_id
wavelength_nm
pupils_mm
defocus_start_d / stop / step
dof_relative_fraction
fft_mtf_sampling
fft_mtf_convergence_samplings
fft_mtf_use_polarization
mtf_frequency_step_cpd
mtfa_max_cpd
mtf_sample_frequencies_cpd
zernike settings
```

`validate()` 必须拒绝 non-finite、非法 sampling、错误 defocus direction、MTF frequency domain 不一致。

## 4.2 `CarrierLock`

包含：

```text
CarrierKey
P / q_source_power / Q
R_ant / R_post
CT / material / IOL position
achieved SA
residual ID/SHA
residual policy ID/hash
lock_hash
```

不把 residual-induced best-focus shift 写入实体 lock identity。

## 4.3 `NominalConfig`

包含：

```text
config_id
carrier_id
base/cornea/platform
MONO or EDOF
pupil_mm
carrier_lock_hash
residual provenance for EDOF only
555 nm / field0 / centered alignment invariants
```

## 4.4 `ThroughFocusRow`

固定：

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
distance_peak_retina_d
distance_peak_mtfa
mtfa_at_zero_d
dof50_far/near/width + censor flags
tf_mtfa_mean
peak_search_censored
C4/C6/HOA RMS
cornea/STOP/IOL footprints
IOL optical diameter
model hash before/after
retina/IOL/ELP before/after
unintended_vignetting
required artifacts
completed
```

## 4.6 `MatchedPairDelta`

主 keys：

```text
distance_peak_retina_d
distance_peak_mtfa
mtfa_at_zero_d
dof50_width_d
tf_mtfa_mean
c40_um
c60_um
hoa_rms_um
```

`DeltaF_residual` 等价于 matched delta 中的 `distance_peak_retina_d`。

---

# 5. FFT MTF acquisition contract

## 5.1 Preconditions

- formal TASK-008 manifest/hash/lock-set 有效；
- `.zmx` carrier hash 与 lock 一致；
- wavelength=555 nm；
- EPD 属于 {3,5} mm；
- field=0；
- MTF units=cycles/mm。

## 5.2 Settings

`FftMtfRunner` 必须显式设置：

- sampling；
- maximum frequency；
- modulation type；
- Wave=1；
- Field=1；
- image surface；
- no polarization；
- diffraction-limit overlay 不作为结果 series。

## 5.3 Result parsing

返回结果必须：

- frequency axis finite、strictly increasing；
- exactly one field series for the requested config；
- 可唯一识别 tangential / sagittal modulation columns；
- MTF finite、non-negative；
- acquisition frequency support 足够覆盖转换后的 60 cpd。

无法唯一解析列或结果结构即 fail-closed；不得根据数组位置静默猜测。

---

# 6. Frequency / metric contract

## 6.1 EFL

使用临时 MFE `EFFL` operand 读取有效焦距；operand 必须运行后删除，MFE 恢复原状。

## 6.2 cycles/mm→cpd

\[
mm/deg=EFL_{mm}\tan(1^\circ)
\]

\[
f_{cpd}=f_{cyc/mm}\cdot mm/deg
\]

只在 acquisition support 内插值。

## 6.3 Average MTF

\[
MTF_{avg}=\frac{MTF_{sag}+MTF_{tan}}2
\]

## 6.4 MTFa

\[
MTFa=\frac1{60}\int_0^{60}MTF_{avg}df
\]

0..60 cpd、1-cpd common grid，梯形积分。

## 6.5 Through-focus

15 planes：+0.50→−3.00 D；分析层通过 object vergence 改变，不保存临时实体状态。

Distance peak：±0.50 D 内最大 MTFa；tie = minimum |D| then larger signed D。

DOF50：threshold = 0.5×distance-peak MTFa；必须取包含 distance peak 的连续区间。

TF mean：对完整冻结 defocus span 的 MTFa 梯形积分除以 3.5 D。

---

# 7. TASK-009 representative module contract

`run_task_009_fft_mtf_representative.py` 只允许读取 frozen TASK-008 assets。

代表 set：

```text
LB+A0+WFS+EPD3
ATC+B0+RAD+EPD5
ATC+C0+HOA+EPD5
```

一次 session 内：

1. 验证 FFT MTF/EFFL API；
2. 三 EDOF × 64/128/256 sampling；
3. 三 EDOF × repeat 128；
4. 三 matched MONO+EDOF × 128；
5. 少量 `MTFA Grid=1` diagnostic cross-check；
6. sanitized evidence 写 GitHub，large `.zmx` 留 project diagnostics。

### convergence

128→256：

- peak MTFa rel ≤2%；
- TF mean rel ≤2%；
- peak shift ≤0.25 D；
- DOF50 width change ≤0.25 D。

### repeatability

- peak grid sample same；
- peak MTFa rel ≤0.1%；
- TF mean rel ≤0.1%；
- C4/C6 delta ≤0.001 µm。

cross-check 只记录差异，不自行设新的 acceptance threshold。

---

# 8. Persistence contract

ProjectStore 保持：

```text
models/
locks/
manifests/
results/
logs/
environments/
```

所有 formal scientific artifacts：

- path 必须在 project root；
- SHA-256 写 artifact index；
- immutable lock 同 ID 不允许不同内容覆盖；
- run environment 保存 program/OpticStudio/baseline/settings/manifest/lock-set identity。

TASK-009 representative evidence 为 evidence-only，不修改 TASK-008 formal lock。

---

# 9. Failure behavior

| Failure | Behavior |
| --- | --- |
| ZOS path/license/session | typed failure，显式 close，不记 completed |
| manifest/hash mismatch | 不进入 analysis |
| missing formal carrier/residual | fail before optical acquisition |
| FFT MTF setting/API mismatch | fail with actual API/header evidence；允许机械适配后重试 |
| insufficient 60-cpd support | fail；不得外推 |
| EFL/Zernike/MTF non-finite | fail |
| model/retina/IOL/ELP changed | config fail |
| unintended vignette | config fail |
| TASK-009 convergence/repeatability fail | STOP before Run72 |
| export incomplete | config fail；不得 completed |

---

# 10. Current architectural boundary

TASK-007/008 已完成并冻结。TASK-009 只能改变尚未正式运行的分析层 settings/implementation；不得改变：

- A0/B0.20/C0；
- carrier P/R/Q/SA；
- residual payload/policy；
- 18 carrier lock set；
- 72-config manifest identity。
