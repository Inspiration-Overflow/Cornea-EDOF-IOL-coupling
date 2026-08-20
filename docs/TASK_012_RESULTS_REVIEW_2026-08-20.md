# TASK-012 — Run72 结果独立审核

## 1. 审核状态

```text
document = TASK_012_RESULTS_REVIEW_2026-08-20
review_date = 2026-08-20
review_scope = TASK-012 offline analysis code + structured evidence + figure-generation contract
result = PASS_WITH_SCIENTIFIC_CAVEATS
opticstudio_rerun_required = false
```

本审核针对已冻结的 TASK-012 分析计划及其纯离线实现。审核目标是确认：正式 TASK-011 Run72 evidence 可在 Git checkout 中独立重建；censoring 未被静默当作精确值；36-pair factorial contrasts 与3×3耦合矩阵可重复生成；结果解释没有把确定性光学矩阵误写成随机临床样本，也没有为了得到更整齐的结论而修改冻结窗口或重跑 OpticStudio。

---

## 2. 审核来源

### 2.1 上游正式来源

```text
TASK-011 formal evidence commit =
f28b3032136aa28f54abb5fe5129765a125d3926

formal Run72 code commit =
01f13b768cf1eca361703469b2fdce3d21f3376d

run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
```

TASK-012 同时验证：

- 四个正式 evidence 文件的 repository-byte SHA256；
- TASK-011 evidence JSON 内记录的三个 Windows producer-export CSV SHA256；
- baseline / manifest / lock-set / settings / acquisition contract / pair-reference set；
- 72 configs、36 matched pairs、1080 through-focus rows；
- `acceptance_passed=true`、`run72_complete=true`、failed=0。

两层文件哈希不同源于 producer 输出与 Git text normalization 的字节差异。四个 evidence 文件在 `f28b303...` 与当前 branch 的 Git blob 已逐一确认完全相同，因此没有 TASK-011 evidence 内容漂移。

### 2.2 TASK-012 正式产物

```text
docs/evidence/task012/TASK_012_ANALYSIS_EVIDENCE.json
docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv
docs/evidence/task012/TASK_012_INTERACTION_CONTRASTS.csv
docs/evidence/task012/TASK_012_COUPLING_MATRIX.csv
docs/evidence/task012/figures/*.png
```

最终分析代码基线：

```text
analysis_code_commit = 330b59171e1dab2ea76d1425d56d8e5175d233ef
```

正式输出由专用 Web/CI 工作流生成并提交；没有调用 OpticStudio。

---

## 3. 计算与 provenance 审核

### 3.1 Reconstruction gate

通过。

```text
config rows = 72
unique matched pairs = 36
through-focus rows = 1080
rows/config = 15
formal paired-delta rows = 36
```

每个 pair 均由显式 `base_id / cornea_id / platform_id / pupil_mm` 列确定，并且恰有一条 MONO 与一条 EDOF。代码不通过拆分 `config_id`、`pair_key` 或 `carrier_id` 推断因素。

从 config-level evidence 独立重建8个 EDOF−MONO paired outcomes，并以 absolute tolerance `1e-12` 与正式 paired-delta CSV 对照；PASS。

从1080-row through-focus evidence 重新读取0 D MTFa，并按冻结梯形积分定义重建 `tf_mtfa_mean`；PASS。

### 3.2 Censor propagation

通过。

正式36 pairs：

```text
DOF50 exact = 31
DOF50 lower_bound = 5
DOF50 upper_bound = 0
DOF50 indeterminate = 0
peak-window-censored pairs = 8
```

5个 DOF50 lower-bound pairs 均由 EDOF far-side crossing 到达 +0.50 D 冻结边界、MONO exact 形成：

1. ATC + B0 + WFS-like + EPD3
2. LB + B0 + WFS-like + EPD3
3. ATC + C0 + HOA-like + EPD5
4. ATC + C0 + RAD-like + EPD5
5. LB + C0 + RAD-like + EPD5

8个 peak-window-censored pairs 均为 EPD5：

- ATC + A0 + HOA-like
- LB + A0 + HOA-like
- ATC + B0 + HOA-like
- LB + B0 + HOA-like
- ATC + B0 + RAD-like
- LB + B0 + RAD-like
- ATC + B0 + WFS-like
- LB + B0 + WFS-like

这些 pair 的 peak position、`DeltaF_residual` 为 boundary-limited；`distance_peak_mtfa` 只能解释为预注册 peak-search window 内的 observed peak MTFa。

### 3.3 DOF50 contrast interval

平台 contrast、角膜 contrast、difference-in-differences、pupil sensitivity 与 base-eye sensitivity 均使用区间代数传播 DOF50 bound。输出保留 `bound_status`、有限 lower/upper bound、source pair status。3×3 matrix 的四-strata DOF50 mean 也保留 bound status。

因此本审核没有把 `≥0.43 D` 之类的边界结果伪装成精确的 `0.43 D` 排名。

---

## 4. 3×3 主结果

以下均为 EDOF−MONO paired effect。四-strata均值只是当前2 base ×2 pupil确定性矩阵的描述性中心，不是总体参数估计。

### 4.1 A0

**WFS-like**：平均 `Delta DOF50 ≈ +0.087 D`，四 strata 均 exact；`Delta MTFa@0D ≈ -0.160`，`Delta TF mean ≈ +0.010`。表现为较温和的延焦，同时0 D质量下降，但全贯焦平均略有增加。

**RAD-like**：平均 `Delta DOF50 ≈ +0.147 D`，exact；`Delta MTFa@0D ≈ -0.197`，`Delta TF mean ≈ +0.018`。相对 WFS-like，延焦更大，同时距离质量代价也更大；全贯焦平均收益更明显。

**HOA-like**：平均 `Delta DOF50 ≈ +0.242 D`，但范围约 `-0.25 → +0.73 D`；`Delta MTFa@0D ≈ -0.322`，`Delta TF mean ≈ -0.053`。EPD3 延焦很强，而 EPD5 可接近零甚至反向；是最明显的 pupil-dependent quality redistribution。

### 4.2 B0

**WFS-like**：四-strata DOF50 mean 为 lower bound，`Delta DOF50 ≥ +0.245 D`。其中 EPD3 为 `≥+0.428 D`（ATC）和 `≥+0.463 D`（LB），而 EPD5 只有约 `+0.055 D` 和 `+0.034 D`。`Delta MTFa@0D` 四 strata 全负，平均约 `-0.151`；`Delta TF mean` 平均约 `+0.008`。

因此 B0×WFS-like 的主要延焦信号是真实且明显的，但它主要集中在 EPD3，不能概括为对大瞳孔同样稳定的优势。

**RAD-like**：平均 `Delta DOF50 ≈ +0.133 D`，全部 exact；EPD3 大约 `+0.175～+0.233 D`，EPD5 约 `+0.053～+0.070 D`。`Delta MTFa@0D ≈ -0.167`，`Delta TF mean ≈ +0.009`。相较 WFS-like，延焦较小但不受 DOF50 censor 限制。

**HOA-like**：平均 `Delta DOF50 ≈ +0.307 D` exact，但范围约 `-0.094 → +0.720 D`；`Delta MTFa@0D ≈ -0.263`，`Delta TF mean ≈ -0.049`。同样表现为 EPD3 强延焦、EPD5 延焦消失/反转，并伴随明显的全贯焦质量损失。

### 4.3 C0

**WFS-like**：平均 `Delta DOF50 ≈ +0.057 D`，exact；`Delta MTFa@0D ≈ -0.121`，`Delta TF mean ≈ +0.011`。延焦较温和，质量代价也相对较小。

**RAD-like**：四-strata mean 为 lower bound，`Delta DOF50 ≥ +0.257 D`；EPD3 约 `+0.200～+0.236 D`，EPD5 为 `≥+0.272 D`（LB）和 `≥+0.320 D`（ATC）。`Delta MTFa@0D ≈ -0.197`，`Delta TF mean ≈ +0.018`。

这是3×3矩阵中较稳定的“DOF-oriented coupling”之一：与 A0 相比，C0 对 RAD-like 的相对 DOF 增益在两种基础眼和两种瞳孔下均明显超过 WFS-like；但距离质量代价也相应更大。

**HOA-like**：四-strata mean 为 lower bound，`Delta DOF50 ≥ +0.449 D`，但范围高度不一致：EPD3约 `+0.65～+0.67 D`，ATC EPD5 为 `≥+0.510 D`，而 LB EPD5 约 `-0.037 D`。`Delta MTFa@0D ≈ -0.290`，`Delta TF mean ≈ -0.048`。

因此 C0×HOA-like 不能用单一均值概括；ATC 与 LB 在 EPD5 出现方向上非常重要的分离，是基础眼×瞳孔交互不可忽略的例子。

---

## 5. Cornea × Platform interaction

### 5.1 B0 × WFS-like

B0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences：

```text
LB  EPD3: >= +0.157 D
ATC EPD3: >= +0.195 D
LB  EPD5:    -0.210 D
ATC EPD5:    -0.097 D
```

WFS-vs-HOA 也表现同类变化：

```text
LB  EPD3: >= +0.152 D
ATC EPD3: >= +0.146 D
LB  EPD5:    -0.093 D
ATC EPD5:    -0.032 D
```

结论：**B0×WFS-like 存在明确的 EPD3-specific relative DOF advantage，但不是 pupil-invariant coupling。** 从 EPD3 到 EPD5，relative interaction 方向发生反转，因此不应写成“B0普遍最适合WFS-like”。

在 `Delta MTFa@0D` 上，B0×WFS-like 相对 RAD-like 在 EPD3 反而更负（约 -0.044～-0.048），EPD5 接近零；对 HOA-like 亦未形成稳定的距离质量优势。TF mean interaction 大多只有约千分位量级。

### 5.2 C0 × RAD-like

C0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences：

```text
LB  EPD3:    -0.066 D
ATC EPD3:    -0.073 D
LB  EPD5: <= -0.274 D
ATC EPD5: <= -0.170 D
```

由于这里定义为 WFS−RAD，持续负值表示 **C0 对 RAD-like 的相对 DOF coupling 高于 WFS-like**，且在 EPD5 更明显。这一方向在两种基础眼中一致。

但 `Delta MTFa@0D` 的同一个 interaction 却为正：

```text
LB  EPD3: +0.017
ATC EPD3: +0.012
LB  EPD5: +0.092
ATC EPD5: +0.079
```

即 C0 条件下，WFS-like 相对 RAD-like 保留了更多0 D质量。换言之，C0×RAD-like 的优势主要体现在 DOF，而不是“无代价地更优”。

TF mean interaction 在 EPD3 接近0；到 EPD5，WFS−RAD约 `-0.005～-0.006`，提示 RAD-like 的全贯焦平均收益略高。

### 5.3 HOA-like 的定位

HOA-like 在 EPD3 常产生矩阵中最大的 DOF50 expansion，但也伴随最大的0 D MTFa下降，并且 TF mean 多为负。EPD5 时其 DOF表现高度依赖 cornea/base，有时延焦几乎消失，有时仍很强。

因此 HOA-like 的主要特征不是“稳定最大焦深”，而是**强烈的质量再分配和显著 pupil/base dependence**。

---

## 6. Pupil 与基础眼

### 6.1 Pupil 是一阶解释变量

WFS-like、RAD-like、HOA-like 都存在 EPD3→EPD5 变化，但 HOA-like 最强；B0×WFS-like 的相对 DOF interaction 甚至发生符号反转。

因此3×3结果不允许先把 EPD3/EPD5 平均后再下结论。主论文结果应至少保留 Base×Pupil 四个 strata 或明确报告 sensitivity contrast。

### 6.2 Base eye 不能平均掉

多数 WFS-like/RAD-like 模式在 LB 与 ATC 间方向一致，但 C0×HOA-like×EPD5 是显著例外：ATC 的 DOF50 为 lower-bound 大正值，而 LB 为轻度负值。这个差异说明基础眼结构可以改变具体高阶机制与角膜原型的耦合方向。

所以当前两种基础眼是机制鲁棒性检查，不是两个可交换的“重复样本”。

---

## 7. 延焦—质量 trade-off

整体矩阵没有出现“焦深增加越多、所有质量指标也同步越好”的单调关系。

- WFS-like：通常是较小到中等延焦，0 D MTFa下降较温和，TF mean 常略正。
- RAD-like：通常比 WFS-like 有更大的 DOF收益，同时0 D损失更大；TF mean在多数条件仍略正。
- HOA-like：EPD3 DOF收益可最大，但0 D与TF mean代价也最大；EPD5表现不稳定。

因此主结果图应以 `Delta DOF50` 对 `Delta MTFa@0D` 和 `Delta TF mean` 的 trade-off 同时呈现，不使用单一综合总分。

peak-window-censored 结果在 `Delta distance_peak_mtfa` 图中已经使用独立标记，不能与未受限峰值直接作精确排名。

---

## 8. HOA mechanism readback

C40/C60/HOA RMS 的 EDOF−MONO变化显示三个 surrogate 的全眼高阶响应存在明显机制分离，但这些值依赖 pupil aperture。尤其 EPD5 下 RAD-like 与 WFS-like 的 HOA RMS 变化可随角膜原型显著变化。

因此：

- C40/C60/HOA RMS 用于解释机制，而不是单独定义“最佳平台”；
- 不跨 EPD3/EPD5 对 raw µm 做无条件平均；
- 不把实际眼 HOA readback 反写成 carrier physical lock。

---

## 9. 图表与代码审核

正式代码生成24张图：

```text
12 × Base/Pupil-stratified 3×3 heatmaps
4  × Base/Pupil-stratified through-focus panels
3  × trade-off plots
4  × pupil/base sensitivity plots
1  × C40/C60 mechanism map
```

图表生成逻辑经独立代码审核后做了两次收紧：

1. DOF50 heatmap 对 lower/upper bound 使用 `>=`/`<=` 语义；
2. distance-peak trade-off 单独标记 peak-window censor；DOF sensitivity 图按 bound status 分组；through-focus 面板标题标记 peak-window / DOF bound。

最终 Offline quality gate：pytest、ruff、compileall、uv lock 全 PASS。

本轮通过 GitHub 结构化接口核对图文件数量、名称、SHA 与生成代码；未进行本地 GUI 逐像素视觉排版验收。该限制只涉及图形排版美观度，不影响 CSV 数值、censor 状态、contrast 或 evidence provenance。

---

## 10. 审核结论

### 10.1 可以冻结的结果

1. TASK-012 reconstruction/provenance/censor gate PASS。
2. 3×3 coupling 的主要信号是真实的条件依赖 interaction，而不是单一平台主效应。
3. B0×WFS-like：EPD3 relative DOF coupling 强，但 EPD5 反转，属于 pupil-specific interaction。
4. C0×RAD-like：相对 WFS-like 的 DOF coupling 在两个 base、两个 pupil 下方向更稳定，但伴随更明显的0 D质量代价；属于 DOF-oriented trade-off，而非无条件优势。
5. HOA-like：最强的 extension/quality redistribution，并且 pupil/base dependence 最明显。
6. Base eye 和 pupil 均不可在主分析前平均掉。
7. 5个 DOF50结果只可按 lower bound 解释；8个 peak-window结果不能当作无限制真实峰值。

### 10.2 不支持的结论

当前结果不支持：

- “某一种角膜原型与某一种 EDoF IOL 绝对最佳”；
- “B0普遍最适合WFS-like”；
- “最大 DOF50 等同于最佳视觉质量”；
- 把2个模型眼当作临床随机样本做普通显著性推断；
- 根据本轮结果事后扩大 focus window 再重跑以消除 censoring；
- 从 surrogate 结果直接作商业 IOL 品牌级推荐。

### 10.3 是否需要新的 OpticStudio 运行

```text
No.
```

当前所有科学结论都可以由已接受 TASK-011 Run72 evidence 支持。Censoring 已有明确的 lower-bound/window-conditioned 解释，不构成补跑72矩阵的理由。

---

## 11. TASK-012 完成建议

从计算、provenance、censor propagation、factorial contrasts、3×3 matrix、through-focus、图表生成、unit test 和独立结果审核角度，TASK-012 已满足冻结计划的完成条件。

建议状态：

```text
TASK-012 = COMPLETE / REVIEW PASS
```

下一阶段可进入论文级 Results / Discussion 写作和对关键机制的定性—定量整合；PR #26 仍保持 Draft，是否合并另行决定。