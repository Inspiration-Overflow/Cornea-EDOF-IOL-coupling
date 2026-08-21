# TASK-013 / TASK-014 residual power-extension 历史说明

日期：2026-08-20  
状态：**historical / partially superseded**

本文件保留一次方法学纠偏的历史背景，但不再定义当前 numerical hard gate。当前执行语义以 `docs/RMD.md` 与 `docs/TASK_013_014_GATE_DOMAIN_RESTORATION_ADDENDUM_2026-08-20.md` 为准。

## 仍然有效的结论

历史 TASK-007/008 carrier power 范围只表示：

```text
existing validation coverage
```

而不是 frozen residual 的物理适用硬边界。因此：

```text
within_existing_coverage = false
→ extension_validation_required = true
≠ residual invalid
≠ automatic exclusion
```

新 carrier 必须继续使用完全相同的 frozen residual bytes/hash/shape，并在 exact carrier 上取得新增验证证据。

TASK-013 与 TASK-014 是平行扩展任务；一个 task 的局部 optical failure 不自动阻止另一个。只有 residual SHA、standard-eye immutable asset、TASK-008 locks、TASK-009 production contract 等共享 provenance 发生错误时，才同时停止二者。

## 已被废止的旧表述

本文件旧版本曾把 actual-eye SSAG Mode-0 piston/global-defocus readback 也写入 numerical hard gate。该表述已经由 TASK-007 consolidated review 的 gate-domain 纠正：

```text
normative low-order hard gate
= STD_IOL_EYE_2024 EPD6 imported-residual readback

actual-eye SSAG Mode-0 low-order
= diagnostic_only_aperture_limited_mode0

actual-eye numerical hard evidence
= MONO EPD5 ray health + EDOF EPD5 ray health
```

阈值本身没有改变：standard-eye `|piston| <= 0.010 µm`、`|global defocus| <= 0.125 D`。不得建立 RAD 专用阈值，也不得修改 residual。

## 当前最小执行原则

```text
carrier build
→ power coverage classification
→ exact-carrier validation
→ standard-eye low-order PASS
→ actual-eye MONO/EDOF ray-health PASS
→ production acquisition
→ 若存在 out-of-coverage carrier，则 Web mechanism review
```

不要再从本历史文件提取其他 gate 或 STOP 规则。