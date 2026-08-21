# Model Revision R0 — 人工审核后模型定义合同

> 日期：2026-08-20  
> 状态：**R0 CONTRACT FROZEN FOR IMPLEMENTATION**  
> 分支：`feat/model-revision-binary4-physical-pupil`  
> 上游基线：`main@d8f77dd5876fdb14d9dfa868a84b651da25b9b7c`  
> 适用范围：人工 Zemax 审核后新版模型；旧 `main` 继续作为 pre-human-audit frozen baseline。

## 1. 修订边界

本轮是模型定义修订，不是对旧结果做补丁。

旧版以下内容保持只读：

- 已接受的 ZMX/ZOS；
- TASK-013 / TASK-014 evidence；
- TASK-015 96-config 数据、图和整合结果；
- 已冻结的 Grid Sag residual 文件与 provenance。

新版完成后形成独立的 post-human-audit dataset；禁止把旧、新模型定义下的部分结果混合成一个正式矩阵。

当前阶段只冻结合同与来源。**R0/R1 不运行 OpticStudio，不生成新正式 ZMX，也不改旧 evidence。**

## 2. 当前实现中需要被新版替换的旧语义

代码审查确认至少有四处直接承载旧定义：

1. `src/whole_eye_mvp/analysis_zos.py`：`_set_epd()` 将系统 aperture 设置为 `EntrancePupilDiameter`，主分析按 3/5 mm 固定 ENPD。
2. `src/whole_eye_mvp/carrier_zos.py`：carrier 求解同样通过 `_set_epd()` 固定 EPD，并在插入 carrier 时把 IMAGE radius/conic 设为 0。
3. `src/whole_eye_mvp/base_assets.py`：基座建立和 validation 把 IMAGE 平面作为显式条件（`image_is_plane`）。
4. `src/whole_eye_mvp/grid_sag_residual.py`：EDoF residual 最终写成 `611×611`、`0.01 mm` step、`3.05 mm` half-width 的 Cartesian Grid Sag，并使用 linear interpolation。

因此 R2 以后必须同时处理 base builder、carrier path 和 analysis path；只改最终 ZMX 的 Lens Data Editor 外观不构成完成修订。

## 3. 物理瞳孔合同

新版研究变量定义为**虹膜 / STOP 平面的实际物理直径**。

系统 aperture：

```text
Aperture Type = Float By Stop Size
```

冻结：

| 条件 | STOP Semi-Diameter | 物理瞳孔直径 |
| --- | ---: | ---: |
| PUPIL_3 | 1.500 mm | 3.000 mm |
| PUPIL_5 | 2.500 mm | 5.000 mm |

不再人工规定 Entrance Pupil Diameter。ENPD 改为 ray-trace 后的诊断量，并应进入 audit summary。

科学解释固定为：在不同角膜结构下保持同一真实虹膜孔径，让角膜对 entrance pupil 成像的改变保留在模型中。

因此旧固定 ENPD 数据不能沿用；MTF、MTFa、DOF50、C4^0、C6^0、HOA RMS、pupil/ray footprint 等必须在新模型中重新计算。

## 4. Clear Semi-Diameter 合同

canonical full-eye model 固定：

| 表面 | Semi-Diameter |
| --- | ---: |
| anterior cornea | 5.000 mm |
| posterior cornea | 5.000 mm |
| STOP, 3 mm pupil | 1.500 mm |
| STOP, 5 mm pupil | 2.500 mm |
| IOL anterior | 3.000 mm |
| IOL posterior | 3.000 mm |
| retina / IMAGE | 5.000 mm |

这些值是模型物理定义，不是单纯 layout 参数。

必须继续审计真实 ray footprint。尤其在 5 mm 物理瞳孔下，如 IOL 上出现 `r_ray,max >= 3.0 mm`，按真实 optical aperture clipping / vignetting 处理；不得自动扩大 6 mm IOL optic 来消除。

## 5. 视网膜合同

### 5.1 Liou–Brennan base

恢复原 Liou–Brennan 模型的球面视网膜：

```text
Surface Type = Standard
Radius = -12.000 mm
Conic = 0
Semi-Diameter = 5.000 mm
```

轴长锚点仍保持 `AL = 23.950 mm`；恢复曲率不等于允许移动 retina 追焦。

### 5.2 Atchison Model 1 @ SR=-3.00 D

恢复 refraction-dependent biconic retina。R1 source lock 冻结的目标参数为：

```text
SR = -3.00 D
Rx = -12.628 mm
Ry = -12.732 mm
Qx = +0.192
Qy = +0.199
```

实现应使用 OpticStudio `Biconic` surface，而不是旋转对称平均半径。

`SR=-3.00 D` 只定义 Atchison 基础眼表型；角膜屈光手术处方仍是独立实验变量。既有 12 mm vertex conversion 规则继续有效，不允许把两者相加。

## 6. EDoF 最终表面：Binary Optic 4 纯折射使用方式

Grid Sag 从新版 final surface representation 退休，但保留为 pilot comparator 和历史 reference。

三平台 residual 所在面不变：

```text
WFS-like -> anterior IOL surface
RAD-like -> posterior IOL surface
HOA-like -> anterior IOL surface
```

新版统一使用 OpticStudio `Binary Optic 4` 的**多分区非球面 sag 能力**，关闭其衍射相位能力：

```text
Np = 0
Diffraction order M_j = 0 for every zone
```

这类表面在本项目中的术语固定为：

- 英文：`piecewise-aspheric refractive EDoF surface`
- 中文：`分区低阶非球面折射型延焦表面`

不得称为“衍射 Binary IOL”。

### 6.1 OpticStudio 编码澄清

Ansys OpticStudio Binary 4 的每区 sag coefficients 使用该区外半径 `A_j` 归一化坐标 `p=r/A_j`；并且 Binary 4 会自动给相邻 zone 加 sag offset，使边界 sag 连续。

因此项目层所说的 `A4/A6` 必须和 OpticStudio native coefficient 明确区分，避免把归一化系数误当作传统 Even Asphere 的未归一化系数。

实现冻结为：

```text
Nz = mechanism-specific zone count
Na = 3
Np = 0
```

每区三个 native aspheric slots 对应 `p^2 / p^4 / p^6`：

- `p^2` coefficient：**永久固定为 0**，避免用额外二次项偷带 defocus；
- `p^4` coefficient：项目逻辑自由度 `A4`；
- `p^6` coefficient：项目逻辑自由度 `A6`。

若 native sag 写作：

```text
z_extra = alpha2 * p^2 + alpha4 * p^4 + alpha6 * p^6
p = r / A_j
```

则 audit/export 必须同时给出：

```text
A4_equiv = alpha4 / A_j^4    [mm^-3]
A6_equiv = alpha6 / A_j^6    [mm^-5]
```

以便与未归一化 `r^4/r^6` 系数比较。不得只导出编辑器中的 native alpha 数字而不记录 normalization radius。

## 7. Binary 4 zone boundary freeze

优化器不得移动任何 radial boundary。

### WFS-like

```text
0 / 0.55 / 0.65 / 0.87 / 1.05 / 3.00 mm
```

5 zones。专利中的 `r5=1.11 mm` 继续保留为 provenance，但由于新版只继承 phase-shift residual、不复制专利第二套 base asphere，不额外制造 1.11 mm optical zone。

### RAD-like

```text
0 / 0.50 / 0.90 / 1.10 / 1.40 / 2.50 / 3.00 mm
```

6 zones。2.50–3.00 mm 为 peripheral neutral zone，永久退化到 base posterior carrier；1.40–2.50 mm 默认也保持 neutral，仅在连续性/几何合理性无法满足时允许进入 review，而不是自动放开。

### HOA-like

```text
0 / 0.90 / 1.10 / 3.00 mm
```

3 zones。1.10–3.00 mm 永久退化到 base anterior carrier。

## 8. 每区自由度与最小复杂度顺序

项目逻辑允许的最大复杂度：

```text
R, Q, A4, A6
```

禁止：

- 额外二次 polynomial sag term；
- A8 及以上高阶 sag；
- 任何 phase coefficient；
- 非零 diffraction order。

自由度按以下顺序增加：

1. `R`
2. `R + Q`
3. `R + Q + A4`
4. `R + Q + A4 + A6`

前一级达到 mechanism-fit acceptance 时不得无理由增加下一项。各 zone 不要求具有相同的 active parameter count。

## 9. 连续性合同

Binary 4 native sag offset 会按设计保证相邻 zone 的 `C0`。因此：

```text
C0 = hard requirement + numerical readback check
C1 = not hard-constrained
```

每个 boundary 都必须计算左右 slope，并记录：

```text
C0_error
C1_slope_jump
```

`C0_error` 应只剩数值误差；过大的 slope jump 进入 geometry/manufacturing review。

禁止为了追求形式上的 C1 连续而升级到高阶全局多项式。

## 10. 机制优先的拟合顺序

任何 Binary 4 pilot 都必须按以下层级处理；不得把 through-focus MTF 作为第一优化目标。

### Level 1 — mechanism fidelity

- WFS-like：拟合 frozen target sag / OPD；重点检查 0.55、0.65、0.87、1.05 mm 边界。
- RAD-like：拟合 frozen radial relative power `P(r)`；POWP X scan 为主要 readback。
- HOA-like：拟合 frozen target OPD，并检查 `C4^0 < 0`、`C6^0 > 0` 的目标机制。

### Level 2 — geometry / manufacturing diagnostics

检查 sag、slope、curvature、zone-boundary slope jump、local power。

### Level 3 — standard-eye validation

检查 residual piston、global defocus、C4、C6、HOA RMS、ray health。

历史 low-order gate 暂保留：

```text
|piston| <= 0.010 um
|global defocus| <= 0.125 D
```

pilot 可以把 `|global defocus| <= 0.05 D` 作为拟合目标，但在 R5 之前不升级成正式 scientific acceptance threshold。

### Level 4 — optical sanity/performance

最后才检查 FFT MTF、through-focus MTF、DOF。不得根据最终 Cornea × IOL 组合表现回头重新优化已冻结机制。

## 11. MONO / EDoF 同构合同

同一平台的 MONO 与 EDoF 必须使用相同 Binary 4 zone structure、CT、材料、IOL 位置、base power 与 carrier geometry。

- MONO：所有 zones 光学上退化为 base carrier；
- EDoF：只改变批准的 zone sag parameters。

R3 必须数值验证：

```text
Binary4-degenerate MONO vs original analytical carrier
```

至少比较：

- radial sag 0–3 mm；
- EFFL / paraxial power；
- C4^0 / C6^0；
- FFT MTF。

未通过等价性验证不得进入 EDoF pilot。

## 12. R4 pilot scope

先选约 `+20 D` representative carrier，不立即扩展 24 carriers / 96 configs。

核心模型：

```text
WFS-like  MONO / EDoF
RAD-like  MONO / EDoF
HOA-like  MONO / EDoF
```

共 6 个核心 Binary 4 ZMX。

每个机制至少比较：

```text
old Grid Sag EDoF
new Binary4 EDoF
new Binary4 MONO
```

必要时加入 original analytical MONO。

pilot acceptance 分开记录：

```text
A mechanism fidelity       PASS / FAIL
B geometry quality         PASS / FAIL
C manufacturing plausibility PASS / REVIEW / FAIL
D standard-eye validation  PASS / FAIL
E optical sanity           PASS / FAIL
F manual reviewer          ACCEPT / REVISE / REJECT
```

任何必需项 FAIL 均不进入 24-carrier 扩展。

## 13. 标准 audit output contract

每个最终 analyzed ZMX 必须自动生成统一 audit package：

```text
audit/<config_id>/
  model.zmx
  layout.png
  fft_mtf_100lpmm.png
  fft_mtf_100lpmm.csv
  cornea_power_map.png
  cornea_power_x_scan.csv
  iol_power_map.png
  iol_power_x_scan.csv
  iol_sag_x_scan.csv
  iol_slope_x_scan.csv
  surface_parameters.csv
  binary4_zones.csv
  ray_footprints.csv
  audit_summary.json
```

布局：

- Liou–Brennan：2D Layout / Cross Section；
- Atchison：3D Layout，能显示 biconic retina、cornea、physical STOP、IOL 和 chief/marginal rays。

FFT MTF：

```text
field = 0 deg
frequency limit = 100 lp/mm
```

首轮仅作为 mandatory audit diagnostic，不替代旧 production MTFA endpoint。

Cornea audit copy：

```text
Power Pupil Map / Spherical Power
radius = 5 mm
sampling = 129 x 129
X scan required
```

IOL isolated audit copy：

```text
n_before = 1.336
n_IOL = 1.460
n_after = 1.336
radius = 3 mm
sampling = 129 x 129
POWP X scan = -3.0 ... +3.0 mm
```

`binary4_zones.csv` 至少包含：

```text
zone
r_inner_mm
r_outer_mm
R_mm
Q
alpha_p2_native
alpha_p4_native
alpha_p6_native
A4_equiv_mm-3
A6_equiv_mm-5
sag_at_inner
sag_at_outer
slope_inner
slope_outer
C0_error
C1_slope_jump
```

## 14. 后续 production 规则

pilot 通过并在 R5 冻结后：

1. R6 重建 `2 Base × 4 Cornea × 3 Platform = 24` physical carriers；
2. 每个 carrier 仍独立求 `P_ijk -> Q_k(P_ijk)`；禁止把 +20 D 的 Q 复制给其他 power；
3. residual 先测试 power-independent normalized parameter set；只有证据显示 carrier curvature 导致机制明显失真时，才讨论 power-specific refit；
4. 即便需要 refit，也只能拟合 mechanism target，不能拟合最终 MTF；
5. R8 完整重跑 `2 × 4 × 3 × 2 State × 2 Pupil = 96` configs；
6. R9 重新形成 48 matched pairs、interaction、censoring 和 figures；
7. R10 单独比较 old-vs-new sensitivity。

首轮重跑尽量保留既有 wavelength、through-focus range、defocus step、MTFa、DOF50 与 censoring 定义，以便把变化主要归因于本次模型定义修订。

## 15. Web / local OpticStudio 协作粒度

为避免过于频繁的 Web ↔ 本地往返，后续采用 phase-gate handoff：

- Web 端：科学合同、文献核对、代码实现/审查、离线测试、生成本地执行说明、检查回传 artifact；
- 本地 zcode / Codex：仅执行必须调用真实 OpticStudio 的批量步骤。

一次本地 handoff 应尽量包含一个完整 phase gate，而不是单个函数级试跑。每份 handoff 至少写明：

```text
branch / commit
exact commands
input scope
expected artifacts
PASS/FAIL conditions
STOP conditions
what to return to Web review
```

预计本地交互节点优先集中在：

1. R2 + R3：新 base-eye + Binary4 MONO equivalence；
2. R4：3 mechanism pilot + audit package；
3. R6/R7：24-carrier rebuild/validation；
4. R8：96-config production rerun。

如某 phase 内出现明确 hard failure，再提前回 Web 修订；不为每个小参数变化单独发起一次 OpticStudio 会话。

## 16. R0 退出条件

R0 完成意味着：

- 物理瞳孔语义已冻结；
- semi-diameter 已冻结；
- retina 类型已冻结，精确参数由 R1 source lock 支持；
- Binary 4 的纯折射使用方式、native coefficient 映射、zone radii、复杂度上限已冻结；
- mechanism-first optimization 和 audit contract 已冻结；
- 旧 evidence 继续只读；
- 尚未运行 OpticStudio。

下一步仅进入 R1 source lock；R1 完成后才允许开始 R2 代码实现。