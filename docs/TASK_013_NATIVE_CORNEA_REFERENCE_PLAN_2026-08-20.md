# TASK-013 未治疗参考角膜扩展研究与 ZMX 模型归档计划

日期：2026-08-20  
状态：**科学定义冻结；代码已实现；首次本地 carrier build 已发现低功率扩展区间，现按 exact-carrier residual validation 规范修订；正式24配置 acquisition 待重跑**  
任务 ID：`TASK-013-NATIVE-CORNEA-REFERENCE`

> 2026-08-20 修订说明：本文件已吸收 `TASK_013_014_RESIDUAL_POWER_EXTENSION_ADDENDUM_2026-08-20.md`。旧版“超出历史 residual power envelope 即终止 TASK-013”的表述已废止。历史 envelope 现在只表示**既有验证覆盖范围**；正式 EDOF production 是否可继续，由 exact-carrier + exact frozen residual 的 replay / low-order / ray-health validation 决定。

---

## 1. 研究目的

冻结的 TASK-011 主矩阵为：

```text
A0 / B0 / C0
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 72 configurations
```

它回答屈光术后角膜与三类非衍射 EDOF 机制的耦合，但缺少未接受角膜屈光手术时的机制参照。

TASK-013 新增：

```text
N0 = native / untreated reference cornea
```

用于回答：同样的 IOL carrier、同样的三类 frozen residual、同样双基础眼和双瞳孔下，未经角膜屈光手术的参考角膜上 MONO/EDOF 本身如何表现。

TASK-013 是独立扩展层，不修改既有 frozen Run72。

---

## 2. 冻结结果与 provenance 边界

以下保持只读：

```text
baseline_id = MVP_2026_v2
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-011 run_id = analysis-1cc1441dec4744a18d7ac73763507a6c
TASK-011 configs = 72
TASK-011 pairs = 36
TASK-011 TF rows = 1080
TASK-012 structured evidence = unchanged
```

禁止：

- 把 N0 写回 TASK-008 frozen manifest；
- 修改旧18个 carrier locks；
- 修改 B0.20；
- 修改 frozen WFS/RAD/HOA residual DAT bytes、SHA 或 morphology；
- 为使新结果通过而 retune residual；
- 修改 TASK-009 production sampling、贯焦窗口或 metric 定义；
- 重跑 legacy TASK-011 作为 TASK-013 前提。

---

## 3. N0 光学定义

N0 使用项目共同参考角膜 scaffold：

```text
scaffold_id = MAIN_CORNEA_LIOU_555_v1
anterior radius = 7.77 mm
anterior conic = -0.18
corneal thickness = 0.50 mm
posterior radius = 6.40 mm
posterior conic = -0.60
n_cornea = 1.376
n_aqueous = 1.336
```

N0：

- 不施加近视角膜 treatment；
- 不人为加入 ΔC4^0；
- 不加入 central-near zone；
- 不加入角膜 EDOF 设计。

N0 是**角膜状态**，不是“正常眼”身份。特别是 `ATC_M3_AL24477 + N0` 仍保留 Atchison 近视来源的基础眼表型。

---

## 4. 研究矩阵

### 4.1 Physical carriers

```text
2 Base × 1 N0 × 3 Platform = 6 carriers
```

ID：

```text
CAR_<base_id>_N0_<platform_id>
```

### 4.2 Nominal configurations

```text
6 carriers × MONO/EDOF × EPD3/5 = 24 configs
12 matched MONO/EDOF pairs
360 through-focus rows
```

其中“MONO”始终是**平台匹配的 residual-free carrier**，不是一枚跨 WFS/RAD/HOA 共用的通用单焦 IOL。

---

## 5. Carrier 构建

每个 `Base × N0 × Platform` 独立执行：

1. actual eye、fixed retina、Q=0 求 P/R；
2. 将 P/R 放入 `STD_IOL_EYE_2024`；
3. 按平台求 power-specific `Q_k(P)`；
4. Q 回放 actual eye；
5. 按既有规则最多两次 P–Q recheck；
6. 验证最终 actual-eye R/Q；
7. 标准眼复核平台 SA target；
8. 保存 canonical carrier `.zmx` 与 SHA-256。

不得从 A0/B0/C0 carrier 复制 P、R 或 Q。

---

## 6. 首次本地 carrier build 的方法学发现

2026-08-20 首次正式本地执行成功构建 N0 与6个 carriers，发现 ATC+N0 的 carrier power 约为：

```text
ATC_M3_AL24477 + N0 + WFS ≈ 19.2446 D
ATC_M3_AL24477 + N0 + RAD ≈ 19.3822 D
ATC_M3_AL24477 + N0 + HOA ≈ 18.9973 D
```

而历史 TASK-007/TASK-008 residual calibration coverage 约为：

```text
WFS  21.0526–25.4766 D
RAD  21.1776–25.5871 D
HOA  20.8149–25.2587 D
```

这不是 carrier 求解错误。未治疗角膜屈光力高于近视角膜屈光术后角膜，在同一固定视网膜条件下需要较低 IOL power，方向合理。

因此该发现说明：**N0 扩展进入了 legacy post-refractive carrier calibration 没有覆盖的低 IOL power 区间。**

---

## 7. Residual power envelope 的新正式语义

每个平台仍计算：

```text
existing_min_power <= new_carrier_power <= existing_max_power
```

但这个判断现在只生成：

```text
existing_validation_coverage = true/false
extension_validation_required = !existing_validation_coverage
```

它不再直接决定 residual 是否“有效”。

历史 envelope 只能证明 frozen residual 此前在哪些 carrier powers 上获得过验证证据；它不能证明区间外 residual 一定产生不可接受的低阶污染或 ray failure。因此，是否允许正式 EDOF production 必须在**exact new carrier** 上验证。

---

## 8. Exact-carrier frozen-residual validation

TASK-013 代码对每个新 carrier 在第一次 EDOF materialization 前执行一次 exact-carrier validation；这样既覆盖所有 out-of-envelope carrier，也对 in-envelope carrier 提供额外直接证据。

验证对象绑定：

```text
exact carrier .zmx SHA
exact frozen residual DAT SHA
platform
RESIDUAL_VALIDATION_546_v1
```

### 8.1 Actual-eye low-order readback

要求：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

### 8.2 Standard-eye low-order readback

从 exact carrier `.zmx` 读取 Rant/Rpost/Q，放入 `STD_IOL_EYE_2024`，对 residual-free / frozen-residual 模型执行同样 readback：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

### 8.3 Actual-eye EPD5 ray health

MONO 与 EDOF 均检查9条标准化 pupil rays：

```text
success = true
error = 0
vignette = 0
```

### 8.4 Hard gate

```text
validation_pass =
  actual_low_order_pass
  AND standard_low_order_pass
  AND MONO_ray_health_pass
  AND EDOF_ray_health_pass
```

失败时只停止当前 TASK-013 的 EDOF production；保存 diagnostics，禁止修改 residual 以追求通过。

---

## 9. Validation artifact 与缓存

固定目录：

```text
models/task013_native_reference/residual_validations/
  <carrier_id>/
    <carrierSHA12>_<residualSHA12>/
      ACTUAL_EDOF.zmx
      STD_MONO.zmx
      STD_EDOF.zmx
      VALIDATION.json
  VALIDATION_INDEX.json
```

缓存只在 `carrier SHA + residual SHA + policy ID + prior PASS` 全部一致且原 artifact SHA 仍匹配时复用，因此第二个 pupil 的 EDOF config 不重复验证同一 carrier。

Validation `.zmx` 属于 diagnostics/provenance，不改变主 production `MODEL_INDEX.csv` 的模型计数。

---

## 10. 正式 production 设置

继续完全继承 TASK-009：

```text
analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4cebc
acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale = paired_residual_free_MONO_EFFL
sampling = 128
wavelength = 555 nm
EPD = 3 / 5 mm
field = 0°
defocus = +0.50 → -3.00 D
step = -0.25 D
planes = 15
frequency = 0–60 cpd, 1 cpd step
```

MTFa、distance peak、DOF50、TF mean、censoring 均不改。

---

## 11. ZMX 保存契约

```text
project_mvp_2026_v2_zmx/
└─ models/
   └─ task013_native_reference/
      ├─ cornea/
      │  └─ N0_REFERENCE_CORNEA.zmx
      ├─ carriers/
      │  └─ CAR_<base>_N0_<platform>.zmx       # 6
      ├─ residual_validations/                  # diagnostics/provenance
      └─ runs/<run_id>/
         ├─ pair_references/<pair_key>.zmx      # 12
         ├─ configs/<config_id>.zmx             # 24
         └─ MODEL_INDEX.csv
```

每个 config `.zmx` 必须在 production 分析前持久化其 EPD3/EPD5，并且归档 SHA 与 analyzed model SHA 一致。

---

## 12. TASK-013 与 TASK-014 的关系

二者是平行扩展：

```text
TASK-013 = N0 untreated reference cornea
TASK-014 = A0V12/B0V12/C0V12 vertex-corrected postoperative corneas
```

因此：

```text
TASK-013 pause/failure != TASK-014 automatic STOP
TASK-014 pause/failure != TASK-013 automatic STOP
```

只有共享冻结基础资产发生 provenance/hash 错误时才应同时阻止二者。

最终 clinically normalized dataset 必须等两者分别 acceptance PASS 后再组合：

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configs
```

---

## 13. Acceptance

```text
N0 reference cornea = 1
physical carriers = 6/6
power coverage classification = complete
exact-carrier residual validations = 6/6 PASS
pair references = 12/12
completed configs = 24/24
failed configs = 0
through-focus rows = 360
matched pairs = 12
MODEL_INDEX complete = true
config-specific ZMX archive = 24/24
acceptance_passed = true
```

历史 envelope 外 carrier 必须标记 `extension_validation_required=true`；但 exact-carrier validation PASS 后不构成排除。

---

## 14. STOP 条件

必须停止 TASK-013，如果：

- frozen residual DAT SHA mismatch；
- exact carrier SHA 不可确认；
- carrier P/Q 或 standard-eye SA replay 失败；
- exact-carrier actual/standard low-order validation 失败；
- MONO/EDOF ray health 失败；
- 需要修改 residual bytes/shape 才能继续；
- TASK-008/011/012 frozen provenance 漂移；
- 正式 config 数、TF rows、pair 数或 ZMX archive 不完整。

**以下不再单独构成 terminal STOP：**

```text
new carrier power outside historical calibration envelope
```

它只意味着需要 extension validation。

---

## 15. Git / rollback 状态

```text
checkpoint/pre-vertex-correction-2026-08-20
  HEAD fa401e2101023e6e409a5366f26f0da134b5476f

checkpoint/task014-phase-c-ready-2026-08-20

checkpoint/pre-residual-validation-trigger-2026-08-20
  HEAD 4e21f94bf8b68767edf5dae620d90bc404394c5c
```

本次 residual gate 修订前的完整记录：

```text
docs/CHECKPOINT_PRE_RESIDUAL_VALIDATION_TRIGGER_2026-08-20.md
```

禁止通过覆盖旧 evidence 的方式回退。
