# TASK-013 / TASK-014 residual validation 实现审核 — 历史记录

日期：2026-08-20  
状态：**historical / superseded**

本文件记录的是“power envelope 从 hard boundary 降级为 coverage classifier”这一中间修订。其核心结论仍有效：

```text
historical power envelope = existing validation coverage
outside envelope = extension_validation_required
TASK-013 / TASK-014 = parallel extensions
frozen residual bytes/hash/shape = unchanged
```

但本文件旧版本把 actual-eye SSAG Mode-0 piston/global-defocus 也写入 exact-carrier numerical hard gate。该部分已经被后续 TASK-007 gate-domain restoration 明确纠正，不得再使用。

当前 authoritative 规则：

```text
standard-eye low-order hard gate:
  STD_IOL_EYE_2024 EPD6
  |piston| <= 0.010 µm
  |global defocus| <= 0.125 D

actual-eye hard numerical gate:
  MONO EPD5 ray health PASS
  EDOF EPD5 ray health PASS

actual-eye SSAG Mode-0 piston/defocus:
  diagnostic_only_aperture_limited_mode0
```

当前执行与状态以：

```text
docs/RMD.md
docs/TASK_013_NATIVE_CORNEA_REFERENCE_PLAN_2026-08-20.md
docs/TASK_014_IMPLEMENTATION_REVIEW_2026-08-20.md
```

为准。

历史 TASK-013 两次 STOP-run 与旧 validation records 继续保留用于审计；不要删除或重解释。