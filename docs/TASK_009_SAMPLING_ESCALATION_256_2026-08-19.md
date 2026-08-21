# TASK-009 sampling escalation：128 → 256

日期：2026-08-19  
状态：**HOLD / not executable**；paired-MONO angular-scale correction 必须先完成真实验证

> 本文记录一次基于 v2 evidence 的 sampling escalation 决策。随后 Web review 发现 HOA EDOF 的 per-state EFFL=9.633 mm 导致异常的 cpd 轴缩放，因此该 sampling 决策在任何本地 256→512 执行前即被暂停。当前执行 authority 为 `TASK_009_PAIR_FIXED_ANGULAR_SCALE_2026-08-19.md`。本文保留作为 provenance，不是当前 handoff。

## 1. 原触发证据

TASK-009 `MTFA Grid=1` representative batch 已完成真实 OpticStudio 验证：

- MFE `MTFA Grid=1` acquisition 正常；
- 三平台 repeat128 全部 PASS；
- 6-config `ZosMtfaGridAnalysisBackend → run_analysis_batch` production integration PASS；
- entity invariants / ray-health / vignetting PASS；
- `MTFA = (MTFT+MTFS)/2` 的 20/40/60 cpd diagnostic 在三个 representative 中均为 exact match；
- 原始 per-state EFFL frequency scaling 下，HOA EPD5 的 sampling convergence 略超 gate。

HOA EPD5 原始结果：

```text
TF_MTFa_mean
64  = 0.04002456314848784
128 = 0.03506487023388816
256 = 0.03435697040199193

relative change 128→256 = 0.020188291791026776
frozen gate              = 0.020000000000000000
```

按该原始坐标定义，128 candidate 不可 post-hoc 视为通过。

## 2. 为什么暂停本 escalation

同一 evidence 显示 HOA EDOF：

```text
EFFL = 9.633329064114418 mm
mm/degree = 0.16815038428900272
60 cpd -> 356.82 cycles/mm
```

明显偏离其它 representative 的约 16.5–17.2 mm / 0.288–0.300 mm/deg。

由于 EFFL 是 paraxial first-order quantity，而 HOA residual 是中心高阶结构，Web 决定不能让 EDOF residual 自身重新定义 matched-pair 的 angular-frequency coordinate。

因此必须先采用 paired-MONO fixed angular scale 重跑 64/128/256 convergence。

## 3. 原拟议 256 candidate（暂不激活）

以下 settings identity 仅在 paired-MONO scale 下 128→256 仍失败后才允许重新激活：

```text
NOMINAL_MAIN_FFT_MTF_555_v3
SHA256 = dd58f5e40e218488e8ad22b8fc4fc9c4f054371ba9cf00953cabbdfbae7287f8

fft_mtf_sampling = 256
fft_mtf_convergence_samplings = (256, 512)
```

其它 scientific settings 与 gate 均不变。

## 4. 当前执行规则

当前不得执行 256→512 escalation。

先执行：

`docs/TASK_009_PAIR_FIXED_ANGULAR_SCALE_2026-08-19.md`

若 corrected paired-MONO scale 下三个 128→256 convergence 全 PASS，则保留 128，不启用本文 v3。

只有 corrected evidence 仍有任一 128→256 convergence FAIL，Web 才可重新激活本文并要求 256→512 validation。

## 5. 不变项

无论本文件是否重新激活，都不得改变：

- A0 / B0.20 / C0；
- 18 carrier locks；
- 3 residuals；
- TASK-008 72-config manifest identity/hash；
- convergence/repeatability thresholds；
- representative set；
- Run72 尚未启动。
