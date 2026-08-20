# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **角色：** 当前项目唯一执行路线图。坚持 MVP：只保留完成研究所必需的模型、验证、证据和 STOP gate；不新增与当前研究问题无关的框架。

## Metadata

- document_id: `RMD-0001`
- version: `2.2`
- status: `active`
- last_updated: `2026-08-20`
- active_branch: `feat/task-011-run72`
- PR: `#26 Draft / open / unmerged`
- production_acquisition: `TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2`
- production_sampling: `128`
- frequency_scale: `paired_residual_free_MONO_EFFL`

---

# 1. Frozen 主研究

以下保持只读：

```text
baseline = MVP_2026_v2
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-009 acquisition = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
TASK-011 = 72 configs / 36 pairs / 1080 TF rows / 0 failed
TASK-012 = accepted structured analysis with stated censoring caveats
```

Legacy A0/B0/C0 的治疗语义仍是 direct corneal-plane `-3.00 D`，不做顶点距回解释。

---

# 2. 当前扩展任务

## TASK-013 — N0 未治疗参考角膜

```text
N0
× 2 Base
× 3 Platform
× MONO/EDOF
× EPD3/5
= 24 configs
```

第三次本地正式 acquisition 已完成：

```text
run_id = task013-183dcffcd1da4f1cb1a219d9eedb39db
physical carriers = 6/6
schema-v2 exact-carrier validations = 6/6 PASS
pair references = 12/12
configs = 24/24
failed = 0
TF rows = 360
matched pairs = 12
MODEL_INDEX records = 43
model archive = complete
```

其中 ATC+N0 的 WFS/RAD/HOA 位于历史 power coverage 之外，因此：

```text
local acquisition acceptance = PASS
final scientific acceptance = PENDING WEB MECHANISM REVIEW
```

**不重跑 TASK-013**，除非后续发现 evidence/hash/archive 完整性问题。

## TASK-014 — 顶点距规范化术后角膜

冻结处方：

```text
spectacle sphere = -3.00 D
vertex = 12 mm
corneal-plane treatment = -2.895752895753 D
IDs = A0V12 / B0V12 / C0V12
```

矩阵：

```text
2 Base × 3 Cornea × 3 Platform = 18 carriers
18 × MONO/EDOF × EPD3/5 = 72 configs
36 pairs
1080 TF rows
```

TASK-014 尚未产生正式 OpticStudio acquisition。

---

# 3. Residual validation — 唯一当前规则

历史 power envelope 只是：

```text
existing validation coverage
```

新 carrier 记录：

```text
within_existing_coverage = true/false
extension_validation_required = !within_existing_coverage
```

越界本身不构成 STOP。

Exact-carrier validation schema = `2`。每个新 carrier 必须绑定 exact carrier SHA + exact frozen residual SHA。

## 3.1 Normative low-order hard gate

只在：

```text
STD_IOL_EYE_2024
EPD6
imported residual readback
```

检查：

```text
|piston| <= 0.010 µm
|global defocus| <= 0.125 D
```

## 3.2 Actual-eye hard gate

```text
MONO EPD5 ray health PASS
EDOF EPD5 ray health PASS
```

要求 success=true、error=0、vignette=0。

## 3.3 Actual-eye SSAG low-order

仍测量、保存、报告，但固定为：

```text
diagnostic_only_aperture_limited_mode0
```

不得进入 numerical pass/fail。不得给 RAD 建例外阈值；不得修改 frozen residual。

---

# 4. Acceptance 语义

扩展任务统一区分：

```text
acquisition_acceptance
scientific_acceptance
```

Local acquisition acceptance 只证明：

- carrier/P-Q/SA replay 完成；
- exact residual identity 与 numerical gate PASS；
- production configs / TF / ZMX archive 完整。

Final scientific acceptance 还要求 Web 审核 structured evidence。任何 `within_existing_coverage=false` 的 carrier 必须额外做 mechanism review。

因此 runner 中旧字段 `acceptance_passed` 若保留，只能作为 **local acquisition compatibility alias**，不得直接解释为 scientific lock。

---

# 5. TASK-013 下一步

只做 Web evidence review，不再做新的 OpticStudio acquisition：

1. 导入本地 `docs/evidence/task013/` 与 validation index；
2. 核对 6 carrier SHA / residual SHA / schema-v2 validation；
3. 对 ATC+N0 WFS/RAD/HOA 审核 EPD3/5 through-focus、distance peak、DOF50、MTFa@0D、TF mean、C4/C6/HOA RMS；
4. 形成 scientific PASS/FAIL；
5. PASS 后将 N0 纳入最终96配置层。

---

# 6. TASK-014 本地执行路线

坚持最短可靠路径，并保持现有 runner 结构：

```text
verify frozen provenance
→ build 5 cornea-layer models
→ solve 6 Q=0 starts
→ solve 18 physical carriers
→ classify historical power coverage
→ build 36 paired-MONO references
→ run 72 production configs
   └─ 每个 carrier 第一次进入 EDOF materialization 前执行 schema-v2 exact validation
      └─ 同 exact carrier SHA + residual SHA 的 PASS record 缓存复用
→ 1080 TF rows
→ ZMX archive / MODEL_INDEX
→ Web review
```

不新增独立 validation-preflight orchestration 层；现有“first EDOF materialization 前 hard gate”已满足 MVP 所需 fail-closed 语义。

不要求 TASK-013 scientific PASS 才能开始 TASK-014；二者是平行扩展。TASK-013 的成功结果仅作为方法学验证经验，不作为 TASK-014 光学输入。

首次正式 TASK-014 run 默认不使用 `--overwrite-models`。

---

# 7. Canonical archive

TASK-013：

```text
models/task013_native_reference/
  cornea/
  carriers/
  residual_validations/
  runs/<run_id>/pair_references/
  runs/<run_id>/configs/
  runs/<run_id>/MODEL_INDEX.csv
```

TASK-014：

```text
models/task014_vertex_corrected/
  corneas/                  # 5
  carriers/                 # 18
  residual_validations/
  runs/<run_id>/p0/         # 6
  runs/<run_id>/pair_references/  # 36
  runs/<run_id>/configs/    # 72
  runs/<run_id>/MODEL_INDEX.csv
```

TASK-014 primary MODEL_INDEX 仍为：

```text
5 + 6 + 18 + 36 + 72 = 137 records
```

Residual validation ZMX 属于 diagnostics/provenance，不并入137。

---

# 8. STOP conditions

立即停止当前 task，如果：

1. frozen residual DAT SHA mismatch；
2. `STD_IOL_EYE_2024` immutable hash mismatch；
3. TASK-008 manifest/lock drift；
4. TASK-009 production contract drift；
5. carrier P/Q 或 standard-eye SA replay fail；
6. standard-eye residual low-order hard gate fail；
7. actual-eye MONO/EDOF ray-health fail；
8. config model SHA / persisted EPD / archive SHA mismatch；
9. 需要修改 residual bytes、B0.20、vertex contract、focus window 或其他 frozen science 才能继续。

以下**不**单独构成 STOP：

```text
carrier power outside historical coverage
actual-eye SSAG piston/defocus diagnostic outside numerical tolerance
```

它们必须记录，并按需进入 Web mechanism review。

---

# 9. 不做的事情

MVP 明确不增加：

- patient-specific optimization；
- 多色、偏心/倾斜扩展；
- 新 composite score；
- 为扩展任务重跑 legacy TASK-011；
- 为结果好看 retune B0/residual；
- 额外数据库、并行调度或复杂 GUI；
- 无必要的 schema/framework 抽象。

---

# 10. 当前最短后续路径

```text
A. Web review TASK-013 local evidence
B. local TASK-014 72-config acquisition
C. Web review TASK-014
D. combine accepted N0 + A0V12/B0V12/C0V12 = 96 configs
E. render all through-focus supplement
```

PR #26 在 A/B/C 完成前继续保持 Draft / open / unmerged。