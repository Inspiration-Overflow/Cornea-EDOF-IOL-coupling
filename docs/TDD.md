# TDD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Test-Driven / Check Plan。目标是用少量高价值 oracle 发现模型、锁、指标或 72-config 执行错误。  
> **来源：** `URD-0001 v1.6`、`ADD-0001 v1.6`、`MDD-0001 v1.5`。

## Metadata

- document_id: `TDD-0001`
- version: `1.6`
- status: `active`
- last_updated: `2026-08-19`
- target_test_runner: pytest
- optical_integration_environment: Windows + OpticStudio 2026 R1 + valid ZOS-API license
- active_main_settings: `NOMINAL_MAIN_FFT_MTF_555_v2`
- active_main_settings_sha256: `0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc`
- active_mtf_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_mtf_acquisition_sha256: `f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d`
- active_frequency_scale_mode: `paired_residual_free_MONO_EFFL`
- production_sampling: `128`
- production_sampling_lock: `TASK009_PRODUCTION_SAMPLING_LOCK_v1`
- active_hoa_settings: `TASK009_MFE_ZERN_HOA_555_v1`
- active_hoa_settings_sha256: `7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2`

---

# 1. Test decisions

| ID | Decision |
| --- | --- |
| TDD-DEC-001 | 主生产 MTF 使用 MFE `MTFA Grid=1`；每 matched pair 使用 residual-free MONO EFFL 固定角尺度；Python 只做确定性频率映射、MTFa、贯焦摘要和 paired delta。 |
| TDD-DEC-002 | 标准眼 carrier SA calibration 固定 EPD6、约546 nm；主实验 EPD3/5 不改变 Q(P) calibration。 |
| TDD-DEC-003 | B0 lock 使用独立 `CORNEA_LOCK_B0_555_v2`，不进入 main-analysis settings identity。 |
| TDD-DEC-004 | DOF50 是固定 50% distance-peak MTFa 的命名指标，不是可调 settings 字段。 |
| TDD-DEC-005 | `DeltaF_residual` 是 matched analysis result，不进入 physical carrier lock identity。 |
| TDD-DEC-006 | TASK-009 代表配置必须来自 frozen TASK-008 manifest；6-config integration 必须走真实 `AnalysisBackend → run_analysis_batch`。 |
| TDD-DEC-007 | numerical settings、MTF acquisition/scale contract、HOA readback settings 分开版本化并分别记录 identity。 |
| TDD-DEC-008 | 本地 TASK-009 只生成 evidence；正式 sampling lock 所有权在 Web。Corrected evidence 已通过，Web 已正式锁定 sampling=128。 |
| TDD-DEC-009 | `MTFT/MTFS` limited extraction check 不定义新 acceptance threshold；只检查 operand/frequency/direction mapping。 |

`AS_FftMtf` production path 已退休。代码中的 `NOMINAL_MAIN_FFT_MTF_555_v2` 和 `fft_mtf_*` 字段名仅为保持冻结 settings hash，不构成 FFT-MTF Analysis 的 active test authority。

---

# 2. Frozen settings / contracts

## 2.1 B0 lock settings

```text
settings_id = CORNEA_LOCK_B0_555_v2
wavelength = 555 nm
EPD = 3 / 5 mm
defocus = +0.50 → -3.50 D
step = -0.25 D
MFE MTFA Grid = 0
Data Type = 0
Samp = 3
frequency = 0..50 cycles/mm
frequency step = 5 cycles/mm
```

只用于 B0 selection provenance。

## 2.2 Main numerical settings

```text
settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
wavelength = 555 nm
EPD = 3 / 5 mm
field = 0 deg
defocus = +0.50 → -3.00 D
step = -0.25 D
planes = 15
production sampling = 128
convergence samplings = 64 / 128 / 256
polarization = false
MTF common grid = 0..60 cpd
frequency step = 1 cpd
reported fixed frequencies = 10/20/30/40/50/60 cpd
```

## 2.3 Production MTF acquisition / scale

```text
contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
operand = MTFA
Grid = 1
Data Type = 0
Wave = 1
Field = 1
frequency_scale_mode = paired_residual_free_MONO_EFFL
sampling mapping = 64→Samp2, 128→Samp3, 256→Samp4
```

Formal sampling lock：

```text
TASK009_PRODUCTION_SAMPLING_LOCK_v1
production_sampling_locked = true
production_sampling = 128
sampling_escalation_256_active = false
```

## 2.4 HOA readback settings

```text
settings_id = TASK009_MFE_ZERN_HOA_555_v1
settings_sha256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
MFE operand = ZERN
Wave = 1
Field = 1
Samp = 1
Type = 1
Epsilon = 0
Vertex = 0
terms = Z7..Z28
```

---

# 3. Metric oracle

## 3.1 Paired-MONO angular-frequency scale

每个 frozen pair 只从 residual-free MONO nominal-distance model 得到一个 reference：

\[
mm/deg=EFL_{MONO}\tan(1^\circ)
\]

\[
f_{cyc/mm}=\frac{f_{cpd}}{mm/deg}
\]

要求 MONO reference EFL finite positive，并绑定 pair key、MONO config ID、model SHA 与 entity fingerprint。同一 reference 必须用于该 pair 的 MONO、EDOF、所有 defocus、所有 sampling。EDOF/state EFFL 仅为诊断，不得改变生产 cpd 轴。

## 3.2 MTFa

生产输入直接为 MFE `MTFA Grid=1`：

\[
MTFa=\frac1{60}\int_0^{60}MTFA(f)df
\]

1-cpd grid + trapezoidal integration。Pure-math oracle：constant MTFA=0.5 → MTFa=0.5，算术容差≤1e-10。

`MTFT/MTFS` 只用于 limited diagnostic；20/40/60 cpd 的方向平均检查为：

\[
MTFA=\frac{MTFT+MTFS}{2}
\]

该检查不成为第二条 production path。

## 3.3 Distance peak / DOF50 / TF mean

Distance peak：±0.50D 内最大 MTFa；tie 先 minimum |D|，再 larger signed D；边界峰标 censored。

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

DOF50 从 distance peak 向两侧取连续 ≥T50 区间，crossing 线性插值，不外推。

\[
TF\_MTFa\_mean=\frac1{3.5D}\int_{-3.0}^{+0.5}MTFa(F)dF
\]

必须对 defocus 数组方向不敏感。

---

# 4. Scientific asset acceptance

| ID | Scenario | Oracle |
| --- | --- | --- |
| TDD-TEST-001 | ZOS session | valid runtime→non-null system + explicit close；bad path/license→typed failure，无假 completed |
| TDD-TEST-002 | bases | AL=23.950/24.477±0.001 mm；STOP/IOL landmarks 与 URD 一致 |
| TDD-TEST-003 | standard eye | EPD=6.000±0.001 mm；corneal C40=+0.258±0.005 µm；footprint=5.15±0.10 mm；λ≈546 nm |
| TDD-TEST-004 | A/B/B0 | A0 与五 B candidate 达 target；B0 review/rank/hash 可复算；B0.20 immutable |
| TDD-TEST-005 | C0 | near3.0、ADD+1.75D、OZ6.5、transition0.75、N8、convergence PASS |
| TDD-TEST-006 | Q(P) | 18 carriers replay standard eye EPD6；WFS−0.20±0.01、RAD−0.27±0.01、HOA0±0.01 µm；q_source_power==P |
| TDD-TEST-007 | matched carrier | 同平台 MONO/EDOF P/R/Q/CT/material/position 完全相同；EDOF 只增加 residual |
| TDD-TEST-008 | exact physical locks | exactly 18 unique Base×Cornea×Platform locks |
| TDD-TEST-009 | exact nominal manifest | exactly 72 configs、36 pair keys、EPD3/5、555nm、field0、centered |

---

# 5. Residual science gate

## TDD-TEST-108 — residual actual-power calibration

每平台 formal carrier power 的 low/median/high 三点必须具备 payload/version/hash、EPD6 standard-eye imported residual low-order readback、ray health 与 mechanism review；共9 records。

冻结 gate：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

actual-eye sag readback只作诊断。

## TDD-TEST-999 — carrier/residual science STOP

versioned residual payload + frozen low-order policy + low/median/high calibration + mechanism review 全部具备后才可正式锁 carrier/residual。当前 evidence 已通过且 `tdd_999_cleared=true`；TASK-009 不重新解释该科学 evidence。

---

# 6. TASK-008 manifest tests

## TDD-TEST-109 — lock/hash integrity

18 carrier 与3 residual asset/validation SHA 必须与 artifact index 一致，locked=true，baseline=`MVP_2026_v2`，lock-set hash 稳定；tampered/missing/duplicate lock 拒绝 manifest。

## TDD-TEST-110 — frozen manifest reload semantics

必须 strict-load `physical_carriers.csv`、`nominal_72.csv`、`manifest.sha256`，并满足 exact18/72 rows、schema/version exact、18 locks 可重建、`build_manifests()` 重新生成的72 configs 与 loaded CSV 全等、manifest/lock-set 与 TASK-008 evidence 一致。MONO residual provenance empty；EDOF complete；555nm、EPD3/5、field0、alignment/monovision=0。

任一 tamper 必须在 OpticStudio acquisition 前 fail。

---

# 7. TASK-009 real API / production gate

## TDD-TEST-201 — MFE MTFA Grid=1 capability

真实 OpticStudio 2026 R1 必须验证：

- `MTFA`、`MTFT`、`MTFS` operands 可写入/读取；
- Grid=1、Data Type=0、Wave1、Field1；
- sampling mapping 64→2、128→3、256→4；
- frequency parameter headers/API mapping 明确；
- cycles/mm 输入与返回 finite；
- MFE 临时 rows 可恢复，不污染模型。

`AS_FftMtf` / `New_FftMtf()` 不再是 active capability prerequisite。

## TDD-TEST-202 — paired MONO EFFL capability

每 representative pair 的 residual-free MONO nominal-distance EFFL 必须 finite positive，并记录 pair key、MONO config ID、model SHA、entity fingerprint。EDOF/state EFFL 可记录为 diagnostic，但不得用于 production frequency scale。

## TDD-TEST-203 — cpd target coverage / mapping

对 0..60 cpd common grid，必须使用 pair MONO reference 计算直接 cycles/mm targets；60 cpd target finite positive。MONO/EDOF、所有 defocus/sampling 必须复用同一个 pair scale，不允许 per-state remapping。

---

# 8. TASK-009 representative gate

代表 pair 必须从 frozen manifest 选择：

```text
REP-1 LB_AL2395 + A0 + WFS + EPD3
REP-2 ATC_M3_AL24477 + B0 + RAD + EPD5
REP-3 ATC_M3_AL24477 + C0 + HOA + EPD5
```

## TDD-TEST-204 — sampling convergence

每 EDOF representative 跑64/128/256。128→256：distance-peak MTFa relative≤2%；TF_MTFa_mean relative≤2%；distance peak shift≤0.25D；DOF50 width change≤0.25D。

Corrected pair-MONO-scale evidence 三组全部 PASS；formal production sampling 已锁128。不执行256→512 escalation。

## TDD-TEST-205 — repeatability

每 EDOF representative 独立重复128：peak sample identical；peak MTFa relative≤0.1%；TF mean relative≤0.1%；C4/C6≤0.001µm。Corrected evidence 三组全部 PASS。

## TDD-TEST-206 — real six-config production integration

三个 frozen pair 的 MONO+EDOF，共6 configs，必须：

- 使用 `ZosMtfaPairScaleAnalysisBackend`；
- 通过 `run_analysis_batch()`；
- selection config IDs 完全来自 frozen manifest；
- RunEnvironment 引用 baseline/main-settings/manifest/lock-set/acquisition ID+hash/frequency-scale mode；
- backend 自报 acquisition ID/hash/scale 与 RunEnvironment 完全一致，否则 acquisition 前 fail；
- 每 config 15 rows、MTFa/fixed MTF/C4/C6/HOA RMS finite；
- `ConfigResult` validator PASS；
- run history 有 running→completed/failed；
- completed artifacts 注册；
- matched deltas 与 `DeltaF_residual` 正确；
- formal carrier/residual 文件不修改。

Corrected evidence completed/failed=6/0，PASS。

## TDD-TEST-207 — limited independent extraction check

3 representative EDOF 在0D、20/40/60 cpd，用同一 paired-MONO scale 比较 production `MTFA` 与独立重复 `MTFA`，并比较 `MTFA` 与 `(MTFT+MTFS)/2`。记录 absolute differences，不新增 threshold。

Corrected evidence 两组差值逐点均为0；Web review=PASS。

---

# 9. Main analysis result / provenance contract

## TDD-TEST-301 — one config

成功 `ConfigResult` 必须保存15 rows、MTFa/MTF10..60、distance peak/zero/DOF50/TF mean、C4/C6/HOA RMS、main settings hash、HOA settings ID/hash、footprints/vignetting、working model hash、entity fingerprint、retina/IOL/ELP、artifacts。summary 必须由15-row curve复算；shape axis 严格由 retina axis 与 distance peak 推导。

Run-level `RunEnvironment` 必须保存 acquisition contract ID/hash 与 frequency-scale mode；backend 必须在 batch acquisition 前与环境一致。

## TDD-TEST-302 — entity invariants

through-focus before/after：working model file hash unchanged；in-memory entity fingerprint unchanged；fingerprint 覆盖 carrier R/Q/CT/material/IOL position/ELP/retina/surface role/type/count/STOP；OBJECT thickness 排除但结束恢复；retina/IOL/ELP unchanged；no unintended vignetting。

## TDD-TEST-303 — matched pair

same carrier ID/lock hash、same Base/Cornea/Platform/Pupil/alignment；MONO residual empty；EDOF residual ID/SHA/policy ID/hash complete；同一 pair angular scale；paired deltas=EDOF−MONO。

---

# 10. Full Run72 acceptance

Run72 前置条件：TDD-TEST-201~207 全部通过；`TASK009_PRODUCTION_SAMPLING_LOCK_v1` 存在且 sampling=128；active RunEnvironment/backend acquisition provenance gate 生效；Web active specs 已同步。

## TDD-TEST-401 — exact completion

```text
completed configs = 72
through-focus rows/config = 15
total through-focus rows = 1080
matched pair deltas = 36
```

config IDs 必须与 frozen manifest 完全相等。

## TDD-TEST-402 — repeatability sample

从正式 Run72 的预注册代表 configs 重跑，使用 TASK-009 repeatability tolerance。该测试属于 Run72 后验 acceptance，不是再次阻塞 Run72 启动的代表性预跑。

## TDD-TEST-403 — failed config isolation

人为失败一个 config：该 config=failed、其他 completed 不回滚、整体 acceptance 不通过；rerun 只选 failed config、使用新 run_id；补齐后才 PASS。

---

# 11. Active prohibition / trace tests

单元测试必须扫描 `src/whole_eye_mvp/**/*.py`、TASK-009/Run72 scripts 和 active URD/ADD/MDD/TDD/RMD/RMD_EXECUTION_STATUS，阻止已移除的旧主分析入口重新成为 production authority。

Active specs 不得把以下内容表述为 production：

```text
OpticStudio FFT MTF Analysis
ZosFftMtfAnalysisBackend
New_FftMtf
per-state EFFL frequency scale
```

`docs/TRACE.md` 必须覆盖当前 ID universe：URD-REQ-001..018、URD-AC-001..010、FR/DP-001..010、MDD-MOD-001..010、MDD-API-001..013。

---

# 12. Current gate status

截至 2026-08-19：

- TASK-005–008 frozen assets PASS；
- TDD-999 cleared；
- TASK-009 MFE MTFA Grid1 API PASS；
- corrected paired-MONO angular-scale convergence PASS；
- repeatability PASS；
- six-config real integration PASS；
- limited extraction Web review PASS；
- production sampling=128 formally locked；
- no 256→512 escalation required；
- Run72 尚未启动。