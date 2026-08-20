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
- active_task_branch: `feat/task-009-fft-mtf-main`
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

三个 frozen pair：

```text
LB+A0+WFS+EPD3
ATC+B0+RAD+EPD5
ATC+C0+HOA+EPD5
```

corrected paired-MONO scale 下：

- 128→256 convergence 全 PASS；
- repeat128 全 PASS；
- 6-config `run_analysis_batch` integration = 6/6 PASS；
- entity/ray-health PASS；
- 20/40/60 cpd production-vs-repeat MTFA abs=0；
- 20/40/60 cpd MTFA-vs-mean(MTFT,MTFS) abs=0；
- HOA TF mean 128→256 从旧坐标的2.019%修正为0.520%；
- 无需256→512 escalation。

Evidence：

```text
commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd
JSON SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49
CSV SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
```

## 4.3 Run-level provenance hardening

`RunEnvironment` 必须非空保存：

```text
program_version
opticstudio_version
baseline_id
analysis_settings_id
manifest_hash
lock_set_hash
acquisition_contract_id
acquisition_contract_hash
frequency_scale_mode
```

`run_analysis_batch()` 在任何 acquisition 前检查 backend 自报的 acquisition ID/hash/scale 是否与 RunEnvironment 完全一致；旧 per-state-EFL backend 不能静默进入正式 Run72。

---

# 5. TASK-010 — GUI integration（非 Run72 科学前置）

TASK-010 仅负责：

- 将已验证的 `run_analysis_batch` 接到 GUI action dispatch；
- progress/log/failed-target rerun UI；
- 必要时做最小 GUI smoke。

**TASK-010 不再负责首次实现或首次验证 real AnalysisBackend，也不是 CLI Run72 的科学前置条件。**

考虑本地运行时间成本，除非 GUI 本身是当轮目标，不应为了 Run72 再做一次长 optical full-flow smoke。

---

# 6. TASK-011 — Run72

TASK-009 Web clearance 后可进入 Run72。正式批次：

\[
18\ carriers\times2\ states\times2\ pupils=72\ configs
\]

每 config 15 planes，共1080 through-focus rows、36 matched deltas。

Run72 preflight 必须在启动 OpticStudio 前检查：

1. clean tracked checkout；
2. offline pytest/ruff/compileall/uv-lock PASS；
3. frozen TASK-008 manifest 18/72/36 + exact hashes PASS；
4. `TASK009_PRODUCTION_SAMPLING_LOCK_v1` 存在且 sampling=128；
5. acquisition contract ID/hash = pair-MONO v2；
6. frequency scale mode = `paired_residual_free_MONO_EFFL`；
7. `RunEnvironment` 完整；
8. backend provenance 与 environment exact match。

Run72 acceptance：

```text
completed config IDs = exact frozen 72
failed = 0 after any permitted rerun
rows/config = 15
total rows = 1080
matched deltas = 36
```

失败 config 不计 completed；failed-only rerun 使用新 run ID，不重跑已成功 config。

---

# 7. Git checkpoints

```text
feat/task-009-fft-mtf-main
  1. analysis migration
  2. local real MTFA evidence
  3. paired-MONO scale correction + corrected evidence
  4. Web sampling lock
  5. Web RunEnvironment/backend provenance hardening
  6. active specs/status synchronization
  7. CI + Run72 Web clearance

next: TASK-011 / Run72 branch or approved continuation
```

PR #25 保持 Draft 作为 Web quality gate，除非另行授权合并。

---

# 8. Current STOP conditions

仍然有效的 STOP：

1. TASK-005–008 frozen assets 不得修改；
2. TASK-008 manifest/hash/lock-set preflight 不通过不得启动 Run72；
3. sampling lock 缺失或不是128不得启动；
4. acquisition ID/hash/scale 与 formal contract 不同不得启动；
5. RunEnvironment/backend provenance 不一致不得启动；
6. 单 config optical/ray/entity/export failure 不能伪装 completed；
7. 不得恢复 `AS_FftMtf` production path；
8. 不得使用 per-state EFFL 改变 matched MONO/EDOF cpd 坐标；
9. 不得为了重复确认 TASK-009 已通过 gate 再执行耗时代表性复验。

TASK-009 已不存在 sampling/convergence/repeatability/crosscheck STOP；这些门禁已通过并正式固化。