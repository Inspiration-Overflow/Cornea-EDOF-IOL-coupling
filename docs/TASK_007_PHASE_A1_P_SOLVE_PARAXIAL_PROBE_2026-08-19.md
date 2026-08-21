# TASK-007 Phase A.1 — provisional carrier P-solve + ZERO_HOA Paraxial capability probe

> 日期：2026-08-19  
> 状态：**Web 端实现完成；等待 Windows/OpticStudio 实机验证**  
> 分支：`feat/task-007-iol-residuals`  
> 上一阶段：Phase A.0 offline validation = PASS (`171 passed`，ruff/compileall/uv lock 全部 PASS)

## 1. 为什么先做 A.1，而不是直接批量解 18 个 P/Q

TASK-007 的实际 carrier power `P_ijk` 可以复用已经通过实机验证的 REF_MONO 工程镜片逻辑：

- `n=1.460`；
- `CT=1.000 mm`；
- 6 mm optic；
- symmetric biconvex；
- EPD3 Wavefront Quick Focus；
- fixed retina；
- Q 暂设为 0。

但 `Q_k(P_ijk)` 的正式标准眼目标必须相对于：

```text
ZERO_HOA_PARAXIAL_REFERENCE
```

当前 repo 已冻结这一科学定义，但尚未验证 OpticStudio 2026 R1 中真实 `Paraxial` surface 的 ZOS-API 枚举名与参数列。不能用 `Q=0` 的物理球面 IOL 冒充 zero-HOA reference，因为球面厚透镜本身仍可产生高阶球差。

因此 A.1 只验证两件事：

1. A0 角膜下两个 base 的实际 carrier P-solve 是否可复用现有稳定原语；
2. 标准眼中的 Paraxial surface 是否可通过当前 ZOS-API 正确枚举、切换并读取参数 header。

A.1 不解 Q，不调整 residual，不解除 TDD-999。

## 2. A.1 新增实现

### 2.1 `src/whole_eye_mvp/carrier_zos.py`

新增：

- `base_spec_for_id()`；
- `iol_ant_to_image_mm_for_base()`；
- `prepare_cornea_for_base()`；
- `insert_controlled_carrier()`；
- `solve_actual_eye_carrier_power()`；
- `choose_paraxial_surface_type()`；
- `probe_paraxial_reference_surface()`。

### 2.2 Base 轴向处理

两个 base 共同保持：

```text
post-cornea → STOP = 3.150 mm
post-cornea → IOL anterior = 4.500 mm
```

A0/B0/C0 角膜本身不因 base 改变。

因此 ATC-M3 相对 LB 的轴向差异在本阶段只通过 IOL anterior → fixed retina 距离体现：

```text
LB_AL2395:      23.950 - 0.500 - 4.500 = 18.950 mm
ATC_M3_AL24477: 24.477 - 0.500 - 4.500 = 19.477 mm
```

程序只改 cornea-only 文件中 IOL reference → IMAGE 的厚度；角膜面型、STOP 和 IOL anterior landmark 均保持不变。

### 2.3 P-solve

代表性输入先固定为 A0。

对 LB 和 ATC-M3 分别：

1. 加载同一 A0 cornea-only `.zmx`；
2. 按 base 调整 fixed-retina 轴向距离；
3. 插入 `CONTROLLED_IOL_CARRIER_546_v1`；
4. 保持前后表面 Q=0；
5. EPD3 下用现有 Wavefront Quick Focus radius bisection；
6. 固定 retina 不动，求 symmetric radius；
7. 由相同 `n/CT/medium` 的 thick-lens 公式记录 equivalent power；
8. 保存为 diagnostics，仅供后续 Web 复核。

本阶段不声称这两个 P 就是最终 18-carrier lock；它们只证明 P-solve 路径在两个 base 上成立。

## 3. Paraxial capability probe

程序加载只读 `STD_IOL_EYE_2024`，不覆盖源文件。

执行：

1. 枚举 `ZOSAPI.Editors.LDE.SurfaceType`；
2. 优先选择 exact `Paraxial`，否则选择名称中包含 `paraxial` 的确定性 fallback；
3. 在内存中的 IOL reference surface 上执行 `ChangeType`；
4. 读取 `Par1..Par16` 非空 header；
5. 把 enum 名、选中 surface type、parameter headers 和任何异常写入 JSON evidence。

本阶段**不猜测**哪个参数是 power，也不写 Q solver。真正的 power 参数映射必须由此次实机 readback 决定。

## 4. 运行命令

先同步分支并执行离线回归：

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

全部 PASS 后运行：

```text
uv run python scripts/probe_task_007_carrier_p_paraxial.py \
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx"
```

默认读取：

```text
diagnostics/task005d/corneas/CORNEA_A0.zmx
models/assets/STD_IOL_EYE_2024.zmx
```

输出：

```text
diagnostics/task007/carrier_p_paraxial_probe/
  TASK007_P_LB_A0.zmx
  TASK007_P_ATC_M3_A0.zmx
  TASK_007_CARRIER_P_PARAXIAL_PROBE.json
```

## 5. PASS 条件

### P-solve

两个 base 都必须：

- 成功生成 7-surface candidate；
- anterior/posterior radius 为等幅反号；
- P-solve 阶段两面 Q 都为 0；
- IOL material readback `n≈1.460`；
- fixed axial length 分别保持 `23.950/24.477 mm`；
- Quick Focus residual shift 在既有 `0.001 mm` gate 内；
- 输出 finite power/radius；
- source/candidate SHA-256 可回溯。

### Paraxial capability

必须：

- 找到一个实际 Paraxial surface type；
- `ChangeType` 成功；
- 返回 parameter header 列表；
- 不修改/保存 locked standard-eye source。

若 Paraxial surface 不存在、类型切换失败或 header 无法读取：A.1 STOP，回 Web 分析，不自行以其他物理镜片替代。

## 6. 明确禁止

A.1 不得：

- 批量解全部 18 个 carrier；
- 解任何 `Q_k(P)`；
- 用 spherical `Q=0` carrier 当 ZERO_HOA；
- 改 WFS/RAD/HOA residual seed；
- rescale residual amplitude；
- 建 Grid Sag；
- 做 low/median/high residual calibration；
- 创建 formal residual/carrier/pair lock；
- 解除 TDD-TEST-999；
- 进入 TASK-008/Run72。

## 7. 回传内容

至少回传：

1. actual HEAD / git status；
2. offline tests/ruff/compileall/lock check；
3. 两个 P-solve 的 radius、power、focus shift、axial length、candidate SHA-256；
4. Paraxial surface enum 中相关名称；
5. selected surface type；
6. `Par1..Par16` 非空 headers；
7. capability `passed` 与 error；
8. report path / SHA-256；
9. OpticStudio/Zemax residual process count；
10. 明确确认 `q_solve_completed=false`、`tdd_999_cleared=false`。

完成后 STOP，返回 Web。