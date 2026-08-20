# RMD 执行状态

> `RMD-0001 v1.6` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`feat/task-009-fft-mtf-main`
- TASK-005/006/007/008：完成并冻结
- TDD-999：cleared
- TASK-009 corrected paired-MONO optical gate：**PASS**
- TASK-009 Web provenance/spec consolidation：**PASS**
- production sampling：**128，Web 正式锁定**
- Run72 Web clearance：**AUTHORIZED**
- Run72：**尚未启动**
- 新增 representative OpticStudio 复验：**不需要**

## TASK-008 formal identity

```text
carrier_count = 18
residual_count = 3
nominal_config_count = 72
pair_key_count = 36
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
```

后续分析只读。

---

## TASK-009 正式主分析定义

Numerical settings：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

`FFT_MTF` 与代码字段 `fft_mtf_*` 仅为历史 hash 兼容命名。

Production acquisition：

```text
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
MFE MTFA / Grid=1 / Data Type=0 / Wave=1 / Field=1
frequency_scale_mode = paired_residual_free_MONO_EFFL
production sampling = 128
```

每 matched pair 在 residual-free MONO formal carrier nominal distance 读取一次 EFFL，并固定用于 MONO、EDOF、全部 defocus 和 sampling 的 cpd→cycles/mm 映射。EDOF-state EFFL 仅作诊断。

HOA：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

已退休的 `AS_FftMtf` 路径不作为 production、fallback 或 prerequisite。

---

## Corrected representative evidence

```text
run-code HEAD = d80b3a1c33fce02deda50f5ce8ebc73326e5b946
Windows offline = 198 passed / ruff / compileall / uv-lock PASS
evidence commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd
JSON SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49
CSV SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
local report SHA256 = fad2824a86ce946c56b269959ed3cf7d4a244fa068a96bd2a0d55d037563d2e8
```

128→256：

```text
WFS EPD3: peak 0.036%, TF mean 0.127%, shift 0 D, DOF50 Δ0.002 D -> PASS
RAD EPD5: peak 0.450%, TF mean 0.568%, shift 0 D, DOF50 Δ0.007 D -> PASS
HOA EPD5: peak 1.764%, TF mean 0.520%, shift 0 D, DOF50 Δ0.000044 D -> PASS
```

repeat128 三平台全部 PASS；6-config integration completed/failed=6/0；entity/ray-health PASS；20/40/60 cpd 的 production-vs-repeat MTFA 和 MTFA-vs-direction-average absolute differences 均为0。

因此旧 HOA 2.019% 仅属于被取代的 per-state-EFL 坐标；corrected gate 未改阈值即通过。256→512 escalation 不启动。

---

## Formal sampling lock

```text
docs/evidence/task009/TASK_009_PRODUCTION_SAMPLING_LOCK.json
lock_id = TASK009_PRODUCTION_SAMPLING_LOCK_v1
production_sampling_locked = true
production_sampling = 128
sampling_escalation_256_active = false
```

该 scientific/method lock 保持独立，不通过事后修改其科学字段来表示工程放行。

---

## Web provenance hardening

`RunEnvironment` 现在必须非空包含：

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

`run_analysis_batch()` 在 acquisition 前检查 backend 自报的 acquisition ID/hash/scale 与 RunEnvironment 完全一致。由此：

- 旧 acquisition backend 不能静默进入 Run72；
- per-state EFFL 不能静默取代 paired-MONO scale；
- provenance mismatch 在启动光学批次前 fail-closed。

Active `URD/ADD/MDD/TDD/RMD` 已全部同步到上述 production contract。

Web hardening CI source：

```text
source HEAD = a16e3e778dfda7f399056ef38dba93cc7a32e03c
GitHub Actions run = 32331070341
pytest = 199 passed
ruff = PASS
compileall = PASS
uv lock = PASS
```

---

## Run72 Web clearance

独立工程放行凭证：

```text
docs/evidence/task009/TASK_009_RUN72_WEB_CLEARANCE.json
clearance_id = TASK009_RUN72_WEB_CLEARANCE_v1
run72_authorized = true
run72_started = false
no_additional_representative_opticstudio_rerun_required = true
```

TASK-010 GUI smoke **不是 CLI Run72 的科学前置条件**。考虑本地 OpticStudio 时间成本，不应在 Run72 前再做一轮32–55分钟量级的代表性 optical validation。

---

## 下一阶段

下一次需要 Windows/OpticStudio 时，优先直接进入一个**单次大粒度 Run72 批次**，而不是新的 TASK-009 probe。

Run72 启动前只做廉价 preflight：

1. clean checkout / process count=0；
2. offline pytest/ruff/compileall/uv-lock；
3. frozen manifest 18/72/36 + exact hash；
4. sampling lock=128；
5. pair-MONO acquisition ID/hash/scale exact；
6. complete RunEnvironment；
7. backend provenance exact match。

正式目标：72 configs ×15 planes =1080 rows，36 matched deltas。单 config 失败只重跑失败项，使用新 run ID，不重跑已成功项。

---

## 当前 STOP

- 不修改 TASK-005–008 frozen assets；
- 不恢复 `AS_FftMtf` production path；
- 不使用 per-state EFFL 作为 matched-pair production scale；
- 不再次执行 TASK-009 representative validation；
- Run72 只有在其自身 preflight 不通过时才 STOP。
