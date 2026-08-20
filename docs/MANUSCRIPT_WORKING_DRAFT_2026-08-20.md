# 角膜屈光术后代表性光学原型与非衍射延伸焦深人工晶状体机制的耦合

## 基于双模型眼、双瞳孔与匹配单焦对照的计算光学研究

> **Working manuscript v0.1 — 2026-08-20**  
> 本稿为自包含论文工作稿。正式数值来源为冻结 TASK-012 结构化 evidence；本稿不建立新的 scientific lock。  
> WFS-like / RAD-like / HOA-like 为机制 surrogate，不对应商业产品排名。

---

## Structured Abstract

### Purpose

评估代表性角膜屈光术后光学原型与不同非衍射延伸焦深（extended depth of focus, EDoF）人工晶状体机制之间是否存在非简单加和的耦合，并描述这种耦合如何随瞳孔和基础模型眼改变焦深、固定焦面成像质量、贯焦质量及全眼高阶像差。

### Methods

建立两个轴上、共轴、单色的人工晶状体模型眼：Liou–Brennan 型 `LB_AL2395`（眼轴23.950 mm）和 Atchison 近视型 `ATC_M3_AL24477`（代表约−3 D，眼轴24.477 mm）。设置三个冻结角膜原型：A0（−3.00 D近视术后、正球差增加型准单焦角膜）、B0.20（连续非球面角膜 EDoF 原型）和 C0（中央3.0 mm近用区、处方附加+1.75 D的径向多焦角膜）。三类 IOL 机制 surrogate 分别为波前塑形型（WFS-like）、连续径向屈光力调制型（RAD-like）和中央高阶球差调制型（HOA-like）。

每个 Base×Cornea×Platform 建立独立 physical carrier；EDoF 与 matched MONO 使用完全相同的基础光焦度、曲率、conic、厚度、材料和位置，唯一设计差异为冻结 residual。正式矩阵包括18个 physical carriers、36个 matched MONO–EDoF pairs 和72个配置，分别在3和5 mm entrance pupil下计算。

生产 MTF 通过 Zemax OpticStudio MFE `MTFA Grid=1` 获取，使用每个 matched pair 的 residual-free MONO EFFL 建立共同0–60 cycles/degree角频率尺度。贯焦范围固定为+0.50至−3.00 D，步长0.25 D，共15个平面。主要 paired outcomes 均定义为 `EDOF−MONO`，包括 DOF50 width、0 D MTFa、完整贯焦窗口平均 MTFa、窗口内 distance-peak MTFa以及 C40、C60和 HOA RMS。分析采用预先冻结的确定性 factorial contrast 与 difference-in-differences，不把36个 pair视为随机临床样本进行传统显著性检验。DOF50 和 distance-peak censoring 均显式传播。

### Results

72/72配置完成且无失败，共获得1080个贯焦采样点。36个 matched pair 中，30个（83.3%）的 `ΔDOF50` 为正、6个为负；31个 DOF50 effect 为精确值，5个为 lower bound。与此相对，`ΔMTFa@0D` 和完整窗口 `ΔTF MTFa mean` 在36/36 pair中均为负，提示延焦主要通过焦轴方向上的光学质量再分配实现。

B0×WFS-like 显示明显的小瞳孔特异耦合：B0相对A0的 WFS-vs-RAD DOF50 difference-in-differences 在两种基础眼的3 mm瞳孔均为正（≥+0.157和≥+0.195 D），但在5 mm瞳孔反转为−0.210和−0.097 D。C0×RAD-like 的相对 DOF coupling 在两种基础眼和两种瞳孔方向一致，并在5 mm瞳孔更明显，但伴随更大的0 D MTFa损失。HOA-like 在3 mm瞳孔产生最大的 DOF 扩展（多数组合约+0.63至+0.73 D），同时表现出最大的固定焦面/贯焦 MTFa下降和最强的瞳孔及基础眼依赖。

### Conclusions

角膜屈光术后光学结构与非衍射 EDoF IOL 机制之间存在条件依赖的完整眼耦合，而非简单可加效应。B0×WFS-like 主要表现为小瞳孔特异的相对延焦耦合，C0×RAD-like 表现为较稳定但有固定焦面质量代价的 DOF-oriented coupling，HOA-like 则表现为最强但最不稳定的质量再分配。结果支持以角膜光学表型、瞳孔和 IOL 延焦机制共同分层的后续实验与临床研究，但不支持将机制 surrogate 直接转化为商业 IOL 排名或患者级推荐。

---

# Introduction

角膜屈光手术后的白内障管理正在从相对少见的特殊情境逐渐转变为常见的屈光性白内障问题。既往综述估计全球已有超过4000万例角膜屈光手术；随着接受 LASIK、PRK 等手术的人群进入白内障高发年龄，术后人工晶状体（IOL）度数预测、视觉质量和老视矫正策略将越来越重要。现代总角膜屈光力、光线追迹、术中像差测量和专用 IOL 计算公式已经改善了屈光预测，但既往角膜屈光手术仍会改变角膜曲率关系、非球面性和高阶像差，使 IOL 选择不再只是“把球镜度数算准”的问题。[3]

这种挑战在老视矫正 IOL 中更加突出。LASIK/PRK 后患者通常已经有过减少眼镜依赖的经历，对白内障术后的视觉范围和屈光结果可能具有较高期待；与此同时，近视角膜消融常增加正球差和其他高阶像差，较大瞳孔下的光学质量尤其可能受影响。对13项研究、445眼的系统综述显示，既往角膜激光手术后植入老视矫正 IOL 可以获得较好的远、中、近视觉和较高眼镜独立性，但眩光、光晕和对比敏感度下降仍是需要考虑的问题，而且现有研究异质性较高，尚不足以形成简单的 IOL 选择规则。[4]

EDoF IOL 因形成连续的有效焦域，而不是依赖多个离散焦点，被认为可能对部分屈光术后眼具有优势。近年的临床证据支持这种可能性。Fan 等在非衍射波前塑形 EDoF IOL 的前瞻性病例系列中发现，既往近视 LASIK 组获得良好的远、中视力，并呈现较平滑的离焦曲线和更大的主观焦深。[6] Micheletti 和 Hall 在角膜球差较高的 post-myopic LASIK/PRK 眼中同样报告了良好的远、中及功能性近视力和较高满意度。[7] 这些结果提示，较高的术后球差并不必然排除非衍射 EDoF IOL，但也不能据此推断所有术后角膜或所有 EDoF 机制均具有同样的适配性。

计算光学研究进一步表明，**瞳孔和角膜像差会改变 EDoF IOL 与术后角膜的相互作用**。Lago、de Castro 和 Marcos 在 post-LASIK 伪晶状体模型中比较单焦与非衍射 EDoF IOL，发现3 mm瞳孔下 EDoF 的焦深优势较明显，而5 mm瞳孔下两者焦深趋于接近；模型同时显示球差、彗差及瞳孔大小都会改变远焦质量和贯焦表现。[5] 临床比较研究也观察到，LASIK/PRK 后全眼球差在较大瞳孔下明显增加，并提示夜间瞳孔及球差范围与视觉现象相关。[10] 因而，仅用“是否做过 LASIK”或单一球差值来概括屈光术后眼，可能不足以预测 EDoF IOL 的完整眼表现。

现有研究仍有一个重要缺口。多数 post-refractive EDoF 研究聚焦于常规近视/远视 LASIK 或 PRK 后角膜与某一具体商业 IOL 的临床结果或计算性能，而较少把角膜本身视为一个具有不同延焦结构的光学子系统，系统研究其与不同非衍射 EDoF 机制之间的耦合。这个问题在曾接受老视角膜屈光设计的人群中尤其重要：连续非球面角膜 EDoF 设计和中央近用型径向多焦角膜已经主动改变了焦轴能量分配，如果再植入具有波前塑形、径向屈光力调制或高阶球差调制特征的 EDoF IOL，两个延焦机制可能协同、相互抵消，也可能产生依赖瞳孔和基础眼结构的质量再分配。我们的目标性文献检索未发现与此类角膜原型和非衍射 EDoF IOL 组合直接对应、且足以建立临床选择规则的高质量系列，因此这一问题更适合首先通过受控机制模型进行分解。

本研究据此建立一个冻结、可追溯的计算光学矩阵，将三个代表性术后角膜原型——传统近视术后准单焦角膜（A0）、连续非球面角膜 EDoF 原型（B0.20）和中央近用型径向多焦角膜（C0）——分别与三类非衍射 EDoF IOL 机制 surrogate——波前塑形型（WFS-like）、连续径向屈光力调制型（RAD-like）和中央高阶球差调制型（HOA-like）——组合，并在两个基础模型眼和3/5 mm瞳孔下与严格匹配的 MONO carrier 比较。研究的主要目的不是寻找一个商业意义上的“最佳 IOL”，而是回答三个机制问题：第一，角膜原型与 IOL 延焦机制之间是否存在非简单加和的 coupling；第二，这种 coupling 是否随瞳孔和基础眼改变方向；第三，焦深增加与固定焦面/完整贯焦光学质量之间如何交换。

---

# Methods

## Study design

本研究为确定性计算光学研究。所有主分析均在单色555 nm、轴上0°视场、角膜/瞳孔/IOL共轴条件下进行。MVP 不加入角膜治疗区偏心、IOL倾斜/偏心或微单视附加离焦，以隔离角膜和 IOL 设计机制本身的相互作用。

采用严格 matched-pair 设计：对于每一个 Base×Cornea×Platform×Pupil 条件，EDoF 配置与 MONO 对照共享完全相同的 physical carrier，唯一设计差异是相应平台的冻结 EDoF residual。因此，所有 `EDOF−MONO` 差异均表示 residual 加入后的完整眼光学效应。

## Model eyes

`LB_AL2395` 基于 Liou–Brennan 解剖学有限模型眼，[1] 眼轴长度固定为23.950 mm，用于代表典型正视眼结构。`ATC_M3_AL24477` 基于 Atchison 2006 Model 1 的居中近视眼框架，[2] 选择代表约−3 D近视的样本，眼轴长度固定为24.477 mm。

两个基础眼共同使用后角膜至 STOP 3.150 mm、后角膜至 IOL 前表面参考位置4.500 mm，房水/玻璃体工程折射率约1.336。IMAGE 顶点由各自眼轴固定，贯焦分析不移动视网膜。

## Post-refractive corneal prototypes

三个角膜原型在主矩阵前冻结，且不允许依据 IOL 结果回调参数。

**A0** 表示传统近视角膜屈光术后准单焦原型。冻结 treatment 为−3.00 D，有效光学区约5.0 mm，并以6 mm口径下约 `+0.13 μm` 的 `ΔC4^0` 表示典型正球差增加；模型保持旋转对称和平滑过渡。

**B0.20** 用于模拟连续非球面角膜 EDoF 设计原则。候选角膜按6 mm口径 `ΔC4^0=+0.10,+0.15,+0.20,+0.25,+0.30 μm` 构建并经过真实 OpticStudio scan、morphology review 和预定义确定性排序。正式候选在 IOL 主分析前冻结为 `B0.20`，后续禁止基于组合表现重新调参。

**C0** 表示中央近用型径向多焦角膜。冻结参数包括−3.00 D基础 treatment、3.00 mm中央近用区、+1.75 D处方 ADD、6.50 mm光学区和0.75 mm平滑过渡区。ADD 为处方层面的设计输入，而不是要求 ray-traced 任一局部位置严格等于+1.75 D局部屈光差。

## IOL carrier scaffold and spherical-aberration calibration

所有平台使用统一 controlled carrier scaffold：IOL折射率1.460、周围介质1.336、中央厚度1.000 mm、光学直径6.000 mm、对称双凸弯曲；主要 conic 位于前表面，后表面 conic 为0。

IOL基础球差通过独立标准眼 `STD_IOL_EYE_2024` 进行 power-specific conic 校准。该标准眼只用于 IOL 球差/锥常数校准，不作为主研究模型眼。冻结校准条件包括6.0 mm entrance pupil、约546 nm波长、模型角膜 `C4^0≈+0.258 μm`、介质折射率约1.336及约5.15±0.10 mm的 IOL footprint。

三平台在标准眼 EPD6 下的基础球差目标为：WFS-like −0.20±0.01 μm，RAD-like −0.27±0.01 μm，HOA-like 0.00±0.01 μm。对于每个 Base×Cornea×Platform carrier，首先在真实基础眼和角膜中以Q=0求远焦基础 power/曲率；随后将该实际 power/geometry 放入标准眼求对应的 power-specific conic `Q(P)`；再放回真实眼进行远焦检查。每个 physical carrier 的 power 与 conic 均独立求取。

## EDoF mechanism surrogates

研究使用三类机制 surrogate，而非商业产品的处方级重建：WFS-like 为波前塑形型 residual，RAD-like 为连续径向屈光力调制型 residual，HOA-like 为中央高阶球差调制型 residual。三类 residual 均作为版本化 Grid Sag resource 冻结。

对同一 matched pair，MONO 与 EDoF 的基础 P/R/Q、中央厚度、材料和 IOL 位置完全相同；EDoF 的唯一设计差异是相应 residual。Residual 冻结前移除非必要 piston 和整体 defocus，并经过实际 power 范围的 low/median/high calibration；加入 residual 后不重新优化 carrier。

## Factorial matrix

共有18个 physical carriers：

\[
2\ Base\times3\ Cornea\times3\ Platform=18
\]

每个 carrier 建立 MONO/EDoF，并在3.0与5.0 mm pupil下分析：

\[
18\times2\ state\times2\ pupil=72\ configurations
\]

因此形成36个 matched MONO–EDoF pairs。报告层将 WFS/RAD/HOA 显示为 WFS-like/RAD-like/HOA-like，3.0/5.0 mm显示为 EPD3/EPD5；正式 evidence 原始 ID 不被改写。

## MTF acquisition and angular-frequency scale

主 MTF acquisition 固定为 `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`。生产数据通过 OpticStudio Merit Function Editor 的 `MTFA` operand 获取，Grid=1、Data Type=0、Wave=1、Field=1，production sampling为128。

为避免 EDoF residual 改变有效焦距后导致 MONO 与 EDoF 使用不同 cycles/degree 坐标，对每个 frozen matched pair 只在 residual-free MONO nominal-distance 状态测量一次 EFFL，并定义：

\[
mm/degree=EFL_{MONO}\tan(1^\circ)
\]

随后将共同的0–60 cycles/degree网格直接映射为 cycles/mm 查询频率。该 pair-specific MONO angular scale 被同一 pair 的 MONO、EDoF、全部贯焦平面和所有 production sampling共同使用；EDoF-state EFFL 不重新定义频率轴。

## Through-focus metrics

贯焦范围固定为+0.50至−3.00 D，步长−0.25 D，共15个 retina-anchored平面。贯焦通过分析层改变输入离焦而不移动视网膜、IOL位置或重新优化 carrier。

在共同0–60 cpd、1 cpd步长网格上定义：

\[
MTFa(F)=\frac{1}{60}\int_0^{60}MTFA(f,F)\,df
\]

并使用梯形积分。固定频率 MTF 同时记录10、20、30、40、50和60 cpd。

在−0.50至+0.50 D范围内取 MTFa 最大点作为 distance peak。若最大值位于±0.50 D边界，则标记 `peak_search_censored=true`。DOF50 以 distance-peak MTFa 的50%为阈值，寻找包含 distance peak 的连续 `MTFa≥50% peak` 区间，并在线性插值相邻采样点后计算 far crossing、near crossing和 width；若 crossing 超出冻结窗口，则相应 width 保留为 lower bound。

完整贯焦窗口平均 MTFa 定义为：

\[
TF\_MTFa\_mean=\frac{1}{3.5D}\int_{-3.00}^{+0.50}MTFa(F)\,dF
\]

完整眼 Zernike n=3–6通过 `TASK009_MFE_ZERN_HOA_555_v1` readback获取，并提取 C40、C60和 HOA RMS。

## Run72 and offline analysis

正式 Run72 code baseline 为 `01f13b768cf1eca361703469b2fdce3d21f3376d`，run ID 为 `analysis-1cc1441dec4744a18d7ac73763507a6c`，`resume_mode=false`。72/72配置完成，无失败，获得1080行贯焦数据和36条 matched-pair delta。

主分析单元为36个 matched pairs，所有效应统一定义为：

\[
\Delta Y=Y_{EDOF}-Y_{MONO}
\]

主要 outcomes 为 `ΔDOF50 width`、`Δdistance-peak MTFa`、`ΔMTFa at 0 D`、`ΔTF MTFa mean`、`ΔC40`、`ΔC60`、`ΔHOA RMS` 和 `ΔF_residual`。

TASK-012 首先从72-config summary重新构建36个 matched effects，并以absolute tolerance `1×10^-12` 与正式 paired-delta evidence比较；同时从1080-row贯焦 evidence重新计算0 D MTFa与贯焦平均 MTFa。随后在固定 Base×Pupil strata 内计算预定义 platform contrasts、cornea contrasts、Cornea×Platform difference-in-differences、EPD5−EPD3 pupil sensitivity和 ATC−LB base-eye sensitivity。

DOF50 censoring通过区间代数传播至 pair-level effect 和各级 contrast。由于36个 matched pairs是完整、确定性的模拟 factorial matrix，而不是从临床总体随机抽样的样本，本研究报告 effect magnitude、direction consistency、interaction contrasts、ranges和censor-aware interpretation，不进行把36个 pair视作独立随机临床样本的传统 ANOVA 或 p-value 推断。

---

# Results

## Data completeness and censoring

正式 Run72 包含72个配置、36个严格匹配的 MONO–EDoF pair 和1080个贯焦采样点。TASK-012 从 config-level evidence 独立重建36个 paired effects，并复算0 D MTFa和完整预注册贯焦窗口内的平均 MTFa；全部 reconstruction gate 通过。

36个 pair 中，31个 DOF50 effect 为精确值，5个为 lower bound。另有8个 pair 的 distance-peak 指标达到预注册 peak-search window 边界。因此，本研究保留 DOF50 lower-bound 与 peak-window-conditioned 属性，不进行伪精确排序。

## Overall extension–quality trade-off

36个 pair 中，30个 `ΔDOF50` 为正、6个为负。相反，`ΔMTFa@0D` 在36/36 pair中均为负，完整预注册贯焦窗口内的 `ΔTF MTFa mean` 也在36/36 pair中均为负；窗口内 observed distance-peak MTFa 同样全部下降，其中8个 pair 受 peak-search window 限制。

因此，EDoF residual 通常通过重新分配焦轴方向上的光学质量来扩展 DOF50，而不是在保持 matched MONO 固定焦面质量的同时简单增加焦深（Figure 3）。

## Cornea × Platform matrix

四个 Base×Pupil strata 的描述性均值如下。带 `≥` 的 DOF50 为 lower-bound mean；均值只描述当前确定性矩阵，不能视为临床总体参数。

| Cornea × Platform | ΔDOF50 mean, D | ΔMTFa@0D mean | ΔTF MTFa mean |
| --- | ---: | ---: | ---: |
| A0 × WFS-like | +0.137 | -0.120 | -0.0108 |
| A0 × RAD-like | +0.107 | -0.168 | -0.0150 |
| A0 × HOA-like | +0.194 | -0.320 | -0.0524 |
| B0 × WFS-like | ≥+0.227 | -0.139 | -0.0112 |
| B0 × RAD-like | +0.185 | -0.166 | -0.0151 |
| B0 × HOA-like | +0.241 | -0.287 | -0.0506 |
| C0 × WFS-like | +0.127 | -0.118 | -0.0083 |
| C0 × RAD-like | ≥+0.243 | -0.216 | -0.0092 |
| C0 × HOA-like | ≥+0.409 | -0.345 | -0.0555 |

这些 cell mean 隐藏了重要 pupil/base 异质性，因此主解释以分层 interaction 为优先，而不是按均值直接排名（Figures 1–2）。

## B0 × WFS-like: pupil-specific relative DOF coupling

B0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences 在 EPD3 为正，在 EPD5 反转：LB EPD3 `≥+0.157 D`、ATC EPD3 `≥+0.195 D`，而 LB EPD5 为 `−0.210 D`、ATC EPD5 为 `−0.097 D`。WFS-vs-HOA 也出现相同方向变化：EPD3 为 `≥+0.152 D` 和 `≥+0.146 D`，EPD5 为 `−0.093 D` 和 `−0.032 D`。

B0×WFS-like 的 pair-level DOF50 在 EPD3 达到 `≥+0.462 D`（LB）和 `≥+0.432 D`（ATC），而 EPD5 仅为 `+0.034 D`（LB）和 `−0.021 D`（ATC）。因此其主要耦合信号为 EPD3-specific，而非跨瞳孔稳定优势（Figure 4）。

该 DOF coupling 也不伴随固定焦面质量优势。B0 条件下 WFS 相对 RAD 的 `ΔMTFa@0D` interaction 在 EPD3 约为−0.044至−0.048，提示额外 DOF 增益仍以0 D MTFa下降为代价。

## C0 × RAD-like: relatively stable DOF-oriented coupling

C0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences 在四个 strata 均为负：LB EPD3 `−0.066 D`、ATC EPD3 `−0.073 D`、LB EPD5 `≤−0.274 D`、ATC EPD5 `≤−0.170 D`。由于 contrast 定义为 WFS−RAD，这表示 C0 对 RAD-like 的相对 DOF coupling 在两种基础眼和两种瞳孔中均高于 WFS-like，并且 EPD5 更明显。

C0×RAD-like 的 pair-level DOF50 在四个 strata 全部正向：LB EPD3 `+0.166 D`、ATC EPD3 `+0.213 D`，LB EPD5 `≥+0.302 D`、ATC EPD5 `≥+0.290 D`。

但固定焦面质量显示相反权衡。C0 条件下 WFS-vs-RAD 的 `ΔMTFa@0D` interaction 在四个 strata 均为正（约+0.012至+0.092），说明 WFS-like 相对保留更多0 D MTFa，而 RAD-like 以更大的固定焦面质量代价换取更多 DOF。因此该模式应描述为 DOF-oriented trade-off，而非总体光学质量的无条件优势。

## HOA-like: strong redistribution and strong pupil/base dependence

HOA-like 在 EPD3 可产生本矩阵中最大的 DOF50 扩展：A0约+0.63～+0.66 D，B0约+0.73 D，C0约+0.66～+0.68 D。然而 A0 和 B0 到 EPD5 后均转为负向 DOF effect。C0×HOA-like 的 EPD5 又显示明显基础眼分离：LB 为 `−0.097 D`，ATC 为 `≥+0.392 D`。

相应地，HOA-like 的0 D及全贯焦平均 MTFa损失也最大。A0/B0/C0 三个 cell 的 `ΔMTFa@0D` mean 分别约−0.320、−0.287和−0.345，`ΔTF MTFa mean` 分别约−0.052、−0.051和−0.056。其主要特征因此是强烈的焦轴质量再分配，而不是跨条件稳定的最大延焦。

## Higher-order-aberration signatures

三类 surrogate 形成不同的 C40/C60 瞳孔签名。WFS-like 在 EPD3 主要表现为约 `+0.032 μm` 的 ΔC40 与约 `−0.017 μm` 的 ΔC60，EPD5 时两者幅度均明显减小。RAD-like 在 EPD3 主要表现为较小正 ΔC40 与约 `−0.09 μm` 的 ΔC60，而 EPD5 转为约 `−0.129 μm` 的 ΔC40 与 `+0.063 μm` 的 ΔC60。HOA-like 在 EPD3 则约为 `−0.067～−0.070 μm` 的 ΔC40 与 `+0.171～+0.175 μm` 的 ΔC60，EPD5 幅度显著降低。

RAD-like 在 EPD5 的 net HOA RMS 对角膜原型高度敏感：B0约为−0.092～−0.100 μm，C0约为+0.127 μm，而 A0接近零。这一方向差异支持 Cornea×Platform 之间存在非简单加和的机制耦合（Figure 5）。

---

# Discussion

本研究的核心结果不是识别一个跨所有条件“最好”的 EDoF surrogate，而是证明角膜原型、IOL 延焦机制、瞳孔和基础眼共同决定延焦—质量交换的形态。B0×WFS-like 的 relative DOF coupling 随瞳孔由 EPD3 到 EPD5 发生方向反转；C0×RAD-like 的 DOF coupling 则在两种基础眼和两种瞳孔中保持较一致方向；HOA-like 的效应幅度最大，但同时具有最强的瞳孔和基础眼依赖。

这种结果支持一个更合适的研究框架：屈光术后角膜不只是需要被“补偿”的静态像差背景，而是会与 EDoF IOL 的具体光学机制共同塑造整个眼的贯焦响应。因此，对术后白内障眼的 EDoF 评价不能仅依据 IOL 本身的标称焦深，也不能只依据角膜球差的单一数值。

## Pupil dependence and WFS-like coupling

Lago 等的 post-LASIK 计算模拟显示，非衍射 EDoF IOL 的焦深优势在3 mm瞳孔下明显，而在5 mm瞳孔下与单焦 IOL 的焦深趋于接近。[5] Garzón 等的光学台研究也证明非衍射波前塑形 IOL 的光焦度和高阶像差在中央光学区具有复杂空间分布，且性能随瞳孔改变。[8] 这些结果不能直接验证本研究的 B0 surrogate，但与 B0×WFS-like 的 EPD3-specific coupling 在方向上相容。

本研究进一步提示，当角膜本身已经具有延焦特征时，瞳孔改变的不只是单独一个光学元件的性能，而可能改变两个延焦机制之间的相互作用方向。因此，若未来临床研究只在单一光照/单一瞳孔条件下比较 EDoF 结果，可能会遗漏关键的耦合异质性。

## Clinical evidence after conventional LASIK/PRK

普通近视 LASIK/PRK 后使用老视矫正或非衍射 EDoF IOL 的临床可行性正在得到支持。Sun 等的系统综述显示，既往角膜激光手术后植入老视矫正 IOL 可以获得较好的视觉范围和眼镜独立性，但仍需重视眩光、光晕和对比敏感度等问题。[4] Fan 等的前瞻性研究中，post-LASIK 组在非衍射波前塑形 EDoF IOL 后呈现较宽的主观焦深和较平滑的离焦曲线。[6] Micheletti 和 Hall 在高角膜球差的 post-myopic LASIK/PRK 眼中也报告了良好的视觉结果和较高满意度。[7]

这些证据支持“屈光术后角膜并不自动排除非衍射 EDoF IOL”，但它们主要研究常规近视 LASIK/PRK 后角膜。当前目标性检索未发现与本研究 B0 所代表的角膜 EDoF/presbyopic-ablation 原型，或 C0 所代表的中央近用径向多焦角膜，直接对应且质量足够高的非衍射 EDoF IOL 临床系列。因此，本研究的 B0×WFS-like 和 C0×RAD-like 应被表述为机制生成与可检验假设，而不是临床选片建议。

## C0 × RAD-like and spatial power redistribution

C0×RAD-like 是当前矩阵中方向较稳定的 DOF coupling 信号之一，尤其在 EPD5 更明显。由于 C0 和 RAD-like 都包含显著的径向空间结构，一个合理的机制假设是，两者的径向功率/相位分配可在完整眼系统中形成更宽的有效贯焦包络。

但 formal evidence 同时显示，C0×RAD-like 的0 D MTFa损失大于 C0×WFS-like，且 C0×RAD-like 的 EPD5 HOA RMS 由 A0/B0 中的接近零或下降转为明显增加。这意味着“径向机制匹配”若存在，也不是简单的像差抵消，而可能是以更强的焦轴能量重分配换取焦深。未来验证应同时观察 DOF、固定焦面质量和贯焦曲线形态，而不是只比较 DOF50 width。

Schmid 和 Borkenstein 的光学台研究显示，新的折射型 enhanced-depth-of-focus IOL 可通过连续光焦度/非球面结构塑造贯焦性能，而且结果会随 pupil aperture 改变。[9] 这一类外部光学台证据为“径向屈光结构应在完整眼和不同瞳孔下评估”提供了背景，但并不构成本研究 C0×RAD-like 的直接验证。

## HOA-like and the double-edged role of aberration-driven DOF

利用球差或高阶像差扩展焦深具有明确物理基础，但本研究显示该路径的鲁棒性较低：EPD3 可以产生非常大的焦深扩展，而 EPD5 可完全反转；C0×HOA-like×EPD5 甚至在两种基础眼间发生方向分离。与此同时，HOA-like 的固定焦面和全贯焦 MTFa损失最大。

这与既往关于球差能够扩展焦深、但其作用高度依赖 pupil 和基础光学状态的研究框架一致。它也说明术后角膜 HOA 不应被简单分类为“有利于 EDoF”或“不利于 EDoF”；同一 HOA 机制在不同 pupil 和不同 eye model 中可能产生相反的有效 DOF 结果。

## Clinical implication: mechanism matching rather than product ranking

本研究尚不足以给出临床产品排名，但为未来屈光术后白内障 IOL 选择提出了可操作的研究假设。一个更有信息量的术前框架可能需要同时考虑角膜贯焦特征、瞳孔、C40/C60及更完整 HOA 结构，而不只是既往屈光手术史或单一 Q 值。

尤其值得进一步验证的两个方向是：第一，具有角膜 EDoF 特征的眼是否存在对中央波前塑形型 IOL 的小瞳孔特异协同；第二，中央近用/径向多焦角膜是否可能与某些径向功率调制型 IOL 形成相对稳定、但伴随距离质量代价的 coupling。上述两点在本研究中均为机制假设，而非临床处方。

## Limitations

本研究是确定性光学模拟而非临床样本研究。两种基础眼和三个角膜原型用于机制覆盖，不代表真实人群分布；结果不宜使用普通随机样本显著性推断。WFS-like、RAD-like 和 HOA-like 是机制 surrogate，不能与任一商业 IOL 一一等同。DOF50 有5个 lower-bound pair，distance-peak 有8个 window-conditioned pair；预注册窗口没有因这些结果而事后扩大。

MVP 中角膜屈光手术居中，未加入角膜消融区偏心/倾斜；IOL偏心和倾斜也未纳入当前矩阵。真实术后角膜还存在不规则像差、上皮重塑、泪膜和个体 pupil dynamics 等因素。因此，本研究更适合用于定义下一步机制实验和临床分层变量，而不是直接预测单个患者结果。

此外，本研究以555 nm单色、轴上 MTFa 为主要视觉质量指标，没有模拟色差、神经视觉适应、双眼整合、眩光或真实视标可见度。后续研究可在不改变当前 MVP 机制结论的前提下，引入多波长、偏心/倾斜、个体角膜 tomography 或视觉模拟进行外部验证。

---

# Conclusion

角膜屈光术后眼中，非衍射 EDoF IOL 的光学效应取决于角膜原型、IOL 延焦机制、瞳孔和基础眼之间的耦合。当前模型中，B0×WFS-like 显示小瞳孔特异的相对 DOF coupling，C0×RAD-like 显示较稳定的 DOF-oriented coupling，而 HOA-like 产生最强但最不稳定的焦轴质量再分配。所有36个 pair 的0 D和完整贯焦平均 MTFa均相对 matched MONO下降，提示焦深扩展应始终与光学质量代价共同解释。当前结果支持机制分层和后续可检验假设，但不支持将3×3矩阵直接转化为商业 IOL 排名或患者级临床推荐。

---

# Figure plan

- **Figure 1:** Base×Pupil 分层 `ΔDOF50` 3×3矩阵。
- **Figure 2:** Base×Pupil 分层 `ΔMTFa@0D` 3×3矩阵。
- **Figure 3:** `ΔDOF50` 与固定焦面/完整窗口质量的 trade-off。
- **Figure 4:** B0×WFS-like、C0×RAD-like、C0×HOA-like 的代表性贯焦曲线。
- **Figure 5:** C40–C60 机制图及 RAD-like EPD5 的角膜依赖 HOA RMS。

论文呈现图由独立 presentation-only renderer 从冻结 CSV 重绘；不改变 TASK-012 scientific values。

---

# References

1. Liou HL, Brennan NA. Anatomically accurate, finite model eye for optical modeling. *J Opt Soc Am A Opt Image Sci Vis*. 1997;14(8):1684-1695. doi:10.1364/JOSAA.14.001684.
2. Atchison DA. Optical models for human myopic eyes. *Vision Res*. 2006;46(14):2236-2250. doi:10.1016/j.visres.2006.01.004.
3. Ting DSJ, Gatinel D, Ang M. Cataract surgery after corneal refractive surgery: preoperative considerations and management. *Curr Opin Ophthalmol*. 2024. PMID:37962882.
4. Sun Y, Hong Y, Rong X, Ji Y. Presbyopia-Correcting Intraocular Lenses Implantation in Eyes After Corneal Refractive Laser Surgery: A Meta-Analysis and Systematic Review. *Front Med (Lausanne)*. 2022;9:834805. doi:10.3389/fmed.2022.834805.
5. Lago CM, de Castro A, Marcos S. Computational simulation of the optical performance of an EDOF intraocular lens in post-LASIK eyes. *J Cataract Refract Surg*. 2023;49(11):1153-1159. doi:10.1097/J.JCRS.0000000000001260.
6. Fan W, Zhu M, Zhang G. Visual outcomes and spectacle independence of a non-diffractive wavefront-shaping intraocular lens in post-LASIK patients. *Front Med (Lausanne)*. 2025;12:1509889. doi:10.3389/fmed.2025.1509889.
7. Micheletti JM, Hall B. Satisfaction and Visual Outcomes with a Non-Diffractive EDOF IOL in Post-Myopic LASIK and PRK Patients with High Corneal Spherical Aberration. *Clin Ophthalmol*. 2026;20. doi:10.2147/OPTH.S566800.
8. Garzón N, Gómez-Pedrero JA, Albarrán-Diego C, et al. Optical power profiles and aberrations of a non-diffractive wavefront-shaping extended depth of focus intraocular lens. *Graefes Arch Clin Exp Ophthalmol*. 2024;262(9):2897-2906. doi:10.1007/s00417-024-06469-y.
9. Schmid R, Borkenstein AF. Optical Bench Evaluation of the Latest Refractive Enhanced Depth of Focus Intraocular Lens. *Clin Ophthalmol*. 2024;18:1921-1932. doi:10.2147/OPTH.S469849.
10. Ni S, Zhuo B, Cai L, et al. Visual outcomes and patient satisfaction after implantations of three types of presbyopia-correcting intraocular lenses that have undergone corneal refractive surgery. *Sci Rep*. 2024;14:8386. doi:10.1038/s41598-024-58653-z.
