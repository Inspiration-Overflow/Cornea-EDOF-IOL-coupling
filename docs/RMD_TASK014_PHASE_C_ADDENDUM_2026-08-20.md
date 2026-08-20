# RMD Addendum — TASK-014 Phase C 完成

日期：2026-08-20  
适用：`RMD-0001 v2.0` 的 TASK-014 状态补充

## 当前状态

`docs/RMD.md` v2.0 中 TASK-014 Phase C 原标记为待实现。现以本 addendum 更新执行状态：

```text
TASK-014 Phase A — 文档/rollback checkpoint        COMPLETE
TASK-014 Phase B — vertex prescription layer       COMPLETE / QA PASS
TASK-014 Phase C — ZOS builders + 72-config runner COMPLETE / QA PASS
TASK-014 Phase D — local OpticStudio acquisition   PENDING
```

ZOS implementation code baseline：

```text
f332da42a84832a088ff401023cdf75b226ba407
```

Offline quality gate：

```text
run #148
run_id = 32406684311
conclusion = success
pytest = 229 passed
ruff = PASS
compileall = PASS
uv lock --check = PASS
```

## Phase C 已完成组件

```text
src/whole_eye_mvp/task014_cornea_zos.py
src/whole_eye_mvp/task014_extension.py
src/whole_eye_mvp/task014_zos.py
scripts/run_task_014_vertex_corrected_cornea.py
tests/unit/test_task014_extension.py
```

加上既有：

```text
src/whole_eye_mvp/task014_vertex_corrected_cornea.py
scripts/inspect_task_014_vertex_corrected_prescriptions.py
tests/unit/test_task014_vertex_corrected_cornea.py
```

## Canonical model archive

Phase C 将实际 canonical 路径冻结为：

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
```

详细目录与 acceptance 见：

```text
docs/TASK_014_IMPLEMENTATION_REVIEW_2026-08-20.md
docs/TASK_014_LOCAL_EXECUTION_HANDOFF_2026-08-20.md
```

## 下一步

```text
1. archive frozen TASK-011 ZMX without OpticStudio
2. run TASK-013 N0 acquisition and review
3. run TASK-014 acquisition and review
4. combine accepted TASK-013 + TASK-014 into normalized 96-config offline dataset
5. render all through-focus supplementary figures
```

旧 frozen TASK-011/TASK-012 identity、rollback checkpoint 和 STOP 条件继续有效。
