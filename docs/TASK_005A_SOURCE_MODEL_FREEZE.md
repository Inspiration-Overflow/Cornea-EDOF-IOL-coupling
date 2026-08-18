# TASK-005A — Liou–Brennan 与 Atchison 近视基座源模型冻结

> 本文完成 RMD-TASK-005 的前置研究子阶段 TASK-005A：只冻结两个主研究基座的权威来源、轴向锚点和项目化继承边界。本文不是完整 schematic eye 复刻说明，也不把原模型天然角膜、天然晶状体或曲面视网膜直接带入本项目主实验。

## 1. 结论

MVP 两个主研究基座继续保持：

- `LB_AL2395`：Liou–Brennan 1997 正视有限模型眼的轴长锚点，`AL = 23.950 mm`。
- `ATC_M3_AL24477`：Atchison 2006 **Model 1（共轴模型）在 SR = -3.00 D 时的近视样本**，`AL = 24.477 mm`。

其中 `ATC_M3` 中的 `M3` 在本项目中固定解释为 **myopia -3 D sample**，不是 Atchison 原文中的“Model 3”。Atchison 2006 原文只给出 Model 1（所有表面共轴）和 Model 2（加入晶状体倾斜、视网膜倾斜/偏心）。主实验采用共轴条件，因此其权威母模型是 Model 1。

这两个基座在主实验中只承担不同的**眼轴/后段传播背景**。主实验统一使用项目自己的 A0/B0/C0 角膜模块、标准化 STOP、IOL 位置和固定平面 IMAGE；不保留两篇原模型的天然角膜、GRIN 天然晶状体、原始 pupil decentration/tilt 或曲面视网膜。

## 2. 权威来源

### 2.1 Liou–Brennan

权威原始文献：

H.-L. Liou, N. A. Brennan. *Anatomically accurate, finite model eye for optical modeling*. Journal of the Optical Society of America A, 1997;14(8):1684-1695. DOI: `10.1364/JOSAA.14.001684`。

原文明确该模型为包含四个非球面折射面和 GRIN 晶状体的有限模型眼，并给出等效光焦度约 60.35 D、轴长 23.95 mm。原文 Table 6 给出结构参数。

### 2.2 Atchison

权威原始文献：

D. A. Atchison. *Optical models for human myopic eyes*. Vision Research, 2006;46(14):2236-2250. DOI: `10.1016/j.visres.2006.01.004`。

原文 Table 1 直接给出各结构参数随 spectacle refraction `SR` 的函数，并区分：

- Model 1：各表面共轴；
- Model 2：加入晶状体倾斜以及视网膜倾斜/偏心。

本项目采用 Model 1 的 `SR=-3.00 D` 轴向样本。

## 3. Liou–Brennan 原始结构核对

原始 Liou–Brennan 结构在 555 nm 下的标准参数为：

| 部位/表面 | 半径 mm | 非球面参数 Q | 到下一面的轴向厚度 mm | 折射率/介质 |
| --- | ---: | ---: | ---: | --- |
| 前角膜 | +7.77 | -0.18 | 0.50 | cornea `n=1.376` |
| 后角膜 | +6.40 | -0.60 | 3.16 | aqueous `n=1.336` |
| 晶状体前表面 | +12.40 | -0.94 | 1.59 | GRIN anterior |
| 晶状体内部中间面 | ∞ | — | 2.43 | GRIN posterior |
| 晶状体后表面 | -8.10 | +0.96 | 16.27 | vitreous `n=1.336` |
| retina | 原模型为有限眼终止面 | — | — | — |

GRIN 形式在后续文献对原模型的复现中写为：

`Grad A = 1.368 + 0.049057 z - 0.015427 z^2 - 0.001978 (x^2+y^2)`

`Grad P = 1.407 - 0.006605 z^2 - 0.001978 (x^2+y^2)`

但 **TASK-005 主实验不复用该天然晶状体 GRIN**；记录它只用于证明 `LB_AL2395` 的来源是完整 Liou–Brennan 模型，而不是凭空选取 23.95 mm。

其轴长可由原始轴向段直接核对：

`0.50 + 3.16 + 1.59 + 2.43 + 16.27 = 23.95 mm`。

因此冻结：

`LB_AL2395.axial_length_mm = 23.950`。

## 4. Atchison 2006 Model 1 原始结构与 -3 D 样本

Atchison 2006 Table 1 在 555 nm 下给出：

| 部位/表面 | 原文参数 |
| --- | --- |
| 前角膜半径 | `R = 7.77 + 0.022 SR` mm |
| 前角膜 Q | `-0.15` |
| 角膜厚度 | `0.55 mm` |
| 角膜折射率 | `1.376` |
| 后角膜半径 | `+6.40 mm` |
| 后角膜 Q | `-0.275` |
| 房水折射率 | `1.3374` |
| 后角膜→晶状体前表面距离 | `3.15 mm` |
| 晶状体前表面半径 | `+11.48 mm` |
| 晶状体前表面 Q | `-5` |
| 前半 GRIN 厚度 | `1.44 mm` |
| 中间面 | `R = ∞` |
| 后半 GRIN 厚度 | `2.16 mm` |
| 晶状体后表面半径 | `-5.90 mm` |
| 晶状体后表面 Q | `-2` |
| 玻璃体折射率 | `1.336` |
| 玻璃体腔长度 | `16.28 - 0.299 SR` mm |

Atchison 还给出曲面视网膜的屈光度依赖半径和 Q；它们用于外围视网膜/周边屈光建模。本项目主实验是轴上、固定平面 IMAGE，因此这些曲面视网膜参数只作为原模型 provenance 保存，不继承到主基座。

### 4.1 SR = -3.00 D 代入

取项目冻结样本：

`SR = -3.00 D`。

得到：

- 前角膜半径：`7.77 + 0.022*(-3) = 7.704 mm`；
- 玻璃体腔长度：`16.28 - 0.299*(-3) = 17.177 mm`。

总眼轴：

`AL = 0.55 + 3.15 + 1.44 + 2.16 + 17.177 = 24.477 mm`。

等价地，Atchison Model 1 的轴长随 SR 为：

`AL = 23.58 - 0.299 SR` mm，

故 `SR=-3.00 D` 时：

`AL = 23.58 + 0.897 = 24.477 mm`。

因此冻结：

`ATC_M3_AL24477.source_model = Atchison_2006_Model_1`

`ATC_M3_AL24477.source_SR_D = -3.00`

`ATC_M3_AL24477.axial_length_mm = 24.477`

并冻结命名解释：

`M3 := myopia_minus_3D_sample`。

## 5. 项目主实验继承矩阵

为了避免“选了经典 schematic eye 就把整个经典眼搬进来”，TASK-005B 必须按下表执行：

| 原模型要素 | `LB_AL2395` | `ATC_M3_AL24477` | 主实验规则 |
| --- | --- | --- | --- |
| 轴长 AL | **继承 23.950 mm** | **继承 24.477 mm** | 冻结，不优化 |
| 原模型天然前/后角膜 | 不继承 | 不继承 | 使用同一 A0/B0/C0 角膜模块 |
| 原模型天然晶状体/GRIN | 不继承 | 不继承 | 移除，使用项目 IOL |
| 原模型原 pupil/STOP 几何 | 不继承 | 不继承 | 后角膜→STOP 固定 3.15 mm |
| IOL 前表面位置 | 原文无项目定义 | 原文无项目定义 | 后角膜→IOL 前表面固定 4.50 mm |
| 房水/玻璃体折射率 | 不作为 base 差异 | 不作为 base 差异 | MVP 统一约 `n=1.336`，具体以 URD/科学资产实现为准 |
| 原模型曲面 retina | 不继承 | 不继承 | 轴上平面 IMAGE，顶点由冻结 AL 决定 |
| tilt/decentration | 不继承 | 不继承 | 主实验 centered/coaxial |
| 主波长 | 文献核对 555 nm | 文献 Table 1 为 555 nm | 主实验 555 nm |

因此两个 base 的科学解释固定为：

> **同一项目化伪晶状体眼前段 + 两个不同的冻结眼轴背景。**

它们不是“完整 Liou–Brennan 眼 vs 完整 Atchison 眼”的比较。

## 6. TASK-005B 构建约束

Codex/OpticStudio 在建立正式 `.zos` 基座时必须满足：

1. `LB_AL2395` 的 anterior-cornea vertex → IMAGE vertex = `23.950 mm`。
2. `ATC_M3_AL24477` 的 anterior-cornea vertex → IMAGE vertex = `24.477 mm`。
3. 两个 base 除由 AL 导致的后段传播长度外，A0/B0/C0、STOP 和 IOL 参考几何必须一致。
4. 后角膜→STOP = `3.150 mm`。
5. 后角膜→IOL 前表面 = `4.500 mm`。
6. 主模型不建立天然晶状体 GRIN。
7. 主模型不使用 Atchison Model 2 的 tilt/decentration。
8. 主模型不使用 Atchison 曲面视网膜或 Liou–Brennan 的天然前段来制造额外 base 差异。
9. 如果实际 Zemax surface stack 因 IOL 厚度需要拆分多段，必须通过 thickness sum 保持最终 IMAGE 顶点的冻结 AL，而不得通过重新优化 AL 获得焦点。
10. 固定 retina 原则继续有效：后续 carrier 求解通过 IOL power/conic 等规定自由度实现，不移动 IMAGE 来追焦。

## 7. 冻结状态

TASK-005A 完成后，下列项目进入 source-model freeze：

- `LB_AL2395 = 23.950 mm`；
- `ATC_M3_AL24477 = Atchison Model 1 @ SR=-3.00 D = 24.477 mm`；
- `ATC_M3` 的 `M3` 解释为 minus-3-D sample，而不是 Model 3；
- 两套 base 只继承眼轴背景，不继承原模型天然角膜/晶状体/曲面视网膜；
- 主实验两 base 采用相同项目化前段几何，只有后段长度因 AL 不同。

任何后续实现若需要改变 23.950、24.477、SR=-3.00 D 或“只继承轴向背景”的原则，必须回到科学设计层重新审查，不能作为 OpticStudio 适配修订静默修改。

## 8. 文献与核对记录

### 权威原始来源

1. Liou HL, Brennan NA. Anatomically accurate, finite model eye for optical modeling. J Opt Soc Am A. 1997;14(8):1684-1695. DOI: `10.1364/JOSAA.14.001684`.
2. Atchison DA. Optical models for human myopic eyes. Vision Res. 2006;46(14):2236-2250. DOI: `10.1016/j.visres.2006.01.004`.

### 交叉核对

- Liou–Brennan 原文摘要明确 AL = 23.95 mm；原文 Table 5/6 给出 60.35 D、23.95 mm 及结构参数。
- 后续 Optica/JOSA 文献对 Liou–Brennan 参数表和 GRIN 方程进行了逐项复现，用于核对网页解析中原始 Table 6 未完整展开的单元格。
- Atchison 原文 ScienceDirect 页面可直接读取 Table 1 的 SR-dependent 参数、Model 1/Model 2 定义和 555 nm 折射率。

## 9. 下一步

TASK-005A 不生成 `.zos/.zmx`，也不生成正式 scientific lock 文件。

下一步为 **TASK-005B：按本冻结说明在代码中定义两个 base prescription，并由 Codex/OpticStudio 实机生成、回读和验证正式基座 `.zos`**。