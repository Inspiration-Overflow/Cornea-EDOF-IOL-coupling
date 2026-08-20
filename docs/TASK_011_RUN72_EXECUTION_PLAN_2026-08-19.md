# TASK-011 Run72 正式执行计划

日期：2026-08-19  
状态：Web execution contract frozen；Run72 尚未启动

## 1. 目的

TASK-011 不再验证 TASK-009 的分析方法，而是使用已经通过并正式冻结的方法执行完整 nominal matrix：

```text
18 physical carriers
× MONO / EDOF
× EPD3 / EPD5
= 72 configurations
```

每个 configuration 使用15个 retina-anchored through-focus planes，因此完整目标为：

```text
72 completed configs
1080 through-focus rows
36 matched MONO/EDOF deltas
36 frozen pair-MONO angular-scale references
```

本任务不得重新设计或重新优化 TASK-005–008 scientific assets，也不得重新执行 TASK-009 representative sampling study。

## 2. 正式身份

```text
baseline = MVP_2026_v2
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
production_sampling = 128

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL

Run72 clearance = TASK009_RUN72_WEB_CLEARANCE_v1
```

## 3. 唯一正式入口

```text
scripts/run_task_011_run72.py
```

主执行链：

```text
TASK-009 Run72 clearance
→ TASK-008 strict manifest reload
→ 36 residual-free MONO EFFL references
→ pair_reference_set_sha256
→ ZosMtfaPairScaleAnalysisBackend(sampling=128)
→ RunEnvironment exact provenance
→ run_analysis_batch(72 configs)
→ exact 72/36/1080 aggregate acceptance
→ sanitized GitHub evidence
```

不得用单独 probe、手工 CSV 或旁路 backend 代替正式 `run_analysis_batch()`。

## 4. 第一次正式运行

开始前：

1. checkout Web 指定的 TASK-011 exact HEAD；
2. tracked working tree clean；
3. OpticStudio/Zemax 残留进程为0；
4. Windows offline：pytest / ruff / compileall / uv-lock PASS；
5. 不做新的 representative optical probe。

正式命令：

```powershell
uv run python scripts/run_task_011_run72.py `
  --install-dir <OpticStudio安装目录> `
  --project-dir project_mvp_2026_v2_zmx `
  --write-repo-evidence
```

也可以预先设置 `WHOLE_EYE_ZOS_INSTALL_DIR` 后省略 `--install-dir`。

脚本自身负责 clearance、manifest、lock-set、settings、acquisition contract 和 provenance preflight。

## 5. 36 条 pair-reference 规则

第一次正式运行必须由 frozen manifest 取得36个 `pair_key`，每个 pair 在 residual-free MONO formal carrier 的 nominal distance 状态读取一次 EFFL。

每条至少保存：

```text
pair_key
reference_effl_mm
mm_per_degree
model_sha256
entity_fingerprint
```

36条记录形成 `pair_reference_set_sha256`。

这个集合是本次 Run72 的正式角频率坐标 provenance：

- MONO/EDOF 共用；
- 全部 defocus planes 共用；
- 失败重跑必须复用；
- 不得因 EDOF diagnostic EFL 重新定义 cpd 轴。

## 6. 失败与恢复

### 6.1 Config-level failure

单个 config 失败时，`run_analysis_batch()` 继续隔离并记录其他 config。批次结束后脚本写本地 report：

```text
project_mvp_2026_v2_zmx/results/task011_run72/reports/<run_id>.json
```

若 `failed_config_ids` 非空，脚本 exit code=2。

**不要重新执行完整72。**

使用：

```powershell
uv run python scripts/run_task_011_run72.py `
  --install-dir <OpticStudio安装目录> `
  --project-dir project_mvp_2026_v2_zmx `
  --resume-report <上一批report.json> `
  --write-repo-evidence
```

resume 必须：

- 重新验证先前所有 completed `config_result.json`；
- 只选择 prior `failed_config_ids`；
- 使用新 run ID；
- 复用 prior 36-reference set；
- 校验 `pair_reference_set_sha256`；
- 不重复已成功 config。

### 6.2 Preflight failure

若 clearance / manifest / lock-set / settings / acquisition ID/hash/scale 不一致：

- 不启动正式 optical acquisition；
- STOP 并返回 Web；
- 不自行修改科学设置绕过。

### 6.3 机械 API 问题

本地允许在同一 TASK-011 工作中最小修复纯机械的 enum/header/type/path/runtime wrapper 问题，并运行离线回归后继续；但不得修改：

- sampling=128；
- frequency-scale definition；
- defocus grid；
- MTFa/DOF50 definition；
- frozen carrier/cornea/residual；
- manifest identity；
- acceptance thresholds。

如果修复改变科学含义，STOP 返回 Web。

## 7. 成功 acceptance

只有以下全部满足才可标记 Run72 PASS：

```text
completed configs = 72
completed config IDs = exact frozen manifest IDs
failed configs = 0
rows/config = 15
total through-focus rows = 1080
matched pairs = 36
pair-reference records = 36
pair-reference set hash present
```

每个 ConfigResult 仍必须通过已有 entity/model/retina/IOL/ELP/vignetting/artifact provenance validator。

## 8. GitHub evidence

成功后脚本生成：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

预期行数：

```text
CONFIG_RESULTS = 72
THROUGH_FOCUS = 1080
PAIRED_DELTAS = 36
```

Evidence JSON 保存：

- all run IDs；
- exact settings/acquisition/manifest/lock identities；
- 36 pair-reference records 与集合 SHA256；
- acceptance counts；
- 三个 CSV SHA256；
- `evidence_only=true`；
- `formal_scientific_lock=false`。

不得把本机 absolute result paths 写进 GitHub evidence。大型 `.zmx`、逐配置 plots/results 留在 project results/diagnostics。

## 9. 本地结束条件

成功时：

1. 只提交上述 sanitized TASK-011 evidence 与必要的机械代码修复；
2. push 到 `feat/task-011-run72`；
3. 回复 Web：最终 commit、local report path/SHA、72/36/1080 counts、pair-reference-set SHA、evidence SHA、是否发生 failed-only resume；
4. STOP。

不要在同一轮继续做 GUI、额外 repeatability、二次 representative study 或新的敏感性分析。

## 10. Web 后续

Web 收到 TASK-011 evidence 后独立审核：

- exact counts / IDs；
- hashes/provenance；
- 36 pair references；
- paired deltas；
- failure/resume history；
- 是否存在 censoring、异常值或需要解释的结果模式。

只有该审核完成后，才进入正式科学结果解释/统计汇总或可选 TASK-010 GUI 收尾。
