# TASK-005C 第二轮 OpticStudio STOP 记录 — 2026-08-18

## 1. 结论

第二轮 TASK-005C 实机验证**未通过，且已按 STOP 条件正确停止**。

本轮结果不能用于判断：

\[
C_4^0(6\,\mathrm{mm})=+0.258\pm0.005\ \mu m
\]

是否在当前 OpticStudio reference convention 下成立，因为失败发生在 Python.NET / ZemaxEngine 的 Zernike analysis 类型创建阶段，而不是在一个成功完成并返回数值的 Zernike 计算之后。

因此：

- PR #22 继续保持 Draft；
- 不合并；
- 不修改 Liou R/Q；
- 不放宽 C40 tolerance；
- 不修改 `MVP_2026_v2`；
- 不生成 005C 正式 asset / validation CSV / lock；
- 下一步先生成无 Zernike-API 调用的 diagnostic `.zos`，由项目负责人在 OpticStudio GUI 中人工读取 Z11/C40。

---

## 2. 验证环境

- branch: `feat/task-005c-standard-eye`
- head: `fca17a61d3a4788edf6139c7075f6d7383073db0`
- OpticStudio: `2026 R1.00`
- license: `Premium`
- Python: `3.12.9`

---

## 3. 已通过项目

```text
uv sync                                   -> PASS
pytest tests/unit/test_standard_eye.py    -> 5 passed
pytest tests/unit                         -> 103 passed
ruff check .                              -> PASS
python -m compileall -q src tests scripts -> PASS
uv lock --check                           -> PASS
```

TASK-005B v2 `--validate-only`：两枚基座均 PASS，文件和 CSV hash 保持不变。

独立既有 Zernike 实机测试：

```text
1 passed
```

因此：

- Python 环境本身可用；
- ZOS-API session 可用；
- 既有独立 Zernike test 仍可用；
- 005B v2 正式资产没有受到本轮诊断影响。

---

## 4. TASK-005C Process B 失败点

候选 `.zos` 可以加载，但在首次取得 Zernike Standard settings 类型时，OpticStudio/Python.NET 原生层崩溃：

```text
FRU__delta_init(): Attempt to start when running!

Failed to create Python type for AS_ZernikeStandardCoefficients
System.IO.FileLoadException:
A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

失败发生于 `AS_ZernikeStandardCoefficients` 类型创建/装载阶段。

因此 Process B 没有形成完整的 `StandardEyeMeasurements`，以下量不能作为本轮正式实机证据：

- `medium_index_after_iol_ref`；
- Quick Focus 最佳 `IOL_REF→IMAGE` 距离；
- Quick Focus 后 C40。

代码与单元测试中 `medium_index_after_iol_ref=1.336` 的要求仍然有效，但在本轮没有获得完整实机报告来把它升级为正式 005C 证据。

---

## 5. 为什么本轮不能改科学目标

本轮已经有一个关键对照：**独立既有 Zernike 实机测试可以通过。**

所以现有证据更支持：

> 005C 特定调用路径触发了 Python.NET / ZemaxEngine 原生生命周期或类型加载问题。

而不是：

> Liou 两面角膜处方本身被证明无法达到 Norrby 的 0.258 µm。

只有在 OpticStudio 成功完成同一处方的 Zernike 计算并返回稳定结果后，才有资格讨论 reference convention 的科学映射问题。

---

## 6. 清理状态

本轮停止后：

- 没有生成正式 `STD_IOL_EYE_2024.zos`；
- 没有生成 005C validation CSV；
- 没有生成 005C lock；
- 临时候选 `.zos` 已删除；
- 无存活 OpticStudio/Zemax 进程；
- 后续 005C build、validate-only、全套 Zemax gates 已停止，避免无效占用 license/实例；
- 未成功的生命周期诊断改动已撤销；
- 本轮没有提交、推送或合并本地诊断代码。

原本的诊断修改仍保存在本地 stash；另有少量 Ruff 修正留在本地工作区，拉取远端时不得盲目覆盖。

---

## 7. 下一步

当前分支已加入：

```text
scripts/build_task_005c_manual_diagnostics.py
docs/TASK_005C_MANUAL_OPTICSTUDIO_DIAGNOSTICS.md
```

由 Codex 运行：

```powershell
uv run python scripts/build_task_005c_manual_diagnostics.py `
  --baseline-id MVP_2026_v2 `
  --output-dir project_mvp_2026_v2/diagnostics/task005c_manual
```

脚本只生成三个 diagnostic-only `.zos` 和一个 manifest：

1. `TASK005C_A_FIXED_REFERENCE.zos`
2. `TASK005C_B_PARAXIAL_FOCUS.zos`
3. `TASK005C_C_WAVEFRONT_BEST_FOCUS.zos`
4. `TASK005C_DIAGNOSTIC_MANIFEST.json`

生成过程不得创建 Zernike analysis，也不得把这些文件登记进 `project/locks`。

随后由项目负责人在 OpticStudio GUI 中使用统一 Zernike Standard Coefficients 设置人工读取 Z11/C40。

详细步骤见：

```text
docs/TASK_005C_MANUAL_OPTICSTUDIO_DIAGNOSTICS.md
```

在人工结果返回前，PR #22 保持 Draft，TASK-005C 保持 STOP。
