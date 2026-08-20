# 论文草稿模块：Structured Abstract 与 Methods

> 状态：manuscript draft；不建立新的 scientific lock。  
> 来源：`URD-0001 v1.6`、冻结 TASK-008/009/011 identity、`TASK012_RUN72_ANALYSIS_PLAN_2026-08-19` 与正式 TASK-012 evidence。  
> 所有模型和分析定义以这些冻结文档为准。

## 拟题

**角膜屈光术后代表性光学原型与非衍射延伸焦深人工晶状体机制的耦合：基于双模型眼、双瞳孔与匹配单焦对照的计算光学研究**

英文工作标题：

**Coupling Between Representative Post-Refractive Corneal Optical Phenotypes and Non-Diffractive Extended-Depth-of-Focus IOL Mechanisms: A Computational Optical Study Across Two Model Eyes and Two Pupil Sizes**

---

## Structured Abstract

### Purpose

评估代表性角膜屈光术后光学原型与不同非衍射延伸焦深（EDoF）人工晶状体机制之间是否存在非简单加和的耦合，并描述这种耦合如何随瞳孔和基础模型眼改变焦深、固定焦面成像质量、贯焦质量及全眼高阶像差。

### Methods

建立两个轴上、共轴、单色的人工晶状体模型眼：Liou–Brennan 型 `LB_AL2395`（眼轴23.950 mm）和 Atchison 近视型 `ATC_M3_AL24477`（代表约−3 D，眼轴24.477 mm）。设置三个冻结角膜原型：A0（−3.00 D近视术后、正球差增加型准单焦角膜）、B0.20（连续非球面角膜 EDoF 原型）和 C0（中央3.0 mm近用区、处方附加+1.75 D的径向多焦角膜）。三类 IOL 机制 surrogate 分别为波前塑形型（WFS-like）、连续径向屈光力调制型（RAD-like）和中央高阶球差调制型（HOA-like）。

每个 Base×Cornea×Platform 建立独立 physical carrier；EDoF 与 matched MONO 使用完全相同的基础光焦度、曲率、conic、厚度、材料和位置，唯一设计差异为冻结 residual。正式矩阵包括18个 physical carriers、36个 matched MONO–EDoF pairs 和72个配置，分别在3和5 mm entrance pupil下计算。

生产 MTF 通过 Zemax OpticStudio MFE `MTFA Grid=1` 获取，使用每个 matched pair 的 residual-free MONO EFFL 建立共同0–60 cycles/degree角频率尺度。贯焦范围固定为+0.50至−3.00 D，步长0.25 D，共15个平面。主要 paired outcomes 均定义为 `EDOF−MONO`，包括 DOF50 width、0 D MTFa、完整贯焦窗口平均 MTFa、窗口内 distance-peak MTFa以及 C40、C60和 HOA RMS。分析为预先冻结的确定性 factorial contrast 与 difference-in-differences，不把36个 pair视为随机临床样本进行传统显著性检验。DOF50 和 distance-peak censoring 均显式传播。

### Results

72/72配置完成且无失败，共获得1080个贯焦采样点。36个 matched pair 中，30个（83.3%）的 `ΔDOF50` 为正、6个为负；31个 DOF50 effect 为精确值，5个为 lower bound。与此相对，`ΔMTFa@0D` 和完整窗口 `ΔTF MTFa mean` 在36/36 pair中均为负，提示延焦主要通过焦轴方向上的光学质量再分配实现。

B0×WFS-like 显示明显的小瞳孔特异耦合：B0相对A0的 WFS-vs-RAD DOF50 difference-in-differences 在两种基础眼的3 mm瞳孔均为正（≥+0.157和≥+0.195 D），但在5 mm瞳孔反转为−0.210和−0.097 D。C0×RAD-like 的相对 DOF coupling 在两种基础眼和两种瞳孔方向一致，并在5 mm瞳孔更明显，但伴随更大的0 D MTFa损失。HOA-like 在3 mm瞳孔产生最大的 DOF 扩展（多数组合约+0.63至+0.73 D），同时表现出最大的固定焦面/贯焦 MTFa下降和最强的瞳孔及基础眼依赖。

### Conclusions

角膜屈光术后光学结构与非衍射 EDoF IOL 机制之间存在条件依赖的完整眼耦合，而非简单可加效应。B0×WFS-like 主要表现为小瞳孔特异的相对延焦耦合，C0×RAD-like 表现为较稳定但有固定焦面质量代价的 DOF-oriented coupling，HOA-like 则表现为最强但最不稳定的质量再分配。结果支持以角膜光学表型、瞳孔和 IOL 延焦机制共同分层的后续实验与临床研究，但不支持将机制 surrogate 直接转化为商业 IOL 排名或患者级推荐。

---

# Methods

## 1. Study design

本研究为确定性计算光学研究，目标是隔离并比较三个代表性术后角膜光学原型与三类非衍射 EDoF IOL 机制的耦合。所有主分析均在单色555 nm、轴上0°视场、角膜/瞳孔/IOL共轴的条件下进行。MVP 不加入角膜治疗区偏心、IOL tilt/decentration 或微单视附加离焦，以避免将定位误差与设计机制混入同一主矩阵。

研究采用 matched-pair 设计：对于每一个 Base×Cornea×Platform×Pupil 条件，EDoF 配置与 MONO 对照共享完全相同的 physical carrier，唯一设计差异是相应平台的冻结 EDoF residual。由此，所有 `EDOF−MONO` 差异可解释为 residual 加入后的完整眼光学效应，而不是基础 IOL power、conic、位置或材料变化。

## 2. Model eyes

使用两个冻结基础模型眼。

### 2.1 LB_AL2395

`LB_AL2395` 基于 Liou–Brennan 模型眼，眼轴长度固定为23.950 mm，用于代表典型正视眼结构。

### 2.2 ATC_M3_AL24477

`ATC_M3_AL24477` 基于 Atchison Model 1 的近视眼框架，选择代表约−3 D近视的典型样本，眼轴长度固定为24.477 mm。

两个基础眼共同使用后角膜至 STOP 3.150 mm、后角膜至 IOL 前表面参考位置4.500 mm，房水/玻璃体工程折射率约1.336。IMAGE 顶点由各自眼轴固定，贯焦分析不移动视网膜。

## 3. Post-refractive corneal prototypes

三个角膜原型在主矩阵前冻结，且不允许依据 IOL 结果回调参数。

### 3.1 A0: aberration-altered post-myopic quasi-monofocal cornea

A0 表示传统近视角膜屈光术后准单焦原型。冻结 treatment 为−3.00 D，有效光学区约5.0 mm，并以6 mm口径下约 `+0.13 μm` 的 `ΔC4^0` 表示典型正球差增加；模型保持旋转对称和平滑过渡。

### 3.2 B0.20: continuous aspheric corneal EDoF prototype

B0 用于模拟连续非球面角膜 EDoF 设计原则。候选角膜按6 mm口径 `ΔC4^0=+0.10,+0.15,+0.20,+0.25,+0.30 μm` 构建并经过真实 OpticStudio scan、morphology review 和预定义确定性排序。正式候选冻结为 `B0.20`，并在所有 IOL 主结果获得前锁定；后续禁止基于组合表现重新调参。

### 3.3 C0: central-near radial multifocal cornea

C0 表示中央近用型径向多焦角膜。冻结参数包括−3.00 D基础 treatment、3.00 mm中央近用区、+1.75 D处方 ADD、6.50 mm光学区和0.75 mm平滑过渡区。ADD 为处方层面的设计输入，而不是要求 ray-traced 任一局部位置严格等于+1.75 D局部屈光差。

## 4. IOL carrier scaffold and spherical-aberration calibration

所有平台使用统一 controlled carrier scaffold：IOL折射率1.460、周围介质1.336、中央厚度1.000 mm、光学直径6.000 mm、对称双凸弯曲；主要 conic 位于前表面，后表面 conic 为0。

IOL基础球差通过独立标准眼 `STD_IOL_EYE_2024` 进行 power-specific conic 校准。该标准眼只用于 IOL 球差/锥常数校准，不作为主研究模型眼。冻结校准条件包括6.0 mm entrance pupil、约546 nm波长、模型角膜 `C4^0≈+0.258 μm`、介质折射率约1.336及约5.15±0.10 mm的 IOL footprint。

三平台在标准眼 EPD6 下的基础球差目标为：WFS-like −0.20±0.01 μm，RAD-like −0.27±0.01 μm，HOA-like 0.00±0.01 μm。

对于每个 Base×Cornea×Platform carrier，首先在真实基础眼和角膜中以Q=0求远焦基础 power/曲率；随后将该实际 power/geometry 放入标准眼求对应的 power-specific conic `Q(P)`；再放回真实眼进行远焦检查。每个 physical carrier 的 power 与 conic 均独立求取，不把一个固定 Q 复制到不同 power。

## 5. EDoF mechanism surrogates

研究使用三类机制 surrogate，而非商业产品的处方级重建：

- **WFS-like**：波前塑形型 residual；
- **RAD-like**：连续径向屈光力调制型 residual；
- **HOA-like**：中央高阶球差调制型 residual。

三类 residual 均作为版本化 Grid Sag resource 冻结。对同一 matched pair，MONO 与 EDoF 的基础 P/R/Q、中央厚度、材料和IOL位置完全相同；EDoF 的唯一设计差异是相应 residual。Residual 冻结前移除非必要 piston 和整体 defocus，并经过实际 power 范围的 low/median/high calibration；加入 residual 后不重新优化 carrier。

## 6. Factorial matrix

共有：

```text
2 Base × 3 Cornea × 3 Platform = 18 physical carriers
18 carriers × 2 optic states × 2 pupils = 72 configurations
36 matched MONO–EDoF pairs
```

正式因素为：

```text
Base: LB_AL2395 / ATC_M3_AL24477
Cornea: A0 / B0 / C0
Platform: WFS / RAD / HOA
Pupil: 3.0 / 5.0 mm
Optic state: MONO / EDOF
```

报告层将 WFS/RAD/HOA 显示为 WFS-like/RAD-like/HOA-like，3.0/5.0 mm显示为 EPD3/EPD5；正式 evidence 原始 ID 不被改写。

## 7. MTF acquisition and common angular-frequency scale

主 MTF acquisition 固定为 `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`。生产数据通过 OpticStudio Merit Function Editor 的 `MTFA` operand 获取，设置为 Grid=1、Data Type=0、Wave=1、Field=1，production sampling为128。

为避免 EDoF residual 改变有效焦距后导致 MONO 与 EDoF 使用不同 cycles/degree 坐标，对每个 frozen matched pair 只在 residual-free MONO nominal-distance 状态测量一次 EFFL，并定义：

\[
mm/degree = EFL_{MONO}\tan(1^\circ)
\]

随后将共同的0–60 cycles/degree网格直接映射为 cycles/mm 查询频率。该 pair-specific MONO angular scale 被同一 pair 的 MONO、EDoF、全部贯焦平面和所有 production sampling共同使用；EDoF-state EFFL 不重新定义频率轴。

## 8. Through-focus analysis and optical metrics

贯焦范围固定为+0.50至−3.00 D，步长−0.25 D，共15个 retina-anchored平面。贯焦通过分析层改变输入离焦而不移动视网膜、IOL位置或重新优化 carrier。

### 8.1 MTFa

在共同0–60 cpd、1 cpd步长网格上定义：

\[
MTFa(F)=\frac{1}{60}\int_0^{60}MTFA(f,F)\,df
\]

并使用梯形积分。固定频率 MTF 同时记录10、20、30、40、50和60 cpd。

### 8.2 Distance peak

在−0.50至+0.50 D范围内取 MTFa 最大点作为 distance peak。若最大值位于±0.50 D搜索边界，则标记 `peak_search_censored=true`；其 peak position 与 peak MTFa只按预注册窗口内观察值解释。

### 8.3 DOF50

以 distance-peak MTFa 的50%为阈值，寻找包含 distance peak 的连续 `MTFa≥50% peak` 区间，并在线性插值相邻0.25 D采样点后计算 far crossing、near crossing和 width。如果 crossing 超出冻结贯焦窗口，则相应 width 作为 lower bound并保留 censor flag。

### 8.4 Through-focus mean MTFa

完整预注册窗口平均值定义为：

\[
TF\_MTFa\_mean=\frac{1}{3.5D}\int_{-3.00}^{+0.50}MTFa(F)\,dF
\]

用于评估延焦机制对整个贯焦窗口总体质量的影响。

### 8.5 Whole-eye higher-order aberrations

完整眼 Zernike n=3–6通过独立冻结的 `TASK009_MFE_ZERN_HOA_555_v1` readback获取，并提取 C40、C60和 HOA RMS，用于机制解释。

## 9. Run72 execution and provenance

正式 Run72 使用冻结72-config manifest执行，正式 code baseline 为 `01f13b768cf1eca361703469b2fdce3d21f3376d`，run ID 为 `analysis-1cc1441dec4744a18d7ac73763507a6c`，`resume_mode=false`。72/72配置完成，无失败，获得1080行贯焦数据和36条 matched-pair delta。

每个结果保存 baseline、manifest、lock-set、analysis settings、acquisition contract、pair-MONO angular reference、carrier/residual identity和run environment provenance。TASK-012 在分析前分别验证 Git repository-byte SHA256 与 TASK-011 evidence 中记录的 producer-export CSV SHA256，并独立复核72/36/1080结构完整性。

## 10. Offline paired and interaction analysis

主分析单元为36个 matched MONO–EDoF pairs。所有效应统一定义为：

\[
\Delta Y=Y_{EDOF}-Y_{MONO}
\]

主要 paired outcomes 为：

1. `ΔDOF50 width`；
2. `Δdistance-peak MTFa`；
3. `ΔMTFa at 0 D`；
4. `ΔTF MTFa mean`；
5. `ΔC40`；
6. `ΔC60`；
7. `ΔHOA RMS`；
8. `ΔF_residual`。

TASK-012 首先从72-config summary重新构建36个 matched effects，并以absolute tolerance `1×10^-12` 与正式 paired-delta evidence比较；同时从1080-row贯焦 evidence重新计算0 D MTFa与贯焦平均 MTFa。

随后在固定 Base×Pupil strata 内计算预定义 platform contrasts、cornea contrasts以及 Cornea×Platform difference-in-differences，并计算 EPD5−EPD3 pupil sensitivity和 ATC−LB base-eye sensitivity。基础眼和瞳孔均作为正式因素，不在 interaction 分析前平均掉。

DOF50 censoring通过区间代数传播至 pair-level effect、platform/cornea contrast、difference-in-differences及pupil/base sensitivity。5个正式 DOF50 effect 为 lower bound；8个 pair 的 peak-related metrics为预注册窗口条件值。

本研究的36个 matched pairs是完整、确定性的模拟 factorial matrix，而不是从临床总体随机抽取的样本。因此默认报告 effect magnitude、direction consistency、interaction contrasts、ranges和censor-aware interpretation，不进行把36个pair视作独立随机临床样本的传统ANOVA或p-value显著性推断。

## 11. Reproducibility

TASK-012分析和论文呈现均为纯Python离线流程，不重新调用 OpticStudio。正式分析产物包括36-pair table、1152个预定义 contrasts、9个3×3 coupling cells和24张分析图。论文级5张组合图仅从冻结 `TASK_012_PAIR_ANALYSIS.csv` 与 TASK-011 through-focus CSV重绘，presentation manifest明确记录 `scientific_values_changed=false` 和 `opticstudio_used=false`。
