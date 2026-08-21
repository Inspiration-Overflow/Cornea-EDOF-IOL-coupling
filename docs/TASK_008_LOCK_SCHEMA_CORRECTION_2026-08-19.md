# TASK-008 Carrier Lock Schema 一致性修订

> 日期：2026-08-19  
> 性质：**URD 一致性修订；不改变任何光学科学参数**  
> 适用：TASK-008 formal carrier/residual locks 与 nominal manifest

## 1. 问题

旧实现把 `delta_f_residual_d` 放入 `CarrierLock`，并进一步纳入 carrier lock hash。

这与 URD-0001 v1.4 的因果定义不完全一致。

URD 对 `ΔF_residual` 的定义是：

> physical carrier 冻结后加入 residual；如果最佳远焦发生变化，该变化作为 `ΔF_residual` **记录为结果**，而不是重新设计或定义另一枚 carrier。

此外，主实验还要求在不同 pupil/analysis condition 下输出 `ΔF_residual`。因此它天然属于分析结果，而不是 physical carrier 的不变量。

## 2. 为什么旧 schema 不合理

如果 `ΔF_residual` 进入 physical lock hash，会产生两个问题：

1. 同一枚完全相同的实体 carrier + residual，仅因 pupil 或最佳焦点 metric 不同就可能得到不同 lock identity；
2. TASK-007 只要求每个平台在 low/median/high actual powers 做 residual calibration。若 TASK-008 要求 18 个 lock 都预先拥有 `ΔF_residual`，就会迫使程序：
   - 额外运行 9 个未预注册的测量；或
   - 在 9 个 calibration point 之间复制/插值结果。

两者都不是 URD 要求，也不符合 MVP 的最小设计原则。

## 3. 修订后的 physical lock identity

`CarrierLock` 只冻结：

```text
Base / Cornea / Platform
P
R_ant / R_post
Q
CT
material/index identity
IOL position
achieved SA calibration identity
residual_id
residual_sha256
residual_validation_policy_id/hash
```

lock hash 只由这些实体/科学 provenance 字段组成。

## 4. ΔF_residual 放在哪里

`ΔF_residual` 不删除，而是保留在正确的数据层：

### TASK-007 residual calibration evidence

每个平台 low/median/high calibration record 继续保存：

```text
distance_shift_d
```

用来证明同一个 residual 跨 power 的机制行为。

### TASK-009 / TASK-011 analysis result

正式 nominal configuration 分析按各自 pupil/through-focus metric 计算并输出：

```text
ΔF_residual = F_best(EDOF) - F_best(MONO)
```

这是 URD 要求的最终结果。

因此：

```text
DeltaF is preserved as evidence/result
!=
DeltaF is part of physical carrier identity
```

## 5. 对 MDD 的影响

本文件对 MDD-0001 v1.3 中以下两个旧表述作局部 supersede：

- `MDD-DATA-006` 中把 `ΔF_residual` 列为 `CarrierLock` frozen field 的部分；
- `MDD-API-008` 中若被解释为“18 个 lock 必须先拥有 18 个 ΔF”的部分。

其余 MDD 架构不变：

- CarrierWorkflow 仍负责 18 个 carrier/pair locks；
- ManifestBuilder 仍要求 exactly 18 locks；
- nominal manifest 仍 exactly 72 configs；
- AnalysisWorkflow 仍输出 `ΔF_residual` 和 paired delta。

下一次文档集中修订 MDD 时，应把本 addendum 合并进正文。

## 6. 代码映射

已同步修改：

```text
src/whole_eye_mvp/manifest.py
src/whole_eye_mvp/workflows.py
tests/unit/test_manifest.py
tests/unit/test_workflows.py
```

核心变化：

```text
CarrierLock.delta_f_residual_d
    removed

compute_carrier_lock_hash(... delta_f ...)
    → delta_f removed

finalize_carrier_locks(... delta_f_by_carrier_id ...)
    → delta_f map removed
```

`ResidualCalibration.distance_shift_d` 保留不变。

## 7. 科学影响

本修订：

- 不改变 P；
- 不改变 Q；
- 不改变 residual；
- 不改变 SA target；
- 不改变任何 pupil 或 through-focus settings；
- 不改变 `ΔF_residual` 的科学含义；
- 不删除任何已取得的 calibration ΔF 数据。

它只把一个 analysis-dependent result 从 physical lock identity 中移回正确的数据层。

## 8. TASK-008 执行边界

TASK-008 可以纯离线执行：

1. 读取已 reviewed TASK-007 evidence；
2. 逐个核验 18 个本地 carrier `.zmx` 与 3 个 residual `.DAT` 的 SHA-256；
3. 复制/登记到 canonical project path 并 immutable lock；
4. 构造 3 个 `ResidualDefinition`，保留 low/median/high `ResidualCalibration.distance_shift_d`；
5. 生成 exactly 18 physical lock rows；
6. 生成 exactly 72 nominal config rows；
7. 写 manifest hash 和 lock-set hash。

此过程不需要重新启动 OpticStudio，也不需要为另外 9 个 carrier 发明 `ΔF_residual`。
