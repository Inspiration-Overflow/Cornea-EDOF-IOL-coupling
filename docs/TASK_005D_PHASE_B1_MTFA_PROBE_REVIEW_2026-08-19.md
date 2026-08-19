# TASK-005D Phase B.1 — MFE MTFA 实机 probe 复核与生产参数冻结

日期：2026-08-19  
状态：**PASS；B0 production `Samp=3`、frequency step=`5 cycles/mm` 已冻结。**

## 1. 目的

Phase B.0 在 `AS_HuygensMtf` settings-type 路径发生 Python.NET / `ZemaxEngine.dll` hard failure 后，B0 生产 MTF acquisition 已修订为：

```text
CORNEA_LOCK_B0_555_v2
MFE MTFA diffraction MTF
Grid = 0
Data Type = 0
Wave = 1
Field = 1
Q_lock frequency range = 0..50 cycles/mm
```

Phase B.1 只验证新的 MFE `MTFA` runtime/API 路径，并检查生产 sampling 与频率离散是否足够稳定；不改变 A/B/C 处方、REF_MONO、EPD、defocus grid、Q_lock 定义或 B0 排序规则。

## 2. 实机覆盖

实机 probe 使用：

```text
candidate = A0 + B0.20
EPD = 3 mm + 5 mm
defocus = 0 D / -1.5 D
Samp = 2 / 3 / 4
frequency step = 5 / 2.5 cycles/mm
```

实机运行代码基线：

```text
c40704cb002c3509f1e738628f8d513735853649
```

MFE `MTFA` operand 插入、一次 `CalculateMeritFunction()` 计算、数值读回、临时 operand 清理和 OBJECT thickness 恢复均成功；未出现残留正式 lock 或 production scan 结果。

## 3. 实测差异

probe 汇总的最大绝对 `Q_lock` 差异：

```text
Samp 2 → 3      0.00221683
Samp 3 → 4      0.00067564
5 → 2.5 cyc/mm  0.00492149
```

这些值是代表状态下的工程敏感性证据，不定义新的科学阈值，也不把一次 probe 扩张为通用 OpticStudio 收敛规律。

## 4. 冻结决定

基于上述实测：

```text
production Samp = 3
production frequency step = 5 cycles/mm
Q_lock maximum frequency = 50 cycles/mm
Grid = 0
Data Type = 0
```

理由：

- `Samp=3 → 4` 的最大 `Q_lock` 变化已经明显小于 `Samp=2 → 3`；
- 5 vs 2.5 cycles/mm 的频率离散差异较小，不足以支持为五候选 × 双瞳孔 × 17 plane 的生产扫描增加一倍频率点；
- 本项目 B0 目标是稳定比较候选的 distance retention、absolute-threshold DOF 和排序，不追求对候选选择没有实质影响的极端数值精度。

因此不增加 `Samp=5`、更细频率网格或额外全候选 convergence study。

## 5. `passed` 语义修订

旧版 probe JSON 使用：

```text
passed = true
```

该字段实际只表示“计划的 MTFA acquisition 成功完成并产生有限结果”，并不代表脚本内部存在一个自动数值收敛阈值。

从本次一致性修订开始，新 probe 输出改为：

```text
runtime_passed = true
passed_semantics = runtime acquisition completed successfully; not an automatic convergence-threshold decision
requires_production_freeze_review = true
```

为保留既有实机证据，full-scan gate 允许读取旧 JSON 的 `passed=true`，但仅把它解释为 `runtime_passed` 的兼容别名；生产参数冻结以本文的人工工程复核决定为准。

**无需重跑 Phase B.1。** 本次修订没有改变已经实机验证过的 MFE MTFA primitive、Q_lock 数学或 probe 光学条件。

## 6. Full-scan 前置 gate

正式五候选 B0 scan 现在必须先找到：

```text
project_mvp_2026_v2_zmx/
  diagnostics/task005d/b0_mtfa_probe/TASK_005D_MTFA_PROBE.json
```

并验证：

- runtime acquisition 成功；
- settings 与当前 `CORNEA_LOCK_B0_555_v2` 完全一致；
- 存在 `Samp=2/3/4` 证据；
- 存在 `5 vs 2.5 cycles/mm` 证据；
- 三项汇总差异均为有限非负值。

该 gate **不重新发明自动 convergence threshold**；它只防止未来在没有 Phase B.1 证据、或 settings 已漂移的情况下误跑完整扫描。

## 7. 下一步

当前允许执行：

```text
scripts/run_task_005d_b0_scan.py
```

生产设置固定为：

```text
CORNEA_LOCK_B0_555_v2
Samp = 3
frequency step = 5 cycles/mm
```

完整 scan 只生成尚未经过 morphology review 的五候选曲线和初步 deterministic recommendation：

```text
morphology_review_pending = true
selection_locked = false
```

五候选曲线生成后，再使用纯 Python morphology review / rerank / lock 路径；该步骤不重新调用 OpticStudio。
