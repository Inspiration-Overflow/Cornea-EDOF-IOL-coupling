# 角膜屈光术后代表性光学表型与非衍射延伸焦深人工晶状体机制的耦合：基于未治疗参照、双模型眼和双瞳孔的计算光学研究

## Structured Abstract

### Purpose

评估代表性角膜屈光术后光学表型是否会改变不同非衍射延伸焦深（EDoF）人工晶状体机制在完整眼中的作用，并以未治疗角膜（N0）为内部参照，描述这种耦合如何随瞳孔和基础模型眼改变焦深、固定焦面成像质量、贯焦质量及全眼高阶像差。

### Methods

建立两个轴上、共轴、单色人工晶状体模型眼：Liou–Brennan 型 `LB_AL2395`（眼轴23.950 mm）和 Atchison 近视型 `ATC_M3_AL24477`（代表约−3 D近视表型，眼轴24.477 mm）。角膜条件包括未治疗参照 N0，以及三个顶点距规范化术后原型 A0V12、B0V12 和 C0V12。术后处方统一定义为镜片平面−3.00 D、顶点距12 mm，对应角膜平面治疗量−2.8957529 D。三类 IOL 机制 surrogate 为波前塑形型（WFS-like）、连续径向屈光力调制型（RAD-like）和中央高阶球差调制型（HOA-like）。

每个 Base×Cornea×Platform 独立建立 physical carrier；EDoF 与 matched MONO 共享完全相同的基础光焦度、曲率、conic、厚度、材料和位置，唯一设计差异为冻结 residual。最终接受矩阵包括24个 physical carriers、48个严格匹配的 MONO–EDoF pairs 和96个配置，在3和5 mm entrance pupil下计算。生产 MTF 通过 Zemax OpticStudio MFE `MTFA Grid=1` 获取；贯焦范围固定为+0.50至−3.00 D、步长0.25 D，共15个平面。主要 paired outcomes 定义为 `EDOF−MONO`；术后耦合定义为 `(EDOF−MONO)_postop − (EDOF−MONO)_N0`。DOF50 与 distance-peak censoring 均显式保留。

### Results

96/96配置完成且无失败，共获得1440个贯焦采样点。35/48 pair 的 `ΔDOF50` 为正、13/48为负；43个 DOF50 effect 为精确值，5个为 lower bound，10个 pair 的 distance peak 位于预注册搜索窗边界。`ΔTF MTFa mean` 在48/48 pair均为负，`ΔMTFa@0D` 在47/48 pair为负。

N0-referenced interaction 显示明显的机制×角膜×瞳孔依赖。B0V12×WFS-like 在3 mm瞳孔下相对 N0 的 DOF50 增强在两种基础眼均为 lower bound（LB ≥+0.266 D；ATC ≥+0.260 D）；B0V12×RAD-like 的主要增强位于5 mm（LB +0.275 D；ATC +0.307 D）。C0V12×RAD-like 在5 mm呈强增强且两种基础眼均为 lower bound（LB ≥+0.379 D；ATC ≥+0.471 D）；C0V12×HOA-like 在5 mm同样明显增强（LB +0.246 D；ATC ≥+0.689 D），而3 mm相对 N0减弱。上述延焦均伴随完整贯焦平均质量下降。

### Conclusions

角膜屈光术后光学结构会以机制特异且瞳孔依赖的方式调制非衍射 EDoF IOL 的完整眼效应，不能用简单可加模型描述。以 N0 为内部参照后，B0V12×WFS-like 的小瞳孔增强、B0V12/C0V12×RAD-like 的大瞳孔增强以及 C0V12×HOA-like 的大瞳孔增强均表现出可重复机制信号，但均需与固定焦面和全贯焦质量代价共同解释。结果支持基于角膜光学表型、瞳孔和 IOL 延焦机制的后续分层研究，不支持将机制 surrogate 直接转化为商业 IOL 排名或患者级推荐。

**Keywords:** corneal refractive surgery; extended depth of focus; intraocular lens; through-focus MTF; spherical aberration; pupil; optical modeling

---

# Introduction

角膜屈光手术后的白内障管理正在从相对少见的特殊情境逐渐转变为常见的屈光性白内障问题。随着接受 LASIK、PRK 等手术的人群进入白内障高发年龄，术后人工晶状体（IOL）度数预测、视觉质量和老视矫正策略将越来越重要。现代总角膜屈光力、光线追迹、术中像差测量和专用 IOL 计算公式已经改善了屈光预测，但既往角膜屈光手术仍会改变角膜曲率关系、非球面性和高阶像差，使 IOL 选择不再只是“把球镜度数算准”的问题。[1]

这种挑战在老视矫正 IOL 中更加突出。系统综述提示，既往角膜激光手术后植入老视矫正 IOL 可以获得较好的远、中、近视觉和较高眼镜独立性，但眩光、光晕和对比敏感度下降仍需考虑，而且现有研究异质性较高，尚不足以形成简单选择规则。[2]

延伸焦深 IOL 因形成连续有效焦域，被认为可能对部分屈光术后眼具有优势。Fan 等在非衍射波前塑形 EDoF IOL 的前瞻性病例系列中发现，既往近视 LASIK 组获得良好远、中视力，并呈现较平滑的离焦曲线和更大主观焦深。[3] Micheletti 和 Hall 在角膜球差较高的 post-myopic LASIK/PRK 眼中也报告了良好视觉结果和较高满意度。[4] 这些结果提示较高术后球差并不必然排除非衍射 EDoF IOL，但也不能据此推断所有术后角膜或所有 EDoF 机制均具有相同适配性。

计算光学研究进一步提示瞳孔和角膜像差会改变 EDoF IOL 与术后角膜的相互作用。Lago、de Castro 和 Marcos 在 post-LASIK 伪晶状体模型中观察到，3 mm瞳孔下 EDoF 焦深优势较明显，而5 mm瞳孔下差异缩小；模型同时显示球差、彗差及瞳孔大小都会改变远焦质量和贯焦表现。[5] 因而，仅用“是否做过 LASIK”或单一球差值概括屈光术后眼，可能不足以预测 EDoF IOL 的完整眼表现。

现有研究仍较少把角膜本身视为具有不同延焦结构的光学子系统，系统研究其与不同非衍射 EDoF 机制的耦合。连续非球面角膜 EDoF 设计和中央近用型径向多焦角膜已经主动改变焦轴能量分配；若再植入具有波前塑形、径向屈光力调制或高阶球差调制特征的 EDoF IOL，两个延焦机制可能协同、相互抵消，也可能产生依赖瞳孔和基础眼结构的质量再分配。

本研究因此建立一个冻结、可追溯的计算光学矩阵。为避免把 IOL residual 自身的瞳孔依赖误认为术后角膜耦合，我们加入统一未治疗角膜 N0 作为内部参照，并将三个术后角膜原型统一到临床处方语义：镜片平面−3.00 D、12 mm顶点距，对应角膜平面−2.8957529 D。研究主要回答：同一 EDoF 机制在术后角膜中的 `EDOF−MONO` 效应是否相对于 N0 系统改变；这种改变是否随瞳孔和基础眼变化；以及焦深增加与固定焦面/完整贯焦质量之间如何交换。

# Methods

## Study design and model eyes

本研究为确定性计算光学研究。所有主分析均在单色555 nm、轴上0°视场、角膜/瞳孔/IOL共轴条件下进行。MVP 不加入角膜治疗区偏心、IOL tilt/decentration、微单视附加离焦、多色效应或患者特异优化。

基础眼包括 `LB_AL2395` 和 `ATC_M3_AL24477`。前者基于 Liou–Brennan 模型眼，眼轴23.950 mm；后者基于 Atchison Model 1近视眼框架，眼轴24.477 mm。ATC 的近视屈光状态只属于基础眼表型，不作为角膜手术处方的第二次输入。

## Corneal conditions

N0 为未治疗角膜内部参照，而非临床“正常眼”分布。两个基础眼使用同一冻结角膜 scaffold：前表面半径7.77 mm、conic −0.18，后表面半径6.40 mm、conic −0.60，中央厚度0.50 mm，角膜折射率1.376。

术后处方使用 `TASK014_SPECTACLE_M3_VERTEX12_v1`。镜片平面球镜−3.00 D、顶点距12.00 mm，角膜平面等效治疗量按

\[
F_c=\frac{F_s}{1-dF_s}
\]

换算为−2.895752895753 D。

A0V12 表示传统近视术后准单焦原型，6 mm口径 `ΔC4⁰≈+0.13 μm`；B0V12 使用冻结的 B0.20 连续非球面角膜 EDoF 机制，`ΔC4⁰≈+0.20 μm`；C0V12 为中央近用型径向多焦角膜，中央区3.00 mm、处方 ADD +1.75 D、光学区6.50 mm、过渡区0.75 mm。

## IOL carrier and EDoF surrogates

所有平台使用统一 controlled carrier scaffold：IOL折射率1.460、周围介质1.336、中央厚度1.000 mm、光学直径6.000 mm、对称双凸弯曲。基础球差通过 `STD_IOL_EYE_2024` 进行 power-specific conic 校准；WFS-like、RAD-like 和 HOA-like 在标准眼 EPD6 下的基础球差目标分别为−0.20±0.01 μm、−0.27±0.01 μm和0.00±0.01 μm。

每个 Base×Cornea×Platform 独立求 actual-eye power 和标准眼 `Q(P)`。三类 EDoF residual 作为冻结 Grid Sag resources：WFS-like 为波前塑形型，RAD-like 为连续径向屈光力调制型，HOA-like 为中央高阶球差调制型。对同一 matched pair，MONO 与 EDoF 的基础 P/R/Q、厚度、材料和位置完全相同；EDoF 唯一增加相应 residual，加入 residual 后不重新优化 carrier。

所有24个 exact carriers 均通过 schema-v2 validation。规范性 low-order gate 位于 `STD_IOL_EYE_2024` EPD6 imported-residual readback；actual-eye MONO/EDOF EPD5 ray health 必须通过。实际眼 SSAG Mode-0 piston/defocus 仅作诊断，不参与 numerical pass/fail。

## Factorial matrix and optical acquisition

最终矩阵为：

```text
2 Base × 4 Cornea × 3 Platform × 2 Optic state × 2 Pupil
= 96 configurations
= 48 matched pairs
```

生产 MTF 使用 `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`，OpticStudio MFE `MTFA Grid=1`，sampling=128。每个 matched pair 使用 residual-free MONO EFFL 建立共同0–60 cycles/degree角频率尺度，EDoF-state EFFL 不重新定义频率轴。

贯焦范围为+0.50至−3.00 D，步长−0.25 D，共15个平面。MTFa 定义为0–60 cpd MTF 的梯形积分平均。distance peak 在−0.50至+0.50 D搜索；若最大值位于边界则标记 censored。DOF50 以 distance-peak MTFa 的50%为阈值，寻找包含峰值的连续区间并线性插值 crossing；若 crossing 超出冻结窗口则 width 作为 lower bound。完整窗口平均定义为

\[
TF\_MTFa\_mean=\frac{1}{3.5D}\int_{-3.00}^{+0.50}MTFa(F)\,dF.
\]

完整眼 Zernike n=3–6 readback 提取 C4⁰、C6⁰和 HOA RMS。

## Paired and N0-referenced analysis

主要 paired effect 为

\[
\Delta Y=Y_{EDOF}-Y_{MONO}.
\]

主要 outcomes 包括 ΔDOF50、Δdistance-peak MTFa、ΔMTFa@0D、ΔTF MTFa mean、ΔC4⁰、ΔC6⁰、ΔHOA RMS 和 ΔF residual。

术后角膜对 EDoF 机制的净调制定义为

\[
Interaction_{postop-N0}=\Delta Y_{postop}-\Delta Y_{N0},
\]

在相同 Base×Platform×Pupil 内比较 A0V12、B0V12、C0V12 与 N0。DOF censoring 使用区间代数传播。48个 matched pairs 是完整确定性 factorial matrix，因此报告 effect magnitude、direction consistency、N0-referenced interactions 和 censor-aware interpretation，而不把它们当作随机临床样本进行传统显著性推断。

## Provenance and figure supplement

N0 来自 TASK-013 正式 run `task013-183dcffcd1da4f1cb1a219d9eedb39db`；A0V12/B0V12/C0V12 来自 TASK-014 正式 run `task014-e270a185207543149c21da83202c4b73`。两者均通过独立 scientific review。TASK-015 离线整合确定性重建96配置、1440行贯焦数据、48个 paired effects 和288个 outcome-specific N0-referenced interactions。

完整 figure supplement 已归档，包括48张逐 pair raw through-focus figures和24张 summary figures，共72张。所有 raw figures 同时展示 MONO/EDOF 的15-plane MTFa，并保留 DOF50 与 peak censoring 标记。

# Results

## Data completeness and overall trade-off

96/96配置完成，无失败。最终共有1440个贯焦采样点和48个 matched pairs。43个 DOF50 effects 为 exact，5个为 lower bound；10个 pair 的 distance peak 位于预注册搜索窗边界。

35/48 pair 的 `ΔDOF50` 为正、13/48为负。`ΔTF MTFa mean` 在48/48 pair均为负，`ΔMTFa@0D` 在47/48为负。唯一0 D正值为 `ATC×N0×RAD-like×EPD5`（+0.0184），但其 `ΔTF MTFa mean` 仍为−0.00731。因此整体结果支持焦深扩展—光学质量再分配，而非跨指标一致改善。

## Cornea × Platform descriptive matrix

| Cornea × Platform | ΔDOF50 mean, D | ΔMTFa@0D mean | ΔTF MTFa mean | DOF方向（+/−） |
| --- | ---: | ---: | ---: | ---: |
| N0 × WFS-like | +0.061 | -0.117 | -0.0094 | 2/2 |
| N0 × RAD-like | +0.041 | -0.147 | -0.0117 | 2/2 |
| N0 × HOA-like | +0.221 | -0.328 | -0.0542 | 2/2 |
| A0V12 × WFS-like | +0.139 | -0.120 | -0.0106 | 4/0 |
| A0V12 × RAD-like | +0.078 | -0.167 | -0.0146 | 3/1 |
| A0V12 × HOA-like | +0.193 | -0.321 | -0.0525 | 2/2 |
| B0V12 × WFS-like | ≥+0.224 | -0.138 | -0.0113 | 3/1 |
| B0V12 × RAD-like | +0.196 | -0.166 | -0.0152 | 4/0 |
| B0V12 × HOA-like | +0.241 | -0.288 | -0.0507 | 2/2 |
| C0V12 × WFS-like | +0.124 | -0.118 | -0.0081 | 4/0 |
| C0V12 × RAD-like | ≥+0.242 | -0.216 | -0.0091 | 4/0 |
| C0V12 × HOA-like | ≥+0.432 | -0.346 | -0.0553 | 3/1 |

这些绝对 paired effects 包含 residual 自身的基线行为，因此术后 coupling 以 N0-referenced interaction 为主要解释。

## N0-referenced coupling

N0 显示 WFS-like、RAD-like 和 HOA-like 均具有自身的瞳孔依赖，尤其 HOA-like 在 EPD3可扩展焦深而 EPD5可转为负效应。因此，大的术后 `EDOF−MONO` 不能自动解释为角膜与 IOL 的协同。

A0V12 对三类机制的调制总体较温和。WFS-like 在四个 strata 相对 N0 均为正向 DOF interaction（+0.030至+0.146 D）；RAD-like 和 HOA-like 在 EPD3相对 N0减弱，到 EPD5转为增强。

B0V12×WFS-like 在 EPD3 显示两基础眼一致的强正 interaction，均为 lower bound：LB `≥+0.266 D`，ATC `≥+0.260 D`；EPD5 仍为正，但减小至+0.073和+0.054 D。B0V12×RAD-like 的主要增强转而位于 EPD5（+0.275和+0.307 D），而 EPD3 接近零并有基础眼间符号差异。B0V12×HOA-like 相对 N0整体接近零。

C0V12×RAD-like 在 EPD3同样接近零且基础眼间符号不一致，但 EPD5 两基础眼均显示强正 interaction并为 lower bound：LB `≥+0.379 D`，ATC `≥+0.471 D`。C0V12×HOA-like 在 EPD3 相对 N0减弱，而 EPD5 强增强（LB +0.246 D；ATC `≥+0.689 D`）。C0V12×WFS-like 的 EPD3 interaction 接近零，EPD5 为中等正向。

## Wavefront mechanism readout

三类 surrogate 在完整眼中保留不同的 C4⁰/C6⁰机制方向：WFS-like 在 EPD3主要为正 ΔC4⁰、负 ΔC6⁰；RAD-like 在 EPD3以负 ΔC6⁰为主；HOA-like 在 EPD3保持负 ΔC4⁰、正 ΔC6⁰的反号组合。这些平台特异签名在两种基础眼中总体连续，包括超出历史 carrier-power coverage 后经 exact-carrier validation 接受的低功率条件，未见机制断裂。

# Discussion

## Principal finding: coupling is not simple addition

本研究最重要的发现是，术后角膜并不提供一个可独立相加的固定“EDoF增益”。同一 residual 在 N0 中已经表现出瞳孔依赖；术后角膜进一步改变这种基线响应，而且调制方向和幅度取决于平台、瞳孔和基础眼。因而，更严格的 coupling 概念应是 postop-minus-N0 interaction，而不是术后条件下单独观察到较大的 `EDOF−MONO`。

## Role of the untreated reference

加入 N0 后，可以区分 residual 固有行为与术后角膜净调制。例如 HOA-like 在 N0 的3 mm条件本身即可产生显著焦深扩展，而5 mm可转为负效应。若无 N0，这种 intrinsic pupil dependence 容易被术后角膜条件中的绝对值放大或误归因。N0 因此提高了对“非简单加和”的判定门槛。

## Vertex correction and clinical prescription semantics

最终术后角膜统一使用镜片平面−3.00 D、12 mm顶点距，对应角膜平面−2.8957529 D，而不是直接将−3.00 D视为角膜平面 treatment。该修订约0.104 D，幅度有限但改善了模型与临床眼镜处方的语义一致性，也避免 ATC 基础眼的近视表型被再次叠加到手术处方。旧 direct-cornea A0/B0/C0 Run72 因此保留为工程历史，不作为最终投稿主结果。

## Pupil-dependent mechanism interactions

B0V12×WFS-like 的相对增强主要位于3 mm瞳孔，这与既往 post-LASIK 计算研究和非衍射波前塑形 IOL 光学台研究所显示的小瞳孔优势在方向上相容。[5,6] 本研究不能把 B0V12 surrogate 等同于具体 presbyopic ablation，也不能把 WFS-like 等同于具体商业 IOL；但结果提示，当角膜本身具有连续延焦结构时，有效瞳孔可能决定两个延焦机制之间的耦合强度。

C0V12×RAD-like 和 C0V12×HOA-like 的主要增强位于5 mm。C0V12 与 RAD-like 均含明显径向空间结构，因此一个可检验假设是，较大瞳孔下径向功率/相位分配形成更宽的有效贯焦包络。C0V12×HOA-like 的 EPD5增强与 EPD3减弱则进一步说明，高阶像差型延焦不能用“球差越多焦深越大”的单变量关系概括。

## Depth-of-focus gain is a trade-off

48/48 pair 的 `ΔTF MTFa mean` 均下降，是本研究最稳定的跨条件结果。即使 DOF50 明显增加，也必须与固定焦面和全窗质量变化共同解释。尤其 B0V12-WFS EPD3、C0V12-RAD EPD5 和 C0V12-HOA EPD5 等强 interaction，不应单独根据 DOF50 宣称总体光学优势。完整 raw through-focus curves 因而作为补充材料全部保留，而不是只展示支持主叙事的代表图。

## Clinical interpretation

现有临床资料提示，经过筛选的 post-myopic LASIK/PRK 眼可从非衍射波前塑形 EDoF IOL 获得良好远中视和较宽主观焦深。[3,4] 本研究的价值不是建立商业产品排名，而是提出未来真实眼分层时应考虑的变量：角膜贯焦形态、瞳孔、C4⁰/C6⁰及更完整 HOA 结构，可能比单一“既往LASIK史”或单一Q值更能解释完整眼 EDoF 响应。

## Limitations

本研究为确定性光学模拟而非临床样本研究。两个基础眼、一个 N0 和三个术后角膜原型用于机制覆盖，不代表真实人群分布；48个 matched pairs 不是随机临床样本。WFS-like、RAD-like 和 HOA-like 是机制 surrogate，不能与任一商业 IOL 一一等同。

5个 DOF50 effects 为 lower bound，10个 distance-peak metrics 受搜索窗边界限制；冻结窗口没有因结果而事后扩大，因此部分强 interaction 只能解释为下界。MVP 未包含治疗区偏心/倾斜、IOL偏心/倾斜、多色效应、真实角膜不规则像差、上皮重塑、泪膜和个体 pupil dynamics。N0 是统一未治疗 scaffold，不等价于临床正常人群分布，因此 postop-minus-N0 interaction 应理解为受控模型中的净光学调制，而非临床平均治疗效应。

# Conclusion

以未治疗 N0 为内部参照后，角膜屈光术后背景对非衍射 EDoF IOL 的作用表现为机制特异、瞳孔依赖的完整眼耦合，而非固定可加效应。B0V12×WFS-like 主要表现为小瞳孔下的 DOF 增强；B0V12×RAD-like、C0V12×RAD-like 和 C0V12×HOA-like 的主要增强位于5 mm瞳孔。与此同时，48/48 pair 的全贯焦平均 MTFa下降，说明焦深扩展需要与光学质量再分配共同解释。当前结果支持机制分层和后续可检验假设，但不支持将4×3矩阵直接转化为商业 IOL 排名或患者级临床推荐。

# Figures and supplementary material

正文计划使用5张组合主图：ΔDOF50 heatmaps、ΔMTFa@0D heatmaps、延焦—质量 trade-off、代表性 N0-referenced raw through-focus curves 和 whole-eye HOA mechanism map。

完整补充材料保留：

- 48张逐 pair raw through-focus figures；
- 24张 summary figures；
- Supplementary Table S1：48-pair完整结果；
- Supplementary Table S2：N0-referenced postoperative interactions。

# References

1. Ting DSJ, Gatinel D, Ang M. Cataract surgery after corneal refractive surgery: preoperative considerations and management. *Curr Opin Ophthalmol*. 2024;35(1):4-10. doi:10.1097/ICU.0000000000001006.
2. Sun Y, Hong Y, Rong X, Ji Y. Presbyopia-Correcting Intraocular Lenses Implantation in Eyes After Corneal Refractive Laser Surgery: A Meta-Analysis and Systematic Review. *Front Med (Lausanne)*. 2022;9:834805. doi:10.3389/fmed.2022.834805.
3. Fan W, Zhu M, Zhang G. Visual outcomes and spectacle independence of a non-diffractive wavefront-shaping intraocular lens in post-LASIK patients. *Front Med (Lausanne)*. 2025;12:1509889. doi:10.3389/fmed.2025.1509889.
4. Micheletti JM, Hall B. Satisfaction and Visual Outcomes with a Non-Diffractive EDOF IOL in Post-Myopic LASIK and PRK Patients with High Corneal Spherical Aberration. *Clin Ophthalmol*. 2026;20:566800. doi:10.2147/OPTH.S566800.
5. Lago CM, de Castro A, Marcos S. Computational simulation of the optical performance of an EDOF intraocular lens in post-LASIK eyes. *J Cataract Refract Surg*. 2023;49(11):1153-1159. doi:10.1097/J.JCRS.0000000000001260.
6. Garzón N, Gómez-Pedrero JA, Albarrán-Diego C, et al. Optical power profiles and aberrations of a non-diffractive wavefront-shaping extended depth of focus intraocular lens. *Graefes Arch Clin Exp Ophthalmol*. 2024;262(9):2897-2906. doi:10.1007/s00417-024-06469-y.
