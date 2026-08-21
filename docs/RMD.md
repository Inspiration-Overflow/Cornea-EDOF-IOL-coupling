# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** 当前项目唯一执行路线图。坚持 MVP / 奥卡姆剃刀：科学 acquisition、analysis 和完整原始 figures 已结束；现在只做投稿呈现、语义化命名和最终格式 QC。

## Metadata

- document_id: `RMD-0001`
- version: `2.9`
- status: `active`
- last_updated: `2026-08-20`
- active_branch: `feat/task-011-run72`
- PR: `#26 Draft / open / unmerged`
- production acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- production sampling: `128`
- frequency scale: `paired_residual_free_MONO_EFFL`

---

# 1. Frozen engineering history

```text
baseline = MVP_2026_v2
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-009 acquisition = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
legacy TASK-011/012 = frozen engineering history
```

Legacy direct-cornea `A0/B0/C0` 不再作为投稿主分析。

---

# 2. Accepted final acquisition layer

## TASK-013 — 未治疗参照角膜

```text
internal ID = N0
run = task013-183dcffcd1da4f1cb1a219d9eedb39db
raw evidence commit = 38ad14a12a18b1a7a30d259cde644d360442f57b
24 configs / 360 TF rows / 12 pairs
6/6 exact-carrier validations PASS
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

## TASK-014 — 三个顶点距规范化术后角膜

读者可见名称：近视术后准单焦角膜、连续非球面角膜延焦原型、中央近用径向多焦角膜。内部 ID 仅为 `A0V12 / B0V12 / C0V12`。

```text
contract = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle = -3.00 D
vertex = 12 mm
corneal-plane treatment = -2.895752895753 D
run = task014-e270a185207543149c21da83202c4b73
raw evidence commit = 6ffb2eaf88e386729aa3965c0f12c9b7ca134081
72 configs / 1080 TF rows / 36 pairs
18/18 exact-carrier validations PASS
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

TASK-013/014 均冻结：**不重跑，不扩展 focus window，不修改 residual/B0/vertex contract。**

---

# 3. TASK-015 — accepted final 96-config analysis

正式科学结构：

```text
2 基础眼
× 4 角膜光学条件（未治疗参照 + 3 个术后表型）
× 3 人工晶状体延焦机制
× 匹配单焦 / EDoF
× 3 mm / 5 mm 瞳孔
= 96 configs
= 1440 TF rows
= 48 matched pairs
```

读者可见人工晶状体机制统一写为：波前塑形型延焦、径向屈光力调制型延焦、高阶像差调制型延焦。内部 ID `WFS / RAD / HOA` 只用于 provenance。

唯一正式 coupling：

```text
术后角膜中的 (EDoF - 匹配单焦)
-
同条件未治疗参照角膜中的 (EDoF - 匹配单焦)
```

正式结果：

```text
DOF50 增加 = 35/48
DOF50 减少 = 13/48
DOF50 = 43 exact + 5 lower_bound
距离峰值搜索窗删失 = 10
0 D MTFa 下降 = 47/48
全贯焦平均 MTFa 下降 = 48/48
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

主要 interaction：连续非球面角膜延焦原型 × 波前塑形型延焦在 3 mm 瞳孔强增强；连续非球面角膜延焦原型 × 径向屈光力调制型延焦在 5 mm 瞳孔增强；中央近用径向多焦角膜 × 径向屈光力调制型延焦在 5 mm 瞳孔强增强且两基础眼均为 lower bound；中央近用径向多焦角膜 × 高阶像差调制型延焦在 3 mm 相对参照减弱、5 mm 强增强。小幅基础眼间符号不一致的 effect 仅解释为 near-zero/base-dependent。

所有结果继续按焦深扩展—光学质量再分配解释，不建立“最佳人工晶状体排名”。

---

# 4. Complete figure supplement — accepted science, presentation relabeling allowed

```text
portability-only CRLF/LF fix = cfb659063c8177223d29711f6b778ec566be3bc5
formal figure commit = bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5
raw figures = 48
summary figures = 24
total PNG = 72
manifest entries = 72
source TF rows = 1440
figure review acceptance = PASS
```

48 张 raw figures 必须全部保留。正式 figure commit 锁定科学曲线、采样点和 censoring。后续可读标签版只允许修改读者可见文字与排版，不允许重算曲线、改变数值、重采样、peak-align 或删除边界标记。

---

# 5. Manuscript layer — semantic rewrite complete

最终自包含稿：

```text
docs/MANUSCRIPT_DRAFT_96_CONFIG_2026-08-20.md
```

辅助模块：

```text
docs/MANUSCRIPT_INTRODUCTION_DRAFT_2026-08-20.md
docs/MANUSCRIPT_ABSTRACT_METHODS_DRAFT_2026-08-20.md
docs/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT_2026-08-20.md
docs/MANUSCRIPT_FIGURE_TABLE_PLAN_2026-08-20.md
```

正文已完成语义化重写。工程 ID 只允许在 Methods 的命名映射处首次出现；Results、Discussion、Conclusion、Table 1 和正文图注不再以 `N0/A0V12/B0V12/C0V12`、`LB/ATC`、`WFS/RAD/HOA`、`EPD3/EPD5`、`MONO` 等变量名作为主要称谓。

展示标签规范：

```text
docs/MANUSCRIPT_DISPLAY_LABELS_2026-08-20.md
```

科学 QC：

```text
docs/MANUSCRIPT_SCIENTIFIC_QC_2026-08-20.md
scientific / numeric / censoring / provenance / reference / raw-figure QC = PASS
```

正文实际引用的 6 篇外部文献已核对 PubMed/DOI；未引用条目不为了“保留参考文献”而扩写正文。

---

# 6. Tables

冻结 source tables 保持机器可追溯：

```text
source S1 = docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv            # 48 rows
source S2 = docs/evidence/task015/TASK_015_SUPPLEMENTARY_TABLE_S2.csv   # 36 rows
```

投稿展示版必须另行生成，使用完整中文光学名称作为前置列，并把内部 ID 移到表尾追溯列。不得为了易读性改写 source evidence。

---

# 7. Main manuscript figures — presentation only

主文计划保留 5 张组合图：

1. DOF50 改变量 4-panel heatmaps；
2. 0 D MTFa 改变量 4-panel heatmaps；
3. 焦深扩展—光学质量交换；
4. 未治疗参照 vs 术后表型的代表性原始贯焦曲线；
5. 完整眼 C4⁰/C6⁰ 高阶像差机制图。

所有读者可见标签使用完整名称：Liou–Brennan 模型眼、Atchison −3 D 近视模型眼、未治疗参照角膜、三个术后角膜表型、三类延焦机制、3 mm/5 mm 瞳孔、匹配单焦对照。文件名可保留内部 ID。

---

# 8. Residual validation rule remains frozen

历史 carrier-power envelope = validation coverage classifier only。

Schema-v2 hard gate：

```text
STD_IOL_EYE_2024 / EPD6 / imported residual readback
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
actual-eye MONO/EDOF EPD5 ray health PASS
```

Actual-eye SSAG Mode-0 piston/defocus 仅为 diagnostic；不得为 RAD 建例外。

---

# 9. Current STOP rules

立即停止，如果任何工作试图：重跑 TASK-011/013/014；扩展 through-focus 或 peak-search window；修改 residual、B0.20、vertex contract、sampling、frequency scale；把 lower bound 或 peak-window-conditioned 值改写成精确值；把 legacy direct-cornea A0/B0/C0 数字重新混入投稿主结果；删除 48 张 raw figures；或将机制 surrogate 转成商业人工晶状体排名或患者级推荐。

---

# 10. MVP 明确不做

不做 patient-specific optimization、多色或偏心/倾斜扩展、新 composite score、新 acquisition、retune B0/residual、新数据库/GUI/调度框架，也不为排版方便重新分析科学数据。

---

# 11. Current shortest path

```text
A. archive/read-QC the reader-facing main figures
B. add publication-facing S1/S2 with semantic labels
C. language/journal formatting
D. final evidence/figure/table/manuscript repo QC
E. only then decide PR ready/merge under separate explicit authorization
```

**当前不需要 ZCode 或 OpticStudio。** PR #26 继续保持 Draft / open / unmerged。
