# RMD 执行状态

> `RMD-0001 v1.6` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`feat/task-011-run72`
- TASK-005/006/007/008：完成并冻结
- TDD-999：cleared
- TASK-009：**complete**
- production sampling：**128，正式锁定**
- Run72 Web clearance：**AUTHORIZED**
- TASK-011 Web runner：**IMPLEMENTED / CI PASS**
- Run72：**尚未启动**
- 新增 TASK-009 representative OpticStudio 复验：**不需要**

## 不可变正式身份

```text
carrier_count = 18
residual_count = 3
nominal_config_count = 72
pair_key_count = 36

manifest_hash =
29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49

lock_set_hash =
b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 =
0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 =
f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
```

TASK-011 对 TASK-005–009 scientific/method locks 只读。

---

## TASK-009 已完成

Corrected paired-MONO-scale representative evidence 已完成并经 Web 审核：

```text
evidence commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd
JSON SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49
CSV SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
```

128→256 convergence、repeatability、6-config production integration、entity/ray-health、fixed-frequency diagnostic 全部 PASS；不启动256→512 escalation。

RunEnvironment/backend provenance 已 fail-closed 绑定 acquisition contract ID/hash 与 `paired_residual_free_MONO_EFFL`；旧 `AS_FftMtf` 和 per-state-EFL production 语义已退休。

独立 Run72 放行凭证：

```text
docs/evidence/task009/TASK_009_RUN72_WEB_CLEARANCE.json
clearance_id = TASK009_RUN72_WEB_CLEARANCE_v1
run72_authorized = true
no_additional_representative_opticstudio_rerun_required = true
```

---

## TASK-011 Web 实现

正式入口：

```text
src/whole_eye_mvp/run72.py
scripts/run_task_011_run72.py
```

执行计划：

```text
docs/TASK_011_RUN72_EXECUTION_PLAN_2026-08-19.md
```

### 首次批次

脚本在启动正式72-config acquisition 前执行严格 clearance/manifest/lock/settings/acquisition provenance preflight。

真实 OpticStudio session 中首先对 frozen 36 `pair_key` 各读取一次 residual-free MONO nominal-distance EFFL，记录：

```text
pair_key
reference_effl_mm
mm_per_degree
model_sha256
entity_fingerprint
```

形成 `pair_reference_set_sha256`。之后72 configs 全部通过：

```text
ZosMtfaPairScaleAnalysisBackend(sampling=128)
→ run_analysis_batch
```

### 失败恢复

首次批次结束都会保存：

```text
project_mvp_2026_v2_zmx/results/task011_run72/reports/<run_id>.json
```

若 config-level failure 存在：

- 已成功 config 不重跑；
- `--resume-report` 只选择 prior `failed_config_ids`；
- 使用新 run ID；
- 重新验证 prior completed `config_result.json`；
- 必须复用第一次36-reference set；
- `pair_reference_set_sha256` 不一致立即 fail-closed。

### 完整 acceptance

```text
completed configs = exact 72
failed configs = 0
through-focus rows/config = 15
total through-focus rows = 1080
matched deltas = 36
pair-reference records = 36
```

成功 evidence：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

CSV 保留每个 config 实际 `run_id`；evidence JSON 保存36 pair references 与其集合 SHA256，但不保存本机 absolute result paths。

---

## TASK-011 Web CI

Web runner、aggregate、clearance、36-reference hash 和 execution-plan 代码路径已通过：

```text
source HEAD = d03f29dd830d71068664811c1f4d0717a8bbbc43
GitHub Actions run = 32332799561
pytest = 203 passed
ruff = PASS
compileall = PASS
uv lock = PASS
final offline gate = PASS
```

本次 Web 开发未启动 OpticStudio，未修改 TASK-005–009 scientific/method locks。

---

## 下一执行

下一次 Windows/OpticStudio 工作只做一个**单次大粒度 TASK-011 Run72**，不再插入小 probe。

正式命令与 failed-only resume 规则以：

```text
docs/TASK_011_RUN72_EXECUTION_PLAN_2026-08-19.md
```

为准。

TASK-010 GUI 不是 CLI Run72 的前置条件。

---

## 当前 STOP

- 不修改 TASK-005–009 frozen assets/method locks；
- 不恢复 `AS_FftMtf` production path；
- 不使用 per-state EFL 作为 matched-pair production scale；
- 不再次执行 TASK-009 representative validation；
- Run72 preflight 不通过时在 optical acquisition 前 STOP；
- config-level failure 后不得重新跑完整72，必须优先 failed-only resume；
- 首次36-reference set 在 resume 中不得重新定义。
