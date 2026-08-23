# Model Revision R8 — direct serialized-model acquisition handoff

> 日期：2026-08-22  
> 状态：Web 实现完成；OpticStudio 本地执行仍待 local orchestrator 进行。  
> 科学处方：R5.2 冻结规则不变；R6/R7 已审核的 48 个 actual-eye Binary4 模型为唯一生产输入。  
> 自动推进：禁止；即使本地 R8 全部通过，仍需 Web 人工审核。

## 1. 本次修订解决的问题

上一版 R8 runner 已能离线证明 24-carrier / 96-config / 48-pair / 1440-row 因子矩阵，并能在打开 OpticStudio 前验证 R6/R7 evidence 与 48 个序列化模型的 SHA-256；但当时缺少一个安全的 acquisition adapter，无法直接消费已经序列化完成的 R5.2 Binary4 模型。

本任务新增：

```text
src/whole_eye_mvp/analysis_zos_r8_direct.py
```

并将：

```text
scripts/run_model_revision_r8_96.py
```

接到该 adapter。旧的 carrier + residual `_prepare_model()` 路径不参与 R8 direct acquisition。

## 2. 唯一允许的 R8 光学输入

每个 physical carrier 的两个状态必须直接来自 R6/R7：

```text
diagnostics/model_revision/r6_r7/
  validated/<carrier_id>/ACTUAL_BINARY4_MONO.zmx
  validated/<carrier_id>/ACTUAL_BINARY4_EDOF.zmx
```

其中 `<carrier_id>` 为：

```text
R6_<base>_<cornea>_<platform>
```

总计：

```text
24 carriers × 2 states = 48 immutable serialized source models
```

runner 在任何生产 acquisition 之前读取 `MODEL_REVISION_R6_R7_EVIDENCE.json`，要求 R5.2 freeze identity、R6/R7 九项 local checks、24-carrier identity 及相关 contract 均保持冻结状态，并从 `artifact_sha256` 中解析恰好 48 个所需模型 SHA-256。随后逐文件重算 SHA-256；缺失、漂移或多余/冲突映射均立即 STOP。

## 3. Copy-on-write 边界

source `.zmx` 永不直接保存或改写。每次 pair-reference 或 config acquisition 均：

1. 再次验证 source SHA-256；
2. `copy2` 到 `diagnostics/model_revision/r8_96/` 下的本次 runtime working path；
3. 验证 copy 初始 SHA 与 source 完全一致；
4. 仅在 working copy 中设置本配置所需 physical STOP；
5. 保存 working copy；
6. 后续 OBJECT vergence 和临时 MFE operand 变化均只存在于内存，并在 `finally` / primitive cleanup 中恢复；
7. acquisition 结束后再次验证 source SHA 未改变。

不调用旧 `apply_grid_sag_residual`，不读取 TASK-013/TASK-014 residual asset，不重建 physical carrier，不重新求 P/Q，不重新拟合 R5.2，不改变 Binary4 zone topology。

## 4. Physical pupil 与 direct Binary4 entity snapshot

R8 继续使用 post-audit actual-eye 语义：

```text
Aperture Type = Float By Stop Size
STOP = surface 3
3 mm pupil -> STOP SemiDiameter = 1.5 mm
5 mm pupil -> STOP SemiDiameter = 2.5 mm
```

adapter 通过现有 `configure_physical_pupil()` 设置，并立刻使用 `read_revision_geometry()` + `validate_revision_geometry()` 对完整眼几何做回读。除 requested physical STOP setting 外，不调用 `apply_revision_to_full_eye()` 等会重写其他几何的 helper。

首次本地 R8 执行暴露出一个 implementation-only 问题：direct adapter 原先复用了 legacy `capture_entity_snapshot()`。该 legacy snapshot 专为对称 Standard 双凸 carrier 设计，要求 anterior/posterior ordinary `Radius` 保持正负对称；而已审核的 R6/R7 Binary4 模型在 Binary4 surface 的 ordinary `Radius=0`，真实 zone radius/conic 存放于 Binary4 参数，因此合法的 R6/R7 模型会在首次 pair EFFL 前被错误拒绝。

修复后，R8 direct adapter **只使用** `capture_direct_entity_snapshot()`；legacy `capture_entity_snapshot()` 保持原行为，继续服务旧 Standard-biconvex acquisition 路径。direct snapshot：

- 保留 7-surface、surface-role、STOP identity、retina/IOL/ELP 轴向完整性检查；
- 复用 R6 `_read_binary4_zones()` 回读，不解析 ZMX 文本，也不建立第二套 Binary4 表示；
- fingerprint 锁定 surfaces 1–6 的 comment/type/radius/conic/thickness/material/is-stop，且除 STOP 外锁定 clear semi-diameter；
- fingerprint 同时锁定 Binary4 zone 的 inner/outer radius、zone radius/conic、diffraction order 与 native p²/p⁴/p⁶；
- 有意排除 OBJECT thickness；
- 有意排除 physical STOP semi-diameter，使 3/5-mm requested pupil 不被误判为 carrier mutation；
- 对旧 `EntitySnapshot.carrier_power_d` 兼容字段写入有限诊断哨兵 `0.0 D`，仅表示“Binary4 geometry 无单一 symmetric-biconvex power 可报告”，该值不进入 EFFL、MTFa、HOA、paired delta 或任何科学结果计算。

因此，设置 physical STOP 前后、save/reload 前后及 MFE/HOA acquisition 前后仍必须保持 direct entity fingerprint 一致；任何 Binary4 zone 值、非 STOP surface state、retina/IOL/ELP 轴向状态的未授权变化仍会立即失败。

## 5. 48 个 matched-pair angular scales

每个：

```text
Base × Cornea × Platform × Pupil
```

构成一个严格 matched pair，共 48 个。pair key 采用既有 `NominalConfig` canonical 形式：

```text
<carrier_id>_EPD<pupil>
```

例如：

```text
R6_LB_AL2395_N0_WFS_EPD3
```

每个 pair 只从 direct MONO working copy 在 nominal-distance 状态测一次 MFE EFFL。该 EFFL 生成：

```text
mm_per_degree = EFFL × tan(1°)
frequency_cycles_per_mm = frequency_cpd / mm_per_degree
```

冻结的 0–60 cycles/degree、1-cpd 步长网格因此得到 61 个 cycles/mm operand 频率。相同 pair reference 对 MONO 与 EDOF、15 个 defocus planes 和全部 production frequencies 固定复用。每态 EFFL 仍可作为 diagnostic 记录，但绝不替换 pair-MONO scale。

## 6. Production MTF acquisition

继续使用既有 TASK-009 contract：

```text
contract = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
operand  = MTFA
grid     = 1
data type= 0
wave     = 1
field    = 1
sampling = 128
```

贯焦网格保持：

```text
+0.50, +0.25, 0.00, -0.25, ... , -3.00 D
```

共 15 planes。每个 plane 只临时修改 OBJECT thickness；`finally` 必须恢复原始 OBJECT thickness。`MfeMtfGridRunner` 自身负责临时 MFE operand 的创建与删除，adapter 在每个 acquisition 段后再检查 MFE operand count 未漂移。

每个 config 同时采集：

- 15-plane MTFa；
- 10/20/30/40/50/60 cpd 固定频点；
- 0-D 完整 MTF curve；
- frozen TASK-009 full-HOA：C4⁰、C6⁰、HOA RMS；
- cornea / STOP / IOL real-ray footprints；
- unintended vignetting；
- direct Binary4 entity snapshot；
- source/working model SHA provenance。

任一非有限值、MTF batch 不完整、意外 vignette、entity drift、working model disk drift、MFE cleanup failure 或 source SHA drift均立即失败。

## 7. ConfigResult 兼容性与 direct provenance

正式输出继续复用 `ConfigResult`、`config_scalar_row()`、`through_focus_rows()`、`paired_delta_row()` 与既有 `matched_pair_delta()`。

由于既有 `matched_pair_delta()` 会要求 EDOF `NominalConfig` 具有 residual provenance，本 adapter 为预序列化 EDOF model 写入**兼容性 provenance metadata**：

```text
residual_id = R5_2_FREEZE_ID
residual_sha256 = immutable EDOF source .zmx SHA-256
residual_validation_policy_id = R8_DIRECT_SERIALIZED_R5_2_MODEL_v1
residual_validation_policy_hash = hash(frozen direct-model provenance policy)
```

这些字段不是一个可再次应用的 residual 文件，也不会进入任何 residual application function。它们只表达“该 EDOF 状态已经内嵌在经 R6/R7 审核并按 SHA 锁定的 source `.zmx` 中”。MONO 的四个 residual provenance 字段继续为 `None`。

## 8. Runtime output tree

本地 `--execute` 成功时只在：

```text
diagnostics/model_revision/r8_96/
```

产生运行时文件，主要包括：

```text
MODEL_REVISION_R8_96_EVIDENCE.json
MODEL_REVISION_R8_96_CONFIG_RESULTS.csv
MODEL_REVISION_R8_96_THROUGH_FOCUS.csv
MODEL_REVISION_R8_96_PAIRED_DELTAS.csv
pair_references/
configs/<config_id>/
  model.zmx
  config_result.json
  through_focus.csv
  through_focus_mtfa.png
  mtf_at_zero_d.png
```

这些 runtime diagnostics 不是本 Web 任务的 Git 写入目标。

## 9. Formal local PASS 条件

`local_r8_passed=true` 只能在以下条件全部满足后写入 formal evidence：

```text
completed_configs = 96
failed_configs = 0
matched_pairs = 48
through_focus_rows = 1440
pair_reference_count = 48
```

并且：

- 48 个 R6/R7 source model SHA 全部验证；
- 96 个 ConfigResult 通过既有完整性校验；
- 全部 mandatory artifacts 存在；
- 三个 aggregate CSV 已写出并计算 SHA-256；
- runtime artifact hash map 非空且可重建；
- 无 unintended vignetting；
- 无 source/model/entity/retina/IOL/ELP drift；
- acquisition contract/hash、分析 settings/hash、pair-scale mode 与 sampling 均为冻结值。

formal evidence 继续明确：

```text
manual_web_review_required = true
automatic_progression_allowed = false
next_gate = STOP for Web R8 review; no automatic progression
```

本地 PASS 不等于论文结果自动接受，也不授权 merge 或后续研究阶段。

## 10. Runner commands

仅查看计划，不读取 OpticStudio：

```text
uv run python scripts/run_model_revision_r8_96.py --plan-only
```

只做 R6/R7 evidence + 48 source SHA preflight，不打开 OpticStudio：

```text
uv run python scripts/run_model_revision_r8_96.py \
  --preflight \
  --project-dir "<project_mvp_2026_v2_zmx>"
```

本地 orchestrator 在独立审核通过且具备有效 OpticStudio/ZOS-API 环境后，才可运行：

```text
uv run python scripts/run_model_revision_r8_96.py \
  --execute \
  --authorization-id r8-96-production-runner-20260822 \
  --install-dir "<OpticStudio install dir>" \
  --project-dir "<project_mvp_2026_v2_zmx>"
```

`--execute` 的顺序固定为：授权检查 → clean Git HEAD → offline R6/R7 evidence/hash preflight → direct source mapping/hash verification → runtime output-empty guard → **最后才打开 ZOS session**。

## 11. Required offline code checks

在完整 repository checkout 中执行：

```text
uv run pytest \
  tests/unit/test_model_revision_r8.py \
  tests/unit/test_analysis_zos_r8_direct.py

uv run ruff check \
  src/whole_eye_mvp/analysis_zos_r8_direct.py \
  scripts/run_model_revision_r8_96.py \
  tests/unit/test_model_revision_r8.py \
  tests/unit/test_analysis_zos_r8_direct.py

uv run python -m compileall \
  src/whole_eye_mvp/analysis_zos_r8_direct.py \
  scripts/run_model_revision_r8_96.py \
  tests/unit/test_model_revision_r8.py \
  tests/unit/test_analysis_zos_r8_direct.py

uv lock --check
```

这些检查不需要 OpticStudio；任何失败必须先修复，不得以 live optical run 替代代码 QA。

## 12. STOP 条件

立即停止且不得写 `local_r8_passed=true`，如果出现任一情况：

1. R6/R7 evidence identity、R5.2 freeze 或九项 local checks 漂移；
2. 48 个 source models 任一缺失或 SHA 不符；
3. factor space 不是 24/96/48/1440；
4. physical STOP 不能严格设置/回读为 1.5 或 2.5 mm；
5. pair MONO EFFL 非有限、非正值或不是每 pair 唯一尺度；
6. TASK-009 MTFA Grid=1 contract/hash、Wave/Field/Data/Sampling 发生漂移；
7. 15-plane acquisition 不完整、存在非有限值或 OBJECT/MFE 未恢复；
8. source SHA、working model、entity、retina/IOL/ELP identity 发生未授权变化；
9. 出现 unintended vignetting；
10. 96 ConfigResults、48 paired deltas、1440 TF rows 或 mandatory artifacts 不完整；
11. 需要重新应用 legacy residual、重新拟合 IOL 或重新构建 carrier 才能继续。

## 13. Web 阶段边界

本任务仅实现代码与 handoff。ChatGPT Web **没有运行 OpticStudio**、没有触碰许可证、没有生成任何 R8 runtime evidence，也没有声明 R8 production PASS。真正的 R8 光学生产结果仍需 local orchestrator 在此任务分支经独立 QA 后执行，并再次提交 Web 人工审核。
