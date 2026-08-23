# Model Revision R6/R7 — 24-carrier rebuild 与 exact-carrier validation

> 日期：2026-08-21  
> 前置状态：R4.2 Web ACCEPT；R5 FROZEN  
> 本阶段：R6 + R7 合并为一次本地 OpticStudio batch  
> R8：**未授权**

## 1. 目的

R6/R7 不再继续优化 +20 D pilot，而是回答一个新的问题：

> R5 在 +20 D pilot 上冻结的 WFS/RAD/HOA Binary4 机制，能否以同一 normalized residual 定义稳定移植到真实 24 个 power-specific physical carriers？

正式 carrier 空间：

```text
2 base eyes
× 4 corneas: N0 / A0 / B0 / C0
× 3 platforms: WFS / RAD / HOA
= 24 physical carriers
```

其中 N0 是未治疗 native cornea reference；A0/B0/C0 为冻结的三类术后角膜。

## 2. 每个 physical carrier 的 P→Q(P) 闭环

每个 `Base × Cornea` 先建立一个 Q=0 analytical carrier，并在**固定曲面视网膜**、3 mm **physical STOP** 条件下求基础 radius/power。

随后每个平台独立：

1. 用当前实际 carrier power/radius 进入 `STD_IOL_EYE_2024`；
2. 按平台 SA target 求 `Q_k(P)`；
3. 回到 actual eye，在固定 retina、3 mm physical STOP 下检查 Q 引入的 focus shift；
4. 若绝对 equivalent vergence shift 达到既有 `0.125 D` recheck threshold，则重新求 radius/power；
5. power 一旦改变，必须重新进入标准眼重新求 Q；
6. 最多允许既有 2 个 P/Q engineering recheck cycles；
7. 最终 physical carrier 冻结后，MONO 与 EDoF 必须共享该 exact carrier。

**EDoF residual 本身不得触发单独的 P/Q refocus。** 如果 EDoF 机制在 carrier range 上失败，应返回 Web 决定 residual power-specific refit，而不是破坏 matched MONO/EDoF carrier identity。

## 3. revised actual-eye pupil/retina 语义

R6/R7 的 actual-eye carrier solve 和 ray health 均不得调用 legacy `EntrancePupilDiameter` carrier-focus helper。

actual eye 必须继续：

```text
Aperture Type = Float By Stop Size
STOP = surface 3
3 mm pupil => STOP SemiDiameter 1.5 mm
5 mm pupil => STOP SemiDiameter 2.5 mm
cornea SD = 5 mm
IOL SD = 3 mm
retina SD = 5 mm
```

Retina：

- LB：Standard R=-12.000 mm, Q=0；
- Atchison M1 -3D：Biconic Ry=-12.732/Qy=.199, Rx=-12.628/Qx=.192。

标准眼仍允许 EPD6，因为它只承担 IOL mechanism calibration，不属于主研究 pupil 定义。

## 4. R5 normalized residual 首选移植

R6 首先应用 R5 freeze 的 power-independent normalized representation：

```text
c_zone(P) = c_base(P) + delta_c_zone_R5
Q_zone(P) = Q_base_surface(P) + delta_Q_zone_R5
alpha4(P) = alpha4_R5
alpha6(P) = alpha6_R5
```

neutral zone 的所有 delta/alpha 永远为 0。

复杂度永久保持：

```text
WFS = R
RAD = R+Q+A4
HOA = R+Q+A4+A6
```

同时保持：

```text
Np = 0
all diffraction order = 0
native p2 = 0
Na = 3
no A8+
fixed zone boundaries
```

R6/R7 **不允许自动 power-specific refit**。

## 5. Binary4 serialization

对每个 exact carrier：

- actual MONO 从 analytical carrier 做一次 fresh analytical→Binary4；
- actual EDoF 也从同一 analytical carrier独立做一次 fresh analytical→Binary4；
- standard MONO / EDoF 同理；
- 禁止通过 Binary4 MONO 二次 ChangeType/configure 生成 EDoF。

每次 serialization 必须回读：

- Nz / Na / Np；
- zone boundaries；
- R / Q / p2 / p4 / p6；
- diffraction order；
- C0；
- C1 diagnostic；
- minimum conic radicand。

C0 必须通过；C1 继续 manufacturing diagnostic only。

## 6. WFS / HOA mechanism gate

WFS 与 HOA 仍以 source-mechanism residual OPD readback 为主。

R6/R7 使用已经存在的 serialized R4 engineering gate：

- RMS <= `2% × 1.25 = 2.5%` target peak-to-peak；
- max <= `5% × 1.25 = 6.25%` target peak-to-peak。

MTF 不进入 mechanism gate。

## 7. RAD mechanism gate

RAD 继续以真实 OpticStudio spherical `POWP Data=0` 为主要机制验证。

每个 exact RAD carrier 继续使用 Px：

```text
0.0, 0.1, ..., 1.0
```

并记录实际 radial intercept 后评价 target `P_RAD(r)`。

R6/R7 不新增更严的绝对 POWP threshold。本地 hard identity/regression gate 仍是：

1. 所有 non-zero target sample 保持同号；
2. RMS error < 被 Web 拒绝 R4 baseline `1.923769959492952 D`；
3. max abs error < 被拒 R4 baseline `6.2575543068007216 D`。

R4.2 +20 D 的 `0.58637 / 1.51227 D` 只作为 comparison evidence，不是所有 power 必须优于的 hard threshold。

如果 normalized residual 在某个 power 上通过上述 gate 但比 +20 D 明显变差，应保留结果给 Web 判断，不得本地自动 refit。

## 8. low-order gate

所有 24 exact carriers 的 standard mechanism readback继续：

```text
|global defocus| <= 0.125 D
```

piston = diagnostic only。

不得用 p2、IOL translation、retina shift 或 MTF tuning 去“修 piston”。

## 9. actual-eye ray health

每个 actual MONO 与 EDoF 均在：

- 3 mm physical pupil；
- 5 mm physical pupil；

执行 full-eye real-ray health。

任何真实 3 mm IOL clear-radius clipping/vignetting 必须如实报告，禁止自动扩大 IOL optic。

## 10. low / median / high full standard audit

为避免把 24-carrier mechanism gate不必要地膨胀为 R8，R6/R7 对每个平台从实际 8 个 power 中确定：

- low；
- deterministic lower-median；
- high；

共 9 个 exact carriers，额外执行完整 standard-eye optical audit：

- best focus；
- C4^0；
- C6^0；
- HOA RMS；
- MFE MTFA / MTFS / MTFT；
- Grid=1；
- sampling=128；
- 0–100 cyc/mm，step 5；
- ray health。

这仍是 diagnostic only，MTF 不用于 residual fitting。

## 11. 本地 runner

```text
scripts/run_model_revision_r6_r7.py
```

输出：

```text
project_mvp_2026_v2_zmx/
  diagnostics/
    model_revision/
      r6_r7/
        MODEL_REVISION_R6_R7_EVIDENCE.json
        q0/
        carriers/
        validated/
```

canonical evidence：

```text
MODEL_REVISION_R6_R7_EVIDENCE.json
```

## 12. local PASS 定义

`local_r6_r7_passed=true` 只表示：

- exact 24 carrier key-space 完整；
- 全 24 carrier P→Q(P) / SA replay 成功；
- WFS/HOA serialized mechanism gates 全过；
- 8 个 RAD exact carriers 的 real POWP identity/regression gate 全过；
- 全 24 global defocus 在 ±0.125 D；
- actual-eye MONO/EDoF 3/5 mm ray health 全过；
- Binary4 structure / C0 / min-radicand 合法；
- low/median/high full standard audits 成功。

它**不表示**：

- R8 已获授权；
- normalized R5 residual 已成为商业 manufacturing truth；
- HOA manufacturing REVIEW 已解除；
- PR 可以 merge。

## 13. FAIL 的处理

任何 carrier 失败均停止在 R6/R7：

- 不自动 refit；
- 不加 A6/A8；
- 不动 zone boundaries；
- 不解冻 p2；
- 不放宽 defocus；
- 不用 MTF 调参；
- 不进入 R8。

Web review 根据失败位置决定是否需要 power-specific mechanism refit，且任何 refit 必须继续以 WFS/HOA source mechanism 或 RAD real POWP 为目标。

## 14. 阶段边界

```text
R2/R3 = ACCEPT
R4/R4.2 = ACCEPT
R5 = FROZEN
R6/R7 Web implementation = READY
R6/R7 local execution = PENDING
R8 = LOCKED
PR merge = NOT AUTHORIZED
```
