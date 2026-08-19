# TASK-007 Phase B Web 审核：18 carrier 与 residual calibration

> 日期：2026-08-19  
> 状态：**Web 科学审核完成；待纯 Python review CLI 本地复核后物化 reviewed evidence**  
> source evidence commit：`a67288a4af1bdd4a9ec692c3b797f0e3e3469d9d`  
> source evidence SHA-256：`88f89484d1684ce43005d5ce7a30feb88b485065962ee4df5ae517426a231c51`

## 1. 审核范围

本次只审核 TASK-007 consolidated batch 已经产生的证据，不重新运行 OpticStudio，也不修改 A0/B0.20/C0、carrier scaffold、平台 SA target 或 residual seed。

源批次已经完成：

- 6 个 Base×Cornea 共用 Q=0 P0；
- exactly 18 个 Base×Cornea×Platform provisional P/Q carrier；
- 3 个 physical Grid Sag residual；
- 每个平台 low/median/high 三点，共 9 个 calibration record；
- actual/standard residual readback；
- MONO/EDOF ray health；
- actual/standard C4/C6；
- EPD3 17-point MFE MTFA through-focus mechanism diagnostic。

源批次的 `numerical_hard_gates_passed=false` 仅由 RAD 三个 actual-eye SSAG low-order readback 的 piston 触发；其余 carrier、SA replay、P-Q convergence、standard-eye low-order readback、ray health 均完成。

## 2. RAD source false negative 的根因

### 2.1 数据表现

RAD 的 actual-eye residual readback 在外周出现非物理的恒定平台，导致：

```text
measured piston ≈ -0.043 µm
measured global defocus ≈ +0.095 D
```

其中 piston 超出冻结的 `0.010 µm` policy。

但同一 residual、同一 low/median/high power 在 `STD_IOL_EYE_2024` 的 EPD6 readback 中：

```text
piston ≈ +0.0013 … +0.0015 µm
global defocus ≈ -0.0012 … -0.0013 D
```

均明显位于原冻结验收带内。

同时：

- RAD 三个 actual-eye MONO/EDOF ray-health 均 PASS；
- 无意外 vignette；
- through-focus 曲线 finite；
- Grid Sag import/save/reload 成功；
- standard-eye residual readback 能继续跟随冻结 radial target。

### 2.2 实现原因

source batch 的 actual-eye residual readback 使用 `SSAG` Mode 0，并固定在数学 normalization radius `2.575 mm` 上取样。

OpticStudio 官方 operand 文档说明，surface sag 的 Mode 0 会服从该面的 clear/mechanical semi-diameter；超过实际光学区域时可以返回平边/常 sag，而 Mode 1 才是忽略 aperture、直接求数学 surface sag 的模式。

因此，当 actual eye 的当前 IOL footprint/semi-diameter 小于固定的 2.575 mm 数学 readback 域时，Mode-0 SSAG 会在外周进入平边，从而把 aperture clipping 错当成 residual 自身的 piston/defocus。

这也解释了为什么：

- RAD 外周仍有明显 radial structure，因此最容易被剪切并产生假性 low-order；
- WFS 外周尾部变化较小，所以虽然也存在 aperture-limited readback 风险，却没有越过 policy；
- HOA 的 EDOF 功能结构在约 1.1 mm 后平滑退出，因此对该问题不敏感。

## 3. 规范性 low-order gate 的恢复

TASK-007 science freeze 已经规定：

```text
seed normalization domain = nominal standard-eye IOL footprint R=2.575 mm
formal standard-eye validation = STD_IOL_EYE_2024 / EPD6 / ~546 nm
```

因此正式 residual piston/global-defocus gate 应使用：

```text
STD_IOL_EYE_2024
EPD = 6 mm
imported physical Grid Sag
low/median/high actual carrier powers
```

actual-eye SSAG readback 仍可保留作为 implementation diagnostic，但不能用一个超出当前 clear/mechanical semi-diameter 的 Mode-0 固定半径拟合去否决 residual。

本次修订：

- **不改变** piston tolerance `0.010 µm`；
- **不改变** global-defocus tolerance `0.125 D`；
- **不改变** residual seed/amplitude；
- **不改变** WFS/RAD/HOA SA targets；
- **不新增**任何事后 numerical threshold；
- 只纠正 source consolidated runner 对既有 scientific oracle 的使用域。

## 4. 18 carrier 审核

源 evidence 已包含 exactly 18 个唯一 carrier，并通过原 `validate_18_provisional_carriers()`。

总体范围：

```text
WFS: P 约 21.05–25.48 D, Q -7.5 … -4.0
RAD: P 约 21.18–25.59 D, Q -11.0 … -5.75
HOA: P 约 20.81–25.26 D, Q = 0
```

WFS/RAD 六个 carrier 均在一次 P-Q 回查内收敛；HOA 不需回查。所有最终 carrier 保持 posterior Q=0，SA replay 均处于原 `±0.01 µm` 目标带内。

结论：**18-carrier gate PASS。**

## 5. WFS-like mechanism review

low/median/high 三点：

- distance peak 均保持约 0 D；
- descriptive DOF50 从约 `1.19–1.21 D` 增至约 `1.29–1.33 D`；
- through-focus 为连续展宽，不出现需要用离散衍射级次解释的结构；
- standard-eye low-order gate PASS；
- MONO/EDOF ray health 3/3 PASS。

本 MVP 的 WFS-like oracle 只要求公开 phase-shift 机制被保留并产生连续焦深扩展趋势，不要求复刻商业 IOL 的绝对 MTF 或焦深。

结论：**WFS-like mechanism PASS。**

## 6. RAD-like mechanism review

low/median/high 三点：

- distance peak 均保持约 0 D；
- descriptive DOF50 稳定增至约 `2.44–2.46 D`；
- standard-eye imported residual low-order gate 3/3 PASS；
- actual-eye MONO/EDOF ray health 3/3 PASS；
- 未见 ray failure / unintended vignette；
- source actual-eye piston FAIL 已由 SSAG Mode-0 aperture clipping 解释，不属于 residual/mechanism failure。

结论：**RAD-like mechanism PASS。**

## 7. HOA-like mechanism review

low/median/high 三点的 actual-eye EDOF wavefront 均保持预期的异号主导结构：

```text
C4 < 0
C6 > 0
```

代表性数值约为：

```text
low:    C4=-0.041 µm, C6=+0.184 µm
median: C4=-0.022 µm, C6=+0.180 µm
high:   C4=-0.033 µm, C6=+0.180 µm
```

同时：

- descriptive DOF50 从约 `1.21–1.28 D` 增至约 `2.03–2.07 D`；
- 三点最佳峰均约移到 `-0.5 D`；
- standard-eye low-order gate PASS；
- ray health 3/3 PASS。

这符合本项目冻结的“4/6 阶异号 HOA + 中央延焦”机制 surrogate；不解释为商业产品制造处方复现。

结论：**HOA-like mechanism PASS。**

## 8. TDD-999 判定

Web 审核后，TDD-999 要求的科学证据已经具备：

- 3 个 versioned physical residual payload 已真实 Grid Sag import/save/reload；
- residual piston/global-defocus 在规范性的 EPD6 standard-eye domain 通过；
- exactly 18 个 actual P/Q carrier 已完成；
- 三个平台 low/median/high actual-power calibration 已完成；
- 三个平台 mechanism oracle 均通过；
- 无需修改 residual、SA target 或 tolerance。

但为保持可重复性，TDD-999 不在本文件中直接靠文字状态改变。下一步必须运行纯 Python：

```text
scripts/review_task_007_consolidated.py
```

由程序重新核验 source evidence hash、9 个 standard-eye gate、全部 ray health 和三项显式 mechanism decisions，并生成 versioned reviewed evidence。该 CLI exit 0 后，`tdd_999_cleared=true` 才作为机器可读状态生效。

## 9. 是否需要重跑 OpticStudio

**不需要。**

原因：需要的 physical payload、18 carrier、9 calibration、standard-eye readback、actual-eye ray health、through-focus 和 C4/C6 都已经存在且带 SHA-256。当前问题只在 source runner 对 actual-eye Mode-0 SSAG diagnostic 的 hard-gate 使用方式，不是光学模型本身缺数据。

## 10. 下一步

纯 Python review PASS 后，直接进入 TASK-008：

```text
18 formal physical carrier/residual locks
→ exactly 72 nominal configs
→ manifest hash / lock-set hash
```

TASK-008 只正式化已经取得的 TASK-007 evidence；无需再次启动 OpticStudio。
