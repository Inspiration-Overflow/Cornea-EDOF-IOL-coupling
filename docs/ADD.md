# ADD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **文档角色：** Axiomatic Design / Design Split。  
> **来源：** `URD-0001 v1.5`。本文只规定功能需求到设计参数的拆分，不重新定义科学数值。

## Metadata

- document_id: `ADD-0001`
- version: `1.5`
- status: `approved`
- source_urd: `URD-0001 v1.5`
- last_updated: `2026-08-19`
- design_goal: MVP、低耦合、fail-closed、可追溯、可配置级重跑

---

# 1. 总体设计原则

系统只保留一套科学真相：

```text
ScientificBaseline / frozen assets
→ immutable carrier + residual locks
→ exact 18/72 manifest
→ versioned analysis settings
→ Zemax acquisition
→ deterministic scalar post-processing
→ result/provenance store
```

设计必须满足：

1. 上游 scientific locks 对下游只读；
2. Zemax 是主光学计算 oracle；
3. Python 只做确定性数据提取、单位转换、积分、贯焦摘要和 paired delta；
4. 主分析只有一条 production acquisition：OpticStudio FFT MTF Analysis；
5. 不为了结果漂亮回调 cornea/carrier/residual；
6. 每个 long action 独立失败、独立记录、可按配置重跑；
7. Web 端负责规范/主代码/审核，本地负责真实 ZOS-API 适配与实机 evidence。

---

# 2. FR / DP

| FR | 功能需求 | DP | 设计参数 |
| --- | --- | --- | --- |
| FR-001 | 可可靠建立/关闭 OpticStudio 会话 | DP-001 | `ZosSessionAdapter`，显式 lifecycle/typed errors |
| FR-002 | 保存 immutable scientific provenance | DP-002 | `ProjectStore` + SHA-256 + artifact index + baseline hash |
| FR-003 | 建立/验证 bases、standard eye、A/B/C scientific assets | DP-003 | `ScientificAssetWorkflow` |
| FR-004 | 对五个 B candidate 产生可复现推荐并人工冻结 B0 | DP-004 | `B0Workflow` + deterministic rank + review lock |
| FR-005 | 求 18 个 power-specific carriers 并验证 residual | DP-005 | `CarrierWorkflow` + P→Q(P) + low/median/high residual gate |
| FR-006 | 产生 exact 18/72 immutable manifest | DP-006 | pure-data `ManifestBuilder` |
| FR-007 | 对 nominal configs 运行主 MTF 分析 | DP-007 | FFT-MTF `AnalysisWorkflow` + MTFa engine |
| FR-008 | 自动形成 MONO/EDOF paired deltas | DP-008 | `MatchedPairDelta` post-processing |
| FR-009 | 隔离配置级失败与 rerun | DP-009 | append-only run history + target selection |
| FR-010 | 提供最小桌面入口 | DP-010 | thin `CustomTkinter` shell，不持有 scientific truth |

---

# 3. 关键解耦

## 3.1 Scientific asset 与 analysis 解耦

A0/B0.20/C0、18 carriers、3 residuals、72 configs 在 analysis 开始前已经冻结。AnalysisWorkflow 只能读取：

- carrier/model hash；
- residual provenance；
- manifest identity；
- `NOMINAL_MAIN_FFT_MTF_555_v2`。

它不得写回任何上游 lock。

## 3.2 Carrier 与 residual 解耦

physical carrier identity 包含：

- P；
- R_ant/R_post；
- Q；
- CT；
- material；
- IOL position；
- achieved SA；
- residual identity/policy provenance。

`DeltaF_residual` 属于分析结果，不进入 physical carrier lock hash。

## 3.3 Zemax acquisition 与 Python metric 解耦

### Zemax 负责

- FFT MTF sagittal/tangential modulation；
- effective focal length；
- Zernike；
- ray/footprint 等光学 oracle。

### Python 负责

- cycles/mm→cycles/degree；
- sagittal/tangential average；
- 0..60 cpd deterministic interpolation；
- MTFa；
- distance peak；
- distance-anchored DOF50；
- TF_MTFa_mean；
- shape-recentered axis；
- EDOF−MONO deltas。

Python 不重新传播光场。

---

# 4. 主分析 DP

## DP-007A — Settings identity

```text
NOMINAL_MAIN_FFT_MTF_555_v2
```

冻结：555 nm、EPD3/5、field0、15-plane +0.50→−3.00 D、1-cpd common grid、0..60 cpd、sampling candidate 128、convergence 64/128/256。

## DP-007B — FFT MTF primitive

单个 config/defocus plane：

```text
load formal model
→ set EPD
→ set analysis-layer object vergence
→ run OpticStudio FFT MTF
→ read cycles/mm + tangential + sagittal
→ restore object vergence
```

禁止保存带临时贯焦状态的 carrier。

## DP-007C — Frequency normalization

使用真实 EFL：

\[
mm/degree=EFL\tan(1^\circ)
\]

只允许 acquired support 内插值到 0..60 cpd；不足覆盖即 fail。

## DP-007D — MTFa

\[
MTFa=\frac1{60}\int_0^{60}\frac{MTF_{sag}+MTF_{tan}}2df
\]

## DP-007E — Through-focus summary

- distance peak：±0.50 D 内最大 MTFa；
- DOF50：包含 distance peak 的 ≥50% distance-peak MTFa 连续区间；
- `TF_MTFa_mean`：+0.50→−3.00 D 区间的平均 MTFa；
- shape axis 只后处理，不改实体模型。

## DP-007F — Aberration / invariant readback

每 config 同时记录 C4/C6/HOA RMS、footprints、model hash、retina/IOL/ELP invariants 和 vignetting 状态。

---

# 5. TASK-009 risk gate 设计

Run72 之前，使用三个冻结代表 pair：

1. LB+A0+WFS+EPD3；
2. ATC+B0+RAD+EPD5；
3. ATC+C0+HOA+EPD5。

### Sampling gate

三个 EDOF config 均跑 64/128/256。

128→256：

- distance-peak MTFa relative ≤2%；
- TF_MTFa_mean relative ≤2%；
- distance peak shift ≤0.25 D；
- DOF50 width change ≤0.25 D。

### Repeatability gate

128 同条件重复：

- peak grid sample 相同；
- distance-peak MTFa relative ≤0.1%；
- TF_MTFa_mean relative ≤0.1%；
- C4/C6 ≤0.001 µm。

### Production-contract gate

三个 pair 的 MONO+EDOF 共 6 configs 必须完整输出，并能形成 `DeltaF_residual` 和主要 paired deltas。

### Independent extraction check

允许使用 MFE `MTFA Grid=1` 或同 family 独立数据导出检查少量固定频率。该检查只用于发现 API/单位/列解析错误，不成为第二条 production path，也不新增未预注册 threshold。

---

# 6. 设计矩阵

按实现依赖排序：

```text
DP-001 Session
   ↓
DP-002 Store / provenance
   ↓
DP-003 Scientific assets
   ↓
DP-004 B0 lock
   ↓
DP-005 Carrier/residual science gate
   ↓
DP-006 Formal 18/72 manifest
   ↓
DP-007 FFT-MTF analysis
   ↓
DP-008 Pair deltas
   ↓
DP-009 Acceptance / rerun
   ↓
DP-010 GUI orchestration
```

主要为三角依赖，不存在需要下游反向优化上游 scientific assets 的设计耦合。

---

# 7. Error strategy

以下情况必须 fail-closed：

- ZOS runtime/license/API type 不可用；
- active manifest/hash/lock-set 不匹配；
- FFT MTF frequency support < 60 cpd；
- sagittal/tangential 列无法唯一识别；
- non-finite MTF/Zernike/EFL；
- through-focus 修改了实体模型/retina/IOL/ELP；
- unintended vignetting；
- TASK-009 convergence/repeatability 不通过；
- result artifact 不完整却试图标 completed。

允许本地机械适配 API enum/header/cast；不得因 API 适配改科学阈值、模型或 lock。

---

# 8. 当前冻结边界

截至 2026-08-19：

- TASK-007 complete，TDD-999 cleared；
- TASK-008 complete，18 carrier / 3 residual / 72 nominal manifest frozen；
- TASK-009 analysis design 已简化并版本化；
- Run72 尚未开始，因此 analysis settings v2 不触发正式主实验重跑；
- TASK-009 只验证分析方法，不重建 TASK-005–008。
