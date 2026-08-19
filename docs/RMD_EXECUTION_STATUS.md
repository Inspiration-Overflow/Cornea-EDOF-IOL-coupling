# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件记录截至 2026-08-18 的真实代码/实机状态，不重新定义科学规范。

## 当前结论

当前正式 scientific baseline 为：

```text
MVP_2026_v2
```

`STD_IOL_EYE_2024` 的标准眼设计/球差校准条件固定为 `EPD=6.0 mm`、`λ≈546 nm`；主实验仍使用 `EPD3/EPD5`，两者不得混用。

截至本次记录：

- TASK-005B v2 两个基础眼已在 OpticStudio 2026 R1.00 Premium 下完成正式只读回载验证，hash 与历史已验证资产一致；
- TASK-005C 的 Liou/Norrby 标准眼科学定义已通过 GUI 人工验证；
- Zernike Standard analysis settings 的 Python.NET 类型在该工作站存在原生加载问题，但 MFE `ZERN` operand 已经通过 A/B/C 三文件 GUI 等价性实机验证；
- production 已切换到 MFE `ZERN` Term11+Term37 获取 C40；
- 正式 TASK-005C build、validate-only、标准眼 Zemax integration test 和全套 Zemax gates 均已通过；
- 正式 `STD_IOL_EYE_2024` asset、validation CSV 和 lock 已生成；
- PR #22 尚未 merge；独立 review 又增加了“冻结 MFE-ZERN settings 不得漂移”的 fail-closed 加固，该加固只需一次小范围本地回归确认。

---

## TASK-005B v2 正式实机证据

```text
BASE_LB_PSEUDOPHAKIC.zos
SHA-256 3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c

BASE_ATC_M3_PSEUDOPHAKIC.zos
SHA-256 217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c

TASK_005B_BASE_VALIDATION.csv
SHA-256 3b7373fce0a1dd8c4ff944055a0d430d4b97946e9479f6997e622450e37ae18f
```

在 `project_mvp_2026_v2` 中执行 `--validate-only`：两枚 base 均 PASS、findings 为空、hash 不变。

旧 `MVP_2026_v1` 同 hash 继续保留为历史工作站证据；不得通过放宽 baseline hash 来混用 v1/v2 project provenance。

---

## TASK-005C 科学验证

### 标准眼冻结定义

```text
Liou cornea anterior R = +7.77 mm
Liou cornea anterior Q = -0.18
corneal thickness       = 0.50 mm
Liou cornea posterior R = +6.40 mm
Liou cornea posterior Q = -0.60
cornea n                 ≈ 1.376
surrounding medium n     ≈ 1.336
EPD                       = 6.0 mm
λ                         = 546 nm
corneal C4^0 target       = +0.258 ± 0.005 µm
IOL-reference footprint   = 5.15 ± 0.10 mm
```

`IOL_ANT_REFERENCE` 是 carrier 插入参考面，不是实际 IOL；空标准眼 scaffold 中该 dummy plane 前后均保持连续 `n≈1.336`，不得产生 `1.336→AIR` 的假平面折射界面。

### GUI 人工 reference-convention 验证

修正连续介质后，生成 A/B/C 三个 diagnostic model：

- A：fixed reference；
- B：cornea-only paraxial diagnostic focus；
- C：OpticStudio Quick Focus / `Wavefront Error` / `UseCentroid=False`。

C 在 OpticStudio GUI Zernike Standard Coefficients 下得到：

```text
Z4  = +0.00434634 waves
Z11 = +0.47360558 waves
Z37 = +0.00025905 waves
λ   = 0.546 µm
C40 = Z11 × λ = +0.25858864668 µm
```

因此 Liou/Norrby `C4^0=+0.258 µm` 在本项目冻结的 OpticStudio best-wavefront-focus convention 下可直接复现，科学 gate = PASS。不得调 Liou R/Q 或放宽该容差。

---

## TASK-005C MFE-ZERN acquisition contract

原 `AS_ZernikeStandardCoefficients` / Zernike Standard analysis settings type 在该工作站曾触发：

```text
FRU__delta_init(): Attempt to start when running!
FileLoadException / ZemaxEngine.dll imported-procedure failure
```

因此 production C40 acquisition 不再创建该 analysis object，而使用经实机验证的 MFE `ZERN`：

```text
Term 11 + Term 37，相邻两行
Wave=1
Samp=1        # 32×32
Field=1
Type=1        # Standard Zernike
Epsilon=0
Vertex=0      # chief-ray OPD reference / Ref OPD To Vertex OFF
```

这些是精确冻结值。若 Term/Wave/Samp/Field/Type/Epsilon/Vertex 任意漂移，production settings validation 必须 fail closed。

API 路径：

```text
InsertNewOperandAt
GetOperandAt
ChangeType(MeritOperandType.ZERN)
set cells
CalculateMeritFunction
read operand.Value
RemoveOperandsAt
```

A/B/C 三个 GUI oracle 的 MFE 等价性均通过；C：

```text
GUI Z11 = 0.47360558
MFE Z11 = 0.4736063027853602
delta   = 7.23e-07 waves

GUI Z37 = 0.00025905
MFE Z37 = 0.00026011052367169805
delta   = 1.06e-06 waves
```

工程等价性 gate：`|MFE-GUI| ≤ 1e-5 waves`。

---

## TASK-005C 正式 production 验证

实机环境：

```text
OpticStudio 2026 R1.00 / Premium
Python 3.12.9
```

production implementation commit：

```text
55ed85f4ac35744f8b5fcf3bf5ace404b0ef52e6
```

当次验证：

```text
tests/unit/test_standard_eye.py -> 5 passed
tests/unit                      -> 112 passed
ruff check .                    -> PASS
compileall                      -> PASS
uv lock --check                 -> PASS

tests/zemax/test_zos_standard_eye.py -> 1 passed
scripts/run_zemax_gates.py            -> 6 gate files PASS
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

所有 scientific/construction gates PASS。

正式资产：

```text
project_mvp_2026_v2/models/assets/STD_IOL_EYE_2024.zos
SHA-256 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414

project_mvp_2026_v2/results/TASK_005C_STANDARD_EYE_VALIDATION.csv
SHA-256 7d329ad1a134cdb557582901b3bd70477826ec5df324927d6a06aa48256c834c
```

`STD_IOL_EYE_2024` 已登记 `locked=true`。validate-only 前后 optical-file SHA-256 完全一致。

production TASK-005C 没有调用 `AS_ZernikeStandardCoefficients`；旧 independent Zernike analysis smoke test 仍单独保留并通过。

成功的 MFE/ZOS worker 在进程退出阶段仍可能打印：

```text
*** FRU__delta_init(): Attempt to start when running!
```

若结果已成功读取、无 `FileLoadException`/`ZemaxEngine.dll` failure、文件 hash 不变且 residual process=0，则该单独 exit-time warning 只记录 provenance，不单独作为 FAIL。

---

## 独立 review hardening

对 production commit 独立复核时发现：`MfeZernikeStandardSettings` 虽然默认值正确，但原 `validate()` 允许改变部分参数；这与“frozen acquisition contract”不一致，而且若 `term_primary` 改为其他 term，返回字段仍叫 `z11_waves`，会产生语义错误。

因此 review hardening 已将 settings 改为只能精确接受：

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

并增加逐参数 drift 单测。该修改不改变 production 默认值和光学计算路径；55ed85f 的正式实机结果继续有效，但 PR 合并前必须在最新 head 上补一次小范围 regression。

---

## RMD task 状态

| RMD task | 当前状态 | 下一阶段 |
| --- | --- | --- |
| TASK-001 Project Setup | **完成并加固** | 保持 locked-env 检查 |
| TASK-002 ZOS session | **实机通过** | 长批次继续记录 native stderr |
| TASK-003 Domain + ProjectStore | **离线完成并在 v2 project 回放通过** | 继续保持 full-baseline hash fail-closed |
| TASK-004 metric engine | **离线完成** | 用真实 Huygens PSF/MTF 做后续 cross-check |
| TASK-005A base definitions | **完成** | 无 |
| TASK-005B base assets | **v2 实机通过并锁定** | 无 |
| TASK-005C standard eye | **production 实机通过并锁定**；最新 review hardening 待小范围回归 | 回归通过后关闭 005C；再进入 005D/后续科学资产 |
| TASK-006 B0 | **算法完成并加固** | 005D/相关资产就绪后运行真实五点 B scan |
| TASK-007 carrier science gate | **fail-closed 门控完成** | 实际求 18 P/Q、ZERO_HOA achieved-SA、residual；TDD-999 仍阻断正式锁 |
| TASK-008 carrier/pair + manifest | **生成器完成** | TASK-007 通过后生成正式 18/36/72 |
| TASK-009 analysis | **API smoke/hardening 完成** | footprint/Prescription/Huygens MTF；3 代表配置；sampling/MTF cross-check |
| TASK-010 GUI | **scaffold/thread boundary 已复核** | GUI display/full-flow smoke |
| TASK-011 nominal acceptance | **验收判定器完成** | 只有代表配置通过后运行 Run72/repeatability |

---

## 仍然有效的 STOP 条件

1. `MVP_2026_v2`、Liou R/Q、EPD6、546 nm、`+0.258 µm`、footprint、WFS/RAD/HOA SA targets 不得为了适配 API 而静默修改。
2. MFE-ZERN production settings 必须严格等于已验证 contract；任何 drift 应 fail closed。
3. `TDD-999` 未解除前，不允许生成正式 EDOF carrier/pair locks，也不允许 Run72。
4. 3 个代表配置未通过 sampling convergence 与独立 MTF cross-check 前，不允许 Run72。
5. 已正式 lock 的 005B/005C asset 不得由下游流程重写；validate-only 必须保持 hash 不变。
6. 合成测试数据只用于代码合同，不能进入正式 locks/manifests/论文结果。

---

## 文件格式后续

OpticStudio 2026 R1 GUI 推荐使用 `.zmx`。当前 005B/005C 正式资产仍保留现有 `.zos` canonical path 和已验证 hash，避免把“Zernike acquisition 修复”和“文件格式迁移”混为一轮改动。

后续应单独执行 docs-first `.zos → .zmx` canonical artifact revision：

- 不改变 scientific baseline；
- 保留现有 `.zos` SHA 作为历史实机证据；
- 明确新 `.zmx` artifact provenance/lock/hash；
- 独立验证 reload/hash/readback 后再切换 canonical extension。

---

## 当前合并前入口

PR #22 当前仍 Draft。最新 review 已把 MFE-ZERN settings 锁为精确 contract，因此在 merge 前仅需在最新 branch head 上执行一次小范围回归：

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

要求：现有正式 `.zos` hash 仍为 `4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414`，所有 readback/C40 仍 PASS，且没有新的 hard native failure。通过后可进入 PR #22 最终独立审核；`.zmx` migration 另开后续工程变更。