# TASK-012 — Run72 结果统计、耦合效应分解与科学解释

## 1. 文档状态

```text
task_id = TASK-012
analysis_plan_id = TASK012_RUN72_ANALYSIS_PLAN_2026-08-19
status = FROZEN_ANALYSIS_PLAN
original_freeze_date = 2026-08-19
provenance_clarification_date = 2026-08-20
execution_environment = Web / pure-Python offline
opticstudio_required = false
upstream_scientific_locks_mutable = false
```

本计划在读取正式 Run72 结果后、进行系统结果筛选和论文级解释前冻结。其目的不是重新定义 TASK-005～009 的科学模型，也不是重新计算 TASK-011 光学数据，而是规定如何从已经接受的 Run72 evidence 中形成可重复、censor-aware 的耦合分析。

2026-08-20 的 provenance 修订不改变任何 outcome、censor、contrast 或科学定义。CI 发现 TASK-011 在 Windows 端写出 CSV 后记录的 producer-export SHA256，与文件提交 Git 后在 Linux checkout 中可复算的 repository-byte SHA256 不同。进一步核对确认：四个 evidence 文件在 `f28b303...` 与当前 branch 的 Git blob 分别完全相同，因此不存在 TASK-011 evidence 内容漂移。TASK-012 从此明确保存并分别验证两层身份：

1. **repository-byte SHA256**：对当前 Git checkout 的实际字节可复算，用于 TASK-012 fail-closed source verification；
2. **TASK-011 recorded producer-export SHA256**：由正式 TASK-011 evidence JSON 在生产端记录，仅适用于三个 CSV，用于保留原始导出 provenance。

`TASK_011_RUN72_EVIDENCE.json` 没有在自身内容中记录 producer-side self-hash；因此不为它虚构第二个 producer hash。此前交接记录中的 JSON 自身 hash 不作为正式 producer identity。

若后续需要改变本计划中的主要 outcome、censor 处理、factorial contrast 定义或正式 source-of-truth，必须先显式修订本文件，不得在看到有利结果后静默改变分析规则。

---

## 2. 唯一正式数据源

TASK-012 只使用 GitHub commit：

```text
f28b3032136aa28f54abb5fe5129765a125d3926
```

中的四个 TASK-011 evidence 文件。

### 2.1 Repository-byte SHA256

这些值必须能从 TASK-012 的 Git checkout 直接复算：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
repository_sha256 = d1b347cc221293fccd5a08679e8b6368788b22eecaa904f6b8f617a6296c50ee

docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
repository_sha256 = f51975b588bae3764806a7930fe6b49b0fc09f357d3ca9c11074fa20749cf615

docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
repository_sha256 = f2723a30e0629b6f0b27f8f4f73bc469f1ee7fee7fe3c62d2413c0d4a8eba2b6

docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
repository_sha256 = a6f0708e3339a6cec7b029f7d6675de291db4cea3162528d489189720c4598c5
```

### 2.2 TASK-011 recorded producer-export SHA256

以下值来自正式 `TASK_011_RUN72_EVIDENCE.json`，记录生产端写出三个 CSV 时的字节身份：

```text
TASK_011_RUN72_CONFIG_RESULTS.csv
producer_export_sha256 = 337628d95529a3711f36e7ea250ef435413d8f6aff11c25739e3c9b9ccc69dfa

TASK_011_RUN72_THROUGH_FOCUS.csv
producer_export_sha256 = cb4ece26a0a5d3a931db52a5f3b7e3325a99cbe26c9e175abd12bec5b7ec79da

TASK_011_RUN72_PAIRED_DELTAS.csv
producer_export_sha256 = 03dfe506566f83f6868c72890c042389ed8d0cd370255967fd1ff3b1ca25fa62
```

TASK-012 不尝试要求 Git checkout 的 CSV 原始字节 SHA 与 producer-export SHA 相等；它必须同时验证 repository-byte hashes，以及 evidence JSON 内部是否仍然保存上述 producer-export hashes。

### 2.3 Git blob identity cross-check

已独立确认 `f28b303...` 与当前 branch 的四个文件 Git blob 完全相同：

```text
TASK_011_RUN72_EVIDENCE.json      blob = d1c9d41375e29de0bbf1cc749eb6742865744fb4
TASK_011_RUN72_CONFIG_RESULTS.csv blob = 8eab9e370714205c37dd35eca58fb052ed25e4d5
TASK_011_RUN72_THROUGH_FOCUS.csv  blob = 572123cd928512b90952a3aab3a762c1f330c973
TASK_011_RUN72_PAIRED_DELTAS.csv  blob = a26ca0a862c2a26aae326fa382a4e315b4ca96a6
```

正式 Run72 identity：

```text
code_commit = 01f13b768cf1eca361703469b2fdce3d21f3376d
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
completed_configs = 72
failed_configs = 0
matched_pairs = 36
through_focus_rows = 1080
pair_reference_records = 36
pair_reference_set_sha256 = a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
acceptance_passed = true
run72_complete = true
```

TASK-012 不从工作目录中的临时结果、手工抄录表格或新的 OpticStudio 运行补充正式结果。

---

## 3. 上游冻结条件

以下定义在 TASK-012 中只读：

```text
baseline_id = MVP_2026_v2
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
B0 = B0.20 immutable
```

`NOMINAL_MAIN_FFT_MTF_555_v2` 仅是历史 ID；当前生产数据由 MFE `MTFA Grid=1` 获得。TASK-012 不恢复任何 TASK-009 已退休的旧 production path。

---

## 4. 分析单元与因素

### 4.1 主分析单元

主分析单元为36个 matched MONO–EDOF pairs。

每个 pair 必须由完全相同的：

```text
Base × Cornea × Platform × Pupil
```

下的一条 MONO config 与一条 EDOF config 构成。

所有 paired effect 定义为：

\[
\Delta Y = Y_{EDOF} - Y_{MONO}
\]

正负方向在所有表格和图中保持一致，不针对不同 outcome 临时反转符号。

### 4.2 正式因素列

因素必须直接读取正式 CSV 的显式列，不得通过拆分 `config_id`、`pair_key` 或 `carrier_id` 推导因素。

正式列及允许值：

```text
base_id:
- LB_AL2395
- ATC_M3_AL24477

cornea_id:
- A0
- B0
- C0

platform_id:
- WFS
- RAD
- HOA

pupil_mm:
- 3.0
- 5.0

optic_state:
- MONO
- EDOF
```

`config_id`、`pair_key` 和 `carrier_id` 只用于身份、一致性和配对校验；它们不能成为因素解析的 source-of-truth。

完整 factorial 结构：

\[
2\times3\times3\times2=36\ matched\ pairs
\]

基础眼和瞳孔是正式因素，不先平均掉。

### 4.3 报告显示名映射

正式 evidence 原始值保持不变。论文、图表和解释层使用以下显示名：

```text
platform_id WFS -> WFS-like
platform_id RAD -> RAD-like
platform_id HOA -> HOA-like

pupil_mm 3.0 -> EPD3
pupil_mm 5.0 -> EPD5
```

分析表可同时保存 raw ID 与 reporting label；不得为了显示名方便而改写或重新生成 TASK-011 evidence。

---

## 5. 主要 paired outcomes

TASK-012 的主要 pair-level outcomes 固定为：

1. `delta_dof50_width_d`
2. `delta_distance_peak_mtfa`
3. `delta_mtfa_at_zero_d`
4. `delta_tf_mtfa_mean`
5. `delta_c40_um`
6. `delta_c60_um`
7. `delta_hoa_rms_um`
8. `delta_f_residual_d`

其中前四项描述延焦收益与光学质量代价，C40/C60/HOA RMS 用于机制解释，`DeltaF_residual` 用于描述 matched EDOF 相对 MONO 的残余焦移结果。

不得把 `DeltaF_residual` 写入 carrier physical lock identity。

---

## 6. Evidence 重建与一致性闸门

正式统计前必须先通过纯离线 reconstruction gate。

### 6.1 文件身份

脚本必须分别验证：

1. 四个正式 evidence 文件的 repository-byte SHA256 与第2.1节完全一致；
2. `TASK_011_RUN72_EVIDENCE.json` 内记录的三个 producer-export CSV SHA256 与第2.2节完全一致。

任一层不一致都停止正式分析。不得通过把其中一层改成另一层的值来“修复”验证。

### 6.2 Run-level metadata

必须从 `TASK_011_RUN72_EVIDENCE.json` 复核：

```text
phase = TASK-011-RUN72
code_commit = 01f13b...
baseline / manifest / lock-set = frozen exact IDs
analysis settings / acquisition contract / frequency scale = frozen exact IDs
production_sampling = 128
run_ids = [analysis-1cc1441dec4744a18d7ac73763507a6c]
resume_mode = false
selection_count = 72
pair_reference_count = 36
pair_reference_set_sha256 = frozen exact hash
completed_config_count = 72
failed_config_count = 0
run72_complete = true
acceptance_passed = true
accepted_completed_configs = 72
accepted_matched_pairs = 36
accepted_through_focus_rows = 1080
```

### 6.3 结构完整性

必须满足：

```text
config rows = 72
unique config_id = 72
unique pair_key = 36
MONO rows/pair = 1
EDOF rows/pair = 1
through-focus rows = 1080
through-focus rows/config = 15
paired-delta rows = 36
```

显式因素列的取值集合必须与第4节完全一致。构造 pair 时必须验证 MONO/EDOF 的 `base_id`、`cornea_id`、`platform_id`、`pupil_mm` 完全相同；不得混合 EPD3/EPD5 或 LB/ATC 后再构造 pair。

### 6.4 Paired delta 独立重建

从 `TASK_011_RUN72_CONFIG_RESULTS.csv` 按 pair_key 找到 MONO 与 EDOF，两侧直接计算第5节8个 delta。

重建值必须与 `TASK_011_RUN72_PAIRED_DELTAS.csv` 对应字段一致；默认数值核对容差：

```text
absolute tolerance = 1e-12
```

该 CSV 是正式 evidence 的组成部分，但不是 TASK-012 唯一 pair-level 数据源，因为它不携带 config-level censor flags。

### 6.5 Through-focus 独立重建

每个 config 必须具有冻结 defocus grid：

```text
+0.50, +0.25, 0.00, -0.25, ... , -3.00 D
```

从1080-row through-focus evidence：

- 读取0.00 D 行重建 `mtfa_at_zero_d`；
- 按 TDD 冻结定义使用 trapezoidal integration 重建 `tf_mtfa_mean`；
- 与72-config summary 对应值比较，默认 absolute tolerance = `1e-12`。

如果 reconstruction gate 失败，停止结果解释，优先检查 evidence 读取、字段映射和分析代码；不得默认通过重跑 OpticStudio 解决。

---

## 7. Censor-aware 规则

### 7.1 原则

Run72 computational acceptance 不等于所有派生标量都是无界精确值。TASK-012 必须保留并传播：

```text
peak_search_censored
dof50_far_censored
dof50_near_censored
```

pair-level censor 状态必须由 MONO 和 EDOF 两侧 config-level flags 构成，不能从 paired-delta CSV 猜测。

### 7.2 DOF50 config-level 状态

对每个 config：

```text
config_dof50_censored =
    dof50_far_censored OR dof50_near_censored
```

在冻结 through-focus 窗口内，只要一侧 crossing 未被观察到，当前 `dof50_width_d` 就是该 config 的 **lower bound**；若两侧均未 censor，则为 exact。

### 7.3 DOF50 pair-level effect status

保留简单布尔标志：

```text
pair_dof50_censored =
    MONO.dof50_far_censored OR
    MONO.dof50_near_censored OR
    EDOF.dof50_far_censored OR
    EDOF.dof50_near_censored
```

同时必须生成方向明确的：

```text
dof50_effect_status =
- exact
- lower_bound
- upper_bound
- indeterminate
```

因 `delta_dof50_width_d = EDOF - MONO`，状态规则固定为：

| EDOF width | MONO width | `delta_dof50_width_d` status |
| --- | --- | --- |
| exact | exact | `exact` |
| lower bound | exact | `lower_bound` |
| exact | lower bound | `upper_bound` |
| lower bound | lower bound | `indeterminate` |

其中：

- `lower_bound`：真实 delta 不小于报告值；
- `upper_bound`：真实 delta 不大于报告值；
- `indeterminate`：两侧都只有 lower bound，差值方向和精确幅度不能由这两个下限单独确定；
- 非 `exact` 结果不得与 exact pair 等价进行精确排名。

若 EDOF far side 达到 `+0.50 D` through-focus 边界而 MONO exact，则 EDOF `dof50_width_d` 及相应 `delta_dof50_width_d` 均按 `lower_bound` 处理。

当前正式 evidence 已知至少包括以下 EDOF far-side censored configs：

1. ATC + B0 + WFS + EPD3
2. LB + B0 + WFS + EPD3
3. ATC + C0 + HOA + EPD5
4. ATC + C0 + RAD + EPD5
5. LB + C0 + RAD + EPD5

TASK-012 仍由代码从正式 CSV 自动识别，不依赖这份手工列表作为计算来源。

### 7.4 DOF50 contrast / matrix bound propagation

对平台 contrast、角膜 contrast、difference-in-differences、pupil sensitivity、base-eye sensitivity，若 outcome 为 `delta_dof50_width_d`，必须把每个 source pair 先表示为区间：

```text
exact         -> [v, v]
lower_bound   -> [v, +inf)
upper_bound   -> (-inf, v]
indeterminate -> (-inf, +inf)
```

再按 contrast 系数进行区间线性运算。输出至少保留：

```text
bound_status
lower_bound (if finite)
upper_bound (if finite)
source_dof50_statuses
```

对3×3 coupling matrix，如计算四 strata 的 DOF50 均值，也必须同时报告该均值的 bound status 与有限边界；不能只给一个看似精确的平均数。

### 7.5 Distance peak / DeltaF_residual

定义：

```text
pair_peak_censored =
    MONO.peak_search_censored OR
    EDOF.peak_search_censored
```

当 `peak_search_censored=true` 且峰位在 `-0.50 D` 边界时：

- `distance_peak_retina_d` 解释为“最佳点达到/越过预注册搜索边界”；
- `delta_f_residual_d` 是 boundary-limited value；
- `distance_peak_mtfa` 是“预注册搜索窗口内观察到的峰值 MTFa”，不能断言为无限制全局峰值。

因此 peak-censored pair 在结果表和图中必须有显式标志。对于非 DOF50 outcome，不使用 `bound_status=exact` 表示 censor-free；DOF50 区间状态与 peak-window 状态必须分开表达。

### 7.6 不扩大窗口

TASK-012 不因 censoring 事后扩大 distance-peak search window 或 through-focus span，也不补跑完整72-config矩阵。

对于边界受限结果，优先使用方向性/下限解释，并结合 `mtfa_at_zero_d`、`tf_mtfa_mean` 和原始 through-focus 曲线。

---

## 8. 描述性 factorial contrasts

本项目当前矩阵是确定性光学模拟，不把36个 pair 视为随机抽样临床样本。默认不做传统 ANOVA p-value 或基于独立同分布样本假设的显著性推断。

### 8.1 平台 contrasts

在固定 `Base × Cornea × Pupil` 条件下，比较：

```text
WFS - RAD
WFS - HOA
RAD - HOA
```

对第5节各 outcome 分别计算。

### 8.2 角膜 contrasts

在固定 `Base × Platform × Pupil` 条件下，比较：

```text
B0 - A0
C0 - A0
B0 - C0
```

### 8.3 Cornea × Platform coupling

“耦合/协同”不能仅由一个组合的绝对结果判断。正式 interaction 使用 difference-in-differences。

例如 B0 是否对 WFS 具有相对特异优势，可计算：

\[
[(B0-A0)_{WFS}] - [(B0-A0)_{RAD}]
\]

以及：

\[
[(B0-A0)_{WFS}] - [(B0-A0)_{HOA}]
\]

C0 × RAD、A0 × platform 等均使用同一结构。所有 interaction 首先在固定 Base 和 Pupil strata 内计算，再检查跨 strata 的方向稳定性。

### 8.4 Pupil sensitivity

固定 `Base × Cornea × Platform`：

\[
Sensitivity_{pupil}=\Delta Y_{EPD5}-\Delta Y_{EPD3}
\]

用于回答大瞳孔是否削弱、增强或改变某个耦合效应。

### 8.5 Base-eye sensitivity

固定 `Cornea × Platform × Pupil`：

\[
Sensitivity_{base}=\Delta Y_{ATC}-\Delta Y_{LB}
\]

用于识别基础眼结构是否改变效应方向、幅度或平台排序。

---

## 9. Through-focus shape 分析

1080-row evidence 不只用于复核 summary 标量，也作为正式形态分析来源。

### 9.1 原始 paired curves

对每个 matched pair，在相同 defocus grid 上直接绘制：

```text
MONO MTFa(F)
EDOF MTFa(F)
```

并可生成：

\[
\Delta MTFa(F)=MTFa_{EDOF}(F)-MTFa_{MONO}(F)
\]

不对焦轴做事后平移以“对齐峰值”。

### 9.2 分层查看

主图保留：

- Cornea × Platform；
- EPD3 vs EPD5；
- LB vs ATC；
- MONO vs EDOF paired relation。

目标是区分：

- 真正的焦深扩展；
- 距离峰下移；
- 峰值压低后的质量再分配；
- 大瞳孔下出现的机制变化。

固定频率 `MTF10...MTF60` 可用于辅助解释具体频率行为，但不替代 MTFa 主分析，也不新增新的 production metric definition。

---

## 10. 3×3 Cornea × Platform 耦合矩阵

最终核心汇总结构：

```text
             WFS-like   RAD-like   HOA-like
A0
B0
C0
```

每个格子必须保留四个 `Base × Pupil` strata，而不是先压缩成单一分数。

每格至少报告：

- `Delta DOF50` 四 strata 值及 censor/bound 状态；
- `Delta mtfa_at_zero_d`；
- `Delta tf_mtfa_mean`；
- `Delta distance_peak_mtfa` 及 peak-censor 状态；
- EPD3→EPD5 sensitivity；
- LB→ATC sensitivity；
- interaction contrast 方向；
- C40/C60/HOA mechanism summary；
- 方向一致性（例如同号 strata 数/4）；
- 是否 boundary-limited。

如果给出四 strata 的连续值中心/范围：

- DOF50 中心值必须附带区间 status；
- C40/C60/HOA RMS 不跨 EPD3/EPD5 做无条件 raw-µm 平均，因为它们是 pupil-aperture-specific；
- 其他 outcome 的 mean/min/max 仅作为当前确定性矩阵的描述性汇总，不表示总体参数估计。

可为了阅读方便给出低/中/高的**研究内部相对分类**，但：

1. 不能把它写成临床阈值；
2. censoring 使精确排序不成立时应写 `boundary-limited`，不强行分级；
3. 不生成把延焦收益、距离质量代价、pupil/base stability 压成一个总分的综合评分。

---

## 11. 主图表

优先生成：

1. **3×3 pair-effect heatmap**：分别显示 `Delta DOF50`、`Delta mtfa_at_zero_d`、`Delta tf_mtfa_mean`；按 Base × Pupil strata 分开或显式保留四 strata；censored cells 显式标注。
2. **Through-focus MTFa curves**：按 Cornea × Platform 组织，MONO/EDOF 成对显示；Base/Pupil 分层。
3. **Trade-off plots**：
   - x = `Delta DOF50`
   - y = `Delta mtfa_at_zero_d`
   - 第二张 y = `Delta tf_mtfa_mean`
   - `Delta distance_peak_mtfa` 作为补充图，peak-censored 点使用独立 marker/annotation。
4. **Pupil sensitivity plot**：显示 EPD3→EPD5 的 paired effect 变化。
5. **Base-eye sensitivity plot**：显示 LB→ATC 的 matched interaction。
6. **C40/C60 mechanism map**：把 residual mechanism 与实际全眼 HOA 变化联系起来。

主结果图不得隐藏 censoring，也不得通过只展示“最好看的” strata 形成选择性叙事。

---

## 12. 代码实现边界

TASK-012 优先使用现有 Python 依赖：

```text
standard library csv/json/hashlib/pathlib
numpy
matplotlib
```

当前不因该分析新增 pandas 依赖，除非后续出现明确而必要的功能需求。

正式实现：

```text
src/whole_eye_mvp/run72_analysis.py
scripts/analyze_task_012_run72.py
tests/unit/test_task012_run72_analysis.py
```

正式产物：

```text
docs/evidence/task012/TASK_012_ANALYSIS_EVIDENCE.json
docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv
docs/evidence/task012/TASK_012_INTERACTION_CONTRASTS.csv
docs/evidence/task012/TASK_012_COUPLING_MATRIX.csv
docs/evidence/task012/figures/
```

正式分析 evidence 必须记录：TASK-011 source commit、四个 repository-byte SHA256、TASK-011 evidence JSON 中三个 producer-export SHA256、分析代码 commit、analysis-plan identity/hash 和输出文件 hashes。输出 evidence 不保存本机绝对路径。

---

## 13. 单元测试要求

至少覆盖：

1. exact 72-config completeness；
2. exact 36-pair completeness；
3. exact 1080 through-focus rows / 15 rows per config；
4. factors 只从显式列读取且允许取值 exact；
5. 每 pair exactly one MONO + one EDOF；
6. no duplicate config/pair result；
7. no accidental EPD3/EPD5 mixing；
8. no accidental LB/ATC mixing；
9. paired delta reconstruction 与正式 CSV 一致；
10. censor propagation 正确；
11. DOF50 exact/lower/upper/indeterminate truth table；
12. DOF50 signed contrast interval oracle；
13. `mtfa_at_zero_d` 从 through-focus row 可重建；
14. `tf_mtfa_mean` 从 through-focus data 可重建；
15. interaction/difference-in-differences 数学 oracle；
16. pupil/base sensitivity 数学 oracle；
17. repository-byte evidence SHA mismatch 必须 fail-closed；
18. producer-export SHA metadata mismatch 必须 fail-closed；
19. TASK-011 run-level metadata mismatch 必须 fail-closed；
20. reporting label 不改写 raw factor IDs；
21. coupling matrix DOF50 mean 保留 bound status；
22. 输出 evidence 不泄漏本机 absolute path。

所有这些测试必须可以在无 OpticStudio 环境下执行。

---

## 14. 科学解释顺序

通过 reconstruction gate 后，结果叙事按以下顺序形成：

1. 平台稳定主效应：是否存在跨角膜、瞳孔和基础眼相对稳定的延焦—质量特征；
2. Cornea × Platform interaction：是否存在 cornea-specific coupling；
3. B0 × WFS-like：是否有相对于其他平台的特异 interaction，而不仅是绝对 DOF50 较大；
4. C0 × RAD-like：是否存在稳定的相对适配信号；
5. HOA-like：是否表现为较强延焦与较高距离/平均质量代价的质量再分配；
6. Pupil：EPD5 是否改变效应大小或平台排序；
7. Base eye：LB/ATC 是否改变 interaction 方向或排序；
8. Censoring：哪些结论只能给方向性、下限或 window-conditioned 解释。

必须区分：

```text
stable main effect
condition-dependent interaction
boundary-limited result
window-conditioned peak result
```

不把描述性信号提前写成临床推荐。

---

## 15. STOP 条件

TASK-012 中以下情况必须停止并返回 Web review：

- 四个正式 TASK-011 evidence 文件的 repository-byte hash 不一致；
- TASK-011 evidence JSON 中三个 producer-export CSV hash 不一致；
- TASK-011 evidence JSON 的 run-level identity/provenance 不一致；
- 72/36/1080 completeness 不成立；
- paired delta 不能从 config summary 重建；
- through-focus summary 不能按冻结定义重建；
- censor flags 无法无歧义传播；
- 因素解析导致 Base/Pupil 混配；
- DOF50 bound 在 contrast 或 matrix 汇总中被静默当作 exact；
- 需要改变 TASK-005～009 scientific/method locks 才能继续；
- 需要改变预注册 peak/DOF focus windows 才能得到希望的结果；
- 分析代码为了得到特定结论而改变 outcome 或 interaction 定义。

上述失败的默认响应是检查 evidence 和纯 Python 分析代码。没有新的科学证据时，不启动 OpticStudio rerun。

---

## 16. TASK-012 完成判据

TASK-012 只有在以下项目全部完成后才能标记 complete：

```text
repository source evidence identity verified
producer-export provenance verified
run-level metadata verified
reconstruction gate PASS
censor propagation PASS
36-pair analysis complete
factorial contrasts complete
through-focus shape analysis complete
3x3 coupling matrix complete
main figures complete
unit tests PASS
code review PASS
document/result review PASS
analysis evidence hashed and committed
```

完成后才进入论文级 Results / Discussion 的正式写作与更高层次结论冻结。