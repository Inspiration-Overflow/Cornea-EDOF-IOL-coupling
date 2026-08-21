# 论文图表计划 — accepted 96-config layer

> 目的：把冻结的 TASK-013/014/015 evidence 转换为投稿级呈现，而不改变分析定义。  
> 原则：正文突出 N0-referenced interaction、pupil/base dependence 与焦深—质量交换；**48张逐 pair 原始贯焦图全部保留在补充材料中，不因正文简化而删除。**

## 1. 呈现原则

1. 所有 paired effect 固定为 `EDOF − MONO`。
2. 术后耦合固定为 `(EDOF−MONO)_postop − (EDOF−MONO)_N0`。
3. DOF50 lower-bound 必须显示 `≥`；peak-window-conditioned 指标必须显式标记。
4. Base 与 Pupil 不得在主图中被静默平均掉；4-strata cell mean 仅作导航性描述。
5. `ΔTF MTFa mean` 是最稳健的全窗质量代价指标，48/48 pair均为负；`ΔMTFa@0D` 在47/48 pair为负。
6. distance-peak MTFa 只作为辅助质量指标，因为10个 pair 存在 peak-window censoring。
7. WFS-like / RAD-like / HOA-like 保持机制标签，不用商业产品名称替换。
8. 数值来源只允许 accepted structured evidence；PNG 仅作为可视化派生，不反向作为数值来源。

---

## 2. 主表

### Table 1. Cornea × Platform 的四-strata描述性汇总

正文保留一个紧凑4×3表，列出：

- Cornea condition；
- Platform mechanism；
- 四-strata `ΔDOF50 mean`，保留 bound status；
- `ΔMTFa@0D mean`；
- `ΔTF MTFa mean`；
- DOF方向计数；
- DOF-censored strata 数；
- peak-window-censored strata 数。

建议正文表值：

| Cornea × Platform | ΔDOF50 mean, D | ΔMTFa@0D | ΔTF mean | 解释提示 |
| --- | ---: | ---: | ---: | --- |
| N0 × WFS-like | +0.061 | -0.117 | -0.0094 | residual 基线、pupil-dependent |
| N0 × RAD-like | +0.041 | -0.147 | -0.0117 | residual 基线、pupil-dependent |
| N0 × HOA-like | +0.221 | -0.328 | -0.0542 | 强基线 pupil dependence |
| A0V12 × WFS-like | +0.139 | -0.120 | -0.0106 | 温和一致增强 |
| A0V12 × RAD-like | +0.078 | -0.167 | -0.0146 | EPD3减弱、EPD5增强 |
| A0V12 × HOA-like | +0.193 | -0.321 | -0.0525 | EPD3减弱、EPD5轻度增强 |
| B0V12 × WFS-like | ≥+0.224 | -0.138 | -0.0113 | EPD3 interaction最明显 |
| B0V12 × RAD-like | +0.196 | -0.166 | -0.0152 | EPD5 interaction明显 |
| B0V12 × HOA-like | +0.241 | -0.288 | -0.0507 | 相对N0整体接近零 |
| C0V12 × WFS-like | +0.124 | -0.118 | -0.0081 | EPD3近零、EPD5增强 |
| C0V12 × RAD-like | ≥+0.242 | -0.216 | -0.0091 | EPD5强增强、lower bound |
| C0V12 × HOA-like | ≥+0.432 | -0.346 | -0.0553 | EPD5强增强、强质量再分配 |

脚注说明：mean 是2 base ×2 pupil确定性矩阵的描述性中心，不是临床总体均值；带 `≥` 为 lower-bound mean。

### Supplementary Table S1. 48-pair完整结果

直接基于 `docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv`，保留：

- base_id；
- cornea_id；
- platform_label；
- pupil_label；
- ΔDOF50 + bound status；
- ΔMTFa@0D；
- ΔTF MTFa mean；
- observed peak ΔMTFa；
- ΔC4⁰ / ΔC6⁰ / ΔHOA RMS；
- pair_peak_censored。

该表作为正文 paired 数值的最终可追踪来源。

### Supplementary Table S2. N0-referenced postoperative interactions

由 TASK-015 确定性重建函数从 accepted TASK-013/014 evidence 生成，不要求仓库另存冗余288行 CSV。投稿表只保留最相关的 `ΔDOF50`、`ΔMTFa@0D` 和 `ΔTF MTFa mean`，按：

```text
Base × Postop Cornea × Platform × Pupil
```

列出，并保留 DOF bound status。

---

## 3. 正文主图

### Figure 1. Base×Pupil 分层的 ΔDOF50 4×3 heatmaps

布局：2×2 panel：

```text
A: LB / EPD3
B: LB / EPD5
C: ATC / EPD3
D: ATC / EPD5
```

每个 panel 为 Cornea(N0/A0V12/B0V12/C0V12) × Platform(WFS-like/RAD-like/HOA-like) 的4×3矩阵，共享色标。lower-bound cell 必须保留 `≥`。

正式来源：

```text
docs/evidence/task015/figures/summary/heatmap_delta_dof50_width_d_*.png
```

### Figure 2. Base×Pupil 分层的 ΔMTFa@0D 4×3 heatmaps

同 Figure 1 的2×2布局，共享色标。图注强调：47/48 pair为负；唯一正值为 ATC+N0+RAD-like+EPD5，但其 `ΔTF MTFa mean` 仍为负。

正式来源：

```text
docs/evidence/task015/figures/summary/heatmap_delta_mtfa_at_zero_d_*.png
```

### Figure 3. 延焦—质量 trade-off

主 panel：x=`ΔDOF50`，y=`ΔMTFa@0D`；辅助 panel：y=`ΔTF MTFa mean`。

正式来源：

```text
docs/evidence/task015/figures/summary/tradeoff_dof50_vs_mtfa_zero.png
docs/evidence/task015/figures/summary/tradeoff_dof50_vs_tf_mean.png
```

DOF lower-bound 点使用独立 marker；核心视觉信息是大部分组合可增加焦深，但完整贯焦平均质量48/48下降。

### Figure 4. 代表性 N0-referenced coupling 的贯焦曲线

正文只选少量机制最有信息量的 raw curves，但不替代补充材料中的48张全量图。建议包括：

1. N0 × WFS-like：作为同机制内部参照；
2. B0V12 × WFS-like × EPD3：小瞳孔强增强、lower bound；
3. C0V12 × RAD-like × EPD5：两基础眼强增强、lower bound；
4. C0V12 × HOA-like × EPD5：强增强与明显质量再分配。

所有代表性图均从 `docs/evidence/task015/figures/raw/` 直接选取，不重新平移峰值、不改纵横轴定义。

### Figure 5. Whole-eye HOA mechanism map

正式来源：

```text
docs/evidence/task015/figures/summary/mechanism_delta_c40_c60.png
```

用于说明三种 surrogate 保持不同的 ΔC4⁰/ΔC6⁰机制路径，并为 N0-referenced coupling 提供波前机制背景。

---

## 4. 完整补充图 — 不抽样

### Supplementary Figure Set S1. 48张 raw through-focus figures

**全部保留。**

目录：

```text
docs/evidence/task015/figures/raw/
```

覆盖：

```text
2 Base × 4 Cornea × 3 Platform × 2 Pupil = 48 matched pairs
```

每张图同时显示 MONO + EDOF 的15-plane MTFa曲线，并显式保留 DOF50 censoring / peak-window censoring 标记。

### Supplementary Figure Set S2. 4张完整4×3 through-focus panels

```text
docs/evidence/task015/figures/summary/through_focus_*.png
```

分别为 LB/ATC × EPD3/EPD5，用于快速浏览全部12个 Cornea×Platform 条件。

### Supplementary Figure Set S3. ΔTF MTFa mean heatmaps

4张 Base×Pupil heatmaps 全部进入补充材料，完整展示48/48 `ΔTF MTFa mean<0` 的结构。

### Supplementary Figure Set S4. Pupil/base sensitivity

保留4张：

```text
pupil_sensitivity_dof50.png
pupil_sensitivity_mtfa_zero.png
base_sensitivity_dof50.png
base_sensitivity_mtfa_zero.png
```

### Supplementary Figure Set S5. Peak-window-conditioned trade-off

```text
tradeoff_dof50_vs_window_peak_mtfa.png
```

放补充材料，不作为主要质量结论，因为10个 pair 的 observed peak 受预注册搜索窗限制。

---

## 5. 正文结果与图表对应

| Results 小节 | 主证据 | 正文图/表 |
| --- | --- | --- |
| 数据完整性/censoring | TASK-015 analysis evidence | 文字 |
| 总体 trade-off | 48-pair CSV | Fig 3 + Table 1 |
| N0 residual baseline | N0 pair rows | Fig 1/2 + Fig 4 |
| A0V12 modulation | N0-referenced interactions | Fig 1/2 |
| B0V12×WFS/RAD | N0-referenced interactions | Fig 1 + Fig 4 |
| C0V12×RAD/HOA | N0-referenced interactions | Fig 1/2 + Fig 4 |
| 高阶像差机制 | pair CSV C4⁰/C6⁰/HOA RMS | Fig 5 |

---

## 6. 正式 figure provenance

完整72张 figure supplement 已归档：

```text
figure commit = bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5
render code commit = cfb659063c8177223d29711f6b778ec566be3bc5
manifest = docs/evidence/task015/figures/TASK_015_FIGURE_MANIFEST.json
figure review = docs/evidence/task015/TASK_015_FIGURE_REVIEW.json
```

数量：

```text
raw = 48
summary = 24
total PNG = 72
manifest entries = 72
source TF rows = 1440
OpticStudio used for render = false
```

跨平台 PNG 字节完全相同不作为科学 gate；正式一次 render 的 manifest 负责绑定该次文件 identity。

---

## 7. 不进入正文的内容

为保持 MVP 论文主线清楚，以下内容不作为正文主结果：

- 把288个 outcome-specific N0 interactions 全部逐项列举；
- 将12个 cell 强行合成为单一 composite score；
- 按四-strata均值生成“最佳组合排行榜”；
- 把 `ΔF_residual` 当作主要效果终点；
- 以商业产品名称替代 WFS-like/RAD-like/HOA-like；
- 因5个 lower-bound DOF 或10个 peak-window pair 而补跑更宽焦轴；
- 删除48张 raw figure 只保留“好看的”代表图。

## 8. 下一步

只剩投稿层整理：

1. 从已归档 summary/raw figures 组合正文5张主图，不重新分析；
2. 生成 Supplementary Table S1/S2；
3. 合并 Introduction、Methods、Results、Discussion 为单一稿件；
4. 完成 evidence / number / figure caption / reference QC。
