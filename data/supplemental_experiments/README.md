# 补充实验结果数据

本目录保存补充实验的正式结果文件，来自 OpticStudio 实际运行和统一分析脚本。

## 文件结构

- `experiment1_96/`：实验一的 96 配置结果、扩展贯焦数据和 48 个匹配配对结果。
  - `SUPPLEMENTAL_EXPERIMENT_1_CONFIG_RESULTS.csv`：96 行配置级结果。
  - `SUPPLEMENTAL_EXPERIMENT_1_THROUGH_FOCUS.csv`：4704 行贯焦结果，96 × 49 个焦点平面。
  - `SUPPLEMENTAL_EXPERIMENT_1_PAIRED_DELTAS.csv`：48 行 MONO/EDOF 匹配配对差值。
  - `SUPPLEMENTAL_EXPERIMENT_1_96_EVIDENCE.json`：执行参数、配置计数、网格和文件哈希。
- `experiment2_distance_anchor/`：实验二的 24 配置结果、距离分量锚定定标记录和 12 个匹配配对结果。
  - `SUPPLEMENTAL_EXPERIMENT_2_CONFIG_RESULTS.csv`：24 行配置级结果。
  - `SUPPLEMENTAL_EXPERIMENT_2_THROUGH_FOCUS.csv`：1176 行贯焦结果，24 × 49 个焦点平面。
  - `SUPPLEMENTAL_EXPERIMENT_2_PAIRED_DELTAS.csv`：12 行 MONO/EDOF 匹配配对差值。
  - `SUPPLEMENTAL_EXPERIMENT_2_DISTANCE_ANCHOR_EVIDENCE.json`：定标约束、执行参数、配置计数和文件哈希。
- `analysis_combined/`：合并后的统一衍生结果。
  - `SUPPLEMENTAL_PAIR_ANALYSIS.csv`：实验一 48 个匹配配对的 30/50/70% 焦深和删失状态。
  - `SUPPLEMENTAL_COMMON_THRESHOLD.csv`：96 个配置的共同参照阈值结果。
  - `SUPPLEMENTAL_30CPD_THROUGH_FOCUS.csv`：实验一 30 cpd 贯焦结果。
  - `SUPPLEMENTAL_DID.csv`：差中差耦合结果，含删失状态。
  - `SUPPLEMENTAL_DISTANCE_PAIR_ANALYSIS.csv`：实验二 12 个匹配配对结果。
  - `SUPPLEMENTAL_DISTANCE_30CPD_THROUGH_FOCUS.csv`：实验二 30 cpd 贯焦结果。
  - `SUPPLEMENTAL_CALIBRATION_STRATEGY_COMPARISON.csv`：两种定标策略的 12 行配对比较。
- `figures/`：四类补充图件的 PNG/PDF 文件及图件清单。

实验一使用 `+1.00 D` 至 `-5.00 D`、`0.125 D` 步长的 49 点网格；配置级结果同时保留原始 `+0.50 D` 至 `-3.00 D` 窗口平均值。实验二恢复 `+1.75 D` 近附加后没有再次求解 IOL 度数、重新定焦或优化载体。

删失状态在原始、配对和衍生结果中继续保留，没有转换成精确数值。首次实验二的失败几何校准目录和逐配置临时文件不属于正式结果，未纳入本目录。

执行过程和完整哈希记录见 [OpticStudio 执行记录](../../docs/SUPPLEMENTAL_EXPERIMENT_OPTICSTUDIO_RUN_2026-08-25.md)。
