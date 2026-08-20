# 论文图表计划 — TASK-012 Run72

> 目的：把冻结的 TASK-012 evidence 转换为论文级呈现，而不改变分析定义。  
> 原则：正文优先呈现 interaction、pupil/base sensitivity 与延焦—质量交换；不按单一均值做“最佳组合”排名。

## 1. 呈现原则

1. 所有 effect 固定为 `EDOF − MONO`。
2. DOF50 lower-bound 必须显示 `≥`；peak-window-conditioned 指标必须显式标记。
3. Base 与 Pupil 不得在主图中被静默平均掉。四-strata均值只能用于导航性表格。
4. `ΔMTFa@0D` 与 `ΔTF MTFa mean` 是当前最稳健的质量代价指标；两者在36/36 pair均为负。
5. `distance_peak_mtfa` 只作为辅助质量指标，因为8个 pair 存在 peak-window censoring。
6. WFS-like / RAD-like / HOA-like 保持机制标签，不用商业产品名称替换。
7. 正文结果来自 `TASK_012_PAIR_ANALYSIS.csv`、`TASK_012_INTERACTION_CONTRASTS.csv`、`TASK_012_COUPLING_MATRIX.csv`；现有 PNG 仅作可视化派生，不反向作为数值来源。

---

## 2. 主表

### Table 1. Cornea × Platform 的四-strata描述性汇总

正文保留一个紧凑3×3表，列出：

- Cornea prototype
- Platform mechanism
- 四-strata `ΔDOF50 mean`，保留 bound status
- `ΔMTFa@0D mean`
- `ΔTF MTFa mean`
- DOF方向计数（正/负）
- DOF-censored strata 数
- peak-window-censored strata 数

建议正文表值：

| Cornea × Platform | ΔDOF50 mean, D | ΔMTFa@0D | ΔTF mean | 解释提示 |
| --- | ---: | ---: | ---: | --- |
| A0 × WFS-like | +0.137 | -0.120 | -0.0108 | 温和延焦 |
| A0 × RAD-like | +0.107 | -0.168 | -0.0150 | 温和延焦、更多0D代价 |
| A0 × HOA-like | +0.194 | -0.320 | -0.0524 | 强 pupil dependence |
| B0 × WFS-like | ≥+0.227 | -0.139 | -0.0112 | EPD3-specific coupling |
| B0 × RAD-like | +0.185 | -0.166 | -0.0151 | 4/4 DOF正向 |
| B0 × HOA-like | +0.241 | -0.287 | -0.0506 | EPD3强、EPD5反转 |
| C0 × WFS-like | +0.127 | -0.118 | -0.0083 | 温和延焦 |
| C0 × RAD-like | ≥+0.243 | -0.216 | -0.0092 | 稳定 DOF-oriented coupling |
| C0 × HOA-like | ≥+0.409 | -0.345 | -0.0555 | 最大但高度异质 |

脚注必须说明：mean 是2 base ×2 pupil确定性矩阵的描述性中心，不是总体均值；带 `≥` 为 lower-bound mean。

### Supplementary Table S1. 36-pair完整结果

直接基于 `TASK_012_PAIR_ANALYSIS.csv`，保留：

- base_id
- cornea_id
- platform_label
- pupil_label
- ΔDOF50 + bound status
- ΔMTFa@0D
- ΔTF MTFa mean
- observed peak ΔMTFa
- ΔC40 / ΔC60 / ΔHOA RMS
- pair_peak_censored

该表作为所有正文数值的最终可追踪来源。

### Supplementary Table S2. 预定义 interactions

从 `TASK_012_INTERACTION_CONTRASTS.csv` 筛选正文关注的：

- `(B0-A0)_WFS-(B0-A0)_RAD`
- `(B0-A0)_WFS-(B0-A0)_HOA`
- `(C0-A0)_WFS-(C0-A0)_RAD`
- pupil sensitivity
- base-eye sensitivity

保留 DOF bound interval，不把 lower/upper bound 填成精确值。

---

## 3. 主图

### Figure 1. Base×Pupil 分层的 ΔDOF50 3×3 heatmaps

布局：2×2 panel。

```text
A: LB / EPD3
B: LB / EPD5
C: ATC / EPD3
D: ATC / EPD5
```

每个 panel 为 Cornea(A0/B0/C0) × Platform(WFS-like/RAD-like/HOA-like) 的3×3矩阵。

现有派生文件：

```text
figures/heatmap_delta_dof50_width_d_lb-al2395_epd3.png
figures/heatmap_delta_dof50_width_d_lb-al2395_epd5.png
figures/heatmap_delta_dof50_width_d_atc-m3-al24477_epd3.png
figures/heatmap_delta_dof50_width_d_atc-m3-al24477_epd5.png
```

论文整图应共享同一色标范围；lower-bound cell 必须保留 `≥`。该图是最重要的 interaction overview。

### Figure 2. Base×Pupil 分层的 ΔMTFa@0D 3×3 heatmaps

同 Figure 1 的2×2布局，共享色标。核心目的不是展示“谁最好”，而是与 Figure 1 并列显示 DOF 与 fixed-focus quality 的交换。

现有文件：

```text
figures/heatmap_delta_mtfa_at_zero_d_*.png
```

正文图注应明确：36/36 cell-level pair effects 均为负值。

### Figure 3. 延焦—质量 trade-off

首选 x=`ΔDOF50`，y=`ΔMTFa@0D`；辅助 panel 可用 y=`ΔTF MTFa mean`。

现有文件：

```text
figures/tradeoff_dof50_vs_mtfa_zero.png
figures/tradeoff_dof50_vs_tf_mean.png
```

建议论文版进一步按 platform shape、cornea label 分层，但不使用仅靠颜色才能识别的单一编码；DOF lower-bound 点应使用不同 marker。核心视觉信息是：大部分点向右（延焦增加），但全部位于 y<0。

### Figure 4. 三个代表性 coupling 的贯焦曲线

不展示全部36 pair，以免正文过载；选择机制最有信息量的三组，并同时显示两个 base 和两个 pupil：

1. **B0 × WFS-like**：展示 EPD3 强延焦与 EPD5 消退/反转。
2. **C0 × RAD-like**：展示跨 base/pupil 较稳定的 DOF-oriented coupling。
3. **C0 × HOA-like**：展示 EPD5 的 base-eye 分离。

原始贯焦数据来自 `TASK_011_RUN72_THROUGH_FOCUS.csv`；现有完整3×3 panel：

```text
figures/through_focus_lb-al2395_epd3.png
figures/through_focus_lb-al2395_epd5.png
figures/through_focus_atc-m3-al24477_epd3.png
figures/through_focus_atc-m3-al24477_epd5.png
```

论文版代表性曲线必须使用相同 y 轴范围，并禁止 post-hoc 横向对齐峰值。

### Figure 5. HOA mechanism map

以 `ΔC40` vs `ΔC60` 为核心，按 platform 分组，说明三种 surrogate 的高阶像差路径不同。

现有文件：

```text
figures/mechanism_delta_c40_c60.png
```

正文解释重点：RAD-like EPD5 的 net HOA RMS 对角膜原型方向不同，支持真实 Cornea×Platform coupling。

---

## 4. 补充图

### Figure S1. ΔTF MTFa mean heatmaps

4个 Base×Pupil heatmap 全部进入补充材料，作为“全窗质量均下降”的完整展示。

### Figure S2. Pupil sensitivity

```text
figures/pupil_sensitivity_dof50.png
figures/pupil_sensitivity_mtfa_zero.png
```

用于定量支持 B0×WFS-like 与 HOA-like 的瞳孔依赖。

### Figure S3. Base-eye sensitivity

```text
figures/base_sensitivity_dof50.png
figures/base_sensitivity_mtfa_zero.png
```

重点标出 C0×HOA-like×EPD5 的基础眼分离。

### Figure S4. Peak-window-conditioned trade-off

`tradeoff_dof50_vs_window_peak_mtfa.png` 放补充材料，不作为主质量结论，因为8个 pair 的 observed peak 受预注册搜索窗限制。

---

## 5. Results 文字与图表的对应关系

| Results 小节 | 主证据 | 正文图/表 |
| --- | --- | --- |
| 数据完整性/censoring | analysis evidence JSON | 文字 |
| 总体 trade-off | 36-pair CSV | Fig 3 + Table 1 |
| B0×WFS | interaction CSV | Fig 1, Fig 4 |
| C0×RAD | interaction CSV | Fig 1, Fig 2, Fig 4 |
| HOA-like pupil/base dependence | pair + interaction CSV | Fig 1, Fig 4 |
| 高阶像差机制 | pair CSV C40/C60/HOA RMS | Fig 5 |

---

## 6. 不进入正文的内容

为保持 MVP 论文主线清楚，以下内容不作为正文主结果：

- 全1152 contrasts逐项列举；
- 将9个 cell 强行合成为单一 composite score；
- 按四-strata均值生成“最佳组合排行榜”；
- 把 `ΔF_residual` 当作主要效果终点；
- 在正文以商业产品名称替代 WFS-like/RAD-like/HOA-like；
- 因5个 lower-bound DOF 或8个 peak-window pair 而补跑更宽焦轴。

## 7. 下一步制作要求

正式投稿图制作时只做**呈现层重绘**，不重新分析数据。建议新建单独 manuscript-figure 脚本，从冻结 CSV 直接读取并输出组合图；脚本不得改变任何 TASK-012 数值、censor policy、坐标或统计定义。
