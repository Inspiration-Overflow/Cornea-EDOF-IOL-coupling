# 论文 R8 图表计划 — 2026-08-22

> 目标：把已提交 R8 production 与 offline analysis evidence 转换为论文呈现层，不重新计算 OpticStudio、不改变冻结数据、不沿用旧 Task015 数值。所有数值来源必须是 CSV/JSON；PNG 只用于呈现，不反向作为数字来源。

## 1. 呈现总原则

1. 所有配对效应固定定义为 `EDoF − MONO`。
2. 正文必须保留 R8 DOF50 四类状态：25 exact、19 lower bound、3 upper bound、1 indeterminate。
3. lower bound 显示“≥”，upper bound 显示“≤”；indeterminate 不得用连续色标或单一数值暗示精确大小。
4. 9 个距离峰值搜索窗删失必须在涉及 peak MTFa 的图注中明确标出。
5. 0 D MTFa 和完整贯焦平均 MTFa 在 48/48 配对中均为负，是 R8 最稳定的方向性结果；不得沿用旧稿“47/48”的表述。
6. 两个基础眼和两个物理瞳孔不在主图中静默平均。四条件均值只作为 Table 1 的描述性导航，并保留 bound 状态。
7. 三类人工晶状体只称“波前塑形型延焦”“径向屈光力调制型延焦”“高阶像差调制型延焦”或在方法首次映射时注明 WFS/RAD/HOA；不得换成商业产品名。
8. 48 张 raw through-focus 图全部保留为补充图，不因正文选图而删除。
9. 所有图注明确：本研究是确定性计算光学，不是临床疗效比较。
10. 图表层不得改变 `manual_web_review_required=true` / `automatic_progression_allowed=false` 的研究状态。

---

# 2. 正文表格

## Table 1. 角膜光学表型 × 非衍射延焦机制的四条件 R8 汇总

**数据源：** `docs/evidence/r8_96/MODEL_REVISION_R8_96_COUPLING_MATRIX.csv`

建议列：

- 角膜光学表型；
- 人工晶状体延焦机制；
- 4 个条件数；
- DOF50 effect status；
- DOF50 均值/有效界限；
- DOF50 正/负记录数；
- DOF50 censor 数；
- `ΔMTFa(0 D)` 均值；
- `ΔTF MTFa mean` 均值；
- peak-window censor 数。

正文使用以下 R8 值：

| 角膜 × 机制 | DOF50 汇总 | 正/负 | censor | ΔMTFa(0 D) | ΔTF MTFa mean | peak censor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 未治疗参照 × 波前塑形 | +0.07268 exact | 3/1 | 0 | −0.11017 | −0.00609 | 0 |
| 未治疗参照 × 径向调制 | ≥+0.21466 | 4/0 | 3 | −0.35639 | −0.03891 | 1 |
| 未治疗参照 × 高阶像差 | +0.01497 exact | 2/2 | 0 | −0.27438 | −0.04191 | 0 |
| 近视术后准单焦 × 波前塑形 | +0.14837 exact | 4/0 | 0 | −0.11632 | −0.00812 | 0 |
| 近视术后准单焦 × 径向调制 | ≥+0.29371 | 4/0 | 4 | −0.34974 | −0.04317 | 2 |
| 近视术后准单焦 × 高阶像差 | +0.09644 exact | 4/0 | 0 | −0.26183 | −0.04178 | 1 |
| 连续非球面延焦 × 波前塑形 | ≥+0.60444 | 4/0 | 2 | −0.12735 | −0.00971 | 2 |
| 连续非球面延焦 × 径向调制 | ≥−0.12111 | 2/2 | 4 | −0.28494 | −0.04326 | 0 |
| 连续非球面延焦 × 高阶像差 | ≤+0.13591 | 3/1 | 3 | −0.19859 | −0.03691 | 2 |
| 中央近用径向多焦 × 波前塑形 | ≥+0.17213 | 4/0 | 1 | −0.10952 | −0.00580 | 0 |
| 中央近用径向多焦 × 径向调制 | ≥+0.10497 | 4/0 | 4 | −0.36287 | −0.04038 | 1 |
| 中央近用径向多焦 × 高阶像差 | indeterminate | 4/0* | 2 | −0.29167 | −0.04311 | 0 |

\* 4/0 仅是记录值符号，不解除 indeterminate 状态。

**表注：** 每个单元包含 2 个基础眼 × 2 个瞳孔，共 4 个确定性条件。四条件汇总不是临床总体均值。带“≥”“≤”或 indeterminate 的 DOF50 单元必须按边界数据解释。

---

## Table 2. R8 production 完整性与总体配对结果

**数据源：** production evidence + offline analysis evidence。

建议内容：

```text
configs                         96 / 96 completed
failed configs                  0
matched MONO/EDoF pairs         48
through-focus rows              1440
planes/config                   15
physical pupils                 3 mm / 5 mm
DOF50 exact                     25
DOF50 lower bound               19
DOF50 upper bound               3
DOF50 indeterminate             1
peak-window censored pairs      9
recorded ΔDOF50 mean            +0.16694 D
recorded ΔDOF50 positive/negative 42 / 6
ΔMTFa(0 D) negative             48 / 48
mean ΔMTFa(0 D)                 -0.23698
ΔTF MTFa mean negative          48 / 48
mean ΔTF MTFa                   -0.02993
```

**表注：** +0.16694 D 是包含删失记录值的描述性算术均值，不是 censor-adjusted estimate。

---

# 3. 补充表格

## Supplementary Table S1. 全部 48 个 matched pair

**直接数据源：** `docs/evidence/r8_96/MODEL_REVISION_R8_96_PAIR_ANALYSIS.csv`

读者版建议列：

- 基础模型眼；
- 角膜光学表型；
- 延焦机制；
- 瞳孔；
- `ΔDOF50`；
- DOF50 effect status；
- MONO/EDoF censor flags；
- `Δdistance-peak MTFa`；
- peak-window censor flag；
- `ΔMTFa(0 D)`；
- `ΔTF MTFa mean`；
- `ΔC4⁰`；
- `ΔC6⁰`；
- `ΔHOA RMS`；
- 工程 pair key（置于表尾用于追溯）。

不要把 lower/upper/indeterminate 强制格式化为普通小数排名。

## Supplementary Table S2. 96 个配置的绝对结果

**直接数据源：** `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_CONFIG_RESULTS.csv`

用于追溯每个 MONO/EDoF 配置的：distance peak、MTFa@0D、DOF50 crossings/width、censor flags、TF mean、C4⁰/C6⁰/HOA RMS、analysis settings hash、model SHA 和 entity fingerprint。

## Supplementary Data S3. 1440 行贯焦曲线

**直接数据源：** `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_THROUGH_FOCUS.csv`

不建议在正文排成静态长表；作为机器可读补充数据提供，并与 48 张 raw through-focus 图一一对应。

> 旧 Task015 的“36 行术后相对未治疗参照 S2”不再作为 R8 正文数值来源。本任务没有一个新的、独立提交的 36 行 R8 interaction table，因此不得从旧 Task015 S2 搬运净耦合数字。

---

# 4. 正文主图

## Figure 1. R8 DOF50 配对效应：基础眼 × 瞳孔四面板热图

将下列 4 张已提交 PNG 作为 2×2 panel source：

- `docs/evidence/r8_96/figures/summary/heatmap_delta_dof50_width_d_lb-al2395_epd3.png`
- `docs/evidence/r8_96/figures/summary/heatmap_delta_dof50_width_d_lb-al2395_epd5.png`
- `docs/evidence/r8_96/figures/summary/heatmap_delta_dof50_width_d_atc-m3-al24477_epd3.png`
- `docs/evidence/r8_96/figures/summary/heatmap_delta_dof50_width_d_atc-m3-al24477_epd5.png`

**建议图注：** 每个单元表示同一基础眼、角膜表型、人工晶状体机制和物理瞳孔下 `EDoF − MONO` 的 DOF50 记录效应。R8 共有 25 exact、19 lower-bound、3 upper-bound 和 1 indeterminate pair effect；边界状态必须在 panel 注释或配套表中保留。颜色用于显示记录值，不覆盖 censor status。

---

## Figure 2. R8 0 D MTFa 配对效应：基础眼 × 瞳孔四面板热图

panel source：

- `heatmap_delta_mtfa_at_zero_d_lb-al2395_epd3.png`
- `heatmap_delta_mtfa_at_zero_d_lb-al2395_epd5.png`
- `heatmap_delta_mtfa_at_zero_d_atc-m3-al24477_epd3.png`
- `heatmap_delta_mtfa_at_zero_d_atc-m3-al24477_epd5.png`

完整路径均位于 `docs/evidence/r8_96/figures/summary/`。

**建议图注：** 48/48 个 matched pair 的 `ΔMTFa(0 D)` 均为负，均值 −0.23698；图的目的在于显示负向幅度的条件依赖，而不是寻找方向例外。

---

## Figure 3. 焦深—光学质量交换

正文建议两个 panel：

- A：`docs/evidence/r8_96/figures/summary/tradeoff_dof50_vs_mtfa_zero.png`
- B：`docs/evidence/r8_96/figures/summary/tradeoff_dof50_vs_tf_mean.png`

第三张：

- `docs/evidence/r8_96/figures/summary/tradeoff_dof50_vs_window_peak_mtfa.png`

建议放补充材料或作为 panel C，并显式注明 9 个 peak-window censored pair。

**建议图注：** 横轴 DOF50 包含 exact、lower-bound、upper-bound 和 indeterminate 状态；边界点不得按普通精确散点解释。0 D MTFa 与完整贯焦平均 MTFa 在 48/48 pair 中均为负，显示焦深扩展伴随焦轴光学质量重新分配。

---

## Figure 4. 完整贯焦总览：两个基础眼 × 两个瞳孔

使用已提交的 4 张 summary panel：

- `docs/evidence/r8_96/figures/summary/through_focus_panel_lb-al2395_epd3.png`
- `docs/evidence/r8_96/figures/summary/through_focus_panel_lb-al2395_epd5.png`
- `docs/evidence/r8_96/figures/summary/through_focus_panel_atc-m3-al24477_epd3.png`
- `docs/evidence/r8_96/figures/summary/through_focus_panel_atc-m3-al24477_epd5.png`

**建议图注：** 每条曲线均来自固定 +0.50 至 −3.00 D、0.25 D 步长的 15 个视网膜离焦平面。曲线不做峰值横向配准，不扩大窗口，不根据视觉印象重新定义 DOF50。

---

## Figure 5. 高阶像差机制图

source：

- `docs/evidence/r8_96/figures/summary/mechanism_delta_c40_c60.png`

**建议图注：** 展示 48 个 matched pair 的 `ΔC4⁰` 与 `ΔC6⁰`，用于说明三类机制 surrogate 采取不同的高阶波前路径。总体 `ΔC4⁰` 均值 −0.02752 μm，35/48 为负；`ΔC6⁰` 均值 −0.00463 μm，24/48 为负、24/48 为正。图不用于建立商业 IOL 优劣阈值。

---

# 5. 补充图

## Supplementary Figure Set S1 — 48 张 raw through-focus 图

`docs/evidence/r8_96/figures/raw/` 中全部 48 张图完整保留。命名模式：

`through_focus_<base>_<cornea>_<platform>_<pupil>.png`

每张图对应一个 matched MONO/EDoF pair，曲线来自 15 个冻结离焦平面。不得抽样删除。

## Supplementary Figure Set S2 — 完整 TF mean heatmaps

4 张：

- `heatmap_delta_tf_mtfa_mean_lb-al2395_epd3.png`
- `heatmap_delta_tf_mtfa_mean_lb-al2395_epd5.png`
- `heatmap_delta_tf_mtfa_mean_atc-m3-al24477_epd3.png`
- `heatmap_delta_tf_mtfa_mean_atc-m3-al24477_epd5.png`

用于支持“48/48 `ΔTF MTFa mean` 为负”的分层幅度展示。

## Supplementary Figure Set S3 — 瞳孔与基础眼敏感性

已提交：

- `pupil_sensitivity_dof50.png`
- `base_sensitivity_dof50.png`
- `pupil_sensitivity_mtfa_zero.png`
- `base_sensitivity_mtfa_zero.png`

均位于 `docs/evidence/r8_96/figures/summary/`。

这些图只描述冻结矩阵内的条件敏感性，不构造统计交互显著性。

## Supplementary Figure Set S4 — peak-window trade-off

`tradeoff_dof50_vs_window_peak_mtfa.png` 必须明确 9 个 peak-window censored pair；不得把边界峰值当作真实无限窗峰值。

---

# 6. Figure set 完整性

Offline evidence 的正式记录：

```text
figure_count = 72
raw figures = 48
summary figures = 24
```

24 张 summary figure 的构成与 evidence refs 一致：

```text
12 heatmaps
4 through-focus panels
3 trade-off figures
2 pupil-sensitivity figures
2 base-sensitivity figures
1 mechanism C40/C60 figure
= 24
```

总计：

```text
48 raw + 24 summary = 72
```

任何投稿级重排只允许改变 panel 组合、标题、字体、图例和 caption；不得改变曲线点、数值、删失标记、颜色所对应的数字、离焦窗口或源文件。

---

# 7. 正文结果—图表对应关系

| 结果主题 | 权威数据 | 正文呈现 |
| --- | --- | --- |
| 96/48/1440 完整性 | production evidence | Table 2 + 文字 |
| 25/19/3/1 DOF50 censoring | offline evidence / pair analysis | Table 2 + Figure 1 |
| 42 正 / 6 负记录 ΔDOF50 | offline evidence | Table 2 + Figure 3 |
| 48/48 `ΔMTFa(0D)<0` | offline evidence | Figure 2 + Figure 3A |
| 48/48 `ΔTF MTFa mean<0` | offline evidence | Figure 3B + Supp S2 |
| 12 角膜 × 机制汇总 | coupling matrix | Table 1 |
| 15-plane 曲线形态 | through-focus CSV | Figure 4 + raw S1 |
| C4⁰/C6⁰ 机制差异 | pair analysis | Figure 5 |
| pupil/base sensitivity | summary figures | Supplementary S3 |

---

# 8. Caption 禁止性清单

图表 caption 不得出现：

- “clinically superior / 临床更优”；
- “best IOL / 最佳人工晶状体”；
- “statistically significant / 显著差异”，除非未来另有预注册统计分析；
- “mean benefit +0.16694 D”而不说明 censoring；
- 把 `B0 × RAD ≥−0.12111 D` 写成确定负均值；
- 把 `C0 × HOA indeterminate` 写成确定正效应；
- 把 9 个 peak-window boundary 值写成真实峰值；
- 把 local R8 PASS 写成 formal scientific lock 或 clinical validation。

---

# 9. 图表来源与审核门

所有图表来自已提交 R8 evidence。图表排版完成后仍需进行人工 Web 科学审核，重点检查：

1. bound/indeterminate 标记是否在视觉上保留；
2. panel 是否错误平均两个基础眼或两个瞳孔；
3. caption 是否与 `48/48` MTFa 负向结果一致；
4. 是否误搬 Task015 数值；
5. 是否有任何商业排名或临床外推；
6. 图件是否仍能追溯到 `docs/evidence/r8_96/figures/`。

图表计划完成不改变：

```text
manual_web_review_required = true
automatic_progression_allowed = false
formal_scientific_lock = false
```
