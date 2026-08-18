# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件记录截至 2026-08-17 的真实代码状态，不修改科学规范。

## 当前结论

当前仓库已经在本机 **OpticStudio 2026 R1.00 + Premium license** 下完成第一批 ZOS-API 适配：主线程与 worker thread 会话、三种顺序面型的实际参数列、Huygens PSF 网格读取、Zernike Standard 系数读取均已通过真实运行。正式眼模型、A0/B0/C0、carrier/residual、三代表配置和 Run72 仍未执行；没有用安装示例或合成数据生成正式科学 lock。

2026-08-17 当前验证：

```text
pytest tests/unit                         -> 83 passed
pytest tests/zemax                        -> 5 passed
ruff check .                              -> PASS
python -m compileall -q src tests scripts -> PASS
```

真实 Zemax 组包含主线程 session、GUI-like worker session、Binary 4/Even Asphere/Coordinate Break 写入回读、32×32 Huygens PSF 和 37 项 Zernike Standard。曲面测试创建临时系统但不保存文件；analysis 测试读取 OpticStudio 自带衍射极限示例。

当前执行注意事项：

- `uv.lock` 已生成，当前 `.venv` 可运行全部上述检查。
- 2026 R1.00 把 `ZOSAPI_NetHelper.dll`、`ZOSAPI.dll`、`ZOSAPI_Interfaces.dll` 放在安装根目录；session 同时保留旧版 `ZOS-API/Libraries` 布局支持。
- 本机必须用 `pytest tests/zemax` 直接收集 Zemax 测试。收集完整测试树后再用 `-m zemax` 筛选，会在第一次创建 ZOS application 时以 Windows 原生状态 `0xc0000139` 退出；独立目录连续复跑通过。
- 个别成功会话曾在 stderr 出现 `FRU__delta_init(): Attempt to start when running!`，没有导致测试失败。后续长批次运行仍需观察。
- GUI display smoke、Huygens MTF 交叉验证、footprint 与 Prescription Data 接口仍待完成。

## RMD task 状态

| RMD task | Git | 当前状态 | 本地 OpticStudio 阶段仍需完成 |
| --- | --- | --- | --- |
| TASK-001 Project Setup | scaffold commit `b53dd798` | **本机完成**：`uv.lock` 已生成；83 个 unit、Ruff、compileall 通过 | 合并前用 locked 环境复核 |
| TASK-002 ZOS session | PR #2 + 本次适配 | **本机通过**：2026 R1.00 新旧 DLL 布局、Premium license、主线程和 worker-thread session | 长批次继续观察原生 stderr；保持 Zemax 测试目录隔离 |
| TASK-003 Domain + ProjectStore | PR #3 | **离线完成并加固**：完整 baseline hash、create-once RunEnvironment、schema v2、artifact/run provenance | 与真实 `.zos` artifact 一起做一次集成回放 |
| TASK-004 metric engine | PR #4 | **离线完成**：complex OTF、MTF、MTFa、VSOTF、DOF、frequency、delta | 用真实 Huygens PSF/MTF 做 TDD-209/403 交叉验证 |
| TASK-005 scientific assets | PR #5 + 本次适配 | **API 映射完成**：Binary 4、Even Asphere、Coordinate Break 实机写入回读通过 | 建立并验证正式 `.zos` assets、Coordinate Return、ZERO_HOA、REF_MONO |
| TASK-006 B0 | PR #6 | **算法完成并加固**：严格 17-plane grid、achieved ΔC4、80/70% gate、DOF rank、morphology/override、settings-bound scan hash | 运行真实五点 B scan；人工 morphology decision；写唯一 B0 lock |
| TASK-007 carrier science gate | PR #7 + #13 | **fail-closed 门控完成**：finite carrier、evidence-backed residual、actual-carrier low/median/high、policy hash | 实际求 18 个 P/Q；STD-eye achieved-SA 回放；提供 3 个 residual payload；确定并冻结 residual 数值 tolerance policy；真实 low/median/high 校准；解除 TDD-999 |
| TASK-008 carrier/pair locks + manifest | PR #8 + #13 | **生成器/CSV/provenance 加固完成**；不会在 gate 前产出正式清单 | TASK-007 通过后生成正式 18 lock、36 pair、72 manifest 并复核 hash |
| TASK-009 analysis | PR #9 + #13 + 本次适配 | **API smoke 通过**：Huygens PSF 网格与 Zernike Standard 严格读取已实机验证 | footprint/Prescription/Huygens MTF；先跑 3 个代表配置；通过 sampling/MTF cross-check |
| TASK-010 GUI | PR #10 | **线程假设已验证**：worker-owned ZOS session 可连接、建临时系统并关闭；无 raw ZOSAPI import | 接入具体 workflow 后做本地 GUI display/full-flow smoke；当前没有 `gui` marker 实测用例 |
| TASK-011 nominal acceptance | PR #11 | **manifest-bound 验收判定器完成**：72/36/1080 + repeatability | 只有 TASK-009 代表配置通过后才运行真实 Run72 和 repeatability |

## 独立 code review 后的加固

详细记录见：`docs/audit/code_review_hardening_2026-08-17.md`。

本轮没有改变 URD/MDD/TDD 的科学阈值，而是将已有契约落实为 fail-closed 代码：

- NaN/Inf carrier 不再穿透科学容差；
- residual 不能仅凭 metadata flag 和三个 `passed=True` 标签形成 formal lock；
- B0 complete 必须满足冻结 17-plane scan、唯一候选和 achieved ΔC4 oracle；
- analysis result 必须与请求 config/run 一致，并重算 distance peak / shape axis；
- formal RunEnvironment 必须与真实 baseline/settings/manifest/lock-set 一致；
- final acceptance 必须对应真实 manifest ID 集合，而不只是计数达到 72/36/1080；
- ZOS analysis result 在 Close 前转换为纯 Python 数据；
- Tk UI 更新只在主线程执行。

## 额外离线加固 Git 记录

- PR #12：锁文件篡改、settings serialization hash、商业产品命名、CSV schema/version、rerun ID 回归测试。
- PR #13：正式 carrier lock 门控、18/72 CSV 导出、单配置失败隔离、失败项定向 rerun。
- PR #14：ZOS-API 顺序模式薄原语；把 surface editing 与 analysis lifecycle 收缩到少量 late-bound 调用。
- PR #15：记录 RMD 执行状态和本地 OpticStudio 验证顺序。
- 本次 code-review hardening：修复 fail-open 科学门槛、身份/provenance 与 GUI/ZOS lifecycle 问题；以本次 PR/merge 记录为准。

## 仍然有效的 STOP 条件

以下条件没有因为代码已写完或 code review 已修复而解除：

1. `TDD-TEST-401` 已在真实 OpticStudio 通过，当前允许 worker-owned ZOS session；若后续 GUI 长流程出现原生失败，必须重新评估线程归属。
2. `TDD-TEST-999` 未解除前，不允许生成真实正式 EDOF carrier/pair locks，也不允许真实 Run72。
3. 3 个代表配置未通过 sampling convergence 与独立 MTF cross-check 前，不允许 Run72。
4. A0/B0/C0、STD eye、residual 或 carrier 一旦正式 lock，任何下游流程不得改其 hash。
5. 当前合成测试数据只用于验证代码合同，不能进入正式 `project/locks`、`project/manifests` 或论文结果。

## Git 执行记录

RMD 主实现均通过独立分支 → PR → squash merge 进入 `main`：PR #2–#15；本次 code-review hardening 同样按独立分支和 PR 提交。

本文件的状态含义是：**离线实现、第一轮 code review 和第一批真实 ZOS-API 适配已完成；下一阶段是正式科学资产建模、三代表配置验证和 GUI smoke。**
