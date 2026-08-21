# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** 当前项目唯一执行路线图。坚持 MVP：只保留完成研究所必需的模型、验证、证据和 STOP gate；不新增与当前研究问题无关的框架。

## Metadata

- document_id: `RMD-0001`
- version: `2.6`
- status: `active`
- last_updated: `2026-08-20`
- active_branch: `feat/task-011-run72`
- PR: `#26 Draft / open / unmerged`
- production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- production_sampling: `128`
- frequency_scale: `paired_residual_free_MONO_EFFL`

---

# 1. Frozen 主研究

以下保持只读：

```text
baseline = MVP_2026_v2
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-009 acquisition = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
TASK-011 = 72 configs / 36 pairs / 1080 TF rows / 0 failed
TASK-012 = PASS_WITH_SCIENTIFIC_CAVEATS
```

Legacy `A0/B0/C0` 的治疗语义仍是 direct corneal-plane `-3.00 D`，不做顶点距回解释。

---

# 2. Accepted 扩展 acquisition

## TASK-013 — N0 未治疗参考角膜

```text
run_id = task013-183dcffcd1da4f1cb1a219d9eedb39db
acquisition code = a3877f5682a9067c1cd420dc31d4f14a6a4e13ab
raw evidence commit = 38ad14a12a18b1a7a30d259cde644d360442f57b
configs = 24/24
failed = 0
TF rows = 360
matched pairs = 12
schema-v2 validations = 6/6 PASS
MODEL_INDEX = 43 / 43 SHA match
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
review = docs/evidence/task013/TASK_013_SCIENTIFIC_REVIEW.json
```

保留 caveat：HOA EDOF EPD5 distance peak 在 `-0.50 D` 边界 censored；N0 EPD5 可出现 `ΔDOF50 < 0`；TASK-007 与 TASK-013 只比较机制方向/波前 signature，不主张绝对数值等同。

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
failed = 0
TF rows = 1080
matched pairs = 36
schema-v2 validations = 18/18 PASS
out-of-coverage carriers = 3 (ATC+C0V12 WFS/RAD/HOA)
MODEL_INDEX = 137 / 137 SHA match
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
review = docs/evidence/task014/TASK_014_SCIENTIFIC_REVIEW.json
```

保留 caveat：5 个 DOF50 为 far-censored lower bounds；8 个 EDOF EPD5 distance peak 在 `-0.50 D` 边界 censored；接近零的小效应可在两个基础眼间改变符号，不解释为稳定方向性机制。

**TASK-013/014 均已冻结；不重跑、不扩展 focus window。**

---

# 3. TASK-015 — accepted 96-config 离线整合

TASK-015 已完成，不使用 OpticStudio：

```text
2 Base
× 4 Cornea = N0 / A0V12 / B0V12 / C0V12
× 3 Platform
× MONO/EDOF
× EPD3/5
= 96 configs
1440 through-focus rows
48 matched pairs
```

来源只允许：

```text
N0 = TASK-013 accepted evidence
A0V12/B0V12/C0V12 = TASK-014 accepted evidence
```

分析保留 TASK-012 的 8 个 pair outcomes，并增加唯一必要的研究对比：

```text
postop-minus-N0 interaction
= (EDOF − MONO)_postop − (EDOF − MONO)_N0
```

正式重建结果：

```text
matched pairs = 48
N0-referenced interaction calculations = 288
coupling cells = 12
DOF50 status = 43 exact + 5 lower_bound
pair peak censored = 10
ΔTF MTFa mean < 0 = 48/48
ΔMTFa@0D < 0 = 47/48
scientific acceptance = PASS_WITH_SCIENTIFIC_CAVEATS
review = docs/evidence/task015/TASK_015_SCIENTIFIC_REVIEW.json
```

主要机制结论：

- A0V12：WFS 的 DOF50 interaction 在 EPD3/5 均为正；RAD/HOA 在 EPD3 相对 N0 减弱，在 EPD5 转为增强；
- B0V12：WFS 在 EPD3 有稳健增强但为 lower bound；RAD 在 EPD5 有明显增强；HOA 整体接近 N0；
- C0V12：RAD/HOA 在 EPD5 的 DOF50 interaction 最明显，其中部分为 lower bound；EPD3 的 WFS/RAD 接近零或基础眼间符号不一致；
- 这些变化描述的是角膜背景对冻结 EDOF 机制的幅度/瞳孔依赖调制，不改变全局的焦深—质量 trade-off。

MVP 结构化输出只持久化：

```text
docs/evidence/task015/TASK_015_PAIR_ANALYSIS.csv
docs/evidence/task015/TASK_015_COUPLING_MATRIX.csv
docs/evidence/task015/TASK_015_ANALYSIS_EVIDENCE.json
docs/evidence/task015/TASK_015_SCIENTIFIC_REVIEW.json
```

288 行 N0 interaction 明细由代码确定性重建并由测试锁定，不另存冗余 CSV。

---

# 4. Figure supplement — 原始 figures 全保留

主文可以只选少量 summary figures，但完整补充材料必须绘制并保留所有原始 matched-pair 贯焦曲线。

正式 figure contract：

```text
docs/evidence/task015/figures/
  raw/      = 48 single-pair through-focus figures
  summary/  = 24 summary figures
  TASK_015_FIGURE_MANIFEST.json
```

其中：

```text
48 raw = 每个 Base × Cornea × Platform × Pupil 各1张
         每张同时绘制 MONO + EDOF 的15-plane MTFa 曲线

24 summary =
  12 outcome heatmaps
  4 Base×Pupil 4×3 through-focus panels
  3 extension–quality trade-off figures
  4 pupil/base sensitivity figures
  1 whole-eye HOA mechanism map
```

总计：

```text
72 figures
```

raw figure 中必须显式标记 DOF50 censoring 与 distance-peak censoring。不得因为 summary 图更简洁而抽样或删除 48 张 raw figure。

---

# 5. Residual validation — 唯一当前规则

历史 carrier-power envelope 只是 `existing validation coverage`，越界本身不构成 STOP。

Exact-carrier validation schema = `2`；规范性 low-order hard gate 只在 `STD_IOL_EYE_2024 EPD6 imported residual readback`：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

Actual-eye hard gate：MONO/EDOF EPD5 ray health PASS。

Actual-eye SSAG Mode-0 piston/defocus 继续保存，但固定为 `diagnostic_only_aperture_limited_mode0`，不得进入 numerical pass/fail；不得为 RAD 建例外阈值；不得修改 frozen residual。

---

# 6. Acceptance / provenance 语义

始终区分 `acquisition_acceptance` 与 `scientific_acceptance`。

TASK-015 是离线重建任务，因此其 acceptance 是：

```text
source accepted
+ Git blob identities exact
+ 96-config factorial reconstruction exact
+ 1440 TF rows reconstruction exact
+ formal pair deltas reconstructed
+ censoring propagated
+ Web scientific review
```

派生 CSV 用 Git blob identity 绑定，避免 CRLF/LF 平台差异造成假漂移。

Figure manifest 只绑定一次正式 render 的文件 identity；不把跨平台 PNG 字节完全一致作为科学 gate。

---

# 7. 当前下一步：完成绘图并整合论文

**不需要新的 OpticStudio acquisition。**

下一步按最短路径：

1. 从已接受 TASK-013/014 的 1440 TF rows 正式渲染 72 张 TASK-015 figures；
2. 保留 48 张 raw through-focus figures 作为完整补充材料；
3. 从 24 张 summary figures 中挑选少量主文图；
4. 将 TASK-015 的 censor-aware coupling 结果写入论文结果与讨论；
5. 最后做 evidence / manuscript / figure QC。

不得为消除 censoring 而扩大窗口重算。

---

# 8. STOP conditions

立即停止，如果：

1. TASK-013/TASK-014 accepted evidence Git blob identity 漂移；
2. source run/config identity 无法唯一对应；
3. TASK-008 / TASK-009 frozen provenance drift；
4. 48/48 raw 或 72/72 total figures 无法从 accepted TF rows 完整渲染；
5. 分析或作图代码试图改变 residual、B0.20、vertex contract、focus window、sampling 或 frequency scale；
6. 为获得“更好”结论而重跑 OpticStudio 或重新优化光学参数。

---

# 9. MVP 明确不做

- patient-specific optimization；
- 多色、偏心/倾斜扩展；
- 新 composite score；
- 重跑 TASK-011/013/014；
- retune B0/residual；
- 新数据库、复杂调度或 GUI；
- 无必要的 schema/framework 抽象。

---

# 10. 当前最短后续路径

```text
A. render all 72 TASK-015 figures
B. manuscript/results integration
C. final evidence/manuscript/figure QC
```

PR #26 继续保持 Draft / open / unmerged，直到 A/B/C 完成并单独获得合并授权。
