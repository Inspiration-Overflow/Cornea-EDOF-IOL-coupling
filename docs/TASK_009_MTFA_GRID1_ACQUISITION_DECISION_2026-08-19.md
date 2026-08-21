# TASK-009 acquisition override：MFE MTFA Grid=1

日期：2026-08-19  
状态：Web decision implemented；local OpticStudio validation pending

## 1. Authority

本文只覆盖 TASK-009 / Run72 的**衍射 MTF 获取接口**。

在该事项上，本文优先于：

- `TASK_009_FFT_MTF_MAIN_ANALYSIS_FREEZE_2026-08-19.md` 中要求 `New_FftMtf()` / `AS_FftMtf` 的部分；
- 当前 URD/ADD/MDD/TDD/RMD 中把 OpticStudio FFT MTF Analysis .NET analysis object 写成唯一 production API 的部分。

本文不改变 TASK-005–008 任何科学资产或正式 hash。

待本 acquisition override 完成真实 OpticStudio validation 后，再统一修订 active URD/ADD/MDD/TDD/RMD，避免在 API 可用性尚未确认时再次大范围改写规范。

---

## 2. 触发原因

TASK-009 首次真实运行在创建：

```text
ZemaxUI.ZOSAPI.Analysis.Mtf.AS_FftMtf
```

时触发 Python.NET / ZemaxEngine 原生类型加载失败：

```text
FileLoadException:
A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

该故障发生在任何代表配置 MTF 数值取得之前。

同一工作站历史上已经在其他 `AS_*` analysis settings 类型出现同类加载故障，因此本项目不再把 `AS_FftMtf` 作为 production、fallback 或 validation prerequisite。

---

## 3. 科学方法不变

主研究仍然使用 OpticStudio **衍射 modulation MTF**，不引入 Huygens、PSF 反算、complex OTF 或视觉加权传递函数。

OpticStudio 官方 MTF operand 定义中：

- `MTFA` = sagittal 与 tangential diffraction modulation MTF 的平均值；
- `MTFS` = sagittal diffraction modulation MTF；
- `MTFT` = tangential diffraction modulation MTF；
- `Grid=0` 使用快速 sparse-sampling 算法；
- `Grid=1` 选择 MTF analysis feature 使用的 grid-based algorithm；
- `Data Type=0` 返回 modulation amplitude。

因此 TASK-009 production acquisition 改为：

```text
MFE MTFA
Grid = 1
Data Type = 0
Wave = 1
Field = 1
```

该修改是 ZOS-API acquisition interface 的替换，不是 cornea/carrier/residual 或主 metric 的重新定义。

---

## 4. 数值 main settings 保持不变

继续使用：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

保持：

- wavelength = 555 nm；
- EPD = 3 / 5 mm；
- field = 0；
- retina-anchored defocus = +0.50 → -3.00 D；
- step = -0.25 D；
- 15 planes；
- convergence sampling grid sizes = 64 / 128 / 256；
- production candidate = 128；
- 0..60 cpd；
- 1-cpd common grid；
- reported MTF = 10/20/30/40/50/60 cpd；
- MTFa、distance peak、DOF50、TF_MTFa_mean 定义不变。

这里 settings ID 保持 v2，因为**没有数值 scientific setting 改变**。获取接口另行版本化。

---

## 5. Acquisition contract

新增：

```text
TASK009_MFE_MTFA_GRID1_v1
SHA256 = 5986a768779fc5be4798b3c9c608babbe46cc311d9e4928d7782879a95c9fd0b
```

内容：

```text
production_operand = MTFA
grid = 1
data_type = 0
wave = 1
field = 1
frequency_axis = direct_0_to_60_cpd_via_nominal_EFL
```

Sampling grid size 到 MFE `Samp` index：

```text
64  -> 2
128 -> 3
256 -> 4
```

该 mapping 必须在本地实际 operand header/readback 中记录。

---

## 6. Frequency acquisition

不再让 FFT MTF Analysis 先生成 native curve 再插值。

对每个 config：

1. 在 nominal object state 读取真实 EFL；
2. 计算：

```text
mm_per_degree = EFL_mm * tan(1 degree)
```

3. 对固定 0..60 cpd、1-cpd grid，直接转换为所需 cycles/mm：

```text
f_cyc_per_mm = f_cpd / mm_per_degree
```

4. 在每个 retina-anchored defocus plane，用 `MTFA Grid=1` 直接请求这 61 个 spatial frequencies；
5. 对 61 个 MTF average 值直接积分 MTFa。

因此新 production path 不需要 frequency interpolation，也不存在超过 native analysis curve support 后外推的问题。

---

## 7. Through-focus 实体约束不变

唯一允许临时改变的是 OBJECT thickness，用于产生冻结的 retina-anchored vergence。

每个 config 仍必须验证：

- formal carrier/residual SHA；
- model hash before/after；
- in-memory entity fingerprint before/after；
- retina unchanged；
- IOL position / ELP unchanged；
- carrier P/R/Q unchanged；
- object thickness restored；
- footprint/ray-health；
- required artifacts complete。

---

## 8. Sampling convergence / repeatability 不变

三个 EDOF representative：

```text
LB+A0+WFS+EPD3
ATC+B0+RAD+EPD5
ATC+C0+HOA+EPD5
```

64/128/256 比较。

128→256 gate 不变：

- distance-peak MTFa relative <=2%；
- TF_MTFa_mean relative <=2%；
- distance peak shift <=0.25 D；
- DOF50 width change <=0.25 D。

repeat128 gate 不变：

- same distance-peak grid sample；
- peak MTFa relative <=0.1%；
- TF_MTFa_mean relative <=0.1%；
- C4/C6 <=0.001 µm。

---

## 9. Independent consistency diagnostic

原“FFT MTF Analysis vs MFE MTFA” cross-check 因 Analysis API 被退休而取消。

新的固定频率诊断在 representative EDOF、0 D、20/40/60 cpd 上记录：

```text
production MTFA Grid=1
repeat MTFA Grid=1
MTFT Grid=1
MTFS Grid=1
(MTFT + MTFS)/2
```

记录：

```text
|production MTFA - repeat MTFA|
|MTFA - (MTFT+MTFS)/2|
```

该诊断用于确认 repeatability、operand semantics、方向平均和 frequency mapping；不新增 scientific acceptance threshold，继续交 Web review。

---

## 10. Production code boundary

新的 production backend：

```text
ZosMtfaGridAnalysisBackend
```

正式链：

```text
frozen TASK-008 manifest
→ formal MONO/EDOF model
→ MFE EFFL
→ MFE MTFA Grid=1 through-focus
→ MFE ZERN whole-eye HOA
→ footprint/ray-health
→ ConfigResult
→ run_analysis_batch
→ ProjectStore provenance
→ matched deltas
```

`AS_FftMtf` / `New_FftMtf()` production path 已从 active TASK-009 source 删除。

---

## 11. Local evidence state

本轮 local evidence 即使全部通过，也只能：

```text
evidence_only = true
formal_artifact = false
production_sampling_candidate_passed = <computed>
production_sampling_locked = false
run72_started = false
```

Web review 后才允许 sampling formal lock 和 Run72。

---

## 12. 不变项

本 override 不改变：

- A0 / B0.20 / C0；
- 18 carrier locks；
- 3 residual payloads / validation；
- 72-config manifest；
- TASK-008 manifest hash；
- TASK-008 lock-set hash；
- TDD-999 cleared state；
- main analysis numerical settings/hash；
- representative set；
- convergence/repeatability gates；
- Run72 尚未启动。
