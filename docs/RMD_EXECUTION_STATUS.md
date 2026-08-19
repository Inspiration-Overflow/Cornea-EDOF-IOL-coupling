# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 仍规定任务依赖和 STOP 条件；本文件只记录当前真实状态。

## 当前基线与活动项目

```text
Scientific baseline = MVP_2026_v2
canonical OpticStudio lens format = .zmx
active local project = project_mvp_2026_v2_zmx
active branch = feat/task-005d-cornea-lock-assets
```

历史 `project_mvp_2026_v2` 中已经锁定的 `.zos` 继续作为原始 provenance，不改名、不改 hash。

## 已完成核心工作

### TASK-005B — 双基座

`.zmx` 项目中已重新 build/reload/validate：

```text
BASE_LB_PSEUDOPHAKIC.zmx
SHA256 3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c

BASE_ATC_M3_PSEUDOPHAKIC.zmx
SHA256 217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c
```

冻结几何继续为：

```text
LB AL = 23.950 mm
ATC-M3 AL = 24.477 mm
post-cornea → STOP = 3.150 mm
post-cornea → IOL anterior reference = 4.500 mm
n ≈ 1.336
λ = 555 nm
field = 0
fixed IMAGE
```

005B 的两个角膜面只是重合模块参考面，不表示物理零厚度角膜。

### TASK-005C — STD_IOL_EYE_2024

已正式完成并锁定。生产 Zernike acquisition 使用 MFE `ZERN`，不依赖工作站不稳定的 `AS_ZernikeStandardCoefficients` settings type。

```text
EPD = 6.000 mm
λ = 546.0 nm
IOL-reference footprint = 5.22108317213591 mm
Z11 = 0.4736063027853602 waves
Z37 = 0.00026011052367169805 waves
C40 = 0.2585890413208067 µm
STD_IOL_EYE_2024.zmx SHA256 = 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414
```

### `.zmx` canonical migration

PR #23 已合并。以后新 lens asset 使用 `.zmx`；历史 `.zos` 只保留 provenance。

## 当前进行中 — TASK-005D 角膜冻结资产

### 处方层

共同主实验物理角膜：

```text
MAIN_CORNEA_LIOU_555_v1
λ = 555 nm
reference anterior R/Q = +7.77 / -0.18
CT = 0.50 mm
posterior R/Q = +6.40 / -0.60
cornea n = 1.376
aqueous n = 1.336
```

A/B/C 继续只改变前表面，第一阶段固定后角膜。

```text
A0:
  Binary4
  T=-3D
  EOZ≈5.0 mm
  ΔC40 target=+0.13 µm

B0.10/B0.15/B0.20/B0.25/B0.30:
  Even Asphere
  T=-3D
  OZ=6.0 mm

C0:
  Binary4
  T=-3D
  near diameter=3.0 mm
  ADD_Rx=+1.75 D
  transition=0.75 mm
  OZ=6.5 mm
```

### Phase A — PASS

真实 OpticStudio 已完成 reference/distance cornea、A0、五个 B 和 C0 N4/N8/N16 的构建与 MFE-ZERN readback。

```text
reference C40 = +0.2573993720 µm
A0 achieved ΔC40 = +0.1329457134 µm
B0.10 = +0.1022823683 µm
B0.15 = +0.1486436926 µm
B0.20 = +0.2002078217 µm
B0.25 = +0.2463973195 µm
B0.30 = +0.2990855153 µm
C0 N8→N16 ΔC40 change = -0.0002593781 µm
```

Phase A 首次相对路径运行暴露了 OpticStudio native SaveAs 与 Python cwd 的路径解释差异；005D 两个入口现已 `project_dir.resolve()`。绝对路径重跑结果有效。

### Phase A.1 — PASS

A0 固定 `inner_conic=-0.1125`，只比较 transition slices 4/8/16：

```text
ΔC40 N8→N16 = -0.0001341103 µm
Z37  N8→N16 = +0.0019070625 waves
```

结论：A0 nominal N8 足够稳定；不增加 N32，不重新调 conic。

### Phase B.0 — Huygens production path STOP

首次长扫描在 A0 候选特异 REF_MONO 已成功构建后，首次创建 Huygens MTF analysis settings 类型时触发：

```text
Failed to create Python type for ... AS_HuygensMtf
System.IO.FileLoadException:
A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

无正式结果 JSON、无正式 lock、残留进程 0。

该失败属于 ZOS-API/Python.NET settings-type 路径，不是角膜、REF_MONO 或 B0 排序失败。不得继续反复重试 `AS_HuygensMtf`。

证据：

```text
docs/TASK_005D_PHASE_B_STOP_2026-08-19.md
```

### B0 acquisition v2 — Web 实现完成

生产 B0 MTF 已改为：

```text
CORNEA_LOCK_B0_555_v2
MFE MTFA diffraction MTF
Grid = 0
Data Type = 0
Wave = 1
Field = 1
frequency = 0..50 cycles/mm, production step 5
```

Web 端已经完成：

```text
MFE MTFA temporary-operand primitive
adjacent rows + one CalculateMeritFunction()
operand header/type validation
finally cleanup + MFE row-count restore
0–50 cycles/mm trapezoidal Q_lock
B0 acquisition switch to MTFA
B0 scan-hash provenance switch to v2
A0/B0.20 focused probe helper
Phase B.1 probe script
full v2 scan output isolation
obsolete TASK-005D Huygens/PSF fallback cleanup
unit tests
```

`Q_lock`、EPD3/EPD5、17-plane defocus grid、distance-retention gates 和 `rank_b0_candidates()` 全部不变。

完整修订依据：

```text
docs/TASK_005D_B0_MTF_ACQUISITION_REVISION_2026-08-19.md
docs/TASK_005D_CORNEA_LOCK_ASSETS.md
```

Huygens 以后只用于 3 个代表性正式配置的独立 cross-check，不再作为 B0 或 Run72 默认生产采集器。

## 当前唯一下一步 — Phase B.1

本地只运行：

```text
scripts/probe_task_005d_mtfa.py
```

Probe 仅覆盖：

```text
A0 + B0.20
EPD3 + EPD5
defocus = 0D / -1.5D
Samp = 2 / 3 / 4
frequency step = 5 / 2.5 cycles/mm
```

目的：

1. 验证当前工作站的 MFE `MTFA` API 路径；
2. 比较相邻 `Samp` 的 Q_lock；
3. 比较 5 vs 2.5 cycles/mm 的 Q_lock；
4. 冻结最小足够的生产 `Samp`。

在 Phase B.1 PASS 并冻结实际 `Samp` 前，不运行完整五候选 scan。

## RMD task 状态

| Task | 状态 | 下一步 |
| --- | --- | --- |
| TASK-001 | 完成 | 无 |
| TASK-002 | ZOS session 实机通过 | 保持 worker/进程约束 |
| TASK-003 | 完成 | 保持 baseline/hash provenance |
| TASK-004 | metric engine 离线完成 | 后续代表配置 cross-check |
| TASK-005A | 完成 | 无 |
| TASK-005B | 完成并锁定 | 下游只读 |
| TASK-005C | 完成并锁定 | 下游只读 |
| TASK-005D | **Phase A/A.1 PASS；Huygens STOP；MTFA v2 Web 实现完成** | Phase B.1 最小实机 probe |
| TASK-006 | B0 排序算法完成 | 等待 MTFA 真实五候选 scan 后锁 B0 |
| TASK-007 | carrier science gate framework 完成 | 等 TASK-005/006；TDD-999 仍阻断 formal locks |
| TASK-008 | manifest/lock 代码框架完成 | 等 TASK-007 |
| TASK-009 | analysis API scaffold 完成 | 等正式 carriers；先 3 代表配置 |
| TASK-010 | GUI scaffold 已复核 | 后续 full-flow smoke |
| TASK-011 | acceptance checker 完成 | 代表配置通过后才 Run72 |

## 仍有效 STOP 条件

1. 不得为 API 适配改变 `MVP_2026_v2`、standard-eye EPD6、546 nm、Liou/Norrby C40 gate 或平台 SA targets。
2. 005B/005C 已锁资产不得被下游重写。
3. A0/B0/C0 必须在 WFS/RAD/HOA 主结果可见前冻结；B0 只在 LB + `REF_MONO_CORNEA_LOCK` 中选择。
4. `TDD-999` 未解除前不得创建正式 EDOF carrier/pair locks 或 Run72。
5. 三代表配置未完成 sampling convergence + 独立 MTF cross-check 前不得 Run72。
6. synthetic/surrogate 数据不能进入正式科学 locks/manifests/论文结果。

## 工作方式

复杂任务必须小步 Git checkpoint。Web 端承担文档、研究、主要代码、静态审查和 Git 整合；本地 zcode 只做依赖 Windows + OpticStudio 的最小实机求解/读回，不把设计决策交给本地反复试错。
