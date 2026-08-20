# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 及已批准独立任务计划提供。

## Metadata

- document_id: `RMD-0001`
- version: `2.1`
- status: `active`
- last_updated: `2026-08-20`
- active_task_branch: `feat/task-011-run72`
- PR: `#26 Draft / open / unmerged`
- active production acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active frequency scale: `paired_residual_free_MONO_EFFL`
- active production sampling: `128`
- completed formal tasks: `TASK-011`, `TASK-012`
- active extension tasks: `TASK-013 N0` + `TASK-014 A0V12/B0V12/C0V12`

---

# 1. 双环境执行模型

## Web / GitHub

负责：

- 科学定义与版本化文档；
- Python 实现、单元测试、静态 QA；
- frozen provenance 审核；
- Git checkpoint；
- structured evidence 审核；
- 后续96配置离线整合、统计和作图。

## Local Windows / ZCode + OpticStudio

只负责必须由真实 ZOS-API 产生的新光学事实：

- TASK-013 N0 optical acquisition；
- TASK-014 corrected-postoperative optical acquisition；
- exact-carrier frozen-residual validation；
- `.zmx`、SHA、through-focus evidence。

既有 TASK-011 不因扩展任务重跑。

---

# 2. 通用离线质量门

每轮代码修订后：

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

Unit tests 不依赖 OpticStudio。

`.zmx` 从 TASK-013 起是强制研究 artifact；正式 analyzed config 必须有 canonical archive + SHA index。

---

# 3. Frozen 主研究状态

## TASK-008 / TASK-009 identity

```text
baseline_id = MVP_2026_v2
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
```

## TASK-011

```text
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
configs = 72
failed = 0
pairs = 36
TF rows = 1080
acceptance = PASS
```

## TASK-012

```text
pairs = 36
predefined contrasts = 1152
coupling cells = 9
figures = 24
DOF50 exact = 31
DOF50 lower-bound = 5
peak-window-censored pairs = 8
review = PASS_WITH_SCIENTIFIC_CAVEATS
```

旧 A0/B0/C0 的真实治疗语义固定为：

```text
direct corneal-plane treatment_d = -3.00 D
vertex conversion = none
```

它们是 legacy engineering factorial，不再被重解释为 spectacle −3.00 D 经 vertex correction 后的临床术后角膜。

---

# 4. TASK-013 — N0 未治疗参考角膜

## 4.1 Scope

```text
N0 = native / untreated reference cornea
2 Base × 1 N0 × 3 Platform = 6 carriers
6 × MONO/EDOF × EPD3/5 = 24 configs
12 matched pairs
360 TF rows
```

N0 使用 `MAIN_CORNEA_LIOU_555_v1`，不施加近视 treatment、额外 ΔC4⁰ 或 central-near zone。

## 4.2 Carrier route

```text
N0 scaffold
→ per Base Q=0 P/R solve
→ per Platform STD_IOL_EYE_2024 Q(P)
→ actual-eye P–Q recheck (max2)
→ 6 canonical carriers
→ power coverage classification
→ exact-carrier frozen-residual validation
→ 12 pair-MONO EFFL references
→ 24-config production
→ ZMX archive
```

首次本地 carrier build 已观察到 ATC+N0 约19 D，低于 legacy post-refractive calibration coverage；这是合理的低功率扩展，不是 carrier 自动失败。

## 4.3 Canonical models

```text
project_mvp_2026_v2_zmx/models/task013_native_reference/
  cornea/N0_REFERENCE_CORNEA.zmx
  carriers/CAR_<base>_N0_<platform>.zmx
  residual_validations/
  runs/<run_id>/pair_references/<pair_key>.zmx
  runs/<run_id>/configs/<config_id>.zmx
  runs/<run_id>/MODEL_INDEX.csv
```

---

# 5. TASK-014 — spectacle-to-corneal-plane normalization

## 5.1 Frozen prescription contract

```text
contract_id = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane distance treatment = -2.895752895753 D
legacy direct treatment = -3.000000000000 D
delta = +0.104247104247 D
```

`ATC_M3_AL24477.source_refraction_d=-3.0` 是 Base phenotype/source-model 信息，不与 surgical prescription 相加。

## 5.2 Corrected IDs

```text
A0V12 = corrected distance baseline + ΔC4^0 target ≈ +0.13 µm
B0V12 = corrected distance baseline + frozen B0.20 target +0.20 µm
C0V12 = corrected distance baseline + prescription ADD +1.75 D
```

## 5.3 Matrix

```text
2 Base × 3 corrected corneas × 3 Platform = 18 carriers
18 × MONO/EDOF × EPD3/5 = 72 configs
36 pairs
1080 TF rows
```

## 5.4 Canonical models

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
  corneas/
  carriers/                              # 18
  residual_validations/
  runs/<run_id>/p0/                      # 6
  runs/<run_id>/pair_references/         # 36
  runs/<run_id>/configs/                 # 72
  runs/<run_id>/MODEL_INDEX.csv          # primary model index = 137 records
```

137 统计：5 cornea-layer + 6 P0 + 18 carriers + 36 pair refs + 72 analyzed configs。Residual validation models 属于 diagnostics/provenance，不并入137。

---

# 6. Residual power coverage 与 exact-carrier validation

这是 RMD v2.1 的核心修订。

## 6.1 Historical envelope 的语义

旧 TASK-007/TASK-008 carrier powers 定义了每个平台**已有验证覆盖范围**。

新 carrier 记录：

```text
within_existing_coverage = true / false
extension_validation_required = !within_existing_coverage
```

**越界本身不再是 terminal exclusion gate。**

## 6.2 真正的 production hard gate

每个 TASK-013 / TASK-014 新 carrier 在第一次 EDOF materialization 前必须绑定：

```text
exact carrier SHA
exact frozen residual DAT SHA
RESIDUAL_VALIDATION_546_v1
```

并执行：

### Actual-eye low-order

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

### Standard-eye low-order

同样：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

### Actual-eye EPD5 ray health

MONO/EDOF 均要求：

```text
9 normalized pupil rays
success = true
error = 0
vignette = 0
```

### Verdict

```text
validation_pass =
  actual_low_order_pass
  AND standard_low_order_pass
  AND MONO_ray_health_pass
  AND EDOF_ray_health_pass
```

只有 PASS 才允许该 carrier 的 EDOF production。

## 6.3 Validation cache / evidence

```text
residual_validations/<carrier_id>/<carrierSHA12>_<residualSHA12>/
  ACTUAL_EDOF.zmx
  STD_MONO.zmx
  STD_EDOF.zmx
  VALIDATION.json
residual_validations/VALIDATION_INDEX.json
```

缓存仅在 exact carrier SHA、residual SHA、policy ID、prior PASS 和 artifact SHA 全部匹配时复用。

---

# 7. TASK-013 与 TASK-014 的执行关系

二者是平行扩展，不互为 scientific prerequisite：

```text
TASK-013 task-local failure != TASK-014 automatic STOP
TASK-014 task-local failure != TASK-013 automatic STOP
```

### Task-local failure

例如：

- 某 exact carrier low-order validation fail；
- 某 carrier ray-health fail；
- 某 task P/Q solve fail。

只暂停该 task，保存 diagnostics；另一 task 可以继续。

### Shared-provenance failure

以下情况同时阻止二者：

- frozen residual DAT SHA mismatch；
- `STD_IOL_EYE_2024` immutable hash mismatch；
- TASK-008 manifest/lock drift；
- TASK-009 production contract drift；
- TASK-011/TASK-012 frozen evidence 被改写。

---

# 8. Final clinically normalized research layer

只有 TASK-013 和 TASK-014 各自 acceptance PASS 后才组合：

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configs
```

不得把 `TASK-013 N0 + legacy TASK-011 A0/B0/C0` 称为统一临床屈光平面规范化96配置。

---

# 9. Implementation / local execution order

```text
A. preserve rollback checkpoints
B. offline code QA
C. verify existing TASK-011 ZMX archive; no legacy rerun
D1. TASK-013 carrier build / coverage classification / exact residual validation / 24-config acquisition
D2. TASK-014 carrier build / coverage classification / exact residual validation / 72-config acquisition
E. Web-review TASK-013 evidence
F. Web-review TASK-014 evidence
G. combine accepted extensions into 96-config dataset
H. render all through-focus supplementary figures
```

D1 与 D2 独立；其中一个 task-local failure 不自动阻止另一个。

权威本地交接：

```text
docs/TASK_013_014_LOCAL_EXECUTION_HANDOFF_V2_2026-08-20.md
```

---

# 10. Git checkpoints

```text
checkpoint/pre-vertex-correction-2026-08-20
  fa401e2101023e6e409a5366f26f0da134b5476f

checkpoint/task014-phase-c-ready-2026-08-20
  TASK-014 Phase C code-ready state

checkpoint/pre-residual-validation-trigger-2026-08-20
  4e21f94bf8b68767edf5dae620d90bc404394c5c
```

相关文档：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
docs/CHECKPOINT_PRE_RESIDUAL_VALIDATION_TRIGGER_2026-08-20.md
docs/TASK_013_014_RESIDUAL_POWER_EXTENSION_ADDENDUM_2026-08-20.md
```

PR #26 保持 Draft / open / unmerged。

---

# 11. Current STOP conditions

1. 不修改 TASK-005–009 frozen assets/method locks；
2. 不改变 TASK-008 manifest/hash/lock-set；
3. sampling 保持128；
4. 不恢复 retired pre-TASK009 production path；
5. matched pair 继续使用 residual-free MONO EFFL；
6. 不扩大冻结 focus/peak window；
7. 不重新优化 B0.20 或 frozen residual；
8. 不把 residual 引起的焦移写入 carrier physical identity；
9. 不把 censor/lower-bound 静默当精确值；
10. 不把确定性矩阵当随机临床样本做传统显著性推断；
11. power outside historical envelope **只触发 extension validation，不自动排除**；
12. exact-carrier residual validation fail 时停止该 task 的 EDOF production；
13. residual DAT SHA mismatch 等 shared provenance failure 同时停止 TASK-013/014；
14. canonical ZMX SHA 与 analyzed model 不一致时不得 acceptance；
15. TASK-013/014 不得覆盖 TASK-011/TASK-012 evidence；
16. 不修改 legacy `BASELINE_CORNEA_SPECS` 或 legacy `distance_corrected_cornea_power_d()`；
17. 不把 ATC source refraction 与 TASK-014 prescription 相加；
18. 不把 frozen A0/B0/C0 静默改名为 A0V12/B0V12/C0V12；
19. 新 evidence/code inconsistency 先审核，不以重跑全部 legacy matrix 作为默认修复。
