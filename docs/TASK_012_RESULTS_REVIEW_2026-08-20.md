# TASK-012 — Run72 结果独立审核

## 1. 审核状态与 QA 更正

```text
document = TASK_012_RESULTS_REVIEW_2026-08-20
review_date = 2026-08-20
review_scope = TASK-012 offline analysis code + structured evidence + figure-generation contract
result = PASS_WITH_SCIENTIFIC_CAVEATS
opticstudio_rerun_required = false
structured_evidence_changed = false
```

本审核针对已冻结的 TASK-012 分析计划及其纯离线实现。正式 source of truth 是 `docs/evidence/task012/` 下的结构化 CSV/JSON 与其分析代码，而不是本文中的人工摘要。

### QA correction note

在进入论文撰写前的 manuscript-prep QA 中发现，本文件早期版本第4节以后存在若干**人工转录错误**：部分3×3均值与 `TASK_012_COUPLING_MATRIX.csv` 不一致，并有 `ΔTF MTFa mean` 正负号抄反。经逐项回查，错误仅存在于人工结果摘要；`TASK_012_ANALYSIS_EVIDENCE.json`、三个正式 CSV、24 张图及分析代码均未发生改变，也不需要重新计算 TASK-011 或调用 OpticStudio。

本版本的数值结论重新直接取自：

```text
docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv
docs/evidence/task012/TASK_012_INTERACTION_CONTRASTS.csv
docs/evidence/task012/TASK_012_COUPLING_MATRIX.csv
```

后续论文 Results/Discussion 必须继续以这些结构化 evidence 为依据，不从旧人工摘要反向取数。

---

## 2. 正式来源与重建状态

```text
TASK-011 formal evidence commit = f28b3032136aa28f54abb5fe5129765a125d3926
formal Run72 code commit = 01f13b768cf1eca361703469b2fdce3d21f3376d
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
TASK-012 analysis code commit = 330b59171e1dab2ea76d1425d56d8e5175d233ef
TASK-012 formal evidence commit = e92960b1f687ff844da07141f6e0aef50f32cea6
```

重建 gate 通过：72 configs、36 matched MONO–EDOF pairs、1080 through-focus rows、15 rows/config。8个 paired outcomes 均由 config-level evidence 独立重建并以 `1e-12` absolute tolerance 对照正式 paired-delta evidence；0 D MTFa 与贯焦平均 MTFa 也从1080-row through-focus evidence 重新计算并通过。

Censor propagation 通过：

```text
DOF50 exact = 31
DOF50 lower_bound = 5
peak-window-censored pairs = 8
```

5个 DOF50 lower-bound pairs 为：ATC+B0+WFS-like+EPD3、LB+B0+WFS-like+EPD3、ATC+C0+HOA-like+EPD5、ATC+C0+RAD-like+EPD5、LB+C0+RAD-like+EPD5。8个 peak-window-censored pairs 均位于 EPD5；其 distance peak 与 `ΔF_residual` 只按预注册窗口内观察值解释。

---

## 3. 3×3 耦合矩阵的结构化结果

以下均为 `EDOF − MONO`。四-strata均值只描述当前 2 base × 2 pupil 确定性矩阵，不是总体参数估计；带 `≥` 的 DOF50 均值是下限。

| Cornea × Platform | ΔDOF50 mean (D) | ΔMTFa@0D mean | ΔTF MTFa mean | 关键异质性 |
| --- | ---: | ---: | ---: | --- |
| A0 × WFS-like | +0.137 exact | -0.120 | -0.0108 | 4/4 DOF正向 |
| A0 × RAD-like | +0.107 exact | -0.168 | -0.0150 | 4/4 DOF正向 |
| A0 × HOA-like | +0.194 exact | -0.320 | -0.0524 | EPD3约+0.63～+0.66，EPD5约-0.23～-0.28 |
| B0 × WFS-like | ≥+0.227 | -0.139 | -0.0112 | EPD3 ≥+0.432/≥+0.462；EPD5 +0.034/-0.021 |
| B0 × RAD-like | +0.185 exact | -0.166 | -0.0151 | 4/4 DOF正向，约+0.136～+0.221 |
| B0 × HOA-like | +0.241 exact | -0.287 | -0.0506 | EPD3约+0.73，EPD5约-0.23～-0.27 |
| C0 × WFS-like | +0.127 exact | -0.118 | -0.0083 | 4/4 DOF正向 |
| C0 × RAD-like | ≥+0.243 | -0.216 | -0.0092 | 4/4 DOF正向；两种 EPD5 均为 lower bound |
| C0 × HOA-like | ≥+0.409 | -0.345 | -0.0555 | EPD3约+0.66～+0.68；LB EPD5 -0.097，ATC EPD5 ≥+0.392 |

矩阵级别有三个稳定事实：

1. `ΔDOF50 > 0` 出现在 30/36 pairs，`< 0` 出现在 6/36；延焦效应普遍存在但并非无条件。
2. `ΔMTFa@0D < 0` 为 36/36。
3. `ΔTF MTFa mean < 0` 为 36/36；窗口内 observed distance-peak MTFa 也为 36/36 下降，其中8 pair为 peak-window-conditioned。

因此当前冻结模型最稳定的总体现象是**延焦—光学质量交换**：EDOF residual 往往扩大 DOF50，但相对 matched MONO 在固定0 D和完整预注册贯焦窗口内的平均 MTFa 均下降。不存在“延焦越大、全窗质量也越高”的单调优势。

---

## 4. Cornea × Platform interaction

### 4.1 B0 × WFS-like：明确的 EPD3-specific relative DOF coupling

B0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences：

```text
LB   EPD3: ≥ +0.157 D
ATC  EPD3: ≥ +0.195 D
LB   EPD5:   -0.210 D
ATC  EPD5:   -0.097 D
```

WFS-vs-HOA 也有相同方向变化：

```text
LB   EPD3: ≥ +0.152 D
ATC  EPD3: ≥ +0.146 D
LB   EPD5:   -0.093 D
ATC  EPD5:   -0.032 D
```

这说明 B0 对 WFS-like 的**相对 DOF 优势只在 EPD3 稳定出现，并在 EPD5 反转**。因此不能表述为“B0普遍最适合WFS-like”，更准确的表述是 pupil-specific coupling。

同时，这一 DOF interaction 并没有转化为稳定的0 D质量优势。`ΔMTFa@0D` 上，B0 条件下 WFS 相对 RAD 的 interaction 在 EPD3 约为 -0.044～-0.048，说明其延焦收益伴随额外的固定焦面质量代价。

### 4.2 C0 × RAD-like：较稳定的 DOF-oriented coupling，但不是无代价优势

C0 相对 A0 的 WFS-vs-RAD DOF50 difference-in-differences：

```text
LB   EPD3:    -0.066 D
ATC  EPD3:    -0.073 D
LB   EPD5: ≤  -0.274 D
ATC  EPD5: ≤  -0.170 D
```

此 contrast 定义为 WFS−RAD，所以持续负值意味着 **C0 对 RAD-like 的相对 DOF coupling 高于 WFS-like**；这一方向在两种基础眼和两种瞳孔均一致，而且 EPD5 更突出。

但是同一 interaction 的 `ΔMTFa@0D` 为正：

```text
LB   EPD3: +0.0166
ATC  EPD3: +0.0119
LB   EPD5: +0.0918
ATC  EPD5: +0.0790
```

即在 C0 条件下，WFS-like 相对 RAD-like 保留更多0 D MTFa。故 C0×RAD-like 是**以更多固定焦面质量为代价换取更强 DOF 的耦合模式**，而不是总体光学质量上的无条件优越。

### 4.3 HOA-like：强延焦、强质量再分配、最强 pupil/base dependence

A0、B0、C0 的 HOA-like 在 EPD3 均可产生约 +0.63～+0.73 D 的 DOF50 扩展，但 A0/B0 在 EPD5 转为负值。C0×HOA-like 的 EPD5 又进一步发生基础眼分离：LB 为 -0.097 D，而 ATC 为 ≥+0.392 D。

与此同时，HOA-like 的3×3 cell 在 `ΔMTFa@0D` 和 `ΔTF MTFa mean` 上均显示矩阵中最大的质量下降量级。因此 HOA-like 更适合被定位为**高阶像差驱动的强质量再分配机制**，而不是“稳定最大焦深”的单指标优胜者。

---

## 5. Pupil 与基础眼

Pupil 是一阶解释变量，而不是可被平均掉的 nuisance factor。B0×WFS-like 的 relative DOF interaction 从 EPD3 到 EPD5 发生符号反转；A0/B0×HOA-like 也从 EPD3 强延焦转为 EPD5 负向。

基础眼同样不能作为可交换重复样本。最清楚的例子是 C0×HOA-like×EPD5：LB 与 ATC 的 DOF50 方向不同。因此主论文至少要在核心图或正文中保留 Base×Pupil 四个 strata；四-strata均值只能作为导航性描述。

---

## 6. 高阶像差机制读数

平台 surrogate 的 C40/C60 读数形成不同的瞳孔相关机制签名：

- **WFS-like**：EPD3 时 ΔC40约 +0.032 μm、ΔC60约 -0.017 μm；EPD5 时幅度明显减小，ΔC40约 +0.002 μm、ΔC60约 -0.0095 μm。
- **RAD-like**：EPD3 主要表现为较小正 ΔC40 与约 -0.09 μm ΔC60；EPD5 转为约 -0.129 μm ΔC40 与 +0.063 μm ΔC60。
- **HOA-like**：EPD3 约为 -0.067～-0.070 μm ΔC40 与 +0.171～+0.175 μm ΔC60；EPD5 幅度显著降低。

RAD-like 在 EPD5 的 net HOA RMS 尤其显示角膜依赖：B0 约 -0.092～-0.100 μm，C0 约 +0.127 μm，而 A0 接近零。该方向差异支持“角膜原型 × IOL机制”不是简单可加效应，而存在真实的耦合结构。

---

## 7. 科学解释边界

- 36 pairs 是确定性光学矩阵，不做普通随机样本 p-value 推断。
- 5个 DOF50 lower-bound effects 不参与伪精确排名；8个 peak-related effects 保持 window-conditioned。
- 不因 censoring 扩大预注册窗口后补跑，也不重新优化 B0.20 或 residual profiles。
- WFS-like / RAD-like / HOA-like 是机制 surrogate，不等同于任一商业 IOL；结果不支持商业产品排名。
- B0/C0 的耦合结果当前应作为**机制发现与可检验假设**，不能直接升级为临床选片建议。

## 8. 最终审核结论

```text
TASK-012 computation: PASS
structured evidence: PASS
censor propagation: PASS
manuscript-prep numerical QA: PASS after correction
scientific interpretation: PASS_WITH_SCIENTIFIC_CAVEATS
additional OpticStudio acquisition: NOT REQUIRED
```

TASK-012 的计算证据仍然成立。本次 QA 仅纠正人工结果摘要，没有修改任何正式结构化 evidence。后续可以进入论文级 Results/Discussion，但所有数值必须从正式 CSV/JSON 自动或逐项对照提取。