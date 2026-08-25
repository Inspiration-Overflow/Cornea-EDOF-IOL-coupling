# 补充实验 OpticStudio 本地执行记录

## 状态

实验一和实验二均已在本地 OpticStudio 2026 R1.00 完成。结果文件位于原项目的 `project_mvp_2026_v2_zmx/diagnostics/supplemental_experiments` 目录；主分析目录未被覆盖。

ChatGPT Web 本轮没有返回可验证的代码提交或审查回执。以下代码和数值结果由当前分支的本地实现以及本地 OpticStudio 执行产生。没有在未取得新的消息确认时向网页会话发送代表用户的消息。

## 固定分析设置

- 波长：555 nm。
- 瞳孔：3 mm、5 mm。
- 贯焦网格：`+1.000 D` 到 `-5.000 D`，步长 `-0.125 D`，共 49 个平面。
- 远焦峰值搜索范围：`[-1.000 D, +1.000 D]`。
- MTF 频率网格：0 到 60 cpd，步长 1 cpd。
- 配置结果同时保留扩展窗口平均值和原始 `+0.50 D` 至 `-3.00 D` 窗口平均值，后者字段为 `tf_mtfa_mean_original_window`。
- 远焦峰值和阈值交点的删失标记保留在结果中；没有扩展 `-5.000 D` 以外的采样范围。

## 实验一：96 配置

实验一的正式结果目录：

`C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment1_96`

结果规模：

- 配置：96。
- MONO/EDOF 配对：48。
- 贯焦数据：4704 行，即 `96 × 49`。
- 本地采集校验：通过。

96 个配置的 OpticStudio 采集均已完成。首次运行在汇总阶段发现匹配配对校验仍使用默认 15 平面设置；因此保留已完成的 96 个配置结果，修正设置传递后重新构建汇总文件，没有重新计算光学结果。

文件：

- [实验一证据](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment1_96\SUPPLEMENTAL_EXPERIMENT_1_96_EVIDENCE.json)
- [配置结果](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment1_96\SUPPLEMENTAL_EXPERIMENT_1_CONFIG_RESULTS.csv)
- [贯焦结果](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment1_96\SUPPLEMENTAL_EXPERIMENT_1_THROUGH_FOCUS.csv)
- [配对差值](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment1_96\SUPPLEMENTAL_EXPERIMENT_1_PAIRED_DELTAS.csv)

实验一文件 SHA-256：证据 `01e53f7d7bd8b68ca97831d84846b426c9f3b4663b3c53be64cec8dd0551db25`，配置 CSV `0a04ca41e6b64f90a69f287f899711530dbddaf4b07b2c916c096ec9add8d1c2`，贯焦 CSV `112f1b4e5167dc70a5b3be3b82e3e5760ba6b93356e20146b283db7b874ac41f`，配对 CSV `05bbeb142c628c573996f49c3209a740154a67087f7a0f5f177f89c51108b6c6`。

## 实验二：C0 距离分量锚定

实验二的正式结果目录：

`C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment2_distance_anchor`

结果规模：

- 配置：24，即 `2 bases × 3 platforms × 2 optic states × 2 pupils`。
- MONO/EDOF 配对：12。
- 贯焦数据：1176 行，即 `24 × 49`。
- 校准记录：6，即 `2 bases × 3 platforms`。
- 本地采集校验：通过。

每一行配置结果均满足以下字段：

- `calibration_strategy=distance_component_anchored`。
- `near_add_d=1.75`。
- `near_add_zeroed_for_solve=True`。
- `carrier_frozen=True`。
- `near_add_restored=True`。
- 恢复近附加后 IOL 度数求解、重新定焦和载体优化次数均为 0。
- 每个配置均有 49 行贯焦数据。

实验路径使用 5 mm 的全眼角膜清孔径，同时保留 C0 Binary4 区域边界；这与 R6/R7 冻结几何一致。MONO 和 EDOF 使用相同 `carrier_key`，EDOF 只保留其自身延焦结构。

文件：

- [实验二证据](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment2_distance_anchor\SUPPLEMENTAL_EXPERIMENT_2_DISTANCE_ANCHOR_EVIDENCE.json)
- [配置结果](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment2_distance_anchor\SUPPLEMENTAL_EXPERIMENT_2_CONFIG_RESULTS.csv)
- [贯焦结果](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment2_distance_anchor\SUPPLEMENTAL_EXPERIMENT_2_THROUGH_FOCUS.csv)
- [配对差值](C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment2_distance_anchor\SUPPLEMENTAL_EXPERIMENT_2_PAIRED_DELTAS.csv)

实验二文件 SHA-256：证据 `cf3eda62385cdb89f637fc160b7caee43df2b3b7e304fa2c01e403af4237e665`，配置 CSV `063c3aebea019bac3b5ce7bad3039e274a0406e8a9822ded4a08d7256cf8b19a`，贯焦 CSV `aacff338a8f14b5f93dce863efce04d09b3fb0a583a7d32cbb2607898fb456d1`，配对 CSV `3cc62be81cf11001dfe7dd539d6ebe2bb229a08ae9c19ba91a27ac7969de440d`。

首次实验二尝试因恢复 C0 角膜时把半径 3.25 mm 的最后一个 Binary4 区域边界误用为全眼清孔径而停止。部分校准文件已保留在：

`C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\experiment2_distance_anchor_failed_geometry_20260825`

正式结果来自修正后的第二次运行。

## 联合派生分析

联合分析输出目录：

`C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\analysis_combined`

输出规模：

- `SUPPLEMENTAL_30CPD_THROUGH_FOCUS.csv`：4704 行。
- `SUPPLEMENTAL_COMMON_THRESHOLD.csv`：96 行。
- `SUPPLEMENTAL_DID.csv`：108 行。
- `SUPPLEMENTAL_PAIR_ANALYSIS.csv`：48 行。
- `SUPPLEMENTAL_DISTANCE_30CPD_THROUGH_FOCUS.csv`：1176 行。
- `SUPPLEMENTAL_DISTANCE_PAIR_ANALYSIS.csv`：12 行。
- `SUPPLEMENTAL_CALIBRATION_STRATEGY_COMPARISON.csv`：12 行，逐基础眼、平台、瞳孔比较整眼定标和距离分量锚定定标；包含 0 D 质量、峰值位置和质量、相对 30%/50%/70% 焦深、删失状态，以及 −1.25 D 至 −2.25 D 区间的局部最高 MTFa 和相对峰值比例。

联合分析目录：

`C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\analysis_combined`

四幅补充图已生成 PNG 和 PDF 两种格式，位于：

`C:\Users\golde\code\inspiration-overflow\Cornea-EDOF-IOL-coupling\project_mvp_2026_v2_zmx\diagnostics\supplemental_experiments\figures`

图件分别覆盖：48 个匹配配对的扩展窗口前后 ΔDOF50、相对阈值与共同参照阈值、C0 两种定标策略的代表性贯焦曲线、以及 12 个基础眼/平台/瞳孔分层的差中差耦合图。`SUPPLEMENTAL_FIGURE_MANIFEST.json` 记录了源数据哈希、行数和图件哈希。

共同阈值使用每个 base、pupil、mechanism 下 N0+MONO 的 50% 峰值作为参考。DID 和 DOF 汇总保留 `exact`、`lower_bound`、`indeterminate` 等状态以及远近端删失字段；删失结果没有被改写成精确数值。

## 代码和验证

本次收尾涉及：

- `src/whole_eye_mvp/analysis.py`：匹配配对校验支持自定义贯焦设置和峰值搜索窗口。
- `src/whole_eye_mvp/analysis_zos_r8_direct.py`：直接采集汇总将自定义设置传递到配对差值校验，并支持动态配置数、配对数和平面数。
- `scripts/run_supplemental_experiment2_distance_anchor.py`：距离分量锚定路径使用冻结的 5 mm 全眼清孔径。
- `scripts/analyze_supplemental_experiments.py`：生成两种定标策略对比表。
- `scripts/generate_supplemental_figures.py`：从已核验 CSV 生成四幅补充图及图件清单。
- `tests/unit/test_analysis.py`：增加 49 平面匹配配对回归测试。

验证命令：

```text
uv run pytest tests/unit/test_analysis.py tests/unit/test_analysis_zos_r8_direct.py -q
uv run python scripts/analyze_supplemental_experiments.py \
  --config-csv <experiment1_96/SUPPLEMENTAL_EXPERIMENT_1_CONFIG_RESULTS.csv> \
  --through-focus-csv <experiment1_96/SUPPLEMENTAL_EXPERIMENT_1_THROUGH_FOCUS.csv> \
  --distance-config-csv <experiment2_distance_anchor/SUPPLEMENTAL_EXPERIMENT_2_CONFIG_RESULTS.csv> \
  --distance-through-focus-csv <experiment2_distance_anchor/SUPPLEMENTAL_EXPERIMENT_2_THROUGH_FOCUS.csv> \
  --output-dir <analysis_combined>
```

两份证据文件已写入最终代码提交号 `24ab474ec0e2cb60091315e5cca66ca387f7ccb1`，并已重新计算 SHA-256。
