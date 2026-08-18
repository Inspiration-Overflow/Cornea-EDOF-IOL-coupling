# TASK-005B — 双基座处方实现与 OpticStudio 实机验证

## 1. 完成范围

TASK-005B 已把 TASK-005A 冻结的两个轴向背景写入代码，并在本机 OpticStudio 2026 R1.00、Premium license 下生成正式基座：

- `BASE_LB_PSEUDOPHAKIC.zos`
- `BASE_ATC_M3_PSEUDOPHAKIC.zos`

两个文件已写入本地 `project/models/assets/`，并在 `MVP_2026_v1` 项目索引中登记为 locked artifact。`.zos`、锁索引和验证 CSV 属于本地生成物，不进入 Git。

本阶段只实现两个基座的轴向参考处方，不实现 A0/B0/C0 的实际角膜曲率和厚度，也不实现 IOL carrier 的曲率、厚度或功率。

## 2. 处方结构

除 OBJECT 外，两个基座都使用以下表面顺序：

| Surface | Comment | 顶点位置定义 | 到下一面的介质 |
| ---: | --- | --- | --- |
| 1 | `CORNEA_ANT_MODULE_REF` | `0.000 mm` | 未定义实际角膜材料 |
| 2 | `CORNEA_POST_REF` | `0.000 mm` | aqueous，555 nm 实际 `n=1.336` |
| 3 | `STOP` | `3.150 mm` | aqueous，555 nm 实际 `n=1.336` |
| 4 | `IOL_ANT_REF` | `4.500 mm` | vitreous，555 nm 实际 `n=1.336` |
| 5 | `IMAGE_FIXED` | `AL` | IMAGE |

其中：

- LB 的 `AL=23.950 mm`；
- Atchison Model 1、`SR=-3.00 D` 样本的 `AL=24.477 mm`；
- STOP 为 Surface 3；
- IMAGE 为平面；
- IOL 前参考面到 IMAGE 的 thickness 使用 Fixed solve；
- 所有参考面均为 Standard 平面，没有 Coordinate Break、GRIN 或天然晶状体面。

## 3. 角膜参考区段的处理

TASK-005A、URD 和 TDD 没有冻结项目 A0/B0/C0 的共同角膜厚度数值。TASK-005B 因此没有采用 Liou–Brennan 的 `0.50 mm`，也没有采用 Atchison 的 `0.55 mm`。

正式基座中的前、后角膜参考面暂时重合，`cornea_reference_slot_mm=0.000 mm`。这不是“实际角膜厚度为零”的科学结论，只表示实际角膜模块尚未安装。后续安装 A0/B0/C0 时必须同时满足：

1. 两个 base 使用相同角膜厚度和后角膜定义；
2. 后角膜到 STOP 仍为 `3.150 mm`；
3. 后角膜到 IOL 前表面仍为 `4.500 mm`；
4. 前角膜顶点到固定 IMAGE 仍为各自冻结 AL；
5. 不移动 IMAGE 追焦。

## 4. 介质实现

MVP 主分析是 555 nm 单色。代码使用 OpticStudio `MaterialModel` solve 表示房水和玻璃体，并通过 `LDE.GetIndex()` 读取 555 nm 实际折射率。写入时迭代调整 model index，直到实际值与 `1.336` 的差小于 `1e-10`；正式文件回读值为：

`1.3360000000001566`

Material Model 的大 Abbe 数只用于降低本单色处方中的色散影响，不构成房水或玻璃体色散模型。多波长研究必须另行冻结介质色散定义。

## 5. 实机回读结果

| 资产 | AL mm | 后角膜→STOP mm | 后角膜→IOL ant mm | aqueous | vitreous | IMAGE | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `BASE_LB_PSEUDOPHAKIC` | 23.950 | 3.150 | 4.500 | 1.3360000000001566 | 1.3360000000001566 | plane / Fixed | PASS |
| `BASE_ATC_M3_PSEUDOPHAKIC` | 24.477 | 3.150 | 4.500 | 1.3360000000001566 | 1.3360000000001566 | plane / Fixed | PASS |

两个文件均为 555 nm、Field X/Y=`0°`、6 个表面（含 OBJECT），STOP Surface=`3`。正式文件在独立 Python/OpticStudio 进程中只读重载后再次通过，校验前后 SHA-256 未变化。

## 6. 正式哈希

| Artifact ID | SHA-256 |
| --- | --- |
| `BASE_LB_PSEUDOPHAKIC` | `3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c` |
| `BASE_ATC_M3_PSEUDOPHAKIC` | `217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c` |

验证 CSV：`project/results/TASK_005B_BASE_VALIDATION.csv`，当前 SHA-256 为：

`3b7373fce0a1dd8c4ff944055a0d430d4b97946e9479f6997e622450e37ae18f`

## 7. 代码和失败保护

实现包含以下约束：

- `BaselineBaseSpec` 保存 `source_model_id` 和 `source_refraction_d`，两项进入 scientific baseline hash；
- 两个 base ID 必须完整且唯一；
- 非有限值、错误的轴向顺序、`n<=1`、非零 field 均被拒绝；
- 构建先写临时 `.zos` 并回读，通过后才复制和登记 lock；
- 复制完成后再次检查 SHA-256；
- 已有 locked base 只做语义、路径、类型、baseline 和 SHA-256 校验，不重新生成；
- 未登记但已占用正式路径的文件不会被覆盖；
- 只读验证不保存 `.zos`，并检查锁哈希。

实机测试还确认 OpticStudio 2026 R1 的 `LDE.StopSurface` 是只读属性。STOP 写入已改为目标 surface 的 `IsStop=True`。

## 8. Python.NET / ZOS-API 测试隔离

同一 pytest/CLR 进程混合编辑器材料类型和 Huygens/Zernike 结果类型时，本机出现 `ZemaxEngine.dll` 类型加载顺序错误。正式 Zemax gate 因此按测试文件使用独立 Python 进程：

```powershell
uv run python scripts/run_zemax_gates.py
```

单个 Python 进程内部只创建一个 OpticStudio application，逻辑 session 串行使用该 application；进程退出时执行一次 `CloseApplication()`。同一进程连续 10 次逻辑 session 和 worker-thread gate 均通过。

本次最终结果：

```text
pytest tests/unit                         -> 98 passed
run_zemax_gates.py                        -> 7 passed
ruff check .                              -> PASS
python -m compileall -q src tests scripts -> PASS
```

## 9. 后续范围

TASK-005B 只完成两个 base。RMD-TASK-005 仍需继续建立并验证：

- `STD_IOL_EYE_2024` 和 `ZERO_HOA_PARAXIAL_REFERENCE`；
- `REF_MONO_CORNEA_LOCK`；
- A0；
- 五个 B candidates；
- C0；
- Coordinate Return 和相关验证。

TASK-005B 没有生成 carrier、pair、manifest 或 Run72 结果，TDD-999 状态不变。
