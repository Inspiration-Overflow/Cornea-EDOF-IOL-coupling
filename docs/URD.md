# URD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **文档角色：** 用户需求文档（User Requirement Document, URD）。  
> **原则：** 本文件为当前独立、完整、自包含的 MVP 需求基线；旧版本只保留 Git provenance，不具有当前规范效力。

## Metadata

- document_id: `URD-0001`
- version: `1.6`
- status: `approved-for-ADD`
- last_updated: `2026-08-19`
- scope_level: `MVP`
- primary_platform: Windows
- optical_engine: Ansys Zemax OpticStudio 2026 R1, Sequential Mode
- automation: Python + ZOS-API
- canonical_lens_format: `.zmx`
- scientific_baseline: `MVP_2026_v2`
- main_analysis_settings: `NOMINAL_MAIN_FFT_MTF_555_v2`
- main_analysis_settings_sha256: `0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc`
- production_mtf_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- production_mtf_acquisition_sha256: `f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d`
- production_frequency_scale_mode: `paired_residual_free_MONO_EFFL`
- production_sampling: `128`
- production_sampling_lock: `TASK009_PRODUCTION_SAMPLING_LOCK_v1`
- hoa_readback_settings: `TASK009_MFE_ZERN_HOA_555_v1`
- hoa_readback_settings_sha256: `7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2`

---

# 1. 研究目标与边界

建立一个本地运行、可重复、可追溯的 Zemax 自动化研究软件，研究：

\[
\boxed{
\text{A/B/C 角膜光学原型}
\times
\text{WFS/RAD/HOA 非衍射 EDOF IOL surrogate}
}
\]

核心问题是：

> 在单色、轴上、共轴的人工晶状体眼中，不同术后角膜光学结构与不同非衍射 EDOF IOL 机制如何共同改变远焦成像质量、贯焦 MTF、焦深以及全眼高阶像差？

项目属于机制性光学研究，不是临床决策支持系统，不用于患者级 IOL 或术式推荐。MVP 的软件目标不是建立通用光学平台，而是把已经冻结的科学模型可靠地自动化、批量化和审计化。

---

# 2. 科学模型基线

## 2.1 双基座

### `LB_AL2395`

\[
AL=23.950\ \mathrm{mm}
\]

### `ATC_M3_AL24477`

\[
AL=24.477\ \mathrm{mm}
\]

共同冻结：

- 后角膜至 STOP = 3.150 mm；
- 后角膜至 IOL 前表面参考位置 = 4.500 mm；
- 房水/玻璃体工程折射率约 1.336；
- IMAGE 顶点由 AL 决定并在贯焦分析中固定；
- Field = 0°；
- 角膜、STOP、IOL 共轴；
- MVP 不加入角膜治疗区偏心、IOL tilt/decentration 或微单视附加 defocus。

## 2.2 三个冻结角膜

### A0：像差改变型近视术后准单焦角膜

- treatment = −3.00 D；
- EOZ ≈ 5.0 mm；
- \(\Delta C_4^0(6\,mm)\approx+0.13\,\mu m\)；
- 旋转对称、平滑过渡。

### B0：连续非球面角膜 EDOF

五候选为：

\[
\Delta C_4^0(6\,mm)=+0.10,+0.15,+0.20,+0.25,+0.30\ \mu m
\]

真实扫描、morphology review 和确定性排序已完成，正式冻结：

```text
B0 = B0.20
```

B0 冻结后禁止根据 IOL 主结果回调。

### C0：中央近用型径向多焦角膜

- treatment = −3.00 D；
- central near diameter = 3.00 mm；
- prescription ADD = +1.75 D；
- OZ = 6.50 mm；
- transition width = 0.75 mm；
- nominal transition discretization control = N=8；
- 中央近用 → 平滑过渡 → 周边远用主导。

ADD 是处方层面的设计输入，不要求 ray-traced 某一局部区域严格呈现 +1.75 D 的局部 vergence 差。

## 2.3 三个 IOL 机制 surrogate

用户可见平台 ID 只允许：

1. `WFS` — 波前塑形型 surrogate；
2. `RAD` — 连续径向屈光力调制型 surrogate；
3. `HOA` — 中央高阶球差调制型 surrogate。

商业产品名称只可作为文献机制锚点，不得作为模型 ID，也不得声称项目 surrogate 是商业制造处方的精确重建。

## 2.4 `STD_IOL_EYE_2024`

标准眼只用于 IOL 基础球差与 power-specific conic 校准，不作为 LB/ATC 主研究基座。

冻结校准条件：

- entrance pupil = 6.0 mm；
- wavelength ≈ 546 nm；
- model corneal \(C_4^0\approx+0.258\,\mu m\)；
- medium index ≈ 1.336；
- IOL footprint 约 5.15±0.10 mm。

同 power/geometry 的球差零参考态保留 carrier 的一阶光焦度、R、CT、材料、位置，只把主要 conic/高阶设计项和 residual 清零。

## 2.5 Controlled carrier scaffold

```text
n = 1.460
surrounding n = 1.336
CT = 1.000 mm
optical diameter = 6.000 mm
bending = symmetric biconvex
primary conic surface = anterior
posterior conic = 0
```

三平台基础球差目标统一定义于标准眼 EPD6：

- WFS: −0.20±0.01 µm；
- RAD: −0.27±0.01 µm；
- HOA: 0.00±0.01 µm。

## 2.6 每个 physical carrier 的 P→Q(P)

每个 `Base×Cornea×Platform` 必须独立完成：

1. 在真实 Base+Cornea 固定 retina 下求 Q=0 carrier 的远焦 power/曲率；
2. 把实际 power/geometry 放入标准眼；
3. 解对应平台 \(Q_k(P_{ijk})\)；
4. 放回实际眼检查远焦；
5. 必要时最多两次 P–Q 工程回查；
6. formal carrier 冻结后禁止因 EDOF residual 再单独改 P、R 或 Q。

不得把一个固定 Q 静默复制到全部 power。

## 2.7 EDOF residual

三 residual 均为版本化、可追溯的 Grid Sag resource。共同要求：

- 与对应 MONO carrier 使用完全相同的 P/R/Q/CT/material/IOL position；
- EDOF 与 MONO 的唯一设计差异是 residual；
- residual 冻结时去除不需要的 piston 和整体 defocus；
- low/median/high actual-power calibration 覆盖每个平台实际 power 范围；
- 正式低阶污染 gate 使用 `STD_IOL_EYE_2024 / EPD6 imported residual readback`；
- actual-eye sag readback 只作诊断；
- residual 加入后的最佳远焦变化以 `DeltaF_residual` 作为分析结果，不重新设计 carrier。

冻结工程 tolerance：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

---

# 3. 正式矩阵与不可变身份

## 3.1 Physical carriers

\[
2\ Base\times3\ Cornea\times3\ Platform=18
\]

必须恰好 18 个唯一 physical carrier locks。

## 3.2 Nominal configurations

每个 physical carrier 建立 matched MONO/EDOF，并分析 EPD3 / EPD5：

\[
18\times2\ state\times2\ pupil=72
\]

必须恰好 72 个唯一 nominal configurations、36 个 matched pair keys。

全部 nominal configs 固定：555 nm、field0、centered、IOL tilt/decentration=0、cornea decentration=0、micro-monovision defocus=0。

从 TASK-008 起，代表测试与 Run72 都必须从冻结的 `physical_carriers.csv` / `nominal_72.csv` 选择身份，不得在分析脚本中重建平行配置宇宙。

---

# 4. 主分析：MFE MTFA Grid=1 + paired-MONO 固定角尺度

## 4.1 唯一 production acquisition

生产 MTF acquisition 固定为：

```text
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

MFE operand = MTFA
Grid = 1
Data Type = 0
Wave = 1
Field = 1
frequency_scale_mode = paired_residual_free_MONO_EFFL
```

主生产链：

```text
formal matched pair
→ residual-free MONO nominal-distance EFFL once per pair
→ pair_mm_per_degree = EFFL_MONO × tan(1°)
→ common 0..60 cpd grid mapped directly to cycles/mm query frequencies
→ MFE MTFA Grid=1 at each retina-anchored defocus plane
→ MTFa + MTF10/20/30/40/50/60
→ through-focus metrics
→ matched EDOF−MONO deltas
```

`AS_FftMtf`/FFT-MTF Analysis production path 已退休，不得作为 Run72 fallback 或 prerequisite。Python 不建立第二套光学传播引擎，只做确定性频率映射、积分、贯焦摘要和 paired delta。

## 4.2 Numerical settings identity

继续使用已冻结：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

冻结：

- wavelength = 555 nm；
- EPD = 3 / 5 mm；
- retina-anchored defocus = +0.50 → −3.00 D；
- step = −0.25 D；
- 15 planes；
- production sampling = 128；
- convergence samplings = 64 / 128 / 256；
- no polarization；
- common grid = 0..60 cpd，1 cpd step；
- fixed output = 10/20/30/40/50/60 cpd。

该 settings ID 中遗留的 `FFT_MTF` 名称和代码字段 `fft_mtf_*` 仅为保持既有 settings hash/历史兼容，不再表示 production acquisition 使用 FFT-MTF Analysis。Acquisition identity 单独由 `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2` 版本化。

## 4.3 Paired-MONO angular-frequency scale

对每个 frozen `pair_key`：

\[
EFL_{ref}=EFL(\text{residual-free MONO carrier at nominal distance})
\]

\[
mm/degree=EFL_{ref}\tan(1^\circ)
\]

对 MONO、EDOF、所有 defocus plane、所有 sampling 使用同一个：

\[
f_{cyc/mm}=\frac{f_{cpd}}{mm/degree}
\]

EDOF-state EFFL 可以记录为 `state_diagnostic`，但不得重新定义 cpd 轴。生产查询直接按 0..60 cpd 对应的 cycles/mm 目标读取，不需要 native curve 插值，也不允许用 per-state EFFL 改变 matched pair 的坐标系。

## 4.4 MTFa 与固定频率 MTF

生产 MTF 值直接来自 MFE `MTFA Grid=1`。定义：

\[
MTFa(F)=\frac1{60}\int_0^{60}MTFA(f,F)df
\]

在 1-cpd grid 上使用梯形积分。固定输出为 10/20/30/40/50/60 cpd 的 `MTFA` 值。

`MTFT` 与 `MTFS` 仅用于独立 extraction diagnostic；TASK-009 已验证 20/40/60 cpd 上 `MTFA=(MTFT+MTFS)/2`，但该诊断不构成第二条 production path。

## 4.5 Distance peak

在 \(F\in[-0.50,+0.50]D\) 内，以 MTFa 最大值定义 distance peak。并列时先最小 \(|F|\)，再取较大的 signed F；若峰落在 ±0.50 D 边界，记录 `peak_search_censored=true`。

## 4.6 DOF50

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

取包含 distance peak、且 MTFa≥T50 的连续区间，相邻 0.25-D sample 间线性插值 crossing，输出 far / near / width 及 censor flags。

## 4.7 Through-focus MTFa mean

\[
TF\_MTFa\_mean=\frac1{3.5D}\int_{-3.00}^{+0.50}MTFa(F)dF
\]

用于连续贯焦总体质量比较。

## 4.8 全眼高阶像差 readback

主实验额外读取完整全眼 Zernike n=3..6，用于 C4、C6 与 HOA RMS：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

该 identity 必须单独随结果保存。

---

# 5. 每配置结果合同

每个成功 config 至少保存：

- config ID / pair key / optic state / pupil；
- 15 行 retina-anchored through-focus data；
- MTFa、MTF10/20/30/40/50/60；
- distance peak、MTFa at zero、DOF50、TF_MTFa_mean；
- C4、C6、HOA RMS；
- main settings hash；
- HOA settings ID/hash；
- formal carrier/residual/manifest identity；
- working model hash before/after；
- in-memory entity fingerprint before/after；
- retina/IOL/ELP before/after；
- cornea/STOP/IOL footprint 与 vignette status；
- run ID 与 environment reference；
- required working `.zmx`、CSV 与图像 artifacts。

`RunEnvironment` 必须包含并验证：program/OpticStudio version、baseline ID、main settings ID、manifest hash、lock-set hash、production acquisition contract ID/hash、frequency-scale mode。Backend 自报 acquisition provenance 必须与环境逐项完全一致，否则在 acquisition 前 fail-closed。

---

# 6. Defocus 与 matched-pair 语义

贯焦使用固定 retina，通过分析层 object vergence/thickness 改变输入离焦；结束后必须恢复。禁止通过移动 retina、修改 IOL 位置或重新优化 carrier 来完成贯焦。

`defocus_retina_d` 为正式坐标；`defocus_shape_d` 仅由 distance peak 后处理重心化：

\[
defocus_{shape}=defocus_{retina}-F_{distance\ peak}
\]

matched pair 的 `DeltaF_residual` 定义为：

\[
F_{peak,EDOF}-F_{peak,MONO}
\]

始终使用 retina-anchored frame。

---

# 7. TASK-009 方法与 sampling lock

代表 pair：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

必须来自 frozen manifest。

Sampling convergence：每个 EDOF 比较 64/128/256；128→256 门限为 peak MTFa relative≤2%、TF_MTFa_mean relative≤2%、peak shift≤0.25D、DOF50 width change≤0.25D。

Repeatability：128 独立重复，peak sample 相同、peak MTFa relative≤0.1%、TF mean relative≤0.1%、C4/C6≤0.001µm。

Six-config integration：三个 MONO+EDOF pair 共6 configs 必须通过真实 `ZosMtfaPairScaleAnalysisBackend → run_analysis_batch()`，并验证 frozen identities、environment、run state、ConfigResult、artifacts、entity/ray-health 与 matched deltas。

Corrected pair-MONO-scale evidence 已全部通过；Web 已正式锁定：

```text
TASK009_PRODUCTION_SAMPLING_LOCK_v1
production_sampling = 128
production_sampling_locked = true
sampling_escalation_256_active = false
```

无需 256→512 escalation。

---

# 8. 用户场景与 GUI

| Scenario | Expected outcome |
| --- | --- |
| 启动并连接 OpticStudio | 显示安装路径、连接/license 状态；失败则明确终止，不伪成功 |
| Build / Validate | 构建或验证 scientific assets，显示 PASS/FAIL 与输出位置 |
| B0 Scan / Lock | 使用冻结五候选流程并读取正式 B0 lock，不允许下游回调 |
| Build / Inspect Carriers | 查看已冻结 18 carriers / 3 residuals / 72 manifest provenance |
| Run72 | 一次执行 frozen 72-config manifest，并显示 completed/failed/remaining |
| Rerun Selected | 只重跑失败或明确选择的 config，生成新 run_id |
| Audit | 从 config ID 追溯 baseline/settings/acquisition/manifest/lock/result/environment |

GUI 保持极简，只负责 workflow orchestration，不持有 scientific truth。至少提供安装路径、项目目录、Build/Validate/B0/Carriers/Run72/Rerun、当前 config、进度、completed/failed/remaining、日志与 Open Output Folder。MVP 不要求 Pause/Cancel，失败恢复由配置级 Rerun 完成。

---

# 9. 软件功能需求

| ID | Requirement | Priority |
| --- | --- | --- |
| URD-REQ-001 | 使用 Python + ZOS-API 控制 OpticStudio 2026 R1 Sequential Mode，并可靠管理 session lifecycle。 | must |
| URD-REQ-002 | 使用版本化 ScientificBaseline、settings ID/hash、acquisition ID/hash、artifact hash 与 immutable provenance。 | must |
| URD-REQ-003 | 构建并验证 LB/ATC 双基座。 | must |
| URD-REQ-004 | 构建并锁定 `STD_IOL_EYE_2024` EPD6 calibration asset。 | must |
| URD-REQ-005 | A0/B0.20/C0 一旦冻结，下游只读。 | must |
| URD-REQ-006 | WFS/RAD/HOA 使用平台特异 SA target 和 power-specific Q(P)。 | must |
| URD-REQ-007 | 每个 Base×Cornea×Platform 生成独立 physical carrier。 | must |
| URD-REQ-008 | MONO/EDOF matched pair 的 carrier 参数完全相同，唯一设计差异为 residual。 | must |
| URD-REQ-009 | residual 通过实际 payload、标准眼低阶污染与 low/median/high power calibration。 | must |
| URD-REQ-010 | 恰好冻结 18 physical carrier locks、3 residual locks 和 72 nominal configs，并从正式 manifest 驱动分析。 | must |
| URD-REQ-011 | 主生产 MTF 必须使用 `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`；每 pair 使用 residual-free MONO EFFL 固定角尺度；sampling=128。 | must |
| URD-REQ-012 | 贯焦不得改变 retina、carrier P/R/Q、IOL position、ELP 或实体面型；必须用 in-memory entity fingerprint 验证。 | must |
| URD-REQ-013 | 每个成功 config 保存第5节要求的 MTFa/MTF/像差/footprint/settings/acquisition/provenance。 | must |
| URD-REQ-014 | 自动形成 36 个 EDOF−MONO matched-pair delta。 | must |
| URD-REQ-015 | 单 config 失败不得显示 completed，必须允许只重跑失败项并生成新 run_id。 | must |
| URD-REQ-016 | 同输入、同软件/settings/acquisition/manifest/locks 的重复运行必须满足 repeatability gate。 | must |
| URD-REQ-017 | 提供极简 GUI/workflow orchestration、进度与日志。 | should |
| URD-REQ-018 | 结构化科学结果以 CSV/JSON 为主；关键 `.zmx`、图像、日志与 run environment 保留可审计 provenance。 | must |

---

# 10. Acceptance

| ID | Acceptance |
| --- | --- |
| URD-AC-001 | ZOS-API lifecycle 成功/失败均明确，无假 completed。 |
| URD-AC-002 | 双基座 AL/STOP/IOL landmarks 与冻结值一致。 |
| URD-AC-003 | 标准眼 EPD6/C40/footprint/index/wavelength calibration 通过。 |
| URD-AC-004 | A0/B0.20/C0 正式冻结且下游 hash 不变。 |
| URD-AC-005 | 18 个 carrier 的 P/Q/SA replay 与 formal lock 一致。 |
| URD-AC-006 | 三 residual 及 low/median/high calibration 正式通过。 |
| URD-AC-007 | physical manifest 恰好18行；nominal manifest恰好72行；36 pair keys；reload 可复算相同 manifest/lock-set。 |
| URD-AC-008 | TASK-009 corrected paired-MONO-scale convergence/repeatability、真实6-config batch integration、Web crosscheck review 与 formal sampling lock 均通过。 |
| URD-AC-009 | Run72 恰好72 completed configs、1080 through-focus rows、36 paired deltas；失败项不得混入 completed。 |
| URD-AC-010 | 结果可追溯到 baseline、main settings hash、acquisition contract ID/hash、frequency-scale mode、HOA settings hash、manifest、lock-set、OpticStudio version、run ID 与 entity fingerprint。 |

---

# 11. 输出、失败与重跑

正式分析至少形成：每 config `config_result.json`、through-focus CSV、through-focus MTFa 图、0D MTF 图、matched-pair result 表、run/environment logs、failed/rerun status 和可追溯工作模型 `.zmx`。

任一 config 失败：该 config 标记 failed；其他 completed 不回滚；失败项不计入 acceptance；Rerun 只选择失败/指定项并使用新 run_id；只有 frozen 72 个 config 全部成功后 Run72 才可整体 PASS。

---

# 12. MVP 范围外

- 角膜治疗区偏心/倾斜；
- IOL tilt/decentration 主矩阵；
- 多色/色差主研究；
- 患者级参数优化；
- 商业 IOL 制造面型精确逆向；
- residual 随所有可能 IOL power 的完整不确定性研究；
- 复杂多目标自动优化 B0；
- C0 transition-width 优化；
- Web 服务、数据库、云端/并行 Zemax 集群；
- 临床推荐或医疗器械决策支持；
- 为得到更漂亮结果而回调冻结 cornea/carrier/residual。

---

# 13. 当前不可变边界

截至 2026-08-19：

- A0/B0.20/C0 frozen；
- `TDD-999` 已解除；
- 18 carrier locks / 3 residual locks / 72 manifest 已正式冻结；
- TASK-005–008 scientific assets/hash 只读；
- TASK-009 corrected paired-MONO scale optical gate 已 PASS；
- production sampling=128 已 Web formal lock；
- `AS_FftMtf` production path retired；
- Run72 尚未启动；
- 后续不得重新优化 TASK-005–008 scientific assets，也不得用 per-state EFFL 改变 matched-pair cpd 坐标。