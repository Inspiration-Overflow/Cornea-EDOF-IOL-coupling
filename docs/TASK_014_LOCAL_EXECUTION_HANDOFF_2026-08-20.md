# TASK-014 本地 OpticStudio 执行交接

日期：2026-08-20  
状态：**待本地 Windows + OpticStudio 正式 acquisition**

本交接只执行 TASK-014。TASK-013 已完成 local acquisition，不需要先重跑，也不是 TASK-014 的 scientific prerequisite。

## 1. 执行前

```powershell
cd C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling
git fetch --all --prune
git switch feat/task-011-run72
git pull --ff-only
git rev-parse HEAD
git status --short

uv sync --frozen
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

任一 offline gate 失败则 STOP。

首次正式 TASK-014 run 不使用 `--overwrite-models`。

## 2. 冻结 scientific contract

```text
contract = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex = 12.00 mm
corneal-plane treatment = -2.895752895753 D
corneas = A0V12 / B0V12 / C0V12
```

不得修改：

- frozen WFS/RAD/HOA residual bytes/hash/shape；
- B0.20；
- +1.75 D C0V12 ADD；
- TASK-009 sampling=128；
- +0.50→−3.00 D focus window；
- paired residual-free MONO EFFL frequency scale；
- TASK-008/011/012 frozen evidence。

## 3. Residual validation 当前规则

Historical power envelope 只做 coverage classification：

```text
within_existing_coverage
extension_validation_required
```

越界本身不 STOP。

每个 carrier 第一次进入 EDOF materialization 前，runner 会调用 shared schema-v2 exact-carrier validator；通过记录按 exact carrier SHA + residual SHA 缓存，第二个 pupil 直接复用。

Hard gate：

```text
STD_IOL_EYE_2024 EPD6:
  |piston| <= 0.010 µm
  |global defocus| <= 0.125 D

actual eye EPD5:
  MONO ray health PASS
  EDOF ray health PASS
```

Actual-eye SSAG Mode-0 piston/defocus 是 diagnostic-only。不得建立 RAD 特例阈值。

## 4. 正式命令

```powershell
uv run python scripts/run_task_014_vertex_corrected_cornea.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence
```

若环境变量未设置，再加：

```text
--install-dir <OpticStudio install dir>
```

## 5. 预期生产规模

```text
corrected cornea layer = 5 models
Q=0 starts = 6
physical carriers = 18
pair references = 36
configs = 72
failed configs = 0
through-focus rows = 1080
matched pairs = 36
primary MODEL_INDEX = 137 records
```

Canonical path：

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
```

Residual validation diagnostics 位于：

```text
models/task014_vertex_corrected/residual_validations/
```

不计入137条 primary model index。

## 6. Acceptance 解释

本地 `acceptance_passed=true` 只表示：

```text
local acquisition/archive acceptance
```

不等于 final scientific acceptance。

若任一 carrier `within_existing_coverage=false`，即使 exact validation PASS，也必须在 Web 侧做 mechanism review。

## 7. STOP 条件

立即停止并保留 diagnostics，如果：

1. A0V12/B0V12/C0V12 build/target solve fail；
2. carrier P-Q recheck >2；
3. standard-eye SA replay fail；
4. residual DAT SHA mismatch；
5. standard-eye residual low-order hard gate fail；
6. actual-eye MONO/EDOF ray-health fail；
7. pair-MONO EFFL invalid；
8. config analysis failure；
9. config EPD 未持久化；
10. model/archive SHA mismatch；
11. 任何过程试图修改 frozen TASK-008/011/012。

以下不是单独 STOP：

```text
carrier power outside historical coverage
actual-eye SSAG diagnostic piston/defocus outside tolerance
```

## 8. 完成后回传

```text
branch =
HEAD =
git status =
OpticStudio version =
run_id =

cornea layer =
Q0 starts =
physical carriers =
coverage summary =
extension validation required carrier IDs =
validation index path =
validation current records =
validation all_passed =

pair references =
completed configs =
failed configs =
TF rows =
matched pairs =
peak/DOF censoring summary =

MODEL_INDEX path =
MODEL_INDEX records =
model archive complete =
local acceptance_passed =

residual bytes changed? = NO
TASK-011/TASK-012 changed? = NO
legacy TASK-011 rerun? = NO
PR merged? = NO

evidence paths =
```

完成后停止。不要自行 merge PR，也不要自行组合96配置；把 evidence 带回 Web review。