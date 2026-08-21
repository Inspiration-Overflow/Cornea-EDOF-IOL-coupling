# TASK-007 — IOL carrier / EDOF residual 科学冻结

> 日期：2026-08-19  
> 状态：**Web 端科学定义冻结；真实 OpticStudio 校准尚未完成；TDD-TEST-999 仍有效**  
> 基线：`MVP_2026_v2`  
> 上游冻结输入：`BASE_LB_PSEUDOPHAKIC`、`BASE_ATC_M3_PSEUDOPHAKIC`、`A0`、`B0.20`、`C0`、`STD_IOL_EYE_2024`

## 1. 本任务现在解决什么

TASK-005D 已完成，A0/B0.20/C0 从此作为只读输入。TASK-007 不再修改角膜，也不提前运行 72 配置。

本阶段只解决两件事：

1. 给 WFS-like / RAD-like / HOA-like 三个平台建立**可复现、可写入 Zemax、可跨实际 IOL power 验证**的 carrier + residual 定义；
2. 在真实 OpticStudio 中完成 18 个 provisional carrier 的 `P_ijk → Q_k(P_ijk)` 求解，并对每个平台 residual 做 low / median / high actual-power 校准。

完成这些之前不得生成正式 carrier/pair lock，不得进入 Run72。

## 2. 规范优先级

如果历史设计文档与当前仓库规范冲突，按以下优先级执行：

1. 当前仓库 `URD-0001 v1.4` / `TDD-0001`；
2. 已锁科学 artifact；
3. `zemax_edof_iol_design_v1_6_standalone.md` 中仍与当前规范一致的机制设计；
4. 外部论文、专利和光学台资料作为 surrogate 的证据与数值种子。

因此，历史 v1.6 中较早的“3 mm 标准校准孔径”描述不再使用。carrier `SA_base`、`Q(P)` 和 residual 的正式标准眼验证统一服从当前 repo：

```text
STD_IOL_EYE_2024
EPD = 6.0 mm
lambda ≈ 546 nm
```

主实验 EPD3/EPD5 仍只用于性能评价。

## 3. 模型身份：机制 surrogate，不是商业产品逆向

WFS/RAD/HOA 是三种**机制 surrogate**。商业产品只作为公开机制锚点，不作为模型 ID，也不声称重建制造处方。

正式模型名称只能使用：

```text
WFS-like
RAD-like
HOA-like
```

或批准的中文等价名称。

本项目首轮 MVP 不引入商业平台之间未知或不完全公开的材料、CT、bending、色散等差异作为额外自变量。

## 4. Controlled carrier scaffold

三平台使用同一个工程载体骨架：

```text
scaffold_id = CONTROLLED_IOL_CARRIER_546_v1
n_IOL = 1.460
n_surrounding = 1.336
CT = 1.000 mm
optical diameter = 6.000 mm
initial bending = symmetric biconvex
Q control surface = anterior
```

这是**本项目工程控制条件**，不是任一商业 IOL 的材料或制造参数。

这样做的目的不是把三个平台做成同一个 IOL，而是避免把缺乏完整公开依据的 material/CT/bending 差异混入角膜 × EDOF 机制比较。

三个平台仍保留不同的基础球差身份：

```text
WFS-like SA_base^STD = -0.20 ± 0.01 µm
RAD-like SA_base^STD = -0.27 ± 0.01 µm
HOA-like SA_base^STD =  0.00 ± 0.01 µm
```

并且每个 `Base × Cornea × Platform` 都必须独立求：

```text
P_ijk
Q_k(P_ijk)
```

所以三个平台并没有被压缩成共同的球差中性 carrier。

## 5. physical carrier 求解仍按既有规范

对 18 个：

```text
2 bases × 3 corneas × 3 platforms
```

逐一执行：

1. 关闭 EDOF residual；
2. 暂设 `Q=0`；
3. 在实际 Base + Cornea 中调基础曲率，使 MONO 最佳远焦落到固定视网膜，得到 `P_ijk`；
4. 保持该 power/geometry/material，转入 `STD_IOL_EYE_2024`；
5. 在 EPD6、约 546 nm 下求前表面 `Q_k(P_ijk)`，相对同 power/geometry 的 `ZERO_HOA_PARAXIAL_REFERENCE` 达到平台 `SA_base` 目标；
6. 回实际眼检查 MONO 远焦；若普通球镜焦移达到约 0.125 D 的工程修正量级，允许 1–2 次简单 P–Q 回查；
7. 只在通过实机验证后形成 provisional carrier record。

不得把 +20 D 或其他单一 power 的 Q 机械复制给六个实际 carrier。

## 6. residual 共用契约

三平台 residual 都遵守：

```text
payload = residual only
physical optic radius = 3.000 mm
seed radial step = 0.005 mm
formal standard-eye validation = EPD6 / ~546 nm
MONO = frozen carrier
EDOF = same frozen carrier + frozen residual
```

同一 matched pair 的以下字段必须完全相同：

- power；
- anterior/posterior radii；
- Q；
- CT；
- material/index；
- optical diameter；
- IOL position；
- tilt/decentration。

唯一允许差异是 residual。

## 7. WFS-like residual

### 7.1 外部机制锚点

US 9,968,440 B2 的公开实施例给出一个非衍射 phase-shift surface residual。Table 1 的代表性参数为：

```text
r1 = 0.55 mm
r2 = 0.65 mm
r3 = 0.87 mm
r4 = 1.05 mm
r5 = 1.11 mm
r6 = 3.00 mm
Delta1 = -1.02 µm
Delta2 = +0.59 µm
```

公开专利把完整表面写为 base profile + phase-shift component。本项目只继承**phase-shift residual**；专利中的 base asphere 不复制，因为基础球差已经由本项目自己的 `Q_WFS(P)` 控制。

### 7.2 MVP residual seed

冻结 residual-only sag：

\[
z_{WFS,raw}(r)=
\begin{cases}
0,&0\le r<r_1\\
\dfrac{r-r_1}{r_2-r_1}\Delta_1,&r_1\le r<r_2\\
\Delta_1,&r_2\le r<r_3\\
\Delta_1+\dfrac{r-r_3}{r_4-r_3}\Delta_2,&r_3\le r<r_4\\
\Delta_1+\Delta_2,&r\ge r_4.
\end{cases}
\]

在本项目只有一个 controlled base profile 的条件下，外侧 plateau 连续到 3 mm optic radius；`r5` 保留为专利实施例 provenance，不再引入第二套商业 base asphere。

第一阶 OPD seed：

\[
W_{WFS,raw}(r)=(n_{IOL}-n_{medium})z_{WFS,raw}(r).
\]

最终 physical sag 仍必须经过真实 OpticStudio ray-trace/readback 校准，不能把这一一阶换算当成正式光学证据。

## 8. RAD-like residual

### 8.1 外部机制锚点

US 2022/0287825 A1 的 Table 3 给出一个连续 cosine radial-power 实施例：

| Zone | r_i–r_e (mm) | S (D) | A (D) | CosOrder |
| --- | --- | ---: | ---: | ---: |
| 1 | 0.00–0.50 | -0.25 | 0.00 | 1 |
| 2 | 0.50–0.90 | -0.25 | -3.25 | 1 |
| 3 | 0.90–1.10 | +3.00 | +3.25 | 1 |
| 4 | 1.10–1.40 | -0.25 | -0.25 | 1 |
| 5 | 1.40–2.50 | 0.00 | 0.00 | 1 |

专利定义：

\[
P_k(r)=S_k-A_k(-1)^{m_k}
\left[-\frac12+\frac12\cos^{m_k}
\left(\pi\frac{r^2-r_{i,k}^2}{r_{e,k}^2-r_{i,k}^2}\right)\right].
\]

当前冻结 `m_k=1`。由此各区端点连续：`P(r_i)=S`，`P(r_e)=S-A`。

### 8.2 MVP residual seed

先把相对 radial power 积分成 wavefront OPD：

\[
\frac{dW}{dr}=P(r)r.
\]

在 `P[D]`、`r[mm]` 下，积分值数值上直接得到 `W[µm]`。

然后执行统一低阶去除，再按后表面传播方向的折射率跃迁生成 posterior residual sag seed。

2.50–3.00 mm 设相对 power 为 0，仅用于把 physical residual 文件覆盖到完整 6 mm optic。

## 9. HOA-like residual

### 9.1 机制依据

Bénard、López-Gil、Legras 的自适应光学研究表明，4 阶与 6 阶球差异号组合可以比同号组合获得更大的焦深扩展。

独立光学台对一类 HOA-based EDOF IOL 的中央波前测得约：

```text
Z4^0 ≈ -0.49 lambda
Z6^0 ≈ +0.46 lambda
```

在 546 nm 下换算为：

```text
C4 seed ≈ -0.26754 µm
C6 seed ≈ +0.25116 µm
```

同一光学台还观察到更高阶项；本 MVP **有意只保留 4/6 阶异号机制**，不追加 Z8/Z10，以避免把一个机制 surrogate 变成商业面型逆向。

### 9.2 冻结 OPD seed

中央功能区采用 OSA/ANSI 归一化径向项：

\[
Z_4^0(\rho)=\sqrt5(6\rho^4-6\rho^2+1)
\]

\[
Z_6^0(\rho)=\sqrt7(20\rho^6-30\rho^4+12\rho^2-1).
\]

定义：

```text
Zernike seed diameter = 2.00 mm
core radius = 0.90 mm
transition = 0.90–1.10 mm
outer residual function = 0 after 1.10 mm, before common low-order normalization
```

raw OPD：

\[
W_{HOA,raw}(r)=A(r)
\left[C_4 Z_4^0(\rho)+C_6 Z_6^0(\rho)\right]
\]

其中 `rho=min(r/1.00 mm, 1)`，`A(r)` 为五次 smoothstep 窗：

\[
S(t)=10t^3-15t^4+6t^5,
\]

\[
A(r)=
\begin{cases}
1,&r\le0.90\\
1-S((r-0.90)/0.20),&0.90<r<1.10\\
0,&r\ge1.10.
\end{cases}
\]

这取代历史 v1.6 中较抽象的 `a r^6+b r^4` seed。原因是直接 Z4/Z6 表达更接近本研究实际要隔离的 HOA 机制，也避免把 Zernike 系数反解成高次多项式后产生很大的低阶抵消项。

## 10. residual 的低阶规范化

历史设计已经要求 residual 不能把明显普通 piston/global defocus 偷带进 matched pair。现在把数值步骤冻结为：

1. raw seed 先生成在完整 0–3.0 mm physical optic；
2. 以 nominal standard-eye IOL footprint：

```text
D = 5.15 mm
R = 2.575 mm
```

作为**纯数学 seed normalization domain**；
3. 对径向 OPD 做面积权重最小二乘：

\[
W(r)\approx p+\frac12Fr^2,
\]

权重 `w(r)=r`；
4. 从完整 0–3 mm OPD 中减去拟合得到的 `p + 0.5 F r²`；
5. 再用前/后表面相应折射率跃迁把 normalized OPD 转为 physical sag 起始值。

这里的 5.15 mm 是 deterministic seed coordinate，不替代真实 `STD_IOL_EYE_2024` ray-trace。正式验收仍在 EPD6 标准眼中读取完整系统 wavefront。

## 11. 冻结 residual 低阶验收带

新 policy：

```text
policy_id = RESIDUAL_VALIDATION_546_v1
|measured piston| <= 0.010 µm
|measured global defocus| <= 0.125 D
```

两者都是 **MVP 工程验收带，不是临床阈值**。

特别注意：

```text
measured global defocus of residual payload
!=
DeltaF_residual
```

`DeltaF_residual = F_best(EDOF)-F_best(MONO)` 是完整非线性光学系统加入 residual 后的科学结果，必须原样记录，不要求小于 0.125 D。0.125 D 只限制 residual payload 的显式低阶 ordinary-defocus 污染。

## 12. same residual across power：MVP 假设与实际 gate

首轮 MVP 每个平台只冻结一个 residual，覆盖其 6 个实际 carrier powers，不建立 `Residual(r;P)` 家族。

但在正式使用前，每个平台必须从 6 个实际 carrier 中确定：

```text
low power
median-nearest power
high power
```

三个不同 carrier，并逐一在真实 OpticStudio 中验证。

每个 calibration record 至少保存：

- exact carrier ID / actual power；
- residual ID / SHA-256；
- standard-eye/actual-eye calibration identity；
- measured piston / global defocus；
- distance peak shift `DeltaF_residual`；
- whole-eye / standard-eye wavefront readback；
- mechanism-specific optical evidence；
- PASS/FAIL；
- evidence file SHA-256。

如果 low/median/high 任一点机制失真、追迹异常或低阶污染超 policy，则该平台 residual 不得 formal lock，应回 Web 端修订；不得由本地脚本自行改科学定义。

## 13. mechanism-specific 最小实机 oracle

不增加复杂自动优化器，只要求少量可解释证据。

### WFS-like

- central phase-shift structure 写入和 readback 正确；
- 无衍射级次建模；
- through-focus 结果相对 matched MONO 出现连续焦深扩展趋势；
- 没有明显非物理 ray failure/vignetting。

### RAD-like

- ray-traced radial relative-power profile 保持连续 distance→near→distance 调制；
- 约 0.9 mm 附近存在设计的较高相对 power；
- through-focus 结果相对 matched MONO 呈连续扩展而不是离散衍射级次。

### HOA-like

- 中央 wavefront 保持 4/6 阶异号主导；
- 约 1.1 mm 外 EDOF 功能结构平滑退出，外围由 carrier 主导；
- through-focus 结果相对 matched MONO 出现延焦趋势。

这些是 mechanism-preservation oracle，不把商业 IOL 的精确 MTF、焦深或 Zernike 值设为硬复刻目标。

## 14. TDD-999 当前状态

### 已解决

- 三平台 residual 机制与数值 seed 已 versioned；
- controlled carrier scaffold 已冻结；
- residual 低阶数学去除方式已冻结；
- piston/global-defocus numerical policy 已冻结；
- low/median/high actual-power 选择算法已存在于 carrier framework。

### 仍未解决，因此 TDD-999 仍为 STOP

- 三个 physical residual payload 尚未在真实 OpticStudio 中生成/readback；
- 18 个 provisional `P_ijk / Q_k(P_ijk)` 尚未实机求解；
- 三平台 low/median/high actual-power calibration evidence 尚未完成；
- formal residual locks / carrier locks 尚不存在。

所以现在**不能**进入 TASK-008 正式 manifest，也不能 Run72。

## 15. STOP 条件

出现以下任一情况停止并回 Web 端，不在本地临时改模型：

- 需要改 A0/B0.20/C0 才能让 IOL 好看；
- 需要把一个 Q 复制到所有 power；
- EDOF 与 MONO 需要不同 carrier power/Q 才能工作；
- residual 低阶污染超 `RESIDUAL_VALIDATION_546_v1`；
- WFS/RAD/HOA 机制表型在 low/median/high 任一点消失；
- physical sag 导致明显非物理面型、ray failure 或意外 vignette；
- 为通过结果需要事后改 SA target；
- 需要加入商业专有面型参数才能“匹配产品”；
- 需要运行 72 configs 才能判断 residual 是否可用。

## 16. 代码映射

```text
src/whole_eye_mvp/carrier_scaffold.py
    CONTROLLED_IOL_CARRIER_546_v1

src/whole_eye_mvp/residual_profiles.py
    WFS patent seed
    RAD cosine-power seed
    HOA Z4/Z6 seed
    area-weighted piston/global-defocus fit

src/whole_eye_mvp/residual_payload.py
    full-optic radial candidate
    low-order normalization
    OPD -> surface-sag engineering start payload

src/whole_eye_mvp/residual_policy.py
    RESIDUAL_VALIDATION_546_v1

src/whole_eye_mvp/carriers.py
    SA targets
    18-carrier key space
    low/median/high selector
    real payload/evidence/hash fail-closed validation
```

## 17. 主要依据

### WFS-like

- Hong X, Milanovic Z, Wei X. *Ophthalmic lens having an extended depth of focus.* US Patent 9,968,440 B2, 2018. 本项目使用其公开 phase-shift residual 实施例作为机制 seed，不复制商业 base asphere。

### RAD-like

- Faria Ribeiro M, Gounou F, Cánovas Vidal C, Alarcon Heredia A. *Refractive extended depth of focus intraocular lens, and methods of use and manufacture.* US 2022/0287825 A1 及其专利族。Table 3 用作 cosine radial-power seed。

### HOA-like

- Bénard Y, López-Gil N, Legras R. *Subjective depth of field in presence of 4th-order and 6th-order Zernike spherical aberration using adaptive optics technology.* J Cataract Refract Surg. 2010;36:2129–2138.
- Bénard Y, López-Gil N, Legras R. *Optimizing the subjective depth-of-focus with combinations of fourth- and sixth-order spherical aberration.* Vision Res. 2011;51:2471–2477.
- Schmid R, Borkenstein AF. *Optical Bench Analysis of 2 Depth of Focus Intraocular Lenses.* Biomed Hub. 2021;6:77–85. 中央 4/6 阶 wavefront 数值仅作为简化 HOA surrogate seed。

## 18. 当前结论

TASK-007 的 Web 端科学定义已经从“缺 residual payload 设计”推进到：

```text
mechanism definitions = frozen
carrier scaffold = frozen
seed math = implemented
low-order policy = frozen
real OpticStudio calibration = pending
formal carrier/residual lock = forbidden until TDD-999 clears
```

下一步不是继续扩大文献范围，也不是运行 72 配置，而是先完成本分支离线测试，然后给 ZCode 一个严格受限的 TASK-007 实机校准任务。
