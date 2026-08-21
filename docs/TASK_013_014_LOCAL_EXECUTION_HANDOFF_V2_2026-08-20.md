# TASK-013 / TASK-014 本地 OpticStudio 执行交接 v2

日期：2026-08-20  
状态：**authoritative local handoff；取代此前“TASK-013 envelope 越界即阻断 TASK-014”的执行顺序**

## 1. 当前方法学修订

旧行为：

```text
new carrier outside historical residual power envelope
→ STOP TASK-013
→ 不再执行 TASK-014
```

新行为：

```text
historical power envelope
→ 只判断已有验证是否覆盖该 power

每个 new carrier 第一次进入 EDOF production 前
→ exact carrier SHA + exact frozen residual SHA
→ actual-eye low-order replay
→ standard-eye low-order replay
→ actual-eye MONO/EDOF EPD5 ray-health
→ PASS 才进入正式 EDOF production
```

TASK-013 与 TASK-014 为平行任务，不再互相自动阻断。

---

## 2. Git 前置状态

仓库：

```text
C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling
```

项目目录：

```text
C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx
```

分支：

```text
feat/task-011-run72
```

开始时：

```powershell
cd C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling
git fetch --all --prune
git switch feat/task-011-run72
git pull --ff-only
git rev-parse HEAD
git status --short
```

必须 clean tracked checkout。

保留 checkpoint：

```text
checkpoint/pre-vertex-correction-2026-08-20
checkpoint/task014-phase-c-ready-2026-08-20
checkpoint/pre-residual-validation-trigger-2026-08-20
```

不 merge PR #26，不 force push，不删除 checkpoint。

---

## 3. 离线 QA

```powershell
uv sync --frozen
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

任一失败：先修纯执行问题；若涉及科学定义则停止并回报。

---

## 4. 既有 TASK-011 archive

此前本地已成功执行纯文件归档：

```text
72 config source snapshots
36 pair-reference source snapshots
18 carrier models
MODEL_INDEX = 126 records
```

不要重跑 TASK-011 OpticStudio。

若 archive 已存在，只做 SHA 验证即可；无需重复复制。

---

## 5. TASK-013 首次失败产物必须保留

首次本地 carrier build 的 run：

```text
run_id = task013-25e426e7c6d64d5aa59ffc089f352db2
```

它成功产生 N0、6个 carriers，并在旧 envelope hard gate 处停止。

保留其 diagnostics，包括：

```text
diagnostics/task013/task013-25e426e7c6d64d5aa59ffc089f352db2/
```

不得删除，以保留方法学变更前后的审计轨迹。

---

## 6. TASK-013 重跑

因为首次失败运行已经写入 canonical N0/carrier 模型，本次重跑允许：

```text
--overwrite-models
```

这仅用于用当前代码重新生成同一 TASK-013 canonical 模型，不代表允许改变科学参数。

执行：

```powershell
uv run python scripts/run_task_013_native_reference.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence `
  --overwrite-models
```

### 6.1 Power coverage

预期仍可能看到 ATC+N0 约19 D 位于历史 envelope 外。

这次**不得因此停止**。

应记录：

```text
existing_validation_coverage = false
extension_validation_required = true
```

### 6.2 Exact-carrier residual validation

第一次 EDOF config 前，程序必须自动生成：

```text
models/task013_native_reference/residual_validations/
```

完整 TASK-013 成功时：

```text
VALIDATION_INDEX.json
validation_count = 6
all_passed = true
```

每个 carrier validation 绑定 exact carrier/residual SHA，并保存：

```text
ACTUAL_EDOF.zmx
STD_MONO.zmx
STD_EDOF.zmx
VALIDATION.json
```

硬门：

```text
actual |piston| <= 0.010 µm
actual |global defocus| <= 0.125 D
standard |piston| <= 0.010 µm
standard |global defocus| <= 0.125 D
MONO ray health PASS
EDOF ray health PASS
```

失败时：

- 停止 TASK-013 的 EDOF production；
- 保存 validation diagnostics；
- 不改 residual；
- 不 retune carrier；
- 不把失败自动传播为 TASK-014 STOP，除非失败原因是共享 frozen asset/hash 漂移。

### 6.3 TASK-013 正式 acceptance

```text
N0 = 1
carriers = 6/6
power coverage classification = complete
residual validations = 6/6 PASS
pair references = 12/12
configs = 24/24
failed = 0
TF rows = 360
pairs = 12
config ZMX = 24/24
MODEL_INDEX complete = true
acceptance_passed = true
```

---

## 7. TASK-014 独立执行

TASK-014 不等待 TASK-013 scientific acceptance 才能启动。

若 TASK-013 因某个 exact-carrier residual validation 失败而暂停，但 frozen residual SHA、standard eye、TASK-008 provenance 均正常，可以继续 TASK-014。

首次 TASK-014 正式运行不要加 overwrite：

```powershell
uv run python scripts/run_task_014_vertex_corrected_cornea.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence
```

TASK-014 contract 保持：

```text
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane distance treatment = -2.895752895753 D
A0V12 / B0V12 / C0V12
```

### 7.1 Residual validation

所有18个 corrected carriers 第一次进入 EDOF 前同样执行 exact-carrier validation。

成功时：

```text
models/task014_vertex_corrected/residual_validations/VALIDATION_INDEX.json
validation_count = 18
all_passed = true
```

历史 power envelope 仍报告 coverage，但不再是 terminal exclusion gate。

### 7.2 TASK-014 acceptance

```text
corrected corneas = 3/3
P0 = 6/6
carriers = 18/18
power coverage classification = complete
residual validations = 18/18 PASS
pair references = 36/36
configs = 72/72
failed = 0
TF rows = 1080
pairs = 36
primary MODEL_INDEX = 137 records
acceptance_passed = true
```

137 仍只统计主研究模型：

```text
5 cornea-layer
6 P0
18 carriers
36 pair references
72 analyzed configs
```

residual validation `.zmx` 是 diagnostics/provenance，不并入137。

---

## 8. TASK-local STOP 与 shared STOP

### 8.1 只暂停当前 task

例如：

- exact-carrier actual low-order validation fail；
- exact-carrier standard low-order validation fail；
- 该 carrier MONO/EDOF ray health fail；
- 该 task carrier P/Q solve fail。

此时保存 diagnostics；另一 task 可以独立继续。

### 8.2 同时阻止 TASK-013 与 TASK-014

如果发现共享 frozen provenance 问题：

- residual DAT SHA mismatch；
- `STD_IOL_EYE_2024` immutable hash mismatch；
- TASK-008 manifest/lock set drift；
- TASK-011/TASK-012 frozen evidence 被修改；
- TASK-009 production contract drift。

此时两者都应停止。

---

## 9. 禁止操作

不得：

- 因约19 D N0 power 而改变 N0 设计；
- 扩大 residual envelope 人工宣称“已验证”；
- 修改 residual DAT bytes/shape/hash；
- 重优化 frozen residual；
- retune B0.20；
- 改 vertex 12 mm contract 以使结果更接近 legacy；
- 修改 EPD、sampling、defocus window、peak window；
- 重跑 legacy TASK-011；
- merge PR。

---

## 10. 最终回传

分别回传 TASK-013 与 TASK-014，不再要求前者 PASS 才报告后者。

至少包括：

```text
branch
HEAD before/after
git status
OpticStudio version

TASK-013:
  run_id
  six carrier P/Q
  coverage checks
  validation_count / all_passed
  exact validation failures if any
  24/24 configs
  360 TF rows
  12 pairs
  MODEL_INDEX
  acceptance

TASK-014:
  run_id
  rx contract
  18 carrier P/Q
  coverage checks
  validation_count / all_passed
  exact validation failures if any
  72/72 configs
  1080 TF rows
  36 pairs
  MODEL_INDEX=137
  acceptance

Frozen status:
  TASK-011/TASK-012 changed? NO
  legacy TASK-011 OpticStudio rerun? NO
  residual bytes changed? NO
  PR merged? NO
```

只有 TASK-013 与 TASK-014 都独立 acceptance PASS 后，才进入最终96配置离线合并与全部贯焦曲线补充材料。
