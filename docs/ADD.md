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
- production_mtf_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- production_sampling: `128`

---

# 1. 总体设计原则

系统只保留一套科学真相：

```text
ScientificBaseline / frozen assets
→ immutable carrier + residual locks
→ exact frozen 18/72 manifest
→ versioned numerical settings
→ versioned MTF acquisition + angular-scale contract
→ manifest-driven Zemax acquisition
→ deterministic scalar post-processing
→ formal batch/result/provenance store
```

设计原则：

1. 上游 scientific locks 对下游只读；
2. Zemax 是主光学计算 oracle；
3. Python 只做确定性频率映射、积分、贯焦摘要和 paired delta；
4. 主生产 MTF 只有一条 acquisition：MFE `MTFA Grid=1`；
5. 每个 matched pair 的 cpd 坐标由 residual-free MONO EFFL 固定，MONO/EDOF 与所有 defocus/sampling 共用；
6. TASK-009 representative integration 与 Run72 使用同一个 `AnalysisBackend → run_analysis_batch` production contract；
7. `RunEnvironment` 必须绑定 numerical settings、manifest/lock-set、acquisition ID/hash 和 frequency-scale mode；
8. 不为了结果漂亮回调 cornea/carrier/residual；
9. 每个 long action 独立失败、独立记录、可按配置重跑；
10. GUI 只做 orchestration，不持有 scientific truth。

`AS_FftMtf` production path 已退休；代码中的 `NOMINAL_MAIN_FFT_MTF_555_v2` 和 `fft_mtf_*` 字段名仅为保持既有 settings hash，不代表实际 production acquisition。

---

# 2. FR / DP

| FR | 功能需求 | DP | 设计参数 |
| --- | --- | --- | --- |
| FR-001 | 可靠建立/关闭 OpticStudio 会话 | DP-001 | `ZosSessionAdapter`，显式 lifecycle/typed errors |
| FR-002 | 保存 immutable scientific + analysis provenance | DP-002 | `ProjectStore` + SHA-256 + artifact index + `RunEnvironment` |
| FR-003 | 建立/验证 bases、standard eye、A/B/C scientific assets | DP-003 | `ScientificAssetWorkflow` |
| FR-004 | 对五个 B candidate 产生可复现推荐并人工冻结 B0 | DP-004 | `B0Workflow` + deterministic rank + review lock |
| FR-005 | 求18个 power-specific carriers 并验证 residual | DP-005 | `CarrierWorkflow` + P→Q(P) + low/median/high residual gate |
| FR-006 | 产生并严格重载 exact 18/72 immutable manifest | DP-006 | `ManifestBuilder` + strict `ManifestLoader` |
| FR-007 | 对 frozen nominal configs 运行正式 MTF/MTFa 分析 | DP-007 | `ZosMtfaPairScaleAnalysisBackend` + `run_analysis_batch` + MTFa engine |
| FR-008 | 自动形成 MONO/EDOF paired deltas | DP-008 | `MatchedPairDelta` post-processing |
| FR-009 | 隔离配置级失败与 rerun | DP-009 | append-only run history + target selection + new run ID |
| FR-010 | 提供最小桌面入口 | DP-010 | thin `CustomTkinter` shell，不持有 scientific truth |

---

# 3. 关键解耦

## 3.1 Scientific asset 与 analysis 解耦

A0/B0.20/C0、18 carriers、3 residuals、72 configs 在 analysis 前已冻结。AnalysisWorkflow 只能读取：

- frozen `physical_carriers.csv` / `nominal_72.csv`；
- carrier/residual SHA；
- manifest / lock-set identity；
- `NOMINAL_MAIN_FFT_MTF_555_v2` settings ID/hash；
- `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2` acquisition ID/hash；
- `paired_residual_free_MONO_EFFL` frequency-scale mode；
- `TASK009_PRODUCTION_SAMPLING_LOCK_v1`，sampling=128；
- HOA readback settings ID/hash。

不得写回上游 lock。

## 3.2 Carrier 与 residual 解耦

physical carrier identity 包含 P、R_ant/R_post、Q、CT、material、IOL position、achieved SA 与 residual identity/policy provenance。`DeltaF_residual` 是分析结果，不进入 physical carrier lock hash。

## 3.3 Zemax acquisition 与 Python metric 解耦

### Zemax 负责

- residual-free MONO nominal-distance EFFL readback；
- MFE `MTFA Grid=1` production MTF；
- MFE `MTFT/MTFS Grid=1` limited diagnostic；
- Zernike；
- real-ray footprint/vignetting；
- loaded in-memory optical entity state。

### Python 负责

- `pair_mm_per_degree = EFFL_MONO × tan(1°)`；
- cpd→cycles/mm direct query target mapping；
- 0..60 cpd 1-cpd grid MTFa integration；
- distance peak / DOF50 / TF_MTFa_mean；
- shape-recentered axis；
- EDOF−MONO deltas；
- deterministic entity fingerprint hashing。

Python 不重新传播光场。

## 3.4 Numerical settings 与 acquisition identity 解耦

`NOMINAL_MAIN_FFT_MTF_555_v2` 继续冻结数值设置及其 hash；真正的生产 acquisition 由独立 contract 标识：

```text
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
```

因此无需为了修正 acquisition/角尺度语义重命名 numerical settings 或改动 settings hash。

## 3.5 Probe 与 production contract 解耦

Sampling convergence 可直接调用真实 backend；但正式 production integration 必须通过 `run_analysis_batch()`，因为该路径负责 frozen selection、RunEnvironment、running/completed/failed、artifact recording 与 failed-target isolation。

---

# 4. 主分析 DP

## DP-007A — Numerical settings identity

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

冻结：555 nm、EPD3/5、+0.50→−3.00 D、0.25 D step、15 planes、production sampling=128、convergence64/128/256、no polarization、0..60 cpd / 1 cpd、固定10/20/30/40/50/60 cpd。

## DP-007B — Frozen manifest loader

TASK-008 的 `physical_carriers.csv`、`nominal_72.csv`、`manifest.sha256` 必须 strict parse、重建18 locks、重建72 configs、与 loaded CSV 全等、manifest hash一致、lock-set hash一致。任一不一致在 optical acquisition 前失败。

## DP-007C — Pair angular-scale reference

对每个 `pair_key` 只测一次 residual-free MONO nominal-distance EFFL：

```text
pair_reference_effl_mm = EFFL(MONO, no residual)
pair_mm_per_degree = pair_reference_effl_mm * tan(1°)
```

该 scale 固定用于 MONO+EDOF、所有 defocus plane、所有 sampling。EDOF-state EFFL 只作诊断。

## DP-007D — MFE MTFA Grid=1 primitive

单个 config/defocus plane：

```text
load verified working model
→ set EPD
→ set analysis-layer object vergence
→ map 0..60 cpd directly with paired-MONO scale
→ MFE MTFA Grid=1, Data Type=0, Wave1, Field1
→ restore object vergence
```

MFE sampling mapping：64→Samp2、128→Samp3、256→Samp4；formal production sampling=128。

## DP-007E — Metric engine

\[
MTFa=\frac1{60}\int_0^{60}MTFA(f)df
\]

使用1-cpd grid梯形积分。固定 MTF10..60 直接取同一 production MTFA acquisition。Distance peak、DOF50、TF_MTFa_mean 按 URD 固定定义。

## DP-007F — Versioned aberration readback

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

读取 Z7..Z28，派生 C4/C6/HOA RMS；该 identity 单独随结果保存。

## DP-007G — Entity invariants

每 config 在 OBJECT vergence 改动前后生成 in-memory entity fingerprint，覆盖 surfaces1..IMAGE role/type/R/Q/thickness/material/STOP、carrier power/R/Q、retina、IOL position/ELP、surface count。OBJECT thickness 故意排除但结束必须恢复。

## DP-007H — Real production backend + run provenance

`ZosMtfaPairScaleAnalysisBackend.run_config()` 负责 formal asset SHA、MONO/EDOF working model、15-plane MTFA、paired-MONO scale、HOA、footprint/vignetting、entity snapshot、CSV/图/working `.zmx`、完整 `ConfigResult`。

`run_analysis_batch()` 在任何 acquisition 前要求 backend 自报：

```text
acquisition_contract_id
acquisition_contract_hash
frequency_scale_mode
```

并与 `RunEnvironment` 完全一致；不一致 fail-closed。随后才负责 run state、environment persistence、artifact recording 与失败隔离。

---

# 5. TASK-009 risk gate 与正式 lock

代表 pair：LB+A0+WFS+EPD3、ATC+B0+RAD+EPD5、ATC+C0+HOA+EPD5。

预注册 convergence：128→256 peak MTFa relative≤2%、TF mean relative≤2%、peak shift≤0.25D、DOF50 width change≤0.25D。

repeat128：peak sample same、peak MTFa relative≤0.1%、TF mean≤0.1%、C4/C6≤0.001µm。

三个 pair 的 MONO+EDOF 共6 configs 已由 `ZosMtfaPairScaleAnalysisBackend → run_analysis_batch()` 完整通过；20/40/60 cpd limited diagnostic 已验证 `MTFA=(MTFT+MTFS)/2` 且不引入新阈值。

Web 正式锁定：

```text
TASK009_PRODUCTION_SAMPLING_LOCK_v1
production_sampling = 128
production_sampling_locked = true
sampling_escalation_256_active = false
```

无需 256→512 escalation。

---

# 6. GUI / rerun DP

DP-010 最小 shell：安装路径、项目目录、Build/Validate/B0/Carriers/Run72/Rerun、当前 config、进度、completed/failed/remaining、日志与 Open Output Folder。长任务串行；MVP 不要求 Pause/Cancel；失败恢复为 failed-only rerun，新 run_id。

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
DP-007 Manifest-driven paired-MONO MTFA production backend
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

必须 fail-closed：ZOS runtime/license/API不可用；manifest/hash/lock-set mismatch；carrier/residual SHA mismatch；pair MONO EFFL non-finite；backend acquisition ID/hash/scale 与 RunEnvironment 不一致；MFE operand/header/mapping异常；MTF/Zernike non-finite；entity fingerprint、retina/IOL/ELP 改变；unintended vignetting；artifact不完整；config failure。

允许本地机械适配 API enum/header/cast/runtime array shape；不得因此改科学阈值、模型或 lock。

---

# 9. 当前冻结边界

截至 2026-08-19：TASK-007 complete、TDD-999 cleared；TASK-008 complete、18 carrier / 3 residual / 72 nominal manifest frozen；TASK-009 corrected pair-MONO optical gate PASS；sampling=128 Web formal lock；Run72 尚未开始；TASK-005–008 scientific assets 只读。