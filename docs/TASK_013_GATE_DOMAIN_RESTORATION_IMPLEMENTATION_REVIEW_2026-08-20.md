# TASK-013 residual validation gate-domain restoration — implementation review

日期：2026-08-20  
结论：**PASS；可再次执行 TASK-013 local acquisition，最终 scientific acceptance 仍需对 out-of-coverage carriers 做 Web mechanism review。**

## 1. 触发问题

TASK-013 第二次本地运行 `task013-2b0dfe62e0eb424a84ae0fe8da942253` 在 `CAR_ATC_M3_AL24477_N0_RAD` 停止，因为 v1 exact-carrier validator 将 actual-eye SSAG Mode-0 piston `≈ -0.042 µm` 与 `0.010 µm` 阈值直接比较并作为 hard gate。

TASK-007 frozen Web review 明确表明该用法错误：

```text
normative low-order gate = STD_IOL_EYE_2024 EPD6 imported residual readback
actual-eye SSAG low-order = diagnostic only; aperture-limited Mode 0
```

RAD 在 TASK-007 已因同样约 `-0.043 µm` actual-eye piston 被认定为 readback artifact，而非 residual/mechanism failure。

## 2. 修订

`src/whole_eye_mvp/residual_extension_validation_zos.py`：

- validation schema `1 -> 2`；
- 固定 `NORMATIVE_LOW_ORDER_GATE_DOMAIN`；
- 固定 `ACTUAL_EYE_LOW_ORDER_ROLE=diagnostic_only_aperture_limited_mode0`；
- exact-carrier hard numerical gate 改为：
  - standard-eye low-order PASS；
  - actual-eye MONO EPD5 ray health PASS；
  - actual-eye EDOF EPD5 ray health PASS；
- actual-eye piston/defocus 继续测量和归档，但不参与 hard pass/fail；
- 没有修改任何数值阈值；
- 没有 RAD 专用例外；
- 没有修改 residual DAT。

## 3. 历史验证保留

v2 路径：

```text
residual_validations/<carrier_id>/v2_<carrierSHA12>_<residualSHA12>/
```

因此旧 v1 `VALIDATION.json`、`ACTUAL_EDOF.zmx`、`STD_MONO.zmx`、`STD_EDOF.zmx` 不被覆盖。

`CURRENT.json` 与 `VALIDATION_INDEX.json` 只指向当前 schema / current exact carrier-residual validation；历史目录仍保留供审计。

## 4. 测试

`tests/unit/test_residual_extension_validation_zos.py` 新增回归断言：

- validation index 使用当前 schema；
- gate-domain identity 被写入 index；
- `_numerical_gate_pass()` 只依赖 standard-eye low-order + MONO/EDOF ray health；
- actual-eye low-order diagnostic failure 不能重新进入 hard gate。

Offline quality gate：

```text
run #184
run_id = 32417671447
result = success
pytest = 232 passed
Ruff = PASS
compileall = PASS
uv lock --check = PASS
```

## 5. 科学边界

本修订不是为了让 N0/RAD “过关”而放宽标准，而是恢复 TASK-007 已冻结的阈值适用域。

对于历史 power coverage 之外的 carrier：

```text
within_existing_coverage = false
extension_validation_required = true
```

允许在 v2 numerical validation PASS 后完成 through-focus acquisition，以产生 mechanism review 所需证据；但最终 scientific acceptance 仍需 Web review through-focus / wavefront / mechanism behavior。

## 6. 不变项

- WFS/RAD/HOA residual bytes/hash/shape：unchanged；
- `RESIDUAL_VALIDATION_546_v1` 阈值：unchanged；
- TASK-007/008：unchanged；
- TASK-009 analysis/acquisition contract：unchanged；
- TASK-011/012 evidence：unchanged；
- N0 与 TASK-014 prescription identities：unchanged；
- B0.20：unchanged。

## 7. Git rollback

修订前 checkpoint：

```text
checkpoint/pre-task013-gate-domain-restore-2026-08-20
@ 88490f590b52f7b1f4aa0f0a9f05e99daae6eeee
```

下一步是在当前 `feat/task-011-run72` 最新 HEAD 上重新执行 TASK-013；必须保留前两次 STOP-run diagnostics，并生成新的 run_id。