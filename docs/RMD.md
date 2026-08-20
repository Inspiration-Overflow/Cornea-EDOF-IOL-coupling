# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 提供。

## Metadata

- document_id: `RMD-0001`
- version: `1.6`
- status: `active`
- source_docs: `URD-0001 v1.6`, `ADD-0001 v1.6`, `MDD-0001 v1.5`, `TDD-0001 v1.6`
- last_updated: `2026-08-19`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-011-run72`
- active_production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_production_sampling: `128`

---

# 1. Dual-environment execution model

## Web

负责科学研究/规范/冻结决策、Python 主代码与测试、GitHub static review、结构化 evidence 审核、formal gate/clearance。

## Local Windows / ZCode

只负责必须由真实 OpticStudio/ZOS-API 给出的新事实：runtime/API 差异、`.zmx` 实机结果、正式大批次 Run72，以及确有必要的 GUI/full-flow smoke。

## Cost-aware handoff rule

本地 OpticStudio 任务成本高。TASK-009 corrected representative batch 已约32分钟，前一轮约55分钟。因此：

- 文档、provenance、普通 Python、unit regression 全部留在 Web/GitHub CI；
- 已满足科学 gate 的代表配置不重复运行；
- 本地任务尽量一次大批量、fail-closed；
- JSON/CSV evidence 推 GitHub，本地只回 commit/path/hash/PASS/FAIL/关键 summary；
- science definition 变化必须回 Web；
- 不用“保险起见”增加未预注册 sampling 层级或重复 probe。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

unit tests 不依赖 OpticStudio。正式 scientific assets immutable；analysis provenance 必须版本化/hashable；formal lock 同 ID 不允许以不同科学内容覆盖。

---

# 3. Completed build path

| Task | Status | Frozen output |
| --- | --- | --- |
| TASK-001 | complete | uv/src/tests/git skeleton |
| TASK-002 | complete | ZOS session lifecycle validated |
| TASK-003 | complete | domain + ProjectStore + hash/run provenance |
| TASK-004 | complete then migrated | current MTFa metric layer |
| TASK-005 | complete | LB/ATC、standard eye、A0/B candidates/C0 |
| TASK-006 | complete | B0.20 immutable lock |
| TASK-007 | complete | 18 P/Q、3 residuals、9 calibrations、TDD-999 cleared |
| TASK-008 | complete | 18 formal carrier locks、3 residual locks、72-config manifest |
| TASK-009 | complete | paired-MONO MTFA production method + 128 formal sampling lock + Web provenance hardening |

TASK-008 identity 只读：

```text
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
```

---

# 4. TASK-009 final state

## 4.1 Production method

```text
frozen TASK-008 manifest
→ residual-free MONO EFFL once per matched pair
→ paired_residual_free_MONO_EFFL angular scale
→ ZosMtfaPairScaleAnalysisBackend
→ MFE MTFA Grid=1 / Data Type=0 / Wave1 / Field1
→ 15-plane MTFa + MTF10..60
→ HOA / footprint / entity invariants
→ ConfigResult
→ run_analysis_batch
→ matched pair deltas
```

Active identities：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL

TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2

TASK009_PRODUCTION_SAMPLING_LOCK_v1
production_sampling = 128
production_sampling_locked = true
sampling_escalation_256_active = false
```

`AS_FftMtf`/`New_FftMtf` production path retired。`NOMINAL_MAIN_FFT_MTF_555_v2` 名称中的 FFT 仅保留历史 hash continuity。

## 4.2 Corrected representative evidence

三个 frozen pair 在 corrected paired-MONO scale 下：128→256 convergence 全 PASS、repeat128 全 PASS、6-config `run_analysis_batch` integration 6/6 PASS、entity/ray-health PASS，且独立 fixed-frequency diagnostic PASS。无需256→512 escalation。

Evidence：

```text
commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd
JSON SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49
CSV SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
```

## 4.3 Run-level provenance hardening

`RunEnvironment` 必须非空保存 program/OpticStudio version、baseline、analysis settings、manifest、lock-set、acquisition contract ID/hash 与 frequency-scale mode。`run_analysis_batch()` 在 acquisition 前检查 backend 自报的 acquisition ID/hash/scale 是否完全一致。

---

# 5. TASK-010 — GUI integration（非 Run72 科学前置）

TASK-010 只负责 GUI action dispatch、progress/log/failed-target rerun UI 与必要的最小 GUI smoke。**它不是 CLI Run72 的科学前置条件。**

---

# 6. TASK-011 — Run72

TASK-011 的 Web runner 已实现于：

```text
src/whole_eye_mvp/run72.py
scripts/run_task_011_run72.py
```

正式批次：

\[
18\ carriers\times2\ states\times2\ pupils=72\ configs
\]

每 config 15 planes，共1080 through-focus rows、36 matched deltas。

## 6.1 Preflight

启动正式 acquisition 前必须满足：

1. clean tracked checkout；
2. offline pytest/ruff/compileall/uv-lock PASS；
3. `TASK009_RUN72_WEB_CLEARANCE_v1` exact PASS；
4. frozen TASK-008 manifest 18/72/36 + exact manifest/lock-set hash；
5. sampling=128 formally locked；
6. pair-MONO acquisition ID/hash/scale exact；
7. complete `RunEnvironment`；
8. backend provenance exact match。

## 6.2 Angular-scale reference freeze

首次 Run72 在真实 OpticStudio 中，对 frozen manifest 的 36 个 `pair_key` 各读取一次 residual-free MONO nominal-distance EFFL。形成 36 条：

```text
pair_key
reference_effl_mm
mm_per_degree
model_sha256
entity_fingerprint
```

并计算 `pair_reference_set_sha256`。该集合定义本次 Run72 的角频率坐标 provenance。

- 同一 pair 的 MONO/EDOF、全部 defocus plane 都复用同一 reference；
- 如果后续仅重跑失败 config，必须复用第一次 report 中同一 36-reference set；
- resume 时集合 hash 不一致立即 fail-closed；
- 不因失败重跑重新测量/改变角尺度。

## 6.3 Failure/resume

首次运行无论是否有 config 失败，都保存本地 report：

```text
project_mvp_2026_v2_zmx/results/task011_run72/reports/<run_id>.json
```

普通 config-level failure 由 `run_analysis_batch()` 隔离，不回滚已完成结果。

若 report 中 `failed_config_ids` 非空：

```text
--resume-report <prior-report.json>
```

只重跑这些 failed IDs，生成新 run ID；已完成 config 的 `config_result.json` 必须重新校验后复用。最终 acceptance 可以由多个 run ID 的完成结果组合，但每个 config 的实际 `run_id` 必须保留在正式 CSV provenance 中。

## 6.4 Acceptance / evidence

完整 acceptance：

```text
completed config IDs = exact frozen 72
failed = 0 after any permitted rerun
rows/config = 15
total rows = 1080
matched deltas = 36
pair-reference records = 36
```

成功后只提交 sanitized structured evidence：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

其中 evidence JSON 保存 36 条 pair-reference records + `pair_reference_set_sha256`，但不保存本机绝对 result paths。大型 working `.zmx` 与逐配置本地 artifacts 留在 project results/diagnostics，不提交 Git。

---

# 7. Git checkpoints

```text
feat/task-009-fft-mtf-main
  TASK-009 complete / Run72 Web clearance

feat/task-011-run72
  1. Web Run72 runner + exact aggregate
  2. failed-only resume + fixed 36-reference provenance
  3. Web CI + execution-plan freeze
  4. one formal local Run72 batch
  5. optional failed-only resume
  6. sanitized TASK-011 evidence
  7. Web final review
```

PR #25 和 TASK-011 PR 均保持 Draft，除非另行授权合并。

---

# 8. Current STOP conditions

1. TASK-005–008 frozen assets 不得修改；
2. TASK-008 manifest/hash/lock-set preflight 不通过不得启动 Run72；
3. sampling lock 缺失或不是128不得启动；
4. acquisition ID/hash/scale 与 formal contract 不同不得启动；
5. RunEnvironment/backend provenance 不一致不得启动；
6. 首次固定的 36-reference set 在 resume 中 hash 不一致不得继续；
7. 单 config optical/ray/entity/export failure 不能伪装 completed；
8. 不得恢复 `AS_FftMtf` production path；
9. 不得使用 per-state EFFL 改变 matched MONO/EDOF cpd 坐标；
10. 不得为了重复确认 TASK-009 已通过 gate 再执行耗时代表性复验。
