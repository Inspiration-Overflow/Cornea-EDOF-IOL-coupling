# TASK-014 本地 OpticStudio 执行交接

日期：2026-08-20  
状态：**Web/GitHub 代码已通过离线质量门；待 Windows + OpticStudio/ZOS-API 执行**

## 1. 执行前 Git 状态

正式执行前应位于：

```text
branch = feat/task-011-run72
```

TASK-014 ZOS implementation code baseline：

```text
f332da42a84832a088ff401023cdf75b226ba407
```

对应离线质量门：

```text
run #148
run_id = 32406684311
conclusion = success
pytest = 229 passed
ruff = PASS
compileall = PASS
uv lock --check = PASS
```

vertex-correction 修订前回退锚点：

```text
checkpoint/pre-vertex-correction-2026-08-20
fa401e2101023e6e409a5366f26f0da134b5476f
```

完整回退说明：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

## 2. 推荐执行顺序

### 2.1 先归档既有 TASK-011 ZMX

该步骤不启动 OpticStudio，也不重新计算结果：

```powershell
uv run python scripts/archive_task011_zmx_models.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx"
```

### 2.2 执行 TASK-013 N0

```powershell
uv run python scripts/run_task_013_native_reference.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence
```

TASK-013 必须先得到：

```text
physical carriers = 6
residual power-envelope = PASS
pair references = 12
completed configs = 24
failed configs = 0
through-focus rows = 360
matched pairs = 12
model_archive_complete = true
acceptance_passed = true
```

若 residual power-envelope FAIL，停止，不进入 EDOF production。

### 2.3 执行 TASK-014 vertex-corrected postoperative corneas

```powershell
uv run python scripts/run_task_014_vertex_corrected_cornea.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence
```

若未通过环境变量设置 OpticStudio 安装目录，再显式加：

```text
--install-dir <OpticStudio install dir>
```

首次正式执行不要使用：

```text
--overwrite-models
```

## 3. TASK-014 预期输出

### Canonical ZMX

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
  corneas/
    REFERENCE_CORNEA.zmx
    DISTANCE_CORNEA_VERTEX12.zmx
    CORNEA_A0V12.zmx
    CORNEA_B0V12.zmx
    CORNEA_C0V12.zmx
  carriers/
    CAR_<base>_<cornea>_<platform>.zmx                 # 18
  runs/<run_id>/
    p0/P0_<base>_<cornea>.zmx                         # 6
    pair_references/<pair_key>.zmx                    # 36
    configs/<config_id>.zmx                           # 72
    MODEL_INDEX.csv
```

成功时模型索引预期：

```text
5 + 6 + 18 + 36 + 72 = 137 ZMX records
```

### Structured results

```text
project_mvp_2026_v2_zmx/results/task014_vertex_corrected/<run_id>/<config_id>/
project_mvp_2026_v2_zmx/results/task014_vertex_corrected/reports/<run_id>.json
```

### Sanitized GitHub evidence

```text
docs/evidence/task014/TASK_014_EVIDENCE.json
docs/evidence/task014/TASK_014_CONFIG_RESULTS.csv
docs/evidence/task014/TASK_014_THROUGH_FOCUS.csv
docs/evidence/task014/TASK_014_PAIRED_DELTAS.csv
docs/evidence/task014/TASK_014_MODEL_INDEX.csv
```

## 4. TASK-014 acceptance

必须全部满足：

```text
A0V12/B0V12/C0V12 built = 3/3
Q=0 start models = 6/6
physical P/Q carriers = 18/18
residual power-envelope = PASS
pair references = 36/36
completed configs = 72/72
failed configs = 0
through-focus rows = 1080
matched pairs = 36
config-specific ZMX = 72/72
MODEL_INDEX hash replay = PASS
model_archive_complete = true
acceptance_passed = true
```

## 5. STOP 条件

立即停止并把 evidence 带回 Web 审核，如果出现：

- A0V12 或 B0V12 ΔC4 target solve 失败；
- C0V12 构建异常；
- 任一 carrier P-Q recheck 超过2轮；
- standard-eye SA replay 超容差；
- 任一 corrected carrier power 超出 frozen residual power envelope；
- pair-MONO EFFL 无效；
- config model SHA 与 archive SHA 不一致；
- 72配置中出现失败；
- 任何脚本试图修改 frozen TASK-008/011/012 evidence。

## 6. 执行后回传

建议完整回传：

```text
HEAD =
git status =
TASK-011 archive command/output =
TASK-013 command/run_id/acceptance =
TASK-014 command/run_id/acceptance =
TASK-014 report path =
TASK-014 MODEL_INDEX path =
TASK-014 evidence files =
```

完成后 Web 侧下一步为：

```text
TASK-013 evidence review
→ TASK-014 evidence review
→ merge N0 + A0V12/B0V12/C0V12 into normalized 96-config offline dataset
→ render all through-focus supplementary figures
```
