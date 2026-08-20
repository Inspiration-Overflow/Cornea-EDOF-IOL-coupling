# TASK-013 本地 OpticStudio 执行交接 v3

日期：2026-08-20  
状态：**authoritative local handoff；取代 TASK-013 v2 中把 actual-eye low-order 作为 hard gate 的部分**

## 1. 本次方法学修复

TASK-007 已冻结：

```text
normative low-order hard gate = STD_IOL_EYE_2024 EPD6 imported residual readback
actual-eye SSAG Mode-0 low-order = diagnostic only; aperture-limited
actual-eye hard evidence = ray health + through-focus + mechanism behavior
```

因此 TASK-013 exact-carrier validation schema 升级为 v2：

```text
hard numerical gate:
  standard-eye |piston| <= 0.010 µm
  standard-eye |global defocus| <= 0.125 D
  actual-eye MONO EPD5 ray health PASS
  actual-eye EDOF EPD5 ray health PASS

diagnostic only:
  actual-eye piston/global defocus readback
```

不得建立 RAD 专用阈值，也不得修改 residual。

## 2. 必须保留的历史 STOP runs

```text
task013-25e426e7c6d64d5aa59ffc089f352db2
  old terminal power-envelope gate

task013-2b0dfe62e0eb424a84ae0fe8da942253
  old v1 validator: actual-eye low-order incorrectly used as hard gate
```

两次 diagnostics、validation JSON、ZMX 均不得删除。

v2 validation 使用独立目录：

```text
residual_validations/<carrier_id>/v2_<carrierSHA12>_<residualSHA12>/
```

因此不会覆盖 v1 历史记录。

## 3. Git 前置

```powershell
cd C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling
git fetch --all --prune
git switch feat/task-011-run72
git pull --ff-only
git rev-parse HEAD
git status --short
```

修订前 rollback checkpoint：

```text
checkpoint/pre-task013-gate-domain-restore-2026-08-20
@ 88490f590b52f7b1f4aa0f0a9f05e99daae6eeee
```

## 4. 离线 QA

```powershell
uv sync --frozen
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

任一失败且涉及科学逻辑则 STOP。

## 5. TASK-013 重跑

允许 `--overwrite-models`，因为 canonical N0/carriers 已由前两次尝试生成；但不得覆盖历史 run diagnostics。

```powershell
uv run python scripts/run_task_013_native_reference.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence `
  --overwrite-models
```

必须生成新 run_id。

## 6. v2 validation 预期

对6个 exact carriers 均生成 v2 validation。

特别关注：

```text
CAR_ATC_M3_AL24477_N0_RAD
```

其 actual-eye piston 预计仍可能约为 `-0.043 µm`。该值必须完整记录，但不参与 v2 numerical pass/fail。

只要：

```text
standard-eye low-order PASS
MONO ray health PASS
EDOF ray health PASS
```

则 exact-carrier numerical validation PASS。

若 standard-eye low-order 或 ray health 任一失败，才是 TASK-local numerical STOP。

## 7. Power coverage 与 Web mechanism review

历史 envelope 仍为 coverage classifier。

预计 ATC+N0 WFS/RAD/HOA：

```text
within_existing_coverage = false
extension_validation_required = true
```

这些 carrier 即使 v2 numerical validation PASS，也必须在 acquisition 完成后标记：

```text
mechanism_review_pending_web = true
```

允许先完成 through-focus acquisition，因为这些数据正是 Web mechanism review 的证据来源。

本地 `acceptance_passed` 若仍由 runner 表示 archive/acquisition 完整性，只解释为 local acquisition acceptance；不得自行解释为最终 scientific acceptance。

## 8. 生产目标

```text
N0 reference cornea = 1
physical carriers = 6/6
v2 exact-carrier numerical validations = 6/6 PASS
pair references = 12/12
configs = 24/24
failed configs = 0
TF rows = 360
matched pairs = 12
config-specific ZMX = 24/24
MODEL_INDEX verification = PASS
model_archive_complete = true
```

## 9. 完成后必须回传 Web review 所需信息

至少：

- run_id / HEAD / OpticStudio version；
- 6 carrier P/Q；
- historical power coverage classification；
- v2 `VALIDATION_INDEX.json`；
- 每个 carrier 的 actual diagnostic piston/defocus；
- standard-eye low-order；
- MONO/EDOF ray health；
- 24 config results / 360 TF rows / paired deltas；
- censoring；
- MODEL_INDEX 和 ZMX SHA；
- residual bytes unchanged；
- TASK-011/012 unchanged。

对 out-of-coverage 的 ATC N0 WFS/RAD/HOA，Web 将基于 through-focus 与 mechanism/wavefront evidence 再作最终 scientific review。

## 10. 禁止

- 不修改 `RESIDUAL_VALIDATION_546_v1` 阈值；
- 不建立 RAD 特例阈值；
- 不修改 residual DAT；
- 不 retune Q/B0/N0；
- 不删除 v1 failure history；
- 不重跑 TASK-011；
- 不执行 TASK-014；
- 不 merge PR。
