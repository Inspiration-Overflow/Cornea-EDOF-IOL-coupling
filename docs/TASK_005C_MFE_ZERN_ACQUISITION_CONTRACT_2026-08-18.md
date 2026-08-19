# TASK-005C — MFE ZERN 自动获取契约与实机等价性证据

> 状态：**docs-first implementation contract**。本文件记录 2026-08-18 人工 GUI 科学验证与随后 MFE `ZERN` 实机 spike 的结果，并冻结 TASK-005C 后续 production 实现应采用的最小 Zernike 获取路径。
>
> 本文件不修改 scientific baseline；`MVP_2026_v2`、Liou 处方、6 mm 校准孔径、546 nm、`C4^0=+0.258±0.005 µm`、IOL footprint、WFS/RAD/HOA SA 目标、EPD3/EPD5 主矩阵和 TDD-999 均保持不变。

## 1. 结论摘要

TASK-005C 已把科学问题和工程问题分开，并分别获得实机证据：

1. **科学模型 / reference convention：PASS**
   - corrected Liou standard-eye scaffold；
   - `EPD=6.0 mm`；
   - `λ=0.546 µm`；
   - `IOL_ANT_REFERENCE` 后连续 `n≈1.336`；
   - OpticStudio Quick Focus 使用 `Wavefront Error`、`UseCentroid=False`；
   - GUI Zernike Standard Coefficients 在 best-focus diagnostic C 中得到：
     - `Z4 = +0.00434634 waves`；
     - `Z11 = +0.47360558 waves`；
     - `Z37 = +0.00025905 waves`；
     - `C40 = Z11 × 0.546 = +0.25858864668 µm`；
   - 因此满足冻结 gate `+0.258±0.005 µm`。

2. **MFE `ZERN` 自动获取与 GUI 等价：PASS**
   - 不创建 `AS_ZernikeStandardCoefficients` / Zernike analysis settings type；
   - 使用 Merit Function `ZERN` 临时 operand；
   - A/B/C 三个 GUI oracle 均被实机复现；
   - C 的 Z11/Z37 差值均远小于 `1e-5 waves` 工程等价性阈值。

3. **production TASK-005C：PASS**
   - production 已切换至 MFE-ZERN；
   - 正式 build、validate-only、Zemax integration test、全套 Zemax gates 均通过；
   - 正式 `STD_IOL_EYE_2024`、validation CSV、lock 已生成；
   - validate-only optical-file hash 不变。

---

## 2. 冻结 MFE-ZERN acquisition contract

production acquisition 必须创建两个**相邻** `ZERN` operands：

```text
Term 11 + Term 37
Wave=1
Samp=1
Field=1
Type=1
Epsilon=0
Vertex=0
```

语义：

- Term 11 = Standard Zernike primary spherical coefficient；
- adjacent Term 37 = 将 Standard-Zernike fit 的 maximum term 固定到 37；
- `Wave=1` = 标准眼唯一 546-nm wavelength；
- `Samp=1` = 32×32 pupil grid；
- `Field=1` = on-axis field；
- `Type=1` = Standard Zernike；
- `Epsilon=0` = full circular pupil；
- `Vertex=0` = chief-ray OPD reference，对应 GUI `Ref OPD To Vertex = OFF`。

这些值是**精确冻结值，不是推荐默认值**。`MfeZernikeStandardSettings.validate()` 必须拒绝任何 drift，包括但不限于：

- Term 12/36/38；
- Wave 2；
- Samp 2；
- Field 2；
- Type 非 1；
- Epsilon 非 0；
- Vertex 1。

原因不仅是 scientific provenance：production result 字段固定命名为 `z11_waves` / `z37_waves`，因此允许 term drift 会直接造成语义错误。

---

## 3. 已验证 API 路径

OpticStudio 2026 R1.00 Premium / Python 3.12.9 实机确认：

```text
MFE.InsertNewOperandAt(...)
MFE.GetOperandAt(...)
operand.ChangeType(MeritOperandType.ZERN)
set Term/Wave/Samp/Field/Type/Epsilon/Vertex cells
MFE.CalculateMeritFunction()
read operand.Value
MFE.RemoveOperandsAt(...)
```

2026 R1 中正确插入方法名是 `InsertNewOperandAt`，不是 `InsertOperandAt`。

production primitive 必须：

1. 记录原始 MFE operand count；
2. 在末尾插入两个 temporary ZERN rows；
3. 验证参数 cell layout；
4. 写入冻结参数；
5. Calculate；
6. 读取 Z11/Z37；
7. `finally` 中移除 temporary rows；
8. 验证 MFE operand count 恢复；
9. 不 Save lens。

operand creation/evaluation、非 finite coefficient、unexpected cell layout、cleanup failure 均 fail closed。

---

## 4. GUI ↔ MFE 实机等价性证据

人工 GUI 使用相同 settings：

```text
Analyze → Wavefront → Zernike Standard Coefficients
Sampling = 32×32
Maximum Term = 37
Wavelength = 1
Field = 1
Ref OPD To Vertex = OFF
Surface = Image
Sx=0, Sy=0, Sr=1, Epsilon=0
```

### C — Wavefront best focus

```text
GUI Z11 = 0.47360558 waves
MFE Z11 = 0.4736063027853602 waves
delta   = 7.23e-07 waves

GUI Z37 = 0.00025905 waves
MFE Z37 = 0.00026011052367169805 waves
delta   = 1.06e-06 waves
```

### A — fixed reference

```text
GUI Z11 = 0.22875730 waves
MFE Z11 = 0.2287573036054908 waves

GUI Z37 = 0.00007592 waves
MFE Z37 = 0.00007592431802708115 waves
```

### B — paraxial diagnostic focus

```text
GUI Z11 = 0.48911744 waves
MFE Z11 = 0.4891174420997102 waves

GUI Z37 = 0.00027315 waves
MFE Z37 = 0.0002731506714183534 waves
```

工程 acquisition-equivalence gate：

```text
|MFE - GUI| <= 1e-5 waves
```

该阈值只用于确认 API acquisition 与 GUI oracle 等价，不替代 scientific `C40=+0.258±0.005 µm` gate。

---

## 5. production TASK-005C 正式结果

production implementation commit：

```text
55ed85f4ac35744f8b5fcf3bf5ace404b0ef52e6
```

实机环境：

```text
OpticStudio 2026 R1.00 Premium
Python 3.12.9
```

正式 readback：

```text
EPD = 6.000 mm
wavelength = 546.0 nm
IOL footprint = 5.22108317213591 mm
cornea_index = 1.376000000000115
medium_index = 1.3360000000001004
medium_index_after_iol_ref = 1.3360000000001004
post-cornea→IOL_REF = 3.92354786166041 mm
best-focus IOL_REF→IMAGE = 26.600571884912345 mm

MFE Z11 = 0.4736063027853602 waves
MFE Z37 = 0.00026011052367169805 waves
C40 = 0.2585890413208067 µm
```

正式资产：

```text
project_mvp_2026_v2/models/assets/STD_IOL_EYE_2024.zos
SHA-256 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414

project_mvp_2026_v2/results/TASK_005C_STANDARD_EYE_VALIDATION.csv
SHA-256 7d329ad1a134cdb557582901b3bd70477826ec5df324927d6a06aa48256c834c
```

validate-only 前后 `.zos` hash 完全一致；正式 asset 已 `locked=true`。

---

## 6. native warning 解释

成功的 MFE/ZOS worker 在进程退出阶段可能输出：

```text
*** FRU__delta_init(): Attempt to start when running!
```

如果同时满足：

- acquisition result 已成功读取；
- 无 `FileLoadException`；
- 无 `ZemaxEngine.dll` imported-procedure failure；
- lens hash 不变；
- residual OpticStudio/Zemax processes = 0；

则该单独 exit-time line 记录为 provenance warning，不单独判 FAIL。

以下仍 hard FAIL：

- operand creation/evaluation failure；
- non-finite Z11/Z37；
- frozen parameter/cell-layout mismatch；
- cleanup failure；
- `FileLoadException` / `ZemaxEngine.dll` type-loading failure；
- lens unexpected hash mutation；
- residual process；
- scientific C40 gate fail。

---

## 7. 与旧 Zernike analysis path 的关系

TASK-005C production 不得调用：

```text
AS_ZernikeStandardCoefficients
IAS_ZernikeStandardCoefficients
New_ZernikeStandardCoefficients
```

旧 independent Zernike analysis smoke test 可以继续保留，用作 API 能力交叉检查；它不是 TASK-005C production C40 acquisition path。

---

## 8. `.zmx` 文件格式后续

OpticStudio 2026 R1 GUI 推荐 `.zmx`。但本次 MFE-ZERN production integration 不与文件格式迁移混在同一变更中。

当前正式 005B/005C `.zos` hash 保留为已验证历史/正式证据。后续另做 docs-first `.zos → .zmx` canonical artifact revision，并独立验证 provenance、reload、readback、hash 与 lock 边界。

---

## 9. 当前状态与合并门槛

```text
scientific C40 definition = PASS
manual GUI C40 validation = PASS
MFE ZERN equivalence = PASS
production MFE-ZERN integration = PASS
formal TASK-005C asset/validation/lock = CREATED + PASS
review hardening: exact frozen settings = IMPLEMENTED
PR #22 = DRAFT until latest-head regression + final review
```

55ed85f 的正式实机结果继续有效；后续 review hardening 只收紧 settings validator，不改变 production 默认参数或光学计算路径。合并 PR #22 前，应在**最新 branch head** 上至少执行：

```text
unit MFE-ZERN tests
unit standard-eye tests
ruff / compileall / uv lock
standard-eye Zemax integration test
formal 005C validate-only
```

要求既有正式 asset hash `4dfc8d84...` 不变，readback/C40 继续 PASS。若通过，可把 TASK-005C 视为完成并进入 PR 最终审核；`.zmx` canonical migration 另开独立工程变更。

本文件的核心规则是：**以后如果需要新的 Term/Wave/Samp/Field/Type/Epsilon/Vertex 组合，应建立新的明确 acquisition contract，而不是修改本 settings 对象后继续把输出称为 TASK-005C Z11/Z37。**