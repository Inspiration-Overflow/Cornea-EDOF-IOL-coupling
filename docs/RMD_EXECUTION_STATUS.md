# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件只记录截至 2026-08-17 的真实代码状态，不修改科学规范。

## 当前结论

当前仓库已经完成 **OpticStudio 之外可独立实现的 MVP 代码层**。所有需要真实 OpticStudio/ZOS-API 光学运行才能判定的项目仍保持为待验证状态；没有用合成数据生成正式科学 lock，也没有声称已经完成 72 配置主实验。

当前离线单元测试：

```text
59 passed
```

当前仍未完成的环境项：

- `uv.lock` 尚未生成；当前执行环境无法访问依赖源，离线 resolver 也没有完整缓存，因此没有伪造 lockfile。
- `uv sync` 尚未在目标 Windows 工作站完成。
- `ruff` 尚未在当前执行环境运行成功；目标工作站需补跑。
- OpticStudio 2026 R1、真实 ZOS-API license、worker-thread gate、GUI display smoke、Huygens/Zernike/MTF cross-check 均待本地完成。

## RMD task 状态

| RMD task | Git | 当前状态 | 本地 OpticStudio 阶段仍需完成 |
| --- | --- | --- | --- |
| TASK-001 Project Setup | scaffold commit `b53dd798` | **部分完成**：`pyproject.toml`、src/tests、fixture、ignore 已有 | 生成 `uv.lock`；`uv sync`；`uv run ruff check .` |
| TASK-002 ZOS session | PR #2 | **代码完成**：typed session/errors/close semantics + worker test | TDD-001/101/401 真实连接和 worker-thread gate |
| TASK-003 Domain + ProjectStore | PR #3 | **离线完成**：settings、hash、lock、run state、schema、Unicode path | 与真实 `.zos` artifact 一起做一次集成回放 |
| TASK-004 metric engine | PR #4 | **离线完成**：complex OTF、MTF、MTFa、VSOTF、DOF、frequency、delta | 用真实 Huygens PSF/MTF 做 TDD-209/403 交叉验证 |
| TASK-005 scientific assets | PR #5 | **离线合同完成**：base/STD/A0/B/C0 参数与 C0 quintic、backend 边界 | 完成 Binary 4/Even Asphere 实际参数映射；建立并验证 `.zos` assets、ZERO_HOA、REF_MONO |
| TASK-006 B0 | PR #6 | **算法完成**：A0 阈值、80/70% gate、DOF rank、morphology/override、scan hash | 运行真实五点 B scan；人工 morphology decision；写唯一 B0 lock |
| TASK-007 carrier science gate | PR #7 + #13 | **门控与正式 lock 编排完成** | 实际求 18 个 P/Q；STD-eye achieved-SA 回放；提供 3 个 residual payload；low/median/high 校准；解除 TDD-999 |
| TASK-008 carrier/pair locks + manifest | PR #8 + #13 | **生成器/CSV 导出完成**；不会在 gate 前产出正式清单 | TASK-007 通过后生成正式 18 lock、36 pair、72 manifest 并复核 hash |
| TASK-009 analysis | PR #9 + #13 | **结果合同、双焦轴、failure/rerun 编排完成** | 补 Huygens PSF/Zernike/footprint 的具体 ZOS setting；先跑 3 个代表配置；通过 sampling/MTF cross-check |
| TASK-010 GUI | PR #10 | **薄 GUI/串行动作调度完成**；无 raw ZOSAPI import | 根据 TDD-401 决定 thread-owned session 或主线程编排；本地 GUI smoke |
| TASK-011 nominal acceptance | PR #11 | **验收判定器完成**：72/36/1080 + repeatability | 只有 TASK-009 代表配置通过后才运行真实 Run72 和 repeatability |

## 额外离线加固

- PR #12：锁文件篡改、settings serialization hash、商业产品命名、CSV schema/version、rerun ID 回归测试。
- PR #13：正式 carrier lock 门控、18/72 CSV 导出、单配置失败隔离、失败项定向 rerun。
- PR #14：ZOS-API 顺序模式薄原语；把 surface editing 与 analysis lifecycle 收缩到少量 late-bound 调用，便于本地 API 差异调试。

## 仍然有效的 STOP 条件

以下条件没有因为代码已写完而解除：

1. `TDD-TEST-401` 未在真实 OpticStudio 运行前，不锁定 GUI 的 ZOS session 线程归属。
2. `TDD-TEST-999` 未解除前，不允许生成正式 EDOF carrier/pair locks，也不允许真实 Run72。
3. 3 个代表配置未通过 sampling convergence 与独立 MTF cross-check 前，不允许 Run72。
4. A0/B0/C0、STD eye、residual 或 carrier 一旦正式 lock，任何下游流程不得改其 hash。
5. 当前合成测试数据只用于验证代码合同，不能进入正式 `project/locks`、`project/manifests` 或论文结果。

## Git 执行记录

本轮实现均通过独立分支 → PR → squash merge 进入 `main`：

- PR #2 `feat: implement RMD-TASK-002 ZOS session boundary`
- PR #3 `feat: implement RMD-TASK-003 project store`
- PR #4 `feat: implement RMD-TASK-004 optical metrics`
- PR #5 `feat: implement RMD-TASK-005 scientific asset contracts`
- PR #6 `feat: implement RMD-TASK-006 B0 workflow`
- PR #7 `feat: implement RMD-TASK-007 carrier science gate`
- PR #8 `feat: implement RMD-TASK-008 manifest builder`
- PR #9 `feat: implement RMD-TASK-009 analysis contracts`
- PR #10 `feat: implement RMD-TASK-010 desktop shell`
- PR #11 `test: implement RMD-TASK-011 nominal acceptance gates`
- PR #12 `test: harden offline RMD regressions`
- PR #13 `feat: complete offline RMD workflow orchestration`
- PR #14 `feat: add ZOS-API sequential primitives`

本文件的状态含义是：**RMD 的离线实现阶段已经走完；下一阶段是目标 Windows + OpticStudio 环境中的 API 适配、科学建模与验收。**
