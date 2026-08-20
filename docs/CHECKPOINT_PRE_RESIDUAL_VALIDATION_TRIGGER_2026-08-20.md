# TASK-013/TASK-014 residual validation trigger 修订前检查点

日期：2026-08-20

## 1. Git 状态

本次修订前 Git 锚点：

```text
branch = feat/task-011-run72
HEAD = 4e21f94bf8b68767edf5dae620d90bc404394c5c
checkpoint branch = checkpoint/pre-residual-validation-trigger-2026-08-20
PR = #26 / Draft / open / unmerged
```

该 checkpoint 用于回退“residual power envelope 由硬终止门改为验证触发器”之前的代码与文档状态。

## 2. 修订前 TASK-013 行为

修订前 `TASK-013` 在完成6个 N0 physical carriers 后执行：

```text
require_residual_power_envelopes(...)
```

只要任一新 carrier power 超出 TASK-007/TASK-008 既有 low–high power calibration envelope，即在 EDOF production acquisition 前抛出错误并终止 TASK-013。

2026-08-20 本地首次正式执行实际观察到：

```text
ATC_M3_AL24477 + N0 + WFS  ≈ 19.2446 D
ATC_M3_AL24477 + N0 + RAD  ≈ 19.3822 D
ATC_M3_AL24477 + N0 + HOA  ≈ 18.9973 D
```

而 frozen TASK-007/TASK-008 既有验证范围约为：

```text
WFS  21.0526–25.4766 D
RAD  21.1776–25.5871 D
HOA  20.8149–25.2587 D
```

因此旧 gate 按设计停止。

## 3. 为什么需要修订

上述约19 D 的 N0 carrier power 本身并不是异常：未治疗角膜相较近视角膜屈光术后角膜具有更高角膜屈光力，因此达到同一远焦条件所需 IOL power 更低是合理方向。

旧 power envelope 的科学含义应为：

> frozen residual 已经在哪些实际 carrier powers 上获得过验证证据。

它不应被解释为：

> residual 在 envelope 之外物理失效或该 carrier 不允许研究。

因此，越界应触发新的、power-specific residual validation，而不是永久排除该配置。

## 4. 本次修订的边界

本次允许修改：

- TASK-013/TASK-014 power-envelope gate 语义；
- 新增 frozen residual power-extension validation；
- TASK-013 与 TASK-014 的执行依赖关系；
- 与上述变化直接相关的文档、测试和 diagnostics。

本次禁止修改：

- frozen WFS/RAD/HOA residual DAT bytes；
- residual SHA-256；
- residual morphology/shape；
- `RESIDUAL_VALIDATION_546_v1` 的 piston/global-defocus tolerance；
- TASK-008 manifest / lock set；
- TASK-011/TASK-012 evidence；
- B0.20；
- TASK-009 production acquisition settings；
- TASK-014 vertex-distance prescription contract。

## 5. 回退原则

若本次新的 validation-trigger 设计后续被证实存在问题，可回退或比较到：

```text
checkpoint/pre-residual-validation-trigger-2026-08-20
4e21f94bf8b68767edf5dae620d90bc404394c5c
```

不得通过覆盖旧 evidence 的方式“回退”。
