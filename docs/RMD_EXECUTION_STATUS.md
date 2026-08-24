# RMD 执行状态

> `RMD-0001 v1.8` 的执行伴随记录。更新日期：2026-08-24。本文记录当前真实状态、冻结身份、正式证据和下一执行边界。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`main`
- R8 主研究与最终稿整合提交：`ef407958303be8736f56b17a8c43de3398343466`（`Merge R8 study and final manuscript`）
- TASK-005/006/007/008：**COMPLETE / FROZEN**
- TDD-999：**CLEARED**
- TASK-009：**COMPLETE**；production sampling = **128**
- TASK-011 Run72：**COMPLETE / ACCEPTED / WEB REVIEW PASS**
- TASK-012：**COMPLETE / OFFLINE RECONSTRUCTION PASS / RESULT REVIEW PASS**
- R5.2：**ACTIVE PRESCRIPTION FREEZE**
- R6/R7：**COMPLETE / 24 PHYSICAL CARRIERS VALIDATED**
- R8 96-config production：**COMPLETE / LOCAL PASS**
- R8 offline integration：**COMPLETE / RECONSTRUCTION + CENSOR PROPAGATION PASS**
- R8 manuscript numeric/scientific QC：**PASS**
- R8 final Web manuscript review：**PASS**（`f4f5fc4498cdf411924c36db489271bedf886d86`）
- 最终 R8 稿：`docs/MANUSCRIPT_FINAL_R8_2026-08-22.md`
- TASK-010 GUI：可选，不是科学前置

历史 Draft PR #25 与 #28 已于 2026-08-24 关闭且未合并；其内容已被后续 Run72、R5.2/R6/R7、R8 和 `main` 集成状态取代。

---

## 当前冻结方法身份

```text
baseline_id = MVP_2026_v2
r5_freeze_id = MODEL-REVISION-R5.2-HOA-BOUNDARY-SAG-INVARIANT-2026-08-21

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 =
0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 =
f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
physical_pupils = 3 mm / 5 mm
through_focus = +0.50 to -3.00 D, 0.25-D step, 15 planes/config
B0 = B0.20 immutable
```

R8 对 R5.2/R6/R7 已序列化 Binary4 模型只读。生产阶段不重新应用 legacy residual、不重建 carrier、不重新求 P/Q、不重新拟合 IOL。

---

## R8 正式 production

权威 evidence：

```text
docs/evidence/r8_96/production/MODEL_REVISION_R8_96_EVIDENCE.json
```

身份与结果：

```text
phase = MODEL-REVISION-R8-96-PRODUCTION
formal_artifact = true
pilot = false
run_id = r8-742953bd22b341c38ebb67af89ccc76e
code_commit = e9083c5faf2bd6fedf061be4c8002b7502d00e1e
opticstudio_version = 260127

physical_carriers = 24
serialized_source_models = 48
completed_configs = 96
failed_configs = 0
matched_pairs = 48
pair_reference_count = 48
through_focus_rows = 1440

legacy_residual_reapplied = false
carrier_rebuilt = false
iol_refit = false
local_r8_passed = true
manual_web_review_required = true
automatic_progression_allowed = false
```

三个 aggregate CSV 的 production SHA-256：

```text
MODEL_REVISION_R8_96_CONFIG_RESULTS.csv
353ffe24965d6a7e4e8f4087c76574a377f77560acfa0775462af95086d7823f

MODEL_REVISION_R8_96_THROUGH_FOCUS.csv
3c5dec2b193f3851d4ec888904c21a0b7ec2471c786ac02eb08ee23e10b1e46b

MODEL_REVISION_R8_96_PAIRED_DELTAS.csv
eadfaa6ca0f9c7e6129a7ef32fc8ed86470feea3d4f60e4af0b78ba9a7417e04
```

`manual_web_review_required=true` 与 `automatic_progression_allowed=false` 是不可变 production evidence 中的审核边界；后续最终 Web manuscript review 已单独完成并记录为 PASS，不回写生产 evidence。

---

## R8 离线整合与科学结果

权威 evidence：

```text
docs/evidence/r8_96/MODEL_REVISION_R8_96_OFFLINE_ANALYSIS_EVIDENCE.json
```

重建状态：

```text
accepted_config_count = 96
accepted_through_focus_row_count = 1440
matched_pair_count = 48
coupling_cell_count = 12
figure_count = 72
reconstruction_gate_passed = true
censor_propagation_passed = true
opticstudio_used = false
formal_scientific_lock = false
```

DOF50 effect 状态：

```text
exact = 25
lower_bound = 19
upper_bound = 3
indeterminate = 1
peak-window-censored pairs = 9
```

所有 paired effect 定义为 `EDOF - MONO`。当前可报告的描述性结果：

```text
ΔDOF50 recorded mean = +0.1669398601 D
range = -0.9628294881 to +0.7425648858 D
positive / negative = 42 / 6

ΔMTFa(0 D) mean = -0.2369817544
negative / positive = 48 / 0

Δthrough-focus mean MTFa = -0.0299300131
negative / positive = 48 / 0

Δdistance-peak MTFa = -0.1721477052
negative / positive = 48 / 0
```

解释边界保持不变：

- `ΔDOF50` 的总体均值包含被删失配对的记录值，只作当前确定性矩阵的描述，不是删失校正总体估计；
- 不能把 DOF50 增加等同临床近视力改善；
- 不能把 MTFa 下降直接等同患者视觉质量下降；
- 不能将 WFS/RAD/HOA surrogate 转写成商业 IOL 排名或患者级选片建议；
- 不能把确定性 48-pair 矩阵按随机临床样本进行传统显著性推断。

---

## 最终论文与审核

当前论文包：

```text
docs/MANUSCRIPT_FINAL_R8_2026-08-22.md
docs/MANUSCRIPT_R8_SCIENTIFIC_QC_2026-08-22.md
docs/MANUSCRIPT_R8_FIGURE_TABLE_PLAN_2026-08-22.md
```

最终 Web manuscript review：

```text
commit = f4f5fc4498cdf411924c36db489271bedf886d86
review_verdict = PASS
documents_required_correction = false
```

该审核确认论文包与已提交 R8 production/offline evidence 在 96-config / 48-pair / 1440-row 因子矩阵、DOF50 删失语义、MTFa 配对结果、12 单元 coupling matrix、R5.2/R6/R7 direct Binary4 provenance、artifact hashes 和 72 张图件追溯关系上一致。

2026-08-24 又对正文 6 篇外部背景文献做了独立核验；题名、作者、期刊、年份、卷期/定位信息、DOI 与正文所承担的论证用途均得到出版商/PubMed/PMC/机构库等来源支持。核验记录：

```text
docs/MANUSCRIPT_REFERENCE_VERIFICATION_2026-08-24.md
```

---

## 历史 Run72 / TASK-012 状态

TASK-011/TASK-012 是已接受的前序 72-config 证据层，保留用于方法演化与追溯，不覆盖 R8 最终数值。其 frozen method identity（TASK-009 MTFA Grid=1、paired-MONO angular scale、sampling=128）继续被 R8 继承。

R8 最终稿的任何数值不得被旧 TASK-011/TASK-012/TASK-015 数值覆盖。

---

## 当前下一执行

MVP 的光学生产主线已完成。当前优先级转为投稿前收尾：

1. 在 `main` 对最终仓库运行一次完整 offline-quality gate，并保留 workflow run 记录；
2. 冻结一个明确的最终 Git ref / release，绑定最终代码、R8 evidence、论文与图表包；
3. 根据目标期刊要求做语言、格式、图件分辨率/尺寸、补充材料和数据可用性声明整理；
4. 如需新增科学分析，优先使用现有 R8 evidence 做预先定义的离线敏感性分析；只有新问题确实需要新光学数据时才重新进入 OpticStudio acquisition。

---

## 当前 STOP

- 不修改 TASK-005–009 frozen assets/method locks；
- 不修改 R5.2 freeze identity；
- 不重新优化 residual profile 或 IOL；
- 不重跑 R8 96 configs 来“改善”删失结果；
- 不事后扩大冻结的 focus/search window 并把结果替换进主分析；
- 不使用 EDOF-state/per-state EFFL 改变 matched-pair production angular scale；
- 不把 lower-bound / upper-bound / indeterminate 静默当作 exact；
- 不把计算 surrogate 结果转写为商业产品优劣、患者级推荐或临床疗效结论；
- 若后续出现 evidence/code inconsistency，先停止解释并做独立审核，不把 OpticStudio rerun 当默认修复手段。
