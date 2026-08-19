# ADD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **文档角色：** Axiomatic Design / Design Split。  
> **来源：** `URD-0001 v1.6`。本文只规定功能需求到设计参数的拆分，不重新定义科学数值。

## Metadata

- document_id: `ADD-0001`
- version: `1.6`
- status: `approved`
- source_urd: `URD-0001 v1.6`
- last_updated: `2026-08-19`
- design_goal: MVP、低耦合、fail-closed、可追溯、可配置级重跑

---

# 1. 总体设计原则

系统只保留一套科学真相：

```text
ScientificBaseline / frozen assets
→ immutable carrier + residual locks
→ exact frozen 18/72 manifest
→ versioned analysis settings
→ manifest-driven Zemax acquisition
→ deterministic scalar post-processing
→ formal batch/result/provenance store
```

设计必须满足：

1. 上游 scientific locks 对下游只读；
2. Zemax 是主光学计算 oracle；
3. Python 只做确定性数据提取、单位转换、积分、贯焦摘要和 paired delta；
4. 主分析只有一条 production acquisition：OpticStudio FFT MTF Analysis；
5. 分析配置身份必须来自 TASK-008 frozen manifest，不在脚本中重建平行配置宇宙；
6. TASK-009 的 6-config integration 与 Run72 使用同一个真实 `AnalysisBackend → run_analysis_batch` production contract；
7. 不为了结果漂亮回调 cornea/carrier/residual；
8. 每个 long action 独立失败、独立记录、可按配置重跑；
9. Web 端负责规范/主代码/审核，本地负责真实 ZOS-API 适配与实机 evidence；
10. GUI 只做 orchestration，不持有 scientific truth。

---

# 2. FR / DP

| FR | 功能需求 | DP | 设计参数 |
| --- | --- | --- | --- |
| FR-001 | 可可靠建立/关闭 OpticStudio 会话 | DP-001 | `ZosSessionAdapter`，显式 lifecycle/typed errors |
| FR-002 | 保存 immutable scientific provenance | DP-002 | `ProjectStore` + SHA-256 + artifact index + baseline/settings/environment identity |
| FR-003 | 建立/验证 bases、standard eye、A/B/C scientific assets | DP-003 | `ScientificAssetWorkflow` |
| FR-004 | 对五个 B candidate 产生可复现推荐并人工冻结 B0 | DP-004 | `B0Workflow` + deterministic rank + review lock |
| FR-005 | 求 18 个 power-specific carriers 并验证 residual | DP-005 | `CarrierWorkflow` + P→Q(P) + low/median/high residual gate |
| FR-006 | 产生并重新加载 exact 18/72 immutable manifest | DP-006 | `ManifestBuilder` + strict `ManifestLoader` |
| FR-007 | 对 frozen nominal configs 运行主 MTF 分析 | DP-007 | `ZosFftMtfAnalysisBackend` + `run_analysis_batch` + MTFa engine |
| FR-008 | 自动形成 MONO/EDOF paired deltas | DP-008 | `MatchedPairDelta` post-processing |
| FR-009 | 隔离配置级失败与 rerun | DP-009 | append-only run history + target selection + new run ID |
| FR-010 | 提供最小桌面入口 | DP-010 | thin `CustomTkinter` shell，不持有 scientific truth |

---

# 3. 关键解耦

## 3.1 Scientific asset 与 analysis 解耦

A0/B0.20/C0、18 carriers、3 residuals、72 configs 在 analysis 开始前已经冻结。AnalysisWorkflow 只能读取：

- frozen `physical_carriers.csv` / `nominal_72.csv`；
- carrier/model hash；
- residual provenance；
- manifest / lock-set identity；
- `NOMINAL_MAIN_FFT_MTF_555_v2` exact settings hash；
- 独立的 HOA readback settings ID/hash。

它不得写回任何上游 lock。

## 3.2 Carrier 与 residual 解耦

physical carrier identity 包含：P、R_ant/R_post、Q、CT、material、IOL position、achieved SA 与 residual identity/policy provenance。

`DeltaF_residual` 属于分析结果，不进入 physical carrier lock hash。

## 3.3 Zemax acquisition 与 Python metric 解耦

### Zemax 负责

- FFT MTF sagittal/tangential modulation；
- effective focal length；
- Zernike；
- real-ray footprint/vignetting；
- loaded in-memory optical entity state。

### Python 负责

- cycles/mm→cycles/degree；
- sagittal/tangential average；
- 0..60 cpd deterministic interpolation；
- MTFa；
- distance peak；
- distance-anchored DOF50；
- TF_MTFa_mean；
- shape-recentered axis；
- EDOF−MONO deltas；
- deterministic in-memory entity fingerprint hashing。

Python 不重新传播光场。

## 3.4 Probe 与 production contract 解耦

Sampling convergence 可直接调用同一真实 backend 获得 evidence，但 **production-contract gate** 必须经过 `run_analysis_batch()`，因为只有该路径负责：

- frozen manifest selection；
- RunEnvironment；
- running/completed/failed state；
- ConfigResult validation；
- artifact recording；
- failed-target isolation / rerun semantics。

独立 probe 手工组装 JSON/CSV 不可替代 production integration。

---

# 4. 主分析 DP

## DP-007A — Settings identity

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

只包含真正改变主 FFT-MTF/MTFa 结果的设置：555 nm、EPD3/5、+0.50→−3.00 D/0.25 D、sampling candidate128、convergence64/128/256、no polarization、0..60 cpd/1 cpd、固定 10..60 cpd 输出。

DOF50 的 50% 是命名指标定义，不作为可调 settings 字段。B0 与 Zernike readback 使用各自独立 settings identity。

## DP-007B — Frozen manifest loader

TASK-008 的 `physical_carriers.csv`、`nominal_72.csv`、`manifest.sha256` 必须：

1. strict schema parse；
2. 重建 18 `CarrierLock`；
3. 重新生成 canonical 72 configs；
4. 与 CSV 逐行身份一致；
5. manifest hash 与 TASK-008 evidence 一致；
6. lock-set hash 可复算一致。

任一不一致 fail before optical acquisition。

## DP-007C — FFT MTF primitive

单个 config/defocus plane：

```text
load verified working model
→ set EPD
→ set analysis-layer object vergence
→ run OpticStudio FFT MTF
→ read cycles/mm + tangential + sagittal + runtime API metadata
→ restore object vergence
```

禁止保存带临时贯焦状态的 carrier。

## DP-007D — Frequency normalization / MTFa

使用真实 EFL：

\[
mm/degree=EFL\tan(1^\circ)
\]

只允许 acquired support 内插值到 0..60 cpd；不足覆盖即 fail。

\[
MTFa=\frac1{60}\int_0^{60}\frac{MTF_{sag}+MTF_{tan}}2df
\]

## DP-007E — Through-focus summary

- distance peak：±0.50 D 内最大 MTFa；
- DOF50：包含 distance peak 的 ≥50% distance-peak MTFa 连续区间；
- `TF_MTFa_mean`：+0.50→−3.00 D 区间的平均 MTFa；
- shape axis 只后处理，不改实体模型。

## DP-007F — Versioned aberration readback

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

读取 Z7..Z28，派生 C4/C6/HOA RMS；该 identity 单独随结果保存。

## DP-007G — Entity invariants

每 config 在 OBJECT vergence 改动前后生成 in-memory entity fingerprint。fingerprint 必须覆盖至少：

- surfaces 1..IMAGE 的 role/type/R/Q/thickness/material/STOP identity；
- carrier R_ant/R_post、Q_ant/Q_post；
- carrier first-order power identity；
- retina axial position；
- IOL position / ELP；
- surface count。

OBJECT thickness 故意排除，因为它是贯焦分析变量；结束必须恢复。

## DP-007H — Real production backend

`ZosFftMtfAnalysisBackend.run_config()` 负责：

- 校验 formal carrier/residual SHA；
- 依据 `NominalConfig` 构造 MONO 或 EDOF working model；
- 运行15 planes FFT-MTF；
- EFL、Zernike、footprint/vignetting；
- before/after entity fingerprint；
- CSV/图/working `.zmx`；
- 完整 `ConfigResult`。

`run_analysis_batch()` 负责批次状态、environment、artifact/provenance 与失败隔离。

---

# 5. TASK-009 risk gate 设计

Run72 之前，三个 frozen pair 由 `nominal_72.csv` 选择：

1. LB+A0+WFS+EPD3；
2. ATC+B0+RAD+EPD5；
3. ATC+C0+HOA+EPD5。

### Sampling gate

三个 EDOF config 均跑 64/128/256；128→256：

- distance-peak MTFa relative ≤2%；
- TF_MTFa_mean relative ≤2%；
- distance peak shift ≤0.25 D；
- DOF50 width change ≤0.25 D。

### Repeatability gate

128 同条件独立重复：

- peak grid sample 相同；
- distance-peak MTFa relative ≤0.1%；
- TF_MTFa_mean relative ≤0.1%；
- C4/C6 ≤0.001 µm。

### Production-contract gate

三个 pair 的 MONO+EDOF 共 6 configs 必须由 `ZosFftMtfAnalysisBackend` 经 `run_analysis_batch()` 完整运行，并形成 `ConfigResult`、run/environment/artifact records、matched deltas 与 `DeltaF_residual`。

### Independent extraction check

允许使用 MFE `MTFA Grid=1` 或同 family 独立数据导出检查少量固定频率。只记录差异，不成为第二条 production path，也不新增未预注册 threshold。

### Sampling lock ownership

本地 TASK-009 evidence 最多写 `production_sampling_candidate_passed=true`；不能自行把 128 标为正式 locked。Web 审核 cross-check 与完整 evidence 后，才允许写 production sampling lock 并进入 Run72。

---

# 6. GUI / rerun DP

DP-010 的最小 shell 保留：安装路径、项目目录、Build/Validate/B0/Carriers/Run72/Rerun、当前 config、进度、completed/failed/remaining、日志与 Open Output Folder。

长任务串行；MVP 不要求 Pause/Cancel。恢复路径是配置级 failed-only rerun，且必须产生新 run ID。

---

# 7. 设计矩阵

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
DP-006 Formal 18/72 manifest + strict reload
   ↓
DP-007 Manifest-driven FFT-MTF production backend
   ↓
DP-008 Pair deltas
   ↓
DP-009 Acceptance / rerun
   ↓
DP-010 GUI orchestration
```

不存在需要下游反向优化上游 scientific assets 的设计耦合。

---

# 8. Error strategy

以下情况必须 fail-closed：

- ZOS runtime/license/API type 不可用；
- manifest CSV/schema/hash/lock-set 不匹配；
- carrier/residual asset hash mismatch；
- FFT MTF frequency support < 60 cpd；
- sagittal/tangential 列无法唯一识别；
- non-finite MTF/Zernike/EFL；
- in-memory entity fingerprint 改变；
- retina/IOL/ELP 改变；
- unintended vignetting；
- result artifact 不完整却试图标 completed；
- TASK-009 convergence/repeatability/6-config integration 不通过。

允许本地机械适配 API enum/header/cast/runtime array shape；不得因 API 适配改科学阈值、模型或 lock。

---

# 9. 当前冻结边界

截至 2026-08-19：

- TASK-007 complete，TDD-999 cleared；
- TASK-008 complete，18 carrier / 3 residual / 72 nominal manifest frozen；
- TASK-009 analysis design 已完成 review-hardening；
- Run72 尚未开始；
- TASK-009 只验证分析方法与 production execution contract，不重建 TASK-005–008。
