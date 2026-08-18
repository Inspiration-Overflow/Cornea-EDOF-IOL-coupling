# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件记录截至 2026-08-18 的真实代码状态，不修改科学规范。

## 当前结论

当前仓库已经在本机 **OpticStudio 2026 R1.00 + Premium license** 下完成第一批 ZOS-API 适配：主线程与 worker thread 会话、三种顺序面型的实际参数列、Huygens PSF 网格读取、Zernike Standard 系数读取均已通过真实运行。正式眼模型、A0/B0/C0、carrier/residual、三代表配置和 Run72 仍未执行；没有用安装示例或合成数据生成正式科学 lock。

随后根据独立 code review 已在 `fix/zosapi-pre-science-hardening` 分支完成第二轮 pre-science hardening：Binary 4 不再写入 OpticStudio 计算型 `Par4`；Huygens PSF 增加 shape/spacing/center/intensity 契约；Huygens/Zernike 采集参数进入 frozen settings hash；Python.NET/ZOS DLL bootstrap 改为进程级幂等；项目新建光学系统时显式 `MakeSequential()`。详细见 `docs/audit/zosapi_pre_science_hardening_2026-08-18.md`。

以下验证结果属于 **pre-science hardening 之前的父集成分支**：

```text
pytest tests/unit                         -> 83 passed
pytest tests/zemax                        -> 5 passed
ruff check .                              -> PASS
python -m compileall -q src tests scripts -> PASS
uv lock --check                           -> PASS
```

这些数字不能自动继承为当前 hardening 分支的验证结论。hardening 分支必须在同一台 OpticStudio 工作站重新运行：

```powershell
uv run pytest tests/unit
uv run pytest tests/zemax
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

当前真实 Zemax 组还新增了同一 Python 进程连续 10 次 open→New→close 的 session stress gate；Huygens/Zernike 实机 smoke 也改为直接从 `NOMINAL_MAIN_555_v1` 派生采集参数。因此 hardening 后 Zemax 通过数应大于父分支的 5 个测试，具体数值以本机复跑为准。

当前执行注意事项：

- `uv.lock` 已生成；父集成分支已通过 `uv lock --check`。
- 2026 R1.00 把 `ZOSAPI_NetHelper.dll`、`ZOSAPI.dll`、`ZOSAPI_Interfaces.dll` 放在安装根目录；session 同时保留旧版 `ZOS-API/Libraries` 布局支持。
- hardening 后 CLR/ZOS assembly load 在同一 Python process 内只允许初始化一次；后续 session 必须复用同一 OpticStudio install identity。若需要切换安装目录，必须启动新的 Python process。
- 本机仍应使用 `pytest tests/zemax` 直接收集 Zemax 测试。父集成分支曾观察到：收集完整测试树后再用 `-m zemax` 筛选，会在第一次创建 ZOS application 时以 Windows 原生状态 `0xc0000139` 退出；该问题尚未宣称解决。
- 父集成分支个别成功会话曾在 stderr 出现 `FRU__delta_init(): Attempt to start when running!`。新增 10 次 session stress gate 用于观察 hardening 是否改善重复初始化风险，但在本机复跑前不得宣称已解决。
- GUI display smoke、Huygens MTF 交叉验证、footprint 与 Prescription Data 接口仍待完成。

## RMD task 状态

| RMD task | Git | 当前状态 | 本地 OpticStudio 阶段仍需完成 |
| --- | --- | --- | --- |
| TASK-001 Project Setup | scaffold commit `b53dd798` | **父分支本机完成**：`uv.lock` 已生成；83 个 unit、Ruff、compileall 通过 | hardening 分支重新执行 locked-env unit/Ruff/compileall |
| TASK-002 ZOS session | PR #2 + 本次适配 + pre-science hardening | **父分支本机通过**：2026 R1.00 新旧 DLL 布局、Premium license、主线程和 worker-thread session；hardening 已加入 process-idempotent bootstrap 和 10 次 stress gate | 重新跑 `tests/zemax`，继续观察原生 stderr/`0xc0000139` |
| TASK-003 Domain + ProjectStore | PR #3 | **离线完成并加固**：完整 baseline hash、create-once RunEnvironment、schema v2、artifact/run provenance；analysis acquisition settings 现已进入 settings hash | 与真实 `.zos` artifact 一起做一次集成回放 |
| TASK-004 metric engine | PR #4 | **离线完成**：complex OTF、MTF、MTFa、VSOTF、DOF、frequency、delta | 用真实 Huygens PSF/MTF 做 TDD-209/403 交叉验证 |
| TASK-005 scientific assets | PR #5 + 本次适配 | **API 映射完成**：Binary 4、Even Asphere、Coordinate Break 父分支实机写入回读通过；hardening 已禁止写 Binary4 `Par4`，新系统显式 Sequential | 重新跑 surface mapping；建立并验证正式 `.zos` assets、Coordinate Return、ZERO_HOA、REF_MONO |
| TASK-006 B0 | PR #6 | **算法完成并加固**：严格 17-plane grid、achieved ΔC4、80/70% gate、DOF rank、morphology/override、settings-bound scan hash | 运行真实五点 B scan；人工 morphology decision；写唯一 B0 lock |
| TASK-007 carrier science gate | PR #7 + #13 | **fail-closed 门控完成**：finite carrier、evidence-backed residual、actual-carrier low/median/high、policy hash | 实际求 18 个 P/Q；STD-eye achieved-SA 回放；提供 3 个 residual payload；确定并冻结 residual 数值 tolerance policy；真实 low/median/high 校准；解除 TDD-999 |
| TASK-008 carrier/pair locks + manifest | PR #8 + #13 | **生成器/CSV/provenance 加固完成**；不会在 gate 前产出正式清单 | TASK-007 通过后生成正式 18 lock、36 pair、72 manifest 并复核 hash |
| TASK-009 analysis | PR #9 + #13 + 本次适配 + pre-science hardening | **父分支 API smoke 通过**：Huygens PSF 网格与 Zernike Standard 严格读取；hardening 已将生产采集参数绑定 frozen settings，并增加 Huygens grid geometry fail-closed 检查 | 重新跑 nominal Huygens/Zernike smoke；footprint/Prescription/Huygens MTF；先跑 3 个代表配置；通过 sampling/MTF cross-check |
| TASK-010 GUI | PR #10 | **父分支线程假设已验证**：worker-owned ZOS session 可连接、建临时系统并关闭；无 raw ZOSAPI import | hardening 后重新跑 worker/stress gate，再做本地 GUI display/full-flow smoke；当前没有 `gui` marker 实测用例 |
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

1. `TDD-TEST-401` 在父集成分支已通过；hardening 分支修改了 session bootstrap，因此在继续依赖 worker-owned ZOS session 前必须重新跑 `tests/zemax`。
2. `TDD-TEST-999` 未解除前，不允许生成真实正式 EDOF carrier/pair locks，也不允许真实 Run72。
3. 3 个代表配置未通过 sampling convergence 与独立 MTF cross-check 前，不允许 Run72。
4. A0/B0/C0、STD eye、residual 或 carrier 一旦正式 lock，任何下游流程不得改其 hash。
5. 当前合成测试数据只用于验证代码合同，不能进入正式 `project/locks`、`project/manifests` 或论文结果。

## Git 执行记录

RMD 主实现均通过独立分支 → PR → squash merge 进入 `main`：PR #2–#15；第一轮 code-review hardening 已按独立分支和 PR 合并。第一批真实 ZOS-API 适配位于 `codex/zosapi-2026-r1-integration`，第二轮修订位于其子分支 `fix/zosapi-pre-science-hardening`。

本文件的状态含义是：**离线实现、第一轮 code review 和第一批真实 ZOS-API 适配已完成；第二轮 pre-science hardening 代码已完成但必须先在 OpticStudio 工作站重新验证，之后才进入正式科学资产建模。**
