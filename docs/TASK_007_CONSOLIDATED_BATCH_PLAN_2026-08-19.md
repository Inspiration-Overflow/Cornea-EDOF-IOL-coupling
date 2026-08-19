# TASK-007 综合实机批次 — 18 carrier + residual low/median/high 校准

> 日期：2026-08-19  
> 状态：**Web 端实现完成；待本地离线回归与 OpticStudio 综合实机批次**  
> 分支：`feat/task-007-iol-residuals`  
> 基线：`MVP_2026_v2`

## 1. 为什么改成综合批次

TASK-007 Phase A.0–A.3 已把主要未知项逐一消除：

- residual seed 数学定义与低阶 policy 已冻结；
- LB/ATC 代表 P-solve 已实机通过；
- `ZERO_HOA` 已明确为同一 physical carrier 的 `Q=0 + residual=0` reference，不使用 OpticStudio `Paraxial` surface；
- `POWP` 只作为 matched first-order diagnostic；
- WFS/RAD/HOA 代表 Q(P) 求解已通过；
- WFS/RAD 的实际眼 P–Q 回查均在第 1 个 cycle 收敛。

因此后续不再需要把“18 carrier”“Grid Sag capability”“low/median/high calibration”拆成多个 Web↔Local 小回合。下一轮采用一个命令、内部 fail-closed 的综合批次。

## 2. 上游冻结输入

综合批次必须只读使用：

```text
BASE_LB_PSEUDOPHAKIC
BASE_ATC_M3_PSEUDOPHAKIC
A0
B0.20 + B0_LOCK
C0 nominal N=8
STD_IOL_EYE_2024
TASK-007 Phase A.3 evidence
```

特别注意：C0 的 convergence diagnostics 包含 N=4/8/16，但 production nominal 是：

```text
C0_TRANSITION_SLICES_NOMINAL = 8
```

不得把 N=16 convergence variant 当正式 C0。

## 3. Stage 1 — 18 个 provisional physical carriers

### 3.1 先只解 6 个共同 Q=0 起点

因为三平台在加入平台特异 Q 以前共用完全相同的 `CONTROLLED_IOL_CARRIER_546_v1`，所以每个：

```text
Base × Cornea
```

只求一次 Q=0 P-solve：

```text
2 bases × 3 corneas = 6 P0 solves
```

然后从这 6 个共同起点分别分叉：

```text
WFS / RAD / HOA
```

得到 18 个平台 carrier。这样避免把同一个 Q=0 P-solve 无意义重复三次。

### 3.2 每个平台 carrier

每个 carrier：

1. 从该 Base×Cornea 的共同 P0/R0 起点开始；
2. 在 `STD_IOL_EYE_2024` EPD6 / ~546 nm 解平台 Q(P)；
3. 回实际眼 EPD3 检查 fixed-retina wavefront best focus；
4. 若 `|DeltaV| >= 0.125 D`，执行已经由 A.3 验证过的 radius→Q 回查；
5. 最多 2 cycles；
6. 最终必须：
   - anterior Q = 当前平台 Q；
   - posterior Q = 0；
   - focus recheck 不再触发；
   - standard-eye SA replay 满足 `±0.01 µm`；
   - C40 solve→replay 差 `≤0.001 µm`；
7. 形成 `ProvisionalCarrier`，但不写 formal lock。

Stage 1 结束必须有 exactly 18 unique carrier keys。

## 4. Stage 2 — 一个 residual / platform 的 physical Grid Sag

三平台继续使用 Web 已冻结的 residual seed，不在本地重新优化 amplitude。

### 4.1 Grid Sag 工程表示

使用 Sequential Grid Sag 的“base R/Q surface + imported additive sag departure”语义。

工程网格冻结为：

```text
half width = 3.05 mm
step = 0.01 mm
size = 611 × 611
interpolation = linear
```

理由：

- physical optic radius = 3.00 mm；3.05 mm 给边缘光线少量 numerical margin；
- WFS 最窄主要 transition 约 0.10 mm，0.01 mm 给约 10 个采样；
- linear interpolation 避免 WFS 分段过渡附近的高阶 spline overshoot；
- Grid Sag 只表达 residual departure，carrier 原有 Radius/Conic/CT/material 必须保留。

三个 `.DAT` 文件较大，只保存在本地诊断目录，不提交 GitHub。

### 4.2 真实 readback

导入并保存 `.zmx` 后重新加载，用 OpticStudio `SSAG` 对 MONO/EDOF 同一表面做真实 surface-sag readback，再取差值：

```text
residual sag = EDOF total surface sag - MONO base surface sag
```

由真实 readback residual sag 按实际折射率跃迁恢复 residual OPD，并在 R=2.575 mm 统一 normalization domain 上重新拟合 piston/global defocus。

硬 gate 仍只使用已冻结：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

不为 Grid Sag interpolation error 临时增加新的科学阈值；`max_abs_opd_error_um` 只记录供 Web 审核。

## 5. Stage 3 — low / median / high actual-power calibration

Stage 1 18/18 全通过以后，使用现有 deterministic selector 对每个平台 6 个实际 power 选：

```text
low
median-nearest
high
```

共：

```text
3 platforms × 3 actual powers = 9 calibrations
```

每个 calibration 同时获取：

- actual-eye Grid Sag import/readback；
- standard-eye Grid Sag import/readback；
- actual/standard residual low-order policy；
- EPD5 9-ray real-ray health / unintended-vignetting check；
- actual-eye MONO/EDOF C4/C6；
- standard-eye MONO/EDOF C4/C6；
- EPD3 的 17-point MFE-MTFA diagnostic through-focus curve；
- distance-peak shift；
- descriptive own-peak 50% width。

这里的 17-point MTFA 只是 TASK-007 mechanism-preservation diagnostic，**不是 Run72 主生产指标**，不改变已冻结的 Huygens-PSF→complex-OTF 主 pipeline。

## 6. 自动 hard gates 与人工 mechanism review 分离

### 自动 hard gates

本地脚本只自动判定：

- 18 carrier 完整唯一；
- P/Q 最多 2 次回查收敛；
- SA replay；
- Q source power identity；
- residual piston/global-defocus policy；
- ray failure / vignette。

### 不自动判定

以下仍由 Web 端从 GitHub evidence 一次性审核，不新增自动阈值：

- WFS 是否保持 phase-shift/连续延焦机制；
- RAD 是否保持 distance→near→distance 连续径向调制；
- HOA 是否保持中央 C4/C6 异号主导并在外围平滑退出；
- 贯焦曲线是否表现为合理连续展宽而非明显非物理形态。

因此输出必须：

```text
mechanism_review_pending_web = true
formal_artifact = false
tdd_999_cleared = false
```

## 7. GitHub evidence handoff

本地完整 `.zmx`、Grid Sag `.DAT` 和大型诊断文件保留在：

```text
project_mvp_2026_v2_zmx/diagnostics/task007/consolidated_batch/
```

GitHub 只提交 sanitized structured evidence：

```text
docs/evidence/task007/consolidated_batch/
  TASK_007_CONSOLIDATED_EVIDENCE.json
  TASK_007_18_CARRIERS.csv
  TASK_007_RESIDUAL_CALIBRATIONS.csv
```

repo evidence：

- 不含 Windows absolute path；
- 不含 `.zmx` 路径；
- 保留所有关键数值、hash、完整 9 组 through-focus arrays 和 wavefront/readback 证据；
- Web 端直接通过 GitHub connector 读取，不要求 ZCode 把大 JSON 贴进聊天上下文。

## 8. 本地允许自行修复的范围

为了减少不必要往返，本轮如果遇到以下 OpticStudio API 机械映射问题，ZCode 可以在同一任务内查看真实 API header/readback 后做**最小实现修复并重新运行**：

- Grid Sag interpolation 参数 cell/header 映射；
- `ImportDataFile` 返回值/调用包装；
- `SSAG` `GetOperandValue` 参数包装；
- Python.NET 类型转换；
- lint/import/typing/path/serialization。

但不得自行改变：

- residual seed 或 amplitude；
- Grid Sag 0.01 mm / 611 / linear 工程定义；
- SA targets；
- 0.125 D P–Q trigger；
- 2-cycle limit；
- residual low-order policy；
- low/median/high selection algorithm；
- A0/B0.20/C0；
- carrier scaffold。

如果需要改变上述科学/工程冻结值才能通过，则 STOP 回 Web。

## 9. 预期结果

理想情况下，本轮一次本地运行将直接给 Web：

```text
6 shared P0 solves
18 provisional carriers
3 residual Grid Sag payloads
9 low/median/high real calibrations
```

如果 18 carrier 和 9 个 numerical hard gates 全部通过，Web 只需做一次 mechanism review。若 Web 接受三平台 low/median/high 表型，下一步可以直接完成 residual/carrier formal lock 与 TDD-999 状态修订，而**不再要求额外 OpticStudio calibration rerun**。
