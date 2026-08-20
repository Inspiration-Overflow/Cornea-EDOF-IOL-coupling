# TASK-013 / TASK-014 residual validation gate-domain restoration addendum

日期：2026-08-20  
状态：**authoritative correction**  
适用：`TASK-013-NATIVE-CORNEA-REFERENCE` 与 `TASK-014-VERTEX-CORRECTED-POSTOP-CORNEA`

## 1. 触发事件

TASK-013 第二次本地运行 `task013-2b0dfe62e0eb424a84ae0fe8da942253` 在 `CAR_ATC_M3_AL24477_N0_RAD` 的 exact-carrier residual validation 处停止。该 carrier 的 actual-eye residual low-order readback 为：

```text
piston ≈ -0.04204 µm
global defocus ≈ +0.09704 D
```

其中 piston 超过 `RESIDUAL_VALIDATION_546_v1` 的 0.010 µm 数值阈值，而 standard-eye low-order 与 MONO/EDOF ray-health 均通过。

复核 TASK-007 冻结审查后确认：该停止属于**验证域实现错误**，不是 RAD residual 新发现的物理失效。

## 2. TASK-007 原始规范性证据

`docs/evidence/task007/consolidated_review/TASK_007_CONSOLIDATED_REVIEW.json` 已明确冻结：

```text
low_order_hard_gate_domain = STD_IOL_EYE_2024_EPD6_imported_residual_readback
actual_eye_ssag_readback_role = diagnostic_only_aperture_limited_mode0
standard_eye_low_order_gate_passed = true
all_ray_health_passed = true
```

并明确规定：

```text
normative_low_order_gate = STD_IOL_EYE_2024 EPD6 imported residual readback
actual_eye_low_order_readback = diagnostic only; source SSAG Mode 0 is aperture-limited
actual_eye_hard_evidence = ray health + through-focus + whole-eye wavefront/mechanism behavior
```

TASK-007 对 RAD 的正式 mechanism decision 同样指出：actual-eye piston failure 是 aperture-limited SSAG Mode-0 readback artifact，不是 residual/mechanism failure；没有修改 residual seed、幅度、SA target、piston/defocus tolerance 或任何新的数值阈值。

因此，TASK-013/014 先前把 actual-eye piston/global-defocus readback 与 standard-eye low-order 一并升级为 exact-carrier hard gate，违背了 TASK-007 已冻结的 gate domain。

## 3. 修订后的数值 gate

从本 addendum 起，exact-carrier residual validation 的数值 hard gate 恢复为 TASK-007 原始语义：

### 3.1 Normative low-order hard gate

仅：

```text
STD_IOL_EYE_2024 EPD6 imported-residual readback
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

### 3.2 Actual-eye hard gate

```text
MONO EPD5 ray health = PASS
EDOF EPD5 ray health = PASS
```

要求所有验证射线 success、error=0、vignette=0。

### 3.3 Actual-eye SSAG low-order readback

仍必须测量、保存、报告，但角色固定为：

```text
diagnostic_only_aperture_limited_mode0
```

其 piston/global-defocus 是否超过 `RESIDUAL_VALIDATION_546_v1` 的数值阈值**不参与 exact-carrier numerical pass/fail**。

这不是放宽阈值，而是恢复原先已冻结的阈值适用域。

## 4. Power coverage 与 mechanism review

历史 TASK-007/008 carrier power 范围仍只表示：

```text
existing validation coverage
```

新 carrier 若在范围内：

```text
within_existing_coverage = true
```

新 carrier 若超出范围：

```text
within_existing_coverage = false
extension_validation_required = true
mechanism_review_pending_web = true
```

越界 carrier 在通过上述 exact-carrier numerical gate 后，允许完成 through-focus acquisition 与 ZMX 归档，以便获得机制审查所需的真实证据；但不得仅凭 local numerical acquisition 宣称 scientific acceptance。

## 5. TASK-013 / TASK-014 两阶段接受语义

### Local acquisition acceptance

只表示：

- physical carrier/P-Q/SA replay 完成；
- exact frozen residual SHA 绑定完成；
- standard-eye low-order hard gate PASS；
- actual-eye MONO/EDOF ray-health PASS；
- production configs、through-focus、ZMX archive 完整。

### Scientific acceptance

对于任何 `within_existing_coverage=false` 的 carrier，仍需 Web mechanism review。Web review 至少检查：

- through-focus mechanism 是否保持预期；
- whole-eye wavefront / mechanism signature 是否与平台定义一致；
- 无新的 ray pathology；
- 无需改变 residual bytes/hash/shape 或 carrier scientific identity。

只有 local acquisition PASS + required Web mechanism review PASS，才能把 TASK-013/014 标记为最终 scientific acceptance。

## 6. RAD 特殊说明

不得建立“RAD 专用放宽阈值”。

RAD 与 WFS/HOA 使用相同的规范性 gate-domain 规则：

- standard-eye low-order 是规范性低阶 hard gate；
- actual-eye SSAG low-order 是 diagnostic-only；
- actual-eye ray-health 是 hard gate；
- out-of-coverage 时进行 Web mechanism review。

`CAR_ATC_M3_AL24477_N0_RAD` 的约 -0.042 µm actual-eye piston 与 TASK-007 RAD 已记录的约 -0.043 µm 模式一致，因此应被记录为预期的 SSAG Mode-0 diagnostic artifact，而不是通过修改 residual 或阈值消除。

## 7. Provenance 与回退

本次修订前精确状态：

```text
branch = feat/task-011-run72
HEAD = 88490f590b52f7b1f4aa0f0a9f05e99daae6eeee
checkpoint = checkpoint/pre-task013-gate-domain-restore-2026-08-20
```

该 checkpoint 包含：

- residual power-envelope → validation-trigger 修订；
- exact-carrier validator 的旧实现（错误地把 actual-eye low-order 作为 hard gate）；
- 本地执行 bug fix `88490f5`。

不得删除该 checkpoint。

## 8. 明确不变项

本修订不改变：

- frozen WFS/RAD/HOA residual DAT bytes/hash/shape；
- `RESIDUAL_VALIDATION_546_v1` 数值阈值本身；
- TASK-007/008 locks；
- TASK-009 production settings；
- TASK-011/012 frozen evidence；
- N0、A0V12、B0V12、C0V12 scientific identities；
- 12 mm vertex contract；
- B0.20；
- EPD、sampling、defocus/peak windows。

## 9. 本地历史运行必须保留

以下两次 TASK-013 STOP run 均为正式审计轨迹，不得删除：

```text
task013-25e426e7c6d64d5aa59ffc089f352db2
  old terminal power-envelope gate

task013-2b0dfe62e0eb424a84ae0fe8da942253
  incorrect actual-eye low-order hard-gate implementation
```

下一次运行必须使用新 run_id，并保留以上 diagnostics。