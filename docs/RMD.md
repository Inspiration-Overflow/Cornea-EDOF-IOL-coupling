# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 提供。

## Metadata

- document_id: `RMD-0001`
- version: `1.5`
- status: `active`
- source_docs: `URD-0001 v1.5`, `ADD-0001 v1.5`, `MDD-0001 v1.4`, `TDD-0001 v1.5`
- last_updated: `2026-08-19`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-009-fft-mtf-main`

---

# 1. Dual-environment execution model

## Web

负责：

- 科学研究、规范、冻结决策；
- Python 主代码和测试；
- static review / GitHub integration；
- 读取 GitHub evidence 并做 science review；
- 决定是否进入下一 RMD task。

## Local Windows / ZCode

负责：

- 真实 OpticStudio/ZOS-API；
- API enum/header/cast/runtime behavior；
- `.zmx` 实机结果；
- 本地 integration/full-flow smoke；
- 在明确允许范围内做纯机械 API 适配；
- 结构化 evidence 推送 GitHub。

## Handoff rule

- 大任务尽量单次批量执行；
- 能由 GitHub 传递的 JSON/CSV 不在本地回复粘贴大块数据；
- 本地回复只给 commit、path、SHA-256、PASS/FAIL、关键 summary；
- science definition 变化必须回 Web，不能在本地试调。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

- 正式依赖只由 uv 管理；
- unit tests 不依赖 OpticStudio；
- 真实 ZOS tests/diagnostics 只在 Windows workstation；
- scientific artifacts 必须 hash/provenance；
- canonical lens format `.zmx`；
- formal locks 同 ID 不允许不同内容覆盖。

---

# 3. Completed build path

| Task | Status | Frozen output |
| --- | --- | --- |
| TASK-001 | complete | uv/src/tests/git skeleton |
| TASK-002 | complete | ZOS session lifecycle / worker assumptions validated |
| TASK-003 | complete | domain + ProjectStore + hash/run provenance |
| TASK-004 | complete then migrated | pure metric layer now FFT-MTF/MTFa v2 |
| TASK-005 | complete | LB/ATC、standard eye、A0/B candidates/C0 scientific assets |
| TASK-006 | complete | B0.20 immutable lock |
| TASK-007 | complete | 18 provisional P/Q solved、3 residuals、9 low/median/high calibrations、TDD-999 cleared |
| TASK-008 | complete | 18 formal carrier locks、3 residual locks、72-config manifest |

TASK-008 formal identity：

```text
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
```

这些资产从 TASK-009 起只读。

---

# 4. Current task — TASK-009

## Goal

在 Run72 前验证 `NOMINAL_MAIN_FFT_MTF_555_v2`：

```text
OpticStudio FFT MTF
→ tangential/sagittal average
→ cycles/mm→cpd
→ MTFa
→ distance peak / DOF50 / TF_MTFa_mean
```

TASK-009 不重建 carrier/residual/manifest。

## Web checkpoint

Branch：

```text
feat/task-009-fft-mtf-main
```

Web 必须先完成：

- active URD/ADD/MDD/TDD/RMD migration；
- `NOMINAL_MAIN_FFT_MTF_555_v2`；
- FFT MTF ZOS primitive；
- EFFL primitive；
- MTFa/DOF50 pure-math engine；
- ConfigResult/acceptance migration；
- consolidated representative script；
- regression test that blocks removed production analysis paths from returning。

## Local TASK-009 batch

一次本地任务按以下阶段执行。

### Stage A — sync/offline cleanup

1. checkout expected Web HEAD；
2. clean status、OpticStudio process=0；
3. full unit/ruff/compileall/uv-lock；
4. 对 stale constructor/import/doc mechanical issues 做最小修复；
5. 不允许改 scientific threshold/settings/representative set。

### Stage B — real FFT MTF capability

验证：

- `New_FftMtf()`；
- real settings object / enum names；
- DataSeries access；
- tangential/sagittal labels；
- cycles/mm units；
- EFFL temporary MFE operand；
- 60-cpd coverage。

API 差异可在同一任务内机械修复并继续。

### Stage C — sampling convergence

冻结代表 EDOF：

```text
LB+A0+WFS+EPD3
ATC+B0+RAD+EPD5
ATC+C0+HOA+EPD5
```

每个：64/128/256 × 15 planes。

128→256 gate：

- distance-peak MTFa relative ≤2%；
- TF_MTFa_mean relative ≤2%；
- peak shift ≤0.25 D；
- DOF50 width change ≤0.25 D。

任一 fail：完成全部三个 representative evidence 后 exit nonzero，STOP；不得自行改 sampling。

### Stage D — repeatability

每个 representative EDOF 再跑一次 128：

- peak sample identical；
- peak MTFa relative ≤0.1%；
- TF mean relative ≤0.1%；
- C4/C6 ≤0.001 µm。

### Stage E — six-config integration

对三个 representative pair 各运行 MONO+EDOF 128：共 6 configs。

记录：

- 15 through-focus rows；
- MTFa / MTF10..60；
- distance peak；
- DOF50；
- TF_MTFa_mean；
- C4/C6/HOA RMS；
- `DeltaF_residual`；
- formal carrier/residual source SHA。

### Stage F — limited independent extraction diagnostic

使用 MFE `MTFA Grid=1` 或同 FFT-MTF family 的独立 data export，在 20/40/60 cpd 比较少量值。

只记录：

- frequencies；
- two acquisitions；
- absolute differences；
- actual API mapping。

不新增 threshold，不因差异“调”主 settings。

### Stage G — GitHub evidence

结构化 evidence：

```text
docs/evidence/task009/TASK_009_FFT_MTF_REPRESENTATIVE_EVIDENCE.json
docs/evidence/task009/TASK_009_REPRESENTATIVE_THROUGH_FOCUS.csv
```

large representative `.zmx` 留本地 diagnostics，不进 Git。

## TASK-009 Done When

- offline checks PASS；
- capability PASS；
- three convergence gates PASS；
- three repeatability gates PASS；
- 6-config integration PASS；
- Web review 接受 independent extraction diagnostic；
- production sampling 正式锁定；
- active docs/status synchronized。

---

# 5. TASK-010

TASK-009 PASS 后：

- 将 real AnalysisBackend 接入 GUI workflow；
- 本地做最小 full-flow smoke；
- 保持一个 long action / explicit progress / failed-target rerun；
- GUI 不改变 scientific state。

TASK-010 不负责重新验证 sampling scientific gate。

---

# 6. TASK-011 / Run72

Depends on TASK-009 PASS（以及需要时的 TASK-010 smoke）。

Run72：

```text
18 carriers
× MONO/EDOF
× EPD3/EPD5
= 72 configs
```

每 config 15 planes → total 1080 through-focus rows。

Acceptance：

- exactly 72 completed config IDs == manifest；
- exactly 36 matched pair deltas；
- no duplicate/missing IDs；
- each config 15 rows；
- all required artifacts；
- all environment/manifest/lock identities match；
- failed config 不计 completed；
- failed-only rerun 产生新 run_id。

---

# 7. Git checkpoints

建议：

```text
feat/task-009-fft-mtf-main
  1. Web analysis migration commits
  2. local mechanical compatibility fixes
  3. TASK-009 evidence commit
  4. Web review/status sync
```

之后才进入 Run72 分支或合并 main。

不要把 generated project `.zmx`、Grid Sag DAT、大型临时分析文件提交到 Git；只提交必要 structured evidence。

---

# 8. Current STOP conditions

1. TASK-005–008 frozen assets 不得被 TASK-009 修改。
2. TASK-009 sampling convergence 未 PASS 前不得 Run72。
3. TASK-009 repeatability 未 PASS 前不得 Run72。
4. representative 6-config integration 未 PASS 前不得 Run72。
5. independent extraction diagnostic 未经 Web review 前不得 Run72。
6. 若 128 sampling 不满足 gate，必须回 Web 版本化新的 settings ID，不允许本地临时接受。
7. 若 API 机械问题可修，允许在同一大任务内修复并继续；若需要改变 science definition，立即 STOP。
