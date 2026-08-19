# TASK-005C — MFE ZERN 自动获取契约与实机等价性证据

> 状态：**docs-first implementation contract**。本文件记录 2026-08-18 人工 GUI 科学验证、MFE `ZERN` 实机 spike、production 集成与独立 review hardening，并冻结 TASK-005C production 的 Zernike 获取路径。
>
> 本文件不修改 scientific baseline；`MVP_2026_v2`、Liou 处方、6 mm 校准孔径、546 nm、`C4^0=+0.258±0.005 µm`、IOL footprint、WFS/RAD/HOA SA 目标、EPD3/EPD5 主矩阵和 TDD-999 均保持不变。

## 1. 已验证结论

### 科学模型 / reference convention：PASS

corrected Liou standard-eye scaffold：

```text
EPD=6.0 mm
λ=0.546 µm
IOL_ANT_REFERENCE 后连续 n≈1.336
Quick Focus = Wavefront Error
UseCentroid=False
```

GUI best-focus diagnostic C：

```text
Z4  = +0.00434634 waves
Z11 = +0.47360558 waves
Z37 = +0.00025905 waves
C40 = +0.25858864668 µm
```

满足冻结 scientific gate `C4^0=+0.258±0.005 µm`。

### MFE ZERN 与 GUI acquisition 等价：PASS

production 不创建不稳定的 `AS_ZernikeStandardCoefficients` analysis settings type，而使用临时 Merit Function `ZERN` operands。

C：

```text
GUI Z11 = 0.47360558
MFE Z11 = 0.4736063027853602
delta   = 7.23e-07 waves

GUI Z37 = 0.00025905
MFE Z37 = 0.00026011052367169805
delta   = 1.06e-06 waves
```

A/B 也分别通过。工程 acquisition-equivalence gate = `|MFE-GUI| ≤ 1e-5 waves`。

### production TASK-005C：PASS

production implementation commit：

```text
55ed85f4ac35744f8b5fcf3bf5ace404b0ef52e6
```

实机环境：OpticStudio 2026 R1.00 Premium / Python 3.12.9。

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

formal asset 已 `locked=true`，validate-only 前后 optical-file hash 不变。

---

## 2. 精确冻结的 MFE-ZERN contract

production 必须创建两个相邻 ZERN rows：

```text
Term 11 + Term 37
Wave=1
Samp=1
Field=1
Type=1
Epsilon=0
Vertex=0
```

这些是**精确冻结值，不是推荐默认值**。`MfeZernikeStandardSettings.validate()` 必须拒绝任何 drift。

理由：

- acquisition provenance 已只验证这一组设置；
- production result 字段固定叫 `z11_waves` / `z37_waves`；
- 若 term 或其他 reference 参数漂移却继续使用这些字段名，会造成语义错误。

后续若需要另一组 acquisition 参数，应建立新的明确 contract，而不是修改本 settings 对象继续运行 TASK-005C。

---

## 3. 已验证 API 路径

```text
MFE.InsertNewOperandAt(...)
MFE.GetOperandAt(...)
operand.ChangeType(MeritOperandType.ZERN)
set Term/Wave/Samp/Field/Type/Epsilon/Vertex cells
MFE.CalculateMeritFunction()
read operand.Value
MFE.RemoveOperandsAt(...)
```

2026 R1 正确插入方法名是 `InsertNewOperandAt`。

production primitive 必须：

1. 记录原始 MFE operand count；
2. 末尾插入两个 temporary ZERN rows；
3. 验证参数 cell layout；
4. 写入精确冻结参数；
5. Calculate；
6. 读取 Z11/Z37；
7. `finally` 移除 temporary rows；
8. 验证 operand count 恢复；
9. 不 Save lens。

operand creation/evaluation、non-finite coefficient、cell-layout mismatch、cleanup failure 均 fail closed。

---

## 4. native warning 规则

成功 worker 在进程退出阶段可能出现：

```text
*** FRU__delta_init(): Attempt to start when running!
```

若结果已成功读取、无 `FileLoadException`/`ZemaxEngine.dll` failure、lens hash 不变、residual process=0，则该单独 exit-time warning 只记录 provenance，不单独判 FAIL。

以下仍 hard FAIL：

- operand creation/evaluation failure；
- non-finite Z11/Z37；
- frozen parameter/cell-layout mismatch；
- cleanup failure；
- `FileLoadException` / `ZemaxEngine.dll` type-loading failure；
- unexpected lens hash mutation；
- residual process；
- scientific C40 gate fail。

---

## 5. 与旧 Zernike analysis path 的关系

TASK-005C production 不得调用：

```text
AS_ZernikeStandardCoefficients
IAS_ZernikeStandardCoefficients
New_ZernikeStandardCoefficients
```

旧 independent Zernike analysis smoke test 可继续作为 API 能力交叉检查，但不是 TASK-005C production acquisition path。

---

## 6. 独立 review hardening

独立 review 发现 production commit 的 settings validator 允许部分参数改变，虽然默认路径正确，但不满足 frozen-contract/fail-closed 语义。

因此 branch 已把 validator 收紧为只能精确接受：

```text
term_primary=11
term_maximum=37
wavelength_number=1
field_number=1
sampling=1
zernike_type=1
epsilon=0
vertex=0
```

并增加逐参数 drift 单测。

该 review hardening **不改变 production 默认值、不改变光学计算路径、不否定 55ed85f 的正式实机结果**。合并 PR 前只需在最新 head 上补小范围 regression。

---

## 7. `.zmx` 文件格式后续

OpticStudio 2026 R1 推荐 `.zmx`。当前已验证的 005B/005C `.zos` canonical paths/hash 暂时保持不变。`.zos → .zmx` 另做独立 docs-first revision，并重新验证 provenance/reload/readback/hash/lock。

---

## 8. 当前状态与 merge gate

```text
scientific C40 definition = PASS
manual GUI C40 validation = PASS
MFE ZERN equivalence = PASS
production MFE-ZERN integration = PASS
formal TASK-005C asset/validation/lock = CREATED + PASS
exact-settings review hardening = IMPLEMENTED
latest-head local regression = PENDING
PR #22 = DRAFT
```

合并前在最新 `feat/task-005c-standard-eye` head 上至少执行：

```powershell
uv run pytest tests/unit/test_zos_mfe_zernike.py -vv
uv run pytest tests/unit/test_standard_eye.py -vv
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check

$P = "project_mvp_2026_v2"
uv run pytest tests/zemax/test_zos_standard_eye.py -vv
uv run python scripts/build_task_005c_standard_eye.py --project-dir $P --baseline-id MVP_2026_v2 --validate-only
```

要求：

```text
formal asset SHA remains 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414
C40/readback remain PASS
no new hard native failure
residual process count = 0
```

通过后，TASK-005C 可正式关闭并进入 PR #22 最终审核；`.zmx` migration 另开后续工程变更。