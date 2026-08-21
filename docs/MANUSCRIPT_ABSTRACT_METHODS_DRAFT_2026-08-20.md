# 论文草稿模块：Structured Abstract 与 Methods

> 状态：manuscript draft；不建立新的 scientific lock。  
> 投稿主分析来源：已通过科学审核的 TASK-013、TASK-014 与 TASK-015 evidence。  
> 所有模拟效应均定义为 `EDOF − MONO`。  
> WFS-like / RAD-like / HOA-like 为机制 surrogate，不对应商业产品排名。

## 拟题

**角膜屈光术后代表性光学表型与非衍射延伸焦深人工晶状体机制的耦合：基于未治疗参照、双模型眼和双瞳孔的计算光学研究**

英文工作标题：

**Coupling Between Representative Post-Refractive Corneal Optical Phenotypes and Non-Diffractive Extended-Depth-of-Focus IOL Mechanisms: A Computational Optical Study With an Untreated Corneal Reference Across Two Model Eyes and Two Pupil Sizes**

---

## Structured Abstract

### Purpose

评估代表性角膜屈光术后光学表型是否会改变不同非衍射延伸焦深（EDoF）人工晶状体机制在完整眼中的作用，并以未治疗角膜（N0）为内部参照，描述这种耦合如何随瞳孔和基础模型眼改变焦深、固定焦面成像质量、贯焦质量及全眼高阶像差。

### Methods

建立两个轴上、共轴、单色的人工晶状体模型眼：Liou–Brennan 型 `LB_AL2395`（眼轴23.950 mm）和 Atchison 近视型 `ATC_M3_AL24477`（代表约−3 D近视表型，眼轴24.477 mm）。角膜条件包括未治疗参照 N0，以及三个顶点距规范化术后原型 A0V12、B0V12 和 C0V12。术后处方统一定义为镜片平面−3.00 D、顶点距12 mm，对应角膜平面治疗量−2.8957529 D。A0V12 为正球差增加型准单焦术后角膜，B0V12 为冻结的连续非球面角膜 EDoF 原型，C0V12 为中央3.0 mm近用区、处方附加+1.75 D的径向多焦角膜。

三类 IOL 机制 surrogate 分别为波前塑形型（WFS-like）、连续径向屈光力调制型（RAD-like）和中央高阶球差调制型（HOA-like）。每个 Base×Cornea×Platform 独立建立 physical carrier；EDoF 与 matched MONO 使用完全相同的基础光焦度、曲率、conic、厚度、材料和位置，唯一设计差异为冻结 residual。最终接受矩阵包含24个 physical carriers、48个严格匹配的 MONO–EDoF pairs 和96个配置，并分别在3和5 mm entrance pupil下计算。

生产 MTF 通过 Zemax OpticStudio MFE `MTFA Grid=1` 获取，使用每个 matched pair 的 residual-free MONO EFFL 建立共同0–60 cycles/degree角频率尺度。贯焦范围固定为+0.50至−3.00 D，步长0.25 D，共15个平面。主要 paired outcomes 包括 DOF50 width、0 D MTFa、完整贯焦窗口平均 MTFa、窗口内 distance-peak MTFa以及 C4⁰、C6⁰和 HOA RMS。术后耦合进一步定义为 `(EDOF−MONO)_postop − (EDOF−MONO)_N0`。分析为确定性 factorial / contrast 分析，不把48个 pair视为随机临床样本进行传统显著性检验；DOF50 和 distance-peak censoring 均显式保留和传播。

### Results

96/96配置完成且无失败，共获得1440个贯焦采样点和48个 matched pairs。35/48 pair 的 `ΔDOF50` 为正、13/48为负；43个 DOF50 effect 为精确值，5个为 lower bound，10个 pair 的 distance peak 位于预注册搜索窗边界。`ΔTF MTFa mean` 在48/48 pair中均为负，`ΔMTFa@0D` 在47/48 pair中为负；唯一0 D正值出现在 ATC+N0+RAD-like+EPD5，但其全贯焦平均 MTFa仍下降。

N0-referenced interaction 显示明显的角膜背景×机制×瞳孔依赖。B0V12×WFS-like 在3 mm瞳孔下相对 N0 的 DOF50 增强在两种基础眼均为 lower bound（LB ≥+0.266 D；ATC ≥+0.260 D），5 mm时仍为较小正向增强。B0V12×RAD-like 的主要增强位于5 mm（LB +0.275 D；ATC +0.307 D）。C0V12×RAD-like 在5 mm呈强增强且两种基础眼均为 lower bound（LB ≥+0.379 D；ATC ≥+0.471 D）；C0V12×HOA-like 在5 mm同样明显增强（LB +0.246 D；ATC ≥+0.689 D），而3 mm相对 N0减弱。上述焦深变化均伴随整体贯焦质量下降，提示其本质为焦轴质量再分配而非无代价增益。

### Conclusions

角膜屈光术后光学结构会以机制特异且瞳孔依赖的方式调制非衍射 EDoF IOL 在完整眼中的效应，不能用简单可加模型描述。以 N0 为内部参照后，B0V12×WFS-like 的小瞳孔增强、B0V12/C0V12×RAD-like 的大瞳孔增强以及 C0V12×HOA-like 的大瞳孔增强均表现出可重复的机制信号，但均需与固定焦面和全贯焦质量代价共同解释。结果支持基于角膜光学表型、瞳孔和 IOL 延焦机制的后续分层研究，不支持将机制 surrogate 直接转化为商业 IOL 排名或患者级推荐。

---

# Methods

## 1. Study design

本研究为确定性计算光学研究。最终投稿主矩阵旨在比较未治疗角膜与三个代表性屈光术后角膜背景下，三类非衍射 EDoF IOL 机制的完整眼效应。所有主分析均在单色555 nm、轴上0°视场、角膜/瞳孔/IOL共轴条件下进行。MVP 不加入角膜治疗区偏心、IOL tilt/decentration、微单视附加离焦或患者特异优化，以避免将定位误差和个体化变量混入机制主矩阵。

采用 matched-pair 设计：对于每一个 Base×Cornea×Platform×Pupil 条件，EDoF 配置与 MONO 对照共享同一 physical carrier，唯一设计差异是相应平台的冻结 EDoF residual。因此 `EDOF−MONO` 表示 residual 加入后的完整眼光学效应，而不混入基础 IOL power、conic、位置或材料变化。

## 2. Model eyes

使用两个冻结基础模型眼。

### 2.1 LB_AL2395

`LB_AL2395` 基于 Liou–Brennan 模型眼，眼轴长度固定为23.950 mm，用于代表典型正视眼结构。

### 2.2 ATC_M3_AL24477

`ATC_M3_AL24477` 基于 Atchison Model 1 近视眼框架，选择代表约−3 D近视表型的典型样本，眼轴长度固定为24.477 mm。这里的近视屈光状态属于基础眼表型，不作为角膜手术处方的第二次输入。

两个基础眼共同使用后角膜至 STOP 3.150 mm、后角膜至 IOL 前表面参考位置4.500 mm，房水/玻璃体工程折射率约1.336。IMAGE 顶点由各自眼轴固定，贯焦分析不移动视网膜。

## 3. Corneal conditions

最终主分析包括1个未治疗参照和3个顶点距规范化术后角膜。

### 3.1 N0: native untreated reference

N0 表示未治疗角膜参照，而非“正常眼”标签。两个基础眼使用同一冻结角膜 scaffold：前表面半径7.77 mm、conic −0.18，后表面半径6.40 mm、conic −0.60，中央厚度0.50 mm，角膜折射率1.376。N0 用于定义同一 IOL 机制在无角膜屈光治疗背景下的基线 EDoF−MONO 效应。

### 3.2 顶点距规范化处方

术后角膜处方使用 `TASK014_SPECTACLE_M3_VERTEX12_v1`：镜片平面球镜−3.00 D、柱镜0、顶点距12.00 mm。角膜平面等效治疗量按

\[
F_c=\frac{F_s}{1-dF_s}
\]

换算为−2.895752895753 D。三个术后原型均使用这一距离治疗量；ATC 基础眼的 `source_refraction` 只描述眼型，不再次叠加到手术处方。

### 3.3 A0V12: aberration-altered post-myopic quasi-monofocal cornea

A0V12 表示传统近视角膜屈光术后准单焦原型，并保留约5 mm有效光学区及6 mm口径下约 `+0.13 μm` 的 `ΔC4⁰` 正球差增加。正式构建实测约为+0.1298 μm。

### 3.4 B0V12: continuous aspheric corneal EDoF prototype

B0V12 使用已冻结的 B0.20 连续非球面角膜 EDoF 机制，不依据 IOL 组合表现回调参数。6 mm口径目标 `ΔC4⁰≈+0.20 μm`，正式构建实测约+0.2016 μm。

### 3.5 C0V12: central-near radial multifocal cornea

C0V12 表示中央近用型径向多焦角膜。冻结参数包括3.00 mm中央近用区、+1.75 D处方 ADD、6.50 mm光学区和0.75 mm平滑过渡区。ADD 为处方层面的设计输入，不要求 ray-traced 任一局部位置严格等于+1.75 D局部屈光差。

## 4. IOL carrier scaffold and spherical-aberration calibration

所有平台使用统一 controlled carrier scaffold：IOL折射率1.460、周围介质1.336、中央厚度1.000 mm、光学直径6.000 mm、对称双凸弯曲；主要 conic 位于前表面，后表面 conic 为0。

IOL基础球差通过独立标准眼 `STD_IOL_EYE_2024` 进行 power-specific conic 校准。三平台在标准眼 EPD6 下的基础球差目标为：WFS-like −0.20±0.01 μm，RAD-like −0.27±0.01 μm，HOA-like 0.00±0.01 μm。

对于每个 Base×Cornea×Platform carrier，首先在实际基础眼与角膜中以Q=0求远焦基础 power；随后将该实际 power/geometry 放入标准眼求 power-specific conic `Q(P)`，再返回实际眼复核远焦与球差。不同 power 不共享单一 Q。N0 产生6个 physical carriers，三个术后角膜产生18个 physical carriers，总计24个。

## 5. EDoF mechanism surrogates and exact-carrier validation

研究使用三类机制 surrogate：

- **WFS-like**：波前塑形型 residual；
- **RAD-like**：连续径向屈光力调制型 residual；
- **HOA-like**：中央高阶球差调制型 residual。

三类 residual 均作为版本化 Grid Sag resource 冻结。对同一 matched pair，MONO 与 EDoF 的基础 P/R/Q、中央厚度、材料和 IOL 位置完全相同；EDoF 的唯一设计差异是相应 residual。加入 residual 后不重新优化 carrier。

每个 exact carrier 在首次 EDoF materialization 前执行 schema-v2 residual validation。规范性 low-order hard gate 位于 `STD_IOL_EYE_2024`、EPD6、imported-residual readback，阈值为 `|piston|≤0.010 μm` 和 `|global defocus|≤0.125 D`；实际眼 MONO/EDOF EPD5 ray health 必须通过。实际眼 SSAG Mode-0 piston/defocus 仅作 aperture-limited diagnostic，不参与数值 pass/fail。最终24/24 exact-carrier validations 均通过。历史 carrier-power envelope 仅作为既有验证覆盖分类器；越界 carrier 通过 exact validation 后可进入正式矩阵。

## 6. Final factorial matrix

最终接受矩阵为：

```text
2 Base
× 4 Cornea = N0 / A0V12 / B0V12 / C0V12
× 3 Platform = WFS / RAD / HOA
× 2 Optic state = MONO / EDOF
× 2 Pupil = 3.0 / 5.0 mm
= 96 configurations
= 48 matched MONO–EDoF pairs
```

报告层将 WFS/RAD/HOA 显示为 WFS-like/RAD-like/HOA-like，3.0/5.0 mm显示为 EPD3/EPD5；正式 evidence 原始 ID 不改写。

## 7. MTF acquisition and common angular-frequency scale

主 MTF acquisition 固定为 `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`。生产数据通过 OpticStudio Merit Function Editor 的 `MTFA` operand 获取，设置为 Grid=1、Data Type=0、Wave=1、Field=1，production sampling为128。

为避免 EDoF residual 改变有效焦距后导致 MONO 与 EDoF 使用不同 cycles/degree 坐标，对每个 frozen matched pair 只在 residual-free MONO nominal-distance 状态测量一次 EFFL，并定义共同角频率尺度：

\[
mm/degree = EFL_{MONO}\tan(1^\circ)
\]

随后将共同0–60 cycles/degree网格映射为 cycles/mm 查询频率。同一 pair 的 MONO、EDOF、全部贯焦平面均使用该 pair-specific MONO angular scale；EDoF-state EFFL 不重新定义频率轴。

## 8. Through-focus analysis and optical metrics

贯焦范围固定为+0.50至−3.00 D，步长−0.25 D，共15个 retina-anchored平面。贯焦分析不移动视网膜、IOL位置或重新优化 carrier。

### 8.1 MTFa

在共同0–60 cpd、1 cpd步长网格上定义：

\[
MTFa(F)=\frac{1}{60}\int_0^{60}MTFA(f,F)\,df
\]

并使用梯形积分。固定频率 MTF 同时记录10、20、30、40、50和60 cpd。

### 8.2 Distance peak

在−0.50至+0.50 D范围内取 MTFa 最大点作为 distance peak。若最大值位于±0.50 D边界，则标记 `peak_search_censored=true`；其位置与 peak MTFa 仅作为预注册窗口内观察值解释。

### 8.3 DOF50

以 distance-peak MTFa 的50%为阈值，寻找包含 distance peak 的连续 `MTFa≥50% peak` 区间，并在线性插值相邻0.25 D采样点后计算 far crossing、near crossing和 width。如果 crossing 超出冻结贯焦窗口，则相应 width 作为 lower bound并保留 censor flag。

### 8.4 Through-focus mean MTFa

完整预注册窗口平均值定义为：

\[
TF\_MTFa\_mean=\frac{1}{3.5D}\int_{-3.00}^{+0.50}MTFa(F)\,dF
\]

用于评估延焦机制对整个贯焦窗口总体质量的影响。

### 8.5 Whole-eye higher-order aberrations

完整眼 Zernike n=3–6通过冻结的 `TASK009_MFE_ZERN_HOA_555_v1` readback获取，并提取 C4⁰、C6⁰和 HOA RMS，用于机制解释。

## 9. Acquisition and provenance

N0 数据来自正式 TASK-013 run `task013-183dcffcd1da4f1cb1a219d9eedb39db`：24/24配置完成、360行贯焦数据、12个 matched pairs、6/6 exact validations通过。A0V12/B0V12/C0V12 数据来自正式 TASK-014 run `task014-e270a185207543149c21da83202c4b73`：72/72配置完成、1080行贯焦数据、36个 matched pairs、18/18 exact validations通过。

两组 acquisition 分别通过独立 Web mechanism review，科学状态均为 `PASS_WITH_SCIENTIFIC_CAVEATS`。原始 repo evidence commits 分别为 `38ad14a12a18b1a7a30d259cde644d360442f57b` 和 `6ffb2eaf88e386729aa3965c0f12c9b7ca134081`。TASK-015 在不调用 OpticStudio 的情况下核验源 Git blob identity，并确定性重建96配置、1440行贯焦数据和48个 paired effects。

## 10. Paired and N0-referenced coupling analysis

主要 paired effect 定义为：

\[
\Delta Y=Y_{EDOF}-Y_{MONO}
\]

主要 outcomes 为：

1. `ΔDOF50 width`；
2. `Δdistance-peak MTFa`；
3. `ΔMTFa at 0 D`；
4. `ΔTF MTFa mean`；
5. `ΔC4⁰`；
6. `ΔC6⁰`；
7. `ΔHOA RMS`；
8. `ΔF_residual`。

为了直接回答角膜屈光术后背景是否改变 EDoF 机制，进一步定义：

\[
Interaction_{postop-N0}=\Delta Y_{postop}-\Delta Y_{N0}
\]

比较在同一 Base×Platform×Pupil 内 A0V12、B0V12、C0V12 相对于 N0 的 EDoF−MONO 效应变化。TASK-015 共确定性重建288个 outcome-specific postop-minus-N0 interactions，并汇总为12个 Cornea×Platform coupling cells。

DOF50 censoring通过区间代数传播：最终48个 paired DOF50 effects 中43个为 exact、5个为 lower bound；10个 pair 的 peak-related metrics为预注册搜索窗条件值。基础眼和瞳孔均作为正式因素，不在机制解释前静默平均掉。

本研究的48个 matched pairs是完整、确定性的模拟 factorial matrix，不是从临床总体随机抽取的样本。因此默认报告 effect magnitude、direction consistency、N0-referenced interaction、ranges和censor-aware interpretation，不进行把48个 pair视作独立随机临床样本的传统ANOVA或p-value显著性推断。

## 11. Reproducibility and figures

TASK-015 分析和图形呈现均为纯Python离线流程，不重新调用 OpticStudio。最终结构化产物包括48-pair table、12-cell coupling matrix、analysis evidence和scientific review。

完整 figure supplement 已正式归档于 `docs/evidence/task015/figures/`，commit 为 `bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5`。其中48张 raw figure 一一覆盖全部 Base×Cornea×Platform×Pupil matched pairs，每张同时展示 MONO/EDOF 的15-plane MTFa曲线；另保留24张 summary figures，总计72张。正式 manifest 记录 source through-focus rows=1440、raw=48、summary=24、OpticStudio used=false。48张 raw figures 不因正文选择少量主图而删除或抽样。
