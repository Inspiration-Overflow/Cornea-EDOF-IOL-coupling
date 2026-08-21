# 论文草稿模块：Introduction

> 状态：manuscript draft。  
> 本节使用外部同行评议文献建立临床与光学背景；研究模型、参数和结果定义仍以仓库冻结文档/evidence 为准。

## Introduction

角膜屈光手术后的白内障管理正在从相对少见的特殊情境逐渐转变为常见的屈光性白内障问题。既往综述估计全球已有超过4000万例角膜屈光手术；随着接受 LASIK、PRK 等手术的人群进入白内障高发年龄，术后人工晶状体（IOL）度数预测、视觉质量和老视矫正策略将越来越重要。现代总角膜屈光力、光线追迹、术中像差测量和专用 IOL 计算公式已经改善了屈光预测，但既往角膜屈光手术仍会改变角膜曲率关系、非球面性和高阶像差，使 IOL 选择不再只是“把球镜度数算准”的问题。[1]

这种挑战在老视矫正 IOL 中更加突出。LASIK/PRK 后患者通常已经有过减少眼镜依赖的经历，对白内障术后的视觉范围和屈光结果可能具有较高期待；与此同时，近视角膜消融常增加正球差和其他高阶像差，较大瞳孔下的光学质量尤其可能受影响。对13项研究、445眼的系统综述显示，既往角膜激光手术后植入老视矫正 IOL 可以获得较好的远、中、近视觉和较高眼镜独立性，但眩光、光晕和对比敏感度下降仍是需要考虑的问题，而且现有研究异质性较高，尚不足以形成简单的 IOL 选择规则。[2]

延伸焦深（extended depth of focus, EDoF）IOL 因形成连续的有效焦域，而不是依赖多个离散焦点，被认为可能对部分屈光术后眼具有优势。近年的临床证据支持这种可能性。Fan 等在非衍射波前塑形 EDoF IOL 的前瞻性病例系列中发现，既往近视 LASIK 组获得良好的远、中视力，并呈现较平滑的离焦曲线和更大的主观焦深。[3] 2026年的另一项研究在角膜球差较高的 post-myopic LASIK/PRK 眼中同样报告了良好的远、中及功能性近视力和较高满意度。[4] 这些结果提示，较高的术后球差并不必然排除非衍射 EDoF IOL，但也不能据此推断所有术后角膜或所有 EDoF 机制均具有同样的适配性。

计算光学研究进一步表明，**瞳孔和角膜像差会改变 EDoF IOL 与术后角膜的相互作用**。Lago、de Castro 和 Marcos 在 post-LASIK 伪晶状体模型中比较单焦与非衍射 EDoF IOL，发现3 mm瞳孔下 EDoF 的焦深优势较明显，而5 mm瞳孔下两者焦深趋于接近；模型同时显示球差、彗差及瞳孔大小都会改变远焦质量和贯焦表现。[5] 临床比较研究也观察到，LASIK/PRK 后全眼球差在较大瞳孔下明显增加，并提示夜间瞳孔及球差范围与视觉现象相关。[6] 因而，仅用“是否做过 LASIK”或单一球差值来概括屈光术后眼，可能不足以预测 EDoF IOL 的完整眼表现。

现有研究仍有一个重要缺口。多数 post-refractive EDoF 研究聚焦于**常规近视/远视 LASIK 或 PRK 后角膜与某一具体商业 IOL**的临床结果或计算性能，而较少把角膜本身视为一个具有不同延焦结构的光学子系统，系统研究其与不同非衍射 EDoF 机制之间的耦合。这个问题在曾接受老视角膜屈光设计的人群中尤其重要：连续非球面角膜 EDoF 设计和中央近用型径向多焦角膜已经主动改变了焦轴能量分配，如果再植入具有波前塑形、径向屈光力调制或高阶球差调制特征的 EDoF IOL，两个延焦机制可能协同、相互抵消，也可能产生依赖瞳孔和基础眼结构的质量再分配。我们在本研究的目标性文献检索中未发现与此类角膜原型和非衍射 EDoF IOL 组合直接对应、且足以建立临床选择规则的高质量系列，因此这一问题更适合首先通过受控机制模型进行分解。

本研究据此建立一个冻结、可追溯的计算光学矩阵。为避免把 IOL residual 自身的瞳孔依赖误认为“术后角膜耦合”，我们加入统一未治疗角膜 N0 作为内部参照，并将三个术后角膜原型统一到临床处方语义：镜片平面−3.00 D、12 mm顶点距，对应角膜平面−2.8957529 D。三个术后原型分别为传统近视术后准单焦角膜（A0V12）、连续非球面角膜 EDoF 原型（B0V12）和中央近用型径向多焦角膜（C0V12）。它们分别与三类非衍射 EDoF IOL 机制 surrogate——波前塑形型（WFS-like）、连续径向屈光力调制型（RAD-like）和中央高阶球差调制型（HOA-like）——组合，并在两个基础模型眼和3/5 mm瞳孔下与严格匹配的 MONO carrier 比较。

研究的主要目的不是寻找商业意义上的“最佳 IOL”，而是回答三个机制问题：第一，同一 EDoF 机制在术后角膜中的 `EDOF−MONO` 效应是否相对于 N0 发生系统性改变，即是否存在非简单加和的完整眼 coupling；第二，这种 coupling 是否随瞳孔和基础眼改变方向或幅度；第三，焦深增加与固定焦面及完整贯焦光学质量之间如何交换。角膜、IOL carrier、residual、角频率尺度、贯焦窗口和 paired analysis 均在结果解释前冻结，以降低依据结果事后调参的风险。

## Introduction references

1. Ting DSJ, Gatinel D, Ang M. Cataract surgery after corneal refractive surgery: preoperative considerations and management. *Curr Opin Ophthalmol*. 2024;35(1):4-10. doi:10.1097/ICU.0000000000001006.
2. Sun Y, Hong Y, Rong X, Ji Y. Presbyopia-Correcting Intraocular Lenses Implantation in Eyes After Corneal Refractive Laser Surgery: A Meta-Analysis and Systematic Review. *Front Med (Lausanne)*. 2022;9:834805. doi:10.3389/fmed.2022.834805.
3. Fan W, Zhu M, Zhang G. Visual outcomes and spectacle independence of a non-diffractive wavefront-shaping intraocular lens in post-LASIK patients. *Front Med (Lausanne)*. 2025;12:1509889. doi:10.3389/fmed.2025.1509889.
4. Micheletti JM, Hall B. Satisfaction and Visual Outcomes with a Non-Diffractive EDOF IOL in Post-Myopic LASIK and PRK Patients with High Corneal Spherical Aberration. *Clin Ophthalmol*. 2026;20:566800. doi:10.2147/OPTH.S566800.
5. Lago CM, de Castro A, Marcos S. Computational simulation of the optical performance of an EDOF intraocular lens in post-LASIK eyes. *J Cataract Refract Surg*. 2023;49(11):1153-1159. doi:10.1097/J.JCRS.0000000000001260.
6. Visual outcomes and patient satisfaction after implantations of three types of presbyopia-correcting intraocular lenses that have undergone corneal refractive surgery. *Sci Rep*. 2024. doi:10.1038/s41598-024-58653-z.
