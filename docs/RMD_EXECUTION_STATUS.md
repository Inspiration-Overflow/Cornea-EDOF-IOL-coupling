# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件记录截至 2026-08-18 的真实代码状态，不修改科学规范。

## 当前结论

当前仓库已经在本机 **OpticStudio 2026 R1.00 + Premium license** 下完成第一批 ZOS-API 适配：主线程与 worker thread 会话、三种顺序面型的实际参数列、Huygens PSF 网格读取、Zernike Standard 系数读取均已通过真实运行。正式眼模型、A0/B0/C0、carrier/residual、三代表配置和 Run72 仍未执行；没有用安装示例或合成数据生成正式科学 lock。

随后根据独立 code review 在 `fix/zosapi-pre-science-hardening` 分支完成第二轮 pre-science hardening：Binary 4 不再写入 OpticStudio 计算型 `Par4`；Huygens PSF 增加 shape/spacing/center/intensity 契约；Huygens/Zernike 采集参数进入 frozen settings hash；Python.NET/ZOS DLL bootstrap 改为进程级幂等；项目新建光学系统时显式 `MakeSequential()`。本分支已在同一台工作站完成复测。详细见 `docs/audit/zosapi_pre_science_hardening_2026-08-18.md`。

2026-08-18 当前 hardening 分支验证：

```text
pytest tests/unit                         -> 94 passed
pytest tests/zemax                        -> 6 passed in 175.14 s
pytest test_zos_worker_gate.py (worker)   -> 1 passed, 2 deselected
ruff check .                              -> PASS
python -m compileall -q src tests scripts -> PASS
uv lock --check                           -> PASS
```

worker-first 使用全新的 Python 进程，并以完整测试函数名选择用例：

```powershell
uv run pytest tests/zemax/test_zos_worker_gate.py -k worker_thread_session_risk_gate -vv
```

`-k worker` 会匹配测试文件名并选中该文件内全部三个测试，因此不能作为 worker-first 的精确命令。当前 6 个 Zemax 测试包含同一 Python 进程连续 10 次 open→New→close 的 session stress gate；Huygens/Zernike 实机 smoke 直接从 `NOMINAL_MAIN_555_v1` 派生采集参数。

当前执行注意事项：

- `uv.lock` 已生成；当前 hardening 分支已通过 `uv lock --check`。
- 2026 R1.00 把 `ZOSAPI_NetHelper.dll`、`ZOSAPI.dll`、`ZOSAPI_Interfaces.dll` 放在安装根目录；session 同时保留旧版 `ZOS-API/Libraries` 布局支持。
- hardening 后 CLR/ZOS assembly load 在同一 Python process 内只允许初始化一次；后续 session 必须复用同一 OpticStudio install identity。若需要切换安装目录，必须启动新的 Python process。
- 本机仍应使用 `pytest tests/zemax` 直接收集 Zemax 测试。父集成分支曾观察到：收集完整测试树后再用 `-m zemax` 筛选，会在第一次创建 ZOS application 时以 Windows 原生状态 `0xc0000139` 退出；该问题尚未宣称解决。
- 父集成分支个别成功会话曾在 stderr 出现 `FRU__delta_init(): Attempt to start when running!`。当前 10 次 session stress gate 通过，捕获的测试输出未再次出现该警告；这只说明本次复跑未复现，不表示已证明原生运行时不存在该问题。
- GUI display smoke、Huygens MTF 交叉验证、footprint 与 Prescription Data 接口仍待完成。

## RMD task 状态

| RMD task | Git | 当前状态 | 本地 OpticStudio 阶段仍需完成 |
| --- | --- | --- | --- |
| TASK-001 Project Setup | scaffold commit `b53dd798` | **hardening 分支本机完成**：`uv.lock` 已生成；94 个 unit、Ruff、compileall 通过 | 合并后保持 locked-env 检查 |
| TASK-002 ZOS session | PR #2 + 本次适配 + pre-science hardening | **hardening 分支本机通过**：2026 R1.00、Premium license、process-idempotent bootstrap、10 次 stress 和独立 worker-first session 均通过 | 长批次继续观察原生 stderr/`0xc0000139` |
| TASK-003 Domain + ProjectStore | PR #3 | **离线完成并加固**：完整 baseline hash、create-once RunEnvironment、schema v2、artifact/run provenance；analysis acquisition settings 现已进入 settings hash | 与真实 `.zos` artifact 一起做一次集成回放 |
| TASK-004 metric engine | PR #4 | **离线完成**：complex OTF、MTF、MTFa、VSOTF、DOF、frequency、delta | 用真实 Huygens PSF/MTF 做 TDD-209/403 交叉验证 |
| TASK-005 scientific assets | PR #5 + 本次适配 | **hardening 分支 API smoke 通过**：Binary 4、Even Asphere、Coordinate Break 实机写入回读通过；Binary4 `Par4` 保持未写入，新系统显式 Sequential | 建立并验证正式 `.zos` assets、Coordinate Return、ZERO_HOA、REF_MONO |
| TASK-006 B0 | PR #6 | **算法完成并加固**：严格 17-plane grid、achieved ΔC4、80/70% gate、DOF rank、morphology/override、settings-bound scan hash | 运行真实五点 B scan；人工 morphology decision；写唯一 B0 lock |
| TASK-007 carrier science gate | PR #7 + #13 | **fail-closed 门控完成**：finite carrier、evidence-backed residual、actual-carrier low/median/high、policy hash | 实际求 18 个 P/Q；STD-eye achieved-SA 回放；提供 3 个 residual payload；确定并冻结 residual 数值 tolerance policy；真实 low/median/high 校准；解除 TDD-999 |
| TASK-008 carrier/pair locks + manifest | PR #8 + #13 | **生成器/CSV/provenance 加固完成**；不会在 gate 前产出正式清单 | TASK-007 通过后生成正式 18 lock、36 pair、72 manifest 并复核 hash |
| TASK-009 analysis | PR #9 + #13 + 本次适配 + pre-science hardening | **hardening 分支 API smoke 通过**：frozen nominal 256×256 Huygens PSF 与 32×32/37 项 Zernike Standard 均通过 | footprint/Prescription/Huygens MTF；先跑 3 个代表配置；通过 sampling/MTF cross-check |
| TASK-010 GUI | PR #10 | **hardening 后线程假设已复核**：独立 worker-first session 和 10 次 stress 均通过；无 raw ZOSAPI import | 本地 GUI display/full-flow smoke；当前没有 `gui` marker 实测用例 |
| TASK-011 nominal acceptance | PR #11 | **manifest-bound 验收判定器完成**：72/36/1080 + repeatability | 只有 TASK-009 代表配置通过后才运行真实 Run72 和 repeatability |

## 独立 code review 后的加固

第一轮详细记录见：`docs/audit/code_review_hardening_2026-08-17.md`。第二轮 ZOS-API pre-science hardening 见：`docs/audit/zosapi_pre_science_hardening_2026-08-18.md`。

第一轮没有改变 URD/MDD/TDD 的科学阈值，而是将已有契约落实为 fail-closed 代码：

- NaN/Inf carrier 不再穿透科学容差；
- residual 不能仅凭 metadata flag 和三个 `passed=True` 标签形成 formal lock；
- B0 complete 必须满足冻结 17-plane scan、唯一候选和 achieved ΔC4 oracle；
- analysis result 必须与请求 config/run 一致，并重算 distance peak / shape axis；
- formal RunEnvironment 必须与真实 baseline/settings/manifest/lock-set 一致；
- final acceptance 必须对应真实 manifest ID 集合，而不只是计数达到 72/36/1080；
- ZOS analysis result 在 Close 前转换为纯 Python 数据；
- Tk UI 更新只在主线程执行。

第二轮继续保持同一原则：

- Binary 4 `Par4` 只作为 OpticStudio 诊断输出，不由项目写入；
- Huygens PSF 的 shape、sampling、几何中心和 intensity 语义进入 parser contract；
- Huygens/Zernike 关键采集选项进入 `AnalysisSettings`，改变即改变 settings hash；
- `AnalysisSettings` 的关键数值拒绝 NaN/Inf；
- Python.NET/ZOS assembly bootstrap 在进程内幂等且拒绝跨安装目录复用；
- 项目新建 optical system 后显式 `MakeSequential()`，不把 application server mode 误当作 optical system mode。

## 额外离线加固 Git 记录

- PR #12：锁文件篡改、settings serialization hash、商业产品命名、CSV schema/version、rerun ID 回归测试。
- PR #13：正式 carrier lock 门控、18/72 CSV 导出、单配置失败隔离、失败项定向 rerun。
- PR #14：ZOS-API 顺序模式薄原语；把 surface editing 与 analysis lifecycle 收缩到少量 late-bound 调用。
- PR #15：记录 RMD 执行状态和本地 OpticStudio 验证顺序。
- 第一轮 code-review hardening：修复 fail-open 科学门槛、身份/provenance 与 GUI/ZOS lifecycle 问题。
- 第二轮 pre-science hardening：修复 Binary4 诊断列语义、Huygens grid 契约、acquisition provenance 与 Python.NET 进程生命周期问题。

## 仍然有效的 STOP 条件

以下条件没有因为代码已写完或 code review 已修复而解除：

1. `TDD-TEST-401` 已在 hardening 分支通过完整 Zemax 组和独立 worker-first 进程复核；后续长流程仍需保留失败记录和原生 stderr。
2. `TDD-TEST-999` 未解除前，不允许生成真实正式 EDOF carrier/pair locks，也不允许真实 Run72。
3. 3 个代表配置未通过 sampling convergence 与独立 MTF cross-check 前，不允许 Run72。
4. A0/B0/C0、STD eye、residual 或 carrier 一旦正式 lock，任何下游流程不得改其 hash。
5. 当前合成测试数据只用于验证代码合同，不能进入正式 `project/locks`、`project/manifests` 或论文结果。

## Git 执行记录

RMD 主实现均通过独立分支 → PR → squash merge 进入 `main`：PR #2–#15；第一轮 code-review hardening 已按独立分支和 PR 合并。第一批真实 ZOS-API 适配位于 `codex/zosapi-2026-r1-integration`，第二轮修订位于其子分支 `fix/zosapi-pre-science-hardening`。

本文件的状态含义是：**离线实现、第一轮 code review、第一批真实 ZOS-API 适配和第二轮 pre-science hardening 实机复测均已完成；下一阶段仍受 TDD-999 和三代表配置条件约束。**
