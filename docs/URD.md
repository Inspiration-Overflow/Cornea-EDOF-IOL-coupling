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

项目属于机制性光学研究，不是临床决策支持系统，不用于患者级 IOL 或术式推荐。

MVP 的软件目标不是建立通用光学平台，而是把已经冻结的科学模型可靠地自动化、批量化和审计化，减少人工逐个修改 Zemax 文件造成的错误和版本漂移。

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

全部 nominal configs 固定：

- wavelength = 555 nm；
- field = 0°；
- centered；
- IOL tilt = 0；
- IOL decentration = 0；
- cornea decentration = 0；
- micro-monovision defocus = 0。

从 TASK-008 起，代表测试与 Run72 都必须**从冻结的 `physical_carriers.csv` / `nominal_72.csv` 选择身份**。不得在分析脚本中重新拼接一个平行的配置宇宙。

---

# 4. 主分析：FFT MTF / MTFa-only

## 4.1 唯一主 acquisition

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

Python 不建立第二套光学传播引擎；仅做确定性数据读取、单位换算、插值、积分与贯焦摘要。

## 4.2 Main-analysis settings

active settings ID：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
```

exact settings SHA-256：

```text
0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
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

B0 selection 与 Zernike readback 不属于该 settings identity，必须各自使用独立、版本化 contract。

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

在 \(F\in[-0.50,+0.50]D\) 内，以 MTFa 最大值定义 distance peak。

并列规则：先最小 \(|F|\)，再选择较大的 signed F。若结果落在 ±0.50 D 边界，记录 `peak_search_censored=true`。

## 4.6 DOF50

DOF50 是固定命名指标，不是可调 settings 参数：

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

取包含 distance peak、且 MTFa≥T50 的连续区间；相邻 0.25-D sample 间用线性插值求 crossing。

输出 far / near / width 及 censor flags。

## 4.7 Through-focus MTFa mean

\[
TF\_MTFa\_mean=\frac1{3.5D}\int_{-3.00}^{+0.50}MTFa(F)dF
\]

用于连续贯焦总体质量比较，不单独设 acceptance threshold。

## 4.8 全眼高阶像差 readback

主实验额外读取完整全眼 Zernike n=3..6，用于 C4、C6 与 HOA RMS。该读取使用独立 contract：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

其身份必须随结果保存，不得静默由 main FFT-MTF settings 代替。

## 4.9 双坐标

每个贯焦结果同时保存：

- `defocus_retina_d` — 因果/实体模型锚定坐标；
- `defocus_shape_d = defocus_retina_d - distance_peak_retina_d` — 只用于曲线形态比较。

shape recenter 不得改变 `.zmx`、retina、IOL、ELP 或任何实体面型。

---

# 5. 每个 config 的正式结果与实体不变性

至少保存：

- 15-plane through-focus rows；
- MTFa；
- MTF10/20/30/40/50/60；
- distance peak defocus / MTFa；
- MTFa at 0 D；
- DOF50；
- TF_MTFa_mean；
- whole-eye C4 / C6 / HOA RMS；
- corneal/STOP/IOL footprints；
- unintended vignetting flag；
- working model file hash；
- **in-memory entity fingerprint before/after**；
- retina/IOL/ELP before/after；
- main-analysis settings hash；
- HOA-readback settings ID/hash；
- config/run/environment/manifest/lock provenance。

in-memory entity fingerprint 至少覆盖：

- carrier R_ant/R_post；
- anterior/posterior Q；
- CT/material；
- IOL position；
- retina axial position；
- corneal/IOL surface identity；
- surface count / STOP identity。

贯焦时允许临时改变 OBJECT vergence，因此 OBJECT thickness 不进入实体 fingerprint；运行结束必须恢复。

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
- C4；
- C6；
- HOA RMS。

其中：

```text
DeltaF_residual = distance_peak_retina_d(EDOF) - distance_peak_retina_d(MONO)
```

始终使用 retina-anchored frame。

---

# 7. TASK-009 方法与生产合同闸门

Run72 前必须验证三个代表 pair：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

这些 pair 必须由冻结 `nominal_72.csv` 读取，不能由脚本自行构造。

### Sampling convergence

每个代表 EDOF config 比较 64/128/256。128→256 必须满足：

- distance-peak MTFa relative change ≤2%；
- TF_MTFa_mean relative change ≤2%；
- distance peak shift ≤0.25 D；
- DOF50 width change ≤0.25 D。

### Repeatability

128 重复运行必须满足：

- distance-peak grid sample 相同；
- distance-peak MTFa relative change ≤0.1%；
- TF_MTFa_mean relative change ≤0.1%；
- C4/C6 repeatability ≤0.001 µm。

### Six-config production integration

三个 matched MONO+EDOF pair，共 6 configs，必须使用真实 `AnalysisBackend` 并通过正式 `run_analysis_batch()` 路径，验证：

- frozen manifest selection；
- RunEnvironment；
- config-level running/completed/failed semantics；
- ConfigResult validator；
- artifact recording；
- in-memory entity invariants；
- matched-pair delta / `DeltaF_residual`。

仅由独立 probe 脚本手工组装 dict/CSV 不算 production-contract PASS。

### Limited extraction diagnostic

允许少量 MFE `MTFA Grid=1` 或同一 FFT-MTF family 的独立 readback 作为数据提取/单位检查；只记录差异，不自行增加新的科学阈值。

TASK-009 本地 evidence 仍是 `formal_artifact=false`。128 只有在上述 gate 全部通过且 Web review 接受独立 extraction evidence 后，才正式写为 production sampling lock。

---

# 8. 用户场景与 GUI

## 8.1 核心用户场景

| Scenario | Expected outcome |
| --- | --- |
| 启动并连接 OpticStudio | 显示安装路径、连接/license 状态；失败则明确终止，不伪成功 |
| Build / Validate | 构建或验证 scientific assets，显示 PASS/FAIL 与输出位置 |
| B0 Scan / Lock | 使用冻结五候选流程并读取正式 B0 lock，不允许下游回调 |
| Build / Inspect Carriers | 查看已冻结 18 carriers / 3 residuals / 72 manifest provenance |
| Run72 | 一次执行 frozen 72-config manifest，并显示 completed/failed/remaining |
| Rerun Selected | 只重跑失败或用户明确选择的 config，生成新 run_id |
| Audit | 从 config ID 追溯 baseline/settings/manifest/lock/model/result/environment |

## 8.2 GUI 最小要求

GUI 保持极简，只负责 workflow orchestration，不持有 scientific truth。至少提供：

- OpticStudio 安装路径显示与选择；
- 项目目录显示与选择；
- Build / Validate / B0 / Carriers / Run72 / Rerun 操作入口；
- 当前阶段与当前 config ID；
- completed / failed / remaining；
- 简单进度条；
- 运行日志区域；
- Open Output Folder。

MVP 不要求复杂光学编辑器、三维交互图、云端队列或多用户系统。长任务不得并发启动；MVP 不要求 Pause/Cancel，失败恢复由配置级 Rerun 完成。

---

# 9. 软件功能需求

| ID | Requirement | Priority |
| --- | --- | --- |
| URD-REQ-001 | 使用 Python + ZOS-API 控制 OpticStudio 2026 R1 Sequential Mode，并可靠管理 session lifecycle。 | must |
| URD-REQ-002 | 使用版本化 ScientificBaseline、settings ID/hash、artifact hash 与 immutable provenance。 | must |
| URD-REQ-003 | 构建并验证 LB/ATC 双基座。 | must |
| URD-REQ-004 | 构建并锁定 `STD_IOL_EYE_2024` EPD6 calibration asset。 | must |
| URD-REQ-005 | A0/B0.20/C0 一旦冻结，下游只读。 | must |
| URD-REQ-006 | WFS/RAD/HOA 使用平台特异 SA target 和 power-specific Q(P)。 | must |
| URD-REQ-007 | 每个 Base×Cornea×Platform 生成独立 physical carrier。 | must |
| URD-REQ-008 | MONO/EDOF matched pair 的 carrier 参数必须完全相同，唯一设计差异为 residual。 | must |
| URD-REQ-009 | residual 必须通过实际 payload、标准眼低阶污染与 low/median/high power calibration。 | must |
| URD-REQ-010 | 必须恰好冻结 18 physical carrier locks、3 residual locks 和 72 nominal configs，并从正式 manifest 驱动分析。 | must |
| URD-REQ-011 | 主分析只使用 `NOMINAL_MAIN_FFT_MTF_555_v2` 定义的 OpticStudio FFT MTF acquisition；settings hash 必须与冻结值一致。 | must |
| URD-REQ-012 | 贯焦不得改变 retina、carrier P/R/Q、IOL position、ELP 或实体面型；必须用 in-memory entity fingerprint 验证。 | must |
| URD-REQ-013 | 每个成功 config 保存第 5 节要求的 MTFa/MTF/像差/footprint/settings/provenance。 | must |
| URD-REQ-014 | 自动形成 36 个 EDOF−MONO matched-pair delta。 | must |
| URD-REQ-015 | 单 config 失败不得显示 completed，必须允许只重跑失败项并生成新 run_id。 | must |
| URD-REQ-016 | 同输入、同软件/settings/manifest/locks 的重复运行必须满足 repeatability gate。 | must |
| URD-REQ-017 | 提供第 8 节定义的极简 GUI/workflow orchestration、进度与日志。 | should |
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
| URD-AC-007 | physical manifest 恰好 18 行；nominal manifest 恰好 72 行；36 pair keys；重新加载可复算相同 manifest/lock-set identity。 |
| URD-AC-008 | TASK-009 三代表 sampling convergence/repeatability、真实 6-config batch integration 与 Web extraction review 通过后才允许 Run72。 |
| URD-AC-009 | Run72 恰好 72 completed configs、1080 through-focus rows、36 paired deltas；失败项不得混入 completed。 |
| URD-AC-010 | 结果可追溯到 baseline、main settings hash、HOA settings hash、manifest、lock-set、OpticStudio version、run ID 与 entity fingerprint。 |

---

# 11. 输出、失败与重跑

正式分析至少形成：

- 每 config `config_result.json`；
- through-focus CSV；
- through-focus MTFa 图；
- 0 D MTF 图；
- matched-pair result 表；
- run/environment logs；
- failed/rerun status；
- 可追溯工作模型 `.zmx`。

输出必须使用稳定 config ID，不依赖人工从文件名猜实验条件。

任一 config 失败：

- 该 config 标记 `failed`；
- 已完成的其他配置不回滚；
- 不计入 completed acceptance；
- `Rerun Selected` 只选择失败/指定项；
- rerun 使用新 run_id；
- 只有 frozen 72 个 config 全部成功后 Run72 才可整体 PASS。

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
- 主实验尚未 Run72；
- TASK-009 只允许验证 FFT-MTF v2 分析方法和生产执行合同，不得重建或重新优化上游 scientific assets。
