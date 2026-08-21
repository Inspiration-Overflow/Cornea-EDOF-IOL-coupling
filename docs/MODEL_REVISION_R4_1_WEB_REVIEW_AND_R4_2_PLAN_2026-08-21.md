# Model Revision R4.1 Web review 与 R4.2 RAD 低阶约束修订

> 日期：2026-08-21  
> R4.1 execution commit：`f0332eea21921ba4aa7ce43ae0fa5e290bb55ba2`  
> R4.1 Web 判定：**REVISE**  
> 下一允许阶段：**仅 R4.2 RAD low-order-constrained pilot**

## 1. R4.1 的实际结论

R4.1 的主要修订目标已经成功：RAD 不再以 integrated OPD 作为机制主目标，而改为局部 spherical-power 机制，并由真实 OpticStudio `POWP Data=0` 独立验证。

本地 R4.1 结果：

- WFS：原 R4 行为保持通过；
- HOA：原 R4 行为保持通过；
- RAD complexity：仍为冻结的 `R+Q+A4`；
- RAD POWP sign identity：通过；
- RAD POWP RMS：由被拒绝 R4 的 `1.9237699595 D` 改善到约 `0.5532 D`；
- RAD POWP max absolute error：由 `6.2575543068 D` 改善到约 `1.3760 D`；
- 原 R4 在约 `r=0.992 mm` 的正目标/负实测符号翻转已消失。

因此，R4.1 证明 spherical-power 目标修订方向正确，不能回退到旧 integrated-OPD objective。

但 R4.1 local pilot 仍为 FAIL，唯一失败项是 RAD global defocus：

- WFS：约 `+0.0040 D`；
- HOA：约 `-0.0009 D`；
- RAD：约 `+0.2417 D`；
- frozen hard reference：`|global defocus| <= 0.125 D`。

所以 R4.1 overall = **REVISE**，不能进入 R6/R7。

## 2. 失败的物理含义

R4.1 的局部 spherical-power optimum 本身不是一个可直接冻结的生产 surrogate，因为它在改善局部 power shape 的同时，引入了额外低阶功率偏置。

关键是：冻结 RAD source 自己并不是零 defocus。

用当前 R4 readback 完全相同的低阶定义：

- radial range：`0–2.575 mm`；
- sampling：`0.025 mm`；
- area-weighted fit：`W(r) = piston + 0.5 * F * r^2`；

对冻结 source `rad_raw_opd_um(r)` 直接拟合得到：

`F_source = +0.10449993581993025 D`

这与旧 R4 的 serialized RAD global defocus `+0.104569 D` 几乎完全一致，也说明既有 `0.125 D` hard reference 与 source mechanism 是相容的。

R4.1 的 `+0.2417 D` 因而不是 source 本身要求，而是 unconstrained spherical-power fit 新引入的约 `+0.137 D` 低阶偏置。

## 3. R4.2 修订原则

R4.2 只修上述单点问题。

不允许：

- 放宽 `0.125 D` global-defocus reference；
- 把目标 defocus 改为 0；
- 回退到 integrated OPD 主目标；
- 使用 MTF 调参；
- 改 RAD source `P(r)`；
- 改 zone boundaries；
- 解冻 p2；
- 给 RAD 增加 A6；
- 改 +20 D representative carrier；
- 改 physical-pupil / retina 定义。

R4.2 仍固定：

- RAD complexity = `R+Q+A4`；
- zone boundaries = `0/.50/.90/1.10/1.40/2.50/3.00 mm`；
- zones 5/6 neutral；
- `Np=0`；
- diffraction order = 0；
- p2 = 0；
- A6 = 0；
- MTF audit = MFE `MTFA/MTFS/MTFT`, Grid=1, sampling=128, 0–100 cyc/mm step 5；
- Standard-to-Binary4 serialized-readback fix 不变。

## 4. R4.2 fitter

Primary fit quantity 仍是 R4.1 已纠正的 source-locked local spherical power：

`P_spherical_proxy = 0.5 * (P_tangential + P_sagittal)`

其中 paraxial：

- `P_tangential ~ d2W/dr2`；
- `P_sagittal ~ (1/r)dW/dr`。

真实 OpticStudio spherical `POWP Data=0` 仍是最终独立验证；proxy 不是 POWP 的替代实现。

R4.2 新增唯一 secondary constraint：

`F_Binary4 -> F_source`

其中：

`F_source = +0.10449993581993025 D`

该 constraint 直接使用冻结 source 和已有 R4 low-order definition 计算，不是新引入的科学目标。

数值上将 defocus residual 按 source 在既有 hard reference 内的 headroom 归一化：

`headroom = 0.125 - |F_source|`

因此没有增加新的 defocus tolerance。

## 5. integrated OPD 的角色不变

R4.2 仍保留完整 integrated-OPD / SSAG 诊断：

- pure historical fit diagnostic；
- serialized mechanism diagnostic；
- piston；
- RMS / max；
- old engineering-pass flag。

但这些指标不重新成为 RAD mechanism gate。

R4 已经实证 integrated OPD 可以非常漂亮地通过，而真实 spherical POWP 同时严重失败，因此不能再次让它主导 RAD 拟合。

## 6. R4.2 本地 gate

R4.2 local PASS 需要：

1. WFS / HOA 原有 R4 engineering + serialized gates 继续通过；
2. RAD fixed `R+Q+A4` fit 数学有效；
3. 所有 ray-health 通过；
4. 三平台 `|global defocus| <= 0.125 D`；
5. RAD 所有 sampled non-zero target 保持 POWP 同号；
6. RAD POWP RMS 仍优于被拒绝 R4 baseline `1.9237699595 D`；
7. RAD POWP max 仍优于被拒绝 R4 baseline `6.2575543068 D`。

R4.2 **不要求** POWP RMS/max 必须继续优于 R4.1 的 `0.5532/1.3760 D`，因为 R4.2 的任务就是在局部 power fidelity 与正确低阶基线之间做受控 trade-off。

R4.1 与 R4.2 的 POWP 数值变化必须完整记录，交给 Web manual review 判断，但不作为自动 hard gate。

## 7. 预期

离线数值预检显示，加入 source-defocus consistency 后：

- complexity 无需超过 `R+Q+A4`；
- global defocus 可回到约 `+0.105 D`；
- spherical-power proxy RMS 预计由约 `0.080 D` 增至约 `0.12–0.13 D`。

这是预检，不是 local OpticStudio evidence，也不是新的科学 acceptance threshold。

真实结果必须由 R4.2 local pilot 的 serialized Binary4、POWP、ray health、low-order、HOA、MTF evidence 决定。

## 8. 阶段边界

R4.1：**REVISE**。

下一步仅允许：

`MODEL-REVISION-R4.2-RAD-LOW-ORDER-CONSTRAINED-PILOT`

无论 R4.2 local PASS 或 FAIL，都必须 STOP FOR WEB REVIEW。

在 Web R4.2 ACCEPT 之前，仍然禁止：

- R6/R7；
- 24-carrier expansion；
- 96-config production rerun；
- production expansion；
- merge PR #27。
