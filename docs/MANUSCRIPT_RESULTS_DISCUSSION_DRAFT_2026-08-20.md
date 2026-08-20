# 论文草稿模块：Results 与 Discussion

> 状态：manuscript draft，供后续整合；不是新的 scientific lock。  
> 数据来源：仅使用冻结的 TASK-012 结构化 evidence；Discussion 中的外部研究单独标记。  
> 所有模拟效应均定义为 `EDOF − MONO`。  
> WFS-like / RAD-like / HOA-like 是机制 surrogate，不对应商业产品排名。

## Results

### 1. 数据完整性与分析矩阵

正式 Run72 包含72个配置、36个严格匹配的 MONO–EDOF pair 和1080个贯焦采样点。TASK-012 从 config-level evidence 独立重建36个 paired effects，并复算0 D MTFa和完整预注册贯焦窗口内的平均 MTFa。所有重建检查均通过。

36个 pair 中，31个 DOF50 effect 为精确值，5个为 lower bound；另有8个 pair 的 distance-peak 指标达到预注册 peak-search window 边界。因此，本文对 DOF50 lower-bound 和 peak-window-conditioned 结果均保留边界属性，不进行伪精确排序。

### 2. 总体延焦—质量交换

当前冻结模型显示出一致的延焦—质量交换，而不是单一方向的“全指标改善”。36个 pair 中，30个 `ΔDOF50` 为正、6个为负；但 `ΔMTFa@0D` 在36/36 pair 中均为负，完整预注册贯焦窗口内的 `ΔTF MTFa mean` 也在36/36 pair 中均为负。窗口内观察到的 distance-peak MTFa 同样全部下降，其中8个 pair 的 peak 指标受搜索窗口边界限制。

因此，EDOF residual 通常通过重新分配焦轴方向上的光学质量来扩展 DOF50，而不是在保留 matched MONO 固定焦面质量的同时简单增加焦深。

### 3. 3×3 Cornea × Platform 矩阵

四个 Base×Pupil strata 的描述性均值如下。带 `≥` 的 DOF50 为 lower-bound mean；这些均值只用于描述当前确定性矩阵，不能视为临床总体参数。

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

这些 cell mean 隐藏了重要的 pupil/base 异质性，因此主解释以分层 interaction 为优先，而不是按均值直接排名。

### 4. B0 与 WFS-like：小瞳孔特异的相对 DOF coupling

B0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences 在 EPD3 为正，在 EPD5 反转：LB EPD3 `≥+0.157 D`、ATC EPD3 `≥+0.195 D`，而 LB EPD5 为 `-0.210 D`、ATC EPD5 为 `-0.097 D`。与 HOA-like 比较也出现相同方向：EPD3 为 `≥+0.152 D` 和 `≥+0.146 D`，EPD5 为 `-0.093 D` 和 `-0.032 D`。

B0×WFS-like 的 pair-level DOF50 在 EPD3 达到 `≥+0.462 D`（LB）和 `≥+0.432 D`（ATC），而 EPD5 仅为 `+0.034 D`（LB）和 `-0.021 D`（ATC）。这表明其主要耦合信号是**EPD3-specific**，不能概括为跨瞳孔稳定的优势。

该 DOF coupling 也不伴随固定焦面质量优势。B0 条件下 WFS 相对 RAD 的 `ΔMTFa@0D` interaction 在 EPD3 约为 -0.044 至 -0.048，提示额外的 DOF 增益仍以0 D MTFa下降为代价。

### 5. C0 与 RAD-like：跨基础眼方向较稳定的 DOF-oriented coupling

C0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences 在四个 strata 均为负：LB EPD3 `-0.066 D`、ATC EPD3 `-0.073 D`、LB EPD5 `≤-0.274 D`、ATC EPD5 `≤-0.170 D`。由于 contrast 定义为 WFS−RAD，这表示 C0 对 RAD-like 的相对 DOF coupling 在两种基础眼和两种瞳孔中均高于 WFS-like，并且 EPD5 更明显。

C0×RAD-like 的 pair-level DOF50 在四个 strata 全部正向：LB EPD3 `+0.166 D`、ATC EPD3 `+0.213 D`，LB EPD5 `≥+0.302 D`、ATC EPD5 `≥+0.290 D`。

但固定焦面质量显示相反的权衡方向。C0 条件下 WFS-vs-RAD 的 `ΔMTFa@0D` interaction 在四个 strata 均为正（约 +0.012 至 +0.092），说明 WFS-like 相对保留更多0 D MTFa，而 RAD-like 以更大的固定焦面质量代价换取更多 DOF。因此该模式应描述为**DOF-oriented trade-off**，而非总体光学质量的无条件优势。

### 6. HOA-like：最大的质量再分配与最强的 pupil/base dependence

HOA-like 在 EPD3 可产生本矩阵中最大的 DOF50 扩展：A0约 +0.63～+0.66 D，B0约 +0.73 D，C0约 +0.66～+0.68 D。然而 A0 和 B0 到 EPD5 后均转为负向 DOF effect。C0×HOA-like 的 EPD5 又显示明显基础眼分离：LB 为 `-0.097 D`，ATC 为 `≥+0.392 D`。

相应地，HOA-like 的0 D及全贯焦平均 MTFa损失也最大。A0/B0/C0 三个 cell 的 `ΔMTFa@0D` mean 分别约 -0.320、-0.287 和 -0.345，`ΔTF MTFa mean` 分别约 -0.052、-0.051 和 -0.056。其主要特征因此是强烈的焦轴质量再分配，而不是跨条件稳定的最大延焦。

### 7. 高阶像差机制读数

三类 surrogate 形成不同的 C40/C60 瞳孔签名。WFS-like 在 EPD3 主要表现为约 `+0.032 μm` 的 ΔC40 与约 `-0.017 μm` 的 ΔC60，EPD5 时两者幅度均明显减小。RAD-like 在 EPD3 主要表现为较小正 ΔC40 与约 `-0.09 μm` 的 ΔC60，而 EPD5 转为约 `-0.129 μm` 的 ΔC40 与 `+0.063 μm` 的 ΔC60。HOA-like 在 EPD3 则约为 `-0.067～-0.070 μm` 的 ΔC40 与 `+0.171～+0.175 μm` 的 ΔC60，EPD5 幅度显著降低。

特别是 RAD-like 在 EPD5 的 net HOA RMS 对角膜原型高度敏感：B0约为 -0.092～-0.100 μm，C0约为 +0.127 μm，而 A0接近零。这一方向差异支持 Cornea×Platform 之间存在非简单加和的机制耦合。

## Discussion

### 1. 主要发现：角膜与 EDoF 机制的关系不是简单相加

本研究的核心结果不是识别一个跨所有条件“最好”的 EDoF surrogate，而是证明角膜原型、IOL 延焦机制、瞳孔和基础眼共同决定延焦—质量交换的形态。B0×WFS-like 的 relative DOF coupling 随瞳孔由 EPD3 到 EPD5 发生方向反转；C0×RAD-like 的 DOF coupling 则在两种基础眼和两种瞳孔中保持较一致方向；HOA-like 的效应幅度最大，但同时具有最强的瞳孔和基础眼依赖。

这种结果支持一个更合适的研究框架：屈光术后角膜不只是需要被“补偿”的静态像差背景，而是会与 EDoF IOL 的具体光学机制共同塑造整个眼的贯焦响应。因此，对术后白内障眼的 EDoF 评价不能仅依据 IOL 本身的标称焦深，也不能只依据角膜球差的单一数值。

### 2. WFS-like 的瞳孔依赖与既往 post-LASIK 研究具有方向一致性

外部研究为这种瞳孔依赖提供了重要背景。Lago、de Castro 和 Marcos 对 post-LASIK 眼进行计算模拟时发现，非衍射波前塑形 EDoF IOL 的焦深优势在较小瞳孔下更突出，而较大瞳孔时 EDoF 与单焦点方案的差异明显缩小。Garzón 等的光学台研究也显示，波前塑形非衍射 EDoF IOL 的光学质量在3 mm瞳孔优于较大瞳孔，并证明其功率和球差分布在中央光学区具有复杂空间结构。

这些外部结果不能直接验证本研究的 B0 surrogate，但与 B0×WFS-like 的 EPD3-specific coupling 在方向上相容。更重要的是，本研究进一步提示：当角膜本身已经被设计成具有延焦特征时，瞳孔改变的不是单独一个光学元件的性能，而可能改变两个延焦机制之间的相互作用方向。

### 3. 普通近视 LASIK/PRK 后使用非衍射 EDoF 的临床可行性正在得到支持，但不能外推为 B0/C0 临床推荐

已有临床资料显示，在经过筛选的普通近视 LASIK/PRK 术后角膜中，非衍射波前塑形 EDoF IOL 可以获得较好的远中视力和较宽的主观焦深。Fan、Zhu 和 Zhang 的前瞻性研究比较了 post-LASIK 与未行 LASIK 的眼，post-LASIK 组表现出较平滑的离焦曲线和更大的主观 DOF；作者讨论了角膜球差和术后角膜形态对焦深的潜在贡献。Micheletti 和 Hall 在高角膜球差的 post-myopic LASIK/PRK 眼中也报告了良好的视觉结果和较高满意度。

这些证据支持“屈光术后角膜并不自动排除非衍射 EDoF IOL”的临床可行性，但它们主要研究常规近视 LASIK/PRK 后角膜。当前目标性检索未发现与本研究 B0 所代表的角膜 EDoF/presbyopic-ablation 原型，或 C0 所代表的中央近用径向多焦角膜，直接对应且质量足够高的非衍射 EDoF IOL 临床系列。因此，B0×WFS-like 和 C0×RAD-like 的结果应被表述为**机制生成与可检验假设**，而不是临床选片建议。

### 4. C0×RAD-like 提示空间功率结构之间可能存在“匹配”，但必须与距离质量代价同时解释

C0×RAD-like 是当前矩阵中方向较稳定的 DOF coupling 信号之一，尤其在 EPD5 更明显。由于 C0 和 RAD-like 都包含显著的径向空间结构，一个合理的机制假设是，两者的径向功率/相位分配可在完整眼系统中形成更宽的有效贯焦包络。

但 formal evidence 同时显示，C0×RAD-like 的0 D MTFa损失大于 C0×WFS-like，且 C0×RAD-like 的 EPD5 HOA RMS 由 A0/B0 中的接近零或下降转为明显增加。这意味着“径向机制匹配”若存在，也不是简单的像差抵消，而可能是以更强的焦轴能量重分配换取焦深。因此，未来的验证重点应同时观察 DOF、固定焦面质量和贯焦曲线形态，而不是只比较 DOF50 width。

### 5. HOA-like 结果强调球差/高阶像差延焦的双刃剑性质

利用球差或高阶像差扩展焦深具有明确的物理基础，但本研究显示该路径的鲁棒性较低：EPD3 可以产生非常大的焦深扩展，而 EPD5 可完全反转；C0×HOA-like×EPD5 甚至在两种基础眼间发生方向分离。与此同时，HOA-like 的固定焦面和全贯焦 MTFa损失最大。

这与既往关于球差能够扩展焦深、但其效应高度依赖瞳孔和基础光学状态的研究框架一致。它也说明术后角膜的 HOA 不应简单地被分类为“有利于 EDoF”或“不利于 EDoF”；同一 HOA 机制在不同瞳孔和不同眼模型中可能产生相反的有效 DOF 结果。

### 6. 临床意义：应从“产品选择”转向“完整眼机制匹配”

本研究尚不足以给出临床产品排名，但为未来屈光术后白内障 IOL 选择提出了可操作的研究假设。一个更有信息量的术前框架可能需要同时考虑角膜贯焦特征、瞳孔、C40/C60及更完整 HOA 结构，而不只是既往屈光手术史或单一 Q 值。

尤其值得进一步验证的两个方向是：第一，具有角膜 EDoF 特征的眼是否存在对中央波前塑形型 IOL 的小瞳孔特异协同；第二，中央近用/径向多焦角膜是否可能与某些径向功率调制型 IOL 形成相对稳定但伴随距离质量代价的 coupling。上述两点在本研究中均为机制假设，而非临床处方。

### 7. 局限性

本研究是确定性光学模拟而非临床样本研究。两种基础眼和三个角膜原型用于机制覆盖，不代表真实人群分布；结果不宜使用普通随机样本显著性推断。WFS-like、RAD-like 和 HOA-like 是机制 surrogate，不能与任一商业 IOL 一一等同。DOF50 有5个 lower-bound pair，distance-peak 有8个 window-conditioned pair；预注册窗口没有因这些结果而事后扩大。

此外，MVP 中角膜屈光手术居中，未加入角膜消融区偏心/倾斜；IOL 偏心和倾斜也未纳入当前矩阵。真实术后角膜还存在不规则像差、上皮重塑、泪膜和个体 pupil dynamics 等因素。本研究因此更适合用于定义下一步机制实验和临床分层变量，而不是直接预测单个患者结果。

## Conclusion

角膜屈光术后眼中，非衍射 EDoF IOL 的光学效应取决于角膜原型、IOL 延焦机制、瞳孔和基础眼之间的耦合。当前模型中，B0×WFS-like 显示小瞳孔特异的相对 DOF coupling，C0×RAD-like 显示较稳定的 DOF-oriented coupling，而 HOA-like 产生最强但最不稳定的焦轴质量再分配。所有36个 pair 的0 D和全贯焦平均 MTFa均相对 matched MONO下降，提示焦深扩展应始终与光学质量代价共同解释。当前结果支持机制分层和后续可检验假设，但不支持将3×3矩阵直接转化为商业 IOL 排名或临床推荐。

## 外部文献锚点（Discussion only）

1. Lago CM, de Castro A, Marcos S. Computational simulation of the optical performance of an EDOF intraocular lens in post-LASIK eyes. *J Cataract Refract Surg*. 2023;49(11):1153-1159. doi:10.1097/J.JCRS.0000000000001260.
2. Fan W, Zhu M, Zhang G. Visual outcomes and spectacle independence of a non-diffractive wavefront-shaping intraocular lens in post-LASIK patients. *Front Med (Lausanne)*. 2025;12:1509889. doi:10.3389/fmed.2025.1509889.
3. Micheletti JM, Hall B. Satisfaction and Visual Outcomes with a Non-Diffractive EDOF IOL in Post-Myopic LASIK and PRK Patients with High Corneal Spherical Aberration. *Clin Ophthalmol*. 2026;20:566800. doi:10.2147/OPTH.S566800.
4. Garzón N, Gómez-Pedrero JA, Albarrán-Diego C, et al. Optical power profiles and aberrations of a non-diffractive wavefront-shaping extended depth of focus intraocular lens. *Graefes Arch Clin Exp Ophthalmol*. 2024;262(9):2897-2906. doi:10.1007/s00417-024-06469-y.
5. Schmid R, Borkenstein AF. Optical Bench Evaluation of the Latest Refractive Enhanced Depth of Focus Intraocular Lens. *Clin Ophthalmol*. 2024;18:1921-1932. doi:10.2147/OPTH.S469849.
