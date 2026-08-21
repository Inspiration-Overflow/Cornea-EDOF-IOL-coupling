# MANUSCRIPT SCIENTIFIC QC — accepted 96-config layer

## Status

```text
scientific / numeric / provenance QC = PASS
semantic-label manuscript QC = PASS
presentation / journal-format QC = PENDING
OpticStudio rerun required = NO
```

本 QC 判断最终投稿主分析、数字、censoring、figure provenance、参考文献以及读者可见命名是否与 accepted evidence 一致；期刊版式和最终主图视觉样式仍属于 presentation layer，不提前视为科学 gate。

---

## 1. Canonical source layer

投稿主分析只允许：

```text
TASK-013 未治疗参照角膜 raw evidence commit
= 38ad14a12a18b1a7a30d259cde644d360442f57b

TASK-014 三个顶点距规范化术后角膜 raw evidence commit
= 6ffb2eaf88e386729aa3965c0f12c9b7ca134081

TASK-015 final 96-config analysis
= PASS_WITH_SCIENTIFIC_CAVEATS

TASK-015 formal figure commit
= bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5

TASK-015 figure review
= PASS
```

Legacy direct-cornea A0/B0/C0 TASK-011/012 仅为工程历史，不作为最终投稿主结果。

QC：**PASS**。

---

## 2. Final model / prescription identity

最终矩阵必须保持：2 个基础模型眼、4 个角膜光学条件、3 类人工晶状体延焦机制、2 个瞳孔、2 个光学状态，共 24 个物理载体、96 个配置、48 个严格匹配配对和 1440 个贯焦采样点。

术后处方固定为镜片平面 −3.00 D、顶点距 12.00 mm、角膜平面等效治疗量 −2.895752895753 D。Atchison −3 D 近视模型眼的屈光状态只定义基础眼表型，不再次叠加到手术处方。

QC：**PASS**。

---

## 3. Reader-facing nomenclature QC

正文展示层使用以下语义化名称：

- Liou–Brennan 模型眼（眼轴 23.95 mm）；
- Atchison −3 D 近视模型眼（眼轴 24.48 mm）；
- 未治疗参照角膜；
- 近视术后准单焦角膜；
- 连续非球面角膜延焦原型；
- 中央近用径向多焦角膜；
- 波前塑形型延焦；
- 径向屈光力调制型延焦；
- 高阶像差调制型延焦；
- 3 mm 瞳孔 / 5 mm 瞳孔；
- 匹配单焦对照 / EDoF 状态。

工程 ID `LB_AL2395 / ATC_M3_AL24477 / N0 / A0V12 / B0V12 / C0V12 / WFS / RAD / HOA` 在 assembled manuscript 中仅允许出现在 Methods 的“研究设计与命名原则”首次映射处。`WFS-like / RAD-like / HOA-like / EPD3 / EPD5` 不再作为主稿读者可见称谓。文件名、source CSV、config ID 和 manifest 继续保留内部 ID 以维持 provenance。

对 `docs/MANUSCRIPT_DRAFT_96_CONFIG_2026-08-20.md` 的残留扫描确认：`A0V12` 和 `LB_AL2395` 等内部 ID 只在 Methods 命名映射中出现；`WFS-like`、`EPD3` 等旧展示标签不再出现于主稿。

QC：**PASS**。

---

## 4. Primary outcome counts

最终稿必须保持：

```text
DOF50 增加 = 35 / 48
DOF50 减少 = 13 / 48
DOF50 exact = 43
DOF50 lower bound = 5
距离峰值搜索窗删失 = 10
0 D MTFa 下降 = 47 / 48
全贯焦平均 MTFa 下降 = 48 / 48
```

唯一 0 D MTFa 正向条件为：Atchison −3 D 近视模型眼 × 未治疗参照角膜 × 径向屈光力调制型延焦 × 5 mm 瞳孔，0 D MTFa 改变量约 +0.0184，但全贯焦平均 MTFa 改变量仍约 −0.00731。因此不得解释为无代价增益。

QC：**PASS**。

---

## 5. Untreated-reference coupling definition

唯一正式术后净耦合定义为：

```text
术后角膜中的 (EDoF - 匹配单焦对照)
-
同一基础眼、同一延焦机制、同一瞳孔下未治疗参照角膜中的 (EDoF - 匹配单焦对照)
```

关键 DOF50 净调制与稿件一致：

```text
连续非球面角膜延焦原型 × 波前塑形型延焦 × 3 mm 瞳孔
Liou–Brennan >= +0.266 D
Atchison      >= +0.260 D

连续非球面角膜延焦原型 × 径向屈光力调制型延焦 × 5 mm 瞳孔
Liou–Brennan +0.275 D
Atchison      +0.307 D

中央近用径向多焦角膜 × 径向屈光力调制型延焦 × 5 mm 瞳孔
Liou–Brennan >= +0.379 D
Atchison      >= +0.471 D

中央近用径向多焦角膜 × 高阶像差调制型延焦 × 5 mm 瞳孔
Liou–Brennan +0.246 D
Atchison      >= +0.689 D
```

接近零且基础眼间符号不一致的 3 mm interactions 只解释为 near-zero/base-dependent，不写成稳定方向反转。

QC：**PASS**。

---

## 6. Censoring semantics

必须保留：5 个 DOF50 效应为下界；10 个配对的距离峰值位于预注册搜索窗边界；下界用“≥”或明确文字说明；距离峰值搜索窗边界不解释为真实精确峰值；不扩大 +0.50 至 −3.00 D 贯焦窗口；不扩大 −0.50 至 +0.50 D 距离峰值搜索窗。

QC：**PASS**。

---

## 7. Tables

Canonical source S1 为 `docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv`，48 行匹配配对。Canonical source S2 为 `docs/evidence/task015/TASK_015_SUPPLEMENTARY_TABLE_S2.csv`，36 行术后相对未治疗参照结果。

投稿展示版 S1/S2 必须以完整中文光学名称作为前置展示列，并把内部 ID 移到表尾追溯列；source evidence 本身不得为了可读性被改写。Web 端已从 accepted source 确定性生成 48 行 S1 和 36 行 S2 的可读标签版本，行数与数值结构核对一致。

QC：**PASS**。

---

## 8. Complete figure supplement

正式 figure set 保持 48 张逐配对原始贯焦图、24 张汇总图，共 72 张 PNG，source through-focus rows=1440。正式 figure archive commit 为 `bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5`，figure review=PASS。

用户要求“原始 figures 都画出来”已满足并冻结：正文可以少选，但 48 张 raw figures 不删除、不抽样。后续可读标签版只允许修改标题、坐标、图例与排版，不改变曲线、数值、删失标记或采样点。

QC：**PASS**。

---

## 9. Manuscript identity

最终自包含稿为：

```text
docs/MANUSCRIPT_DRAFT_96_CONFIG_2026-08-20.md
```

当前稿件已统一使用未治疗参照、三个顶点距规范化术后角膜、12 mm vertex-corrected prescription、96 configs / 48 pairs / 1440 TF rows、43 exact + 5 lower-bound DOF effects、10 peak-window-censored pairs、未治疗参照耦合、47/48 0 D MTFa下降和48/48全贯焦平均 MTFa下降。

旧 direct-cornea A0/B0/C0 只以“工程历史”语义出现在 Discussion，不作为最终结果来源。

QC：**PASS**。

---

## 10. Reference QC

正文实际引用的 6 篇外部文献已于 2026-08-20 通过 PubMed/期刊元数据复核：Ting 2024、Sun 2022、Fan 2025、Micheletti & Hall 2026、Lago 2023、Garzón 2024。整合稿未引用的 Schmid 2024 条目已删除，而不是为了保留参考文献人为扩写正文。

QC：**PASS**。

---

## 11. Repository quality gate

最近一次已完成的完整质量门为 239 tests PASS、Ruff PASS、compileall PASS、`uv lock --check` PASS。语义化正文重写均为 documentation/presentation-layer changes，不改变代码、模型、evidence 或科学值；最终 semantic-rewrite HEAD 仍需等待常规 CI 绿灯后完成 repo-level closure。

---

# Verdict

```text
SCIENTIFIC_QC = PASS
NUMERIC_QC = PASS
CENSORING_QC = PASS
PROVENANCE_QC = PASS
REFERENCE_QC = PASS
SEMANTIC_LABEL_QC = PASS
COMPLETE_RAW_FIGURE_QC = PASS

PRESENTATION_QC = PENDING
JOURNAL_FORMATTING = PENDING
PR_READY_FOR_REVIEW = NO
PR_MERGE_AUTHORIZED = NO
```

剩余工作只属于投稿呈现层：归档可读标签版主图、caption/表格最终排版、期刊格式与语言润色。不得重新进入 OpticStudio acquisition 或修改冻结光学合同。
