# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件记录截至 2026-08-18 的真实代码/实机状态，不重新定义科学规范。

## 当前结论

当前正式 scientific baseline：

```text
MVP_2026_v2
```

`STD_IOL_EYE_2024` 的标准眼设计/球差校准条件固定为 `EPD=6.0 mm`、`λ≈546 nm`；主实验仍使用 `EPD3/EPD5`，不得用主实验瞳孔重调 carrier。

截至本次记录：TASK-005B v2 已实机回载通过；TASK-005C 科学定义、GUI C40、MFE-ZERN acquisition equivalence、production build/validate/gates 均已通过，并已生成正式 standard-eye asset、validation CSV 和 lock。独立 review 随后把 MFE-ZERN settings 从“正确默认值”进一步收紧为“只能取已验证精确值”的 fail-closed contract；该 hardening 不改变默认光路或既有正式结果，但 PR #22 merge 前需在最新 head 上补一次小范围本地 regression。

---

## TASK-005B v2 正式证据

```text
BASE_LB_PSEUDOPHAKIC.zos
SHA-256 3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c

BASE_ATC_M3_PSEUDOPHAKIC.zos
SHA-256 217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c

TASK_005B_BASE_VALIDATION.csv
SHA-256 3b7373fce0a1dd8c4ff944055a0d430d4b97946e9479f6997e622450e37ae18f
```

`project_mvp_2026_v2` 下 `--validate-only`：两 base PASS、findings 空、hash 不变。

---

## TASK-005C 科学定义与 GUI 验证

冻结：

```text
Liou anterior R/Q = +7.77 mm / -0.18
corneal thickness = 0.50 mm
Liou posterior R/Q = +6.40 mm / -0.60
cornea n ≈ 1.376
surrounding medium n ≈ 1.336
EPD = 6.0 mm
λ = 546 nm
corneal C4^0 target = +0.258 ± 0.005 µm
IOL-reference footprint = 5.15 ± 0.10 mm
```

`IOL_ANT_REFERENCE` 是 carrier 插入参考面，不是实际 IOL；空 standard-eye scaffold 中该 dummy plane 后继续 `n≈1.336`。

GUI best-wavefront-focus diagnostic C：

```text
Quick Focus = Wavefront Error
UseCentroid = False
Z4  = +0.00434634 waves
Z11 = +0.47360558 waves
Z37 = +0.00025905 waves
λ   = 0.546 µm
C40 = +0.25858864668 µm
```

科学 gate PASS；不得调 Liou R/Q 或放宽 `+0.258±0.005 µm`。

---

## MFE-ZERN production contract

TASK-005C production 不创建工作站上不稳定的 `AS_ZernikeStandardCoefficients` analysis settings type，而使用两个相邻临时 Merit Function `ZERN` operands：

```text
Term 11 + Term 37
Wave=1
Samp=1
Field=1
Type=1
Epsilon=0
Vertex=0
```

这些是**精确冻结值**；任何 drift 必须 fail closed。

C 的 GUI/MFE 等价性：

```text
GUI Z11 = 0.47360558
MFE Z11 = 0.4736063027853602
delta   = 7.23e-07 waves

GUI Z37 = 0.00025905
MFE Z37 = 0.00026011052367169805
delta   = 1.06e-06 waves
```

工程 acquisition-equivalence gate：`|MFE-GUI| ≤ 1e-5 waves`。A/B 亦通过。

API 路径：

```text
InsertNewOperandAt
GetOperandAt
ChangeType(MeritOperandType.ZERN)
set frozen cells
CalculateMeritFunction
read operand.Value
RemoveOperandsAt
```

临时 operands 必须在 `finally` 清理，MFE operand count 恢复，lens 不 Save。

---

## TASK-005C 正式 production 验证

实机环境：

```text
OpticStudio 2026 R1.00 Premium
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

正式资产：

```text
project_mvp_2026_v2/models/assets/STD_IOL_EYE_2024.zos
SHA-256 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414

project_mvp_2026_v2/results/TASK_005C_STANDARD_EYE_VALIDATION.csv
SHA-256 7d329ad1a134cdb557582901b3bd70477826ec5df324927d6a06aa48256c834c
```

formal standard eye 已 `locked=true`；validate-only 前后 `.zos` hash 完全一致。

成功 worker 的 exit-time `*** FRU__delta_init(): Attempt to start when running!` 若没有 `FileLoadException`/`ZemaxEngine.dll` failure、结果成功读取、hash 不变、residual process=0，则只记录 provenance，不单独判 FAIL。

---

## 独立 review hardening

独立复核发现原 settings validator 允许部分参数改变；虽然默认路径实机正确，但与 frozen contract 不一致，而且 term drift 会让固定字段 `z11_waves`/`z37_waves` 产生语义错误。

因此最新 branch 已收紧为只接受：

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

并加入逐参数 drift 单测。该修改不改变 production 默认参数或光学计算路径，55ed85f 的正式实机证据继续有效。

---

## RMD task 状态

| Task | 当前状态 | 下一步 |
| --- | --- | --- |
| TASK-001 | **完成并加固** | 保持 env gate |
| TASK-002 | **ZOS session 实机通过** | 长批次继续记录 native stderr |
| TASK-003 | **完成并在 v2 project 回放通过** | 保持 full-baseline hash fail-closed |
| TASK-004 | **metric engine 离线完成** | 后续真实 Huygens cross-check |
| TASK-005A | **完成** | 无 |
| TASK-005B | **v2 实机通过并锁定** | 无 |
| TASK-005C | **production 实机通过并锁定**；latest-head review hardening 待小回归 | 回归通过后正式关闭 |
| TASK-006 | **B0 算法完成** | 后续真实五点 scan |
| TASK-007 | **carrier science gate framework 完成** | 18 P/Q、ZERO_HOA、residual；TDD-999 仍阻断正式 lock |
| TASK-008 | **生成器完成** | TASK-007 后 18/36/72 |
| TASK-009 | **analysis API smoke/hardening 完成** | 代表配置 + sampling/MTF cross-check |
| TASK-010 | **GUI scaffold/thread boundary 已复核** | full-flow smoke |
| TASK-011 | **nominal acceptance checker 完成** | 代表配置通过后才可 Run72 |

---

## 仍有效 STOP 条件

1. 不得为 API 适配修改 `MVP_2026_v2`、Liou R/Q、EPD6、546 nm、`+0.258 µm`、footprint 或 carrier SA targets。
2. MFE-ZERN production settings 必须严格等于冻结 contract。
3. `TDD-999` 未解除前不得正式 EDOF carrier/pair locks 或 Run72。
4. 三代表配置未通过 sampling convergence + 独立 MTF cross-check 前不得 Run72。
5. 已 lock 的 005B/005C 不得由下游重写；validate-only 必须保持 hash。
6. synthetic data 不能进入正式 locks/manifests/论文结果。

---

## `.zmx` 文件格式后续

OpticStudio 2026 R1 推荐 `.zmx`。当前已验证的 005B/005C `.zos` canonical path/hash 暂不修改。`.zos → .zmx` 作为下一轮独立 docs-first 工程 revision，保留旧 `.zos` hash，并重新验证 `.zmx` provenance/reload/readback/hash/lock。

---

## PR #22 合并前最后回归

同步最新 branch head 后运行：

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
formal asset SHA = 4dfc8d84d37f2ef6bf28c08a5b46436311ad0036e267cf5463cc4dc0d58fa414
C40/readback PASS
no new hard native failure
residual process count = 0
```

通过后 TASK-005C 正式完成，可进入 PR #22 最终审核；`.zmx` migration 另开后续工程变更。