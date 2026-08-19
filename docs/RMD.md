# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** Build Path / Route-Runbook-Execution Map。只规定安全实现顺序、测试闸门、Git checkpoint 与 STOP；科学定义由 URD/TDD 提供。

## Metadata

- document_id: `RMD-0001`
- version: `1.6`
- status: `active`
- source_docs: `URD-0001 v1.6`, `ADD-0001 v1.6`, `MDD-0001 v1.5`, `TDD-0001 v1.6`
- last_updated: `2026-08-19`
- implementation_language: Python
- package_manager: uv
- default_branch: main
- active_task_branch: `feat/task-009-fft-mtf-main`

---

# 1. Dual-environment execution model

## Web

负责科学研究/规范/冻结决策、Python 主代码与测试、GitHub static review、读取结构化 evidence、决定是否进入下一 task。

## Local Windows / ZCode

负责真实 OpticStudio/ZOS-API、API enum/header/cast/runtime behavior、`.zmx` 实机结果、integration/full-flow smoke，以及明确允许范围内的机械 API 适配。

## Handoff rule

- 大任务尽量单次批量执行；
- JSON/CSV evidence 优先推 GitHub；
- 本地回复只给 commit/path/hash/PASS/FAIL/关键 summary；
- science definition 变化必须回 Web；
- 本地不得自行把 sampling candidate 变成 formal sampling lock。

---

# 2. Development conventions

```text
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

unit tests 不依赖 OpticStudio；真实 ZOS diagnostics 只在 Windows workstation；scientific artifacts 必须 hash/provenance；formal locks 同 ID 不允许不同内容覆盖。

---

# 3. Completed build path

| Task | Status | Frozen output |
| --- | --- | --- |
| TASK-001 | complete | uv/src/tests/git skeleton |
| TASK-002 | complete | ZOS session lifecycle validated |
| TASK-003 | complete | domain + ProjectStore + hash/run provenance |
| TASK-004 | complete then migrated | pure metric layer now FFT-MTF/MTFa v2 |
| TASK-005 | complete | LB/ATC、standard eye、A0/B candidates/C0 |
| TASK-006 | complete | B0.20 immutable lock |
| TASK-007 | complete | 18 P/Q、3 residuals、9 calibrations、TDD-999 cleared |
| TASK-008 | complete | 18 formal carrier locks、3 residual locks、72-config manifest |

TASK-008 formal identity：

```text
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
```

从 TASK-009 起只读。

---

# 4. Current task — TASK-009

## Goal

在 Run72 前一次验证新的主分析方法及**真实 production execution contract**：

```text
frozen TASK-008 manifest
→ ZosFftMtfAnalysisBackend
→ OpticStudio FFT MTF / EFFL / HOA / footprint
→ MTFa / DOF50 / TF_MTFa_mean
→ ConfigResult
→ run_analysis_batch
→ artifact/run/environment provenance
→ matched pair deltas
```

active main settings：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

HOA readback：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

## Web checkpoint — review hardened

Web 必须在 local run 前完成：

- active URD/ADD/MDD/TDD/RMD synchronization；
- strict frozen-manifest loader；
- exact main/HOA settings hash regression；
- FFT MTF runtime API metadata capture；
- real `ZosFftMtfAnalysisBackend`；
- in-memory entity fingerprint；
- ConfigResult/acceptance migration；
- representative script 使用 frozen config IDs；
- 6-config integration 经 `run_analysis_batch`；
- active-source/script/spec regression gate。

## Local TASK-009 batch

### Stage A — sync/offline regression

1. checkout expected Web HEAD；
2. clean status、OpticStudio process=0；
3. full pytest/ruff/compileall/uv-lock；
4. 机械性 stale constructor/import/API wrapper 问题可最小修复并继续；
5. 不允许改 scientific threshold/settings/representative set。

### Stage B — frozen manifest reload

在启动 OpticStudio 前：

- physical CSV SHA 与 TASK-008 evidence 一致；
- nominal CSV SHA 一致；
- strict 18/72 reload；
- rebuild manifest hash 一致；
- lock-set hash 一致；
- frozen representative 6 config IDs 可唯一选择。

任何差异立即 STOP，不启动 optical acquisition。

### Stage C — real FFT MTF / EFFL / HOA capability

验证并记录：

- `New_FftMtf()`；
- settings implementation type；
- sample enum mapping64/128/256；
- modulation enum；
- DataSeries count/runtime type；
- selected series type；
- labels/XLabel；
- EFFL temporary operand；
- ZERN Z7..Z28 temporary operands；
- 60-cpd coverage。

真实 API 差异可机械适配；不得猜列位置。

### Stage D — sampling convergence

冻结代表 EDOF：

```text
LB+A0+WFS+EPD3
ATC+B0+RAD+EPD5
ATC+C0+HOA+EPD5
```

每个 64/128/256 ×15 planes。

128→256：peak MTFa relative≤2%；TF mean relative≤2%；peak shift≤0.25D；DOF50 width change≤0.25D。

任一 fail：尽量完成三个 representative evidence 后 exit nonzero；不得自行改 sampling。

### Stage E — repeatability

每 EDOF representative 独立再跑一次128：peak sample identical、peak MTFa relative≤0.1%、TF mean≤0.1%、C4/C6≤0.001µm。

### Stage F — six-config real production integration

三个 frozen pair 的 MONO+EDOF 共6 configs 必须由：

```text
ZosFftMtfAnalysisBackend
→ run_analysis_batch
```

运行。

必须验证：

- frozen manifest config identity；
- formal carrier/residual hashes；
- RunEnvironment；
- running/completed/failed states；
- complete ConfigResult；
- analysis/HOA settings hashes；
- working model hash；
- entity fingerprint before/after；
- retina/IOL/ELP invariants；
- footprint/vignetting；
- required artifacts；
- matched delta / `DeltaF_residual`。

独立 probe 手工输出不算本阶段 PASS。

### Stage G — limited extraction diagnostic

MFE `MTFA Grid=1` 或同 family 独立 export/readback，在20/40/60 cpd比较少量值。只记录 frequency、两种 acquisition、absolute differences、actual API mapping；不新增 threshold。

### Stage H — GitHub evidence

结构化 evidence：

```text
docs/evidence/task009/TASK_009_FFT_MTF_REPRESENTATIVE_EVIDENCE.json
docs/evidence/task009/TASK_009_REPRESENTATIVE_THROUGH_FOCUS.csv
```

large `.zmx` 留 project diagnostics/results，不进 Git。

Local evidence 必须：

```text
evidence_only = true
formal_artifact = false
run72_started = false
production_sampling_candidate_passed = <computed>
production_sampling_locked = false
```

## TASK-009 Done When

1. offline checks PASS；
2. strict manifest reload PASS；
3. real API/EFFL/HOA PASS；
4. three convergence gates PASS；
5. three repeatability gates PASS；
6. real 6-config batch integration PASS；
7. Web review 接受 independent extraction diagnostic；
8. Web 写正式 production-sampling lock；
9. docs/status synchronized。

---

# 5. TASK-010

TASK-009 PASS 后只做：

- 将已经验证的 `run_analysis_batch` 接到现有 GUI action dispatch；
- 本地最小 GUI/full-flow smoke；
- progress/log/failed-target rerun UI 验证。

**TASK-010 不再负责首次实现或首次验证 real AnalysisBackend。**

---

# 6. TASK-011 / Run72

Depends on TASK-009 formal sampling lock（以及需要时 TASK-010 smoke）。

Run72：18 carriers × MONO/EDOF × EPD3/5 =72 configs；每 config15 planes→1080 rows。

Acceptance：exact72 completed IDs==manifest、36 matched deltas、1080 rows、all required artifacts/environment/settings/manifest/lock identities；failed 不计 completed；failed-only rerun 使用新 run ID。

---

# 7. Git checkpoints

```text
feat/task-009-fft-mtf-main
  1. Web analysis migration
  2. Web review-hardening
  3. local mechanical compatibility fixes
  4. TASK-009 evidence
  5. Web cross-check review + formal sampling lock + status sync
```

之后才进入 Run72 分支或合并 main。

---

# 8. Current STOP conditions

1. TASK-005–008 frozen assets 不得被 TASK-009 修改。
2. strict frozen manifest reload 不通过不得启动 real analysis。
3. sampling convergence/repeatability 未 PASS 不得 Run72。
4. real 6-config batch integration 未 PASS 不得 Run72。
5. independent extraction diagnostic 未经 Web review 不得 Run72。
6. Web 未写正式 production-sampling lock 不得 Run72。
7. 若128不满足 gate，必须回 Web 版本化新 settings ID。
8. API 机械问题可同一大任务最小修复；science definition 变化立即 STOP。
