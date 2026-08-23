# Model Revision R4.2 Web review 与 R5 机制冻结

> 日期：2026-08-21  
> R4.2 execution commit：`e242cc88a6e59cce85f2a990e44a56b070b11149`  
> R4.2 Web 判定：**ACCEPT**  
> R4 总体判定：**ACCEPT FOR MVP SURROGATE STUDY**  
> R5 状态：**FROZEN**  
> 下一允许阶段：**R6/R7 — 24-carrier rebuild / mechanism validation**

## 1. 审核依据与边界

本审核基于本地 R4.2 完整 OpticStudio pilot 的回传 evidence 摘要。canonical 本地文件为：

`project_mvp_2026_v2_zmx/diagnostics/model_revision/r4_2_pilot/MODEL_REVISION_R4_2_PILOT_EVIDENCE.json`

本地报告确认：

- HEAD = `e242cc88a6e59cce85f2a990e44a56b070b11149`；
- 工作区 clean；
- 252 unit tests passed；
- `local_pilot_passed=true`；
- `manual_web_review_required=true`；
- `automatic_progression_allowed=false`；
- WFS / RAD / HOA 三个平台全部 ray-health 通过；
- 三个平台 global defocus 均满足既有 `|F| <= 0.125 D` gate。

R5 冻结并不声称重建商业产品制造处方。三个 IOL 继续只解释为 WFS-like、RAD-like、HOA-like **机制性 surrogate**。

## 2. R4.2 Web gate 逐项判定

| Gate | 判定 | 说明 |
| --- | --- | --- |
| A mechanism fidelity | PASS | WFS/HOA 延续 R4 已通过机制；RAD 真实 POWP 符号结构恢复且较被拒 R4 大幅改善 |
| B geometry quality | PASS | C0 全部为零；RAD min conic radicand 0.941；未发现非法几何 |
| C manufacturing plausibility | REVIEW | RAD/HOA 部分边界 C1 jump 较大；HOA 参数仍较激进。本项目不据此做制造可行性结论 |
| D standard-eye validation | PASS | WFS +0.0040 D、RAD +0.10453 D、HOA -0.00095 D，均在 ±0.125 D |
| E optical sanity | PASS | MFE Grid=1 MTF、C4/C6/HOA、best focus、ray health 均完成；MTF 未参与拟合 |
| F manual reviewer | ACCEPT | 作为 MVP 机制 surrogate 接受，进入 power-range validation |

`manufacturing plausibility = REVIEW` 不阻止本研究的计算 surrogate 进入 R6/R7；但它永久阻止把 R5 参数表述为可制造商业 IOL 处方。

## 3. RAD 的最终人工裁决

R4 被拒的主要原因不是 MTF，而是真实 OpticStudio `POWP Data=0` 与 source mechanism 不一致：

- rejected R4 POWP RMS = `1.9237699595 D`；
- rejected R4 max = `6.2575543068 D`；
- 在约 `r=0.992 mm` 出现 target positive / measured negative 的符号翻转。

R4.1 修复 spherical-power objective 后：

- sign identity PASS；
- POWP RMS ≈ `0.5532 D`；
- max ≈ `1.3760 D`；
- 但 global defocus ≈ `+0.2417 D`，超过既有 0.125 D gate。

R4.2 增加 frozen-source low-order constraint 后：

- source global defocus = `+0.1044999358 D`；
- modeled / serialized global defocus = `+0.10453379 D`；
- 差值仅约 `3.39e-05 D`；
- POWP RMS = `0.58637 D`；
- max = `1.51227 D`；
- non-zero target sampled points sign identity 全部 PASS。

R4.2 相比 R4.1 的 POWP RMS 增加约 0.033 D、max 增加约 0.136 D，是可接受的受控 trade-off：它换回了正确的 source low-order baseline，而不是通过放宽 defocus gate 获得通过。

### 3.1 对残余 POWP 误差的解释限制

R5 **不把** `0.58637 D RMS / 1.51227 D max` 宣称为专利 RAD profile 的逐点高精度复刻。尤其约 `r≈0.495 mm` 的 transition-near sample 仍存在约 `-1.51 D` error；0.74–0.99 mm 内部正 power 也仍低于 target。

但对 MVP 而言，以下条件已同时满足：

1. source 的径向 power 机制身份与正负结构保持；
2. 被拒 R4 的灾难性 sign reversal 已消失；
3. POWP RMS/max 均显著优于被拒 R4；
4. source 自身 low-order component 被正确保留；
5. 未通过 MTF 反向调参；
6. 未增加新的高阶自由度或移动 zone boundaries。

因此 RAD 在 R5 中冻结为**机制型近似 surrogate**。R6/R7 的职责是检查该 surrogate 是否可跨实际 carrier power 范围稳定移植，而不是继续把 +20 D pilot 调到局部最优。

## 4. WFS 最终 R5 状态

- surface：anterior IOL；
- zones：`0/.55/.65/.87/1.05/3.00 mm`；
- complexity：`R`；
- `p2=0`、`A4=0`、`A6=0`、`Np=0`、all diffraction order=0；
- +20 D serialized mechanism RMS fraction ≈ `0.004894`；
- global defocus ≈ `+0.003996 D`；
- geometry / ray / optical sanity：PASS。

WFS = **ACCEPT**。

## 5. HOA 最终 R5 状态

- surface：anterior IOL；
- zones：`0/.90/1.10/3.00 mm`；
- complexity：`R+Q+A4+A6`；
- 1.10–3.00 mm neutral；
- +20 D serialized RMS fraction ≈ `0.010838`；
- global defocus ≈ `-0.00095 D`；
- Binary4 vs GridSag optical sanity 保持接近；
- ray health PASS。

仍保留以下制造诊断警示：

- zone 1 / zone 2 参数较激进；
- zone 2 representative Q 到达既有搜索上界 `+50`；
- `r=0.90 mm` C1 slope jump 约 `0.0486`；
- representative minimum conic radicand 约 `0.275`。

这些警示在 MVP 中记为 `manufacturing plausibility = REVIEW`，**不再触发机制重新优化**。不得据此添加 A8+ 或改变 zone topology。

HOA = **ACCEPT AS COMPUTATIONAL SURROGATE / MANUFACTURING REVIEW**。

## 6. R5 Binary4 结构永久冻结

所有后续阶段继续：

```text
Np = 0
all diffraction order = 0
Na = 3
native p2 = 0
```

最大逻辑自由度仍只有：

```text
R, Q, A4, A6
```

禁止：

- native p2 作为 defocus 调节器；
- A8+；
- diffraction phase；
- movable zone boundaries；
- MTF-driven residual refit。

最终复杂度：

```text
WFS = R
RAD = R+Q+A4
HOA = R+Q+A4+A6
```

## 7. R5 低阶 gate 最终解释

R0 的 historical low-order 项在 R5 做如下收口：

### global defocus

继续作为 hard mechanism/reference gate：

```text
|global defocus| <= 0.125 D
```

R5 不升级为更严格的 0.05 D scientific threshold。

### residual piston

从 R5 起明确为 **diagnostic only**，不再作为 Binary4 hard gate。

原因是 Binary4 zone-1 vertex sag 与自动 C0 offsets 固定了面形的绝对 sag origin；本项目没有独立的 surface-translation piston 自由度。真正受控的轴向位置、IOL CT、ELP、retina position 均由几何合同单独锁定。

不得为了让报告中的 fitted piston 接近零而平移 IOL 或加入 p2。

## 8. R5 power-independent normalized residual 假设

+20 D pilot 给出的**绝对 zone radius**不能机械复制到所有 IOL powers。

R6 首先测试一个更物理且可审计的 power-independent residual 参数化：

```text
c_base(P) = 1 / R_base(P)

c_zone(P) = c_base(P) + Δc_zone_R5
Q_zone(P) = Q_base_surface(P) + ΔQ_zone_R5
alpha4_zone(P) = alpha4_zone_R5
alpha6_zone(P) = alpha6_zone_R5
```

其中：

- `Δc_zone_R5` 是 +20 D pilot 的 zone curvature 相对 carrier base curvature 的差；
- `ΔQ_zone_R5` 是 zone conic 相对其承载 surface base conic 的差；
- Binary4 native `alpha4/alpha6` 因各 zone normalization radius 已冻结，可先直接沿用；
- neutral zones 的所有 delta 与 alpha 永远为 0。

这一规则只是 **R6/R7 首选移植假设**，不是未经验证的 production truth。

若不同 power 的真实 mechanism readback 明显失真，R7 才允许对该 power 做 mechanism-only refit；不能用最终全眼 MTF 做 refit objective。

## 9. R6/R7 的允许范围

R5 冻结后，下一批本地 handoff 可以一次完成 R6/R7：

1. 重建 `2 Base × 4 Cornea × 3 Platform = 24` physical carriers；
2. 对每个 carrier 先在实际眼求 Q=0 所需 power；
3. 回到 `STD_IOL_EYE_2024` 按该 power 独立求平台 Q；
4. 必要时最多做既有 1–2 次 P/Q engineering recheck，且 power 一变必须重新求 Q；
5. 生成严格匹配的 Binary4 MONO / EDoF；
6. 首先应用 R5 normalized residual；
7. 检查 WFS/HOA mechanism、RAD real POWP、global defocus、ray health、C0/C1/min-radicand；
8. 按 low / median / high carrier power 和全 24 carrier summary 判断 normalized residual 是否足够稳定；
9. 如果需要 power-specific refit，必须返回 Web review 后再执行，不得本地自动改参数。

## 10. R5 退出状态

```text
R2/R3 = ACCEPT
R4 WFS = ACCEPT
R4/R4.2 RAD = ACCEPT AS MVP MECHANISM SURROGATE
R4 HOA = ACCEPT AS COMPUTATIONAL SURROGATE / MANUFACTURING REVIEW
R4 overall = ACCEPT
R5 = FROZEN
R6/R7 = AUTHORIZED NEXT
R8 = NOT YET AUTHORIZED
PR merge = NOT YET AUTHORIZED
```

R8 的 96-config production rerun 只有在 R6/R7 Web review 通过后才允许开始。
