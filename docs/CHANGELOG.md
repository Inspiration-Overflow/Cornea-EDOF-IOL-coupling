# CHANGELOG

## 2026-08-17 — OpticStudio 2026 R1.00 本机联调

- ZOS session 同时支持 2026 R1.00 根目录 DLL 布局和旧版 `ZOS-API/Libraries` 布局。
- 在真实 Premium license 下通过主线程和 GUI-like worker thread 会话测试。
- 实机确认 Binary 4、Even Asphere、Coordinate Break 参数列，并加入写入后回读测试；测试使用临时系统，不保存 `.zos` 文件。
- 新增 Huygens PSF 专用 runner，将 ZOS-API 网格复制为纯 Python 不可变数据后再关闭 analysis。
- 新增 Zernike Standard 专用 runner，严格读取 UTF-16 文本并计算 C4、C6 与 n=3…6 HOA RMS。
- 生成 `uv.lock`，完成 Ruff 整理，并把真实 Zemax 测试入口限定为 `tests/zemax` 目录。
- 未建立或冻结正式 A0/B0/C0、carrier、residual、manifest，也未运行代表三配置或 Run72。

## 2026-08-17 — RMD v1.1

- 新增项目级开发约定：Python 包与虚拟环境统一使用 `uv` 管理。
- 正式依赖变更必须通过 `uv add` / `uv remove`，环境同步使用 `uv sync`，命令优先使用 `uv run`。
- 单元测试统一使用 `pytest`，所有自动化测试仍由 pytest 统一调度，包括 unit / Zemax integration / GUI smoke markers。
- 不引入第二套 Python 包管理或单元测试框架。

## 2026-08-17 — RMD v1.0

- 新建 Build Path，共 11 个小任务；按 setup → ZOS risk gate → store/domain → pure metrics → assets → B0 → provisional carrier/residual gate → formal carriers/manifest → 3-config analysis → GUI → Run72 排序。
- 前三任务明确测试命令、rollback 和 Git branch，形成 Build Path checkpoint。
- `TDD-TEST-401` 提前作为 ZOS worker-thread risk gate。
- `TDD-TEST-999` 固定为 TASK-007 → TASK-008 之间的科学数据 STOP gate；未解除不得生成正式 EDOF pair locks/Run72。
- 正式 Run72 前必须先通过 3 个代表配置的 sampling/Huygens-MTF cross-check。
- 每个 task 都有 local Git checkpoint；remote 未知，第一次 push/merge 仍需用户明确批准。
- 未加入患者级、多色、偏心/倾斜、并行、数据库或复杂 GUI。

## 2026-08-17 — TDD v1.2 / science-baseline consistency

- URD v1.3：B0 恢复为 A0-derived `Q_lock` 阈值 + 80/70% distance gates + deterministic recommendation + human confirmation/override reason；未增加候选或优化器。
- URD/MDD/TDD：贯焦固定为 analysis-layer object/incident vergence；retina、IOL power/conic、ELP 和实体面型不随贯焦改变。
- Analysis 输出增加 `retina-anchored` 与 `shape-recentered` 两个坐标；后者仅用于曲线形态比较，`ΔF_residual` 仍用 retina frame。
- `ZERO_HOA_PARAXIAL_REFERENCE` 纳入标准眼和 power-specific Q(P) achieved-SA oracle。
- `COMPLEX_OTF_GOLDEN_3x3_v1` 写成完整 JSON fixture，并锁定 `fftshift(fft2(ifftshift(...)))` convention。
- distance-peak 搜索加入边界 censor flag。
- residual 的 STOP gate 扩展为实际 payload piston/global-defocus + 每平台 low/median/high actual-power calibration；metadata flag 不能替代数值验证。
- A0/C0 numerical convergence 合并进现有 acceptance tests；没有新增测试 ID。
- ADD v1.4 仅同步 URD 版本；8 FR/DP 和 decoupled classification 不变。

## 2026-08-17 — TDD v1.1 / baseline alignment

- URD v1.2：删除 MVP Stop/Cancel 要求，新增 `URD-DEC-008`，明确长任务串行、失败后 Rerun。
- ADD v1.3：仅更新 source URD 与状态，不改变 8 个 FR/DP 或 decoupled 设计。
- MDD v1.2：统一 metric contract 为 `Zemax Huygens PSF → deterministic FFT → OTF/MTF/MTFa/VSOTF`；Huygens MTF 仅用于交叉验证。
- TDD v1.1：不显著增加测试数量，重点强化 A/B/C、Q(P)、phase-sensitive VSOTF、sampling convergence、Zernike 和 72/36 completeness oracle。
- B0 scan 与主 72 实验拆为两套 settings：`CORNEA_LOCK_B0_555_v1` 与 `NOMINAL_MAIN_555_v1`。
- `DOF_abs=VSOTF 0.10` 记录为 `DEC-001` 工程比较阈值，不宣称临床阈值。
- residual 科学 payload 仍由 `TDD-TEST-999` 阻断真实 Build Carriers；未增加占位处方。

## 2026-08-17 — TDD v1.0

- 新建 Check Plan，映射 URD-AC-001~015、MDD-API-001~012。
- 冻结 `ANALYSIS_MVP_555_v1`：555 nm、EPD3/5、+0.50→−3.00 D、0.25 D 步长、Huygens PSF sampling、MTFa/VSOTF/DOF 规则。
- 将 DOF_rel 固定为 VSOTF 50% 自身距离峰阈值；DOF_abs 固定为 VSOTF 0.10 工程阈值，并明确非临床阈值。
- 增加数值 oracle、sampling convergence、锁定/manifest/配对回归测试和 GUI/ZOS-API negative tests。
- worker-thread ZOS-API 调用增加 blocking environment smoke test。
- residual 完整数值资源仍缺失；仅其科学校准显式 deferred 为 `TDD-TEST-999`，并在 Build Carriers 实现前触发 STOP。

## 2026-08-17 — MDD v1.1

- 不改变 8 个模块架构，修正 `ADD-DP → MDD-MOD` trace 对应关系。
- 将 MDD 从 1140 行收敛为紧凑的 Building Blocks 文档；删除重复接口长篇说明。
- 12 个 public API 统一补齐 Inputs、Outputs、Side Effects、Preconditions、Postconditions、Invariants 和 Failure Behavior。
- 新增 `MDD-DATA-012 RunEnvironment`，记录程序版本、OpticStudio 版本、baseline/settings/manifest/lock hashes。
- 新增 `MDD-DATA-013 ResidualDefinition`，定义 residual 资源格式边界而不发明具体光学处方。
- 修正 Build 语义：core asset Build 不因 residual 缺失失败；`Build Carriers` 才把 3 个 validated residual 作为硬前置。
- 取消 `partial` run status；B0 五点任一失败即 action failed，但保留已成功 candidate artifacts。
- 将 GUI worker 上的 ZOS-API 调用标记为 TDD 必须验证的实现假设。
- 删除旧的假阳性 MDD validation 逻辑，改为逐 API contract lint。

## 2026-08-17 — MDD v1.0

- 将 ADD 的 8 个 DP 映射为 8 个 Building Blocks。
- 定义 12 个公共接口及其输入、输出、前置/后置条件、不变量、副作用和失败行为。
- 将 raw ZOS-API object 限制在 Zemax-facing 模块；GUI 和 manifest 不直接依赖 ZOSAPI。
- 定义本地 Project Store、18/72 manifest、carrier/pair lock、分析结果和 GUI event 数据契约。
- 明确 MVP 使用单一后台 worker 串行执行 Zemax 长流程，不增加并行或 Cancel 框架。
- 显式记录 URD 未给出三平台 residual 完整数值表这一输入数据缺口；MDD 不自行发明 residual 面型。
- 为 TDD 保留 `AnalysisSettings` 数值冻结和 contract oracle 工作。

## 2026-08-17 — ADD v1.2

- 保留 8 个 FR/DP 的设计拆分和 `DECOUPLED` 分类，不改变 MVP 科学范围。
- 将设计矩阵标题调整为 skill 检查器可识别的 `## FR / DP Design Matrix`。
- 将已批准的独立自包含 URD 复制到规范路径 `docs/URD.md`，作为后续 MDD 的正式输入。
- `.vibe/trace.json` 改为 `version + items + links` 结构；每条 link 只包含一个 source 和一个 target。
- 修正 TRACE 的语义映射：GUI 路径配置、失败/重跑、surrogate 命名、A0/B0/C0 冻结等同时链接到实际受影响的 FR/DP。
- `.vibe/coupling_history.json` 改用 `accepted_couplings` 复数标准字段。
- 从 ADD 删除重复的 requirement coverage 表和历史修订说明；追踪关系由 TRACE 保存，历史由本 CHANGELOG 保存。

## 2026-08-17 — ADD v1.1

- 将 DP-007 修订为前置的 `Project Store & Run State Boundary`。
- 显式公开 Assets / B0 / Carrier / Manifest / Analysis 对持久化边界的依赖。
- 删除 URD 未要求的 GUI “安全停止/Cancel”行为。
- 增加第三次 coupling retry，确认真实依赖公开后仍为 decoupled design。

## 2026-08-17 — ADD v1.0

- 初次完成 Design Split。
- 建立 8 个 FR/DP、FR/DP 矩阵和两次 coupling retry。
