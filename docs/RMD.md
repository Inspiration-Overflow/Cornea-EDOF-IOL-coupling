# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 提供。

## Metadata

- document_id: `RMD-0001`
- version: `1.7`
- status: `active`
- source_docs: `URD-0001 v1.6`, `ADD-0001 v1.6`, `MDD-0001 v1.5`, `TDD-0001 v1.6`
- last_updated: `2026-08-19`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-011-run72`
- active_production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_production_sampling: `128`
- active_analysis_task: `TASK-012`
- active_analysis_plan: `docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md`

---

# 1. Dual-environment execution model

## Web

负责科学研究/规范/冻结决策、Python 主代码与测试、GitHub static review、结构化 evidence 审核、formal gate/clearance，以及 TASK-012 的纯离线结果统计和图表。

## Local Windows / ZCode

只负责必须由真实 OpticStudio/ZOS-API 给出的新事实：runtime/API 差异、`.zmx` 实机结果，以及未来确有科学必要的新增光学 acquisition。

TASK-011 正式 Run72 已完成。TASK-012 不需要 OpticStudio。

## Cost-aware handoff rule

本地 OpticStudio 任务成本高。TASK-009 corrected representative batch 已约32分钟，前一轮约55分钟。因此：

- 文档、provenance、普通 Python、unit regression、Run72 结果统计全部留在 Web/GitHub CI；
- 已满足科学 gate 的代表配置不重复运行；
- 已接受的 Run72 不因少量 censoring 重新运行；
- science definition 变化必须回 Web；
- 不用“保险起见”增加未预注册 sampling 层级、扩大 focus window 或重复 probe。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

unit tests 不依赖 OpticStudio。正式 scientific assets immutable；analysis provenance 必须版本化/hashable；formal lock 同 ID 不允许以不同科学内容覆盖。

TASK-012 新分析代码也必须满足上述离线 gate，并优先使用现有依赖，不为了普通 CSV 分析引入不必要的新依赖。

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
| TASK-009 | complete | paired-MONO MTFA production method + 128 formal sampling lock + Web provenance hardening |
| TASK-011 | complete | formal Run72: 72 configs / 36 pairs / 1080 through-focus rows; Web evidence review PASS |

TASK-010 GUI 仍为 optional integration，不是 TASK-012 前置条件。

TASK-008 identity 只读：

```text
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
```

---

# 4. TASK-009 final state

## 4.1 Production method

```text
frozen TASK-008 manifest
→ residual-free MONO EFFL once per matched pair
→ paired_residual_free_MONO_EFFL angular scale
→ ZosMtfaPairScaleAnalysisBackend
→ MFE MTFA Grid=1 / Data Type=0 / Wave1 / Field1
→ 15-plane MTFa + MTF10..60
→ HOA / footprint / entity invariants
→ ConfigResult
→ run_analysis_batch
→ matched pair deltas
```

Active identities：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
SHA256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL

TASK009_MFE_ZERN_HOA_555_v1
SHA256 = 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2

TASK009_PRODUCTION_SAMPLING_LOCK_v1
production_sampling = 128
production_sampling_locked = true
sampling_escalation_256_active = false
```

`AS_FftMtf`/`New_FftMtf()` production path retired。`NOMINAL_MAIN_FFT_MTF_555_v2` 名称中的 FFT 仅保留历史 hash continuity。Huygens、complex OTF 与 VSOTF 也不属于当前生产路线。

## 4.2 Corrected representative evidence

三个 frozen pair 在 corrected paired-MONO scale 下：128→256 convergence 全 PASS、repeat128 全 PASS、6-config `run_analysis_batch` integration 6/6 PASS、entity/ray-health PASS，且独立 fixed-frequency diagnostic PASS。无需256→512 escalation。

Evidence：

```text
commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd
JSON SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49
CSV SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
```

## 4.3 Run-level provenance hardening

`RunEnvironment` 非空保存 program/OpticStudio version、baseline、analysis settings、manifest、lock-set、acquisition contract ID/hash 与 frequency-scale mode。`run_analysis_batch()` 在 acquisition 前检查 backend 自报 acquisition ID/hash/scale 是否完全一致。

---

# 5. TASK-010 — GUI integration（可选）

TASK-010 只负责 GUI action dispatch、progress/log/failed-target rerun UI 与必要的最小 GUI smoke。

它不是 TASK-011 CLI Run72 的前置条件，也不是 TASK-012 结果分析的前置条件。当前科学优先级不因 GUI 推迟。

---

# 6. TASK-011 — Formal Run72 complete

TASK-011 的正式 runner：

```text
src/whole_eye_mvp/run72.py
scripts/run_task_011_run72.py
```

Web 代码基点：

```text
01f13b768cf1eca361703469b2fdce3d21f3376d
```

正式 evidence commit：

```text
f28b3032136aa28f54abb5fe5129765a125d3926
```

正式批次结果：

```text
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
completed config IDs = exact frozen 72
failed configs = 0
through-focus rows/config = 15
total through-focus rows = 1080
matched deltas = 36
pair-reference records = 36
pair_reference_set_sha256 = a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
acceptance_passed = true
run72_complete = true
```

正式 evidence：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
```

Web 已独立从 GitHub evidence 审核：配置完整、无 failed config、无 resume 混入、provenance/identity 一致。TASK-011 computational PASS + Web evidence review PASS。

## 6.1 Censoring 保留

TASK-011 acceptance 不取消派生指标的边界限制：

- `peak_search_censored=true` 时，`distance_peak_retina_d=-0.50 D` 与相应 `DeltaF_residual` 是预注册距离峰搜索边界受限值；
- peak-censored 时 `distance_peak_mtfa` 只解释为预注册搜索窗口内观察到的峰值；
- `dof50_far_censored=true` 时 DOF50 width 为 lower bound；
- TASK-012 必须从 config-level CSV 传播 censor flags，不能只读取 paired-delta CSV 后直接排序。

不因这些 censoring 改变预注册窗口或重跑72 configs。

---

# 7. TASK-012 — Run72 offline analysis

正式计划：

```text
docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md
```

## 7.1 Scope

TASK-012 只读取 `f28b303...` 的四个 TASK-011 evidence 文件，完成：

1. evidence SHA 与72/36/1080 completeness 校验；
2. 从72-config summary 独立重建36个 EDOF−MONO deltas；
3. 从1080-row through-focus evidence 复核 `mtfa_at_zero_d` 与 `tf_mtfa_mean`；
4. config→pair censor propagation；
5. Base × Cornea × Platform × Pupil 描述性 factorial contrasts；
6. Cornea × Platform difference-in-differences interaction；
7. pupil/base sensitivity；
8. through-focus shape analysis；
9. 3×3 coupling matrix、trade-off、mechanism figures；
10. 单元测试、code review、result/document review 和 hashed analysis evidence。

不启动 OpticStudio。

## 7.2 Primary paired outcomes

所有 paired effect 固定定义为 `EDOF - MONO`：

```text
Delta DOF50_width
Delta distance_peak_mtfa
Delta mtfa_at_zero_d
Delta tf_mtfa_mean
Delta C40
Delta C60
Delta HOA_RMS
Delta F_residual
```

## 7.3 Statistical interpretation

这是确定性光学矩阵。默认使用：

- matched contrasts；
- difference-in-differences interactions；
- effect ranges；
- rank/direction stability；
- pupil/base sensitivity；
- censor-aware qualitative classification。

不把36个 pair 当作随机临床样本直接做传统 ANOVA p-value 推断。

## 7.4 Proposed code boundary

```text
src/whole_eye_mvp/run72_analysis.py
scripts/analyze_task_012_run72.py
tests/unit/test_task012_run72_analysis.py
```

正式分析产物放入：

```text
docs/evidence/task012/
```

并记录上游四文件 hashes、分析计划 identity/hash、分析代码 commit 与输出 hashes。

---

# 8. Git checkpoints

```text
feat/task-009-fft-mtf-main
  TASK-009 complete / Run72 Web clearance

feat/task-011-run72
  1. Web Run72 runner + exact aggregate
  2. failed-only resume + fixed 36-reference provenance
  3. Web CI + execution-plan freeze
  4. formal local Run72 batch
  5. sanitized TASK-011 evidence
  6. Web independent evidence review PASS
  7. status docs synchronized
  8. TASK-012 analysis plan frozen
  9. TASK-012 pure-Web analysis implementation + tests
  10. TASK-012 results/evidence + scientific review
```

PR #26 保持 Draft，除非另行授权改变状态或合并。

---

# 9. Current STOP conditions

1. TASK-005–009 frozen assets/method locks 不得修改；
2. TASK-008 manifest/hash/lock-set 不得因 TASK-012 改变；
3. sampling lock 必须保持128；
4. 不恢复 `AS_FftMtf`、Huygens、complex OTF 或 VSOTF production path；
5. 不使用 per-state/EDOF EFFL 改变 matched MONO/EDOF cpd 坐标；
6. 不因 peak/DOF censoring 扩大预注册窗口后补跑矩阵；
7. 不重新优化 B0.20 或 residual profiles；
8. 不把 `DeltaF_residual` 写入 carrier physical lock identity；
9. TASK-012 四文件 SHA、72/36/1080 completeness 或 paired reconstruction 任一失败时停止结果解释；
10. TASK-012 分析失败默认检查 evidence/代码，不以 OpticStudio rerun 作为机械修复；
11. 不把确定性矩阵直接当随机临床样本做传统显著性检验；
12. 不为获得特定结果事后改变主要 outcome、censor policy 或 interaction definition。
