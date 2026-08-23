# Model Revision R4 — representative +20 D mechanism-fit pilot 与本地 Codex handoff

> 日期：2026-08-21  
> 分支：`feat/model-revision-binary4-physical-pupil`  
> 上游 gate：R2/R3 Web review = **ACCEPT**  
> 本阶段性质：**pilot / evidence acquisition；不是 production expansion**

## 1. R4 要回答的问题

R3 已证明：固定 topology 的 degenerate Binary Optic 4 MONO 可以与 analytical carrier 达到数值等效。

R4 不再证明“Binary4 能不能表示一个普通 IOL”，而是分别问：

```text
WFS：固定 WFS zone topology 能否用低阶分区非球面复现 source-locked phase-shift mechanism？
RAD：固定 RAD zone topology 能否复现 source-locked radial relative-power mechanism？
HOA：固定 HOA core/transition topology 能否复现 source-locked Z4/Z6 mechanism？
```

R4 必须先回答机制问题，再看 MTF。禁止把 MTF 作为拟合 objective。

## 2. 为什么用统一约 +20 D 标准眼 pilot

R4 使用 `STD_IOL_EYE_2024` 作为**机制校准域**，而不是主实验眼。

统一 carrier：

```text
physical IOL power = +20.000 D
n_IOL = 1.460
n_medium = 1.336
CT = 1.000 mm
optic diameter = 6.000 mm
bending = symmetric biconvex
Rant = +12.3573878112 mm（约）
Rpost = -12.3573878112 mm（约）
```

每个平台仍按现有标准眼 SA calibration 解 anterior Q，因此 WFS/RAD/HOA 保留各自的 carrier spherical-aberration identity；EDoF residual 再独立拟合。

`STD_IOL_EYE_2024` 的 6-mm EPD 只属于历史标准眼/机制校准语境。它**不重新定义** R2 之后主实验模型的 3/5-mm physical STOP。

## 3. source-locked mechanism target

### 3.1 WFS

使用冻结 WFS phase-shift raw OPD：

```text
r boundaries = .55/.65/.87/1.05 mm
Delta1 = -1.02 µm surface sag
Delta2 = +0.59 µm surface sag
```

fit objective 使用由该 raw surface sag 与 index step 得到的 OPD，不使用 MTF。

### 3.2 RAD

使用冻结 radial relative-power function：

```text
0-.50      S=-0.25 D, A=0
.50-.90    S=-0.25 D, A=-3.25 D
.90-1.10   S=+3.00 D, A=+3.25 D
1.10-1.40  S=-0.25 D, A=-0.25 D
1.40-2.50  neutral
2.50-3.00  neutral
```

离线 fit 使用该 P(r) 的解析积分 raw OPD；进入 OpticStudio 后再用 `POWP` X/pupil scan 对 MONO→EDOF relative power 做独立 readback。

### 3.3 HOA

使用冻结 HOA raw OPD：

```text
lambda = 0.546 µm
Z4^0 = -0.49 waves
Z6^0 = +0.46 waves
normalization radius = 1.0 mm
core = 0-.90 mm
C2 transition = .90-1.10 mm
neutral = 1.10-3.00 mm
```

不加入 Z8+。

## 4. Binary4 parameter policy

继续冻结：

```text
Np = 0
all diffraction order = 0
Na = 3
p2 = permanently 0
p4 = logical A4
p6 = logical A6
```

复杂度严格逐级：

```text
Level 1: R
Level 2: R + Q
Level 3: R + Q + A4
Level 4: R + Q + A4 + A6
```

一个平台达到 pilot mechanism fidelity target 后立即停止，不再增加自由度。

neutral zones：

```text
RAD zone 5 (1.40-2.50) = base posterior carrier
RAD zone 6 (2.50-3.00) = base posterior carrier
HOA zone 3 (1.10-3.00) = base anterior carrier
```

WFS 五区均属于 mechanism topology，但 optimizer 可以自然得到接近 base 的退化区。

## 5. R4 fitter 的数值目标

拟合 radial grid：

```text
0–3.0 mm
step = 0.005 mm
```

为避免大外区把窄 transition zone 淹没，objective 对每个 fixed zone 给予相同总权重，再在区内平均。

绝对 piston 只代表 surface-sag 原点，因此 mechanism fidelity 比较允许一个最优常数 piston alignment；**不允许移除或优化 global defocus**。

R4 pilot 的工程目标：

```text
weighted RMS OPD error <= 2% of target peak-to-peak OPD
max absolute OPD error <= 5% of target peak-to-peak OPD
```

这两个数值只用于 R4 的“是否值得继续验证这个低阶参数化”的工程筛选，不是最终临床/科学 acceptance threshold。R5 Web review 后才能决定是否冻结为后续生产门槛。

search envelope 只是 optimizer 数值边界，不是制造 acceptance：

```text
same-sign zone curvature: |c| = 0.01–0.50 mm^-1
Q: base Q ± 50
native p4/p6 coefficient: ±0.10 mm
```

因此某个解即使 mechanism fidelity 很好，如果 R/Q/A4/A6 或 C1 slope jump 明显不合理，仍可在 manufacturing-plausibility review 被判 `REVISE/REJECT`。

## 6. C0 / C1

Binary4 依靠 OpticStudio 自动 zone sag offset 保证 C0。

R4 fitter 同样显式模拟该 C0 offset，并记录：

```text
boundary C0 error
left slope
right slope
C1 slope jump
minimum conic radicand
```

规则：

- C0 为结构 hard requirement；
- C1 不强行连续，只作为制造/光学风险诊断；
- conic radicand 必须全区有效。

## 7. OpticStudio pilot 输出

每个平台产生：

```text
R4_ANALYTICAL_MONO_<platform>.zmx
R4_BINARY4_MONO_<platform>.zmx
R4_BINARY4_EDOF_<platform>.zmx
R4_GRID_SAG_<platform>.DAT
R4_GRID_SAG_EDOF_<platform>.zmx
```

共 3 个 analytical carrier、3 个 Binary4 MONO、3 个 Binary4 EDoF、3 个历史 GridSag comparator。

最终统一 evidence：

```text
MODEL_REVISION_R4_PILOT_EVIDENCE.json
```

## 8. 保存/reload 后的 mechanism readback

Binary4 EDoF 保存后必须 reload，并核对：

```text
Nz / Na / Np
zone boundaries
zone R/Q
order = 0
p2 = 0
p4/p6
```

随后用 SSAG 直接读取 MONO→EDOF surface sag，并重新构造 OPD；serialized readback 允许相对纯 Python fit target 1.25 倍的数值 slack：

```text
RMS fraction <= 2.5%
max fraction <= 6.25%
```

这个 slack 只允许保存/reload 和 OpticStudio surface implementation 的小差异，不能用于放宽 fitter 本身的 2%/5% pilot target。

## 9. RAD 的独立 POWP 验证

RAD 额外执行 `POWP` scan：

```text
Px = 0.0, 0.1, ..., 1.0
Wave = 1
Field = on-axis
Data = spherical power
```

同一个 Px 分别读取 MONO 与 Binary4 EDoF：

```text
DeltaP_measured = POWP_EDOF - POWP_MONO
```

同时用 real-ray trace 记录该 Px 在 posterior IOL surface 的实际 radial intercept，再计算 source-locked `P_target(r)`。

R4 只记录 POWP RMS/max error，由 Web 端结合 radial plot/zone readback审核；本地不为了过 gate 调 fit。

## 10. standard-eye low-order

R4 对 serialized Binary4 residual 记录：

```text
surface-derived piston diagnostic
surface-derived global defocus
```

历史 global-defocus reference 继续使用：

```text
|global defocus| <= 0.125 D
```

R4 暂不把 surface-sag piston 当自动 hard gate。原因不是取消历史 low-order control，而是 Binary4 zone-1 vertex 把绝对 sag 原点固定为零；与可任意加常数的 imported GridSag residual 相比，二者的 surface-piston reference 不同。

因此：

- piston 仍完整记录；
- R4 不静默把它解释为已通过；
- 最终 piston convention 留到 Web/R5 明确冻结。

## 11. optical sanity：只在 mechanism fit 以后

对以下三种模型分别做：

```text
Binary4 MONO
Binary4 EDoF
historical GridSag EDoF
```

先记录 ray health，再在临时 best focus 下读取：

```text
C4^0
C6^0
HOA RMS
MFE MTFA / MTFS / MTFT, Grid=1
128 sampling
0–100 cyc/mm, 5 cyc/mm step
```

MTF 不进入 optimizer；只用于发现明显光学灾难与比较新旧 representation。

继续禁止调用 `New_FftMtf/AS_FftMtf`。

## 12. R4 本地 PASS 的含义

脚本的 `local_pilot_passed=true` 只表示：

1. 三个平台的纯 Python mechanism fit 达到 pilot target；
2. Binary4 保存/reload 后 mechanism fidelity 仍达标；
3. MONO / Binary4 EDoF / GridSag EDoF ray health 均通过；
4. serialized Binary4 residual 的 global defocus 均在历史 ±0.125 D reference 内。

它**不等于 R4 Web ACCEPT**。

以下仍需 Web 人工审核：

```text
RAD POWP profile
R/Q/A4/A6 manufacturing plausibility
C1 slope jumps
new Binary4 vs old GridSag optical behavior
MTF / HOA sanity
piston convention
```

因此 evidence 永远写：

```text
manual_web_review_required = true
automatic_progression_allowed = false
```

本地无论 PASS/FAIL 都必须停止，不进入 24 carriers、96 configs 或后续生产阶段。

## 13. 本地 Codex 执行边界

本阶段只执行一个完整批次：

```text
scripts/run_model_revision_r4_pilot.py
```

Codex 不得：

- 修改 fitter target；
- 修改 2%/5% pilot target；
- 修改 serialized 1.25x slack；
- 修改 zone boundaries；
- 解锁 p2；
- 加入 A8+；
- 调 MTF 来改善 fit；
- 改用 native FFT analysis；
- 因 manufacturing 参数难看而自行重新设计；
- 进入 full carrier expansion。

任何 hard error 或 `local_pilot_passed=false` 都保留 evidence/traceback 后回传 Web。
