# RMD 执行状态

> `RMD-0001 v1.6` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门。
>
> TASK-009 acquisition / angular-frequency / sampling 的当前最高优先级说明为：
> `TASK_009_PRODUCTION_SAMPLING_LOCK_2026-08-19.md`。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`feat/task-009-fft-mtf-main`
- TASK-005/006/007/008：完成并冻结
- TDD-999：cleared
- TASK-009 corrected representative optical gate：**PASS**
- production sampling：**128，Web 正式锁定**
- Run72：**未启动、未授权**

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

TASK-009/Run72 对这些 formal assets 只读。

---

## TASK-009 正式主分析定义

主数值 settings identity 保持：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

`FFT_MTF` 仅为历史兼容命名，不表示恢复 `AS_FftMtf` Analysis。

正式 acquisition：

```text
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

MFE MTFA
Grid = 1
Data Type = 0
Wave = 1
Field = 1
```

正式 angular-frequency scale：

```text
paired_residual_free_MONO_EFFL
```

每个 matched pair 先在 residual-free MONO formal carrier 上测一次 nominal-distance EFFL；该 EFL 固定用于该 pair 的 MONO、EDOF、所有 defocus plane 与所有 sampling 的 cpd→cycles/mm 映射。EDOF state EFFL 只作诊断。

HOA readback：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

---

## `AS_FftMtf` 路径状态

早期 `AS_FftMtf` Analysis 在当前工作站触发 Python.NET/ZemaxEngine 原生 `FileLoadException`。该路径已经退休：

- 不作为 production path；
- 不作为 fallback；
- 不作为 Run72 prerequisite；
- 不把该工作站加载问题解释为科学模型失败。

旧 per-state-EFL MTFA Grid1 evidence 也不再用于 sampling acceptance，因为它允许 EDOF residual 改变评价自身的角频率坐标。

---

## Corrected pair-MONO-scale 真实复验

### 代码与离线门禁

```text
run-code HEAD = d80b3a1c33fce02deda50f5ce8ebc73326e5b946
Windows offline = 198 passed / ruff PASS / compileall PASS / uv-lock PASS
local code modification = none
GitHub Actions = PASS
```

### Evidence

```text
evidence commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd

docs/evidence/task009/TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE_EVIDENCE.json
SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49

docs/evidence/task009/TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE_THROUGH_FOCUS.csv
SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
rows = 90 = 6 x 15

local report SHA256 =
fad2824a86ce946c56b269959ed3cf7d4a244fa068a96bd2a0d55d037563d2e8
```

### Angular-scale readback

```text
WFS EPD3:
  MONO ref EFL = 16.502920718221272 mm
  pair mm/deg = 0.2880595526417795
  EDOF diagnostic EFL = 16.50658554155713 mm
  60 cpd = 208.2902630714484 cycles/mm

RAD EPD5:
  MONO ref EFL = 16.991651983952405 mm
  pair mm/deg = 0.29659038861756637
  EDOF diagnostic EFL = 17.197218726256647 mm
  60 cpd = 202.2992055800096 cycles/mm

HOA EPD5:
  MONO ref EFL = 17.155135985882993 mm
  pair mm/deg = 0.2994440124859896
  EDOF diagnostic EFL = 9.633329064114418 mm
  60 cpd = 200.37134655616893 cycles/mm
```

HOA 的 EDOF diagnostic EFL 不参与 cpd 轴。

### Sampling convergence

预注册 128→256 gate 保持不变：peak MTFa≤2%、TF mean≤2%、peak shift≤0.25 D、DOF50 width change≤0.25 D。

```text
WFS EPD3: peak 0.036%, TF mean 0.127%, shift 0 D, DOF50 Δ0.002 D -> PASS
RAD EPD5: peak 0.450%, TF mean 0.568%, shift 0 D, DOF50 Δ0.007 D -> PASS
HOA EPD5: peak 1.764%, TF mean 0.520%, shift 0 D, DOF50 Δ0.000044 D -> PASS
```

旧 HOA TF-mean 2.019% 属于已被取代的 per-state-EFL 坐标；修正坐标后为 0.520%，没有更改 2% gate。

### Repeatability

三个 EDOF representative 的独立 repeat128：

```text
peak MTFa relative = 0
TF mean relative = 0
C4 delta = 0 um
C6 delta = 0 um
same peak sample = true
```

全部 PASS。

### 6-config production integration

```text
completed = 6
failed = 0
run_id = analysis-d94299c0575e451484f3a655b346d0e8
environment_ref = environments/analysis-d94299c0575e451484f3a655b346d0e8.json
```

entity fingerprint、model hash、retina、IOL/ELP 全部保持；无 unintended vignetting / ray-health failure。

### Fixed-frequency Web review

三个 EDOF representative 在 0 D、20/40/60 cpd：

```text
production MTFA == independent repeat MTFA
MTFA == (MTFT + MTFS) / 2
```

三平台两组 absolute differences 均逐点为 0.0。Web 接受该 diagnostic，不新增事后数值阈值。

---

## 正式 sampling lock

Web 独立审核后正式决定：

```text
production_sampling = 128
production_sampling_locked = true
sampling_escalation_256_active = false
```

正式机器可读 lock：

```text
docs/evidence/task009/TASK_009_PRODUCTION_SAMPLING_LOCK.json
```

决策说明：

```text
docs/TASK_009_PRODUCTION_SAMPLING_LOCK_2026-08-19.md
```

不执行 256→512 escalation，因为 corrected 128→256 已全部满足预注册 gate。

---

## 当前无需更多 ZCode sampling 工作

TASK-009 representative OpticStudio evidence 已足够支持 sampling lock。因此：

- 不再重复 representative optics；
- 不执行 256→512；
- 不要求本地修正文档/provenance；
- 不启动 Run72。

---

## Run72 前剩余 Web-only gate

还有两项工程/规范收口必须在 Web 端完成：

1. **Run-level acquisition provenance**：`RunEnvironment` 或等价 run-level provenance 必须显式绑定：
   - acquisition contract ID；
   - acquisition contract SHA256；
   - `paired_residual_free_MONO_EFFL` frequency-scale mode。

2. **active normative-document consolidation**：将 URD/ADD/MDD/TDD/RMD 中遗留的旧 `FFT MTF Analysis`、per-state EFL、`ZosFftMtfAnalysisBackend` 描述统一修正为当前正式 MTFA Grid1 pair-MONO contract，并用单元测试防回归。

完成以上 Web-only gate 并再次通过 GitHub Actions 后，才判断 TASK-009 fully complete，并进入 TASK-010 / TASK-011。

---

## 当前 STOP

在上述 Web-only gate 完成前：

- `run72_authorized = false`；
- 不启动 Run72；
- 不恢复 `AS_FftMtf` production path；
- 不修改 TASK-005–008 frozen assets；
- 不让 ZCode承担普通 Python、文档或 provenance 修订。
