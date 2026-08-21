# 论文草稿模块：Results 与 Discussion

> 状态：manuscript draft，供后续整合；不是新的 scientific lock。  
> 投稿主结果来源：仅使用已接受的 TASK-013 / TASK-014 / TASK-015 structured evidence。  
> 所有 paired effect 定义为 `EDOF − MONO`；术后耦合定义为 `(EDOF−MONO)_postop − (EDOF−MONO)_N0`。  
> WFS-like / RAD-like / HOA-like 是机制 surrogate，不对应商业产品排名。

## Results

### 1. 数据完整性与最终分析矩阵

最终接受矩阵包括96个配置、48个严格匹配的 MONO–EDOF pairs 和1440个贯焦采样点，覆盖2种基础眼、4种角膜背景（N0、A0V12、B0V12、C0V12）、3类 IOL 机制和2种瞳孔。N0 来自 TASK-013；三个顶点距规范化术后角膜来自 TASK-014；TASK-015 在不调用 OpticStudio 的情况下独立核验源 evidence identity，并重建全部 paired effects 与 N0-referenced interactions。

48个 pair 中，43个 DOF50 effect 为精确值，5个为 lower bound；10个 pair 的 distance-peak 指标达到预注册 peak-search window 边界。所有 lower-bound 和 peak-window-conditioned 结果均保留边界属性，不进行伪精确排序或事后扩窗。

完整图形补充材料包含48张逐 pair 原始贯焦曲线和24张 summary figures，总计72张。48张 raw figure 一一覆盖全部 Base×Cornea×Platform×Pupil 条件，并同时显示 matched MONO 与 EDOF 的15-plane MTFa曲线。

### 2. 总体延焦—质量交换

在48个 matched pairs 中，35个 `ΔDOF50` 为正、13个为负。与此相对，`ΔTF MTFa mean` 在48/48 pair中均为负；`ΔMTFa@0D` 在47/48 pair中为负。唯一0 D MTFa 正向 pair 为 `ATC_M3_AL24477 × N0 × RAD-like × EPD5`（+0.0184），但其完整贯焦窗口 `ΔTF MTFa mean` 仍为−0.00731。

因此，当前冻结机制没有显示跨条件的“无代价增益”。EDoF residual 的主要作用是重新分配焦轴方向上的光学质量：在若干条件中扩大 DOF50，同时通常降低0 D质量并一致降低完整预注册窗口内的平均 MTFa。

### 3. 4×3 Cornea × Platform 描述性矩阵

下表对每个 Cornea×Platform 的4个 Base×Pupil strata 作确定性描述。带 `≥` 的 DOF50 mean 为 lower-bound mean；该表用于导航，不代表临床总体均值。

| Cornea × Platform | ΔDOF50 mean, D | ΔMTFa@0D mean | ΔTF MTFa mean | DOF方向（+/−） | DOF censored | Peak censored |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N0 × WFS-like | +0.061 | -0.117 | -0.0094 | 2/2 | 0 | 0 |
| N0 × RAD-like | +0.041 | -0.147 | -0.0117 | 2/2 | 0 | 0 |
| N0 × HOA-like | +0.221 | -0.328 | -0.0542 | 2/2 | 0 | 2 |
| A0V12 × WFS-like | +0.139 | -0.120 | -0.0106 | 4/0 | 0 | 0 |
| A0V12 × RAD-like | +0.078 | -0.167 | -0.0146 | 3/1 | 0 | 0 |
| A0V12 × HOA-like | +0.193 | -0.321 | -0.0525 | 2/2 | 0 | 2 |
| B0V12 × WFS-like | ≥+0.224 | -0.138 | -0.0113 | 3/1 | 2 | 2 |
| B0V12 × RAD-like | +0.196 | -0.166 | -0.0152 | 4/0 | 0 | 2 |
| B0V12 × HOA-like | +0.241 | -0.288 | -0.0507 | 2/2 | 0 | 2 |
| C0V12 × WFS-like | +0.124 | -0.118 | -0.0081 | 4/0 | 0 | 0 |
| C0V12 × RAD-like | ≥+0.242 | -0.216 | -0.0091 | 4/0 | 2 | 0 |
| C0V12 × HOA-like | ≥+0.432 | -0.346 | -0.0553 | 3/1 | 1 | 0 |

该表也说明仅比较术后 cell 的绝对 `EDOF−MONO` 并不足以证明“耦合”：N0 本身即表现出明显的平台和瞳孔依赖。因此，下面的术后解释以相对于 N0 的 interaction 为主。

### 4. N0 内部参照揭示 residual 自身的基线行为

N0 条件下，三类 surrogate 已经表现出明显不同的瞳孔依赖。WFS-like 和 RAD-like 的四-strata DOF50 mean 分别仅为+0.061 D和+0.041 D，且各有2个正向、2个负向 pair；HOA-like 的 mean 为+0.221 D，但同样有2正2负，并有2个 EPD5 distance peak 位于−0.50 D搜索边界。

这意味着术后角膜条件下看到的绝对延焦幅度不能全部归因于角膜×IOL coupling。N0-referenced interaction 将 IOL residual 在未治疗角膜中的基线响应扣除后，才能描述术后角膜背景对该机制的净调制。

### 5. A0V12：传统近视术后背景的相对调制较温和

A0V12×WFS-like 的 DOF50 interaction 相对于 N0 在两种基础眼、两种瞳孔中均为正：LB EPD3 +0.030 D、EPD5 +0.146 D；ATC EPD3 +0.036 D、EPD5 +0.098 D。其作用方向较一致，但幅度总体小于后述 B0V12-WFS EPD3 或 C0V12-RAD/HOA EPD5。

A0V12×RAD-like 在 EPD3 相对 N0 减弱（LB −0.027 D；ATC −0.085 D），但在 EPD5 转为增强（+0.091和+0.171 D）。A0V12×HOA-like 亦呈类似瞳孔依赖：EPD3 相对 N0 减弱约−0.076至−0.083 D，EPD5仅轻度增强（+0.005至+0.042 D）。因此，普通近视术后角膜背景并不产生统一方向的机制放大，而是对不同 residual 的瞳孔响应作有限调制。

### 6. B0V12：WFS-like 的小瞳孔增强与 RAD-like 的大瞳孔增强

B0V12×WFS-like 是最清晰的小瞳孔 interaction 之一。相对于 N0，其 EPD3 `ΔDOF50` 在两种基础眼均为 lower bound：LB `≥+0.266 D`，ATC `≥+0.260 D`。EPD5 仍保持正向，但幅度明显缩小至+0.073 D和+0.054 D。因此，B0V12 对 WFS-like 的调制可描述为**小瞳孔优势明显的增强**，而不是跨瞳孔恒定协同。

B0V12×RAD-like 则呈相反的瞳孔分布：EPD3 interaction 很小且基础眼间符号不一致（LB +0.056 D；ATC −0.018 D），EPD5 在两种基础眼均明显增强（LB +0.275 D；ATC +0.307 D）。因此更稳健的信号位于大瞳孔条件。

B0V12×HOA-like 相对于 N0 基本接近零：EPD3 为−0.001和+0.010 D，EPD5为+0.059和+0.012 D。该结果提示 B0V12 并不会普遍放大所有 EDoF 机制，其 interaction 具有机制选择性。

### 7. C0V12：RAD-like 与 HOA-like 的 EPD5 增强最突出

C0V12×RAD-like 在 EPD3 相对于 N0 接近零并存在基础眼间符号差异（LB +0.007 D；ATC −0.054 D），不支持稳定的小瞳孔耦合方向。到 EPD5 后，两种基础眼均出现强正 interaction 且均为 lower bound：LB `≥+0.379 D`，ATC `≥+0.471 D`。这是当前矩阵中最稳健的大瞳孔 DOF-oriented coupling 之一。

C0V12×HOA-like 同样具有显著瞳孔依赖。EPD3 相对 N0 均减弱（LB −0.043 D；ATC −0.049 D），而 EPD5 转为强增强：LB +0.246 D，ATC `≥+0.689 D`。ATC 条件的 lower bound 说明其真实增强可能更大，但冻结窗口不允许给出更精确排序。

C0V12×WFS-like 的 EPD3 interaction 接近零（−0.007和+0.004 D），EPD5 则呈中等正向（+0.118和+0.136 D）。因此 C0V12 的主要机制特征不是“所有 EDoF 均增强”，而是大瞳孔下对 RAD-like 和 HOA-like 的更强调制。

### 8. 高阶像差机制读数

三类 surrogate 在完整眼中保留了冻结机制的 C4⁰/C6⁰方向特征。WFS-like 在 EPD3 主要表现为正 ΔC4⁰ 与负 ΔC6⁰；RAD-like 的 EPD3 以负 ΔC6⁰为主要特征，而 EPD5 可出现 C4⁰/C6⁰方向重分配；HOA-like 在 EPD3 保持负 ΔC4⁰、正 ΔC6⁰的反号组合。

这种平台特异波前签名在 LB 与 ATC 两种基础眼中总体连续，支持上述 interaction 来自角膜背景对既有 EDoF 机制的调制，而不是 carrier 越界或 residual identity 漂移。尤其是先前超出历史 power coverage 的 ATC+N0 与 ATC+C0V12 carriers 均通过 exact-carrier validation，未观察到低功率机制断裂。

## Discussion

### 1. 主要发现：角膜与 EDoF 机制的关系不是简单相加

本研究的核心结果不是识别一个跨所有条件“最好”的 EDoF surrogate，而是证明角膜光学背景、IOL 延焦机制、瞳孔和基础眼共同决定焦深—质量交换的形态。加入 N0 内部参照后，这一结论更为明确：不同 residual 在未治疗角膜中本身已有明显瞳孔依赖，术后角膜的作用是进一步改变该基线机制的幅度和条件依赖，而不是产生一个可以简单相加的固定“术后增益”。

B0V12×WFS-like 的主要 interaction 位于 EPD3；B0V12×RAD-like 的主要增强位于 EPD5；C0V12×RAD-like 与 C0V12×HOA-like 的最强增强也位于 EPD5。相反，若干 EPD3 interaction 接近零且在两基础眼间改变符号，应解释为 near-zero/base-dependent，而不是稳定的“反向耦合”。

### 2. N0 参照改变了“耦合”的解释门槛

没有 N0 时，较大的 `EDOF−MONO` 很容易被直接解释为术后角膜与 IOL 的协同。但 N0 显示，例如 HOA-like 在3 mm本身即可产生较大 DOF50扩展，而到5 mm则可转为负效应；WFS-like 和 RAD-like 同样具有自身的瞳孔依赖。因此，更严格的耦合定义应回答：在相同 Base×Platform×Pupil 下，术后角膜是否使该 EDoF−MONO 效应相对于未治疗角膜发生系统性改变。

这一 N0-referenced 框架使结果更接近真正的 interaction 问题，也避免把 IOL residual 自身的非线性响应误归因于屈光术后角膜。

### 3. 顶点距规范化提高了术后处方语义的一致性

最终术后角膜统一使用镜片平面−3.00 D、12 mm顶点距，对应角膜平面−2.8957529 D，而不是直接把−3.00 D视为角膜平面 treatment。该修订幅度约0.104 D，数值不大，但使模型输入与临床眼镜处方语义一致，并避免在 ATC 近视基础眼中把眼型屈光状态再次叠加到手术处方。

因此，最终 A0V12/B0V12/C0V12 更适合作为投稿主分析；旧 A0/B0/C0 direct-corneal-plane Run72 保留为工程历史和方法演化证据，而不与最终主结果混算。

### 4. WFS-like 的小瞳孔依赖与既往 post-LASIK 研究方向相容

外部研究为这种瞳孔依赖提供了背景。Lago、de Castro 和 Marcos 对 post-LASIK 眼进行计算模拟时发现，非衍射波前塑形 EDoF IOL 的焦深优势在较小瞳孔下更突出，而较大瞳孔时与单焦点方案的差异缩小。Garzón 等的光学台研究也显示，波前塑形非衍射 EDoF IOL 的光学质量具有明显瞳孔依赖，并具有复杂的中央功率/球差分布。

本研究不能把 B0V12 surrogate 等同于任何真实 presbyopic ablation，也不能把 WFS-like 等同于具体商业产品；但 B0V12×WFS-like 相对 N0 在 EPD3 的一致增强与上述方向相容。更重要的是，EPD5 interaction 明显缩小，提示角膜 EDoF 与 IOL 波前塑形机制之间的关系本身受有效瞳孔限制。

### 5. C0V12×RAD-like 与 C0V12×HOA-like：大瞳孔下的空间机制耦合假设

C0V12×RAD-like 在 EPD5 的强正 interaction 跨两基础眼保持一致，并均为 lower bound。由于 C0V12 和 RAD-like 都包含显著径向空间结构，一个合理但仍需验证的机制假设是，两者的径向功率/相位分配在较大瞳孔下形成更宽的有效贯焦包络。

C0V12×HOA-like 同样在 EPD5 强增强，而 EPD3 相对 N0减弱。这说明中央近用径向结构与高阶球差型 residual 的组合不能简单描述为“更多 HOA 就更多 DOF”，而更可能反映瞳孔决定的区域权重和焦轴能量重分配。

这些 interaction 不能仅凭 DOF50 命名为“匹配成功”。C0V12×RAD-like 和 C0V12×HOA-like 同时伴随0 D或全窗 MTFa代价，因此其科学含义是**DOF-oriented trade-off**，不是总体光学质量优势。

### 6. 焦深扩展应与全窗质量代价共同报告

本研究最稳健的跨矩阵结果是 `ΔTF MTFa mean < 0` 出现在48/48 pair；`ΔMTFa@0D` 也在47/48为负。即使唯一0 D正向的 ATC+N0+RAD-like+EPD5，其全贯焦平均质量仍下降。

因此，DOF50 扩展不能单独作为“更优”的依据。对于强 interaction，尤其是 B0V12-WFS EPD3、C0V12-RAD EPD5 和 C0V12-HOA EPD5，应同时展示 raw through-focus curves、0 D MTFa和全窗平均 MTFa，以说明新增焦深来自何种质量再分配。

### 7. 临床意义：从“产品排名”转向完整眼机制分层

已有临床资料提示，在经过筛选的普通近视 LASIK/PRK 术后眼中，非衍射波前塑形 EDoF IOL 可以获得良好的远中视力和较宽主观焦深。Fan、Zhu 和 Zhang 的前瞻性研究以及 Micheletti 和 Hall 的术后系列均支持“既往近视角膜屈光手术并不自动排除非衍射 EDoF”的临床可行性。

但当前研究的 B0V12 和 C0V12 是机制原型，不是对特定商业角膜手术或 IOL 的处方级重建。现有结果更适合提出分层变量：角膜贯焦形态、瞳孔、C4⁰/C6⁰及更完整 HOA 结构，可能比“是否做过 LASIK”或单一 Q 值更能解释完整眼 EDoF 响应。任何产品级或患者级推荐仍需要真实器件、真实术后角膜和临床数据验证。

### 8. 局限性

本研究是确定性光学模拟而非临床样本研究。两种基础眼、一个未治疗角膜和三个术后角膜原型用于机制覆盖，不代表真实人群分布；48个 matched pairs 不是随机样本，不宜使用普通临床总体显著性推断。WFS-like、RAD-like 和 HOA-like 是机制 surrogate，不能与任一商业 IOL 一一等同。

DOF50 有5个 lower-bound pair，distance peak 有10个 window-conditioned pair；预注册窗口没有因这些结果而事后扩大。因此部分强 interaction 只能作为下界，不适合做精确数值排名。MVP 中角膜屈光手术居中，未加入治疗区偏心/倾斜；IOL 偏心和倾斜、多色效应、真实角膜不规则像差、上皮重塑、泪膜和个体 pupil dynamics 亦未纳入当前矩阵。

此外，N0 是统一未治疗角膜 scaffold，用于内部机制参照，并不等价于真实人群中的“正常眼分布”。因此 postop-minus-N0 interaction 应理解为受控模型中的净光学调制，而不是临床平均治疗效应。

## Conclusion

以未治疗 N0 为内部参照后，角膜屈光术后背景对非衍射 EDoF IOL 的作用表现为机制特异、瞳孔依赖的完整眼耦合，而非固定可加效应。B0V12×WFS-like 主要表现为小瞳孔下的 DOF 增强；B0V12×RAD-like、C0V12×RAD-like 及 C0V12×HOA-like 的主要增强位于5 mm瞳孔。与此同时，48/48 pair 的全贯焦平均 MTFa下降，说明焦深扩展始终需要与光学质量再分配共同解释。当前结果支持机制分层和后续可检验假设，但不支持将4×3矩阵直接转化为商业 IOL 排名或患者级临床推荐。

## 外部文献锚点（Discussion only）

1. Lago CM, de Castro A, Marcos S. Computational simulation of the optical performance of an EDOF intraocular lens in post-LASIK eyes. *J Cataract Refract Surg*. 2023;49(11):1153-1159. doi:10.1097/J.JCRS.0000000000001260.
2. Fan W, Zhu M, Zhang G. Visual outcomes and spectacle independence of a non-diffractive wavefront-shaping intraocular lens in post-LASIK patients. *Front Med (Lausanne)*. 2025;12:1509889. doi:10.3389/fmed.2025.1509889.
3. Micheletti JM, Hall B. Satisfaction and Visual Outcomes with a Non-Diffractive EDOF IOL in Post-Myopic LASIK and PRK Patients with High Corneal Spherical Aberration. *Clin Ophthalmol*. 2026;20:566800. doi:10.2147/OPTH.S566800.
4. Garzón N, Gómez-Pedrero JA, Albarrán-Diego C, et al. Optical power profiles and aberrations of a non-diffractive wavefront-shaping extended depth of focus intraocular lens. *Graefes Arch Clin Exp Ophthalmol*. 2024;262(9):2897-2906. doi:10.1007/s00417-024-06469-y.
5. Schmid R, Borkenstein AF. Optical Bench Evaluation of the Latest Refractive Enhanced Depth of Focus Intraocular Lens. *Clin Ophthalmol*. 2024;18:1921-1932. doi:10.2147/OPTH.S469849.
