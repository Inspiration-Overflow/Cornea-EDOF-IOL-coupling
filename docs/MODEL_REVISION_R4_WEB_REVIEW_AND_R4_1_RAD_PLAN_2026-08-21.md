# Model Revision R4 Web review 与 R4.1 RAD 局部光焦度修订

> 日期：2026-08-21  
> R4 execution commit：`a8f5ab5d575008adcecd76446324d1674d7b90b7`  
> R4 evidence SHA256：`936148f7aa881f55112507a2b6691f17a5863b5b54801496a3023ac84d4a8637`  
> Web 判定：**R4 overall = REVISE**

## 1. R4 已通过的部分

R4 本地执行本身有效：窄回归 4 passed、完整单元测试 248 passed、工作树 clean，三平台均通过 serialized Binary4 结构/OPD readback、ray health 与历史 global-defocus reference。

平台结论：

```text
WFS = ACCEPT
RAD = REVISE
HOA = PROVISIONAL ACCEPT
OVERALL = REVISE
```

WFS 仅用 `R` 即达到机制目标；serialized RMS/max 分别为 0.489% / 1.108%，global defocus 0.0040 D。Binary4 与历史 GridSag 的 0–100 cyc/mm MTF 最大绝对差约 0.000397。

HOA 使用 `R+Q+A4+A6`，serialized RMS/max 为 1.084% / 3.694%，global defocus -0.00095 D。Binary4 与 GridSag 的 MTF 最大绝对差约 0.00651。机制 surrogate 可接受，但 zone 2 `Q=+50` 触及搜索边界，0.9 mm 处 C1 slope jump 约 0.0486，因此暂不作为 production parameter lock。

## 2. RAD 为什么必须 REVISE

RAD 的 `R+Q+A4` 对 integrated OPD 的拟合非常好：serialized RMS/max 仅 0.270% / 0.909%。Binary4 与 GridSag 的 C4/C6/MTF 也接近。

但是 RAD 的 source identity 不是“任意近似 OPD”，而是冻结的径向相对光焦度函数 `P(r)`。R4 的独立 OpticStudio POWP readback 显示：

```text
POWP RMS error = 1.92377 D
POWP max error = 6.25755 D
```

在实际 posterior-IOL radial intercept `r≈0.9923 mm`：

```text
P_target = +1.69608 D
POWP Binary4 relative power = -4.56148 D
error = -6.25755 D
```

即关键 0.90–1.10 mm 区出现局部机制符号反转。这个结果不能用“OPD 已通过”覆盖。

OpticStudio User Guide 对 `POWP` 的定义是：计算指定面折射后、指定光瞳点处的 power/EFL；`Data=0` 为 spherical power，单位 D。因此 POWP 是本项目 RAD source identity 的直接独立验证量，而不是普通 MTF surrogate。

参考：Ansys OpticStudio User Guide, Optimization Operands Alphabetically, `POWP`。

## 3. R4.1 的最小修订原则

R4.1 **只改 RAD fitter objective**：

```text
旧：fit integrated OPD
新：fit source-locked local radial power P(r)
```

对冻结的 RAD 定义：

```text
W(r) = integral_0^r P(s) s ds
```

因此在本项目的 mm / µm / D 数值单位下：

```text
P(r) = (1/r) dW/dr
```

Binary4 的 C0 automatic sag offsets 是常数，不影响导数，所以可以从每区实际 `R/Q/A4/A6` 的 surface slope 直接构造离线 local-power proxy。`r=0` 使用 curvature limit。

这个 proxy **只用于离线 fit objective**；最终 serialized/full-ray identity 仍由真实 OpticStudio `POWP` 独立验证。

## 4. 明确不改的内容

R4.1 不改变：

- RAD source `P(r)`；
- RAD zone boundaries：`0/.50/.90/1.10/1.40/2.50/3.00 mm`；
- neutral zone 5/6；
- `Np=0`；
- diffraction order = 0；
- `Na=3`；
- native p2 = 0；
- A6 ceiling；
- `R -> R+Q -> +A4 -> +A6` complexity escalation；
- 原 R4 2% RMS / 5% max integrated-OPD engineering gate；
- serialized 1.25x slack；
- ±0.125 D historical global-defocus reference；
- +20.000 D representative carrier；
- WFS / HOA scientific definitions；
- MFE Grid=1 MTF backend、128 sampling、0–100 cyc/mm / 5 cyc/mm step；
- physical-pupil / retina 主研究定义。

没有新增一个任意的 POWP 数值 acceptance threshold。

## 5. R4.1 local gate

R4.1 重新在同一个新 HEAD 跑 WFS/RAD/HOA 三个平台：

- WFS 与 HOA 使用 R4 原 fitter，作为同 HEAD regression；
- RAD 使用 local-power objective；
- 三平台仍执行 serialized SSAG OPD、defocus、ray health、HOA、MFE Grid=1 MTF；
- RAD 仍执行完整 `Px=0.0..1.0 step 0.1` POWP readback。

在不新增数值阈值的前提下，RAD 增加一个最小 hard identity check：所有 `P_target != 0` 的 sampled points，实测 relative POWP 必须与 target 同号。POWP magnitude error 仍留给 Web review，不由本地自动调参。

因此：

```text
local_pilot_passed =
    existing engineering targets passed
    AND ray health passed
    AND |global defocus| <= 0.125 D
    AND RAD non-zero target POWP sign identity passed
```

即使 `local_pilot_passed=true`：

```text
manual_web_review_required=true
automatic_progression_allowed=false
```

## 6. 离线预检

在不调用 OpticStudio 的数学预检中，RAD local-power objective 仍在 `R+Q+A4` 首次通过原 integrated-OPD 2%/5% gate。

预期离线 local-power proxy：

```text
RMS error ≈ 0.08 D
max error ≈ 0.35 D
```

同时 integrated OPD RMS fraction 约 0.32%，仍远低于原 2% gate。

这些值只是 deterministic offline regression reference，不是新增科学 acceptance threshold。最终判定仍看真实 OpticStudio POWP evidence。

## 7. 阶段边界

R4.1 完成后必须 STOP for Web review。

禁止进入：

- R6/R7；
- 24-carrier expansion；
- 96-config production rerun；
- 任何基于 MTF 的 RAD re-optimization。
