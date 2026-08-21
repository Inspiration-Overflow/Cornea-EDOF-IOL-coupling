# MANUSCRIPT SCIENTIFIC QC — accepted 96-config layer

## Status

```text
scientific / numeric / provenance QC = PASS
presentation / journal-format QC = PENDING
OpticStudio rerun required = NO
```

本 QC 只判断最终投稿主分析、数字、censoring、figure provenance 与参考文献是否与 accepted evidence 一致；不把期刊版式或组合主图的视觉样式提前视为科学 gate。

---

## 1. Canonical source layer

投稿主分析只允许：

```text
TASK-013 N0 raw evidence commit
= 38ad14a12a18b1a7a30d259cde644d360442f57b

TASK-014 A0V12/B0V12/C0V12 raw evidence commit
= 6ffb2eaf88e386729aa3965c0f12c9b7ca134081

TASK-015 analysis
= PASS_WITH_SCIENTIFIC_CAVEATS

TASK-015 formal figure commit
= bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5

TASK-015 figure review
= PASS
```

Legacy direct-cornea `A0/B0/C0` TASK-011/012 仅为工程历史，不作为最终投稿主结果。

---

## 2. Final model / prescription identity

必须同时满足：

```text
Base eyes = 2
Corneas = N0 / A0V12 / B0V12 / C0V12
Platforms = WFS-like / RAD-like / HOA-like
Pupils = EPD3 / EPD5
Optic states = MONO / EDOF
physical carriers = 24
configs = 96
matched pairs = 48
through-focus rows = 1440
```

术后处方语义：

```text
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane equivalent = -2.895752895753 D
```

ATC source refraction 只定义基础眼表型，不再次叠加到手术处方。

QC：**PASS**。

---

## 3. Primary outcome counts

最终整合稿必须保持：

```text
ΔDOF50 > 0 = 35 / 48
ΔDOF50 < 0 = 13 / 48
DOF50 exact = 43
DOF50 lower_bound = 5
pair peak-window censored = 10
ΔMTFa@0D < 0 = 47 / 48
ΔTF MTFa mean < 0 = 48 / 48
```

唯一 `ΔMTFa@0D > 0` 条件：

```text
ATC_M3_AL24477 × N0 × RAD-like × EPD5
ΔMTFa@0D ≈ +0.0184
ΔTF MTFa mean ≈ -0.00731
```

因此稿件不得将其解释为无代价增益。

QC：**PASS**。

---

## 4. N0-referenced coupling definition

唯一正式术后 coupling 定义：

```text
(EDOF - MONO)_postop - (EDOF - MONO)_N0
```

同一 Base×Platform×Pupil 内进行比较。

关键 DOF50 interaction 与稿件一致：

```text
B0V12 × WFS-like × EPD3
LB  >= +0.266 D
ATC >= +0.260 D

B0V12 × RAD-like × EPD5
LB  +0.275 D
ATC +0.307 D

C0V12 × RAD-like × EPD5
LB  >= +0.379 D
ATC >= +0.471 D

C0V12 × HOA-like × EPD5
LB  +0.246 D
ATC >= +0.689 D
```

接近零且基础眼间符号不一致的 EPD3 interactions 只解释为 near-zero/base-dependent，不写成稳定的方向反转。

QC：**PASS**。

---

## 5. Censoring semantics

必须保留：

- 5 个 DOF50 effects 为 lower bounds；
- 10 个 pair 的 distance peak 位于预注册搜索窗边界；
- lower bound 用 `>=` / `≥` 表示；
- peak-window boundary 不解释为真实精确 peak；
- 不扩大 `+0.50 -> -3.00 D` through-focus window；
- 不扩大 `-0.50 -> +0.50 D` distance-peak search window。

整合稿、结果模块、图表计划与 figure supplement 均遵守上述规则。

QC：**PASS**。

---

## 6. Tables

### Supplementary Table S1

Canonical source：

```text
docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv
rows = 48 matched pairs
```

### Supplementary Table S2

Canonical publication table：

```text
docs/evidence/task015/TASK_015_SUPPLEMENTARY_TABLE_S2.csv
rows = 36
= 2 Base × 3 postoperative corneas × 3 platforms × 2 pupils
```

S2 只持久化投稿所需的 N0-referenced `ΔDOF50`、`ΔMTFa@0D` 和 `ΔTF MTFa mean`；288 个 outcome-specific interactions 继续由 accepted source evidence + TASK-015 code 确定性重建，不复制冗余全表。

QC：**PASS**。

---

## 7. Complete figure supplement

正式 figure set：

```text
raw single-pair through-focus = 48
summary figures = 24
total PNG = 72
manifest entries = 72
source through-focus rows = 1440
```

Formal render：

```text
portability-only code fix
= cfb659063c8177223d29711f6b778ec566be3bc5

figure archive commit
= bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5

manifest SHA256
= e1892a0ad547e99c5a0c7816b31f06a059ecdaca6f09ff51748aca834e1a967c

formal ZIP SHA256
= fa2ed14194ed91ff419bc9e4316c76007a953975e7ec9b53b580e1099c5b6c97
```

正式 ZIP 已在 Web 端独立复核：73 entries、72/72 PNG manifest SHA/size match、48/48 raw pair coverage complete。

用户要求“原始 figures 都画出来”已满足并冻结：正文可以少选，但48张 raw figures 不删除、不抽样。

QC：**PASS**。

---

## 8. Manuscript identity

最终自包含稿：

```text
docs/MANUSCRIPT_DRAFT_96_CONFIG_2026-08-20.md
```

当前稿件已统一使用：

- N0 内部参照；
- A0V12/B0V12/C0V12；
- 12 mm vertex-corrected prescription；
- 96 configs / 48 pairs / 1440 TF rows；
- 43 exact + 5 lower-bound DOF effects；
- 10 peak-window-censored pairs；
- N0-referenced postop coupling；
- 47/48 `ΔMTFa@0D<0`；
- 48/48 `ΔTF MTFa mean<0`。

旧 direct-cornea A0/B0/C0 只在 Discussion 中以“工程历史”语义出现，不作为最终结果来源。

QC：**PASS**。

---

## 9. Reference QC

2026-08-20 通过 PubMed/期刊元数据复核正文实际引用的6篇外部文献：

1. Ting DSJ, Gatinel D, Ang M. *Curr Opin Ophthalmol*. 2024;35(1):4-10. DOI `10.1097/ICU.0000000000001006`, PMID 37962882.
2. Sun Y, Hong Y, Rong X, Ji Y. *Front Med (Lausanne)*. 2022;9:834805. DOI `10.3389/fmed.2022.834805`, PMID 35479941.
3. Fan W, Zhu M, Zhang G. *Front Med (Lausanne)*. 2025;12:1509889. DOI `10.3389/fmed.2025.1509889`, PMID 40470056.
4. Micheletti JM, Hall B. *Clin Ophthalmol*. 2026;20:566800. DOI `10.2147/OPTH.S566800`, PMID 41858986.
5. Lago CM, de Castro A, Marcos S. *J Cataract Refract Surg*. 2023;49(11):1153-1159. DOI `10.1097/J.JCRS.0000000000001260`, PMID 37458453.
6. Garzón N, Gómez-Pedrero JA, Albarrán-Diego C, et al. *Graefes Arch Clin Exp Ophthalmol*. 2024;262(9):2897-2906. DOI `10.1007/s00417-024-06469-y`, PMID 38597962.

整合稿原未引用的 Schmid 2024 条目已删除，而不是为了保留参考文献人为扩写正文。

QC：**PASS**。

---

## 10. Offline quality gate

在 manuscript integration + S2 后的 CI run #232：

```text
pytest = 239 passed
Ruff = PASS
compileall = PASS
uv lock --check = PASS
```

后续 reference-only 文档修订不改变代码或 scientific evidence；仍需等待该最终 HEAD 的常规 CI 绿灯后再视为 repo-level QC closure。

---

## 11. Main manuscript figures

Web 端已从正式 figure ZIP 做 presentation-only composition：

```text
Figure 1 = 4-panel ΔDOF50 heatmaps
Figure 2 = 4-panel ΔMTFa@0D heatmaps
Figure 3 = 2-panel extension-quality trade-off
Figure 4 = 12-panel direct N0 vs postop raw through-focus comparison
Figure 5 = whole-eye HOA mechanism map
```

Figure 4 采用3列机制：WFS-like EPD3、RAD-like EPD5、HOA-like EPD5；4行分别为 LB-N0、LB-postop、ATC-N0、ATC-postop。术后行为分别使用 B0V12-WFS、C0V12-RAD、C0V12-HOA，从而在同一主图中直接保留 N0 对照。

这些组合图不重新计算、不平移、不重采样、不改变原图 censoring；在视觉样式确认前不作为新的 scientific evidence，也不替代72张正式 figure supplement。

---

# Verdict

```text
SCIENTIFIC_QC = PASS
NUMERIC_QC = PASS
CENSORING_QC = PASS
PROVENANCE_QC = PASS
REFERENCE_QC = PASS
COMPLETE_RAW_FIGURE_QC = PASS

PRESENTATION_QC = PENDING
JOURNAL_FORMATTING = PENDING
PR_READY_FOR_REVIEW = NO
PR_MERGE_AUTHORIZED = NO
```

剩余工作只属于投稿呈现层：主图视觉确认、caption/表格最终排版、期刊格式与语言润色。不得重新进入 OpticStudio acquisition 或修改冻结光学合同。
