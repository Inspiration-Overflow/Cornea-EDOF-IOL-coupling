# TASK-005C — OpticStudio GUI 人工诊断文件方案

> 状态：**第二轮实机 STOP 后的诊断方案。本文先于对应诊断脚本实现。**
>
> 目的：在不调用 Zernike Standard ZOS-API 类型的前提下，生成少量可由项目负责人直接在 OpticStudio GUI 中打开和检查的 `.zos` 文件，以区分“光学处方/焦面定义问题”与“Python.NET/ZemaxEngine 原生生命周期问题”。

## 1. 背景

第二轮 TASK-005C 实机验证在以下条件下停止：

- `feat/task-005c-standard-eye@fca17a61d3a4788edf6139c7075f6d7383073db0`；
- OpticStudio 2026 R1.00 Premium；
- Python 3.12.9；
- 全部离线单元测试、Ruff、compileall、`uv lock --check` 通过；
- TASK-005B v2 只读验证通过且 hash 不变；
- 独立既有 Zernike 实机测试通过；
- 但 005C Process B 在候选 `.zos` 已加载后，首次取得 `AS_ZernikeStandardCoefficients` settings 类型时发生原生崩溃：

```text
FRU__delta_init(): Attempt to start when running!

Failed to create Python type for AS_ZernikeStandardCoefficients
System.IO.FileLoadException:
A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

因此第二轮没有获得可用于科学判断的：

- `medium_index_after_iol_ref` 完整实机回读报告；
- Quick Focus 最佳 `IOL_REF→IMAGE` 距离；
- Quick Focus 后 `C4^0`。

该失败只证明当前 005C 的 Zernike/Python.NET 生命周期仍不可靠，**不能证明 Liou/Norrby 的 `C4^0=+0.258 µm` 在 OpticStudio GUI 下不成立，也不能据此修改 Liou 的 R/Q 或放宽容差。**

---

## 2. 本轮诊断原则

本轮不继续用自动化 Zernike 来“撞”原生生命周期，而改为：

1. Codex 仅通过 ZOS-API 建立/派生几个 `.zos` 文件；
2. 这些文件的生成流程**不得创建 Zernike Standard analysis**；
3. 每个文件在独立 Python/OpticStudio 进程中生成或派生；
4. 项目负责人随后在 OpticStudio GUI 中人工打开这些文件；
5. 在 GUI 中使用同一套 Zernike Standard Coefficients 设置读取 Z11/C40；
6. 诊断文件只进入本地 diagnostic 目录，**不得登记为 `STD_IOL_EYE_2024` 正式 asset、不得写 TASK-005C validation CSV、不得写 lock。**

这一步是诊断，不修改：

- `MVP_2026_v2`；
- Liou 角膜 R/Q/厚度/折射率；
- EPD=6 mm；
- λ≈546 nm；
- `C4^0=+0.258±0.005 µm` 当前科学目标；
- `5.15±0.10 mm` footprint；
- WFS/RAD/HOA `SA_base`；
- EPD3/EPD5 主矩阵；
- TDD-999。

---

## 3. 生成三个诊断 `.zos`

统一从当前修订后的标准眼处方出发：

- Liou 两面角膜；
- EPD=6.0 mm；
- λ=546 nm；
- `CORNEA_POST → IOL_ANT_REFERENCE = 3.923547862... mm` 的当前几何起点；
- `CORNEA_POST` 后介质 `n=1.336`；
- **`IOL_ANT_REFERENCE` 后也继续 `n=1.336`**，不得出现 `1.336 → AIR` 的假平面折射界面。

### DIAG-A — 固定参考面

文件：

```text
TASK005C_A_FIXED_REFERENCE.zos
```

定义：

- 与当前标准眼候选的保存态一致；
- anterior-cornea vertex → IMAGE 保持项目固定参考长度 `23.950 mm`；
- 不运行 Quick Focus；
- 不运行 Zernike API。

用途：

- 人工确认 LDE、材料、EPD、波长、IOL reference 和固定 IMAGE；
- 在 GUI 中得到“固定参考面条件”的 Z11/C40，作为已知第一轮 `0.276491 µm` 的复核基准。

### DIAG-B — 连续介质下的旁轴焦面

文件：

```text
TASK005C_B_PARAXIAL_FOCUS.zos
```

定义：

- 从 DIAG-A 在**新的 OpticStudio 进程**中加载；
- 使用项目当前一阶计算得到的 cornea-only paraxial focus；
- 只改变 `IOL_ANT_REFERENCE → IMAGE` thickness，使后角膜至 IMAGE 等于该旁轴焦距；
- 保持 `IOL_ANT_REFERENCE` 后 `n=1.336`；
- 保存该诊断焦面；
- 不运行 Zernike API。

用途：

- 复核第一轮 `0.385937 µm` 是否主要来自当时意外 `1.336 → AIR` 平面界面；
- 明确“连续 1.336 + 旁轴焦面”下 GUI Zernike 的实际结果。

**该文件不是正式 best-focus 定义。**

### DIAG-C — Wavefront Error Quick Focus 最佳焦面

文件：

```text
TASK005C_C_WAVEFRONT_BEST_FOCUS.zos
```

定义：

- 从 DIAG-A 在**另一个新的 OpticStudio 进程**中加载；
- 只运行 OpticStudio Quick Focus；
- criterion = `Wavefront Error`；
- `UseCentroid = False`；
- Quick Focus 完成后保存 resulting IMAGE thickness；
- **之后不得创建 Zernike Standard analysis**；
- 退出该 OpticStudio 进程。

用途：

- 让项目负责人在 GUI 中直接看到 OpticStudio 自己选择的 minimum-RMS-wavefront best focus；
- 再由 GUI 手工运行 Zernike Standard，避免 Python.NET `AS_ZernikeStandardCoefficients` 类型创建问题。

Ansys 官方 Python.NET 示例明确支持 `TheSystem.Tools.OpenQuickFocus()`；OpticStudio Zernike Standard 文档则说明 Zernike 系数由 normalized pupil ray grid 对波前拟合，并受 Reference OPD / evaluation surface 约定影响。因此本轮把“文件生成”和“Zernike GUI 读取”刻意拆开。

---

## 4. Codex 只应生成文件和最小 manifest

建议本地输出目录：

```text
project_mvp_2026_v2/diagnostics/task005c_manual/
```

运行：

```powershell
uv run python scripts/build_task_005c_manual_diagnostics.py `
  --baseline-id MVP_2026_v2 `
  --output-dir project_mvp_2026_v2/diagnostics/task005c_manual
```

该目录只保存：

```text
TASK005C_A_FIXED_REFERENCE.zos
TASK005C_B_PARAXIAL_FOCUS.zos
TASK005C_C_WAVEFRONT_BEST_FOCUS.zos
TASK005C_DIAGNOSTIC_MANIFEST.json
```

manifest 至少记录脚本能够可靠取得的：

- git head；
- Python version；
- OpticStudio install dir；
- ZOS-API license status / API mode / instance number（API 可用时）；
- 每个 `.zos` 的 SHA-256；
- EPD；
- λ；
- surface count；
- 后角膜→IOL reference 距离；
- IOL reference 后 medium index；
- anterior-cornea→IMAGE 总距离；
- `IOL_REF→IMAGE` thickness；
- variant ID；
- focus method：`fixed_reference` / `paraxial_diagnostic` / `quickfocus_wavefront_error`；
- `formal_artifact=false`；
- `zernike_api_invoked_by_this_script=false`；
- `must_not_enter_project_locks=true`。

若 B/C 中途 STOP，manifest 仍写出此前成功文件，并记录 `completed_all_variants=false` 与 error；这样不需要为了完整 manifest 重跑已经成功的 worker。

OpticStudio 产品版本与 edition/license 名称仍由 Codex 在运行报告中人工记录（例如 `2026 R1.00 / Premium`），不因为某个 ZOS-API 属性在不同版本不可用而阻断诊断文件生成。

不得把这些 diagnostic SHA 写入 `project/locks`。

### 4.1 诊断生成的 STOP 规则

- 不运行正式 `build_task_005c_standard_eye.py`；
- 不运行 Zernike integration test；
- 不运行全套 Zemax gates；
- 每个 diagnostic worker 只尝试一次，不做自动重试循环；
- 若 A 失败：停止，不生成 B/C；
- 若 A 成功、B 失败：保留 A，停止并报告；
- 若 A/B 成功、C 的 Quick Focus 失败：保留 A/B，停止并报告；
- 无论生成多少个诊断文件，都不得登记 lock。

---

## 5. 项目负责人在 OpticStudio GUI 中的人工检查

对生成成功的文件逐一执行。

### 5.1 先看 LDE / System Explorer

确认：

- EPD = `6.000 mm`；
- wavelength 1 = `0.546 µm`；
- field = 0°；
- 前角膜：R=`+7.77 mm`，Q=`-0.18`；
- 后角膜：R=`+6.40 mm`，Q=`-0.60`；
- 角膜厚度=`0.50 mm`；
- 角膜 n≈`1.376`；
- 后角膜后 n≈`1.336`；
- IOL reference 后 n≈`1.336`；
- IOL reference 为平面 dummy/reference surface，不应产生额外屈光力。

### 5.2 手工运行 Zernike Standard Coefficients

三个文件使用完全相同设置：

```text
Analyze → Wavefront → Zernike Standard Coefficients
Sampling: 32 × 32
Maximum Term: 37
Wavelength: 1
Field: 1
Ref OPD To Vertex: OFF
Surface: Image
Sx: 0
Sy: 0
Sr: 1
Epsilon: 0
```

记录：

- Z11（primary spherical）数值，单位 waves；
- GUI 显示的相关 reference/evaluation 信息；
- 截图；
- 如方便，同时记录 RMS wavefront error。

换算：

\[
C_4^0(\mu m)=Z11(\mathrm{waves})\times0.546\ \mu m.
\]

### 5.3 最希望得到的人工诊断结果

请把三组结果回传为：

```text
A_FIXED_REFERENCE:
  IOL_REF→IMAGE = ... mm
  Z11 = ... waves
  C40 = ... µm

B_PARAXIAL_FOCUS:
  IOL_REF→IMAGE = ... mm
  Z11 = ... waves
  C40 = ... µm

C_WAVEFRONT_BEST_FOCUS:
  IOL_REF→IMAGE = ... mm
  Z11 = ... waves
  C40 = ... µm
```

最好附三张 Zernike Standard Coefficients 截图和一张 DIAG-A 的 LDE 截图。

---

## 6. Codex 回传格式

若三个文件全部成功生成，只需回传：

```text
head = ...
OpticStudio = 2026 R1.00 / Premium
Python = ...
output_dir = ...

A sha256 = ...
B sha256 = ...
C sha256 = ...
manifest = ...

A/B/C medium_index_after_iol_ref = ...
A/B/C IOL_REF→IMAGE = ...
```

不要由 Codex 打开 Zernike analysis，也不要替项目负责人读取 GUI C40。

---

## 7. 结果解释规则

1. 若 DIAG-C GUI C40 落入 `0.258±0.005 µm`：
   - Liou/Norrby → OpticStudio 的科学映射基本成立；
   - 下一步主要修 Zernike Python.NET 生命周期，不改科学目标。
2. 若 DIAG-B 与第一轮 `0.385937 µm` 明显不同：
   - 支持第一轮 paraxial-focus 结果受到假 AIR 界面污染。
3. 若 DIAG-C 仍稳定偏离 `0.258±0.005 µm`：
   - 再次 STOP；
   - 不调 Liou R/Q，不放宽 tolerance；
   - Web 端专门研究 OSLO 与 OpticStudio 的 reference-sphere / best-focus / Zernike convention 映射，再决定 `0.258` 是 direct gate 还是 provenance anchor。
4. 任何一个诊断 `.zos` 都不得直接升级为正式 005C lock。

---

## 8. 当前结论

第二轮实机失败仍不足以改变科学 baseline。下一步最小、信息量最高的动作不是继续自动 Zernike，而是生成三个没有 Zernike API 调用的 diagnostic `.zos`，由项目负责人在 OpticStudio GUI 内人工统一读取 Z11/C40。
