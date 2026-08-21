# RMD 执行状态

> `RMD-0001 v1.8` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`feat/task-011-run72`
- TASK-005/006/007/008：完成并冻结
- TDD-999：cleared
- TASK-009：**COMPLETE**
- production sampling：**128，正式锁定**
- TASK-011 formal Run72：**COMPLETE / ACCEPTED / WEB REVIEW PASS**
- TASK-012：**COMPLETE / OFFLINE RECONSTRUCTION PASS / RESULT REVIEW PASS**
- TASK-012 OpticStudio：**未使用，也不需要补跑**
- TASK-010 GUI：可选，不是当前科学前置

## 不可变正式身份

```text
baseline_id = MVP_2026_v2
carrier_count = 18
residual_count = 3
nominal_config_count = 72
pair_key_count = 36

manifest_hash =
29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49

lock_set_hash =
b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 =
0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 =
f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
B0 = B0.20 immutable
```

TASK-011/TASK-012 对 TASK-005–009 scientific/method locks 只读。

---

## TASK-011 正式 Run72

```text
code_commit = 01f13b768cf1eca361703469b2fdce3d21f3376d
formal_evidence_commit = f28b3032136aa28f54abb5fe5129765a125d3926
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
completed_configs = 72
failed_configs = 0
matched_pairs = 36
through_focus_rows = 1080
pair_reference_records = 36
acceptance_passed = true
run72_complete = true
pair_reference_set_sha256 =
a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
```

正式文件：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

TASK-012 复核时明确拆分了两层文件身份。

### Git repository-byte SHA256

```text
TASK_011_RUN72_EVIDENCE.json
= d1b347cc221293fccd5a08679e8b6368788b22eecaa904f6b8f617a6296c50ee

TASK_011_RUN72_CONFIG_RESULTS.csv
= f51975b588bae3764806a7930fe6b49b0fc09f357d3ca9c11074fa20749cf615

TASK_011_RUN72_THROUGH_FOCUS.csv
= f2723a30e0629b6f0b27f8f4f73bc469f1ee7fee7fe3c62d2413c0d4a8eba2b6

TASK_011_RUN72_PAIRED_DELTAS.csv
= a6f0708e3339a6cec7b029f7d6675de291db4cea3162528d489189720c4598c5
```

### TASK-011 producer-export CSV SHA256

由正式 TASK-011 evidence JSON 在 Windows 生产端记录：

```text
CONFIG_RESULTS = 337628d95529a3711f36e7ea250ef435413d8f6aff11c25739e3c9b9ccc69dfa
THROUGH_FOCUS = cb4ece26a0a5d3a931db52a5f3b7e3325a99cbe26c9e175abd12bec5b7ec79da
PAIRED_DELTAS = 03dfe506566f83f6868c72890c042389ed8d0cd370255967fd1ff3b1ca25fa62
```

两层 SHA 不相等是 Git text normalization 后的字节差异。四个文件在 `f28b303...` 与当前 branch 的 Git blob 已逐一确认一致；没有 TASK-011 evidence 内容漂移。

---

## TASK-012 已完成

正式计划：

```text
docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md
```

正式实现：

```text
src/whole_eye_mvp/run72_analysis.py
src/whole_eye_mvp/run72_figures.py
scripts/analyze_task_012_run72.py
tests/unit/test_task012_run72_analysis.py
.github/workflows/task012-analysis.yml
```

正式分析代码基线：

```text
330b59171e1dab2ea76d1425d56d8e5175d233ef
```

派生 evidence 由专用 Web/CI 工作流生成并提交；当前 evidence commit：

```text
e92960b1f687ff844da07141f6e0aef50f32cea6
```

正式产物：

```text
docs/evidence/task012/TASK_012_ANALYSIS_EVIDENCE.json
docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv
docs/evidence/task012/TASK_012_INTERACTION_CONTRASTS.csv
docs/evidence/task012/TASK_012_COUPLING_MATRIX.csv
docs/evidence/task012/figures/*.png
```

结果审核：

```text
docs/TASK_012_RESULTS_REVIEW_2026-08-20.md
result = PASS_WITH_SCIENTIFIC_CAVEATS
```

### Reconstruction / analysis acceptance

```text
pair_count = 36
contrast_count = 1152
coupling_cell_count = 9
figure_count = 24
reconstruction_gate_passed = true
censor_propagation_passed = true
opticstudio_used = false

DOF50 exact pairs = 31
DOF50 lower-bound pairs = 5
peak-window-censored pairs = 8
```

最新 TASK-012 代码 gate：

```text
source head = 330b59171e1dab2ea76d1425d56d8e5175d233ef
GitHub Actions offline-quality run = 32345872258
pytest = 212 passed
ruff = PASS
compileall = PASS
uv lock = PASS
final offline gate = PASS
```

---

## TASK-012 科学结果状态

所有 paired effect 定义为 `EDOF - MONO`。

当前可冻结的描述性结论：

- **B0 × WFS-like**：EPD3 下存在明确 relative DOF advantage；EPD5 时 interaction 反转，因此属于 pupil-specific coupling，不是 pupil-invariant 优势。
- **C0 × RAD-like**：相对 WFS-like 的 DOF coupling 在两个基础眼和两个瞳孔下方向较稳定，EPD5 更明显；但伴随更大的0 D质量代价，是 DOF-oriented trade-off，不是无条件优势。
- **HOA-like**：EPD3 常出现最大 DOF expansion，同时有最大的0 D/全贯焦质量再分配；EPD5 时高度依赖 cornea/base，是最强 pupil/base-dependent mechanism。
- **Pupil 和 Base eye 均不可先平均掉**；C0×HOA-like×EPD5 是基础眼可改变效应方向的重要例子。
- 5个 DOF50 lower-bound pair 只作下限解释；8个 peak-window pair 的 peak/DeltaF 是边界受限，`distance_peak_mtfa` 只代表预注册窗口内观察峰值。
- 不支持“单一最佳角膜×IOL组合”、不支持把最大 DOF50 等同最佳整体质量，也不支持品牌级临床推荐。

---

## 下一执行

TASK-012 后不再需要新的光学 acquisition。下一阶段优先进入：

1. 论文级 Results：把36-pair、3×3 coupling、pupil/base sensitivity、censor-aware trade-off 写成正式结果；
2. Discussion：将 B0×WFS-like、C0×RAD-like、HOA-like quality redistribution 与前期定性机制假设对照；
3. 形成主表、主图筛选及论文级图注；
4. 必要时补充只基于现有 evidence 的 sensitivity/visualization，不重跑 OpticStudio；
5. TASK-010 GUI 继续保持可选。

PR #26 保持 Draft；不在本阶段自动合并。

---

## 当前 STOP

- 不修改 TASK-005–009 frozen assets/method locks；
- 不重跑正式72 configs；
- 不因 censored peak/DOF 事后扩大 focus/search span 并补跑矩阵；
- 不恢复任何已退休的 pre-TASK009 production path；
- 不使用 EDOF-state/per-state EFFL 改变 matched-pair production angular scale；
- 不修改 B0.20；
- 不重新优化 residual profile；
- 不把 `DeltaF_residual` 写入 carrier physical lock identity；
- 不把确定性36-pair矩阵直接当随机临床样本做传统显著性检验；
- 不把 DOF50 lower bound 或 peak-window result 静默当作精确值；
- 后续若 evidence/code inconsistency 出现，先停止解释并做 Web review，不把 OpticStudio rerun 当默认修复手段。
