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
- active_hoa_settings: `TASK009_MFE_ZERN_HOA_555_v1`
- active_hoa_settings_sha256: `7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2`

---

# 1. Test decisions

| ID | Decision |
| --- | --- |
| TDD-DEC-001 | 主实验使用 OpticStudio FFT MTF Analysis；Python 只做单位转换、MTFa、贯焦摘要和 paired delta。 |
| TDD-DEC-002 | 标准眼 carrier SA calibration 固定 EPD6、约546 nm；主实验 EPD3/5 不改变 Q(P) calibration。 |
| TDD-DEC-003 | B0 lock 使用独立 `CORNEA_LOCK_B0_555_v2`，不进入 main-analysis settings identity。 |
| TDD-DEC-004 | DOF50 是固定 50% distance-peak MTFa 的命名指标，不是可调 settings 字段。 |
| TDD-DEC-005 | `DeltaF_residual` 是 matched analysis result，不进入 physical carrier lock identity。 |
| TDD-DEC-006 | TASK-009 代表配置必须来自 frozen TASK-008 manifest；6-config integration 必须走真实 `AnalysisBackend → run_analysis_batch`。 |
| TDD-DEC-007 | 主分析 settings 与 HOA readback settings 分开版本化并各自记录 hash。 |
| TDD-DEC-008 | 本地 TASK-009 只能证明 sampling candidate；Web review 后才允许写正式 production sampling lock。 |
| TDD-DEC-009 | limited extraction check 不自行定义新 acceptance threshold；只用于发现 API/单位/列解析错误。 |

---

# 2. Frozen settings

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

## 2.2 Main analysis settings

```text
settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
wavelength = 555 nm
EPD = 3 / 5 mm
field = 0 deg
defocus = +0.50 → -3.00 D
step = -0.25 D
planes = 15
production sampling candidate = 128
convergence samplings = 64 / 128 / 256
polarization = false
MTF common grid = 0..60 cpd
frequency step = 1 cpd
reported fixed frequencies = 10/20/30/40/50/60 cpd
```

## 2.3 HOA readback settings

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

## 3.1 Frequency conversion

\[
mm/deg=EFL_{mm}\tan(1^\circ),\qquad
f_{cpd}=f_{cyc/mm}\times mm/deg
\]

要求 EFL finite positive、native frequency strictly increasing、覆盖≥60 cpd，且 common-grid 不外推。

## 3.2 Average MTF / MTFa

\[
MTF_{avg}=\frac{MTF_{sag}+MTF_{tan}}2
\]

\[
MTFa=\frac1{60}\int_0^{60}MTF_{avg}(f)df
\]

输入 equal length、finite、non-negative。1-cpd grid + trapezoidal integration。Pure-math oracle：constant MTF=0.5 → MTFa=0.5，算术容差≤1e-10。

## 3.3 Distance peak / DOF50 / TF mean

Distance peak：±0.50D 内最大 MTFa；tie 先 minimum |D|，再 larger signed D；边界峰标 censored。

DOF50：

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

从 distance peak 向两侧扩展，取包含 distance peak 的连续区间；crossing 线性插值，不外推。

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

必须 strict-load `physical_carriers.csv`、`nominal_72.csv`、`manifest.sha256`，并满足 exact 18/72 rows、schema/version exact、18 locks 可重建、`build_manifests()` 重新生成的72 configs 与 loaded CSV 全等、manifest/lock-set 与 TASK-008 evidence 一致。MONO residual provenance empty；EDOF complete；555nm、EPD3/5、field0、alignment/monovision=0。

任一 tamper 必须在 OpticStudio acquisition 前 fail。

---

# 7. TASK-009 real API gate

## TDD-TEST-201 — FFT MTF capability

真实 OpticStudio 2026 R1：

- `New_FftMtf()` 可创建；
- sampling/max frequency/modulation/wave/field/image surface 明确设置；
- DataSeries 可读；
- sagittal/tangential columns 由 label 唯一识别；
- frequency unit cycles/mm；
- result finite；analysis 显式 close；
- evidence 记录真实 settings implementation type、sample enum、modulation enum、DataSeries count/runtime type、selected series runtime type、SeriesLabels、XLabel。

API enum/header/array wrapper 差异可机械适配；不得猜列位置或改科学 settings。

## TDD-TEST-202 — EFFL capability

临时 MFE `EFFL` 返回 finite positive mm，运行后删除并恢复 MFE row count。

## TDD-TEST-203 — cpd coverage

每 representative acquisition 覆盖≥60 cpd；不足时 fail，不外推。

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

本地全部通过只得到 `production_sampling_candidate_passed=true`，不能自行写正式 lock。

## TDD-TEST-205 — repeatability

每 EDOF representative 独立重复一次128：peak sample identical；peak MTFa relative≤0.1%；TF mean relative≤0.1%；C4/C6≤0.001µm。

## TDD-TEST-206 — real six-config production integration

三个 frozen pair 的 MONO+EDOF，共6 configs，必须：

- 使用 `ZosFftMtfAnalysisBackend`；
- 通过 `run_analysis_batch()`，不能用手工 dict/CSV 代替；
- selection config IDs 完全来自 frozen manifest；
- RunEnvironment 引用 baseline/main-settings/manifest/lock-set；
- 每 config 15 rows、MTFa/fixed MTF/C4/C6/HOA RMS finite；
- `ConfigResult` validator PASS；
- run history 有 running→completed/failed；
- completed result artifacts 注册；
- matched deltas 与 `DeltaF_residual` 正确；
- formal carrier/residual 文件不修改。

## TDD-TEST-207 — limited independent extraction check

3 representative EDOF 在少量 fixed frequencies 比较主 FFT MTF Analysis average 与 MFE `MTFA Grid=1` 或同 family 独立 export/readback。

要求两边 finite、frequency/unit/direction mapping 明确并保存 absolute differences；本地不设新一致性 threshold，Web review 后才能正式锁 sampling。

---

# 9. Main analysis result contract

## TDD-TEST-301 — one config

成功 `ConfigResult` 必须保存15 rows、MTFa/MTF10..60、distance peak/zero/DOF50/TF mean、C4/C6/HOA RMS、main settings hash、HOA settings ID/hash、footprints/vignetting、working model hash、entity fingerprint、retina/IOL/ELP、artifacts。summary 必须可由15-row curve复算，shape axis 必须严格由 retina axis 与 distance peak 推导。

## TDD-TEST-302 — entity invariants

through-focus before/after：

- working model file hash unchanged；
- in-memory entity fingerprint unchanged；
- fingerprint 覆盖 carrier R_ant/R_post、Q_ant/Q_post、CT/material、IOL position/ELP、retina、surface role/type/count/STOP；
- OBJECT thickness 故意排除，但运行结束必须恢复；
- retina/IOL/ELP unchanged；
- no unintended vignetting。

## TDD-TEST-303 — matched pair

same carrier ID/lock hash、same Base/Cornea/Platform/Pupil/alignment；MONO residual empty；EDOF residual ID/SHA/policy ID/hash complete；paired deltas=EDOF−MONO。

---

# 10. Full Run72 acceptance

只有 TDD-TEST-201~207 全部通过、Web 接受 independent extraction evidence，并写入正式 production-sampling lock 后才允许 Run72。

## TDD-TEST-401 — exact completion

```text
completed configs = 72
through-focus rows/config = 15
total through-focus rows = 1080
matched pair deltas = 36
```

config IDs 必须与 frozen manifest 完全相等。

## TDD-TEST-402 — repeatability sample

从正式 Run72 的预注册代表 configs 重跑，使用 TASK-009 repeatability tolerance。

## TDD-TEST-403 — failed config isolation

人为失败一个 config：该 config=failed、其他 completed 不回滚、整体 acceptance 不通过；rerun 只选 failed config、使用新 run_id；补齐后才 PASS。

---

# 11. Active prohibition / trace tests

单元测试必须扫描 `src/whole_eye_mvp/**/*.py`、TASK-009/Run72 scripts 和 active URD/ADD/MDD/TDD/RMD/RMD_EXECUTION_STATUS，阻止已移除的旧主分析入口重新进入 runtime。

`docs/TRACE.md` 必须覆盖当前 ID universe：URD-REQ001..018、URD-AC001..010、FR/DP001..010、MDD-MOD001..010、MDD-API001..013。旧文档 ID 不可继续让 trace checker 假通过。

---

# 12. 当前 STOP

截至 TASK-008：18/3/72 formal artifacts 已冻结，`TDD-999` 已解除。

当前 STOP：TASK-009 real API + sampling convergence + repeatability + real 6-config production integration + Web extraction review + formal sampling lock 未全部通过前，不得启动 Run72。
