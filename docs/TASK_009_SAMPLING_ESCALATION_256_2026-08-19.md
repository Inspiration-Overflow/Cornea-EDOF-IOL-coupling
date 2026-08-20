# TASK-009 sampling escalation：128 → 256

日期：2026-08-19  
状态：Web decision frozen；local 256→512 validation pending

## 1. 触发证据

TASK-009 `MTFA Grid=1` representative batch 已完成真实 OpticStudio 验证：

- MFE `MTFA Grid=1` acquisition 正常；
- 三平台 repeat128 全部 PASS；
- 6-config `ZosMtfaGridAnalysisBackend → run_analysis_batch` production integration PASS；
- entity invariants / ray-health / vignetting PASS；
- `MTFA = (MTFT+MTFS)/2` 的 20/40/60 cpd diagnostic 在三个 representative 中均为 exact match；
- 唯一失败项为 HOA EPD5 的 sampling convergence。

HOA EPD5：

```text
TF_MTFa_mean
64  = 0.04002456314848784
128 = 0.03506487023388816
256 = 0.03435697040199193

relative change 128→256 = 0.020188291791026776
frozen gate              = 0.020000000000000000
```

因此 128 candidate 按预注册 gate **FAIL**。不得因只超 0.0001883 而 post-hoc 放宽 2% threshold。

同时趋势为单调收敛，且 HOA 的其它 128→256 gate 均通过：

- distance-peak MTFa relative = 0.01774635813552245；
- distance peak shift = 0 D；
- DOF50 width change = 0.026781428708645083 D。

WFS/RAD 的 128→256 convergence 全部 PASS。

## 2. 新 production candidate

将 production sampling candidate 从 128 升级为 **256**。

新增 numerical settings identity：

```text
NOMINAL_MAIN_FFT_MTF_555_v3
SHA256 = dd58f5e40e218488e8ad22b8fc4fc9c4f054371ba9cf00953cabbdfbae7287f8
```

与 v2 相比只改变：

```text
fft_mtf_sampling = 256
fft_mtf_convergence_samplings = (256, 512)
settings_id = NOMINAL_MAIN_FFT_MTF_555_v3
```

其它 scientific settings 全部不变：

- wavelength = 555 nm；
- EPD = 3 / 5 mm；
- field = 0；
- defocus = +0.50 → -3.00 D，step=-0.25 D；
- 0..60 cpd，step=1 cpd；
- MTFa / distance peak / DOF50 / TF_MTFa_mean 定义；
- fixed MTF10/20/30/40/50/60；
- polarization=false。

`TASK009_MFE_MTFA_GRID1_v1` acquisition contract 不变。

## 3. 256→512 convergence gate

不改变任何 threshold。

三个 frozen EDOF representatives 均比较 production 256 vs 512：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

每个必须同时满足：

```text
distance-peak MTFa relative change <= 2%
TF_MTFa_mean relative change       <= 2%
distance peak shift                <= 0.25 D
DOF50 width change                 <= 0.25 D
```

512 对应 MFE `Samp=5`，必须本地真实 header/readback 确认。

## 4. 256 repeatability gate

production candidate 改为 256 后，repeatability 也必须在 256 重新验证。

三个 EDOF representatives：

```text
same distance-peak grid sample
peak MTFa relative change <= 0.1%
TF_MTFa_mean relative change <= 0.1%
C4 delta <= 0.001 µm
C6 delta <= 0.001 µm
```

## 5. 最小但完整的新实机批次

不重复已经通过的 API/cross-check science work。

一次本地任务只需要：

### A. six-config production integration @256

三个 frozen pair 的 MONO+EDOF，共 6 configs，通过：

```text
ZosMtfaGridAnalysisBackend(sampling=256)
→ run_analysis_batch
```

该 integration 的三个 EDOF 结果同时作为 convergence 的 256 anchor。

### B. three EDOF @512

只跑三个 representative EDOF，sampling=512，用于 256→512 convergence。

### C. three independent repeat256

只跑三个 representative EDOF，独立 sampling=256，用于 production repeatability。

因此新批次共：

```text
6 × 15 planes @256 integration
+ 3 × 15 planes @512 convergence
+ 3 × 15 planes @256 repeatability
```

无需重跑：

- 64；
- 128；
- MTFA/MTFT/MTFS fixed-frequency semantic diagnostic；
- AS_FftMtf；
- TASK-007/008 calibration/locks。

既有 evidence commit `e508a83f41a63bc74a4a4ae1fc1bf060f0de4ea9` 保留为 v2 candidate failure + acquisition/production-chain validation provenance。

## 6. 决策规则

若三个 256→512 convergence 和三个 repeat256 全 PASS，且 six-config @256 integration PASS：

```text
production_sampling_candidate_passed = true
production_sampling_locked = false
```

随后 STOP，由 Web 读取 evidence 并创建 formal sampling lock。

若任一 256→512 convergence fail：

- 不放宽 gate；
- 不自动升到 512；
- STOP 返回 Web 重新评估 sampling strategy。

## 7. 不变项

本 sampling escalation 不改变：

- A0 / B0.20 / C0；
- 18 carrier locks；
- 3 residuals；
- TASK-008 72-config manifest identity/hash；
- acquisition contract `TASK009_MFE_MTFA_GRID1_v1`；
- convergence/repeatability thresholds；
- representative set；
- Run72 尚未启动。
