# MANUSCRIPT R8 SCIENTIFIC QC — 2026-08-22

## 结论状态

```text
R8 manuscript numeric QC          = PASS
R8 factorial QC                   = PASS
R8 through-focus reconstruction   = PASS
R8 paired-delta QC                = PASS
R8 censoring QC                   = PASS
R8 production provenance QC       = PASS
R8 artifact-hash QC               = PASS
R8 entity-integrity QC            = PASS
R8 figure/source QC               = PASS
R8 wording/scope QC               = PASS

local R8 acquisition PASS         = TRUE
formal offline scientific lock    = FALSE
manual Web scientific review      = REQUIRED
automatic progression             = NOT ALLOWED
```

本 QC 的作用是确认 `docs/MANUSCRIPT_FINAL_R8_2026-08-22.md` 是否忠实反映已提交的 R8 production evidence 和 R8 offline analysis evidence。它不是新的 OpticStudio 运行，也不建立新的科学锁。

---

## 1. 权威证据层

本稿数值只允许来自以下已提交 R8 文件：

- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_EVIDENCE.json`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_CONFIG_RESULTS.csv`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_THROUGH_FOCUS.csv`
- `docs/evidence/r8_96/production/MODEL_REVISION_R8_96_PAIRED_DELTAS.csv`
- `docs/evidence/r8_96/MODEL_REVISION_R8_96_OFFLINE_ANALYSIS_EVIDENCE.json`
- `docs/evidence/r8_96/MODEL_REVISION_R8_96_PAIR_ANALYSIS.csv`
- `docs/evidence/r8_96/MODEL_REVISION_R8_96_COUPLING_MATRIX.csv`
- `docs/evidence/r8_96/figures/`

旧 TASK015 数值只可作为稿件历史结构参考，不可覆盖 R8。最终稿已删除旧层中的以下陈述：`43 exact + 5 lower bound`、`10 peak-window censored`、`47/48 ΔMTFa(0D)<0`、`35 positive / 13 negative ΔDOF50`。

**QC：PASS。**

---

## 2. Production identity 与审核门

R8 production evidence 记录：

```text
formal_artifact = true
pilot = false
phase = MODEL-REVISION-R8-96-PRODUCTION
run_id = r8-742953bd22b341c38ebb67af89ccc76e
code_commit = e9083c5faf2bd6fedf061be4c8002b7502d00e1e
opticstudio_version = 260127
local_r8_passed = true
manual_web_review_required = true
automatic_progression_allowed = false
next_gate = STOP for Web R8 review; no automatic progression
```

Offline analysis evidence 同时记录：

```text
formal_scientific_lock = false
opticstudio_used = false
```

最终稿将“本地 acquisition PASS”和“人工 Web 科学审核”明确区分，没有写成“正式临床验证”“自动科学锁”或“允许自动推进”。

**QC：PASS。**

---

## 3. 因子矩阵与配置数

合同和 production evidence 要求并实际得到：

```text
2 bases
× 4 corneal states
× 3 platform surrogates
× 2 physical pupils
× 2 optic states
= 96 configs
```

由每个 `Base × Cornea × Platform × Pupil` 的 MONO/EDoF 严格匹配得到：

```text
24 carriers
48 matched pairs
96 configs
```

最终稿所有配置计数均为 96，配对计数均为 48；没有沿用旧 72-config/36-pair 结构。

**QC：PASS。**

---

## 4. 物理瞳孔、贯焦网格与 acquisition contract

最终稿保持以下 R8 acquisition facts：

```text
physical pupils = 3 mm / 5 mm
STOP = surface 3
3 mm -> 1.5 mm STOP semi-diameter
5 mm -> 2.5 mm STOP semi-diameter
retinal defocus = +0.50 to -3.00 D
step = 0.25 D
planes/config = 15
production operand = MFE MTFA
Grid = 1
Data Type = 0
Wave = 1
Field = 1
production sampling = 128
analysis settings = NOMINAL_MAIN_FFT_MTF_555_v2
frequency scale = paired_residual_free_MONO_EFFL
```

最终稿没有把 EDoF 状态自身 EFFL 用作独立频率轴，也没有扩大冻结贯焦窗。

**QC：PASS。**

---

## 5. Through-focus reconstruction QC

Production evidence 记录：

```text
completed_configs = 96
failed_configs = 0
through_focus_rows = 1440
```

理论重建：

```text
96 configs × 15 planes/config = 1440 rows
```

Offline evidence 记录：

```text
accepted_config_count = 96
accepted_through_focus_row_count = 1440
reconstruction_gate_passed = true
```

最终稿中的 96/96、0 failure、1440 行和 15-plane 描述完全一致。

**QC：PASS。**

---

## 6. Paired-delta QC

Production 和 offline evidence 均要求 48 个匹配配对。离线 summary statistics 与最终稿核对如下：

| 指标 | R8 evidence | 最终稿 |
| --- | ---: | ---: |
| `ΔDOF50` mean | +0.16693986012763976 D | +0.1669398601 D |
| `ΔDOF50` min | −0.9628294880918479 D | −0.9628294881 D |
| `ΔDOF50` max | +0.7425648857759279 D | +0.7425648858 D |
| `ΔDOF50` negative / positive | 6 / 42 | 6 / 42 |
| `ΔMTFa(0D)` mean | −0.2369817543570585 | −0.2369817544 |
| `ΔMTFa(0D)` negative / positive | 48 / 0 | 48 / 0 |
| `ΔTF MTFa mean` mean | −0.029930013123285453 | −0.0299300131 |
| `ΔTF MTFa mean` negative / positive | 48 / 0 | 48 / 0 |
| `Δdistance-peak MTFa` mean | −0.17214770519237235 | −0.1721477052 |
| `Δdistance-peak MTFa` negative / positive | 48 / 0 | 48 / 0 |

最终稿没有将 paired delta 写成临床平均治疗效应。

**QC：PASS。**

---

## 7. DOF50 与 peak censoring QC

Offline evidence 的唯一正式状态计数：

```text
exact = 25
lower_bound = 19
upper_bound = 3
indeterminate = 1
peak-window-censored pairs = 9
```

合计检查：

```text
25 + 19 + 3 + 1 = 48
non-exact DOF50 = 23 / 48
```

最终稿已按上述四类报告，并明确：

- lower bound 使用“≥”；
- upper bound 使用“≤”；
- indeterminate 不转写为精确均值或有效单向界限；
- 总体 +0.16694 D 只是记录值算术均值，不是删失校正估计；
- 9 个距离峰值删失不解释为无限搜索范围下的真实峰值。

Offline evidence 记录 `censor_propagation_passed=true`。

**QC：PASS。**

---

## 8. 12 单元 coupling matrix QC

`MODEL_REVISION_R8_96_COUPLING_MATRIX.csv` 共 12 个角膜 × 机制单元，每个 `stratum_count=4`，对应两个基础眼 × 两个瞳孔。最终稿 Table 1 逐项采用 R8 matrix，而不是 Task015 表。

重点核对：

```text
N0 × WFS  exact        +0.0726833789 D
N0 × RAD  lower bound >= +0.2146564590 D
N0 × HOA  exact        +0.0149746761 D
A0 × WFS  exact        +0.1483716204 D
A0 × RAD  lower bound >= +0.2937145396 D
A0 × HOA  exact        +0.0964380589 D
B0 × WFS  lower bound >= +0.6044428344 D
B0 × RAD  lower bound >= -0.1211093140 D
B0 × HOA  upper bound <= +0.1359074004 D
C0 × WFS  lower bound >= +0.1721302772 D
C0 × RAD  lower bound >= +0.1049731298 D
C0 × HOA  indeterminate
```

特别检查了两个容易误写的单元：

1. `B0 × RAD` 的记录均值为负，但状态为 lower bound，因此不得写成“真实平均效应为负”；最终稿写为 `≥−0.12111 D` 并附解释。
2. `C0 × HOA` 的记录符号为 4/0 正，但均值状态是 indeterminate；最终稿没有将其改写为精确正向均值。

所有 12 单元的 `ΔMTFa(0D)` 和 `ΔTF MTFa mean` 汇总均为负向，最终稿与 CSV 一致。

**QC：PASS。**

---

## 9. R5.2/R6/R7 Binary4 provenance QC

Production evidence 记录：

```text
r5_freeze_id = MODEL-REVISION-R5.2-HOA-BOUNDARY-SAG-INVARIANT-2026-08-21
direct_model_provenance_policy_id = R8_DIRECT_SERIALIZED_R5_2_MODEL_v1
legacy_residual_reapplied = false
carrier_rebuilt = false
iol_refit = false
source models = 48 serialized R6/R7 ACTUAL_BINARY4_MONO/EDOF models
```

最终稿明确 R8 是“直接测量已接受序列化模型”，没有把生产阶段描述成 residual 再应用、载体重建或 IOL 再拟合。

**QC：PASS。**

---

## 10. Artifact-hash QC

Production evidence 锁定三个核心 aggregate CSV：

```text
CONFIG_RESULTS.csv
sha256 = 353ffe24965d6a7e4e8f4087c76574a377f77560acfa0775462af95086d7823f

THROUGH_FOCUS.csv
sha256 = 3c5dec2b193f3851d4ec888904c21a0b7ec2471c786ac02eb08ee23e10b1e46b

PAIRED_DELTAS.csv
sha256 = eadfaa6ca0f9c7e6129a7ef32fc8ed86470feea3d4f60e4af0b78ba9a7417e04
```

Offline evidence 锁定：

```text
source_r8_evidence_sha256 = e1d983ae8c86fa1a87053418e603cc406c108a4255a54f5dc71044cd2a66d8e9
pair_analysis_sha256 = 67cbac1006730b9d48e755560e8dc7d7dec73ad910197a443e3751b71593def5
coupling_matrix_sha256 = 12bdf9cf338da94492e0c7b12645f5f54d63db587fd02bb686ce5e77ed0b085e
```

Production evidence 还包含完整 runtime `artifact_sha256` 映射；最终稿只引用 aggregate/evidence provenance，不对 runtime 文件重新计算或改写。

**QC：PASS。**

---

## 11. Entity-integrity QC

Production evidence 的 `config_diagnostics` 对 96 个配置保存 entity snapshot；检索显示 96 个 `entity_before` 和 96 个 `entity_after` 记录。快照包含 fingerprint、retina position、IOL position、ELP 及 Binary4-aware carrier diagnostic。R8 formal PASS 要求采集前后实体指纹和轴向关键位置不发生未授权漂移。

最终稿的表述限定为：“production evidence 中 96 个配置完成实体完整性路径，没有产生失败配置。”没有把 `carrier_power_d=0.0` 这一 Binary4 兼容性诊断字段误解释为人工晶状体真实光焦度。

**QC：PASS。**

---

## 12. Figure QC

Offline evidence 记录：

```text
figure_count = 72
raw through-focus figures = 48
summary figures = 24
```

`figure_refs` 覆盖：

- 48 个 matched pair 的 raw through-focus 图；
- 12 张 DOF50/MTFa heatmap；
- 4 张 through-focus summary panel；
- 3 张 trade-off 图；
- pupil sensitivity 图；
- base sensitivity 图；
- `mechanism_delta_c40_c60.png`。

最终图表计划仅选择这些已提交 R8 图件或把它们作为 panel source，不从旧 Task015 PNG 反推数值。

**QC：PASS。**

---

## 13. Wording / scope QC

最终稿逐项检查并满足：

- 写明“确定性全眼计算光学研究”，不写成临床试验；
- 不虚构受试者、样本量、视力、对比敏感度、眩光/光晕、满意度或眼镜独立性结果；
- 不生成 P 值、置信区间、显著性或人群外推；
- 不把 WFS/RAD/HOA surrogate 写成商业 IOL；
- 不使用“临床验证”“最佳 IOL”“患者应选择”等超出证据的表述；
- MTFa 下降不等同患者视觉下降；DOF50 增加不等同临床近视力改善；
- `local_r8_passed=true` 不等于 `formal_scientific_lock=true`；
- 保留人工 Web review gate 与禁止自动推进。

**QC：PASS。**

---

## 14. Reference / background QC

最终稿沿用旧稿已使用的 6 篇背景文献，只用于说明 post-refractive cataract/EDoF 的临床与计算背景；R8 数值不来自外部文献。没有新增未经当前任务证据支持的临床数字或文献结论。

**QC：PASS。**

---

# Final verdict

```text
MANUSCRIPT_FINAL_R8_NUMERICALLY_CONSISTENT = true
MANUSCRIPT_FINAL_R8_CENSORING_CONSISTENT = true
MANUSCRIPT_FINAL_R8_PROVENANCE_CONSISTENT = true
MANUSCRIPT_FINAL_R8_SCOPE_CONSISTENT = true

R8_LOCAL_ACQUISITION_PASS = true
R8_OFFLINE_FORMAL_SCIENTIFIC_LOCK = false
MANUAL_WEB_REVIEW_REQUIRED = true
AUTOMATIC_PROGRESSION_ALLOWED = false
```

本 QC 支持把当前稿件提交到下一步人工科学审核与呈现层编辑；不授权修改 R8 runtime evidence、不授权重新运行 OpticStudio、不授权自动推进研究阶段，也不授权合并默认分支。
