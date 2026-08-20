# TASK-013 未治疗参考角膜扩展研究与 ZMX 模型归档计划

日期：2026-08-20  
状态：**科学与执行方案冻结；待代码实现与本地 OpticStudio 执行**  
任务 ID：`TASK-013-NATIVE-CORNEA-REFERENCE`

## 1. 背景与目的

TASK-011/TASK-012 已完成并接受的正式主矩阵为：

```text
A0 / B0 / C0
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 72 configurations
```

该矩阵完整回答“代表性屈光术后角膜条件下，加入某一非衍射 EDOF residual 相对于严格匹配 MONO carrier 会发生什么”。但它缺少一个更基础的参照层：**同一组 IOL 机制在未经屈光手术的参考角膜上本来呈现怎样的贯焦表现。**

TASK-013 因此新增一个独立的未治疗参考角膜层，目的不是修改 TASK-011 的主结果，也不是为了获得特定论文叙事，而是补足机制研究所需的基线对照数据。

TASK-013 的核心问题为：

> 在相同双基础眼、相同 IOL carrier 构建规则、相同三类 EDOF residual、相同双瞳孔和相同贯焦分析条件下，未治疗参考角膜与 A0/B0/C0 三类术后角膜相比，MONO 与 EDOF 的贯焦表现有何异同？

---

## 2. 不修改既有冻结结果

以下身份和证据继续保持只读，不因 TASK-013 改写：

```text
baseline_id = MVP_2026_v2
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-011 formal configs = 72
TASK-011 matched pairs = 36
TASK-011 through-focus rows = 1080
TASK-012 structured evidence = unchanged
```

特别禁止：

- 不把新角膜层加入或重写 TASK-008 `nominal_72.csv`；
- 不改变既有18个 physical carrier locks；
- 不修改 B0.20；
- 不重新优化 WFS/RAD/HOA residual；
- 不扩大已冻结的贯焦窗口、distance-peak 窗口或改变 MTFa/DOF50 定义；
- 不重跑既有72配置作为 TASK-013 的前置条件。

TASK-013 是**扩展研究层**，不是 `MVP_2026_v2` frozen manifest 的版本替换。

---

## 3. 新角膜身份：N0

### 3.1 正式命名

新增研究层 ID：

```text
N0 = native / untreated reference cornea
```

中文建议统一称：**未治疗参考角膜**或**原生参考角膜**。

不建议在正式方法中把 N0 简称为“正常眼”，原因是两个基础眼的解剖/屈光背景并不相同：

- `LB_AL2395 + N0`：Liou–Brennan 基础眼结构中的未治疗参考角膜；
- `ATC_M3_AL24477 + N0`：Atchison 约 −3 D 近视基础眼结构中的同一未治疗参考角膜光学模块。

因此，N0 描述的是**角膜状态**，不把 ATC 基础眼重新定义为正常眼。

### 3.2 N0 的光学定义

N0 直接采用项目已存在并用于 A0/B0/C0 构建的物理参考角膜 scaffold：

```text
scaffold_id = MAIN_CORNEA_LIOU_555_v1
anterior radius = 7.77 mm
anterior conic = -0.18
corneal thickness = 0.50 mm
posterior radius = 6.40 mm
posterior conic = -0.60
corneal index = 1.376
aqueous index = 1.336
wavelength = 555 nm
```

该定义的优点是：

1. N0 与 A0/B0/C0 具有同一参考角膜来源；
2. A0/B0/C0 的术后改变可解释为从同一 N0 scaffold 出发的设计变换；
3. 不需要引入第三套正常角膜参数或另一个外部模型；
4. 可直接复用现有 `build_reference_cornea_scaffold()` 与 carrier P→Q(P) 流程。

N0 不加入角膜屈光治疗、不加入人工 ΔC4^0、不加入近用区或 EDOF 角膜设计。

---

## 4. TASK-013 研究矩阵

### 4.1 新增 physical carriers

每个 `Base × N0 × Platform` 独立求 physical carrier：

```text
2 Base × 1 N0 × 3 Platform = 6 physical carriers
```

正式 carrier ID：

```text
CAR_<base_id>_N0_<platform_id>
```

例如：

```text
CAR_LB_AL2395_N0_WFS
CAR_ATC_M3_AL24477_N0_RAD
```

### 4.2 新增 nominal configurations

每个新 carrier 建立 matched MONO/EDOF，并分析两个瞳孔：

```text
6 carriers × 2 optic states × 2 pupils = 24 configurations
```

形成：

```text
12 matched MONO/EDOF pairs
24 through-focus curves
360 through-focus rows
```

每条贯焦曲线仍为15个 retina-anchored defocus planes。

### 4.3 完整研究数据矩阵

TASK-013 完成后，研究数据库可描述为：

```text
N0 / A0 / B0 / C0
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configurations
```

其中：

- 既有术后层：72配置，来自 TASK-011，保持冻结；
- 新增 N0 层：24配置，来自 TASK-013，独立 provenance；
- 两者可以在离线汇总时组合，但不得伪装成同一 frozen manifest/run。

---

## 5. IOL 与 matched MONO 规则

TASK-013 延续现有 matched-pair 设计。

“单焦点 IOL”不是一个跨平台共用的全局镜片，而是每个机制平台自己的 residual-free matched MONO carrier：

```text
N0 + WFS-matched MONO  ↔ N0 + WFS-like EDOF
N0 + RAD-matched MONO  ↔ N0 + RAD-like EDOF
N0 + HOA-matched MONO  ↔ N0 + HOA-like EDOF
```

同一 pair 内 MONO/EDOF 必须共享：

- physical power / radii；
- power-specific anterior conic Q(P)；
- center thickness；
- material；
- IOL axial position；
- base eye；
- cornea；
- pupil；
- analysis settings；
- paired-MONO angular-frequency reference。

唯一设计差异仍为相应平台的冻结 EDOF residual。

---

## 6. N0 carrier 构建规则

每个 `Base × N0 × Platform` 严格复用 TASK-007 已验证的 carrier 逻辑：

1. 在实际 `Base + N0`、fixed retina、Q=0 条件下求远焦 carrier power/对称曲率 P；
2. 把实际 P/R 放入 `STD_IOL_EYE_2024`；
3. 按平台求 power-specific `Q_k(P)`；
4. 把 Q 放回实际 `Base + N0`；
5. 按既有 P–Q 回查规则，必要时最多两次工程 recheck；
6. 验证最终 actual-eye R/Q replay；
7. 在标准眼 EPD6 复核相应平台 SA target；
8. 保存 canonical N0 physical carrier `.zmx` 和 SHA-256。

不得从 A0/B0/C0 直接复制 P、R 或 Q 到 N0。

---

## 7. Residual 复用与 power-envelope gate

TASK-013 不重新设计 residual。仍使用 TASK-008 已冻结的：

```text
WFS residual
RAD residual
HOA residual
```

但是，N0 会产生6个新的 carrier powers。因此，在任何 N0 EDOF 正式贯焦 acquisition 之前，必须执行 residual power-envelope preflight：

对每个平台分别比较新 N0 carrier power 与 TASK-007/TASK-008 已验证的该平台实际 carrier power 范围。

```text
existing_min_power(platform)
<= N0_power
<= existing_max_power(platform)
```

若全部6个 N0 carrier 均落在已验证 power envelope 内，则可直接复用冻结 residual。

若任一 N0 carrier 超出该平台已验证 power envelope：

- STOP 在 EDOF production acquisition 之前；
- 不修改 residual；
- 不外推声称 residual 已被验证；
- 需要另行增加该实际 power 的 residual replay/低阶污染/ray-health 验证；
- 验证通过后仍使用原 residual bytes/hash，不做重新优化。

---

## 8. 分析设置完全继承 TASK-009

TASK-013 不建立新的 MTF 定义。

正式分析继续使用：

```text
analysis_settings_id = NOMINAL_MAIN_FFT_MTF_555_v2
analysis_settings_sha256 = 0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc

acquisition_contract_id = TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
acquisition_contract_sha256 = f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d
frequency_scale_mode = paired_residual_free_MONO_EFFL
production_sampling = 128
```

冻结条件：

- 555 nm；
- EPD 3 / 5 mm；
- field 0°；
- centered/coaxial；
- retina-anchored defocus +0.50 → −3.00 D；
- −0.25 D step；
- 15 planes；
- 0–60 cpd，1 cpd step；
- MTFa 与固定 10/20/30/40/50/60 cpd；
- distance peak / DOF50 / TF mean / censor policy 均不变。

每个 N0 matched pair 重新从其 residual-free MONO 读取一次 EFFL，并在 MONO/EDOF 和所有 defocus planes 间共享。

---

## 9. ZMX 模型文件必须保留

### 9.1 原则

从 TASK-013 起，`.zmx` 不仅是运行时中间文件，而是正式研究 artifact。

每个最终参与数据计算的实际模型均必须：

1. 保存为独立 `.zmx`；
2. 有稳定、可预测的目录和文件名；
3. 记录 SHA-256；
4. 在模型索引中绑定 `config_id/pair_key/carrier_id`；
5. 禁止成功计算后只留下 CSV/JSON 而丢弃模型。

### 9.2 TASK-013 canonical model archive

固定本地目录：

```text
project_mvp_2026_v2_zmx/
└─ models/
   └─ task013_native_reference/
      ├─ cornea/
      │  └─ N0_REFERENCE_CORNEA.zmx
      ├─ carriers/
      │  ├─ CAR_LB_AL2395_N0_WFS.zmx
      │  ├─ CAR_LB_AL2395_N0_RAD.zmx
      │  ├─ CAR_LB_AL2395_N0_HOA.zmx
      │  ├─ CAR_ATC_M3_AL24477_N0_WFS.zmx
      │  ├─ CAR_ATC_M3_AL24477_N0_RAD.zmx
      │  └─ CAR_ATC_M3_AL24477_N0_HOA.zmx
      └─ runs/
         └─ <run_id>/
            ├─ pair_references/
            │  └─ <pair_key>.zmx          # 12 files
            ├─ configs/
            │  └─ <config_id>.zmx         # 24 exact analyzed models
            └─ MODEL_INDEX.csv
```

其中 `configs/<config_id>.zmx` 必须是**实际用于该 configuration through-focus acquisition 的 exact model snapshot**。

### 9.3 MODEL_INDEX.csv

至少包含：

```text
model_role
run_id
config_id
pair_key
carrier_id
base_id
cornea_id
platform_id
optic_state
pupil_mm
relative_path
sha256
```

`relative_path` 必须相对于 `project_mvp_2026_v2_zmx/`，GitHub evidence 不记录本机绝对路径。

### 9.4 原运行目录仍可保留

每个 configuration 的工作产物仍可写入：

```text
results/task013_native_reference/<run_id>/<config_id>/
  model.zmx
  through_focus.csv
  through_focus_mtfa.png
  mtf_at_zero_d.png
  config_result.json
```

但成功后必须把 `model.zmx` hash-verified copy 到 canonical model archive：

```text
models/task013_native_reference/runs/<run_id>/configs/<config_id>.zmx
```

若复制后的 SHA 与 `ConfigResult.model_hash_before` 不一致，则该 config 不得标记为 archive-complete。

---

## 10. 既有 TASK-011 ZMX 的补归档

现有实现已经保留 TASK-011 每个配置的：

```text
results/task011_run72/<run_id>/<config_id>/model.zmx
```

并保留36个 pair-MONO reference model：

```text
diagnostics/task011/pair_reference_models/<pair_key>.zmx
```

TASK-013 代码阶段应同时增加一个**纯文件归档工具**，在不重新运行 OpticStudio 的前提下，把现有 TASK-011 模型复制到稳定目录：

```text
models/task011_run72/archive/<run_id>/
  configs/<config_id>.zmx            # 72
  pair_references/<pair_key>.zmx     # 36
  MODEL_INDEX.csv
```

归档工具必须：

- 从 formal TASK-011 evidence/config result 解析身份；
- 校验源文件存在；
- 校验源 model SHA 与已记录 `model_sha256`/ConfigResult 一致；
- copy 后再次校验 SHA；
- 只做 provenance/文件管理，不启动 OpticStudio；
- 不修改 TASK-011 科学 evidence。

---

## 11. TASK-013 正式输出

### 11.1 本地结构化结果

建议固定：

```text
results/task013_native_reference/reports/<run_id>.json
```

### 11.2 GitHub sanitized evidence

成功后输出：

```text
docs/evidence/task013/TASK_013_NATIVE_REFERENCE_EVIDENCE.json
docs/evidence/task013/TASK_013_NATIVE_REFERENCE_CONFIG_RESULTS.csv
docs/evidence/task013/TASK_013_NATIVE_REFERENCE_THROUGH_FOCUS.csv
docs/evidence/task013/TASK_013_NATIVE_REFERENCE_PAIRED_DELTAS.csv
docs/evidence/task013/TASK_013_MODEL_INDEX.csv
```

预期：

```text
CONFIG_RESULTS = 24
THROUGH_FOCUS = 360
PAIRED_DELTAS = 12
MODEL_INDEX config snapshots = 24
MODEL_INDEX pair references = 12
MODEL_INDEX carriers = 6
```

N0 reference cornea本身另有1个 canonical `.zmx` 和 SHA 记录。

GitHub 不提交大型 `.zmx` 二进制模型；只提交相对路径、SHA 和结构化 evidence。`.zmx` 保存在本地项目指定 `models/` 归档目录。

---

## 12. Acceptance gates

TASK-013 只有以下全部满足才算完成：

```text
N0 reference cornea = 1 canonical ZMX + SHA
N0 physical carriers = 6/6
residual power-envelope preflight = PASS
pair references = 12/12
nominal configs completed = 24/24
failed configs = 0 after permitted failed-only resume
through-focus rows/config = 15
through-focus rows total = 360
matched deltas = 12
canonical config ZMX = 24/24
canonical pair-reference ZMX = 12/12
canonical carrier ZMX = 6/6
MODEL_INDEX hash/path verification = PASS
analysis/settings/acquisition identities = exact TASK-009 production identities
```

如果 power-envelope gate 失败，不得把 TASK-013 标为 production PASS。

---

## 13. 分析与论文使用

TASK-013 数据的首要角色是**研究参照层**，而不是强制进入最终论文主结果。

后续离线可生成：

1. N0/A0/B0/C0 × WFS/RAD/HOA 的完整贯焦曲线图；
2. 每个平台 EDOF 在 N0 与术后角膜中的差异；
3. `postoperative − N0` 的 descriptive contrasts；
4. N0 条件下各机制自身的 extension–quality trade-off；
5. 用于补充材料或机制解释的4×3 panel through-focus figures。

是否进入主文、补充材料或仅保留研究档案，由后续稿件编辑阶段决定。数据一旦完成，不因最终未使用而删除。

---

## 14. 实现顺序：先文档，后代码，最后本地光学执行

```text
Phase A — 文档冻结
  本文件
  → RMD/TRACE 状态同步

Phase B — 纯代码实现
  N0 extension manifest / carrier builder
  → backward-compatible custom carrier directory support
  → TASK-013 runner
  → ZMX canonical archive/index helper
  → TASK-011 retroactive archive helper
  → unit tests / ruff / compileall

Phase C — 本地 Windows / OpticStudio
  build N0 reference cornea
  → solve 6 N0 P/Q carriers
  → residual power-envelope gate
  → measure 12 paired-MONO EFFL references
  → run 24 configs
  → archive exact ZMX snapshots
  → write sanitized evidence

Phase D — Web/offline review
  24/12/360 reconstruction
  → ZMX index/hash audit
  → censor review
  → full N0/A0/B0/C0 through-focus supplement
```

---

## 15. STOP 条件

立即停止并返回科学/代码审核，如果出现任一项：

- 需要修改 TASK-008 manifest/lock hashes 才能运行 N0；
- 需要修改 B0.20 或 residual 才能让 N0 结果“更好看”；
- N0 carrier power 超出 frozen residual calibration envelope 且尚未补做 replay validation；
- custom carrier directory 改动导致 TASK-011 默认路径/行为改变；
- canonical archive 中 ZMX SHA 与实际 analyzed model 不一致；
- 24-config extension 被错误合并成新的“96-config frozen TASK-011 run”；
- 为减少 censoring 而改变 TASK-009 analysis windows/settings；
- 任何已有 TASK-011/TASK-012 structured evidence 因 TASK-013 被覆写。

TASK-013 的原则是：**增加缺失的未治疗角膜基线数据，同时最大限度保护既有冻结研究的身份和可追溯性。**
