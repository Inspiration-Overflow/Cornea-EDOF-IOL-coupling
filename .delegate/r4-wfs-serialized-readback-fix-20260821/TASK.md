# Task: R4 WFS serialized Binary4 readback fix

## Objective

修复 R4 representative +20 D mechanism-fit pilot 在 WFS 阶段的硬失败：
`R4 WFS serialized Binary4 readback lost the fitted mechanism fidelity`。

只处理 serialized Binary4 readback 的程序错误或 API 映射错误。保持 R4 已冻结的
科学定义、fitter target、2%/5% pilot target、serialized 1.25x slack、zone
boundaries、p2 lock、A4/A6 参数语义、physical pupil、retina、MFE Grid=1
分析设置和所有阈值不变。

## Authorized repository and branch

- Repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- Base commit: `35297ef4477bec555e19c5b0aa6bfe709b122016`
- Task branch: `delegate/r4-wfs-serialized-readback-fix-20260821`

## Authorized inputs

- `src/whole_eye_mvp/revision_r4_zos.py`
- `src/whole_eye_mvp/revision_r4_fit.py`
- `scripts/run_model_revision_r4_pilot.py`
- `tests/unit/test_revision_r4_fit.py`
- `docs/MODEL_REVISION_R4_MECHANISM_PILOT_AND_LOCAL_HANDOFF_2026-08-21.md`
- The local failure evidence paths named in this task:
  `project_mvp_2026_v2_zmx/diagnostics/model_revision/r4_pilot/R4_ANALYTICAL_MONO_WFS.zmx`,
  `R4_BINARY4_MONO_WFS.zmx`, and `R4_BINARY4_EDOF_WFS.zmx`.

## Authorized writes

- `.delegate/r4-wfs-serialized-readback-fix-20260821/TASK.md`
- `.delegate/r4-wfs-serialized-readback-fix-20260821/manifest.json`
- `.delegate/r4-wfs-serialized-readback-fix-20260821/result.json`
- `src/whole_eye_mvp/revision_r4_zos.py`
- `src/whole_eye_mvp/revision_r4_fit.py` only if strictly required by the readback fix
- `scripts/run_model_revision_r4_pilot.py` only if strictly required by the readback fix
- `tests/unit/test_revision_r4_fit.py` and one narrowly scoped R4 ZOS unit test file only if
  strictly required to lock the fixed behavior

## Constraints

- Do not change scientific definitions, targets, thresholds, zone boundaries, physical STOP,
  retina, Binary4 parameter definitions, MFE frequency grid, sampling, Grid, Data Type, or
  analysis backend.
- Do not change R2/R3 evidence or frozen model artifacts.
- Do not restore native FFT analysis.
- Do not run a live OpticStudio regression. Local Codex will run the single complete R4 pilot
  after the Web result is independently verified.
- Do not enter R6/R7, production expansion, full carrier expansion, or mechanism fitting beyond
  the existing R4 pilot implementation.
- Do not modify unrelated files or the default/protected branch.

## Required work

1. Inspect the WFS serialized Binary4 write/readback path and identify the minimal cause of the
   fidelity loss.
2. Implement the minimal code fix within the authorized write paths.
3. Add or update only narrowly scoped offline tests that prove the fixed readback mapping without
   changing scientific targets.
4. Run the relevant offline tests and the repository unit suite if practical.
5. Commit the changes on this task branch.
6. Write `.delegate/r4-wfs-serialized-readback-fix-20260821/result.json` with the matching task
   metadata, dispatch commit, result commit reference, changed paths, tests run, summary, and
   limitations. Do not put the result commit SHA inside `result.json` itself.

## Acceptance criteria

- The failure cause is addressed by a minimal, reviewable code change.
- Offline tests pass.
- No authorized scientific or analysis setting changes are introduced.
- No live OpticStudio run is performed by Web.
- The result contract is complete and references only authorized paths.
