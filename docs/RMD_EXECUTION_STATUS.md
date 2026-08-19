# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 规定任务依赖和 STOP 条件；本文件只记录当前真实状态。

## 当前基线与活动项目

```text
Scientific baseline = MVP_2026_v2
canonical OpticStudio lens format = .zmx
active local project = project_mvp_2026_v2_zmx
integration target = main
```

历史 `project_mvp_2026_v2` 中已经锁定的 `.zos` 继续作为原始 provenance，不改名、不改 hash。

## 已完成核心资产

### TASK-005B — 双基座

已在 `.zmx` 项目中 build/reload/validate 并锁定：

```text
BASE_LB_PSEUDOPHAKIC.zmx
SHA256 3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c

BASE_ATC_M3_PSEUDOPHAKIC.zmx
SHA256 217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c
```

冻结几何：LB AL=23.950 mm；ATC-M3 AL=24.477 mm；post-cornea→STOP=3.150 mm；post-cornea→IOL anterior reference=4.500 mm；aqueous/vitreous n≈1.336；λ=555 nm；field=0；IMAGE 固定。

### TASK-005C — STD_IOL_EYE_2024

已正式完成并锁定。生产 Zernike acquisition 使用 MFE `ZERN`。

```text
EPD = 6.000 mm
λ = 546.0 nm
IOL-reference footprint = 5.22108317213591 mm
C40 = 0.2585890413208067 µm
STD_IOL_EYE_2024.zmx SHA256 = 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414
```

## TASK-005D / TASK-006 — 角膜 A/B/C 与 B0：完成并冻结

共同主实验物理角膜仍为 `MAIN_CORNEA_LIOU_555_v1`；A/B/C 只改变前表面，第一阶段固定后角膜。

```text
A0: Binary4, T=-3 D, EOZ≈5.0 mm, ΔC40 target=+0.13 µm
B candidates: Even Asphere, T=-3 D, OZ=6.0 mm, ΔC40 target=+0.10…+0.30 µm
C0: Binary4, T=-3 D, near diameter=3.0 mm, ADD_Rx=+1.75 D, transition=0.75 mm, OZ=6.5 mm
```

### Phase A / A.1 — PASS

真实 OpticStudio build/readback 已通过。主要结果：

```text
reference C40 = +0.2573993720 µm
A0 achieved ΔC40 = +0.1329457134 µm
B0.10 = +0.1022823683 µm
B0.15 = +0.1486436926 µm
B0.20 = +0.2002078217 µm
B0.25 = +0.2463973195 µm
B0.30 = +0.2990855153 µm
C0 N8→N16 ΔC40 change = -0.0002593781 µm
A0 N8→N16 ΔC40 change = -0.0001341103 µm
```

A0 nominal N8 已冻结；不增加 N32，不重新调 conic。

### Phase B.0 — 历史 STOP

旧 `AS_HuygensMtf` production 路径因 Python.NET / `ZemaxEngine.dll` settings-type 加载失败停止。该失败仅属于 Huygens MTF Analysis API 路径，不外推到 Huygens PSF。B0 production 后续已改为 MFE `MTFA`。

### Phase B.1 — PASS；B0 production 参数冻结

冻结 `CORNEA_LOCK_B0_555_v2`：

```text
MFE MTFA diffraction MTF
Samp = 3
Grid = 0
Data Type = 0
Wave = 1
Field = 1
frequency = 0..50 cycles/mm, step 5
EPD = 3/5 mm
defocus = +0.50 → -3.50 D, 17 planes
```

实机敏感性证据：

```text
Samp 2→3      max |ΔQ_lock| = 0.00221683
Samp 3→4      max |ΔQ_lock| = 0.00067564
5→2.5 cyc/mm  max |ΔQ_lock| = 0.00492149
```

这些值只作为工程冻结证据，不构成新的自动科学 threshold。

### Phase B.2 — PASS；完整五候选 scan

在 commit `c9720ae6975cb2b0176045a2eb1975569c70d704`、clean Git checkout、冻结 v2 settings 下完成真实 OpticStudio full scan；exit 0，`scan_complete=true`，无 hard error，残留 OpticStudio/Zemax 进程=0。

source scan hash：

```text
11d8eac7a79696d4f5219b60bd79cadad7bdc114994b77e8afe1b6325ae7af84
```

五候选结果：

| candidate | ΔC40 (µm) | EPD3 retention | EPD5 retention | EPD3 DOF_lock_abs (D) | EPD5 DOF_lock_abs (D) | eligible | rank |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| B0.10 | 0.10228 | 0.98882 | 0.83211 | 1.21641 | 1.28146 | true | 3 |
| B0.15 | 0.14864 | 0.98294 | 0.76782 | 1.22015 | 1.32341 | true | 2 |
| B0.20 | 0.20021 | 0.97581 | 0.72053 | 1.22231 | 1.33766 | true | 1 |
| B0.25 | 0.24640 | 0.96839 | 0.68355 | 1.22578 | 1.39449 | false | — |
| B0.30 | 0.29909 | 0.95877 | 0.63851 | 1.23080 | 1.26312 | false | — |

所有 A0/B candidate-specific `REF_MONO` calibration 均 PASS。

### Phase B.3 — PASS；morphology review

原始 A0 + 五候选曲线重新构造后 source scan hash 与保存值完全一致，scan report 逐字段一致。五个 B 候选均未出现预先规定的“明显、稳定双峰 + 有意义深谷”；因此五项 `morphology_reject=false`，未增加新阈值，deterministic recommendation 保持 `B0.20`。

### Phase B.4 — PASS；B0.20 正式锁定

通过现有 `scripts/review_task_005d_b0.py` 写入不可变正式 artifact：

```text
locks/B0_LOCK.json
candidate_id = B0.20
recommendation_id = B0.20
override = false
formal_artifact = true
selection_locked = true
artifact SHA256 = 24c25fea95db394998c0a4dd2ef7b0499e1e792c1275c117c23faeba0d2ea06c
source scan hash = 11d8eac7a79696d4f5219b60bd79cadad7bdc114994b77e8afe1b6325ae7af84
reviewed scan hash = 11d8eac7a79696d4f5219b60bd79cadad7bdc114994b77e8afe1b6325ae7af84
```

`locks/artifact_index.csv` 的 B0_LOCK SHA-256 与磁盘独立复算一致，`locked=true`。最终离线检查：`pytest tests/unit = 157 passed`、Ruff PASS、compileall PASS、`uv lock --check` PASS。

**A0 / B0.20 / C0 从此作为冻结角膜输入；后续 IOL 结果不得回头调 B0。**

## TASK-005D 与主实验 pipeline 的边界

B0 使用 MFE MTFA 只是角膜冻结 acquisition。TASK-009/Run72 主实验仍保持：

```text
Huygens PSF
→ deterministic FFT
→ complex OTF
→ radial MTF / MTFa / VSOTF
```

三代表配置的 sampling convergence 和独立 MTF cross-check 仍留在 TASK-009。

## 当前下一步 — TASK-007 IOL residual / carrier 科学 gate

当前不需要继续修改角膜代码，也不需要重跑 TASK-005D OpticStudio。下一阶段首先在 Web 端完成 WFS-like / RAD-like / HOA-like residual scientific payload 的独立审核与版本冻结。

`TDD-TEST-999` 仍是正式 carrier/Run72 的唯一前置科学 STOP：

1. 三个平台必须有 versioned residual scientific payload；
2. 必须冻结 piston/global-defocus 数值 tolerance；
3. 每个平台必须在其实际 carrier powers 的 low/median/high 代表点完成 residual calibration oracle。

上述定义完成后，再安排本地 OpticStudio 做最小代表点验证；不得先生成正式 carrier locks 或 Run72。

## RMD task 状态

| Task | 状态 | 下一步 |
| --- | --- | --- |
| TASK-001 | 完成 | 无 |
| TASK-002 | ZOS session 实机通过 | 保持 worker/进程约束 |
| TASK-003 | 完成 | 保持 baseline/hash provenance |
| TASK-004 | metric engine 离线完成 | TASK-009 代表配置 cross-check |
| TASK-005A | 完成 | 无 |
| TASK-005B | 完成并锁定 | 下游只读 |
| TASK-005C | 完成并锁定 | 下游只读 |
| TASK-005D | **完成；A0/B0.20/C0 冻结** | 无；下游只读 |
| TASK-006 | **完成；B0.20 immutable lock 已生成** | 无 |
| TASK-007 | science gate framework 完成 | **当前工作：解除 TDD-999** |
| TASK-008 | manifest/lock 代码框架完成 | 等 TASK-007 |
| TASK-009 | analysis API scaffold 完成 | 等正式 carriers；先 3 代表配置 |
| TASK-010 | GUI scaffold 已复核 | 后续 full-flow smoke |
| TASK-011 | acceptance checker 完成 | 代表配置通过后才 Run72 |

## 仍有效 STOP 条件

1. 005B/005C/B0 已锁资产不得被下游重写。
2. A0/B0.20/C0 已冻结，不得根据 WFS/RAD/HOA 后续结果反向调参。
3. `TDD-999` 未解除前不得创建正式 EDOF carrier/pair locks 或 Run72。
4. 三代表配置未完成 sampling convergence + 独立 MTF cross-check 前不得 Run72。
5. synthetic/surrogate 数据不能进入正式科学 locks/manifests/论文结果。

## 工作方式

复杂任务小步 Git checkpoint。Web 端承担文档、研究、主要代码、静态审查和 Git 整合；本地 ZCode 只做依赖 Windows + OpticStudio 的最小实机求解/读回，不把科学设计决策交给本地反复试错。
