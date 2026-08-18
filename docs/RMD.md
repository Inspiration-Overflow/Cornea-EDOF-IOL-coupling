# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **Build Path / Route-Runbook-Execution Map。** 本文件只规定安全实现顺序、测试闸门、回滚和 Git checkpoint；不重新定义科学模型。来源：`URD-0001 v1.3`、`ADD-0001 v1.4`、`MDD-0001 v1.3`、`TDD-0001 v1.2`。

## Metadata

- document_id: RMD-0001
- version: 1.2
- status: active
- last_updated: 2026-08-18
- document_strength: standard
- implementation_language: Python
- package_manager: uv
- default_branch: main
- merge_style: squash
- remote_status: connected
- implementation_status: TASK-001–004 complete; TASK-005 formal scientific assets pending

## Development Conventions

- **Python 包与虚拟环境统一由 `uv` 管理。**
  - 初始化：`uv init --app .`
  - 添加运行依赖：`uv add <package>`
  - 添加开发依赖：`uv add --dev <package>`
  - 同步环境：`uv sync`
  - 运行 Python/工具命令：优先使用 `uv run ...`
  - 不直接使用 `pip install` 作为项目依赖管理方式；确有临时诊断需要时，不得把结果当作正式项目状态。
- **单元测试统一使用 `pytest`。**
  - 所有自动化测试放入 `tests/`。
  - 运行离线测试：`uv run pytest tests/unit`
  - 在配置好的工作站运行真实 ZOS-API 测试：`uv run pytest tests/zemax`
  - 单元测试使用 `pytest` marker/命名组织；Zemax integration 与 GUI smoke 仍由 pytest 统一调度。
  - 不引入第二套单元测试框架。

## Default Dual-Environment Workflow

本项目默认采用已经实测可行的 **ChatGPT Web ↔ Codex 本地 Windows/OpticStudio** 双环境闭环，不为两端另设重复实现流程。

### ChatGPT Web：主研究与主开发环境

ChatGPT Web 默认负责：

- 权威文献、标准、专利、厂商资料和既有项目文档的研究、比较与溯源；
- URD/ADD/MDD/TDD/RMD、模型设计文档、审计记录和科学决策的整理与修订；
- Python 主代码、测试、schema、provenance、fail-closed gate 和 Git 变更的设计、实现与独立审核；
- 不依赖本地 OpticStudio 的单元测试逻辑、算法验证和代码审查；
- 根据 Codex 本地返回的真实运行证据继续修订代码、文档或测试契约。

### Codex 本地：OpticStudio 实机执行与适配环境

Codex 在配置好的 Windows + OpticStudio 工作站默认负责：

- 从远端取得指定分支/提交并保持工作区可追溯；
- 执行真实 ZOS-API、Zemax integration、GUI/full-flow smoke 和需要 OpticStudio license 的测试；
- 生成并检查真实 `.zos`/`.zmx` 科学资产、Prescription Data、footprint、PSF/MTF/Zernike 等实机结果；
- 观察 Python.NET、CLR、OpticStudio native runtime、stderr、线程/进程生命周期等 Web 端无法验证的问题；
- 对明确由实机 API 差异或本地运行问题造成的错误做**最小必要修订**，并运行相应回归测试；
- 将真实测试结果、失败日志、必要代码修订和新生成的科学证据同步回远端，供 ChatGPT Web 继续研究、审核和主线整合。

### Handoff / Evidence Rule

1. **Web 端先定义问题和验收条件。** 科学模型、参数来源、测试 oracle、锁边界和计划先在 Web 端明确；不得把未定义的科学问题直接交给本地“试出来”。
2. **本地只验证需要真实 OpticStudio 的部分。** 能由 unit test、纯 Python 或静态审查完成的工作不要求 Codex 重复执行。
3. **本地允许最小适配，不允许静默改变科学定义。** 若实机运行要求改变冻结参数、科学阈值、模型含义或 lock boundary，立即按 STOP 条件返回 Web 端处理。
4. **真实结果优先于假设。** 本地 OpticStudio 返回的 API 行为、数据结构和数值结果是实机接口与科学资产验证的证据；Web 端据此更新实现，但不得把一次 smoke 结果扩张为未经验证的科学结论。
5. **所有正式科学资产必须可追溯。** `.zos/.zmx`、lock、manifest、residual、代表配置和 Run72 结果必须能追溯到代码 commit、settings/hash、OpticStudio 环境与本地验证记录。
6. **回传后再进入下一科学阶段。** 本地结果通过后，由 Web 端完成独立审核、文档/状态同步和必要 Git 整合，再进入下一个 RMD task。

该双环境工作流是执行方式，不改变 `RMD-TASK-001`–`011` 的科学依赖顺序和 STOP 条件。

## Build Path Checkpoint Summary

进入实现后的**前三步**固定为：

| Order | Task | Purpose | Test command | Rollback | Git branch |
| --- | --- | --- | --- | --- | --- |
| 1 | RMD-TASK-001 Project Setup + test skeleton | 建干净 uv/src/tests/git 基础，不写科学 feature | `uv run pytest --collect-only && uv run ruff check .` | RMD-RB-001 | `chore/rmd-task-001-setup` |
| 2 | RMD-TASK-002 ZOS session + environment risk gate | 尽早验证真实 ZOS-API lifecycle 与 worker-thread assumption | `uv run pytest tests/zemax -m zemax -k "session or worker_thread"` | RMD-RB-002 | `feat/rmd-task-002-zos-session` |
| 3 | RMD-TASK-003 Domain + ProjectStore | 冻结 ID/schema/hash/run-state 基础，避免后续科学代码各自写文件 | `uv run pytest -m unit -k "store or schema or settings or environment or path"` | RMD-RB-003 | `feat/rmd-task-003-project-store` |

**Checkpoint rule：** Build Path 已被用户接受并进入执行；后续仍按 task、STOP 条件与 Git checkpoint 推进。

## Project Setup

| ID | Item | Decision / Command | Done When |
| --- | --- | --- | --- |
| RMD-SETUP-001 | project root | 在 TASK-001 选择/创建一个本地项目根目录；如果目录已有代码，先 `git status`/inspect，不覆盖 | root 明确且无未解释的既有文件冲突 |
| RMD-SETUP-002 | Python package management | **只用 `uv` 管理正式 Python 依赖/环境**：`uv init --app .`、`uv add ...`、`uv sync` | `pyproject.toml` + `uv.lock` 存在且 `uv sync` 成功 |
| RMD-SETUP-003 | runtime deps | `uv add pythonnet customtkinter numpy matplotlib` | dependencies 只来自 MDD 需要 |
| RMD-SETUP-004 | tests/dev deps | **单元测试统一使用 `pytest`**：`uv add --dev pytest ruff` | `uv run pytest --collect-only` 可运行；测试入口统一为 pytest |
| RMD-SETUP-005 | folders | `src/whole_eye_mvp/`, `tests/`, `tests/fixtures/` | package/test import 正常 |
| RMD-SETUP-006 | fixture | 复制 `COMPLEX_OTF_GOLDEN_3x3_v1.json` 到测试 fixture | fixture hash 固定 |
| RMD-SETUP-007 | ignore | `.gitignore`: `.venv/`, caches, `.env`, generated project results/`.zos` unless explicit test fixture | 首次 commit 前完成 |
| RMD-SETUP-008 | git | verify/init repo；检查 remote；不自动 push | clean starting state；remote 状态记录 |

## Execution Strategy

- **strategy:** test-first, risk-first, dependency-ordered。
- **execution ownership:** ChatGPT Web 负责研究、规范、主要代码实现与审核；Codex 本地负责真实 OpticStudio/ZOS-API 执行、证据采集和最小必要适配。
- **scope:** 只实现当前 MVP；不实现患者 Grid Sag、多色、倾斜/偏心、并行运行、数据库、Web、Cancel/Pause。
- **test-first rule:** 每个 task 先加入/启用其 TDD tests，使其失败；再写最小实现直到通过。
- **Zemax rule:** unit tests 不依赖 OpticStudio；`zemax` marker 只在配置好的 Windows workstation 上运行。
- **science lock rule:** 下游只读上游 locks；任何需要“修正上游 lock 才让测试通过”的情况立即 STOP。
- **carrier rule:** RMD-TASK-007 可以生成**provisional** carrier power/Q records，但 `TDD-TEST-999` 未解除前不得写正式 EDOF carrier/pair locks。
- **result rule:** 先通过 3 个代表配置 integration，再运行 72；禁止一上来跑完整矩阵来调试。

## Ordered Tasks

| ID | Task | Depends On | Primary IDs | Outputs | Test / Check | Branch | Done When |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RMD-TASK-001 | Project Setup + test skeleton | — | TDD structure | `pyproject.toml`, `.gitignore`, src/tests skeleton, copied fixture | `uv run pytest --collect-only`; `uv run ruff check .` | `chore/rmd-task-001-setup` | clean setup commit；无 feature code |
| RMD-TASK-002 | `ZosSessionAdapter` + worker risk gate | 001 | MDD-MOD-001/API-001; TEST-001/101/401 | session adapter + typed errors + integration smoke | `uv run pytest tests/zemax -m zemax -k "session or worker_thread"` | `feat/rmd-task-002-zos-session` | lifecycle tests pass；401 决定 orchestration placement |
| RMD-TASK-003 | Domain + `ProjectStore` | 001 | MOD-002; DATA-001/003/004/008/011/012/013; TEST-102/103/201/313-315 | frozen dataclasses/enums/settings serialization; filesystem store/run history | `uv run pytest -m unit -k "store or schema or settings or environment or path"` | `feat/rmd-task-003-project-store` | lock/hash/schema/run provenance tests pass |
| RMD-TASK-004 | Pure metric engine | 003 | MOD-007 math boundary; TEST-202-208/211/212 | PSF→complex OTF, radial MTF, MTFa, VSOTF, peak/DOF, dual-axis utilities | `uv run pytest -m unit -k "otf or mtf or vsotf or dof or defocus"` | `feat/rmd-task-004-metrics` | golden fixture、phase、FFT shift、DOF tests pass |
| RMD-TASK-005 | Core scientific assets + validation | 002,003 | MOD-003/API-004/005; TEST-002/003/005/104/105 | two bases, STD eye + ZERO_HOA reference, REF_MONO, A0, B candidates, C0 `.zos` + validation | `uv run pytest tests/zemax -m zemax -k "asset or base or standard_eye or cornea"` | `feat/rmd-task-005-assets` | core locks valid；A0/C0 convergence PASS；residual 可仍 not-ready |
| RMD-TASK-006 | B0 scan + recommendation + human lock | 004,005 | MOD-004/API-006/007; TEST-004/106/107/304 | A0 thresholds, 5-candidate Q_lock curves/gates/rank, B0 lock | `uv run pytest tests/zemax -m zemax -k "b0 or cornea_lock"` | `feat/rmd-task-006-b0` | deterministic recommendation 可重算；用户确认/override reason 后 B0 immutable |
| RMD-TASK-007 | Provisional carrier solve + residual science gate | 005,006 | MOD-005 internals; TEST-006/303/305/999 | provisional 18 `P,Q` records; residual payload validation; per-platform low/median/high calibration record | `uv run pytest tests/zemax -m zemax -k "carrier or residual or standard_eye"` | `feat/rmd-task-007-carrier-gate` | ZERO_HOA achieved-SA checks pass；**TEST-999 cleared**；仍不写正式 pair lock |
| RMD-TASK-008 | Formal carrier/pair locks + 18/72 manifests | 007 | API-008/009; TEST-007-009/108/109/301/306/307/502 | 18 carrier/pair locks + `physical_carriers.csv` + `nominal_72.csv` | `uv run pytest tests/unit -k "carrier_lock or pair or manifest"`<br>`uv run pytest tests/zemax -k "carrier_lock or pair or manifest"` | `feat/rmd-task-008-carriers-manifest` | 18/72 exact；matched invariants pass；manifest hash stable |
| RMD-TASK-009 | Analysis workflow on representative set | 004,008 | MOD-007/API-010; TEST-010/011/110/209/210/308-310/402/403/501 | 3 representative config results, PSF/MTF/VSOTF/Zernike/dual frames/artifacts | `uv run pytest tests/zemax -m zemax -k "analysis or sampling or zernike or huygens"` | `feat/rmd-task-009-analysis` | sampling/MTF cross-check pass；artifact completion rules pass |
| RMD-TASK-010 | Thin CustomTkinter shell | 002,003,005,006,008,009 | MOD-008/API-011/012; TEST-014/015/111/112/311/312 | minimal GUI actions/status/log/rerun/output-folder | `uv run pytest tests/unit -m gui`<br>`uv run pytest tests/unit -m unit -k "action or naming"` | `feat/rmd-task-010-gui` | GUI 不 import raw ZOSAPI；single-action/busy/naming smoke pass |
| RMD-TASK-011 | Nominal 72 acceptance run | 009,010 | TEST-012/013/016/404/504/505 | final nominal result set + paired deltas + acceptance log | `uv run pytest tests/unit`<br>`uv run pytest tests/zemax`<br>then controlled `Run 72` acceptance command/UI | `test/rmd-task-011-nominal-72` | 72 completed、36 pairs、1080 TF rows；repeatability/trace acceptance pass |

## Task Discipline

每个 RMD-TASK 按同一闭环执行：

1. **ChatGPT Web：** 从 clean `main` 明确 task scope、权威来源、验收条件和 STOP 条件，并创建/准备 task branch。
2. **ChatGPT Web：** 只启用/编写该 task 对应的 failing tests，完成不依赖 OpticStudio 的最小实现、文档和代码审查。
3. **Codex 本地：** 拉取指定 branch/commit；运行该 task 所需真实 OpticStudio/ZOS-API 测试和必要 smoke。
4. **Codex 本地：** 若仅有实机 API/运行时适配问题，可做最小修订并回归；若涉及科学定义、冻结参数、阈值或 lock boundary，停止并回传 Web 端。
5. **Codex 本地 → Web：** 回传测试命令、通过/失败数、关键 stderr/日志、真实结果摘要、修改 commit 和 generated artifact 状态。
6. **ChatGPT Web：** 独立审核回传证据；修订代码/文档/测试，并确认未把 smoke 结果误作正式科学结论。
7. 测试统一通过 `pytest` 执行；相关 task 通过后再跑 `uv run ruff check .`、`uv run python -m compileall -q src tests scripts` 和 `uv lock --check`（适用时）。
8. 更新受到影响的 `docs/TRACE.md`、`.vibe/trace.json`、`docs/RMD_EXECUTION_STATUS.md`、CHANGELOG；必要时更新短 OKF 页面。
9. `git diff` / `git status` 检查无 secrets、未计划 `.zos/.zmx` 运行产物和无关改动；正式科学资产仅按对应 task 的 artifact/lock contract 提交。
10. commit → PR → squash merge；不得跳过相应 STOP 条件。

## Git Checkpoints

| ID | Task | Branch | Planned Commit | PR | Merge |
| --- | --- | --- | --- | --- | --- |
| RMD-GIT-001 | TASK-001 | `chore/rmd-task-001-setup` | `chore: complete RMD-TASK-001 project setup` | completed | completed |
| RMD-GIT-002 | TASK-002 | `feat/rmd-task-002-zos-session` | `feat: implement RMD-TASK-002 ZOS session boundary` | completed | completed |
| RMD-GIT-003 | TASK-003 | `feat/rmd-task-003-project-store` | `feat: implement RMD-TASK-003 project store` | completed | completed |
| RMD-GIT-004 | TASK-004 | `feat/rmd-task-004-metrics` | `feat: implement RMD-TASK-004 optical metrics` | completed | completed |
| RMD-GIT-005 | TASK-005 | `feat/rmd-task-005-assets` | `feat: implement RMD-TASK-005 scientific assets` | pending formal science assets | pending |
| RMD-GIT-006 | TASK-006 | `feat/rmd-task-006-b0` | `feat: implement RMD-TASK-006 B0 workflow` | algorithm implemented; science execution pending | pending science lock |
| RMD-GIT-007 | TASK-007 | `feat/rmd-task-007-carrier-gate` | `feat: implement RMD-TASK-007 carrier science gate` | gate implemented; science execution pending | pending TDD-999 |
| RMD-GIT-008 | TASK-008 | `feat/rmd-task-008-carriers-manifest` | `feat: implement RMD-TASK-008 carrier locks and manifest` | generator implemented | pending upstream gate |
| RMD-GIT-009 | TASK-009 | `feat/rmd-task-009-analysis` | `feat: implement RMD-TASK-009 analysis workflow` | API implemented/hardened | pending representative run |
| RMD-GIT-010 | TASK-010 | `feat/rmd-task-010-gui` | `feat: implement RMD-TASK-010 desktop shell` | scaffold implemented | pending local GUI smoke |
| RMD-GIT-011 | TASK-011 | `test/rmd-task-011-nominal-72` | `test: complete RMD-TASK-011 nominal acceptance` | acceptance logic implemented | pending Run72 |

## 🛑 Stop Conditions

| ID | Condition | Required Action |
| --- | --- | --- |
| RMD-STOP-001 | TDD test 缺 oracle、或实现需要改变已冻结 analysis setting/科学阈值 | 停止实现，回到 TDD |
| RMD-STOP-002 | 实现需要修改 ADD lock boundary / 出现未记录 coupling | 停止，回到 ADD/MDD |
| RMD-STOP-003 | `TDD-TEST-401` worker-thread ZOS-API gate 失败/卡死 | 不继续 thread-owned session；只调整 MOD-008 orchestration placement，更新 MDD/TDD/RMD 后再实现 GUI |
| RMD-STOP-004 | `TDD-TEST-999` 未解除或任一 residual low/median/high calibration 失败 | 停在 TASK-007；禁止 TASK-008 正式 EDOF pair lock 和 Run72 |
| RMD-STOP-005 | 任何 downstream workflow 改变已冻结 A0/B0/C0/STD/residual/carrier hash | 停止；修复违反 lock contract 的代码 |
| RMD-STOP-006 | test/ruff 失败 | 不 commit/merge；修复或回到 MDD/TDD |
| RMD-STOP-007 | 未经授权删除、覆盖真实项目文件，或进行其他破坏性仓库操作 | 必须取得用户明确批准 |
| RMD-STOP-008 | git working tree 有无关改动、secret、`.env`、local DB/cache 或未计划 generated artifacts | 不提交；先隔离/ignore/询问 |
| RMD-STOP-009 | 3-config representative analysis 未通过 sampling/MTF cross-check | 禁止 Run72；先修 TASK-009 |
| RMD-STOP-010 | 用户要求新增患者级、多色、偏心/倾斜、并行等 MVP 外功能 | 放入 PARKING_LOT/新 URD 版本，不插入当前 task |
| RMD-STOP-011 | Codex 本地为通过实机测试需要改变科学模型、冻结参数、阈值、oracle 或 lock boundary | 停止本地修订；保留日志/证据并返回 ChatGPT Web 重新研究与修订规范 |

## Rollback Points

| ID | After | Rollback |
| --- | --- | --- |
| RMD-RB-001 | TASK-001 setup | 删除新建项目目录或 revert setup commit；不触碰既有目录 |
| RMD-RB-002 | TASK-002 environment/session | revert session branch；若 401 fail，保留测试证据并回 MDD 调整 orchestration |
| RMD-RB-003 | TASK-003 persistence boundary | revert store commit；任何已写 test project 用临时目录销毁 |
| RMD-RB-004 | TASK-004 metrics | revert metric commit；golden fixture 保持 docs source-of-truth |
| RMD-RB-005 | TASK-005/006 science locks | 在测试项目中删除本 task 生成物后重建；正式锁不得原地改写 |
| RMD-RB-006 | TASK-007 science gate | 删除 provisional carrier records；不产生正式 pair locks |
| RMD-RB-007 | TASK-008 carrier/manifest | 若未 merge：丢弃 branch；若已 merge：revert PR，并使所有下游 result invalidated |
| RMD-RB-008 | TASK-009/010 app workflows | revert task branch；保留上游 locks/manifests |
| RMD-RB-009 | TASK-011 nominal run | 不修改模型 locks；标记该 run invalid/failed，保留 logs 后重新运行新 run_id |

## RMD Planning Gate

- [x] 任务按依赖和高风险点排序；ZOS environment gate 在早期。
- [x] 前三项任务、test commands、rollback 和 Git branches 已明确。
- [x] project setup 在任何 feature implementation 之前。
- [x] Python 包/环境统一由 uv 管理；单元测试统一由 pytest 执行。
- [x] interface/tests-first 规则明确。
- [x] 每个 task 有测试/检查命令和 Git checkpoint。
- [x] `TDD-TEST-999` 是正式 carrier/Run72 前明确 STOP。
- [x] representative 3-config gate 位于 Run72 前。
- [x] ChatGPT Web ↔ Codex 本地 OpticStudio 双环境职责和回传证据规则已明确。
- [x] 未把 MVP 外科学鲁棒性工作混入实现路径。
- [x] 用户已接受并实际采用本 Build Path。

**Result:** `RMD-0001 v1.2` 为当前 active runbook。TASK-001–004 已完成；当前从 TASK-005 的正式科学资产构建继续执行，并默认使用 ChatGPT Web 主研究/主开发 + Codex 本地 OpticStudio 实机验证闭环。