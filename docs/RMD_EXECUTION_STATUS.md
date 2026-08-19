# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 仍规定任务依赖和 STOP 条件；本文件只记录当前真实状态。

## 当前基线与活动项目

```text
Scientific baseline = MVP_2026_v2
canonical OpticStudio lens format = .zmx
active local project = project_mvp_2026_v2_zmx
```

历史 `project_mvp_2026_v2` 中已经锁定的 `.zos` 继续作为原始 provenance，不改名、不改 hash。

## 已完成的核心工作

### TASK-005B — 双基座

两个基座已在 `.zmx` 项目中重新 build/reload/validate：

```text
BASE_LB_PSEUDOPHAKIC.zmx
SHA256 3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c

BASE_ATC_M3_PSEUDOPHAKIC.zmx
SHA256 217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c
```

冻结几何仍为：

```text
LB AL = 23.950 mm
ATC-M3 AL = 24.477 mm
post-cornea → STOP = 3.150 mm
post-cornea → IOL anterior reference = 4.500 mm
n ≈ 1.336
λ = 555 nm
field = 0
fixed plane IMAGE
```

005B 的两个角膜面只是重合的模块参考面，不代表物理零厚度角膜。

### TASK-005C — STD_IOL_EYE_2024

TASK-005C 已正式完成并锁定。生产路径采用 MFE `ZERN`，不依赖工作站上不稳定的 `AS_ZernikeStandardCoefficients` settings type。

正式 readback：

```text
EPD = 6.000 mm
λ = 546.0 nm
IOL-reference footprint = 5.22108317213591 mm
Z11 = 0.4736063027853602 waves
Z37 = 0.00026011052367169805 waves
C40 = 0.2585890413208067 µm
```

科学 gate：

```text
C40 = +0.258 ± 0.005 µm   PASS
footprint = 5.15 ± 0.10 mm PASS
```

当前 `.zmx` 正式标准眼：

```text
STD_IOL_EYE_2024.zmx
SHA256 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414
```

### `.zmx` canonical migration

PR #23 已合并。以后新 lens asset 使用 `.zmx`；历史 `.zos` 只保留 provenance。

新旧文件在本工作站上出现相同 SHA；项目仍按历史 path+hash 保留旧 lock。

## 当前进行中 — TASK-005D 角膜冻结资产

分支：

```text
feat/task-005d-cornea-lock-assets
```

005D 补齐 TASK-005 剩余角膜冻结链，不提前进入正式 EDOF carrier/pair lock。

### 已完成的 Web 端实现

共同主实验角膜 scaffold：

```text
MAIN_CORNEA_LIOU_555_v1
λ = 555 nm
reference anterior R/Q = +7.77 / -0.18
CT = 0.50 mm
posterior R/Q = +6.40 / -0.60
cornea n = 1.376
aqueous n = 1.336
```

第一阶段固定后角膜，A/B/C 只改变前表面。

厚角膜一阶 −3 D distance baseline：

```text
reference corneal power = 42.251148573823 D
distance target power = 39.251148573823 D
anterior distance radius = 8.282294760256 mm
```

处方/构造：

```text
A0:
  Binary4
  T=-3D
  EOZ≈5.0 mm
  ΔC40 target=+0.13 µm
  2.50→3.25 mm numerical smooth transition
  8 nominal transition slices

B0.10/B0.15/B0.20/B0.25/B0.30:
  Even Asphere
  T=-3D
  OZ=6.0 mm
  r^4 control -> respective ΔC40 targets

C0:
  Binary4
  T=-3D
  near diameter=3.0 mm
  ADD_Rx=+1.75 D
  transition=0.75 mm
  OZ=6.5 mm
  4/8/16 transition-slice diagnostics
```

C0 的 `ADD_Rx` 只定义目标处方分布；实际局部/环带光学结果由最终物理表面 ray trace 输出。

`REF_MONO_CORNEA_LOCK` 的候选特异 radius solve、standard-eye near-SA-neutral conic solve、最多两轮 power–conic 回查已编码。

B0 专用 Huygens MTF 采集和 17-plane `Q_lock` acquisition 已编码；五候选结果继续复用既有 `b0.py` 排序规则。

本地主要入口已经收敛到：

```text
scripts/build_task_005d_cornea_candidates.py
scripts/run_task_005d_b0_scan.py
```

详细契约：

```text
docs/TASK_005D_CORNEA_LOCK_ASSETS.md
```

### 当前唯一下一步 — Phase A

先只运行：

```text
build_task_005d_cornea_candidates.py
```

让 OpticStudio 实机产生：

- reference / distance cornea；
- A0；
- 五个 B candidates；
- C0 N4/N8/N16；
- `TASK_005D_CORNEA_CANDIDATES.json`。

Web 端审核该 JSON 后，才决定是否运行真实 B0 scan。当前不要求本地做设计判断或手工调参数。

### 尚未完成

必须等真实 OpticStudio 结果后才能确认：

- A0 achieved ΔC40 与表型；
- 五个 B 的 achieved ΔC40 / Even-Asphere coefficients；
- C0 Binary4 4/8/16 基本离散稳定性；
- `REF_MONO_CORNEA_LOCK` 的真实 radius/conic；
- A0 + 五个 B 的 EPD3/EPD5 lock curves；
- B0 recommendation、形态审核和用户确认；
- 正式 A0/B0/C0/REF_MONO locks。

这些结果不得由 Web 端伪造。

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
| TASK-005D | **Web 端实现完成，待 Phase A 实机** | 构建 A/B/C diagnostics |
| TASK-006 | B0 排序算法完成 | Phase A 通过后跑真实五点 scan |
| TASK-007 | carrier science gate framework 完成 | 等 TASK-005/006；TDD-999 仍阻断 formal locks |
| TASK-008 | manifest/lock 代码框架完成 | 等 TASK-007 |
| TASK-009 | analysis API scaffold 完成 | 等正式 carriers；先 3 代表配置 |
| TASK-010 | GUI scaffold 已复核 | 后续 full-flow smoke |
| TASK-011 | acceptance checker 完成 | 代表配置通过后才 Run72 |

## 仍有效的 STOP 条件

1. 不得为 API 适配改变 `MVP_2026_v2`、standard-eye EPD6、546 nm、Liou/Norrby C40 gate 或平台 SA targets。
2. 005B/005C 已锁资产不得被下游重写。
3. A0/B0/C0 必须在 WFS/RAD/HOA 主结果可见前冻结；B0 只在 LB + `REF_MONO_CORNEA_LOCK` 中选择。
4. `TDD-999` 未解除前不得创建正式 EDOF carrier/pair locks 或 Run72。
5. 三代表配置未完成 sampling convergence + 独立 MTF cross-check 前不得 Run72。
6. synthetic/surrogate 测试数据不能进入正式科学 locks/manifests/论文结果。

## 工作方式

Web 端承担文档、研究、主要代码编写、静态审查和 Git 整合；本地 zcode 只做必须依赖 Windows + OpticStudio 的最小实机求解/读回。复杂任务按小步提交 Git，避免长时间工作只保存在未提交状态。
