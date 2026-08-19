# RMD 执行状态

> `RMD-0001` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门；科学定义以当前 active URD/TDD 与 `TASK_009_FFT_MTF_MAIN_ANALYSIS_FREEZE_2026-08-19.md` 为准。

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
- `STD_IOL_EYE_2024`: EPD6、约 546 nm、corneal C40≈+0.258 µm。

### Cornea

- A0 frozen。
- B0.20 immutable lock frozen。
- C0 nominal N=8 frozen。
- B0 lock SHA256: `24c25fea95db394998c0a4dd2ef7b0499e1e792c1275c117c23faeba0d2ea06c`。

下游不得根据 IOL/主实验结果回调 A0/B0.20/C0。

### TASK-007 — 完成

真实 OpticStudio evidence 已完成：

- 6 个 shared P0；
- 18 个 power-specific P/Q carriers；
- WFS/RAD/HOA 三个平台 residual；
- 每个平台 low/median/high actual-power calibration，共 9 项；
- WFS/RAD/HOA mechanism Web review 全部 PASS；
- `TDD-999` machine-readable gate 已解除。

正式 review evidence：

```text
docs/evidence/task007/consolidated_review/TASK_007_CONSOLIDATED_REVIEW.json
SHA256 c11b70f9ed5c2cb874484900445e62be8fc71ad05540a7cac7f12fa6b67ee93a
commit 935415efe5152f9318654a60161aaa632c49540d
```

RAD source batch 的 actual-eye low-order readback false negative 已解释为 aperture-limited SSAG Mode-0 诊断行为；正式 residual low-order gate 使用 `STD_IOL_EYE_2024 / EPD6 imported residual readback`。未修改 residual payload、piston tolerance 或 global-defocus tolerance，也不要求重跑 TASK-007。

### TASK-008 — 完成并正式锁定

正式 evidence：

```text
docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json
commit d4a8f96bce50e01078623fbcbda015374967344a
```

冻结：

```text
physical carrier locks = 18
residual locks = 3
nominal configurations = 72
matched pair keys = 36
manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
formal_artifact = true
selection_locked = true
tdd_999_cleared = true
```

TASK-008 的实体 carrier/residual/manifest identity 从此只读；TASK-009 的分析指标简化不改变上述 lock/hash。

## 主分析架构 — 2026-08-19 简化冻结

从 TASK-009 起，主分析只使用 OpticStudio **FFT MTF Analysis** 作为 diffraction image-quality acquisition。

唯一主链：

```text
OpticStudio FFT MTF
→ sagittal/tangential modulation average
→ cycles/mm → cycles/degree
→ 0..60 cpd common grid
→ MTFa + MTF10/20/30/40/50/60
→ through-focus distance peak / DOF50 / TF_MTFa_mean
→ MONO vs EDOF paired deltas
```

active settings ID：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
```

冻结候选生产条件：

- λ=555 nm；
- EPD3 / EPD5；
- field=0；
- defocus=+0.50→−3.00 D，step=−0.25 D，15 planes；
- FFT MTF nominal sampling candidate=128；
- convergence sampling=64/128/256；
- 0..60 cpd、1-cpd common grid；
- MTFa 为 0..60 cpd 平均积分；
- DOF50 以 distance-peak MTFa 的 50% 为阈值，并要求连续区间包含 distance peak；
- `TF_MTFa_mean` 为冻结贯焦区间内的平均 MTFa。

不再要求 PSF 图作为每个 nominal config 的正式 artifact。

完整冻结说明：

```text
docs/TASK_009_FFT_MTF_MAIN_ANALYSIS_FREEZE_2026-08-19.md
```

## TASK-009 当前状态

Web 端已经完成：

- FFT-MTF-only metric engine migration；
- new `NOMINAL_MAIN_FFT_MTF_555_v2` settings；
- `ConfigResult` / matched-pair metric contract migration；
- OpticStudio FFT MTF acquisition primitive；
- cycles/mm→cpd、MTFa、distance peak、DOF50、TF_MTFa_mean pure-math implementation；
- legacy main-analysis source entrypoints removal；
- regression test preventing removed paths from returning to production source。

尚待本地 Windows + OpticStudio 验证：

1. active docs/remaining stale tests 完成 deterministic migration 后全离线回归；
2. FFT MTF 2026 R1 API settings/data-series readback；
3. EFFL readback 与 frequency conversion；
4. 三代表 EDOF sampling 64/128/256 convergence；
5. 128-sampling repeatability；
6. 三代表 matched MONO+EDOF integration，共 6 configs；
7. limited FFT-family independent cross-check；
8. sanitized TASK-009 evidence 提交 GitHub。

冻结三个代表 pair：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

## Task 状态

| Task | 状态 | 下一步 |
| --- | --- | --- |
| TASK-001 | 完成 | 无 |
| TASK-002 | 完成；ZOS lifecycle 实机通过 | 保持进程约束 |
| TASK-003 | 完成 | 保持 provenance |
| TASK-004 | pure metric layer 已迁移至 FFT-MTF v2 | TASK-009 实机验证 |
| TASK-005 | 完成；核心资产冻结 | 下游只读 |
| TASK-006 | 完成；B0.20 immutable | 下游只读 |
| TASK-007 | **完成；TDD-999 cleared** | 无 |
| TASK-008 | **完成；18/3/72 formal locks/manifests frozen** | 无 |
| TASK-009 | **Web migration complete；local FFT-MTF validation pending** | 当前任务 |
| TASK-010 | GUI scaffold complete | TASK-009 后 full-flow smoke |
| TASK-011 | acceptance framework migrated to MTFa | TASK-009 通过后才 Run72 |

## 当前 STOP 条件

1. TASK-005/006/007/008 已冻结资产不得被 TASK-009 重写。
2. TASK-009 三代表配置 sampling convergence / repeatability 未通过前不得 Run72。
3. 若 128 sampling 不满足冻结 convergence gate，不得临时接受；必须在 Web 端版本化新 production settings。
4. 若真实 FFT MTF API/header 与当前实现不同，只允许机械性 API 适配；不得改变主指标定义。
5. synthetic data 不得进入正式 TASK-009 evidence 或 Run72 结果。

## 双环境工作方式

Web 端负责科学定义、规范、主要代码和 Git 审核；本地 ZCode 负责 Windows + OpticStudio 实机验证与纯机械 API 适配。结构化 evidence 优先提交 GitHub，本地回复只回摘要、commit、路径、SHA-256 和异常，避免大块数据进入本地 AI 上下文。
