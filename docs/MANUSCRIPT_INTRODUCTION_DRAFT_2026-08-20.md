# 论文草稿模块：引言

> 状态：manuscript draft。正文采用读者可理解的语义化名称；工程 ID 仅在 Methods 首次映射时使用。

## 引言

角膜屈光手术后的白内障管理正在从相对少见的特殊情境逐渐转变为常见的屈光性白内障问题。随着接受 LASIK、PRK 等手术的人群逐渐进入白内障高发年龄，临床关注点已经从单纯提高人工晶状体度数预测准确性，扩展到术后视觉范围、光学质量和老视矫正策略。总角膜屈光力、光线追迹、术中像差测量和专用人工晶状体计算公式可以改善屈光预测，但角膜屈光手术还会改变前后表面曲率关系、角膜非球面性以及高阶像差，因此术后人工晶状体选择并不只是“把球镜度数算准”的问题。[1]

这一问题在老视矫正人工晶状体中更为突出。系统综述提示，既往接受角膜激光屈光手术的眼在植入老视矫正人工晶状体后可以获得较好的远、中、近视力以及较高的眼镜独立性，但眩光、光晕和对比敏感度下降仍需要考虑，且现有研究在术式、角膜状态、人工晶状体类型和结局指标方面具有明显异质性，尚不足以形成简单的选片规则。[2]

非衍射延伸焦深（extended depth of focus，EDoF）人工晶状体通过在焦轴方向上形成连续有效焦域，被认为可能对部分屈光术后眼具有优势。Fan 等在非衍射波前塑形型 EDoF 人工晶状体的前瞻性病例系列中发现，既往近视 LASIK 眼可获得良好的远、中视力，并呈现较平滑的离焦曲线和较宽的主观焦深。[3] Micheletti 和 Hall 在角膜球差较高的近视 LASIK/PRK 术后眼中也报告了良好的视觉结果和较高满意度。[4] 这些结果说明，较高的术后球差并不必然排除非衍射 EDoF 人工晶状体，但也不能据此推断所有术后角膜或所有非衍射延焦机制都具有相同的适配性。

计算光学研究进一步表明，瞳孔和角膜像差会显著改变 EDoF 人工晶状体在术后眼中的贯焦响应。Lago、de Castro 和 Marcos 在 post-LASIK 伪晶状体模型中观察到，3 mm 瞳孔下 EDoF 的焦深优势较明显，而 5 mm 瞳孔下差异明显缩小；模型还显示球差、彗差和瞳孔大小共同影响远焦质量及贯焦表现。[5] Garzón 等的光学台研究也显示，波前塑形型非衍射 EDoF 人工晶状体在中央光学区具有复杂的空间功率和像差分布，其光学表现会随瞳孔而变化。[6] 因此，仅以“是否做过 LASIK”或单一角膜球差值概括屈光术后眼，难以充分预测完整眼的 EDoF 响应。

现有研究仍较少把角膜本身视为具有不同延焦结构的光学子系统，并系统比较其与不同非衍射 EDoF 机制之间的相互作用。这一缺口在曾接受老视角膜屈光设计的眼中尤其重要。连续非球面角膜延焦设计和中央近用径向多焦角膜会主动改变焦轴方向的能量分配；如果此后再植入具有波前塑形、径向屈光力调制或高阶像差调制特征的 EDoF 人工晶状体，角膜与人工晶状体两个延焦系统可能产生增强、削弱或瞳孔依赖的重新分配。

本研究因此建立一个冻结、可追溯的计算光学矩阵，并加入未治疗参照角膜作为内部对照。这样可以先明确同一人工晶状体延焦机制在未治疗角膜背景下的固有贯焦行为，再判断术后角膜是否对这一行为产生额外调制。研究重点不是寻找跨条件“最好”的人工晶状体，而是回答三个机制问题：第一，术后角膜是否系统改变同一延焦机制相对于匹配单焦对照的效应；第二，这种改变是否随瞳孔和基础眼结构而变化；第三，焦深扩展与固定焦面及全贯焦光学质量之间如何交换。

## 引言参考文献

1. Ting DSJ, Gatinel D, Ang M. Cataract surgery after corneal refractive surgery: preoperative considerations and management. *Curr Opin Ophthalmol*. 2024;35(1):4-10. doi:10.1097/ICU.0000000000001006.
2. Sun Y, Hong Y, Rong X, Ji Y. Presbyopia-Correcting Intraocular Lenses Implantation in Eyes After Corneal Refractive Laser Surgery: A Meta-Analysis and Systematic Review. *Front Med (Lausanne)*. 2022;9:834805. doi:10.3389/fmed.2022.834805.
3. Fan W, Zhu M, Zhang G. Visual outcomes and spectacle independence of a non-diffractive wavefront-shaping intraocular lens in post-LASIK patients. *Front Med (Lausanne)*. 2025;12:1509889. doi:10.3389/fmed.2025.1509889.
4. Micheletti JM, Hall B. Satisfaction and Visual Outcomes with a Non-Diffractive EDOF IOL in Post-Myopic LASIK and PRK Patients with High Corneal Spherical Aberration. *Clin Ophthalmol*. 2026;20:566800. doi:10.2147/OPTH.S566800.
5. Lago CM, de Castro A, Marcos S. Computational simulation of the optical performance of an EDOF intraocular lens in post-LASIK eyes. *J Cataract Refract Surg*. 2023;49(11):1153-1159. doi:10.1097/J.JCRS.0000000000001260.
6. Garzón N, Gómez-Pedrero JA, Albarrán-Diego C, et al. Optical power profiles and aberrations of a non-diffractive wavefront-shaping extended depth of focus intraocular lens. *Graefes Arch Clin Exp Ophthalmol*. 2024;262(9):2897-2906. doi:10.1007/s00417-024-06469-y.
