# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 及已批准的独立任务计划提供。

## Metadata

- document_id: `RMD-0001`
- version: `2.0`
- status: `active`
- source_docs: `URD-0001 v1.6`, `ADD-0001 v1.6`, `MDD-0001 v1.5`, `TDD-0001 v1.6`, `TASK-013-NATIVE-CORNEA-REFERENCE`, `TASK-014-VERTEX-CORRECTED-POSTOP-CORNEA`
- last_updated: `2026-08-20`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-011-run72`
- active_production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- active_frequency_scale: `paired_residual_free_MONO_EFFL`
- active_production_sampling: `128`
- completed_analysis_task: `TASK-012`
- active_extension_tasks: `TASK-013 N0` + `TASK-014 vertex-corrected postoperative cornea prescription layer`
- next_science_phase: `TASK-013 N0 acquisition → TASK-014 corrected postoperative optical implementation/acquisition → clinically normalized 4-cornea supplement`

---

# 1. Dual-environment execution model

## Web / GitHub

负责科学规范、冻结决策、Python 代码与测试、GitHub static review、structured evidence 审核、TASK-012 离线统计/图表、TASK-013/014 文档与纯代码实现，以及后续离线整合。

## Local Windows / ZCode

只负责必须由真实 OpticStudio/ZOS-API 给出的新事实。

- TASK-011 正式 Run72 已完成；
- TASK-012 完全基于冻结 evidence；
- TASK-013 只运行新增 N0 层，不重跑既有72配置；
- TASK-014 后续只运行新的 A0V12/B0V12/C0V12 层，不重写 legacy A0/B0/C0。

## Cost-aware rule

- 已满足 gate 的代表配置不重复运行；
- 已接受的72-config Run72 不因后续扩展或少量 censoring 重跑；
- 不事后扩大冻结 focus/peak window；
- 普通统计、图表、provenance、文档和归档工具留在 Web/GitHub；
- 新的本地 optical acquisition 必须有独立科学问题支持；
- 任何新任务不得静默改写旧 scientific identity。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

unit tests 不依赖 OpticStudio。正式 scientific assets immutable；analysis provenance 必须版本化/hashable。`.zmx` exact analyzed model 从 TASK-013 起是强制研究 artifact，并要求 canonical archive + SHA index。

---

# 3. Completed build path and active extensions

| Task | Status | Frozen / planned output |
| --- | --- | --- |
| TASK-001 | complete | uv/src/tests/git skeleton |
| TASK-002 | complete | ZOS session lifecycle validated |
| TASK-003 | complete | domain + ProjectStore + hash/run provenance |
| TASK-004 | complete then migrated | current MTFa metric layer |
| TASK-005 | complete | LB/ATC、standard eye、A0/B candidates/C0 |
| TASK-006 | complete | B0.20 immutable lock |
| TASK-007 | complete | 18 P/Q、3 residuals、9 calibrations、TDD-999 cleared |
| TASK-008 | complete | 18 formal carrier locks、3 residual locks、72-config manifest |
| TASK-009 | complete | paired-MONO MFE MTFA production method + sampling128 |
| TASK-011 | complete | formal Run72: 72 configs / 36 pairs / 1080 rows; Web review PASS |
| TASK-012 | complete | offline reconstruction + censor-aware factorial analysis + 24 figures + review PASS |
| TASK-013 | implementation complete / optical run pending | N0 + 6 carriers + 24 configs + 12 pairs + 360 TF rows + canonical ZMX archive |
| TASK-014 | prescription layer active / optical implementation pending | spectacle −3.00 D @12 mm → corneal plane −2.895752895753 D; A0V12/B0V12/C0V12 |

TASK-010 GUI 保持 optional，不是科学前置条件。

TASK-013/014 文档：

```text
docs/TASK_013_NATIVE_CORNEA_REFERENCE_PLAN_2026-08-20.md
docs/TASK_013_VERTEX_CORRECTION_ADDENDUM_2026-08-20.md
docs/TASK_014_VERTEX_CORRECTED_CORNEA_EXTENSION_PLAN_2026-08-20.md
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

---

# 4. Frozen production identity

以下 TASK-008/009/011 identity 继续只读：

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

生产方法：

```text
residual-free MONO EFFL once per matched pair
→ paired_residual_free_MONO_EFFL angular scale
→ MFE MTFA Grid=1
→ 15-plane MTFa + fixed-frequency MTF + HOA readback
→ ConfigResult / matched deltas
```

TASK-013/014 必须复用该 production method，但使用各自 extension identity，不改写 TASK-008 manifest/hash。

---

# 5. TASK-011 / TASK-012 frozen state

TASK-011：

```text
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
completed_configs = 72
failed_configs = 0
matched_pairs = 36
through_focus_rows = 1080
acceptance_passed = true
```

TASK-012：

```text
pairs = 36
contrasts = 1152
coupling cells = 9
figures = 24
DOF50 exact = 31
DOF50 lower_bound = 5
peak-window-censored pairs = 8
result_review = PASS_WITH_SCIENTIFIC_CAVEATS
```

旧 A0/B0/C0 的真实治疗语义固定为：

```text
direct corneal-plane treatment_d = -3.00 D
vertex-distance conversion = none
```

因此旧结果仍是有效的 legacy engineering factorial，但不再被无条件解释为“框架镜 −3.00 D 经顶点距转换后的临床术后角膜”。

---

# 6. Vertex-correction rollback checkpoint

在引入 TASK-014 前固定：

```text
pre-revision HEAD = fa401e2101023e6e409a5366f26f0da134b5476f
checkpoint branch = checkpoint/pre-vertex-correction-2026-08-20
PR = #26 Draft / open / unmerged
pre-revision offline quality = run #132 / 32396661153 / success
```

完整旧设定见：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

该 branch/commit 是比较与恢复锚点，不应删除。

---

# 7. TASK-013 — N0 native/untreated cornea reference

## 7.1 Scope

```text
N0 = native / untreated reference cornea
2 Base × 1 N0 × 3 Platform = 6 carriers
6 × MONO/EDOF × EPD3/5 = 24 configs
12 matched pairs
360 TF rows
```

N0 不进行角膜近视治疗，因此 vertex correction 不改变 N0 本身的定义。

## 7.2 Route

```text
N0 scaffold
→ per Base Q=0 P/R solve
→ per Platform STD_IOL_EYE_2024 power-specific Q(P)
→ actual-eye P–Q recheck (max2)
→ 6 canonical carriers
→ frozen residual power-envelope gate
→ 12 pair-MONO EFFL references
→ 24-config production acquisition
→ exact ZMX archive
```

若任一 N0 power 超出相应 residual validated power envelope，必须 STOP 于 EDOF production 前。

## 7.3 Canonical ZMX

```text
project_mvp_2026_v2_zmx/models/task013_native_reference/
  cornea/N0_REFERENCE_CORNEA.zmx
  carriers/CAR_<base>_N0_<platform>.zmx
  runs/<run_id>/pair_references/<pair_key>.zmx
  runs/<run_id>/configs/<config_id>.zmx
  runs/<run_id>/MODEL_INDEX.csv
```

## 7.4 Interpretation boundary after vertex review

TASK-013 N0 + frozen TASK-011 A0/B0/C0 可以做 legacy descriptive comparison，但不得称为统一临床屈光平面规范化96配置。

最终 clinically normalized 4-cornea layer 必须等待 TASK-014 corrected postoperative data。

---

# 8. TASK-014 — spectacle-to-corneal-plane prescription normalization

## 8.1 Frozen prescription contract

```text
contract_id = TASK014_SPECTACLE_M3_VERTEX12_v1
preoperative spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane distance treatment = -2.895752895753 D
legacy direct treatment = -3.000000000000 D
delta versus legacy = +0.104247104247 D
```

12 mm 是冻结工程建模约定；若未来做 vertex sensitivity，必须另建 identity。

## 8.2 Corrected cornea IDs

```text
A0V12: treatment -2.895752895753 D + Delta C4^0 target +0.13 µm
B0V12: treatment -2.895752895753 D + B0.20 target +0.20 µm
C0V12: treatment -2.895752895753 D + central-near ADD +1.75 D
```

不得复用旧 A0/B0/C0 identity。

## 8.3 Base phenotype is orthogonal

```text
Base phenotype = LB_AL2395 / ATC_M3_AL24477
standardized surgical prescription = spectacle -3.00 D @ 12 mm
```

`ATC_M3_AL24477.source_refraction_d=-3.0` 是来源模型/表型信息，不与 TASK-014 treatment 相加。

## 8.4 Planned optical matrix

```text
2 Base × 3 corrected corneas × 3 Platform = 18 carriers
18 × MONO/EDOF × EPD3/5 = 72 configs
36 matched pairs
1080 TF rows
```

与 accepted TASK-013 N0 合并后：

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 clinically normalized configs
```

## 8.5 Current implementation boundary

本轮先完成纯 Python prescription layer：

```text
src/whole_eye_mvp/task014_vertex_corrected_cornea.py
scripts/inspect_task_014_vertex_corrected_prescriptions.py
tests/unit/test_task014_vertex_corrected_cornea.py
```

OpticStudio corrected-cornea builders、18 carriers、72-config runner 在下一代码阶段实现；不得提前把处方快照当作 optical result。

---

# 9. ZMX preservation

TASK-013 已建立 canonical archive 规则。TASK-014 继续使用：

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected_postop/
  corneas/CORNEA_A0V12.zmx
  corneas/CORNEA_B0V12.zmx
  corneas/CORNEA_C0V12.zmx
  carriers/CAR_<base>_<cornea>_<platform>.zmx
  runs/<run_id>/pair_references/<pair_key>.zmx
  runs/<run_id>/configs/<config_id>.zmx
  runs/<run_id>/MODEL_INDEX.csv
```

每个 config `.zmx` 必须包含其 config-specific EPD，并与 analyzed model SHA 绑定。

现有 TASK-011 `.zmx` 继续只做历史 source-snapshot 归档，不重跑数值结果。

---

# 10. Implementation order

```text
A. rollback checkpoint + TASK-014 science doc
B. pure Python vertex/prescription layer + tests
C. offline quality gate
D. TASK-013 local N0 acquisition + Web review
E. TASK-014 OpticStudio corrected-cornea builder/runner implementation
F. TASK-014 local 72-config acquisition + Web review
G. combine accepted TASK-013 + TASK-014
H. final clinically normalized 4×3 through-focus supplement
```

A/B/C 当前正在本分支执行；任何 optical acquisition 前必须重新确认代码 HEAD 与文档 identity。

---

# 11. Git checkpoints

```text
feat/task-009-fft-mtf-main
  TASK-009 complete / Run72 Web clearance

feat/task-011-run72
  TASK-011 formal Run72 accepted
  TASK-012 offline analysis accepted
  manuscript working draft assembled
  TASK-013 N0 implementation
  TASK-014 vertex-corrected prescription normalization

checkpoint/pre-vertex-correction-2026-08-20
  exact pre-TASK014 state at fa401e2101023e6e409a5366f26f0da134b5476f
```

PR #26 保持 Draft，除非另行授权改变状态或合并。

---

# 12. Current STOP conditions

1. TASK-005–009 frozen assets/method locks 不得修改；
2. TASK-008 manifest/hash/lock-set 不得因 TASK-013/014 改变；
3. sampling lock 保持128；
4. 不恢复任何已退休的 pre-TASK009 production path；
5. 不使用 per-state/EDOF EFFL 改变 matched pair cpd 坐标；
6. 不因 peak/DOF censoring 扩大预注册窗口；
7. 不重新优化 B0.20 或 residual profiles；
8. 不把 `DeltaF_residual` 写入 carrier physical identity；
9. 不把 DOF50 lower bound/peak-window result 静默当精确值；
10. 不把确定性矩阵当随机临床样本做传统显著性检验；
11. 不为论文叙事事后改变 outcome/censor/interaction definition；
12. N0 或 TASK-014 carrier power 超出 frozen residual calibration envelope 时必须先 STOP/validate；
13. canonical ZMX SHA 与 analyzed model 不一致时不得完成 archive；
14. custom carrier-directory 支持不得改变 TASK-011 默认路径/行为；
15. TASK-013/014 不得覆盖 TASK-011/TASK-012 structured evidence；
16. 不修改 legacy `BASELINE_CORNEA_SPECS` 以实现 TASK-014；
17. 不修改 legacy `distance_corrected_cornea_power_d()` 的语义；
18. 不把 ATC source refraction 与 TASK-014 surgical prescription 相加；
19. 不把 frozen A0/B0/C0 静默重命名为 A0V12/B0V12/C0V12；
20. 新 evidence/code inconsistency 出现时先停止解释并做 Web review，不以重跑全部 OpticStudio 矩阵作为默认修复。
