# RMD 执行状态

> `RMD-0001 v1.7` 的执行伴随记录。本文只记录当前真实状态、不可变上游资产和下一执行闸门。

## 当前项目

- baseline：`MVP_2026_v2`
- active branch：`feat/task-011-run72`
- TASK-005/006/007/008：完成并冻结
- TDD-999：cleared
- TASK-009：**complete**
- production sampling：**128，正式锁定**
- Run72 Web clearance：**AUTHORIZED**
- TASK-011 Web runner：**IMPLEMENTED / CI PASS**
- TASK-011 formal Run72：**COMPLETE / ACCEPTED**
- TASK-011 Web independent evidence review：**PASS**
- TASK-012：**analysis plan frozen；纯 Web/offline analysis next**
- 新增 TASK-009 representative OpticStudio 复验：**不需要**
- 新增 TASK-011 OpticStudio rerun：**不需要**

## 不可变正式身份

```text
carrier_count = 18
residual_count = 3
nominal_config_count = 72
pair_key_count = 36

manifest_hash =
29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49

lock_set_hash =
b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923

analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 =
0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 =
f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d

frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
```

TASK-011/TASK-012 对 TASK-005–009 scientific/method locks 只读。

---

## TASK-009 已完成

Corrected paired-MONO-scale representative evidence 已完成并经 Web 审核：

```text
evidence commit = 47f901dad36fb9d407826a6da8baceeef4c2edfd
JSON SHA256 = 404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49
CSV SHA256 = e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006
```

128→256 convergence、repeatability、6-config production integration、entity/ray-health、fixed-frequency diagnostic 全部 PASS；不启动256→512 escalation。

RunEnvironment/backend provenance 已 fail-closed 绑定 acquisition contract ID/hash 与 `paired_residual_free_MONO_EFFL`；旧 `AS_FftMtf` 和其他已退休的 pre-TASK009 production routes 不属于当前生产路线，per-state-EFL production 语义也已退休。

---

## TASK-011 正式 Run72 已完成

正式 Run72 的 Web 代码基点：

```text
01f13b768cf1eca361703469b2fdce3d21f3376d
```

正式 evidence commit：

```text
f28b3032136aa28f54abb5fe5129765a125d3926
```

唯一 run：

```text
run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
resume_mode = false
completed configs = 72
failed configs = 0
matched pairs = 36
through-focus rows = 1080
pair-reference records = 36
acceptance_passed = true
run72_complete = true
```

角尺度 reference set：

```text
pair_reference_set_sha256 =
a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d
```

正式 evidence：

```text
docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json
SHA256 = 9044898ca71109269b1a35bd5f8701d682bad125e819c54afe50593341e0aa51

docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv
SHA256 = 337628d95529a3711f36e7ea250ef435413d8f6aff11c25739e3c9b9ccc69dfa

docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv
SHA256 = cb4ece26a0a5d3a931db52a5f3b7e3325a99cbe26c9e175abd12bec5b7ec79da

docs/evidence/task011/TASK_011_RUN72_PAIRED_DELTAS.csv
SHA256 = 03dfe506566f83f6868c72890c042389ed8d0cd370255967fd1ff3b1ca25fa62
```

Web 已从 GitHub evidence 独立审核：配置完整、无 failed config、无 resume 混入、provenance/identity 一致，无理由重跑 OpticStudio。

---

## TASK-011 censoring 状态

Run72 acceptance 与 censoring 是两个不同层级：批次计算通过，但部分派生指标是预注册窗口边界受限值。

### distance peak censoring

`peak_search_censored=true` 的 EDOF 配置中，`distance_peak_retina_d=-0.50 D` 只表示最佳点达到或越过预注册距离峰搜索边界；相应 `DeltaF_residual` 也属于边界受限值。不得解释为无限制精确峰位。

主要集中于 EPD5，尤其 A0/B0 × HOA-like，以及 B0 × RAD-like/WFS-like；两个基础眼均可出现。

### DOF50 far-side censoring

已明确的 EDOF 配置：

1. ATC + B0 + WFS-like + EPD3
2. LB + B0 + WFS-like + EPD3
3. ATC + C0 + HOA-like + EPD5
4. ATC + C0 + RAD-like + EPD5
5. LB + C0 + RAD-like + EPD5

其 `dof50_width_d` 为受限值/下限，不得与 uncensored width 等价解释。

TASK-012 必须从 config-level evidence 把 censor flags 传播到 pair-level 结果；不能只读取 `TASK_011_RUN72_PAIRED_DELTAS.csv` 后直接排名。

---

## TASK-012 当前任务

正式分析计划：

```text
docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md
```

TASK-012 使用 `f28b303...` 的四个 TASK-011 evidence 文件作为唯一正式数据源，不启动 OpticStudio。

主分析单元：36 个 matched MONO–EDOF pairs。

因素：

```text
Base: LB / ATC
Cornea: A0 / B0 / C0
Platform: WFS / RAD / HOA
Pupil: EPD3 / EPD5
```

主要 paired outcomes：

```text
Delta DOF50_width
Delta distance_peak_mtfa
Delta mtfa_at_zero_d
Delta tf_mtfa_mean
Delta C40
Delta C60
Delta HOA_RMS
Delta F_residual
```

分析以描述性 factorial contrasts、interaction contrasts、effect ranges、rank stability、pupil/base sensitivity 和 censor-aware interpretation 为主；不把 36 个确定性模拟 pair 当作随机临床样本做传统 p-value 推断。

---

## 下一执行

下一步为纯 Web/offline TASK-012：

1. 从 config-level evidence 重建并验证36个 paired deltas；
2. 将 config-level censor flags 传播到 pair-level；
3. 从1080-row through-focus evidence 复核 `mtfa_at_zero_d` 与 `tf_mtfa_mean`；
4. 计算 cornea × platform interaction、pupil/base sensitivity；
5. 生成3×3耦合矩阵、through-focus 曲线和收益—质量代价图；
6. 完成单元测试、代码 review、结果 review 后再进入论文级解释。

TASK-010 GUI 不是 TASK-012 前置条件。

---

## 当前 STOP

- 不修改 TASK-005–009 frozen assets/method locks；
- 不重跑正式72 configs；
- 不因 censored peak/DOF 事后扩大 focus/search span 并补跑矩阵；
- 不恢复任何已退休的 pre-TASK009 production path；
- 不使用 EDOF-state/per-state EFFL 改变 matched-pair production angular scale；
- 不修改 B0.20；
- 不重新优化 residual profile；
- 不把 `DeltaF_residual` 写入 carrier physical lock identity；
- 不把确定性36-pair矩阵直接当随机临床样本做传统显著性检验；
- TASK-012 离线一致性检查失败时停止结果解释，先返回 evidence/code review，不启动 OpticStudio 作为默认修复手段。
