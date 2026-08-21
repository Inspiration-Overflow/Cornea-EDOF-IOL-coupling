# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** 当前项目唯一执行路线图。坚持 MVP：只保留完成研究所必需的模型、验证、证据、图形和稿件 QC；不新增与当前研究问题无关的框架。

## Metadata

- document_id: `RMD-0001`
- version: `2.7`
- status: `active`
- last_updated: `2026-08-20`
- active_branch: `feat/task-011-run72`
- PR: `#26 Draft / open / unmerged`
- production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- production_sampling: `128`
- frequency_scale: `paired_residual_free_MONO_EFFL`

---

# 1. Frozen engineering history

以下保持只读：

```text
baseline = MVP_2026_v2
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-009 acquisition = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
TASK-011 legacy Run72 = 72 configs / 36 pairs / 1080 TF rows / 0 failed
TASK-012 legacy analysis = PASS_WITH_SCIENTIFIC_CAVEATS
```

Legacy `A0/B0/C0` 的治疗语义是 direct corneal-plane `-3.00 D`，仅保留为工程历史，不再与最终投稿主矩阵混算。

---

# 2. Accepted final acquisition layer

## TASK-013 — N0 未治疗参考角膜

```text
run_id = task013-183dcffcd1da4f1cb1a219d9eedb39db
acquisition code = a3877f5682a9067c1cd420dc31d4f14a6a4e13ab
raw evidence commit = 38ad14a12a18b1a7a30d259cde644d360442f57b
configs = 24/24
TF rows = 360
matched pairs = 12
schema-v2 validations = 6/6 PASS
MODEL_INDEX = 43 / 43 SHA match
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

## TASK-014 — 顶点距规范化术后角膜

```text
contract = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex = 12 mm
corneal-plane treatment = -2.895752895753 D
IDs = A0V12 / B0V12 / C0V12
run_id = task014-e270a185207543149c21da83202c4b73
acquisition code = 38ad14a12a18b1a7a30d259cde644d360442f57b
raw evidence commit = 6ffb2eaf88e386729aa3965c0f12c9b7ca134081
carriers = 18
configs = 72/72
TF rows = 1080
matched pairs = 36
schema-v2 validations = 18/18 PASS
MODEL_INDEX = 137 / 137 SHA match
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

TASK-013/014 均冻结：不重跑、不扩展 focus window、不修改 residual/B0/vertex contract。

---

# 3. TASK-015 — accepted 96-config final analysis layer

最终投稿主矩阵：

```text
2 Base
× 4 Cornea = N0 / A0V12 / B0V12 / C0V12
× 3 Platform
× MONO/EDOF
× EPD3/5
= 96 configs
= 1440 through-focus rows
= 48 matched pairs
```

术后耦合唯一正式定义：

```text
postop-minus-N0 interaction
= (EDOF − MONO)_postop − (EDOF − MONO)_N0
```

正式结果：

```text
N0-referenced interaction calculations = 288
coupling cells = 12
DOF50 status = 43 exact + 5 lower_bound
pair peak censored = 10
ΔDOF50 > 0 = 35/48
ΔDOF50 < 0 = 13/48
ΔTF MTFa mean < 0 = 48/48
ΔMTFa@0D < 0 = 47/48
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
```

主要机制解释：

- N0 明确了 residual 自身的 pupil-dependent baseline；术后绝对 `EDOF−MONO` 不再自动等同于 coupling；
- A0V12 对三类机制的调制整体较温和；
- B0V12×WFS-like 的主要增强位于 EPD3，且两基础眼均为 lower bound；
- B0V12×RAD-like 的主要增强位于 EPD5；
- C0V12×RAD-like 与 C0V12×HOA-like 的主要增强位于 EPD5，其中部分为 lower bound；
- 小幅、基础眼间符号不一致的 interaction 解释为 near-zero/base-dependent，不上升为稳定方向性结论；
- 全局仍是焦深扩展—光学质量再分配 trade-off。

结构化 evidence：

```text
docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv
docs/evidence/task015/TASK_015_COUPLING_MATRIX.csv
docs/evidence/task015/TASK_015_ANALYSIS_EVIDENCE.json
docs/evidence/task015/TASK_015_SCIENTIFIC_REVIEW.json
```

---

# 4. TASK-015 figure supplement — accepted

正式 binary render 已完成并入库：

```text
render portability fix = cfb659063c8177223d29711f6b778ec566be3bc5
figure commit = bc4e451c22b0cbe1a3f08798b0119942bb9bc5c5
figure review = docs/evidence/task015/TASK_015_FIGURE_REVIEW.json
```

`cfb6590` 仅将 Windows CRLF working-tree bytes 在 Git blob identity 计算前规范化为 LF；科学定义、accepted source evidence 和 figure 数值均未改变。

正式 figure set：

```text
raw through-focus = 48
summary = 24
total PNG = 72
manifest entries = 72
source TF rows = 1440
OpticStudio used for render = false
figure review acceptance = PASS
```

目录：

```text
docs/evidence/task015/figures/
  raw/
  summary/
  TASK_015_FIGURE_MANIFEST.json
```

48张 raw figure 必须作为完整补充证据保留；正文只能“少选”，不能删除原始 figure set。

---

# 5. Residual validation — 唯一当前规则

历史 carrier-power envelope 只表示 `existing validation coverage`，越界本身不构成 STOP。

Exact-carrier validation schema = `2`。规范性 low-order hard gate 只在：

```text
STD_IOL_EYE_2024
EPD6
imported residual readback
```

阈值：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

Actual-eye hard gate：MONO/EDOF EPD5 ray health PASS。

Actual-eye SSAG Mode-0 piston/defocus 固定为 `diagnostic_only_aperture_limited_mode0`，不得进入 numerical pass/fail；不得为 RAD 建例外阈值。

---

# 6. 当前稿件状态

投稿主分析已经从 legacy TASK-012 迁移到 accepted TASK-015 96-config layer。

以下稿件模块已按最终主矩阵修订：

```text
docs/MANUSCRIPT_INTRODUCTION_DRAFT_2026-08-20.md
docs/MANUSCRIPT_ABSTRACT_METHODS_DRAFT_2026-08-20.md
docs/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT_2026-08-20.md
docs/MANUSCRIPT_FIGURE_TABLE_PLAN_2026-08-20.md
```

稿件必须保持：

- N0 为内部参照；
- A0V12/B0V12/C0V12 使用12 mm顶点距规范化处方；
- 48 pair / 1440 TF rows / 43 exact+5 lower-bound / 10 peak-censored；
- 47/48 `ΔMTFa@0D<0`、48/48 `ΔTF mean<0`；
- 术后 coupling 用 postop-minus-N0 定义；
- 机制 surrogate 不转换为商业产品排名或患者级推荐。

---

# 7. 当前下一步：稿件合并与最终 QC

**不再需要新的 OpticStudio acquisition，也不需要重新渲染 figure supplement。**

最短路径：

1. 将四个稿件模块合并为单一自包含 manuscript；
2. 从已归档 summary/raw figures 组合少量正文主图；
3. 生成 Supplementary Table S1（48-pair）与 S2（N0-referenced interactions）；
4. 做 evidence ↔ manuscript ↔ figure caption ↔ reference 的逐项 QC；
5. PR #26 保持 Draft/open/unmerged，等待单独合并授权。

---

# 8. STOP conditions

立即停止，如果：

1. TASK-013/TASK-014 accepted evidence Git blob identity 漂移；
2. TASK-015 48-pair / 1440-TF reconstruction 无法复现；
3. 48/48 raw 或72/72 total figure identity 与正式 manifest 不一致；
4. 稿件重新使用 legacy A0/B0/C0 direct-cornea 数值作为投稿主结果；
5. 稿件把 lower bound 或 peak-window-conditioned 值写成精确值；
6. 为改善结论而重跑 OpticStudio、扩展窗口、修改 residual/B0/vertex contract 或重新优化 carrier。

---

# 9. MVP 明确不做

- patient-specific optimization；
- 多色、偏心/倾斜扩展；
- 新 composite score；
- 重跑 TASK-011/013/014；
- retune B0/residual；
- 新数据库、复杂调度或 GUI；
- 无必要的 schema/framework 抽象；
- 删除不利于叙事的 raw figures。

---

# 10. 当前最短后续路径

```text
A. merge manuscript modules
B. make manuscript composite figures/tables from accepted evidence
C. final manuscript/evidence/figure/reference QC
D. only then decide PR readiness/merge separately
```
