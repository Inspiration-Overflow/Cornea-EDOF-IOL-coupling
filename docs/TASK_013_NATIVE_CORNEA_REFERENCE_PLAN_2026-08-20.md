# TASK-013 未治疗参考角膜扩展研究与 ZMX 归档计划

日期：2026-08-20  
任务 ID：`TASK-013-NATIVE-CORNEA-REFERENCE`  
状态：**local acquisition complete；final scientific acceptance pending Web mechanism review**

本文件是 TASK-013 当前主计划。旧的 power-envelope hard-gate 与 actual-eye low-order hard-gate 表述均已废止；当前 gate 以 `docs/RMD.md` 为准。

## 1. 目的与范围

新增：

```text
N0 = native / untreated reference cornea
```

N0 是角膜状态，不是“正常眼”标签。`ATC_M3_AL24477 + N0` 仍保留 Atchison 近视来源的基础眼表型。

矩阵：

```text
2 Base × 1 N0 × 3 Platform = 6 physical carriers
6 × MONO/EDOF × EPD3/5 = 24 configs
12 matched pairs
360 through-focus rows
```

MONO 始终是各平台自己的 residual-free matched carrier。

## 2. N0 光学定义

```text
scaffold = MAIN_CORNEA_LIOU_555_v1
Rant = 7.77 mm
Qant = -0.18
thickness = 0.50 mm
Rpost = 6.40 mm
Qpost = -0.60
n_cornea = 1.376
n_aqueous = 1.336
```

N0 不施加 myopic treatment、额外 ΔC4^0、central-near zone 或角膜 EDOF modulation。

## 3. Carrier 路线

每个 `Base × N0 × Platform` 独立：

```text
actual eye Q=0 P/R solve
→ STD_IOL_EYE_2024 power-specific Q(P)
→ actual-eye P–Q recheck (max2)
→ final standard-eye SA replay
→ save canonical carrier + SHA
```

不得从 legacy A0/B0/C0 carrier 复制 P/R/Q。

## 4. Residual coverage 与 schema-v2 validation

历史 TASK-007/008 power envelope 仅是已有验证覆盖范围：

```text
within_existing_coverage
extension_validation_required
```

越界不自动排除。

每个新 carrier 绑定 exact carrier SHA + exact frozen residual SHA。Schema v2 的 numerical gate：

```text
STD_IOL_EYE_2024 EPD6:
  |piston| <= 0.010 µm
  |global defocus| <= 0.125 D

actual eye EPD5:
  MONO ray health PASS
  EDOF ray health PASS
```

Actual-eye SSAG Mode-0 piston/defocus 必须保存，但固定为 diagnostic-only，不参与 pass/fail。不得修改 residual bytes/hash/shape 或给 RAD 建专用阈值。

## 5. 已完成的本地正式 acquisition

正式成功 run：

```text
run_id = task013-183dcffcd1da4f1cb1a219d9eedb39db
code HEAD = a3877f5682a9067c1cd420dc31d4f14a6a4e13ab
OpticStudio = 2026 R1.00
```

结果：

```text
N0 reference cornea = 1
physical carriers = 6/6
schema-v2 validations = 6/6 PASS
pair references = 12/12
configs = 24/24
failed configs = 0
TF rows = 360
matched pairs = 12
MODEL_INDEX = 43 records
model_archive_complete = true
```

Carrier P/Q：

```text
LB  N0 WFS  P=21.2179 D   Q=-7.5
LB  N0 RAD  P=21.3354 D   Q=-11.0
LB  N0 HOA  P=20.9867 D   Q=0.0
ATC N0 WFS  P=19.2446 D   Q=-10.5
ATC N0 RAD  P=19.3822 D   Q=-15.5
ATC N0 HOA  P=18.9973 D   Q=0.0
```

LB 三个平台位于历史 coverage 内；ATC 三个平台位于 coverage 外并已完成 exact-carrier extension validation。

RAD actual-eye diagnostic piston 在 LB 与 ATC 均约 `-0.042 µm`，而 standard-eye low-order 与 MONO/EDOF ray health 均 PASS，支持其为既有 aperture-limited Mode-0 readback 特征，而不是低功率 N0 外推新失效。

贯焦 acquisition 中 24 个 config 均完成；2 个 `HOA EDOF EPD5` config 标记 distance-peak-window censoring，DOF50 无 censoring。该 censoring 必须在后续分析中继续显式传播。

## 6. 历史 STOP runs

必须永久保留：

```text
task013-25e426e7c6d64d5aa59ffc089f352db2
  old terminal power-envelope gate

task013-2b0dfe62e0eb424a84ae0fe8da942253
  old schema-v1 actual-eye low-order hard-gate error
```

旧 v1 validation records 不删除；v2 current records 与其并存。

## 7. Acceptance 语义

当前结论：

```text
local acquisition acceptance = PASS
final scientific acceptance = PENDING WEB REVIEW
```

本地 `acceptance_passed=true` 只解释为 acquisition/archive 完整性的兼容字段，不构成 scientific lock。

Web review 至少检查 out-of-coverage 的 ATC N0 WFS/RAD/HOA：

- EPD3/EPD5 through-focus mechanism；
- distance peak 与 censoring；
- DOF50；
- MTFa@0D 与 TF MTFa mean；
- C4^0、C6^0、HOA RMS；
- 与各平台 TASK-007 mechanism signature 的一致性；
- 无新增 ray pathology。

只有 Web review PASS 后，TASK-013 才可标记 final scientific acceptance。

## 8. Canonical artifacts

```text
models/task013_native_reference/
  cornea/N0_REFERENCE_CORNEA.zmx
  carriers/                              # 6
  residual_validations/                  # v1 history + v2 current
  runs/task013-183dcffcd1da4f1cb1a219d9eedb39db/
    pair_references/                     # 12
    configs/                             # 24
    MODEL_INDEX.csv                      # 43 records
```

Repo evidence 由本地成功 run 生成在 `docs/evidence/task013/`；在 Web 审核完成前不把它解释为 final scientific lock。

## 9. 下一步

**不要重跑 TASK-013。**

下一步仅为：

```text
导入/审核 TASK-013 evidence
→ Web mechanism review
→ scientific PASS/FAIL
```

若证据完整且机制审核 PASS，再与后续 accepted TASK-014 合并成：

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configs
```

Frozen TASK-011 继续独立保留，不被重跑或改写。