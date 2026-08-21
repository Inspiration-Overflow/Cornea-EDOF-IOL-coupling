# CHECKPOINT — TASK-014 Phase C Ready

日期：2026-08-20  
用途：记录顶点距修订后、TASK-014 OpticStudio 正式 acquisition **之前**的可回退代码状态。

## 1. Git checkpoint

```text
active branch = feat/task-011-run72
checkpoint commit = 78fcadae13b381e30bafb3fdfdcf74e2430f9358
checkpoint branch = checkpoint/task014-phase-c-ready-2026-08-20
PR = #26
PR state at checkpoint = Draft / open / unmerged
PR base = feat/task-009-fft-mtf-main
```

该 checkpoint 与更早的修订前 checkpoint 不同：

```text
checkpoint/pre-vertex-correction-2026-08-20
→ fa401e2101023e6e409a5366f26f0da134b5476f
→ legacy direct corneal-plane -3.00 D 状态
```

而本 checkpoint：

```text
checkpoint/task014-phase-c-ready-2026-08-20
→ 78fcadae13b381e30bafb3fdfdcf74e2430f9358
→ vertex-corrected TASK-014 definition + ZOS implementation ready
→ no TASK-013/TASK-014 OpticStudio numerical acquisition yet
```

## 2. Scientific state at this checkpoint

Frozen legacy TASK-011/TASK-012 remains unchanged.

TASK-014 prescription contract:

```text
contract_id = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane distance treatment = -2.895752895753 D
corrected corneas = A0V12 / B0V12 / C0V12
```

TASK-013 N0 and TASK-014 are independent extensions; final normalized layer, after successful acquisition/review, is intended to be:

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configs
```

No N0 or corrected-cornea numerical result is considered acquired at this checkpoint.

## 3. TASK-014 implementation state

Code-complete components include:

```text
src/whole_eye_mvp/task014_vertex_corrected_cornea.py
src/whole_eye_mvp/task014_cornea_zos.py
src/whole_eye_mvp/task014_extension.py
src/whole_eye_mvp/task014_zos.py
scripts/run_task_014_vertex_corrected_cornea.py
scripts/inspect_task_014_vertex_corrected_prescriptions.py
tests/unit/test_task014_vertex_corrected_cornea.py
tests/unit/test_task014_extension.py
```

TASK-014 ZOS implementation code baseline:

```text
f332da42a84832a088ff401023cdf75b226ba407
```

Offline quality gate for that code baseline:

```text
run #148
run_id = 32406684311
conclusion = success
pytest = 229 passed
ruff = PASS
compileall = PASS
uv lock --check = PASS
```

Commits after the code baseline and before this checkpoint are documentation/status synchronization only.

## 4. Canonical ZMX contract at checkpoint

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
  corneas/                                      # 5 files
  carriers/                                     # 18 files
  runs/<run_id>/p0/                             # 6 files
  runs/<run_id>/pair_references/                # 36 files
  runs/<run_id>/configs/                        # 72 files
  runs/<run_id>/MODEL_INDEX.csv
```

Expected successful TASK-014 index size:

```text
5 + 6 + 18 + 36 + 72 = 137 ZMX records
```

## 5. Rollback use

If later OpticStudio acquisition reveals a problem in the new optical implementation but the vertex-corrected scientific definition remains valid, compare/recover from:

```text
checkpoint/task014-phase-c-ready-2026-08-20
```

If the vertex-corrected scientific definition itself must be abandoned, compare/recover from:

```text
checkpoint/pre-vertex-correction-2026-08-20
```

Do not overwrite frozen TASK-011/TASK-012 evidence in either rollback path.
