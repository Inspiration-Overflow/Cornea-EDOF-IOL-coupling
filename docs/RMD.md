# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** 当前项目唯一执行路线图。坚持 MVP：只保留完成研究所必需的模型、验证、证据和 STOP gate；不新增与当前研究问题无关的框架。

## Metadata

- document_id: `RMD-0001`
- version: `2.4`
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

# 2. Accepted 扩展任务

## TASK-013 — N0 未治疗参考角膜

```text
run_id = task013-183dcffcd1da4f1cb1a219d9eedb39db
acquisition code = a3877f5682a9067c1cd420dc31d4f14a6a4e13ab
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

**不重跑 TASK-013。**

## TASK-014 — 顶点距规范化术后角膜

处方合同：

```text
TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex = 12 mm
corneal-plane treatment = -2.895752895753 D
IDs = A0V12 / B0V12 / C0V12
```

正式 acquisition：

```text
run_id = task014-e270a185207543149c21da83202c4b73
acquisition code = 38ad14a12a18b1a7a30d259cde644d360442f57b
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

Web mechanism review 结论：两基础眼间 EDOF through-focus 曲线一致性高，最低相关系数约 `0.9804`；3 mm 波前 signature 保持冻结机制方向；3 个 out-of-coverage carrier 无低功率机制断裂证据。

保留 caveat：

1. 5 个 EDOF pair 的 DOF50 far-side censored，因此其 DOF50 只能作为冻结窗口内的下界；
2. 8 个 EDOF EPD5 pair 的 distance peak 在 `-0.50 D` 搜索边界 censored；
3. 少数未 censored 的 EPD5 `ΔDOF50` 接近 0，并可在两个基础眼间出现小幅正负差异，不解释为稳定方向性效应；
4. TASK-007/TASK-013/TASK-014 只比较 mechanism direction / wavefront signature，不主张绝对 DOF50 或 peak shift 数值可互换。

**不重跑 TASK-014，不扩展冻结 focus window。**

---

# 3. Residual validation — 唯一当前规则

历史 carrier-power envelope 只是：

```text
existing validation coverage
```

记录：

```text
within_existing_coverage = true/false
extension_validation_required = !within_existing_coverage
```

越界本身不构成 STOP。

Exact-carrier validation schema = `2`，绑定 exact carrier SHA + exact frozen residual SHA。

规范性 low-order hard gate 只在：

```text
STD_IOL_EYE_2024
EPD6
imported residual readback
```

阈值保持：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

Actual-eye hard gate：

```text
MONO EPD5 ray health PASS
EDOF EPD5 ray health PASS
```

Actual-eye SSAG Mode-0 piston/defocus 继续测量和保存，但固定为：

```text
diagnostic_only_aperture_limited_mode0
```

不得进入 numerical pass/fail；不得为 RAD 建例外阈值；不得修改 frozen residual。

---

# 4. Acceptance 语义

始终区分：

```text
acquisition_acceptance
scientific_acceptance
```

runner 的旧字段 `acceptance_passed` 若保留，只能解释为 local acquisition/archive compatibility alias，不能替代 Web scientific review。

TASK-013 和 TASK-014 当前均已完成两层 acceptance。

---

# 5. Canonical archive / provenance

TASK-013：

```text
models/task013_native_reference/
formal run = task013-183dcffcd1da4f1cb1a219d9eedb39db
```

TASK-014：

```text
models/task014_vertex_corrected/
formal run = task014-e270a185207543149c21da83202c4b73
primary MODEL_INDEX = 5 corneas + 6 P0 + 18 carriers + 36 pair refs + 72 configs = 137
```

Residual-validation ZMX 属于 diagnostics/provenance，不并入 primary MODEL_INDEX。

---

# 6. 当前唯一分析目标：accepted 96-config layer

不再需要新的 OpticStudio acquisition。

最终 accepted extension matrix：

```text
2 Base
× 4 Cornea = N0 / A0V12 / B0V12 / C0V12
× 3 Platform
× MONO/EDOF
× EPD3/5
= 96 configs
```

来源固定为：

```text
N0 = accepted TASK-013 evidence
A0V12/B0V12/C0V12 = accepted TASK-014 evidence
```

下一步只做离线整合：

1. 将 TASK-014 的5个原始 repo evidence 文件按已审核 SHA 原样入库；
2. 合并 TASK-013 + TASK-014 structured evidence；
3. 生成96-config config table、1440-row through-focus table、48 matched-pair delta table；
4. 做 censor-aware 描述性/耦合分析；
5. 输出全贯焦补充材料；
6. 不重新拟合、不重新优化、不扩大冻结窗口。

---

# 7. STOP conditions

立即停止，如果：

1. TASK-013/TASK-014 原始 evidence SHA 与已审核值不一致；
2. source run/config identity 无法唯一对应；
3. TASK-008 / TASK-009 frozen provenance drift；
4. 分析代码试图改变 residual、B0.20、vertex contract、focus window、sampling 或 frequency scale；
5. 为获得“更好”结论而重跑 OpticStudio 或重新优化任何光学参数。

Censoring 必须保留在结果语义中，不因不方便而扩窗重算。

---

# 8. MVP 明确不做

- patient-specific optimization；
- 多色、偏心/倾斜扩展；
- 新 composite score；
- 重跑 TASK-011/013/014；
- retune B0/residual；
- 新数据库、复杂调度或 GUI；
- 无必要的 schema/framework 抽象。

---

# 9. 当前最短后续路径

```text
A. archive reviewed TASK-014 raw repo evidence
B. offline combine TASK-013 + TASK-014 = accepted 96 configs
C. censor-aware final extension analysis
D. render all through-focus supplement
E. manuscript/results integration
```

A 只做 provenance 入库，不需要 OpticStudio。PR #26 在 B/C/D 完成前继续保持 Draft / open / unmerged。
