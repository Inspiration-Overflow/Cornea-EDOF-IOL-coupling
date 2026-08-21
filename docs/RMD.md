# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** 当前项目唯一执行路线图。坚持 MVP / 奥卡姆剃刀：科学 acquisition、analysis 和完整原始 figures 已结束；现在只做投稿呈现与最终格式 QC。

## Metadata

- document_id: `RMD-0001`
- version: `2.8`
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

## TASK-013 — N0

```text
run = task013-183dcffcd1da4f1cb1a219d9eedb39db
raw evidence commit = 38ad14a12a18b1a7a30d259cde644d360442f57b
24 configs / 360 TF rows / 12 pairs
6/6 exact-carrier validations PASS
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

## TASK-014 — A0V12 / B0V12 / C0V12

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

```text
2 Base
× 4 Cornea = N0 / A0V12 / B0V12 / C0V12
× 3 Platform
× MONO/EDOF
× EPD3/EPD5
= 96 configs
= 1440 TF rows
= 48 matched pairs
```

唯一正式 coupling：

```text
(EDOF - MONO)_postop - (EDOF - MONO)_N0
```

正式结果：

```text
ΔDOF50 > 0 = 35/48
ΔDOF50 < 0 = 13/48
DOF50 = 43 exact + 5 lower_bound
peak-window censored = 10
ΔMTFa@0D < 0 = 47/48
ΔTF MTFa mean < 0 = 48/48
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

主要 interaction：

- B0V12×WFS-like：EPD3 强增强，两基础眼均为 lower bound；
- B0V12×RAD-like：主要增强位于 EPD5；
- C0V12×RAD-like：EPD5 强增强，两基础眼均为 lower bound；
- C0V12×HOA-like：EPD3 相对 N0减弱，EPD5 强增强；
- 小幅基础眼间符号不一致的 effect 仅解释为 near-zero/base-dependent。

所有结果继续按焦深扩展—光学质量再分配解释，不建立“最佳 IOL 排名”。

---

# 4. Complete figure supplement — accepted

```text
portability-only CRLF/LF fix
= cfb659063c8177223d29711f6b778ec566be3bc5

formal figure commit
= bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5

raw figures = 48
summary figures = 24
total PNG = 72
manifest entries = 72
source TF rows = 1440
figure review acceptance = PASS
```

目录：

```text
docs/evidence/task015/figures/raw/
docs/evidence/task015/figures/summary/
docs/evidence/task015/figures/TASK_015_FIGURE_MANIFEST.json
```

**48张 raw figures 必须全部保留。** 正文可以少选，但不能删除或抽样替代完整补充图。

---

# 5. Manuscript layer

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

补充表：

```text
S1 = docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv      # 48 rows
S2 = docs/evidence/task015/TASK_015_SUPPLEMENTARY_TABLE_S2.csv  # 36 rows
```

科学 QC：

```text
docs/MANUSCRIPT_SCIENTIFIC_QC_2026-08-20.md
scientific / numeric / censoring / provenance / reference / raw-figure QC = PASS
```

正文实际引用的6篇外部文献已核对 PubMed/DOI；未引用条目不为了“保留参考文献”而扩写正文。

---

# 6. Main manuscript figures — presentation only

Web 端已从正式 figure supplement 做5张组合主图：

```text
Figure 1 = 4-panel ΔDOF50 heatmaps
Figure 2 = 4-panel ΔMTFa@0D heatmaps
Figure 3 = 2-panel extension-quality trade-off
Figure 4 = 12-panel N0 vs postop raw through-focus comparison
Figure 5 = whole-eye HOA mechanism map
```

这些仅做排版组合：不重新计算、不重采样、不 peak-align、不改变 censoring，也不替代72张正式图。

在视觉样式确认前，不需要把组合图提升为新的 scientific evidence。

---

# 7. Residual validation rule remains frozen

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

# 8. Current STOP rules

立即停止，如果任何工作试图：

1. 重跑 TASK-011/013/014；
2. 扩展 through-focus 或 peak-search window；
3. 修改 residual、B0.20、vertex contract、sampling、frequency scale；
4. 把 lower bound / peak-window-conditioned 值改写成精确值；
5. 把 legacy A0/B0/C0 数字重新混入投稿主结果；
6. 删除48张 raw figures 以简化叙事；
7. 将机制 surrogate 转成商业 IOL 排名或患者级推荐。

---

# 9. MVP 明确不做

- patient-specific optimization；
- 多色、偏心/倾斜扩展；
- 新 composite score；
- 新 acquisition；
- retune B0/residual；
- 新数据库/GUI/调度框架；
- 为排版方便重新分析科学数据。

---

# 10. Current shortest path

```text
A. visual QC of the 5 manuscript composite figures
B. finalize figure captions + Table 1/S1/S2 formatting
C. journal/style/language formatting
D. final repo/PR review
E. only then decide PR ready/merge under separate explicit authorization
```

**当前不需要 ZCode 或 OpticStudio。** PR #26 继续保持 Draft / open / unmerged。
