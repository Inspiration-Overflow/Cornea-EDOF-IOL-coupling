# RMD 执行状态

> `RMD-0001 v1.6` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门；科学定义以当前 active URD/TDD 与 TASK-009 analysis freeze 为准。

## 当前项目

```text
Scientific baseline = MVP_2026_v2
canonical OpticStudio lens format = .zmx
active local project = project_mvp_2026_v2_zmx
active development branch = feat/task-009-fft-mtf-main
integration target = main
```

## 已完成并冻结

### Base / standard eye

- `LB_AL2395`: AL=23.950 mm。
- `ATC_M3_AL24477`: AL=24.477 mm。
- post-cornea→STOP=3.150 mm。
- post-cornea→IOL anterior=4.500 mm。
- `STD_IOL_EYE_2024`: EPD6、约546 nm、corneal C40≈+0.258 µm。

### Cornea

- A0 frozen；B0.20 immutable；C0 nominal N=8 frozen。
- B0 lock SHA256: `24c25fea95db394998c0a4dd2ef7b0499e1e792c1275c117c23faeba0d2ea06c`。

### TASK-007 — complete

- 18 power-specific P/Q carriers；
- WFS/RAD/HOA residuals；
- 9 low/median/high actual-power calibrations；
- three mechanism reviews PASS；
- `TDD-999` cleared。

review evidence：

```text
docs/evidence/task007/consolidated_review/TASK_007_CONSOLIDATED_REVIEW.json
SHA256 c11b70f9ed5c2cb874484900445e62be8fc71ad05540a7cac7f12fa6b67ee93a
commit 935415efe5152f9318654a60161aaa632c49540d
```

RAD source-batch actual-eye low-order false negative 已解释为 aperture-limited SSAG Mode-0 诊断行为；正式 gate 保持 EPD6 standard-eye imported residual readback，未修改 residual 或 tolerance。

### TASK-008 — complete / formal

```text
physical carriers = 18
residual locks = 3
nominal configs = 72
matched pair keys = 36
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
formal_artifact = true
selection_locked = true
tdd_999_cleared = true
```

formal evidence：`docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json`，commit `d4a8f96bce50e01078623fbcbda015374967344a`。

TASK-005–008 assets/hash 从 TASK-009 起只读。

---

## 主分析架构

唯一主链：

```text
frozen TASK-008 nominal manifest
→ OpticStudio FFT MTF
→ sagittal/tangential modulation average
→ cycles/mm → cycles/degree
→ 0..60 cpd common grid
→ MTFa + MTF10/20/30/40/50/60
→ distance peak / DOF50 / TF_MTFa_mean
→ MONO vs EDOF paired deltas
```

main settings：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
SHA256 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

HOA readback：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

DOF50 固定为 50% distance-peak MTFa；不是可调 main settings 字段。

---

## TASK-009 Web review-hardening

在原 analysis migration 后完成了一次独立文档/代码审查。发现并修订了以下结构问题：

1. 代表 6-config integration 原先绕过正式 batch workflow；现已实现 `ZosFftMtfAnalysisBackend`，并要求经 `run_analysis_batch()`。
2. 代表配置原先由脚本重新拼 identity；现由 strict TASK-008 manifest loader 读取 frozen config IDs。
3. `TRACE.md` 原先仍是旧 ID universe；现重建为 URD1.6/ADD1.6/MDD1.5/TDD1.6 current trace，checker 同步更新。
4. `ConfigResult` 原先不能证明内存中 carrier P/R/Q 未变；现新增 entity fingerprint before/after，并排除唯一允许临时改变的 OBJECT vergence。
5. main settings 原先混入 B0/Zernike unrelated fields；现 main settings 只含真正影响 FFT-MTF/MTFa 的参数，HOA readback 独立版本化。
6. FFT MTF evidence 现记录真实 API/settings implementation/sample enum/modulation enum/DataSeries runtime metadata。
7. URD 已补回仍有效的 GUI/rerun/audit/output 要求。
8. active-path regression test 现覆盖 production source、TASK-009/Run72 scripts 与 active specs。

### Web 已实现但尚未本地验证

- strict `load_formal_manifest_bundle()`；
- exact main/HOA settings hashes；
- real `ZosFftMtfAnalysisBackend`；
- in-memory optical entity fingerprint；
- manifest-driven 3 representative selection；
- 6-config `run_analysis_batch()` integration；
- ConfigResult settings/entity provenance；
- runtime FFT API metadata capture；
- real-ray footprint/vignetting；
- revised TASK-009 consolidated local script。

**重要：本轮 Web review-hardening 后尚未运行完整离线回归，也尚未启动新的 OpticStudio TASK-009 run。** 最后一个完整本地离线基线仍是 TASK-008 的 `190 passed`。

---

## TASK-009 下一本地 gate

冻结三个 pair：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

下一次本地任务应一次完成：

1. full offline pytest/ruff/compileall/uv-lock；
2. strict TASK-008 manifest reload/hash/lock-set；
3. real FFT MTF API/runtime metadata；
4. EFFL + 60-cpd coverage；
5. 3 EDOF ×64/128/256 convergence；
6. 3 EDOF × independent repeat128；
7. 6 frozen configs through real `run_analysis_batch()`；
8. entity fingerprint/footprint/artifact/run-environment validation；
9. limited 20/40/60 cpd extraction diagnostic；
10. sanitized GitHub evidence。

Local output 只能写：

```text
production_sampling_candidate_passed = <computed>
production_sampling_locked = false
run72_started = false
```

Web review evidence 后才允许 formal sampling lock。

---

## Task 状态

| Task | 状态 | 下一步 |
| --- | --- | --- |
| TASK-001~003 | 完成 | 保持 provenance/session rules |
| TASK-004 | metric layer migrated | TASK-009 real validation |
| TASK-005 | 完成 | frozen |
| TASK-006 | 完成 | B0.20 immutable |
| TASK-007 | 完成 | TDD-999 cleared |
| TASK-008 | 完成 | 18/3/72 formal frozen |
| TASK-009 | **Web migration + review-hardening complete；offline/OpticStudio validation pending** | 当前任务 |
| TASK-010 | GUI scaffold exists | TASK-009 后只做 GUI/full-flow smoke |
| TASK-011 | acceptance migrated | formal sampling lock 后 Run72 |

## 当前 STOP 条件

1. TASK-005–008 frozen assets 不得改写。
2. strict manifest reload 不通过不得启动 real analysis。
3. TASK-009 convergence/repeatability/real six-config integration 未通过不得 Run72。
4. independent extraction evidence 未经 Web review 不得 Run72。
5. `production_sampling_locked` 在 Web formal review 前必须为 false。
6. 128 不满足 gate 时必须版本化新 settings ID，不允许本地临时接受。
7. synthetic data 不得进入正式 TASK-009 evidence 或 Run72。
