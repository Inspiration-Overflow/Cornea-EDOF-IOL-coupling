# 补充实验软件实现与本地执行手册

## 状态

本文档只描述补充实验的软件契约和本地执行前检查。它不包含 OpticStudio 数值结果，也不预设实验趋势。原有主分析保持不变。

实现文件：

- `src/whole_eye_mvp/supplemental_experiments.py`
- `scripts/analyze_supplemental_experiments.py`
- `tests/unit/test_supplemental_experiments.py`

## 已固定的实验边界

实验一的贯焦网格必须是：

```text
+1.000, +0.875, ..., 0.000, ..., -4.875, -5.000 D
步长 = -0.125 D
平面数 = 49
```

远焦峰值只在 `[-1.000, +1.000] D` 内搜索。峰值落在 `-1.000 D` 或 `+1.000 D` 时标记峰值删失。阈值交点采用已有 `dof_interval` 的线性插值；如果 `-5.000 D` 仍是阈值区间边界，报告边界删失，不扩大采样范围。

原 96 配置的因子必须完整覆盖：

```text
2 bases × 4 corneas (N0/A0/B0/C0)
× 3 IOL mechanisms (WFS/RAD/HOA)
× 2 pupils (3/5 mm)
× 2 optic states (MONO/EDOF)
= 96 configs = 48 matched pairs
```

新增距离成分锚定分支只覆盖 `C0` 中央近用径向多焦角膜：

```text
2 bases × 3 IOL mechanisms × 2 optic states × 2 pupils = 24 configs
```

`C0` 的中央近附加仍为 `+1.75 D`。距离成分锚定的实际流程必须在本地光学执行器中完成：

1. 仅在求解基础 IOL 度数和机制基础球差时把近附加临时置零；
2. 完成求解和机制校准后冻结 IOL 载体；
3. 恢复 `+1.75 D` 近附加；
4. 恢复后不得求 IOL 度数、自动对焦、重新定焦或优化载体；
5. MONO 和 EDOF 必须共享同一冻结 `carrier_key`，EDOF 只附加延焦结构。

代码用 `SupplementalConfig` 记录这些状态，并在 `validate_distance_component_anchored_plan()` 中拒绝违反状态的输入。`carrier_key` 必须由本地冻结资产提供；代码不会生成光学载体数值。

## 输入 CSV 最小字段

配置 CSV 至少包含：

```text
config_id,pair_key,base_id,cornea_id,platform_id,pupil_mm,optic_state,carrier_key
```

可选但在距离成分锚定分支中必须正确记录的字段：

```text
calibration_strategy
near_add_d
near_add_zeroed_for_solve
carrier_frozen
near_add_restored
post_restore_iol_power_solves
post_restore_refocus_count
post_restore_carrier_optimizations
```

贯焦 CSV 至少包含：

```text
config_id,defocus_d,mtfa,mtf30_cpd
```

也接受现有结果中的 `defocus_retina_d`、`mtfa_0_60_cpd`、`mtf30` 或 `mtfa30_cpd` 别名。`mtf30_cpd` 是固定 30 cycles/degree 的测量值；它是派生图的数据源，不是新的主要结局。

## 离线分析输出

运行：

```powershell
uv run python scripts/analyze_supplemental_experiments.py `
  --config-csv <96-config.csv> `
  --through-focus-csv <96-through-focus.csv> `
  --output-dir <output-dir>
```

主分支输出：

- `SUPPLEMENTAL_PAIR_ANALYSIS.csv`：48 个匹配配对，包含相对 30%/50%/70% 焦深、0 D 质量、远焦峰值、贯焦平均值及删失标记；
- `SUPPLEMENTAL_COMMON_THRESHOLD.csv`：以同一基础眼×瞳孔×机制层内 `N0 + MONO` 远焦峰值的 50% 为共同阈值；
- `SUPPLEMENTAL_30CPD_THROUGH_FOCUS.csv`：30 cycles/degree 贯焦曲线；
- `SUPPLEMENTAL_DID.csv`：A0、B0、C0 相对于 N0 的 EDOF−MONO 差中差，逐基础眼、瞳孔和机制计算。

如果已经有 24 配置的距离成分锚定输出，可以同时运行：

```powershell
uv run python scripts/analyze_supplemental_experiments.py `
  --config-csv <96-config.csv> `
  --through-focus-csv <96-through-focus.csv> `
  --distance-config-csv <24-distance-config.csv> `
  --distance-through-focus-csv <24-distance-through-focus.csv> `
  --output-dir <output-dir>
```

此时额外输出 `SUPPLEMENTAL_DISTANCE_PAIR_ANALYSIS.csv` 和 `SUPPLEMENTAL_DISTANCE_30CPD_THROUGH_FOCUS.csv`。脚本会拒绝非 `C0`、非 24 配置、缺少 MONO/EDOF 配对、载体不一致或恢复近附加后发生调整的输入。

## 删失规则

边界删失不是缺失值。代码保留边界状态；在差中差计算中，只要任一来源焦深有边界删失，结果就不会静默转成精确点估计。`lower_bound`、`bounded_interval` 或 `indeterminate` 等状态必须在输出表中保留。

## 本地 OpticStudio 执行前置条件

本地执行器在开始 96 或 24 配置前必须核对：

1. 使用当前冻结的模型眼、角膜、IOL 材料、厚度、位置、视网膜位置和瞳孔；
2. 不修改原有主分析资产和 `NOMINAL_MAIN` 设置；
3. 贯焦输出严格写出 49 个平面，且包含 0 D；
4. 峰值搜索窗口只使用 ±1 D；
5. 30 cpd 必须来自同一批贯焦采集；
6. 距离成分锚定分支在恢复近附加后记录零次 IOL solve、零次 refocus 和零次载体优化；
7. MONO/EDOF 的 carrier hash/key 相同，EDOF-only provenance 是唯一状态差异；
8. 每个配置保留真实模型、运行环境、载体和输入文件 hash；
9. 任何失败配置不得写成 completed；
10. 不因剩余删失自动扩展到 `-6/-8/-10 D`。

OpticStudio 运行、许可证和真实光学数据不由本模块模拟。没有真实导出的 CSV 时，不得运行分析脚本生成论文结果。

## 测试

纯单元测试不需要 OpticStudio：

```powershell
uv run pytest tests/unit/test_supplemental_experiments.py
uv run ruff check src/whole_eye_mvp/supplemental_experiments.py scripts/analyze_supplemental_experiments.py tests/unit/test_supplemental_experiments.py
```

测试覆盖 49 点网格、±1 D 峰值窗口、96/24 组合、冻结载体状态、恢复近附加后的禁止操作、三种相对阈值、共同阈值、30 cpd、差中差和边界删失传播。
