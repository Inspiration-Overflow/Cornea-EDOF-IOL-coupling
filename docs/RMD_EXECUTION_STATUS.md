# RMD 执行状态

> `RMD-0001 v1.6` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门。
>
> TASK-009 acquisition 的当前最高优先级说明为：
> `TASK_009_MTFA_GRID1_ACQUISITION_DECISION_2026-08-19.md`。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`feat/task-009-fft-mtf-main`
- TASK-005/006/007/008：完成并冻结
- TDD-999：cleared
- Run72：**未启动**

## TASK-008 formal identity

```text
carrier_count = 18
residual_count = 3
nominal_config_count = 72
pair_key_count = 36

manifest_hash =
29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49

lock_set_hash =
b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
```

TASK-009 对这些 formal assets 只读。

---

## TASK-009 数值主设置

继续冻结：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

保持：555 nm、EPD3/5、field0、+0.50→−3.00 D、−0.25 D step、15 planes、64/128/256 convergence、128 candidate、0..60 cpd、1-cpd grid、MTFa、distance peak、DOF50、TF_MTFa_mean。

HOA readback：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

---

## 已完成：review-hardening

Web 已完成：

- strict TASK-008 manifest reload；
- real `AnalysisBackend` / `run_analysis_batch()` production contract；
- entity fingerprint before/after；
- exact settings/hash provenance；
- footprint/ray-health contract；
- representative 6-config manifest identity；
- active-source/spec regression checks。

本地第一轮 review-hardened TASK-009：

```text
initial HEAD = f5fa57baf55562c7cf7819e9d6ba21461be278a8
actual run-code HEAD = 57c18627bbea939bdd56cc88474a633d328e15d1
offline = 193 passed / ruff PASS / compileall PASS / uv-lock PASS
strict manifest reload = PASS
```

机械修复：

- `ce0b3ab` — stale settings / stale DOF call / fixture type / lint；
- `57c1862` — `OpticStudioVersion` property。

---

## 第一轮真实 TASK-009 STOP

在第一个 representative config 开始前，创建：

```text
ZemaxUI.ZOSAPI.Analysis.Mtf.AS_FftMtf
```

触发：

```text
FileLoadException
A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

结果：

- 没有取得 FFT MTF numerical data；
- convergence 未执行；
- repeatability 未执行；
- 6-config integration 未执行；
- evidence 未生成；
- Run72 未启动；
- OpticStudio 最终 process count=0。

该故障属于当前工作站 Python.NET/ZemaxEngine 对部分 `AS_*` Analysis settings 类型的原生加载问题，不解释为科学模型失败。

---

## Web acquisition 决策

`AS_FftMtf` production path 已退休，不作为 fallback 或 prerequisite。

新的 acquisition contract：

```text
TASK009_MFE_MTFA_GRID1_v1
SHA256 = 5986a768779fc5be4798b3c9c608babbe46cc311d9e4928d7782879a95c9fd0b
```

正式 acquisition：

```text
MFE MTFA
Grid=1
Data Type=0
Wave=1
Field=1
```

frequency path：

```text
nominal EFL
→ mm/degree = EFL*tan(1°)
→ 0..60 cpd directly mapped to 61 cycles/mm targets
→ MTFA Grid=1 direct acquisition at every defocus plane
→ MTFa / fixed-frequency MTF
```

不再需要 FFT MTF Analysis native curve，也不需要 frequency interpolation。

新的 real backend：

```text
ZosMtfaGridAnalysisBackend
```

新的本地入口：

```text
scripts/run_task_009_mtfa_grid1_representative.py
```

---

## 下一本地 TASK-009 gate

一次完成：

1. full offline pytest/ruff/compileall/uv-lock；
2. strict TASK-008 18/72/36 + hash preflight；
3. MFE `MTFA/MTFS/MTFT` Grid=1 header/API readback；
4. 3 EDOF × 64/128/256 convergence；
5. 3 EDOF × repeat128；
6. 6 frozen configs 通过 `ZosMtfaGridAnalysisBackend → run_analysis_batch()`；
7. EFFL / HOA / entity / footprint / ray-health；
8. 20/40/60 cpd：`MTFA` vs `(MTFT+MTFS)/2` diagnostic；
9. sanitized GitHub evidence；
10. final offline regression。

代表 pair 不变：

```text
LB_AL2395 × A0 × WFS × EPD3
ATC_M3_AL24477 × B0 × RAD × EPD5
ATC_M3_AL24477 × C0 × HOA × EPD5
```

Local evidence 即使全部 PASS，也只能：

```text
evidence_only = true
formal_artifact = false
production_sampling_candidate_passed = <computed>
production_sampling_locked = false
run72_started = false
```

---

## 当前 STOP

在新的 MTFA Grid=1 representative evidence 经 Web review 前：

- 不写 formal sampling lock；
- 不启动 Run72；
- 不进入 TASK-010；
- 不改 TASK-005–008 frozen assets；
- 不恢复 `AS_FftMtf` production path；
- 不自行更改 scientific settings 或 convergence/repeatability gate。
