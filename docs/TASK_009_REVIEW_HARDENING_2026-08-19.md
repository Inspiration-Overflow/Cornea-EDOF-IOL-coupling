# TASK-009 文档与代码审查加固记录

日期：2026-08-19  
状态：Web review-hardening complete；offline/OpticStudio validation pending

## 1. 角色

本文补充 `TASK_009_FFT_MTF_MAIN_ANALYSIS_FREEZE_2026-08-19.md` 的**实现与验证合同**。主指标、频率域、贯焦网格、代表配置和 convergence/repeatability 数值 gate 不变。

若原冻结说明与本文在以下事项有表述差异，以本文为准：

- frozen manifest identity 的使用方式；
- real production backend；
- entity invariants；
- settings provenance；
- local candidate 与 formal sampling lock 的边界。

## 2. 审查发现与处理

### 2.1 Production integration 不能由独立 probe 代替

发现：早期代表脚本直接调用 optical primitives 并手工组装 JSON/CSV，没有经过正式 `AnalysisBackend`、`ConfigResult` validator、RunEnvironment、artifact store 和 failed/completed workflow。

修订：实现 `ZosFftMtfAnalysisBackend`。TASK-009 的 6-config integration 必须通过：

```text
frozen NominalConfig
→ ZosFftMtfAnalysisBackend.run_config
→ ConfigResult
→ run_analysis_batch
→ ProjectStore run/environment/artifact records
```

### 2.2 Representative identity 必须来自 TASK-008 manifest

发现：早期脚本用 base/cornea/platform/pupil 元组重新拼 carrier/config identity。

修订：新增 strict `load_formal_manifest_bundle()`：

- 读取 frozen `physical_carriers.csv`、`nominal_72.csv`、`manifest.sha256`；
- 重建18 locks；
- 用 canonical `build_manifests()` 重新产生72 configs；
- 要求 loaded CSV 与 rebuilt configs 全等；
- 对照 TASK-008 CSV SHA、manifest hash、lock-set hash。

三个 representative pair 只能从这个 bundle 选择。

### 2.3 Main settings provenance 收口

发现：main `AnalysisSettings` 混入 B0 和高阶像差读取的独立参数；部分字段改变 hash 却不改变主计算。

修订：`NOMINAL_MAIN_FFT_MTF_555_v2` 只保留真正影响主 FFT-MTF/MTFa 计算的参数。

exact SHA-256：

```text
0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc
```

DOF50 的50%是命名指标定义，不再是可调 settings 字段。

### 2.4 HOA readback 独立版本化

新增：

```text
TASK009_MFE_ZERN_HOA_555_v1
SHA256 7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2
```

固定 MFE ZERN Wave1/Field1/Samp1/Type1/Epsilon0/Vertex0/Z7..Z28。每个 `ConfigResult` 保存该 ID/hash。

### 2.5 Entity invariants 从“文件未变”升级到“内存实体未变”

发现：只检查 `.zmx` 文件 hash 不能证明通过焦期间 in-memory prescription 未被意外修改。

修订：新增 entity fingerprint before/after，至少覆盖 surfaces1..IMAGE 的：

- role/type；
- radius/conic；
- thickness/material；
- STOP identity；
- carrier first-order power；
- retina；
- IOL position/ELP；
- surface count。

OBJECT thickness 是唯一允许的贯焦分析变量，因此从 fingerprint 排除；分析结束必须恢复。

### 2.6 Runtime API evidence

FFT-MTF result 除 numerical data 外，新增记录：

- analysis API name；
- settings implementation type；
- sample-size enum；
- modulation enum；
- DataSeries count/runtime type；
- selected series runtime type；
- SeriesLabels / XLabel。

真实 2026 R1 wrapper 差异允许本地做机械适配，但不得静默猜列位置。

### 2.7 Traceability 修复

旧 `TRACE.md` 仍对应早期文档 ID universe，存在旧 trace 与旧 checker 互相“假通过”的风险。

已重建 current trace，并把 checker 更新为：

```text
URD-REQ 001..018
URD-AC  001..010
FR      001..010
DP      001..010
MDD-MOD 001..010
MDD-API 001..013
```

### 2.8 URD 自包含性恢复

把仍有效、但在分析架构简化时被过度压缩的 GUI、进度、日志、failed-only rerun、audit 与输出要求补回当前 URD；不改变科学模型或 TASK-005–008 locks。

## 3. TASK-009 local evidence 的身份

Local TASK-009 完成 convergence/repeatability/6-config integration 后，最多允许：

```text
evidence_only = true
formal_artifact = false
production_sampling_candidate_passed = true
production_sampling_locked = false
run72_started = false
```

Web 必须读取完整 GitHub evidence，审核 limited extraction diagnostic 和 runtime API mapping 后，才可创建 formal production-sampling lock。

## 4. 不变项

本次 review-hardening 没有改变：

- A0/B0.20/C0；
- 18 carrier P/R/Q/SA；
- 3 residual payloads/policies；
- residual low-order tolerance；
- 9 actual-power calibration evidence；
- TASK-007 review；
- TASK-008 18/3/72 formal identity；
- manifest hash；
- lock-set hash；
- TASK-009 representative set；
- 64/128/256 sampling set；
- convergence/repeatability numerical gates；
- 0..60 cpd MTFa definition；
- +0.50→−3.00D/0.25D through-focus grid。

## 5. 当前 STOP

Web review-hardening 已完成，但尚未跑新的本地离线回归和 OpticStudio TASK-009 batch。

因此当前不能声称：

- current branch unit tests PASS；
- real 2026 R1 FFT-MTF wrapper 已适配；
- real-ray footprint tuple mapping 已验证；
- 128 sampling 已锁定；
- Run72 ready。

下一步必须先完成本地完整离线回归，再在同一个大批次中完成 TASK-009 real validation。
