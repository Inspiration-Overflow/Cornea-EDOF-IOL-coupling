# TASK-005D Phase B 实机 STOP

日期：2026-08-19  
分支：`feat/task-005d-cornea-lock-assets`  
实机 HEAD：`5883dee40096909a4290361b5a39a14602e8f8d9`

> 本文是 Phase B.0 的历史 STOP 证据。后续恢复路径已经完成 Phase B.1 实机验证；当前状态以 `TASK_005D_PHASE_B1_MTFA_PROBE_REVIEW_2026-08-19.md` 和 `RMD_EXECUTION_STATUS.md` 为准。

## 结论

Phase B 在 A0 的候选特异 `REF_MONO_CORNEA_LOCK` 已成功构建之后，首次创建 Huygens MTF 分析 settings 类型时触发 Python.NET / ZemaxEngine 原生硬错误，因此本次扫描按 STOP 规则失败。

该失败属于 **ZOS-API runtime/settings 类型加载路径**，不是 A/B 角膜、REF_MONO 光学求解或 B0 排序逻辑失败。

## 已完成到的位置

本次运行已成功生成诊断产物：

```text
project_mvp_2026_v2_zmx/diagnostics/task005d/b0_scan/REF_MONO_A0.zmx
project_mvp_2026_v2_zmx/diagnostics/task005d/b0_scan/REF_MONO_A0.ZDA
```

随后在 A0 首次 Huygens MTF 分析创建阶段失败，未生成：

```text
TASK_006_B0_REAL_SCAN.json
```

因此：

```text
formal_artifact = false
selection_locked = false
recommendation_id = none
```

没有创建任何正式 lock，artifact index 未改变。

## 原生错误

核心异常：

```text
Python.Runtime.InternalPythonnetException:
Failed to create Python type for ZemaxUI.ZOSAPI.Analysis.Mtf.AS_HuygensMtf
 ---> Python.Runtime.InternalPythonnetException:
 Failed to create Python type for ZemaxUI.ZOSAPI.Analysis.AS_Base
 ---> System.IO.FileLoadException:
 A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

该错误类别与 TASK-005C 曾遇到的 `AS_ZernikeStandardCoefficients` settings type 失败相同。

进程最终退出后：

```text
residual OpticStudio/Zemax process count = 0
```

退出阶段另有已知：

```text
*** FRU__delta_init(): Attempt to start when running!
```

但本次存在明确 `FileLoadException / ZemaxEngine.dll`，因此必须判为 hard failure，而不是可忽略 exit warning。

## 不变的科学约束

不得反复重试 `AS_HuygensMtf` 路径，也不得因此改变：

- A0/B 候选科学处方；
- 17-plane B0 defocus grid；
- EPD3/EPD5；
- `Q_lock=(1/50)∫_0^50 MTF(f)df`；
- B0 distance-retention gates；
- `rank_b0_candidates()` 排序规则。

后续只允许替换 **B0 MTF acquisition primitive**。

## 后续方案更新

STOP 后曾短暂实现 `Huygens PSF → Python FFT → MTF` 作为 TASK-005D 的备选恢复路线。经后续设计复核，该中间方案已被废弃，相关 TASK-005D 专用 fallback 代码已从 PR 中删除。

正式恢复方案为：

```text
CORNEA_LOCK_B0_555_v2
MFE MTFA diffraction MTF
Samp = 3
Grid = 0
Data Type = 0
Wave = 1
Field = 1
frequency = 0..50 cycles/mm
production step = 5 cycles/mm
```

该修订不改变眼模型 scientific baseline，也不改变 B0 的光学条件、Q_lock 或排序规则。

## Phase B.1 后续结果

Phase B.1 已在 A0/B0.20、EPD3/EPD5、0D/-1.5D 上成功完成 MFE MTFA probe，并比较：

```text
Samp = 2 / 3 / 4
frequency step = 5 / 2.5 cycles/mm
```

实测最大绝对 `Q_lock` 差异：

```text
Samp 2→3      0.00221683
Samp 3→4      0.00067564
5→2.5 cyc/mm  0.00492149
```

据此项目已经冻结：

```text
production Samp = 3
production frequency step = 5 cycles/mm
```

Phase B.1 无需重跑。

当前下一步已更新为：

```text
scripts/run_task_005d_b0_scan.py
```

完整 scan 前必须通过 Phase B.1 evidence gate；完整 scan 后仍需人工 morphology review/re-rank，才允许写不可变 B0 lock。

权威后续定义见：

```text
docs/TASK_005D_PHASE_B1_MTFA_PROBE_REVIEW_2026-08-19.md
docs/TASK_005D_B0_MTF_ACQUISITION_REVISION_2026-08-19.md
docs/TASK_005D_CORNEA_LOCK_ASSETS.md
```
