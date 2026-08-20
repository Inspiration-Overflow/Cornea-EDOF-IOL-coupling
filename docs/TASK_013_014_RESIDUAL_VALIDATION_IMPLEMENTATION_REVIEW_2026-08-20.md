# TASK-013 / TASK-014 residual power-extension validation 实现审核

日期：2026-08-20  
状态：**代码与文档修订完成；离线 QA PASS；待本地 OpticStudio 重新执行**

## 1. 审核结论

本轮修订解决两个执行设计问题：

1. 历史 residual carrier-power envelope 不再作为 residual 的物理适用硬边界；
2. TASK-013 与 TASK-014 不再形成串联阻断关系。

新的正式定义是：

```text
historical power envelope
= existing validation coverage

outside historical envelope
= extension_validation_required = true
!= residual invalid
!= configuration excluded
```

真正决定某个新 carrier 是否可以进入 EDOF production 的 hard gate 是：

```text
exact saved carrier .zmx SHA
+
exact frozen residual DAT SHA
+
RESIDUAL_VALIDATION_546_v1
+
actual-eye low-order replay
+
standard-eye low-order replay
+
actual-eye MONO/EDOF EPD5 ray health
```

本轮没有修改 residual bytes、residual SHA、residual morphology、B0.20、TASK-009 production contract、TASK-011/TASK-012 frozen evidence 或 TASK-014 vertex prescription contract。

---

## 2. 触发修订的本地事实

TASK-013 首次本地执行 run：

```text
run_id = task013-25e426e7c6d64d5aa59ffc089f352db2
```

成功建立 N0 reference cornea 与6个 physical carriers，但旧 power-envelope hard gate 在 EDOF production 前停止。

ATC+N0 carrier powers 约为：

```text
WFS = 19.2446 D
RAD = 19.3822 D
HOA = 18.9973 D
```

历史验证覆盖约为：

```text
WFS = 21.0526–25.4766 D
RAD = 21.1776–25.5871 D
HOA = 20.8149–25.2587 D
```

该方向符合未治疗角膜屈光力较高、所需 IOL power 较低的预期，因此“约19 D”本身不是 carrier 求解异常。

旧逻辑错误在于把“此前没有在该 power 上验证”直接等价为“不能研究”。

---

## 3. Git 回退状态

本轮 residual-gate 语义修订前：

```text
branch = feat/task-011-run72
HEAD = 4e21f94bf8b68767edf5dae620d90bc404394c5c
checkpoint = checkpoint/pre-residual-validation-trigger-2026-08-20
```

记录：

```text
docs/CHECKPOINT_PRE_RESIDUAL_VALIDATION_TRIGGER_2026-08-20.md
```

此前 checkpoint 同样保留：

```text
checkpoint/pre-vertex-correction-2026-08-20
checkpoint/task014-phase-c-ready-2026-08-20
```

---

## 4. 文档修订

权威规范：

```text
docs/TASK_013_014_RESIDUAL_POWER_EXTENSION_ADDENDUM_2026-08-20.md
docs/TASK_013_NATIVE_CORNEA_REFERENCE_PLAN_2026-08-20.md
docs/TASK_013_014_LOCAL_EXECUTION_HANDOFF_V2_2026-08-20.md
docs/RMD.md  v2.1
```

其中明确：

- envelope = validation coverage；
- out-of-envelope = validation trigger；
- exact-carrier validation 使用既有 TASK-007 numerical hard gates；
- TASK-013 / TASK-014 是平行扩展；
- task-local optical failure 只暂停本 task；
- shared frozen-provenance failure 才同时阻止两者。

---

## 5. 代码修订

### 5.1 Coverage classification

```text
src/whole_eye_mvp/task013_native_reference.py
src/whole_eye_mvp/task014_extension.py
```

coverage record 使用明确字段：

```text
within_existing_coverage
extension_validation_required
```

不再使用容易误读为科学 PASS/FAIL 的 envelope `passed` 字段。

历史函数名 `require_residual_power_envelopes()` / `require_task014_residual_power_envelopes()` 暂保留用于兼容，但只返回 coverage classification，不因越界直接抛错。

### 5.2 Exact-carrier residual validator

新增：

```text
src/whole_eye_mvp/residual_extension_validation_zos.py
```

验证输入绑定：

```text
carrier_id
base_id
cornea_id
platform_id
exact carrier .zmx SHA
frozen residual ID/SHA
RESIDUAL_VALIDATION_546_v1
```

从 exact saved actual-eye carrier `.zmx` 读取：

```text
Rant
Rpost
Qant
Qpost
```

并验证：

```text
symmetric biconvex
Qpost = 0
finite R/Q
```

随后执行 actual-eye 与 standard-eye residual replay。

### 5.3 TASK-013 / TASK-014 production integration

```text
src/whole_eye_mvp/task013_zos.py
src/whole_eye_mvp/task014_zos.py
```

EDOF model materialization 顺序现在固定为：

```text
verify carrier SHA
→ verify frozen residual SHA
→ ensure exact-carrier validation PASS/reusable
→ apply frozen residual for production
→ persist config pupil
→ production acquisition
```

MONO production 不加 residual。

如果 exact validation FAIL，使用 `SystemExit` 在 EDOF production 前停止当前 task，避免被 per-config ordinary exception handling 当成一个普通失败后继续运行。

---

## 6. Numerical hard gates

本轮不新建阈值，沿用 TASK-007 的 `RESIDUAL_VALIDATION_546_v1`：

### Actual eye

```text
|measured piston| <= 0.010 µm
|measured global defocus| <= 0.125 D
```

### Standard eye

```text
|measured piston| <= 0.010 µm
|measured global defocus| <= 0.125 D
```

### Actual-eye ray health at EPD5

对 MONO 与 EDOF 分别检查9条 normalized pupil rays：

```text
success = true
error = 0
vignette = 0
```

### Final verdict

```text
passed =
  actual_low_order_pass
  AND standard_low_order_pass
  AND mono_ray_health_pass
  AND edof_ray_health_pass
```

---

## 7. Validation artifact / history preservation

TASK-013：

```text
models/task013_native_reference/residual_validations/
```

TASK-014：

```text
models/task014_vertex_corrected/residual_validations/
```

每个 carrier：

```text
<carrier_id>/
  <carrierSHA12>_<residualSHA12>/
    ACTUAL_EDOF.zmx
    STD_MONO.zmx
    STD_EDOF.zmx
    VALIDATION.json
  CURRENT.json
```

根目录：

```text
VALIDATION_INDEX.json
```

历史 carrier/residual SHA 的 validation records 不删除。

`CURRENT.json` 指向该 carrier 当前 exact SHA 的 validation record；`VALIDATION_INDEX.json` 只聚合 CURRENT records，因此历史失败/旧 SHA 记录不会污染当前 `all_passed`，同时审计历史完整保留。

缓存只在以下条件全部满足时复用：

```text
exact carrier SHA unchanged
frozen residual SHA unchanged
policy ID unchanged
prior passed = true
validation artifact SHAs still match
```

---

## 8. 主 ZMX model index 不改变

Residual validation `.zmx` 是 diagnostics/provenance artifacts，不改变主研究模型计数。

TASK-013 主模型仍为：

```text
N0 + 6 carriers + 12 pair refs + 24 config models
```

TASK-014 primary `MODEL_INDEX.csv` 仍预计：

```text
5 cornea layer
+ 6 P0
+ 18 carriers
+ 36 pair refs
+ 72 analyzed configs
= 137 records
```

---

## 9. TASK-013 / TASK-014 独立性

新的执行原则：

```text
TASK-013 task-local validation/PQ failure
!= TASK-014 automatic STOP

TASK-014 task-local validation/PQ failure
!= TASK-013 automatic STOP
```

只有共享 frozen provenance 故障才同时停止：

```text
residual DAT SHA mismatch
STD_IOL_EYE_2024 immutable hash mismatch
TASK-008 manifest/lock drift
TASK-009 production contract drift
TASK-011/TASK-012 evidence drift
```

最终96配置汇总仍要求两者各自 acceptance PASS。

---

## 10. Tests / offline QA

新增或修订：

```text
tests/unit/test_task013_native_reference.py
tests/unit/test_task014_extension.py
tests/unit/test_residual_extension_validation_zos.py
```

新增回归保护包括：

- out-of-envelope 不再直接 raise；
- `extension_validation_required=true`；
- coverage 与 validation verdict 使用不同字段语义；
- historical validation record 保留；
- CURRENT pointer 可切换到新 exact carrier SHA；
- validation index 只汇总当前记录。

最终离线质量门：

```text
Offline quality gate run #177
run_id = 32413663423
pytest = 231 passed
Ruff = PASS
compileall = PASS
uv lock --check = PASS
```

---

## 11. 尚未生成的新光学事实

本轮 Web/GitHub 修订没有声称已经完成新的 residual validation，也没有产生新的 TASK-013/TASK-014 through-focus 数值。

仍待本地 Windows + OpticStudio：

```text
TASK-013 rerun
→ 6 exact-carrier residual validations
→ 24 configs / 360 TF rows

TASK-014 independent run
→ 18 exact-carrier residual validations
→ 72 configs / 1080 TF rows
```

第一次 TASK-013 旧 STOP run 的 diagnostics 应保留，不删除。

---

## 12. 审核结论

```text
historical power envelope = coverage classifier
exact-carrier frozen-residual validation = production hard gate
residual bytes/hash/shape = unchanged
TASK-013 / TASK-014 = parallel tasks
frozen TASK-011/012 = unchanged
rollback checkpoint = established
offline QA = PASS
new OpticStudio validation/acquisition = PENDING
PR #26 = Draft / open / unmerged
```
