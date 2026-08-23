# Model Revision R4 Web review 与 R4.1 RAD 球镜光焦度修订

> 日期：2026-08-21  
> R4 execution commit：`a8f5ab5d575008adcecd76446324d1674d7b90b7`  
> R4 evidence SHA256：`936148f7aa881f55112507a2b6691f17a5863b5b54801496a3023ac84d4a8637`  
> Web 判定：**R4 overall = REVISE**

## 1. R4 Web review 结论

R4 本地执行本身有效：WFS/RAD/HOA 均完成 Binary4 保存重载、结构 readback、SSAG、ray health、HOA 与 MFE Grid=1 MTF audit。

平台结论：

```text
WFS = ACCEPT
RAD = REVISE
HOA = PROVISIONAL ACCEPT
OVERALL = REVISE
```

WFS 仅用 `R` 即达到机制目标；serialized RMS/max 分别为 0.489% / 1.108%，global defocus 约 0.0040 D。Binary4 与历史 GridSag 的 0–100 cyc/mm MTF 几乎重合。

HOA 使用 `R+Q+A4+A6`；serialized RMS/max 为 1.084% / 3.694%，global defocus 约 -0.00095 D。Binary4 与 GridSag 的光学结果接近，但 zone 2 `Q=+50` 触及搜索边界，0.9 mm 处 C1 slope jump 约 0.0486，因此只作 mechanism proof-of-concept，暂不 production-lock 参数。

## 2. RAD 为什么必须 REVISE

R4 RAD 的 `R+Q+A4` 对 integrated OPD 拟合非常好：serialized RMS/max 约 0.270% / 0.909%。但 RAD 的 source identity 是冻结的径向相对球镜光焦度函数 `P(r)`，不是“任意一个具有相近积分 OPD 的表面”。

独立 OpticStudio `POWP Data=0` readback：

```text
RMS error = 1.92377 D
max abs error = 6.25755 D
```

在实际 posterior-IOL intercept `r≈0.9923 mm`：

```text
P_target = +1.69608 D
measured relative POWP = -4.56148 D
error = -6.25755 D
```

即关键 0.90–1.10 mm 区出现符号反转。R4 overall 因此必须 REVISE。

## 3. 对 POWP 语义的进一步核对

OpticStudio 的 `POWP` 并不是简单的 `(1/r)dW/dr`。

Ansys OpticStudio User Guide 对 Power Pupil Map / POWP 的定义说明：在指定 pupil reference point 周围追迹一圈 real rays，并从该 ray ring 求局部光焦度；`Data=0` 是 spherical power，另有 tangential/sagittal power 选项。

因此，对轴对称系统：

```text
(1/r)dW/dr
```

最多只是局部 sagittal principal-power 的近轴 proxy，不能单独代表 `POWP Data=0`。

R4.1 第一版 Web 草案曾使用这个 slope/r proxy。离线 CI 及时否定了它：旧 R4 integrated-OPD 解在该 proxy 上已经有约 0.0857 D RMS，新解仅改善到约 0.0803 D，无法解释真实 POWP 的 1.924 / 6.258 D 失败。因此第一版草案被丢弃，没有交给本地 OpticStudio。

## 4. R4.1 的修正近轴 proxy

对于轴对称局部波前，两个近轴 principal-power proxy 为：

```text
sagittal   ~ (1/r) dW/dr
tangential ~ d²W/dr²
```

所以 R4.1 使用：

```text
P_spherical_proxy(r)
    = 0.5 * [ P_sagittal(r) + P_tangential(r) ]
```

作为 **离线 fitter objective**。

其中：

```text
W(r) = 1000 * (n_after - n_before) * [z_EDOF(r) - z_MONO(r)]
```

单位为 µm；`r` 用 mm，因此数值直接对应 D。

对 Binary4 每区 conic + p4 + p6：

```text
dz/dr
```

由现有解析 slope 计算；

```text
d²z/dr² = c / [1-(1+Q)c²r²]^(3/2)
          + 12*A4*r²/Rzone^4
          + 30*A6*r^4/Rzone^6
```

这里 A4/A6 指 Binary4 native normalized coefficients。自动 C0 zone sag offsets 是常数，不影响一阶/二阶导数。

`r=0` 使用 curvature limit。

这个 spherical-power proxy 仍不是对 OpticStudio POWP 的重新实现；真实 `POWP Data=0` 始终保留为独立 serialized/full-ray validation。

## 5. 为什么 R4.1 固定在 R+Q+A4

R4 已经通过严格复杂度阶梯确定 RAD 首次达到原 pilot representation fidelity 的级别是：

```text
R+Q+A4
```

R4.1 的目标是**只修正机制 identity**，不再重新打开模型选择问题。因此：

- 不回退到 R/R+Q 做新的 science selection；
- 不升级 A6；
- 固定 `R+Q+A4`；
- 只对冻结的 `P(r)` 重新拟合。

这样可以避免把“机制目标修正”和“复杂度变化”混在一起。

## 6. 离线 deterministic regression

对 R4 已接受执行得到的旧 RAD `R+Q+A4` 参数，新的 spherical-power proxy 会明确识别出错误：

```text
old R4 spherical-proxy RMS  ≈ 4.49 D
old R4 spherical-proxy max  ≈ 12.61 D
```

用同一个固定 `R+Q+A4` topology 对 spherical-power proxy 重新拟合后：

```text
R4.1 spherical-proxy RMS ≈ 0.080 D
R4.1 spherical-proxy max ≈ 0.351 D
```

这些数值只作为离线回归 reference，用于证明新 objective 确实识别并修复了旧 objective 漏掉的形状问题；**不是新增的科学 acceptance threshold**。

## 7. integrated OPD 在 R4.1 的地位

RAD 的旧 2%/5% integrated-OPD gate 在 R4.1 中不再作为 RAD mechanism acceptance gate。

原因不是放宽标准，而是 R4 Web review 已经用真实 POWP 证明：这个 surrogate 可以在局部球镜光焦度错误甚至符号翻转时仍然轻松通过。继续把它作为 hard gate 会把已被证伪的 surrogate 重新放在 source identity 之上。

因此：

- RAD integrated OPD fit/readback **完整保留**；
- 继续报告 RMS/max/piston/global defocus；
- 明确标记为 historical diagnostic；
- 不参与 R4.1 RAD local pass。

WFS 与 HOA 的原 R4 机制 gate 和 serialized slack 完全不变。

## 8. R4.1 明确不改的内容

R4.1 不改变：

- RAD source `P(r)`；
- RAD boundaries `0/.50/.90/1.10/1.40/2.50/3.00 mm`；
- neutral zone 5/6；
- `Np=0`；
- diffraction order = 0；
- `Na=3`；
- native p2 = 0；
- A6 ceiling；
- RAD 本轮 complexity 固定为 R4 已选 `R+Q+A4`；
- +20.000 D representative carrier；
- WFS / HOA scientific definitions；
- MFE Grid=1 MTF backend、128 sampling、0–100 cyc/mm / 5 cyc/mm step；
- physical-pupil / retina 主研究定义；
- ±0.125 D historical global-defocus reference；
- serialized-readback 修复：MONO/EDoF 都从 analytical Standard carrier 独立转换。

禁止用 MTF 参与 RAD fit。

## 9. R4.1 local gate

R4.1 在同一新 HEAD 完整重跑 WFS/RAD/HOA：

- WFS：原 R4 implementation，不变；
- HOA：原 R4 implementation，不变；
- RAD：固定 `R+Q+A4`，使用 spherical-power proxy fit；
- 三平台继续做 ray health、global defocus、HOA、MFE Grid=1 MTF；
- RAD 继续做真实 `Px=0.0..1.0 step 0.1` POWP readback。

RAD 不新增绝对 POWP 数值阈值。本地只加入两个与已拒绝 R4 baseline 直接相关的最低限度 identity/regression 条件：

1. 所有 sampled `P_target != 0` 的点，实测 relative POWP 必须与 target 同号；
2. 新 POWP RMS error 和 max error 必须分别低于被 Web 拒绝的 R4 baseline：
   - RMS baseline = 1.92377 D
   - max baseline = 6.25755 D。

这两个条件只保证“旧失败确实被改善且不再符号翻转”；最终 POWP magnitude 是否足以接受，仍由 Web review 决定。

R4.1 local pass：

```text
WFS/HOA existing mechanism gates pass
AND RAD spherical-power fit is valid
AND all ray health pass
AND all |global defocus| <= 0.125 D
AND RAD nonzero-target POWP sign identity passes
AND RAD POWP RMS improves vs rejected R4
AND RAD POWP max improves vs rejected R4
```

即使 `local_pilot_passed=true`：

```text
manual_web_review_required=true
automatic_progression_allowed=false
```

## 10. 阶段边界

R4.1 完成后必须 STOP for Web review。

禁止进入：

- R6/R7；
- 24-carrier expansion；
- 96-config production rerun；
- production expansion；
- 基于 MTF 的 RAD re-optimization。
