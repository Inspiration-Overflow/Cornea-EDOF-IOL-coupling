# TASK-009 正式生产采样锁与 Web 独立审核

## 1. 决策

TASK-009 的正式生产采样锁定为：

```text
production sampling = 128
production_sampling_locked = true
sampling_escalation_256_active = false
```

本决策由 Web 端在读取并独立审核真实 OpticStudio evidence 后作出；不要求再次运行 OpticStudio。

本文件是 TASK-009 主分析 acquisition / angular-frequency / sampling 的当前最高优先级规范。若 `URD.md`、`ADD.md`、`MDD.md`、`TDD.md`、`RMD.md` 中仍保留更早的 `FFT MTF Analysis`、per-state EFL 或 `ZosFftMtfAnalysisBackend` 描述，这些旧描述仅保留历史上下文，在 TASK-009 主分析语义上由本文件、`TASK_009_MTFA_GRID1_ACQUISITION_DECISION_2026-08-19.md` 与 `TASK_009_PAIR_FIXED_ANGULAR_SCALE_2026-08-19.md` 共同取代。后续规范整合不得改变本锁的科学含义，除非产生新的版本化科学决策。

## 2. 正式 acquisition contract

生产 MTF acquisition 固定为：

```text
contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
operand = MFE MTFA
Grid = 1
Data Type = 0
Wave = 1
Field = 1
```

主数值 settings 继续使用既有冻结 identity：

```text
settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
wavelength = 555 nm
EPD = 3 / 5 mm
defocus = +0.50 -> -3.00 D
step = -0.25 D
planes = 15
convergence samplings = 64 / 128 / 256
MTF grid = 0..60 cpd, 1 cpd step
fixed outputs = 10/20/30/40/50/60 cpd
```

`NOMINAL_MAIN_FFT_MTF_555_v2` 中的 `FFT_MTF` 是历史兼容命名；它不再表示调用 OpticStudio `AS_FftMtf` Analysis。

## 3. 角频率坐标

每一个 matched MONO/EDOF pair 只定义一次角频率比例尺：

1. 加载冻结的 residual-free MONO formal carrier；
2. 在 nominal distance 条件测量 MONO EFFL；
3. 定义

\[
mm/degree_{pair}=EFFL_{MONO,pair}\tan(1^\circ)
\]

4. 对该 pair 的 MONO、EDOF、所有 defocus plane、所有 sampling 统一使用：

\[
f_{cyc/mm}=f_{cpd}/mm/degree_{pair}
\]

EDOF state 自身 EFFL 只作诊断，禁止重新定义被评价的 cpd 轴。

正式 frequency-scale mode：

```text
paired_residual_free_MONO_EFFL
```

## 4. 审核 evidence

真实复验代码提交：

```text
d80b3a1c33fce02deda50f5ce8ebc73326e5b946
```

结构化 evidence 提交：

```text
47f901dad36fb9d407826a6da8baceeef4c2edfd
```

Evidence：

```text
docs/evidence/task009/TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE_EVIDENCE.json
SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49

docs/evidence/task009/TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE_THROUGH_FOCUS.csv
SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
rows = 90 = 6 configs x 15 planes
```

本地报告：

```text
SHA256 = fad2824a86ce946c56b269959ed3cf7d4a244fa068a96bd2a0d55d037563d2e8
```

Evidence 明确保持：

```text
evidence_only = true
formal_artifact = false
run72_started = false
```

这里的 `formal_artifact=false` 只描述本地实验 evidence 本身；正式 sampling lock 由 Web 端另行写入 `TASK_009_PRODUCTION_SAMPLING_LOCK.json`。

## 5. 三个代表 pair 的角尺度审核

### WFS / LB+A0 / EPD3

```text
MONO reference EFL = 16.502920718221272 mm
pair mm/degree = 0.2880595526417795
EDOF diagnostic EFL = 16.50658554155713 mm
EDOF/reference ratio = 1.0002220711956649
60 cpd target = 208.2902630714484 cycles/mm
```

### RAD / ATC+B0 / EPD5

```text
MONO reference EFL = 16.991651983952405 mm
pair mm/degree = 0.29659038861756637
EDOF diagnostic EFL = 17.197218726256647 mm
EDOF/reference ratio = 1.0120981022032693
60 cpd target = 202.2992055800096 cycles/mm
```

### HOA / ATC+C0 / EPD5

```text
MONO reference EFL = 17.155135985882993 mm
pair mm/degree = 0.2994440124859896
EDOF diagnostic EFL = 9.633329064114418 mm
EDOF/reference ratio = 0.5615419820654124
60 cpd target = 200.37134655616893 cycles/mm
```

HOA 的异常 EDOF diagnostic EFL 不用于空间频率换算。旧 per-state-EFL 计算把 60 cpd 映射到约 356.8 cycles/mm，并导致一个不具有同一角频率基准的收敛比较；该旧数值不再具有 production acceptance 权威性。

## 6. Sampling convergence 审核

预注册 128->256 gate：

```text
distance-peak MTFa relative <= 2%
TF_MTFa_mean relative <= 2%
distance peak shift <= 0.25 D
DOF50 width change <= 0.25 D
```

修正 pair-MONO scale 后：

| Representative | Peak MTFa rel | TF mean rel | Peak shift | DOF50 width change | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| WFS EPD3 | 0.036% | 0.127% | 0.0 D | 0.002 D | PASS |
| RAD EPD5 | 0.450% | 0.568% | 0.0 D | 0.007 D | PASS |
| HOA EPD5 | 1.764% | 0.520% | 0.0 D | 0.000044 D | PASS |

因此三个代表 configuration 均通过预注册的 128->256 数值 gate。

旧 HOA TF-mean 2.019% 结果属于已被取代的 per-state-EFL frequency-axis 定义；在正确的 matched-pair 固定角尺度下为 0.520%。这不是放宽阈值，也没有修改 2% gate。

## 7. Repeatability 与生产集成

三个 EDOF representative 的独立 repeat128：

```text
peak MTFa relative change = 0
TF mean relative change = 0
C4 delta = 0 um
C6 delta = 0 um
same peak sample = true
```

全部通过既有 repeatability gate。

6-config production integration：

```text
completed = 6
failed = 0
run_id = analysis-d94299c0575e451484f3a655b346d0e8
environment_ref = environments/analysis-d94299c0575e451484f3a655b346d0e8.json
```

entity fingerprint、working-model hash、retina、IOL/ELP 均保持不变；无 unintended vignetting / ray-health failure。

## 8. Independent fixed-frequency diagnostic

三个 EDOF representative 在 0 D、20/40/60 cpd 上：

```text
production MTFA == independent repeat MTFA
MTFA == (MTFT + MTFS) / 2
```

三平台两组 absolute differences 均逐点为 0.0。

该检查原先只规定“保存差异，由 Web 审核，不新增数值 threshold”。Web 审核接受该 diagnostic，认为 operand/header/direction/frequency mapping 与 production MTFA acquisition 一致；不新增事后阈值。

## 9. 正式 sampling 决策

128 已满足：

- corrected 128->256 convergence；
- independent repeatability；
- 6-config real production integration；
- entity/ray-health invariants；
- fixed-frequency independent diagnostic；
- Windows 与 GitHub Actions 离线质量门禁。

因此：

```text
production_sampling = 128
production_sampling_locked = true
```

不启动 256->512 escalation。只有未来出现新的、版本化且预先说明的科学/实现证据证明 128 不再满足正式要求时，才允许新建 superseding sampling lock；不得静默修改本锁。

## 10. Run72 前置要求

本锁解除“sampling 未锁”这一 STOP，但**不自动启动 Run72**。正式 Run72 仍必须：

1. 从 TASK-008 frozen 72-config manifest 读取身份；
2. 使用 `ZosMtfaPairScaleAnalysisBackend`（或与其严格等价、经版本化 review 的 production wrapper）；
3. 每个 matched pair 先取得 residual-free MONO reference EFL，并固定该 pair 的 cpd scale；
4. `RunEnvironment` / run-level provenance 必须显式记录 acquisition contract ID/hash 与 `paired_residual_free_MONO_EFFL` frequency-scale mode；
5. 保留 main settings hash、HOA settings ID/hash、manifest hash、lock-set hash；
6. 不允许恢复 `AS_FftMtf` production path；
7. 不修改 TASK-005--008 scientific assets；
8. Run72 正式启动前完成 active URD/ADD/MDD/TDD/RMD 的 consolidation，消除其中遗留的旧 acquisition 描述。

第 4 与第 8 项属于 Web 端实现/规范追溯工作，不要求重复 OpticStudio representative 测量。
