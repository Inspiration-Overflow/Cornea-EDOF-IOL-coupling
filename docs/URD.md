# URD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **文档角色：** 用户需求文档（User Requirement Document, URD）。  
> **原则：** 本文件为当前独立、完整、自包含的 MVP 需求基线；旧版本只保留 Git provenance，不具有当前规范效力。

## Metadata

- document_id: `URD-0001`
- version: `1.5`
- status: `approved-for-ADD`
- last_updated: `2026-08-19`
- scope_level: `MVP`
- primary_platform: Windows
- optical_engine: Ansys Zemax OpticStudio 2026 R1, Sequential Mode
- automation: Python + ZOS-API
- canonical_lens_format: `.zmx`
- scientific_baseline: `MVP_2026_v2`
- main_analysis_settings: `NOMINAL_MAIN_FFT_MTF_555_v2`

---

# 1. 研究目标

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

项目属于机制性光学研究，不是临床决策支持系统，不用于患者级 IOL 或术式推荐。

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

双基座用于检查机制趋势对轴长背景是否敏感，不用于比较经典 schematic eye 的优劣。

## 2.2 三个冻结角膜

### A0：像差改变型近视术后准单焦角膜

冻结 nominal：

- treatment = −3.00 D；
- EOZ ≈ 5.0 mm；
- \(\Delta C_4^0(6\,mm)\approx+0.13\,\mu m\)；
- 旋转对称、平滑过渡。

### B0：连续非球面角膜 EDOF

五候选来自：

\[
\Delta C_4^0(6\,mm)=+0.10,+0.15,+0.20,+0.25,+0.30\ \mu m
\]

第一轮真实扫描、morphology review 和确定性排序已完成；正式冻结：

```text
B0 = B0.20
```

B0 冻结后禁止根据 IOL 主结果回调。

### C0：中央近用型径向多焦角膜

冻结 nominal：

- treatment = −3.00 D；
- central near diameter = 3.00 mm；
- prescription ADD = +1.75 D；
- OZ = 6.50 mm；
- transition width = 0.75 mm；
- nominal transition discretization control = N=8；
- 中央近用 → 平滑过渡 → 周边远用主导。

ADD 是处方层面的设计输入，不要求 ray-traced 某一局部区域严格呈现 +1.75 D 的局部 vergence 差。

A0 / B0.20 / C0 均为旋转对称机制 surrogate；MVP 不主动引入彗差或随机不规则像差。

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

同 power/geometry 的球差零参考态必须保留 carrier 的一阶光焦度、R、CT、材料、位置，只把主要 conic/高阶设计项和 residual 清零。

## 2.5 Controlled carrier scaffold

MVP 使用工程控制 scaffold，而不是商业 IOL 几何逆向：

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

对每个：

\[
Base\times Cornea\times Platform
\]

必须独立完成：

1. 在真实 Base+Cornea 固定 retina 下求 Q=0 carrier 的远焦 power/曲率；
2. 把实际 power/geometry 放入标准眼；
3. 解对应平台 \(Q_k(P_{ijk})\)；
4. 放回实际眼检查远焦；
5. 必要时最多进行两次 P–Q 工程回查；
6. formal carrier 冻结后禁止因 EDOF residual 再单独改 P、R 或 Q。

不得把一个固定 Q 静默复制到全部 power。

## 2.7 EDOF residual

三 residual 均为版本化、可追溯的 Grid Sag resource。

共同要求：

- 与对应 MONO carrier 使用完全相同的 P/R/Q/CT/material/IOL position；
- EDOF 与 MONO 的唯一设计差异是 residual；
- residual 冻结时去除不需要的 piston 和整体 defocus；
- low/median/high actual-power calibration 必须覆盖每个平台实际 power 范围；
- 正式低阶污染 gate 使用 `STD_IOL_EYE_2024 / EPD6 imported residual readback`；
- actual-eye sag readback 可作为诊断，不取代上述标准眼 gate；
- residual 加入后的最佳远焦变化以 `DeltaF_residual` 作为分析结果，不重新设计 carrier。

冻结工程 tolerance：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

---

# 3. 正式矩阵

## 3.1 Physical carriers

\[
2\ Base\times3\ Cornea\times3\ Platform=18
\]

必须恰好 18 个唯一 physical carrier locks。

## 3.2 Nominal configurations

每个 physical carrier 建立 matched：

```text
MONO
EDOF
```

并分析 EPD3 / EPD5：

\[
18\times2\ state\times2\ pupil=72
\]

必须恰好 72 个唯一 nominal configurations、36 个 matched pair keys。

全部 nominal configs 固定：

- wavelength = 555 nm；
- field = 0°；
- centered；
- IOL tilt = 0；
- IOL decentration = 0；
- cornea decentration = 0；
- micro-monovision defocus = 0。

---

# 4. 主分析：FFT MTF / MTFa-only

## 4.1 唯一 diffraction image-quality acquisition

主实验必须直接使用 OpticStudio FFT MTF Analysis。

生产链：

```text
OpticStudio FFT MTF
→ sagittal/tangential modulation average
→ cycles/mm 转 cycles/degree
→ 0..60 cpd common grid
→ MTFa + MTF10/20/30/40/50/60
→ through-focus metrics
→ matched EDOF−MONO deltas
```

软件不得再建立第二套独立光学传播引擎来生成主结果。

## 4.2 Analysis settings

active settings ID：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
```

冻结：

- 555 nm；
- EPD3 / EPD5；
- retina-anchored defocus = +0.50 → −3.00 D；
- step = −0.25 D；
- 15 planes；
- production sampling candidate = 128；
- convergence sampling = 64 / 128 / 256；
- no polarization；
- common grid = 0..60 cpd，1 cpd step；
- fixed output = 10/20/30/40/50/60 cpd。

128 只有在 TASK-009 real OpticStudio convergence 通过后才成为 Run72 production sampling；若失败，必须产生新 settings ID。

## 4.3 Frequency conversion

OpticStudio FFT MTF frequency 以 cycles/mm 读取。使用当前模型 effective focal length：

\[
mm/degree=EFL_{mm}\tan(1^\circ)
\]

\[
f_{cpd}=f_{cyc/mm}\times mm/degree
\]

只允许在真实 acquisition 覆盖范围内插值，不允许外推到 60 cpd。

## 4.4 MTFa

\[
MTF_{avg}(f)=\frac{MTF_{sag}(f)+MTF_{tan}(f)}{2}
\]

\[
\boxed{MTFa(F)=\frac1{60}\int_0^{60}MTF_{avg}(f,F)df}
\]

使用 1-cpd grid 梯形积分。

## 4.5 Distance peak

在：

\[
F\in[-0.50,+0.50]D
\]

以 MTFa 最大值定义 distance peak。

并列：先最小 \(|F|\)，再选择较大的 signed F。若结果落在 ±0.50 D 边界，记录 `peak_search_censored=true`。

## 4.6 DOF50

MVP 不设置新的绝对 MTFa 焦深阈值。

定义：

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

取包含 distance peak、且 MTFa≥T50 的连续区间；相邻 0.25-D sample 间用线性插值求 crossing。

输出：

- `dof50_far_d`；
- `dof50_near_d`；
- `dof50_width_d`；
- far/near censor flags。

## 4.7 Through-focus MTFa mean

\[
TF\_MTFa\_mean=\frac1{3.5D}\int_{-3.00}^{+0.50}MTFa(F)dF
\]

该值用于连续贯焦总体质量比较，不单独设 acceptance threshold。

## 4.8 双坐标

每个贯焦结果同时保存：

- `defocus_retina_d` — 因果/实体模型锚定坐标；
- `defocus_shape_d = defocus_retina_d - distance_peak_retina_d` — 只用于曲线形态比较。

shape recenter 不得改变 `.zmx`、retina、IOL、ELP 或任何实体面型。

---

# 5. 每个 config 的正式结果

至少保存：

- 15-plane through-focus rows；
- MTFa；
- MTF10/20/30/40/50/60；
- distance peak defocus；
- distance peak MTFa；
- MTFa at 0 D；
- DOF50；
- TF_MTFa_mean；
- whole-eye C4^0；
- whole-eye C6^0；
- HOA RMS；
- corneal/STOP/IOL footprints；
- model hash；
- retina/IOL/ELP before/after invariants；
- unintended vignetting flag；
- config/run/environment/manifest/lock provenance。

PSF 图不是 MVP 每配置 mandatory artifact。

---

# 6. Matched-pair 主比较

同一 carrier/pupil 下：

\[
\Delta M=M(EDOF)-M(MONO)
\]

至少计算：

- distance peak；
- distance peak MTFa；
- MTFa at 0 D；
- DOF50 width；
- TF_MTFa_mean；
- C4^0；
- C6^0；
- HOA RMS。

其中：

```text
DeltaF_residual = distance_peak_retina_d(EDOF) - distance_peak_retina_d(MONO)
```

始终使用 retina-anchored frame。

---

# 7. TASK-009 方法闸门

Run72 前必须先验证三个代表 pair：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

每个代表 EDOF config 比较 sampling 64/128/256。

128→256 必须满足：

- distance-peak MTFa relative change ≤2%；
- TF_MTFa_mean relative change ≤2%；
- distance peak shift ≤0.25 D；
- DOF50 width change ≤0.25 D。

128 重复运行必须满足：

- distance-peak grid sample 相同；
- distance-peak MTFa relative change ≤0.1%；
- TF_MTFa_mean relative change ≤0.1%；
- C4/C6 repeatability ≤0.001 µm。

同时运行三个 matched MONO+EDOF pair，共 6 configs，确认生产 contract 和 `DeltaF_residual`。

允许少量 MFE `MTFA Grid=1` 或同一 FFT-MTF family 的独立 readback 作为数据提取/单位检查；该检查不构成第二条 production path，也不自行增加新 scientific threshold。

---

# 8. 软件功能需求

| ID | Requirement | Priority |
| --- | --- | --- |
| URD-REQ-001 | 使用 Python + ZOS-API 控制 OpticStudio 2026 R1 Sequential Mode。 | must |
| URD-REQ-002 | 使用版本化 ScientificBaseline、settings ID、hash 与 immutable provenance。 | must |
| URD-REQ-003 | 构建并验证 LB/ATC 双基座。 | must |
| URD-REQ-004 | 构建并锁定 `STD_IOL_EYE_2024` EPD6 calibration asset。 | must |
| URD-REQ-005 | A0/B0.20/C0 一旦冻结，下游只读。 | must |
| URD-REQ-006 | WFS/RAD/HOA 使用平台特异 SA target 和 power-specific Q(P)。 | must |
| URD-REQ-007 | 每个 Base×Cornea×Platform 生成独立 physical carrier。 | must |
| URD-REQ-008 | MONO/EDOF matched pair 的 carrier 参数必须完全相同，唯一设计差异为 residual。 | must |
| URD-REQ-009 | residual 必须通过实际 payload、标准眼低阶污染与 low/median/high power calibration。 | must |
| URD-REQ-010 | 必须恰好冻结 18 physical carrier locks 和 72 nominal configs。 | must |
| URD-REQ-011 | 主分析只使用 `NOMINAL_MAIN_FFT_MTF_555_v2` 定义的 OpticStudio FFT MTF acquisition。 | must |
| URD-REQ-012 | 贯焦不得改变 retina、carrier P/R/Q、IOL position、ELP 或实体面型。 | must |
| URD-REQ-013 | 每个成功 config 保存第 5 节要求的 MTFa/MTF/像差/footprint/provenance。 | must |
| URD-REQ-014 | 自动形成 36 个 EDOF−MONO matched-pair delta。 | must |
| URD-REQ-015 | 单 config 失败不得显示 completed，必须允许只重跑失败项。 | must |
| URD-REQ-016 | 同输入、同软件/settings/manifest/locks 的重复运行必须满足 repeatability gate。 | must |
| URD-REQ-017 | GUI 保持极简：路径、Build/Validate/B0/Carriers/Run72/Rerun、进度和日志。 | should |
| URD-REQ-018 | 结构化科学结果以 CSV/JSON 为主，关键 `.zmx` 保留 provenance。 | must |

---

# 9. Acceptance

| ID | Acceptance |
| --- | --- |
| URD-AC-001 | ZOS-API lifecycle 成功/失败均明确，无假 completed。 |
| URD-AC-002 | 双基座 AL/STOP/IOL landmarks 与冻结值一致。 |
| URD-AC-003 | 标准眼 EPD6/C40/footprint/index/wavelength calibration 通过。 |
| URD-AC-004 | A0/B0.20/C0 正式冻结且下游 hash 不变。 |
| URD-AC-005 | 18 个 carrier 的 P/Q/SA replay 与 formal lock 一致。 |
| URD-AC-006 | 三 residual 及 low/median/high calibration 正式通过。 |
| URD-AC-007 | physical carrier manifest 恰好 18 行；nominal manifest 恰好 72 行；36 pair keys。 |
| URD-AC-008 | TASK-009 三代表 sampling convergence/repeatability 和 6-config integration 通过后才允许 Run72。 |
| URD-AC-009 | Run72 恰好 72 completed configs、1080 through-focus rows、36 paired deltas；失败项不得混入 completed。 |
| URD-AC-010 | 结果可追溯到 baseline/settings/manifest/lock-set/OpticStudio version/run ID。 |

---

# 10. MVP 范围外

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

# 11. 当前不可变边界

截至 2026-08-19：

- A0/B0.20/C0 frozen；
- `TDD-999` 已解除；
- 18 carrier locks / 3 residual locks / 72 manifest 已正式冻结；
- 主实验尚未 Run72；
- TASK-009 只允许验证新的 FFT-MTF v2 分析方法，不得重建或重新优化 TASK-005–008 scientific assets。
