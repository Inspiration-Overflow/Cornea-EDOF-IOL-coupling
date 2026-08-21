# TASK-013 实现审核：N0 未治疗参考角膜扩展与 ZMX 归档

日期：2026-08-20  
状态：**代码实现完成；离线质量门通过；待本地 Windows/OpticStudio 正式执行**

## 1. 审核结论

TASK-013 已按“先文档、后代码”的顺序完成 Web/GitHub 侧实现。

科学边界保持正确：

- TASK-008 的18个 carrier locks、72-config manifest、manifest hash 与 lock-set hash 未改变；
- TASK-011 的72配置、36 pair、1080 TF rows 与正式 evidence 未改变；
- TASK-012 的 structured evidence 未改变；
- N0 未加入 `ScientificBaseline.cornea_specs`，仍是独立 extension；
- B0.20 和3个 frozen residual 均未修改；
- TASK-009 MFE MTFA、paired-MONO EFFL、sampling128、defocus window 与 censor policy 均继承不变。

新增研究规模固定为：

```text
N0 × 2 base × 3 platform = 6 new physical carriers
6 carrier × 2 optic state × 2 pupil = 24 configs
12 matched MONO/EDOF pairs
24 × 15 = 360 through-focus rows
```

---

## 2. 新增实现

### 2.1 TASK-013 identity / manifest / power-envelope gate

```text
src/whole_eye_mvp/task013_native_reference.py
```

负责：

- `N0 = native/untreated reference cornea`；
- 6-carrier/24-config/12-pair extension identity；
- N0 carrier lock/hash；
- frozen residual provenance 继承；
- residual power-envelope fail-closed preflight。

N0 不改变 A0/B0/C0 的 frozen enum/baseline/manifest。

### 2.2 N0 OpticStudio carrier 与 production backend

```text
src/whole_eye_mvp/task013_zos.py
```

负责：

- 复用 TASK-007 的 actual-eye P → standard-eye Q(P) → actual-eye recheck 逻辑；
- 每个 Base×N0×Platform 独立求 carrier；
- final actual-eye R/Q replay；
- final STD_IOL_EYE_2024 SA replay；
- materialize TASK-013 MONO/EDOF config；
- 复用 TASK-009 paired-MONO angular scale backend；
- 在分析前把 config EPD 写入并保存 `.zmx`。

### 2.3 正式 runner

```text
scripts/run_task_013_native_reference.py
```

正式顺序：

```text
N0 reference cornea
→ 2 Q=0 base starts
→ 6 platform-specific P/Q carriers
→ residual power-envelope gate
→ 12 paired-MONO EFFL references
→ 24 production configs
→ per-config result validation
→ canonical ZMX archive
→ MODEL_INDEX verification
→ optional sanitized repo evidence
```

### 2.4 通用 ZMX archive helper

```text
src/whole_eye_mvp/model_archive.py
```

提供：

- SHA-256；
- copy + post-copy hash verification；
- project-relative path enforcement；
- `MODEL_INDEX.csv`；
- index path/SHA replay validation。

### 2.5 TASK-011 retroactive archive

```text
scripts/archive_task011_zmx_models.py
```

该脚本不启动 OpticStudio，不重新计算任何 MTF；只把已有 TASK-011 模型做稳定归档和索引。

---

## 3. ZMX 语义审核

### 3.1 TASK-013 新配置

TASK-013 新 backend 在 production analysis 前显式执行：

```text
prepare carrier / residual
→ load model
→ set config pupil (EPD3 or EPD5)
→ validate nominal model
→ SaveAs config model.zmx
→ compute model hash
→ start through-focus acquisition
```

因此 TASK-013 的：

```text
models/task013_native_reference/runs/<run_id>/configs/<config_id>.zmx
```

是 config-specific 保存文件，包含该配置的瞳孔设置，并与 `ConfigResult.model_hash_before` 做 hash binding。

### 3.2 TASK-011 历史配置

TASK-011 旧 production code 的顺序是：

```text
prepare model.zmx
→ hash file
→ LoadFile
→ _assert_loaded_nominal_model() sets config pupil in memory
→ analysis
```

旧代码没有在设置 EPD3/EPD5 后再次 `SaveAs`。因此，已有：

```text
results/task011_run72/<run_id>/<config_id>/model.zmx
```

应严格称为**per-config analyzed source model snapshot**，而不是声称其文件 bytes 必然持久化了全部运行时 system settings。

这不影响 TASK-011 数值结果，因为正式分析在内存中使用了 manifest 指定的 EPD，并且 `pupil_mm` 已进入 structured evidence；但在模型归档语义上应保持这一历史事实。

因此 retroactive archive 使用：

```text
model_role = analyzed_config_source_snapshot
model_role = pair_mono_reference_source_snapshot
```

同时在 `MODEL_INDEX.csv` 中绑定对应 `pupil_mm`，确保可重建运行条件。

如果未来需要把 TASK-011 也 materialize 成“打开文件即包含 EPD3/EPD5”的 exact config snapshots，可以另做一次**只加载/设置系统孔径/SaveAs、完全不重新分析 MTF**的 OpticStudio materialization；这不是 TASK-011 科学结果重跑的前置条件。

---

## 4. Canonical ZMX 目录

### TASK-013

```text
project_mvp_2026_v2_zmx/
└─ models/
   └─ task013_native_reference/
      ├─ cornea/
      │  └─ N0_REFERENCE_CORNEA.zmx
      ├─ carriers/
      │  └─ CAR_<base>_N0_<platform>.zmx      # 6
      └─ runs/
         └─ <run_id>/
            ├─ pair_references/
            │  └─ <pair_key>.zmx              # 12
            ├─ configs/
            │  └─ <config_id>.zmx              # 24
            └─ MODEL_INDEX.csv
```

### TASK-011 retrospective archive

```text
project_mvp_2026_v2_zmx/
└─ models/
   └─ task011_run72/
      └─ archive/
         └─ <run_id>/
            ├─ configs/                         # 72 source snapshots
            ├─ pair_references/                 # 36 source snapshots
            └─ MODEL_INDEX.csv                  # + 18 existing physical carriers indexed
```

TASK-011 archive index total记录数：

```text
72 config source snapshots
+ 36 pair-reference source snapshots
+ 18 physical carriers
= 126 records
```

---

## 5. 离线质量门

首次代码 head 的 unit tests 通过，但 Ruff 报4个 `B009` 静态风格问题；均为同一 residual provenance helper 中的固定属性 `getattr()` 写法，不涉及科学逻辑。

修复后 head：

```text
0473737a870facfc50c429b19665074cc058adb6
```

GitHub Actions：

```text
Offline quality gate
run_number = 131
run_id = 32396473385
conclusion = success
```

通过：

```text
pytest: 218 passed
ruff: PASS
compileall: PASS
uv lock --check: PASS
```

当前 Web 侧没有执行 OpticStudio，也没有生成任何新的 N0 光学数值。

---

## 6. 本地执行顺序

### 6.1 先归档既有 TASK-011 ZMX（无需 OpticStudio）

```powershell
uv run python scripts/archive_task011_zmx_models.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx"
```

该步骤只复制/hash/index，不改变已有结果。

### 6.2 再执行 TASK-013（需要 OpticStudio/ZOS-API）

```powershell
uv run python scripts/run_task_013_native_reference.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence
```

如果未通过环境变量提供 OpticStudio 安装目录，再增加：

```text
--install-dir <OpticStudio install dir>
```

### 6.3 正式本地 acceptance

必须得到：

```text
native carriers = 6
residual power-envelope = PASS
pair references = 12
completed configs = 24
failed configs = 0
through-focus rows = 360
matched pairs = 12
model_archive_complete = true
acceptance_passed = true
```

随后再进入 Web 独立审核与 N0/A0/B0/C0 全贯焦补充材料绘图。

---

## 7. 当前 STOP

现在不应直接修改论文主结果，也不应提前把 N0 当作已获得的数据。

下一步必须先在本地执行上述 TASK-013 acquisition；如果 residual power-envelope gate 失败，应把实际 N0 carrier powers 带回 Web 审核，先决定 residual replay validation，再继续 EDOF acquisition。
