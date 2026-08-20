# TASK-013 / TASK-014 residual power-extension 验证补充规范

日期：2026-08-20  
状态：**authoritative addendum；覆盖此前“power envelope 越界即终止研究”的解释**

## 1. 修订结论

TASK-013/TASK-014 中的 frozen residual power envelope 改为：

> **既有验证覆盖范围（existing validation coverage envelope）**

而不是：

> residual 的物理适用硬边界。

因此，新 carrier power 若超出既有 envelope，不再被解释为 residual 失效，也不再作为整个扩展研究的 terminal exclusion gate。

新的正式逻辑为：

```text
new carrier
→ compare with existing validated power envelope
→ inside envelope: existing coverage flag = true
→ outside envelope: existing coverage flag = false
→ 对该 exact carrier + exact frozen residual 执行 power-specific extension validation
→ validation PASS 后允许 EDOF production
```

frozen residual bytes/hash/shape 不允许改变。

---

## 2. 触发本次修订的实测现象

TASK-013 首次本地 carrier build 获得约：

```text
ATC_M3_AL24477 + N0 + WFS  = 19.2446 D
ATC_M3_AL24477 + N0 + RAD  = 19.3822 D
ATC_M3_AL24477 + N0 + HOA  = 18.9973 D
```

既有 TASK-007/TASK-008 power calibration coverage 约：

```text
WFS  = 21.0526–25.4766 D
RAD  = 21.1776–25.5871 D
HOA  = 20.8149–25.2587 D
```

这表示 ATC+N0 扩展到了旧术后角膜矩阵未覆盖的低 IOL power 区间；它本身不是 carrier 求解异常。

---

## 3. Power-extension validation 必须验证什么

沿用 TASK-007 consolidated residual calibration 的既有 numerical hard gates，不新建阈值。

对每个需要扩展验证的 `carrier + platform residual`：

### 3.1 Frozen residual identity

必须确认：

```text
residual_id unchanged
residual DAT SHA-256 unchanged
residual validation policy unchanged
```

禁止重生成一个不同 residual 并把它当作原 residual。

### 3.2 Actual-eye residual low-order readback

将 exact frozen residual 加到 exact actual-eye carrier，使用现有 `readback_residual_low_order()`。

必须满足 `RESIDUAL_VALIDATION_546_v1`：

```text
|measured piston| <= 0.010 µm
|measured global defocus| <= 0.125 D
```

### 3.3 Standard-eye residual low-order readback

将同一 carrier R/Q 放入 `STD_IOL_EYE_2024`，在 residual-free 与 frozen-residual 模型之间执行同样 readback。

必须满足同一 policy：

```text
|measured piston| <= 0.010 µm
|measured global defocus| <= 0.125 D
```

### 3.4 Actual-eye ray health

按 TASK-007 已验证的 batch-ray 规则，至少在 EPD5 对 residual-free MONO 与 frozen-residual EDOF 检查：

```text
ray success = true
error code = 0
vignette code = 0
```

两者均必须通过。

### 3.5 Hard-gate verdict

```text
extension_validation_passed =
    actual_low_order_pass
    AND standard_low_order_pass
    AND mono_ray_health_pass
    AND edof_ray_health_pass
```

若失败，只暂停该 task 的 EDOF production，并保存 diagnostics；不修改 residual 来追求通过。

---

## 4. 为什么不再把 envelope 本身作为 hard gate

旧 envelope 是从既有18个术后角膜 carrier 的 low/median/high calibration 自然形成的经验覆盖区间。

它回答的是：

> 这个 frozen residual 此前在哪些 carrier powers 上已经验证过？

它不直接回答：

> 在范围外是否一定产生不可接受的低阶污染或 ray failure？

后一个问题必须通过 exact carrier 上的 replay validation 回答。

因此新规范把：

```text
power envelope
```

从“适用性判决器”降级为“是否需要新增验证证据的触发器”。

---

## 5. TASK-013 与 TASK-014 不再串联阻断

TASK-013 与 TASK-014 是两个平行扩展任务：

```text
TASK-013 = N0 untreated reference cornea
TASK-014 = A0V12/B0V12/C0V12 vertex-corrected postoperative corneas
```

它们共享 frozen residual 与验证原则，但不互为科学前置条件。

正式执行依赖改为：

```text
TASK-013 failure/pause
!= TASK-014 automatic STOP

TASK-014 failure/pause
!= TASK-013 automatic STOP
```

只有共同基础资产或 frozen provenance 发生错误（例如 residual SHA mismatch、TASK-008 lock drift、standard eye hash failure）时，才应同时阻止两者。

因此：

- TASK-013 某个 N0 residual power-extension validation 未通过时，可以继续独立执行 TASK-014；
- TASK-014 自己仍必须完成自己的 residual coverage/extension validation；
- 最终96配置汇总必须等两个 task 各自 acceptance PASS 后再进行。

---

## 6. 生产流程

### TASK-013

```text
N0 reference cornea
→ 6 P/Q carriers
→ power coverage classification
→ exact-carrier frozen-residual validation（代码可对全部6个新 carrier执行，至少覆盖所有越界 carrier）
→ validation PASS
→ 12 paired-MONO references
→ 24 production configs
→ 360 TF rows
```

### TASK-014

```text
A0V12/B0V12/C0V12
→ 18 P/Q carriers
→ power coverage classification
→ exact-carrier frozen-residual validation（至少覆盖所有越界 carrier）
→ validation PASS
→ 36 paired-MONO references
→ 72 production configs
→ 1080 TF rows
```

为减少未来遗漏，实现允许对**全部新 carrier**统一执行 exact-carrier validation；这比只验证越界 carrier 更保守，不改变 residual 定义。

---

## 7. 验证证据与 ZMX

每个 exact-carrier residual validation 至少保存：

```text
carrier SHA
residual SHA
actual-eye EDOF validation .zmx + SHA
standard-eye MONO validation .zmx + SHA
standard-eye EDOF validation .zmx + SHA
actual residual readback
standard residual readback
MONO ray-health
EDOF ray-health
policy ID/tolerances
PASS/FAIL
```

验证模型是 diagnostics/provenance artifact，不改变主 production `MODEL_INDEX.csv` 对正式研究模型数量的既有定义；应另有 validation evidence/index 或稳定目录保存。

---

## 8. STOP 条件

仍然必须 STOP 当前 task，如果：

- residual DAT SHA 与 frozen evidence 不一致；
- exact carrier SHA 不可确认；
- actual-eye low-order gate 失败；
- standard-eye low-order gate 失败；
- MONO/EDOF ray-health 失败；
- 需要修改 residual bytes/shape 才能通过；
- 需要改变 P/Q carrier 科学定义才可继续；
- TASK-008/TASK-011/TASK-012 frozen provenance 漂移。

以下不再单独构成 terminal STOP：

```text
new carrier power outside old calibration envelope
```

它只构成 `extension_validation_required = true`。

---

## 9. Git 回退

本次语义修订前：

```text
HEAD = 4e21f94bf8b68767edf5dae620d90bc404394c5c
checkpoint = checkpoint/pre-residual-validation-trigger-2026-08-20
```

完整记录：

```text
docs/CHECKPOINT_PRE_RESIDUAL_VALIDATION_TRIGGER_2026-08-20.md
```

旧的 `checkpoint/pre-vertex-correction-2026-08-20` 与 `checkpoint/task014-phase-c-ready-2026-08-20` 同样保留。

---

## 10. 不变项

本修订不改变：

- A0/B0/C0 legacy TASK-011 结果；
- TASK-014 的 −3.00 D spectacle @12 mm → −2.895752895753 D corneal-plane contract；
- B0.20；
- WFS/RAD/HOA residual bytes/hash；
- matched MONO/EDOF 设计；
- 555 nm、EPD3/5、sampling128；
- +0.50→−3.00 D / −0.25 D 贯焦窗口；
- MTFa、DOF50、TF mean 和 censoring 定义。
