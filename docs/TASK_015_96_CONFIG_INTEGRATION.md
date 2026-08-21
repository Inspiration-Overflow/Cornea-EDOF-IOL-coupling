# TASK-015：96-config 扩展层离线整合

## 目的

将已经分别通过 Web 科学审核的两组结构化证据合并为一个统一扩展层：

- TASK-013：N0，24 configs；
- TASK-014：A0V12 / B0V12 / C0V12，72 configs。

总计：

```text
2 Base × 4 Cornea × 3 Platform × MONO/EDOF × EPD3/5 = 96 configs
48 matched pairs
1440 through-focus rows
```

本任务纯离线，不调用 OpticStudio，不改变任何冻结光学设置。

## 分析定义

保留 TASK-012 的 8 个 pair outcomes：

- ΔDOF50；
- Δdistance-peak MTFa；
- ΔMTFa@0D；
- Δthrough-focus MTFa mean；
- ΔC4^0；
- ΔC6^0；
- ΔHOA RMS；
- ΔF residual。

其中 `Δ = EDOF − MONO`。

新增且仅新增一个面向研究问题的 interaction：

```text
postop-minus-N0 interaction
= (EDOF − MONO)_postop − (EDOF − MONO)_N0
```

在同一 Base × Platform × Pupil 内比较 A0V12/B0V12/C0V12 与 N0，从而描述术后角膜背景如何改变同一 EDOF 机制的效应。

## Censoring

继续使用冻结窗口，不扩窗重算。

- exact DOF50：按精确值；
- EDOF far-censored：`EDOF−MONO` 作为 lower bound；
- N0-referenced DOF50 interaction 按区间算术传播 censoring；
- distance peak 位于搜索边界时只标记 censored，不把边界值解释为真实精确峰值。

## 输出

```text
docs/evidence/task015/
  TASK_015_PAIR_ANALYSIS.csv
  TASK_015_COUPLING_MATRIX.csv
  TASK_015_ANALYSIS_EVIDENCE.json
```

288 个 N0-referenced interactions 由分析代码在内存中确定性重建并受单元测试约束，不另存一份冗余明细 CSV。TASK-013/014 的原始 96 config rows 与 1440 TF rows 同样保持各自原 evidence 为单一来源。

## STOP

立即停止，如果：

1. TASK-013 或 TASK-014 scientific review 不再是 `PASS_WITH_SCIENTIFIC_CAVEATS`；
2. 任一接受源文件 Git blob identity 漂移；
3. config / TF / pair 数量不再为 24+72 / 360+1080 / 12+36；
4. 15-plane defocus grid、0D MTFa 或 TF mean 无法从原始 TF rows 重建；
5. formal paired deltas 无法从 MONO/EDOF config 重建；
6. 需要新 OpticStudio acquisition 或改变冻结窗口才能继续。
