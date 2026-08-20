# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD及已批准的独立任务计划提供。

## Metadata

- document_id: `RMD-0001`
- version: `1.9`
- status: `active`
- source_docs: `URD-0001 v1.6`, `ADD-0001 v1.6`, `MDD-0001 v1.5`, `TDD-0001 v1.6`, `TASK-013-NATIVE-CORNEA-REFERENCE`
- last_updated: `2026-08-20`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-011-run72`
- active_production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_frequency_scale: `paired_residual_free_MONO_EFFL`
- active_production_sampling: `128`
- completed_analysis_task: `TASK-012`
- active_extension_task: `TASK-013`
- next_science_phase: `TASK-013 native/untreated cornea reference acquisition → offline comparison → final manuscript consolidation`

---

# 1. Dual-environment execution model

## Web

负责科学规范、冻结决策、Python 代码与测试、GitHub static review、structured evidence 审核、TASK-012 纯离线结果统计和图表，以及 TASK-013 文档/代码实现与后续离线整合。

## Local Windows / ZCode

只负责必须由真实 OpticStudio/ZOS-API 给出的新事实。TASK-011 正式 Run72 已完成；TASK-012 完全基于冻结 evidence。TASK-013 是经过明确科学问题批准的独立新增 optical acquisition，只运行新增 N0 层，不重跑既有72配置。

## Cost-aware rule

- 已满足 gate 的代表配置不重复运行；
- 已接受的72-config Run72 不因 TASK-013 或少量 censoring 重跑；
- 不事后扩大冻结 focus/peak window；
- 普通统计、图表、provenance、文档和归档工具留在 Web/GitHub；
- 新的本地 optical acquisition 必须有独立、明确的科学问题支持；TASK-013 的缺失未治疗角膜基线已经满足这一条件；
- 任何新任务都不得静默改写旧 scientific identity。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

unit tests 不依赖 OpticStudio。正式 scientific assets immutable；analysis provenance 必须版本化/hashable。`.zmx` exact analyzed model 从 TASK-013 起是强制研究 artifact，并要求 canonical archive + SHA index。

---

# 3. Completed build path and active extension

| Task | Status | Frozen / planned output |
| --- | --- | --- |
| TASK-001 | complete | uv/src/tests/git skeleton |
| TASK-002 | complete | ZOS session lifecycle validated |
| TASK-003 | complete | domain + ProjectStore + hash/run provenance |
| TASK-004 | complete then migrated | current MTFa metric layer |
| TASK-005 | complete | LB/ATC、standard eye、A0/B candidates/C0 |
| TASK-006 | complete | B0.20 immutable lock |
| TASK-007 | complete | 18 P/Q、3 residuals、9 calibrations、TDD-999 cleared |
| TASK-008 | complete | 18 formal carrier locks、3 residual locks、72-config manifest |
| TASK-009 | complete | paired-MONO MFE MTFA production method + sampling 128 |
| TASK-011 | complete | formal Run72: 72 configs / 36 pairs / 1080 rows; Web review PASS |
| TASK-012 | complete | pure-offline reconstruction + censor-aware factorial analysis + 24 figures + result review PASS |
| TASK-013 | approved / implementation | N0 reference cornea + 6 new carriers + 24 configs + 12 pairs + 360 TF rows + canonical ZMX archive |

TASK-010 GUI 保持 optional，不是科学前置条件。

TASK-013 计划全文：

```text
docs/TASK_013_NATIVE_CORNEA_REFERENCE_PLAN_2026-08-20.md
```

---

# 4. Frozen production identity

以下 TASK-008/009/011 identity 继续只读：

```text
baseline_id = MVP_2026_v2
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
```

生产方法：

```text
residual-free MONO EFFL once per matched pair
→ paired_residual_free_MONO_EFFL angular scale
→ ZosMtfaPairScaleAnalysisBackend
→ MFE MTFA Grid=1
→ 15-plane MTFa + fixed-frequency MTF + HOA readback
→ ConfigResult / matched deltas
```

TASK-013 必须复用该 production method，但使用独立 extension identity，不改写 TASK-008 manifest/hash。

---

# 5. TASK-011 — Formal Run72 complete

```text
code_commit = 01f13b768cf1eca361703469b2fdce3d21f3376d
formal_evidence_commit = f28b3032136aa28f54abb5fe5129765a125d3926
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
completed_configs = 72
failed_configs = 0
matched_pairs = 36
through_focus_rows = 1080
pair_reference_records = 36
pair_reference_set_sha256 = a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
acceptance_passed = true
run72_complete = true
```

Formal evidence：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

现有代码已在每个 target 目录保存 exact `model.zmx`，并把其纳入 `ConfigArtifacts` 的强制存在校验；TASK-013 只增加稳定 canonical archive，不需要为“补保存模型”重跑 TASK-011。

---

# 6. TASK-012 — Offline analysis complete

正式计划：

```text
docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md
```

正式产物：

```text
docs/evidence/task012/TASK_012_ANALYSIS_EVIDENCE.json
docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv
docs/evidence/task012/TASK_012_INTERACTION_CONTRASTS.csv
docs/evidence/task012/TASK_012_COUPLING_MATRIX.csv
docs/evidence/task012/figures/
docs/TASK_012_RESULTS_REVIEW_2026-08-20.md
```

Acceptance：

```text
pairs = 36
contrasts = 1152
coupling cells = 9
figures = 24
DOF50 exact = 31
DOF50 lower_bound = 5
peak-window-censored pairs = 8
reconstruction_gate = PASS
censor_propagation = PASS
result_review = PASS_WITH_SCIENTIFIC_CAVEATS
opticstudio_used = false
```

TASK-012 structured evidence 不因 TASK-013 改写。后续 N0 comparison 必须作为新的离线分析层，并清楚标记来源为 TASK-013 + frozen TASK-011。

---

# 7. TASK-013 — N0 native/untreated cornea reference extension

## 7.1 Scientific scope

正式 N0 ID：

```text
N0 = native / untreated reference cornea
```

N0 使用既有 `MAIN_CORNEA_LIOU_555_v1` 参考角膜 scaffold；它描述角膜状态，不把 `ATC_M3_AL24477` 重新定义为正常眼。

新增矩阵：

```text
2 Base × 1 N0 × 3 Platform = 6 new physical carriers
6 carriers × MONO/EDOF × EPD3/EPD5 = 24 new configs
12 matched pairs
360 through-focus rows
```

完成后完整研究数据库为96 configs，但 TASK-011 仍然是原72-config frozen run，TASK-013 是独立24-config extension。

## 7.2 Carrier and residual route

```text
N0 cornea scaffold
→ per Base Q=0 P/R solve
→ per Platform STD_IOL_EYE_2024 power-specific Q(P)
→ actual-eye P–Q recheck (max 2)
→ 6 canonical N0 carriers
→ frozen residual power-envelope gate
→ 12 pair-MONO EFFL references
→ 24-config production acquisition
```

若任一 N0 power 超出相应平台既有 residual validated power envelope，必须 STOP 于 EDOF production 前；允许补做原 residual 的 replay validation，但不允许重新优化 residual。

## 7.3 Canonical ZMX output

固定：

```text
project_mvp_2026_v2_zmx/models/task013_native_reference/
  cornea/N0_REFERENCE_CORNEA.zmx
  carriers/CAR_<base>_N0_<platform>.zmx
  runs/<run_id>/pair_references/<pair_key>.zmx
  runs/<run_id>/configs/<config_id>.zmx
  runs/<run_id>/MODEL_INDEX.csv
```

每个 exact analyzed config model 必须存在于 canonical `configs/`，并记录 SHA-256。工作目录中的 `results/.../<config_id>/model.zmx` 不可替代 canonical archive。

`MODEL_INDEX.csv` 至少绑定：model role、run/config/pair/carrier、base/cornea/platform/state/pupil、project-relative path、SHA-256。

## 7.4 Existing TASK-011 model archive

新增纯文件工具，在**不启动 OpticStudio**的情况下将已有：

```text
72 results/task011_run72/<run_id>/<config_id>/model.zmx
36 diagnostics/task011/pair_reference_models/<pair_key>.zmx
```

复制并 hash-verify 到：

```text
models/task011_run72/archive/<run_id>/configs/
models/task011_run72/archive/<run_id>/pair_references/
models/task011_run72/archive/<run_id>/MODEL_INDEX.csv
```

该操作只改善 provenance/可查找性，不改变 TASK-011 evidence。

---

# 8. TASK-013 implementation order

必须遵守“先文档、后代码、最后光学执行”：

```text
A. docs/TASK_013_NATIVE_CORNEA_REFERENCE_PLAN_2026-08-20.md + RMD sync
B. offline code / tests
   - N0 extension identities and 24-config manifest
   - N0 carrier builder
   - backward-compatible carrier/residual directory override
   - TASK-013 runner
   - ZMX archive + MODEL_INDEX helper
   - TASK-011 retroactive archive helper
C. offline gates: pytest / ruff / compileall / uv-lock
D. Local Windows OpticStudio: N0 + 6 carriers + 12 refs + 24 configs
E. Web review: 24/12/360 + model SHA/index audit + censor review
F. offline N0/A0/B0/C0 through-focus supplement
```

任何代码改动不得要求 TASK-011 rerun 才证明 backward compatibility。

---

# 9. Git checkpoints

```text
feat/task-009-fft-mtf-main
  TASK-009 complete / Run72 Web clearance

feat/task-011-run72
  TASK-011 formal Run72 accepted
  TASK-012 offline analysis accepted
  manuscript working draft assembled
  TASK-013 document freeze
  TASK-013 code implementation
  TASK-013 local acquisition/evidence (pending Windows execution)
```

PR #26 保持 Draft，除非另行授权改变状态或合并。

---

# 10. Current STOP conditions

1. TASK-005–009 frozen assets/method locks 不得修改；
2. TASK-008 manifest/hash/lock-set 不得因 TASK-013 改变；
3. sampling lock 保持128；
4. 不恢复任何已退休的 pre-TASK009 production path；
5. 不使用 per-state/EDOF EFFL 改变 matched MONO/EDOF cpd 坐标；
6. 不因 peak/DOF censoring 扩大预注册窗口；
7. 不重新优化 B0.20 或 residual profiles；
8. 不把 `DeltaF_residual` 写入 carrier physical identity；
9. 不把 DOF50 lower bound 或 peak-window result 静默当精确值；
10. 不把确定性矩阵当随机临床样本做传统显著性检验；
11. 不为获得特定论文叙事事后改变主要 outcome/censor policy/interaction definition；
12. N0 carrier power 超出 frozen residual calibration envelope 时必须先 STOP/validate；
13. canonical ZMX copy 的 SHA 与 analyzed model 不一致时不得完成该 config archive；
14. custom carrier-directory 支持不得改变 TASK-011 默认目录/行为；
15. TASK-013 不得覆盖 TASK-011/TASK-012 structured evidence；
16. 新 evidence/code inconsistency 出现时先停止解释并做 Web review，不以重跑全部 OpticStudio 矩阵作为默认修复。
