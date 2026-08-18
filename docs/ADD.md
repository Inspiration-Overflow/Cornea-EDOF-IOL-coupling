# ADD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **文档角色：** Axiomatic Design Document / Design Split。  
> **目标：** 把已批准的 `URD-0001 v1.3` 拆成尽量独立、可按顺序实现的功能需求（FR）和设计参数（DP），在进入模块设计与编码前检查耦合。  
> **边界：** 本文不重新定义科学模型，不替代 URD；科学数值、冻结规则、18 个 physical carriers、72 个 nominal configurations、matched MONO/EDOF 原则均以 URD 为需求基线。

## Metadata

- project: Corneal Archetypes × Nondiffractive EDOF IOL Whole-Eye Zemax Automation
- document_id: ADD-0001
- version: 1.4
- status: approved
- source_urd: URD-0001 v1.3
- last_updated: 2026-08-17
- document_strength: standard
- target_stack_constraint: Python + ZOS-API + CustomTkinter
- design_goal: MVP、低耦合、可追溯、可单阶段重跑

---

# 1. 设计拆分原则

本项目采用顺序型研究工作流，因此完全“零依赖”并不现实。目标不是把每一步做成彼此不知道对方存在，而是让：

1. 每个设计部分只负责一个清楚的研究动作；
2. 上一步通过明确的文件/数据契约把结果交给下一步；
3. GUI 不包含科学计算逻辑；
4. Zemax 会话细节不散落到各个科学流程；
5. 已冻结的科学对象只能被读取，不能被后续步骤静默改写；
6. 失败可以停在当前阶段，并从已完成的锁定产物继续。

最终设计允许**有明确执行顺序的解耦设计（decoupled design）**，不追求为了矩阵好看而拆出没有意义的小模块。

---

# 2. Functional Requirements

| ID | Source | Functional Requirement | 完成条件摘要 |
| --- | --- | --- | --- |
| ADD-FR-001 | URD-REQ-001~004; URD-AC-001 | 建立可靠的 OpticStudio 运行环境边界，使软件能连接、检查、使用并关闭 ZOS-API 会话。 | 有效路径/license 成功；无效条件明确失败；Sequential Mode 可用。 |
| ADD-FR-002 | URD-REQ-005~008,010; URD-AC-002~005 | 生成并验证 MVP 基础科学资产：两个基座、`STD_IOL_EYE_2024`、`REF_MONO_CORNEA_LOCK`、A0、五个 B 候选、C0。 | 关键几何与标准眼锚点通过；模型保存为可追溯 `.zos`。 |
| ADD-FR-003 | URD-REQ-009,011; URD-ASM-003; URD-DEC-004 | 完成 B0 第一轮五点扫描，由用户确认一个代表性 B0 并冻结。 | 只在 `LB_AL2395 + REF_MONO_CORNEA_LOCK` 运行；B0 lock 生成后不可由主实验回调。 |
| ADD-FR-004 | URD-REQ-012~016; URD-AC-006~007 | 为 18 个 `Base × Cornea × Platform` 条件生成平台特异 physical carrier，并建立严格匹配的 MONO/EDOF pair。 | 每个 `P_ijk` 有对应 `Q_k(P_ijk)`；pair carrier 完全相同；仅 residual 不同；保存 `ΔF_residual`。 |
| ADD-FR-005 | URD-REQ-017~019; URD-AC-008~009 | 生成唯一、完整、可验证的实验清单：18 个 physical carrier 条件和 72 个 nominal analysis configurations。 | 组合计数、唯一性、555 nm、EPD3/EPD5、centered 条件全部通过。 |
| ADD-FR-006 | URD-REQ-020~022; URD-AC-010 | 使用 Zemax 运行统一分析并形成主科学结果，包括 matched-pair `EDOF − MONO` 比较。 | 每个成功配置产出规定的 MTF/PSF/像差/贯焦数据与配对差值。 |
| ADD-FR-007 | URD-REQ-023~027; URD-AC-011~014 | 保存 CSV、`.zos`、图像和日志，维护配置级追溯、失败状态和单阶段/单配置重跑能力。 | 任一结果可追溯；失败不计 completed；可选择性 rerun；surrogate 命名正确。 |
| ADD-FR-008 | URD-REQ-028; URD-AC-015; URD-DEC-001 | 提供极简 CustomTkinter GUI，让用户无需编辑代码即可执行 Build / Validate / B0 Scan / Build Carriers / Run 72 / Rerun。 | GUI 可选择路径和动作，显示进度、失败、日志和输出目录访问。 |

---

# 3. Design Parameters

| ID | Satisfies FR | Design Parameter | Rationale |
| --- | --- | --- | --- |
| ADD-DP-001 | ADD-FR-001 | **OpticStudio Session Boundary**：统一承担安装路径检查、NetHelper/ZOSAPI 初始化、Application 创建、license 检查、Primary System 获取、Sequential Mode 确认和关闭。 | 把 ZOS-API 生命周期集中在一个边界，避免每个研究流程各自连接/关闭 OpticStudio。 |
| ADD-DP-002 | ADD-FR-002 | **Scientific Asset Build & Validation Pipeline**：依据 URD 固定科学参数生成基础 `.zos`，并立即运行对应最小验证。 | 把“生成”和“验证”视为一个完整研究动作，避免生成未验证模型被后续误用。 |
| ADD-DP-003 | ADD-FR-003 | **B0 Scan & Human Lock Workflow**：只生成五个候选的统一扫描结果，等待用户选择后写入不可变 B0 lock。 | B0 是研究决策，不应由主 3×3 结果或复杂自动优化器反向决定。 |
| ADD-DP-004 | ADD-FR-004 | **Carrier Solve & Pair Lock Pipeline**：按 `Base × Cornea × Platform` 求 `P_ijk → Q_k(P_ijk)`，进行有限工程回查，随后一次性生成 MONO/EDOF pair lock。 | 把 power–conic 和 matched-pair 约束放在同一设计边界，防止 EDOF 状态被单独重新优化。 |
| ADD-DP-005 | ADD-FR-005 | **Deterministic Experiment Manifest Builder**：用稳定枚举和 ID 生成 18/72 清单，并在运行前验证组合计数与 nominal 条件。 | 实验矩阵是纯数据问题，应与 Zemax 计算分开，可在无 OpticStudio 时测试。 |
| ADD-DP-006 | ADD-FR-006 | **Zemax Analysis Workflow**：对 manifest 中单个配置运行统一 Zemax 分析、提取结果，并在配置完成后生成平台内 matched-pair 派生数据。 | 统一分析流程，避免不同组合手工使用不同分析设置。 |
| ADD-DP-007 | ADD-FR-007 | **Project Store & Run State Boundary**：统一规定项目目录、稳定配置 ID、CSV schema、`.zos`/图像命名、科学 lock metadata、run status、failed/completed 状态和 rerun 输入；所有产生正式研究产物的工作流均通过这一边界写入。 | 追溯和重跑是从第一份科学资产开始就存在的基础能力，应作为共享持久化边界，而不是分析结束后的附加层；MVP 不需要数据库或复杂任务系统。 |
| ADD-DP-008 | ADD-FR-008 | **Thin CustomTkinter Workflow Shell**：GUI 只调用应用工作流接口、显示状态和收集用户选择，不直接实现科学求解。 | 保持 GUI 极简，防止 UI 与光学逻辑耦合。 |

---

# 4. Design Matrix

## FR / DP Design Matrix

符号：

- `X`：该 DP 直接决定该 FR；
- `d`：该 FR 在执行时消费此前 DP 已提供的服务或已产生/冻结的产物，但不允许反向修改此前 DP。

为真实反映持久化依赖，矩阵按**实际执行顺序**排列，而不按 DP 编号排序。`DP-007 Project Store & Run State` 在第一份正式科学资产产生前即建立；之后 Assets、B0、Carrier、Manifest 和 Analysis 都通过它写入正式产物和状态。

| FR \ DP | DP-001 Session | DP-007 Project Store | DP-002 Assets | DP-003 B0 | DP-004 Carrier | DP-005 Manifest | DP-006 Analysis | DP-008 GUI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ADD-FR-001 Session | X |  |  |  |  |  |  |  |
| ADD-FR-007 Persistence / audit / rerun |  | X |  |  |  |  |  |  |
| ADD-FR-002 Scientific assets | d | d | X |  |  |  |  |  |
| ADD-FR-003 B0 scan/lock | d | d | d | X |  |  |  |  |
| ADD-FR-004 Carrier + pair locks | d | d | d | d | X |  |  |  |
| ADD-FR-005 18/72 manifests |  | d |  | d | d | X |  |  |
| ADD-FR-006 Zemax analyses | d | d |  |  | d | d | X |  |
| ADD-FR-008 GUI workflow | d | d | d | d | d | d | d | X |

## Matrix Classification

- **classification:** decoupled
- **reason:** 每个 FR 仍只有一个主要 DP；共享 Project Store、Session 和冻结产物的关系已显式画入矩阵。额外关系均为单向、按顺序消费，不允许下游反向修改上游科学定义或 lock。
- **execution_order_if_decoupled:**

\[
DP001
\rightarrow
DP007
\rightarrow
DP002
\rightarrow
DP003
\rightarrow
DP004
\rightarrow
DP005
\rightarrow
DP006
\]

`DP008` 是薄 GUI 外壳，在工作流接口稳定后调用上述步骤，不改变科学执行顺序。

关键不可逆边界：

\[
\boxed{B0\ LOCK}
\]

之后 carrier workflow 只能读取 B0；

\[
\boxed{PHYSICAL\ CARRIER\ LOCK}
\]

之后 MONO/EDOF 分析只能读取 carrier；

\[
\boxed{MANIFEST\ VALID}
\]

之后 nominal runner 只执行 manifest，不在运行中自行增加/删除配置。

Project Store 只负责持久化、索引和状态，不拥有改变科学对象内容的权限。

---

# 5. Coupling Retry Log

| Attempt | Problem | Change Made | Result |
| --- | --- | --- | --- |
| 1 | 初始直觉方案使用一个“Zemax Automation Controller”同时负责连接、建模、B0、carrier、分析、CSV 和 GUI；任何修改都会波及多数功能。 | 按研究阶段拆成 Session / Assets / B0 / Carrier / Manifest / Analysis / Persistence / GUI 八个设计责任，并用冻结产物传递状态。 | 从 dense coupling 降为顺序型依赖。 |
| 2 | GUI 若直接访问 ZOS-API 和模型对象，会使界面状态与科学计算强耦合；manifest 若由 analysis runner 临时生成，也会使实验矩阵无法独立验证。 | 将 GUI 定义为薄 workflow shell；将 18/72 manifest 作为独立确定性 DP，在任何分析开始前生成和校验。 | 得到接近 triangular 的 decoupled 设计。 |
| 3 | 前一版矩阵把 persistence 放在工作流末端，隐藏了 Assets/B0/Carrier/Manifest/Analysis 都需要保存 `.zos`、CSV、图像、lock 和状态的真实依赖。 | 将 DP-007 明确定义为 `Project Store & Run State Boundary`，前移到科学资产生成之前，并在矩阵中显式标记所有工作流对它的单向依赖。 | 真实依赖被公开后，矩阵仍保持有序的 lower-triangular / decoupled 结构，无需增加新模块。 |

---

# 6. Accepted Coupling

**无需要接受的结构性耦合。**

以下属于明确的顺序依赖，不记录为 Accepted Coupling：

1. 产生正式研究产物的工作流必须通过 `Project Store & Run State Boundary` 写入项目目录和状态；
2. B0 scan 必须消费已验证的 LB/REF/B-candidate 模型；
3. carrier 求解必须消费冻结的 A0/B0/C0 和标准眼；
4. nominal analysis 必须消费 carrier locks 和 validated manifest；
5. GUI 必须调用上述工作流；
6. 所有真实 Zemax 工作流必须经统一 Session Boundary 访问 OpticStudio。

这些依赖只允许**上游 → 下游**传播，不允许下游回写上游科学定义。

---

# 7. 科学锁定边界

为了防止实现过程中“自动优化”破坏研究设计，ADD 把以下对象视为明确锁定边界：

| Lock | 产生阶段 | 后续允许 | 后续禁止 |
| --- | --- | --- | --- |
| `STD_IOL_EYE_2024_LOCK` | DP-002 | 读取、复制用于校准 | 因某个平台结果改变标准眼 |
| `A0_LOCK` | DP-002 | 用于两个基座 | 因 WFS/RAD/HOA 表现重新调整 |
| `B0_LOCK` | DP-003 | 用于 carrier 和主实验 | 因主 3×3 结果重新选择 B0 |
| `C0_LOCK` | DP-002 | 用于两个基座 | 优化 wT 或 ADD 以改善主结果 |
| `CARRIER_LOCK_{i,j,k}` | DP-004 | 同时生成 MONO 与 EDOF | 为 EDOF 单独修改 P/R/Q/CT/material |
| `RESIDUAL_LOCK_k` | DP-004/既定 surrogate 输入 | 叠加到对应 carrier | 为某个 Base/Cornea 单独重做 residual |
| `MANIFEST_72_LOCK` | DP-005 | 顺序运行或选择性 rerun | runner 运行中静默新增/删除配置 |

---

# 8. 失败与恢复设计要求

这些不是新的用户需求，而是为已存在的 URD failed/rerun 要求提供设计边界。

| Stage | Failure behavior | Recovery input |
| --- | --- | --- |
| Session | 不创建研究产物；显示连接/license 原因 | 修复路径/license 后重试 |
| Asset build/validate | 当前 asset 标记 failed；不创建 lock | 重新 build/validate 该 asset |
| B0 scan | 保留已完成候选结果；未完成候选可重跑 | 五点 scan manifest |
| B0 user lock | 未选择时不得进入正式 carrier build | 用户选择 candidate ID |
| Carrier solve | 单个 carrier failed，不生成该 pair lock | Base/Cornea/Platform ID |
| Manifest validation | 不允许开始 Run 72 | 修复 lock/manifest 后重建 |
| Nominal analysis | 仅该 config failed；其他完成结果保留 | config ID |
| Export | 计算结果不得因图像/CSV 写入失败被标记为完整成功 | config ID + export stage |

---

# 9. MDD 入口边界

若本 ADD 通过 checkpoint，MDD 应围绕上述 DP 设计实际 Building Blocks。MDD 至少需要定义：

- ZOS-API session adapter；
- 科学配置/锁定数据结构；
- model builder / validator；
- B0 scan service；
- carrier solver；
- manifest builder；
- analysis runner；
- project store / run-state repository；
- CustomTkinter GUI shell；
- 公共接口的 inputs / outputs / preconditions / postconditions / invariants / side effects。

MDD 不应把每一个 Zemax surface 做成一个 Python 模块，也不应为未来患者级建模、云端运行、并行集群或复杂 GUI 预先增加抽象层。

---

# 10. ADD Completion Gate

- [x] 每个影响行为的已确认 URD requirement 均映射到 FR。
- [x] 每个 FR 均有一个主要 DP。
- [x] Design Matrix 已建立。
- [x] Coupling classification 已明确。
- [x] 已记录结构重试过程。
- [x] 当前没有必须接受的 residual structural coupling。
- [x] 科学 lock 边界已显式记录。
- [x] 没有为了追求对角矩阵而把系统拆成无意义小块。
- [x] 没有引入 URD Out-of-Scope 的未来功能。
- [x] `docs/TRACE.md` 与 `.vibe/trace.json` 已按稳定 ID 建立逐条追踪，并使用 skill 兼容 schema。

## Checkpoint Result

\[
\boxed{
ADD\ CLASSIFICATION = DECOUPLED
}
\]

建议实现顺序为：

\[
\boxed{
Session
\rightarrow
Project\ Store
\rightarrow
Scientific\ Assets
\rightarrow
B0\ Lock
\rightarrow
Carrier\ Locks
\rightarrow
18/72\ Manifest
\rightarrow
Analysis
}
\]

Project Store / Run State 从第一份正式资产开始贯穿记录；CustomTkinter GUI 作为薄外壳调用这些工作流。

**状态：本轮审核问题已修订，ADD 已达到 Design Split checkpoint-ready；等待用户确认后进入 MDD。**
