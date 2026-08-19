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

新旧文件在本工作站上出现相同 SHA，说明此前 `.zos` 扩展名下的内容本身已采用相同序列化；项目仍按历史 path+hash 保留旧 lock。

## 当前进行中 — TASK-005D 角膜冻结资产

新分支：

```text
feat/task-005d-cornea-lock-assets
```

005D 补齐 TASK-005 剩余的角膜冻结链，不提前进入正式 EDOF carrier/pair lock。

### 已冻结的处方层

新增共同主实验角膜 scaffold：

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

A/B/C prescriptions：

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
  respective ΔC40 targets

C0:
  Binary4
  T=-3D
  near diameter=3.0 mm
  ADD_Rx=+1.75 D
  transition=0.75 mm
  OZ=6.5 mm
```

C0 使用 quintic radial weight；`rN=1.50 mm`、`rT=2.25 mm`、`rOZ=3.25 mm`，2.25→3.25 mm 保留远用主导环带。

详细实现契约见：

```text
docs/TASK_005D_CORNEA_LOCK_ASSETS.md
```

### Phase A 实机诊断 — PASS

真实 OpticStudio 已完成 reference/distance cornea、A0、五个 B 候选、C0 N4/N8/N16 的构建和 MFE-ZERN readback。

关键结果：

```text
reference C40 = +0.2573993720 µm
A0 achieved ΔC40 = +0.1329457134 µm

B0.10 = +0.1022823683 µm
B0.15 = +0.1486436926 µm
B0.20 = +0.2002078217 µm
B0.25 = +0.2463973195 µm
B0.30 = +0.2990855153 µm

C0 N4→N8  ΔC40 change = -0.0011966407 µm
C0 N8→N16 ΔC40 change = -0.0002593781 µm
```

五个 B 候选目标和控制系数单调、构造稳定；C0 nominal N8 已达到足够的 MVP 离散稳定性。

A0 目标本身 PASS，但其 `Z37≈0.121 waves` 高于连续 B 候选。由于 A0 将作为 B0 排序阈值参考，在 Phase B 前只追加一次低成本 A0 N4/N8/N16 离散检查；不改变 scientific prescription，不重新优化每个 N 的 conic。

Phase A 首次使用相对 `--project-dir` 时暴露了 OpticStudio 原生 SaveAs 与 Python cwd 的相对路径差异。Web 端已把 005D 两个入口统一 `resolve()`；该问题不影响绝对路径重跑后的成功实机光学结果。

### 当前下一步

只运行：

```text
scripts/run_task_005d_a0_convergence.py
```

固定 Phase A 已求得的 `inner_conic=-0.1125`，比较 A0 transition slices 4/8/16 的 achieved ΔC40 与 Z37。

若 N8→N16 已基本稳定，则直接进入 Phase B `REF_MONO + B0 real scan`；否则只修 A0 数值离散实现。

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
| TASK-005D | **Phase A PASS** | A0 最小离散检查 → Phase B |
| TASK-006 | B0 排序算法完成 | 等待真实五点 scan 后锁 B0 |
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

Web 端承担文档、研究、主要代码编写、静态审查和 Git 整合；本地 zcode 只做必须依赖 Windows + OpticStudio 的最小实机求解/读回，不再把设计决策交给本地反复试错。
