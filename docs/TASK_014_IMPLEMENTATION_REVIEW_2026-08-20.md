# TASK-014 实现审核：顶点距规范化术后角膜扩展

日期：2026-08-20  
状态：**Web/GitHub implementation ready；local OpticStudio acquisition pending**

## 1. 审核结论

TASK-014 保持 MVP：不修改 frozen TASK-011/012，只新增一个顶点距规范化的术后角膜扩展层。

```text
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane treatment = -2.895752895753 D
cornea IDs = A0V12 / B0V12 / C0V12
```

`ATC_M3_AL24477.source_refraction_d=-3.0` 仅是 Base phenotype/source-model 信息，不与 surgical prescription 相加。

## 2. Matrix

```text
2 Base × 3 corrected corneas × 3 Platform = 18 physical carriers
18 × MONO/EDOF × EPD3/5 = 72 configs
36 matched pairs
1080 through-focus rows
```

Matched MONO/EDOF 共享 P/R/Q/CT/material/IOL position；唯一设计差异仍是 frozen residual。

## 3. Carrier 与角膜构建

实现文件：

```text
src/whole_eye_mvp/task014_vertex_corrected_cornea.py
src/whole_eye_mvp/task014_cornea_zos.py
src/whole_eye_mvp/task014_extension.py
src/whole_eye_mvp/task014_zos.py
scripts/run_task_014_vertex_corrected_cornea.py
```

Carrier 路线：

```text
actual eye Q=0 P/R
→ STD_IOL_EYE_2024 Q(P)
→ actual-eye P–Q recheck max2
→ final actual-eye replay
→ standard-eye EPD6 SA replay
→ canonical physical carrier
```

不得从 legacy A0/B0/C0 carrier 复制 P/R/Q。

## 4. Residual power coverage

历史 power envelope 只是 coverage classifier：

```text
within_existing_coverage
extension_validation_required
```

越界不再自动 STOP。

为避免破坏已实现 runner，`Task014ResidualPowerEnvelopeCheck.passed` 仅保留为旧 report 的兼容别名，严格等价于 `within_existing_coverage`；它**不是 residual-validity hard gate，也不决定 acquisition acceptance**。

## 5. Exact-carrier residual validation

TASK-014 复用与 TASK-013 相同的 schema-v2 validator。

Numerical hard gate：

```text
STD_IOL_EYE_2024 EPD6:
  |piston| <= 0.010 µm
  |global defocus| <= 0.125 D

actual eye EPD5:
  MONO ray health PASS
  EDOF ray health PASS
```

Actual-eye SSAG Mode-0 piston/defocus 仍测量和归档，但只作 diagnostic。

当前实现采用最小路径：每个 carrier 在**第一次 EDOF materialization 前**调用 validator；同一 exact carrier SHA + residual SHA 的通过记录随后缓存复用。无需新增独立 preflight orchestration 层。

如果 validation FAIL，使用 task-level `SystemExit` 阻止该 carrier 进入 EDOF production；不得修改 residual 或阈值追求通过。

## 6. Production contract

完全继承 TASK-009：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
paired_residual_free_MONO_EFFL
sampling = 128
555 nm
EPD3 / EPD5
field = 0°
defocus = +0.50 → -3.00 D
step = -0.25 D
15 planes
```

不扩大 focus/peak window，不改 frequency scale，不改 matched-MONO 定义。

## 7. Canonical archive

唯一实际路径：

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
```

Primary MODEL_INDEX：

```text
5 cornea-layer models
+ 6 Q=0 starts
+ 18 physical carriers
+ 36 pair references
+ 72 analyzed configs
= 137 records
```

Residual validation ZMX 属于 diagnostics/provenance，不并入137。

每个 analyzed config 必须在分析前持久化 EPD3/EPD5，archive SHA 与 `ConfigResult.model_hash_before` 一致。

## 8. Acceptance 语义

本地 runner 的 `acceptance_passed` 只解释为 **local acquisition/archive acceptance**。最终 scientific acceptance 必须由 Web review 决定。

若存在 `within_existing_coverage=false` carrier，即使 exact validation PASS 并完成72配置，也必须做 mechanism review。

## 9. 当前未产生的事实

TASK-014 尚未在 OpticStudio 正式 acquisition，因此当前没有：

- A0V12/B0V12/C0V12 的正式 ZOS readback；
- 18 carrier 的正式 P/Q；
- TASK-014 power-coverage 实测分布；
- 36 pair-MONO EFFL；
- 72 configs / 1080 TF rows。

不得提前写入论文结果。

## 10. STOP

立即停止当前 TASK-014，如果：

- corrected cornea build/target solve fail；
- P–Q recheck >2；
- standard-eye SA replay fail；
- frozen residual SHA mismatch；
- standard-eye residual low-order hard gate fail；
- actual-eye MONO/EDOF ray-health fail；
- pair-MONO EFFL invalid；
- config EPD/SHA/archive mismatch；
- 任何代码尝试修改 TASK-008/011/012 frozen evidence。

以下不单独构成 STOP：

```text
carrier outside historical power coverage
actual-eye SSAG diagnostic piston/defocus outside tolerance
```

## 11. 审核状态

```text
prescription contract = frozen
cornea builder = implemented
18/72/36 manifest = implemented
coverage classifier = implemented
schema-v2 exact validation = implemented
TASK-014 report compatibility bug = covered by explicit compatibility alias + unit test
OpticStudio acquisition = PENDING
```

正式本地执行前只需要当前 HEAD 的 offline QA PASS；不再新增架构或科学参数。