# TDD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Test-Driven / Check Plan。目标是用少量高价值 oracle 发现模型、锁、指标或 72-config 执行错误。  
> **来源：** `URD-0001 v1.5`、`ADD-0001 v1.5`、`MDD-0001 v1.4`。

## Metadata

- document_id: `TDD-0001`
- version: `1.5`
- status: `active`
- last_updated: `2026-08-19`
- target_test_runner: pytest
- optical_integration_environment: Windows + OpticStudio 2026 R1 + valid ZOS-API license
- active_main_settings: `NOMINAL_MAIN_FFT_MTF_555_v2`

---

# 1. Test decisions

| ID | Decision |
| --- | --- |
| TDD-DEC-001 | 主实验使用 OpticStudio FFT MTF Analysis；Python 只做单位转换、MTFa、贯焦摘要和 paired delta。 |
| TDD-DEC-002 | 标准眼 carrier SA calibration 固定 EPD6、约 546 nm；主实验 EPD3/5 不改变 Q(P) calibration。 |
| TDD-DEC-003 | B0 lock 继续使用独立 `CORNEA_LOCK_B0_555_v2` MFE MTFA acquisition；其数值不得被 TASK-009 settings 改写。 |
| TDD-DEC-004 | 主实验不设 absolute MTFa DOF threshold；使用 distance-anchored DOF50。 |
| TDD-DEC-005 | `DeltaF_residual` 是 matched analysis result，不进入 physical carrier lock identity。 |
| TDD-DEC-006 | Run72 前必须通过三代表 sampling convergence、repeatability 和 6-config integration。 |
| TDD-DEC-007 | TASK-009 的 independent extraction check 不自行定义新 acceptance threshold；只用于发现 API/单位/列解析错误。 |

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

此 settings 只用于 B0 selection provenance。

## 2.2 Main analysis settings

```text
settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
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

128 只有在 TASK-009 实机 convergence 通过后才可成为 Run72 production setting。

---

# 3. Metric oracle

## 3.1 Frequency conversion

使用真实 EFL：

\[
mm/deg=EFL_{mm}\tan(1^\circ)
\]

\[
f_{cpd}=f_{cyc/mm}\times mm/deg
\]

测试必须验证：

- EFL finite positive；
- FFT MTF output frequency strictly increasing；
- acquisition 覆盖转换后的 60 cpd；
- common-grid interpolation 不允许外推。

## 3.2 Average MTF

\[
MTF_{avg}=\frac{MTF_{sag}+MTF_{tan}}2
\]

要求输入 equal length、finite、non-negative。

## 3.3 MTFa

\[
MTFa=\frac1{60}\int_0^{60}MTF_{avg}(f)df
\]

1-cpd grid、trapezoidal integration。

Pure-math oracle：constant MTF=0.5 时 MTFa=0.5，默认 arithmetic tolerance ≤1e-10。

## 3.4 Distance peak

在 ±0.50 D 内选最大 MTFa。

Tie-break：

1. minimum |D|；
2. larger signed D。

边界峰必须 `peak_search_censored=true`。

## 3.5 DOF50

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

从 distance peak 向两侧扩展，取包含 distance peak 的连续 ≥T50 区间；crossing 线性插值，不外推；保存 far/near censor。

## 3.6 TF_MTFa_mean

\[
TF\_MTFa\_mean=\frac1{3.5D}\int_{-3.0}^{+0.5}MTFa(F)dF
\]

必须对 defocus 方向不敏感。

---

# 4. Scientific asset acceptance

| ID | Scenario | Oracle |
| --- | --- | --- |
| TDD-TEST-001 | ZOS session | valid runtime→non-null system + explicit close；bad path/license→typed failure，无假 completed |
| TDD-TEST-002 | bases | AL=23.950/24.477±0.001 mm；STOP/IOL landmarks 与 URD 一致 |
| TDD-TEST-003 | standard eye | EPD=6.000±0.001 mm；corneal C40=+0.258±0.005 µm；footprint=5.15±0.10 mm；λ≈546 nm |
| TDD-TEST-004 | A/B/B0 | A0 与五 B candidate 达 target；B0 review/rank/hash 可复算；B0.20 immutable |
| TDD-TEST-005 | C0 | near 3.0 mm、ADD +1.75 D、OZ6.5、transition0.75、nominal N8、convergence PASS |
| TDD-TEST-006 | Q(P) | 18 carriers replay to standard eye EPD6；WFS −0.20±0.01、RAD −0.27±0.01、HOA 0.00±0.01 µm；q_source_power==P |
| TDD-TEST-007 | matched carrier | 同平台 MONO/EDOF P/R/Q/CT/material/position 完全相同；EDOF 只增加 residual |
| TDD-TEST-008 | exact physical locks | exactly 18 unique Base×Cornea×Platform locks |
| TDD-TEST-009 | exact nominal manifest | exactly 72 configs、36 pair keys、EPD3/5、555 nm、field0、centered |

---

# 5. Residual science gate

## TDD-TEST-108 — residual actual-power calibration

每个平台必须在其 formal carrier power 集合选择 low/median/high 三点：

- residual payload/version/hash 明确；
- standard-eye EPD6 imported residual low-order readback：
  - |piston|≤0.010 µm；
  - |global defocus|≤0.125 D；
- ray health PASS；
- mechanism evidence low/median/high 均经 Web review；
- 3×3=9 calibration records 完整。

actual-eye sag readback可记录为诊断，但不得替代冻结的 standard-eye low-order gate。

## TDD-TEST-999 — carrier/residual science STOP

正式 18 carrier/residual locks 前必须同时具备：

1. versioned WFS/RAD/HOA residual payload；
2. frozen piston/global-defocus policy；
3. low/median/high actual-power calibration；
4. mechanism review PASS。

当前项目 evidence 已于 TASK-007 通过并 machine-readable `tdd_999_cleared=true`。后续测试只验证这一 provenance 不被破坏，不重新解释 TASK-007 scientific evidence。

---

# 6. TASK-008 manifest tests

## TDD-TEST-109 — lock/hash integrity

- 18 carrier asset SHA 与 index 一致；
- 3 residual asset/validation SHA 与 index 一致；
- all locked=true；
- baseline=`MVP_2026_v2`；
- lock-set hash 稳定且对 input ordering 不敏感；
- tampered/missing/duplicate lock 拒绝 manifest。

## TDD-TEST-110 — 72-config semantics

MONO rows：residual provenance 必须为空。

EDOF rows：必须存在 residual ID/SHA/policy。

全部 72：

```text
555 nm
EPD 3 or 5
field 0
tilt 0
decentration 0
micro-monovision 0
```

---

# 7. TASK-009 FFT MTF API gate

## TDD-TEST-201 — FFT MTF capability

真实 OpticStudio 2026 R1：

- `New_FftMtf()` 可创建 analysis；
- settings 可明确设置 sampling/max frequency/modulation/wave/field/image surface；
- `DataSeries` 可读；
- 唯一识别 sagittal/tangential columns；
- frequency axis 单位 cycles/mm；
- result finite；
- analysis 显式 close。

如果安装版本 enum/header/cast 不同，可机械适配并记录 actual API evidence；不得猜列位置或改科学 settings。

## TDD-TEST-202 — EFFL capability

临时 MFE `EFFL`：

- 返回 finite positive mm；
- operand 运行后删除；
- MFE row count 恢复原值。

## TDD-TEST-203 — cpd coverage

每 representative config 的 FFT MTF acquisition 必须覆盖 ≥60 cpd；不足时 fail，而不是外推。

---

# 8. TASK-009 representative convergence

冻结三代表：

```text
REP-1 LB_AL2395 + A0 + WFS + EPD3
REP-2 ATC_M3_AL24477 + B0 + RAD + EPD5
REP-3 ATC_M3_AL24477 + C0 + HOA + EPD5
```

## TDD-TEST-204 — sampling convergence

每个 EDOF representative 跑 64/128/256 sampling。

对 128→256：

| metric | tolerance |
| --- | ---: |
| distance-peak MTFa relative change | ≤2% |
| TF_MTFa_mean relative change | ≤2% |
| distance peak shift | ≤0.25 D |
| DOF50 width change | ≤0.25 D |

三者全部通过才允许 `production_sampling_locked=true`。

## TDD-TEST-205 — repeatability

每个 EDOF representative 再重复一次 128：

| metric | tolerance |
| --- | ---: |
| distance-peak sample | identical |
| distance-peak MTFa relative | ≤0.1% |
| TF_MTFa_mean relative | ≤0.1% |
| C4 | ≤0.001 µm |
| C6 | ≤0.001 µm |

## TDD-TEST-206 — six-config integration

三个 representative pair 的 MONO+EDOF，共 6 configs：

- 每 config 15 through-focus rows；
- MTFa + fixed-frequency MTF finite；
- C4/C6/HOA RMS finite；
- matched carrier provenance 与 TASK-008 相同；
- `DeltaF_residual` 由 retina-frame distance-peak delta 得出；
- 不修改 formal carrier/residual files。

## TDD-TEST-207 — limited independent extraction check

在 3 representative EDOF 的少量 fixed frequencies，比较主 FFT MTF Analysis average 与 MFE `MTFA Grid=1` 或同 family 独立 text export。

本测试：

- 要求两边 finite、频率/单位/方向映射明确；
- 保存 absolute differences；
- 不预注册新的数值一致性 threshold；
- Web review 后才能进入 Run72。

---

# 9. Main analysis result contract

## TDD-TEST-301 — one config

成功 ConfigResult 必须恰好 15 rows，并保存：

```text
defocus_retina_d
defocus_shape_d
MTFa
MTF10/20/30/40/50/60
distance_peak_retina_d
distance_peak_mtfa
mtfa_at_zero_d
DOF50 fields
TF_MTFa_mean
C4/C6/HOA RMS
footprints
model/retina/IOL/ELP invariants
unintended_vignetting
artifacts
```

`defocus_shape_d` 必须严格等于 retina defocus − distance peak。

## TDD-TEST-302 — entity invariants

through-focus before/after：

- model hash unchanged；
- retina unchanged；
- IOL position unchanged；
- ELP unchanged；
- carrier P/R/Q unchanged；
- no unintended vignetting。

## TDD-TEST-303 — matched pair

必须校验 MONO/EDOF：

- same carrier ID/lock hash；
- same Base/Cornea/Platform/Pupil/alignment；
- MONO residual empty；
- EDOF residual provenance complete。

Paired deltas = EDOF−MONO。

---

# 10. Full Run72 acceptance

只有 TDD-TEST-201~207 全部通过且 Web review 接受 independent extraction evidence 后才允许 Run72。

## TDD-TEST-401 — exact completion

formal run 必须：

```text
completed configs = 72
through-focus rows/config = 15
total through-focus rows = 1080
matched pair deltas = 36
```

config IDs 必须与 frozen manifest 完全相等，不允许多/少/重复。

## TDD-TEST-402 — repeatability sample

从正式 Run72 选择预注册代表 configs 重跑；使用 TASK-009 repeatability tolerance。

## TDD-TEST-403 — failed config isolation

人为失败一个 config：

- 该 config status=failed；
- 其他 completed 不回滚；
- acceptance 不通过；
- rerun 只选择 failed config；
- 新 run_id；
- 全部补齐后 acceptance 才可 PASS。

---

# 11. Active prohibition test

生产源码与 active URD/ADD/MDD/TDD/RMD 不得重新出现已移除的旧主分析入口或旧视觉加权指标字段。

单元测试必须扫描：

- `src/whole_eye_mvp/**/*.py`；
- active specification files。

历史 Git commit、diagnostic evidence 和迁移说明允许保留旧术语作为 provenance，但不得被 runtime import 或 active settings 引用。

---

# 12. 当前 STOP

截至 TASK-008：18/3/72 formal artifacts 已冻结，`TDD-999` 已解除。

当前唯一科学 STOP：

> TASK-009 real FFT MTF capability + sampling convergence + repeatability + representative 6-config integration + independent extraction review 未全部通过前，不得启动 Run72。
