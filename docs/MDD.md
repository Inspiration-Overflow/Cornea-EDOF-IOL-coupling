# MDD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **Building Blocks / Module Design Document。** 将 `ADD-0001 v1.4` 的 DP 落实为模块、接口、契约和数据结构；科学定义由 `URD-0001 v1.4` 通过稳定 ID 提供，本文件不重复其长篇科学叙述。URD v1.4 的 standard-eye 6 mm 修订不改变本 MDD 的模块拆分。

## Metadata

- document_id: MDD-0001
- version: 1.3
- status: active
- source_add: ADD-0001 v1.4
- source_urd: URD-0001 v1.4
- last_updated: 2026-08-19
- stack: Python + ZOS-API + CustomTkinter
- optical_oracle: Zemax OpticStudio
- persistence: local filesystem; CSV + canonical `.zmx` + images + text log；历史 `.zos` 仅保留 provenance

## Architecture Summary

```text
CustomTkinter Shell
        |
        v
 workflow dispatch
   |           |
   v           v
ZOS Session  Project Store
   |           ^
   v           |
Assets -> B0 -> Carrier -> Manifest -> Analysis
```

- GUI、Manifest、Project Store 不持有 raw ZOSAPI object。
- 所有正式科学产物通过 Project Store 写入；lock 同 ID 不可被不同内容覆盖。
- 主流程串行执行；不引入数据库、Web、并行 Zemax 作业或第二套光学引擎。
- `AnalysisSettings` 的数值由 TDD 在实现前冻结。

## Module List

| ID | Module | Related DP | Responsibility | Non-Responsibility |
| --- | --- | --- | --- | --- |
| MDD-MOD-001 | `ZosSessionAdapter` | ADD-DP-001 | 建立/验证/关闭 ZOS-API 会话并提供 `ZosSession`。 | 不建科学模型、不保存结果。 |
| MDD-MOD-002 | `ProjectStore` | ADD-DP-007 | 管理目录、artifact、lock、hash、run history 和 rerun 状态。 | 不解释光学、不调用 Zemax。 |
| MDD-MOD-003 | `ScientificAssetWorkflow` | ADD-DP-002 | 建立/验证两个 base、标准眼、REF_MONO、A0、5 个 B candidate、C0；报告 residual readiness。 | 不选择 B0、不建 carrier。 |
| MDD-MOD-004 | `B0Workflow` | ADD-DP-003 | 运行固定五点 B0 scan，计算 A0-derived `Q_lock` gates 和确定性推荐，并把用户确认/override 写成不可变 B0 lock。 | 不引入复杂自动形态分类器；不根据主 3×3 结果回调 B0。 |
| MDD-MOD-005 | `CarrierWorkflow` | ADD-DP-004 | 求 18 个 `P→Q(P)` carrier，验证 residual，生成 matched MONO/EDOF locks。 | 不修改 A0/B0/C0；不为 EDOF 单独调 carrier。 |
| MDD-MOD-006 | `ManifestBuilder` | ADD-DP-005 | 纯数据生成/验证 18 carrier manifest 与 72 nominal manifest。 | 不调用 Zemax。 |
| MDD-MOD-007 | `AnalysisWorkflow` | ADD-DP-006 | 按 manifest 运行 Zemax 分析、导出结果并生成 `EDOF−MONO` paired delta。 | 不改 carrier/manifest。 |
| MDD-MOD-008 | `DesktopAppShell` | ADD-DP-008 | 极简 CustomTkinter UI、动作调度、进度/日志/失败/rerun 显示。 | 不实现光学算法、不直接编辑 `.zmx`。 |

## Module Dependency Notes

| Module | Depends On | Why | Risk |
| --- | --- | --- | --- |
| MOD-001 | installed ZOSAPI / Python-.NET bridge | 外部 API 生命周期 | medium |
| MOD-002 | stdlib filesystem/CSV/hash/logging | 本地持久化 | low |
| MOD-003 | MOD-001, MOD-002 | Zemax 建模 + 保存资产 | medium |
| MOD-004 | MOD-001, MOD-002 | B candidate 分析 + B0 lock | low |
| MOD-005 | MOD-001, MOD-002 | power/conic solve + pair lock | medium |
| MOD-006 | MOD-002 | 读取 lock 索引生成 manifest | low |
| MOD-007 | MOD-001, MOD-002 | Zemax 分析 + 结果持久化 | medium |
| MOD-008 | MOD-001~007 的 public interfaces | 仅做 orchestration | medium |

## Public Interfaces

| ID | Module | Interface | Inputs | Outputs | Side Effects |
| --- | --- | --- | --- | --- | --- |
| MDD-API-001 | MOD-001 | `open_zos_session` | `install_dir` | `ZosSession` context | 加载 .NET；启动/关闭 OpticStudio |
| MDD-API-002 | MOD-002 | `open_project_store` | `project_dir, baseline` | `ProjectStore` | 创建/验证项目目录与 metadata |
| MDD-API-003 | MOD-002 | `record_artifact` | `store, ArtifactRecord, lock` | `ArtifactRef` | 写文件/CSV/hash；lock 可原子登记 |
| MDD-API-004 | MOD-003 | `build_scientific_assets` | `session, store, baseline` | `AssetBuildReport` | Zemax 建模；写 `.zmx`/validation/locks |
| MDD-API-005 | MOD-003 | `validate_scientific_assets` | `session, store, baseline` | `ValidationReport` | 只写 validation/log；不改科学 lock |
| MDD-API-006 | MOD-004 | `run_b0_scan` | `session, store, B0 settings` | `B0ScanReport` | Zemax 分析；写 A0 thresholds、candidate gates/ranking、CSV/图像/log |
| MDD-API-007 | MOD-004 | `lock_b0` | `store, candidate_id, morphology_decisions, selection_reason` | `B0Lock` | 一次性写不可变 B0 lock |
| MDD-API-008 | MOD-005 | `build_carrier_locks` | `session, store, baseline` | `CarrierBuildReport` | Zemax solve；写 carrier/pair locks |
| MDD-API-009 | MOD-006 | `build_manifests` | `store` | `ManifestBundle` | 写 18/72 CSV + hash |
| MDD-API-010 | MOD-007 | `run_analysis` | `session, store, manifest, settings, selection` | `RunSummary` | Zemax 分析；写 CSV/`.zmx`/images/log |
| MDD-API-011 | MOD-008 | `launch_desktop_app` | none | none | 创建 GUI main loop |
| MDD-API-012 | MOD-008 | `submit_action` | `ActionRequest, event_sink` | none | 串行调度一个 workflow；发 `ProgressEvent` |

## Contracts

| API | Preconditions | Postconditions | Invariants | Failure Behavior |
| --- | --- | --- | --- | --- |
| MDD-API-001 | install dir/API files/license 有效 | 返回非空 `PrimarySystem`；离开 context 必关闭 app | 一个 long action 一个 session；raw ZOSAPI 不越过 Zemax-facing 边界 | 环境/初始化/连接/license 分别抛明确错误；license 失败先关闭 app |
| MDD-API-002 | project dir 可写；baseline 有版本 ID | 规范目录与 metadata 可用 | 路径相对 project root；项目 baseline 不静默切换 | 不可写或 schema 冲突即失败 |
| MDD-API-003 | artifact 源存在且 record 完整 | 文件成功后才登记；返回稳定 ref/hash | lock 同 ID：同内容可 no-op，不同内容禁止覆盖 | 写入/hash/schema 失败不记 completed |
| MDD-API-004 | session/store 可用；无冲突 lock | core assets 成功项保存；返回 residual readiness | Build 成功**不要求 residual 已提供**；B candidates 不是 B0；不建 carrier | core asset validation 失败则该 asset 无 lock；已成功 lock 保留 |
| MDD-API-005 | 对应 core assets 已存在 | 返回 core validation + `carrier_ready`/residual readiness | 不优化、不重写 lock | 缺失/失配进入 failed finding，不伪装通过 |
| MDD-API-006 | LB、REF_MONO、A0、5 candidates、冻结 B0 settings 均有效 | 五点都成功才得到 complete report，并含 A0 thresholds、distance gates、DOF_lock_abs 和 deterministic recommendation | 所有候选同条件；morphology reject 只由显式人工标记提供，排序算法本身确定 | 任一候选失败则 action=`failed`，保留成功 artifact；禁止 `lock_b0` |
| MDD-API-007 | 最近一次完整五点 scan；candidate ID 合法；morphology decisions 完整；无 B0 lock | 产生唯一 B0 lock，保存 recommendation rank、scan hash 和 selection reason | 推荐项可直接确认；override 必须有 reason；B0 后续只读 | 非完整 scan/非法 ID/缺 reason/冲突 lock 即失败 |
| MDD-API-008 | A0/B0/C0、bases、标准眼与 `ZERO_HOA_PARAXIAL_REFERENCE` 有效；3 个 `ResidualDefinition` payload 已验证 | 先求 18 carrier powers；每个平台 residual 在其 low/median/high actual power 代表点通过科学校准 gate 后，才产生 18 carrier/pair locks | MONO/EDOF carrier 完全相同，仅 residual 不同；SA 相对 ZERO_HOA reference 计算；保存 `ΔF_residual` | residual gate/单 key/pair invariant 任一失败则对应正式 lock 不产生；不足 18 禁止 manifest |
| MDD-API-009 | 18 carrier locks 完整且 hash 有效 | 生成 exactly 18 + 72 unique rows 与 `manifest_hash` | 枚举只允许 URD nominal 维度；无 Zemax 调用 | 缺 lock、重复、数量/固定字段错误即拒绝生成 |
| MDD-API-010 | manifest/hash/locks/settings 有效；selection 属于 manifest | 每 config 必需 artifact 全写成功后才 `completed`；每个 TF row 同时保存 retina-anchored 与 shape-recentered 坐标；可生成 paired delta | 贯焦只改变 analysis vergence，retina/IOL/ELP/实体面型不变；shape recenter 仅后处理；optical oracle=Zemax；主 metric 只由 Huygens PSF 确定性后处理得到 | 单 config 失败只标该 target failed；其余完成结果保留；rerun 新 `run_id` |
| MDD-API-011 | GUI runtime 可用 | UI 提供 URD 指定最小动作/路径/进度/日志/rerun | GUI 不持有 scientific truth 或 raw `PrimarySystem` | 初始化失败显示明确错误并退出，不创建假成功状态 |
| MDD-API-012 | 当前无 long action；前置 lock 满足 | action 结束产生 completed/failed event 与 run record | 同时最多一个 long action；不提供 Cancel/Pause | busy 或 workflow exception 转 failed event + log；不得吞异常后显示成功 |

## Data Structures

| ID | Used By | Shape / Fields | Mutability / Access | Justification |
| --- | --- | --- | --- | --- |
| MDD-DATA-001 | MOD-002~007 | `ScientificBaseline`: `baseline_id, base_specs, standard_eye_spec, cornea_specs, b_candidates, platform_specs, nominal_condition, iteration_limit` | frozen/read-many | 消除散落 magic numbers |
| MDD-DATA-002 | MOD-001,003~005,007 | `ZosSession`: `app, zosapi, system` | mutable/external-handle | 限制 ZOSAPI 边界 |
| MDD-DATA-003 | MOD-002~007 | `ArtifactRecord/ArtifactRef`: `id,type,path,sha256,baseline_id,run_id,locked` | record→frozen ref | 统一文件/lock 引用 |
| MDD-DATA-004 | MOD-002,008 | `RunRecord`: `run_id,action,target_id,status,started_at,finished_at,error_* , environment_ref` | append-only | failed/completed 与 rerun 审计 |
| MDD-DATA-005 | MOD-004 | `B0CandidateResult/B0Lock`: candidate ID、`ΔC4`、Q_lock curves、A0 thresholds、distance retention、DOF_lock_abs、morphology flag/reason、recommendation rank；lock 含 chosen ID/scan hash/selection reason | candidate frozen；lock immutable | 确定性推荐与人工确认都可审计 |
| MDD-DATA-006 | MOD-005,006 | `CarrierKey/CarrierLock`: base/cornea/platform + `P,R_ant,R_post,Q,CT,material,SA,ΔF_residual,refs` | frozen | 18 physical carriers |
| MDD-DATA-007 | MOD-006,007 | `NominalConfig`: config/carrier IDs + base/cornea/platform/state/pupil/wavelength/alignment | frozen/read-many | 72 条规模无需 dataframe 架构 |
| MDD-DATA-008 | MOD-004,007 | `AnalysisSettings`: settings ID、defocus range/step、DOF threshold、MTF/PSF/Zernike/VSOTF settings | frozen | 数值由 TDD 冻结 |
| MDD-DATA-009 | MOD-007 | `ConfigResult`: config/run IDs、scalar metrics、TF rows(`defocus_retina_d`,`defocus_shape_d`)、aberrations、footprints、artifact refs、status | frozen result | 保留因果性的 retina frame，同时提供形态比较 frame |
| MDD-DATA-010 | MOD-007 | `MatchedPairDelta`: pair key、MONO/EDOF IDs、delta metrics | derived immutable | 主机制比较 |
| MDD-DATA-011 | MOD-008 | `ActionRequest/ProgressEvent`: action/paths/selected IDs；timestamp/status/message/counts | request frozen；event append-only | GUI 与 workflow 隔离 |
| MDD-DATA-012 | MOD-002,007,008 | `RunEnvironment`: `program_version, opticstudio_version, baseline_id, analysis_settings_id, manifest_hash, lock_set_hash` | frozen/per-run | 满足可重复性与版本追踪 |
| MDD-DATA-013 | MOD-003,005 | `ResidualDefinition`: `residual_id,platform,version,representation,payload_ref,units,radial_domain,piston_removed,defocus_removed,sha256` | frozen/read-many | 定义合法 residual 资源而不发明光学处方 |

`ResidualDefinition.representation` MVP 允许 `radial_sag_samples | analytic_coefficients | grid_sag_resource`。具体 WFS/RAD/HOA 数值仍由科学 baseline resource 提供；`validated=True` 只有在实际 payload 的 piston/global-defocus 检查以及平台 low/median/high actual-power gate 均完成后才成立。

## Artifact / Lock Contract

```text
project/
  models/{assets,b_candidates,carriers,configs}/
  locks/{asset_locks,b0_lock,residual_locks,carrier_locks}.csv
  manifests/{physical_carriers,nominal_72}.csv
  results/{config_results,through_focus,matched_pair_delta}.csv
  results/images/<config_id>/
  logs/{run_history.csv,app.log}
```

- CSV 为主结构化交付；`.zmx` 为当前规范可追溯模型；历史 `.zos` 只保留原始 provenance；图像来自 Zemax 输出或 Zemax 数值的确定性绘图。
- lock `.zmx` / residual payload 记录 SHA-256；用途是检测静默修改，不是安全加密。
- `run_history.csv` append-only；最新状态由 target + 时间派生。
- `RunEnvironment` 每次正式 action 都记录；对应的 baseline/manifest/lock hashes 使结果可复跑。
- 标准眼、A0、B0、C0、3 residual、18 carrier、72 manifest 均禁止下游原地改写。

## Workflow Rules

1. **Build**：建立 core scientific assets。residual 缺失不使 Build 假失败，但 `ValidationReport.carrier_ready=False`。
2. **Validate**：只读复核 core assets，并报告 residual readiness；不产生新的科学解。
3. **B0 Scan**：固定五点；任一点失败则 action=`failed`，但已成功候选保留；不存在 `partial` run status。
4. **Build Carriers**：3 个 residual 必须存在且 hash 正确；实际 payload 的 piston/global-defocus 与各平台 low/median/high actual-power gate 都通过后才能成为正式 residual lock；metadata flag 不能替代数值验证。
5. **Manifest**：只有 18 carrier 完整时才能生成 72 nominal manifest。
6. **Run/Rerun**：每个 target 新建 `RunRecord + RunEnvironment`；只有 CSV/`.zmx`/必需图像都成功才 completed。
7. **Matched pair**：同一 base/cornea/platform/pupil 的 MONO 与 EDOF 均完成后才生成 `EDOF−MONO`；`ΔF_residual` 使用 retina-anchored frame，shape-recentered frame 只比较曲线形态。
8. **GUI worker assumption**：默认用单一后台 worker 避免 Tk 主循环阻塞；**这不是已证明的 ZOS-API thread-safety 事实**，TDD 必须先做 connect→operate→close smoke test。若 oracle 失败，只调整 orchestration placement，不改变上述科学模块接口。

## Error Model

| Error | Meaning / Required Outcome |
| --- | --- |
| `ZosEnvironmentError / ZosLicenseError` | 环境或 license 无效；失败且不创建研究产物 |
| `ProjectStoreError / LockedArtifactConflict` | 写入失败或 lock 冲突；不得记 completed |
| `AssetValidationError` | 当前 asset 无 lock；其他已通过 lock 保留 |
| `ScientificInvariantError` | pair/manifest/lock 违反科学不变量；阻断下游 |
| `ZemaxOperationError` | 当前 solve/analysis target failed |
| `ExportError` | 必需输出未完成；当前 target failed |
| `WorkflowBusyError` | 已有 long action；不启动第二个 |

## Implementation Style Constraints

- 默认 pure function + frozen dataclass；显式可变边界仅 ZOS session、filesystem store、GUI state。
- GUI 不 `import clr/ZOSAPI`；ManifestBuilder 不 `import Zemax`。
- 不引入 ORM、数据库、Web framework、message broker、plugin system 或“每个 Zemax surface 一个 class”。
- WFS/RAD/HOA 用 `PlatformSpec/ResidualDefinition` 数据和少量明确分支，不建立深继承体系。
- `numpy` 只用于 Zemax 数组/确定性指标；`matplotlib` 只用于结果图；Zemax 始终是 optical oracle。
- 用户可见名称保持 `WFS-like / RAD-like / HOA-like surrogate` 或中文等价。
- 三个平台 residual 的完整数值表目前不在 URD 中；MDD 不填充占位处方。缺失时 Build Carriers 必须失败为缺少 baseline resource。

## MDD Completion Gate

- [x] 8 个模块分别映射到正确 ADD-DP，责任/非责任明确。
- [x] 12 个 public interfaces 均具有 Inputs、Outputs、Side Effects、Preconditions、Postconditions、Invariants、Failure Behavior。
- [x] 关键数据默认 immutable/append-only；`RunEnvironment` 覆盖程序/Zemax/baseline/settings/manifest/lock 版本追踪。
- [x] `ResidualDefinition` 定义资源契约但不发明科学面型。
- [x] Build/residual readiness、B0 failed 状态、carrier/pair lock 语义无冲突。
- [x] worker-thread ZOS-API 被标记为待 TDD 验证的实现假设，而不是平台事实。
- [x] 未引入 URD 范围外的数据库、并行、Cancel、复杂 GUI 或患者级框架。
- [x] MDD 只保留 Building Blocks 阶段需要的信息；测试 oracle 留给 TDD。

**Result:** `MDD-0001 v1.3` 继续作为当前有效模块设计基线；URD v1.4 的 6 mm standard-eye 数值修订和 `.zmx` 规范迁移不改变 8 模块 / 12 API 架构拆分。
