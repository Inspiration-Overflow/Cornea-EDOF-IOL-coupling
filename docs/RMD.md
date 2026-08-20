# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 提供。

## Metadata

- document_id: `RMD-0001`
- version: `1.8`
- status: `active`
- source_docs: `URD-0001 v1.6`, `ADD-0001 v1.6`, `MDD-0001 v1.5`, `TDD-0001 v1.6`
- last_updated: `2026-08-20`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-011-run72`
- active_production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_frequency_scale: `paired_residual_free_MONO_EFFL`
- active_production_sampling: `128`
- completed_analysis_task: `TASK-012`
- next_science_phase: paper-level Results / Discussion

---

# 1. Dual-environment execution model

## Web

负责科学规范、冻结决策、Python 代码与测试、GitHub static review、structured evidence 审核、TASK-012 纯离线结果统计和图表，以及下一阶段论文级 Results/Discussion。

## Local Windows / ZCode

只负责必须由真实 OpticStudio/ZOS-API 给出的新事实。TASK-011 正式 Run72 已完成；TASK-012 完全基于冻结 evidence，不使用 OpticStudio。

## Cost-aware rule

- 已满足 gate 的代表配置不重复运行；
- 已接受的72-config Run72 不因少量 censoring 重跑；
- 不事后扩大冻结 focus/peak window 以获得更整齐结果；
- 普通统计、图表、provenance 和文档留在 Web；
- 新的本地 optical acquisition 必须有独立、明确的科学问题支持。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

unit tests 不依赖 OpticStudio。正式 scientific assets immutable；analysis provenance 必须版本化/hashable。

---

# 3. Completed build path

| Task | Status | Frozen output |
| --- | --- | --- |
| TASK-001 | complete | uv/src/tests/git skeleton |
| TASK-002 | complete | ZOS session lifecycle validated |
| TASK-003 | complete | domain + ProjectStore + hash/run provenance |
| TASK-004 | complete then migrated | current MTFa metric layer |
| TASK-005 | complete | LB/ATC、standard eye、A0/B candidates/C0 |
| TASK-006 | complete | B0.20 immutable lock |
| TASK-007 | complete | 18 P/Q、3 residuals、9 calibrations、TDD-999 cleared |
| TASK-008 | complete | 18 formal carrier locks、3 residual locks、72-config manifest |
| TASK-009 | complete | paired-MONO MFE MTFA production method + sampling 128 |
| TASK-011 | complete | formal Run72: 72 configs / 36 pairs / 1080 rows; Web review PASS |
| TASK-012 | complete | pure-offline reconstruction + censor-aware factorial analysis + 24 figures + result review PASS |

TASK-010 GUI 保持 optional，不是科学前置条件。

---

# 4. Frozen production identity

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
```

当前生产路径：

```text
frozen TASK-008 manifest
→ residual-free MONO EFFL once per matched pair
→ paired_residual_free_MONO_EFFL angular scale
→ ZosMtfaPairScaleAnalysisBackend
→ MFE MTFA Grid=1
→ 15-plane MTFa + fixed-frequency MTF + HOA readback
→ ConfigResult / matched deltas
```

TASK-009 以前已退休的 production routes 不再属于 active specs。

---

# 5. TASK-011 — Formal Run72 complete

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
pair_reference_set_sha256 = a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
acceptance_passed = true
run72_complete = true
```

Formal evidence：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

TASK-012 已独立重建这些 evidence；不需要 TASK-011 rerun。

---

# 6. TASK-012 — Offline analysis complete

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

分析代码基线：

```text
330b59171e1dab2ea76d1425d56d8e5175d233ef
```

派生 evidence commit：

```text
e92960b1f687ff844da07141f6e0aef50f32cea6
```

正式产物：

```text
docs/evidence/task012/TASK_012_ANALYSIS_EVIDENCE.json
docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv
docs/evidence/task012/TASK_012_INTERACTION_CONTRASTS.csv
docs/evidence/task012/TASK_012_COUPLING_MATRIX.csv
docs/evidence/task012/figures/
docs/TASK_012_RESULTS_REVIEW_2026-08-20.md
```

Acceptance：

```text
pairs = 36
contrasts = 1152
coupling cells = 9
figures = 24
DOF50 exact = 31
DOF50 lower_bound = 5
peak-window-censored pairs = 8
reconstruction_gate = PASS
censor_propagation = PASS
result_review = PASS_WITH_SCIENTIFIC_CAVEATS
opticstudio_used = false
```

TASK-012 source verification 同时保存：

1. Git checkout 可复算的 repository-byte SHA256；
2. TASK-011 evidence JSON 内记录的 producer-export CSV SHA256。

这两层 identity 不互相替代。

---

# 7. Frozen interpretation from TASK-012

所有 paired effect 均为 `EDOF - MONO`。

- **B0 × WFS-like**：EPD3 relative DOF coupling 明显；EPD5 interaction 反转，所以属于 pupil-specific interaction。
- **C0 × RAD-like**：相对 WFS-like 的 DOF coupling 跨两 base、两 pupil 方向更稳定，EPD5 更明显，但0 D质量代价更大。
- **HOA-like**：EPD3 常有最大 DOF extension，同时伴随最大0 D/全贯焦质量再分配；EPD5 对 cornea/base 高度敏感。
- Pupil 与 Base eye 都是一阶解释因素，不能在主分析前平均掉。
- 5个 DOF50 lower-bound 只按下限解释；8个 peak-window pair 只按 boundary/window-conditioned 解释。
- 当前确定性矩阵不支持单一“最佳组合”、传统随机样本显著性推断或品牌级临床推荐。

详见：

```text
docs/TASK_012_RESULTS_REVIEW_2026-08-20.md
```

---

# 8. Git checkpoints

```text
feat/task-009-fft-mtf-main
  TASK-009 complete / Run72 Web clearance

feat/task-011-run72
  TASK-011 runner + formal Run72 + evidence review
  TASK-012 analysis plan
  TASK-012 offline implementation/tests
  TASK-012 formal analysis evidence + 24 figures
  TASK-012 independent result review
  status/trace synchronization
```

PR #26 保持 Draft，除非另行授权改变状态或合并。

---

# 9. Next science phase

优先进入论文级 Results / Discussion：

1. 从冻结 TASK-012 evidence 形成论文主表与主结果段；
2. 选择最能表达3×3 coupling、pupil/base sensitivity 和 trade-off 的主图；
3. 把 B0×WFS-like、C0×RAD-like、HOA-like 结果与前期定性机制框架对照；
4. 明确 lower-bound、peak-window 和模型眼外推限制；
5. 如需新 sensitivity，只在现有 evidence 上做纯离线分析。

不需要新的 OpticStudio acquisition。

---

# 10. Current STOP conditions

1. TASK-005–009 frozen assets/method locks 不得修改；
2. TASK-008 manifest/hash/lock-set 不得因后续写作改变；
3. sampling lock 保持128；
4. 不恢复任何已退休的 pre-TASK009 production path；
5. 不使用 per-state/EDOF EFFL 改变 matched MONO/EDOF cpd 坐标；
6. 不因 peak/DOF censoring 扩大预注册窗口后补跑矩阵；
7. 不重新优化 B0.20 或 residual profiles；
8. 不把 `DeltaF_residual` 写入 carrier physical lock identity；
9. 不把 DOF50 lower bound 或 peak-window result 静默当精确值；
10. 不把确定性矩阵当随机临床样本做传统显著性检验；
11. 不为获得特定论文叙事事后改变主要 outcome、censor policy 或 interaction definition；
12. 新 evidence/code inconsistency 出现时先停止解释并做 Web review，不以 OpticStudio rerun 作为默认修复。
