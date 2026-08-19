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

## 后续约束

不得反复重试 `AS_HuygensMtf` 路径，也不得因此改变：

- A0/B 候选科学处方；
- 17-plane B0 defocus grid；
- EPD3/EPD5；
- `Q_lock=(1/50)∫_0^50 MTF(f)df`；
- B0 distance-retention gates；
- `rank_b0_candidates()` 排序规则。

后续只允许替换 **Huygens MTF acquisition primitive**。

Ansys OpticStudio 官方说明 Huygens MTF 是对 Huygens PSF 做 FFT，且两者的 Image Sampling / Image Delta 定义一致。因此优先评估在保持 `128 pupil / 256 image / 0.5 µm` 不变的条件下，由 Huygens PSF 网格在 Python 中计算等价 MTF；在真实工作站验证 Huygens PSF API 路径之前，不启动完整 Phase B 重跑。
