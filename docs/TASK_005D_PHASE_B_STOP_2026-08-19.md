# TASK-005D Phase B 实机 STOP

日期：2026-08-19  
分支：`feat/task-005d-cornea-lock-assets`  
实机 HEAD：`5883dee40096909a4290361b5a39a14602e8f8d9`

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

后续只允许替换 **MTF acquisition primitive**。

## 后续方案更新

STOP 后曾短暂实现 `Huygens PSF → Python FFT → MTF` 作为备选恢复路线。经后续设计复核，该中间方案已被正式废弃，相关 TASK-005D 专用代码已从 PR 中删除；不得将其视为当前下一步。

当前正式恢复方案为：

```text
CORNEA_LOCK_B0_555_v2
MFE MTFA diffraction MTF
Grid = 0
Data Type = 0
Wave = 1
Field = 1
frequency = 0..50 cycles/mm
production step = 5 cycles/mm
```

该修订不改变眼模型 scientific baseline，也不改变 B0 的光学条件、Q_lock 或排序规则。

当前下一步是运行：

```text
scripts/probe_task_005d_mtfa.py
```

只在 A0 与 B0.20、少量代表 defocus plane 上验证：

- MFE MTFA runtime/API；
- 相邻 `Samp` 收敛；
- 5 vs 2.5 cycles/mm frequency-step 敏感性。

Probe PASS 后才允许重新运行完整五候选 Phase B。

权威后续定义见：

```text
docs/TASK_005D_B0_MTF_ACQUISITION_REVISION_2026-08-19.md
docs/TASK_005D_CORNEA_LOCK_ASSETS.md
```
