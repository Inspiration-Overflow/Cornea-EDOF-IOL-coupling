# RMD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **Build Path / Route-Runbook-Execution Map。** 本文件只规定安全实现顺序、测试闸门、回滚和 Git checkpoint；不重新定义科学模型。来源：`URD-0001 v1.3`、`ADD-0001 v1.4`、`MDD-0001 v1.3`、`TDD-0001 v1.2`。

## Metadata

- document_id: RMD-0001
- version: 1.1
- status: checkpoint-ready
- last_updated: 2026-08-17
- document_strength: standard
- implementation_language: Python
- package_manager: uv
- default_branch: main
- merge_style: squash
- remote_status: unknown / not yet inspected
- implementation_status: not started

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

## Build Path Checkpoint Summary

进入实现后的**前三步**固定为：

| Order | Task | Purpose | Test command | Rollback | Git branch |
| --- | --- | --- | --- | --- | --- |
| 1 | RMD-TASK-001 Project Setup + test skeleton | 建干净 uv/src/tests/git 基础，不写科学 feature | `uv run pytest --collect-only && uv run ruff check .` | RMD-RB-001 | `chore/rmd-task-001-setup` |
| 2 | RMD-TASK-002 ZOS session + environment risk gate | 尽早验证真实 ZOS-API lifecycle 与 worker-thread assumption | `uv run pytest tests/zemax -m zemax -k "session or worker_thread"` | RMD-RB-002 | `feat/rmd-task-002-zos-session` |
| 3 | RMD-TASK-003 Domain + ProjectStore | 冻结 ID/schema/hash/run-state 基础，避免后续科学代码各自写文件 | `uv run pytest -m unit -k "store or schema or settings or environment or path"` | RMD-RB-003 | `feat/rmd-task-003-project-store` |

**Checkpoint rule：** 用户接受本 Build Path 后才进入 RMD-TASK-001；第一次真实 push 或 merge 仍需单独明确批准。

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

每个 RMD-TASK 按同一顺序执行：

1. 从 clean `main` 创建该 task branch。
2. 只启用/编写该 task 对应的 failing tests。
3. 写最小实现；不顺手实现后续 task；任何 Python 依赖变更通过 `uv add` / `uv remove` 完成。
4. 测试统一通过 `pytest` 执行：跑该 task 的 `uv run pytest ...` 命令 + `uv run ruff check .`。
5. 更新受到影响的 `docs/TRACE.md`、`.vibe/trace.json`、CHANGELOG；必要时更新短 OKF 页面。
6. `git diff` / `git status` 检查无 secrets、`.zos` 运行产物和无关改动。
7. commit。
8. 有 remote 时，第一次 push/PR/merge 前触发 RMD-STOP-007。

## Git Checkpoints

| ID | Task | Branch | Planned Commit | PR | Merge |
| --- | --- | --- | --- | --- | --- |
| RMD-GIT-001 | TASK-001 | `chore/rmd-task-001-setup` | `chore: complete RMD-TASK-001 project setup` | not started | not started |
| RMD-GIT-002 | TASK-002 | `feat/rmd-task-002-zos-session` | `feat: implement RMD-TASK-002 ZOS session boundary` | not started | not started |
| RMD-GIT-003 | TASK-003 | `feat/rmd-task-003-project-store` | `feat: implement RMD-TASK-003 project store` | not started | not started |
| RMD-GIT-004 | TASK-004 | `feat/rmd-task-004-metrics` | `feat: implement RMD-TASK-004 optical metrics` | not started | not started |
| RMD-GIT-005 | TASK-005 | `feat/rmd-task-005-assets` | `feat: implement RMD-TASK-005 scientific assets` | not started | not started |
| RMD-GIT-006 | TASK-006 | `feat/rmd-task-006-b0` | `feat: implement RMD-TASK-006 B0 workflow` | not started | not started |
| RMD-GIT-007 | TASK-007 | `feat/rmd-task-007-carrier-gate` | `feat: implement RMD-TASK-007 carrier science gate` | not started | not started |
| RMD-GIT-008 | TASK-008 | `feat/rmd-task-008-carriers-manifest` | `feat: implement RMD-TASK-008 carrier locks and manifest` | not started | not started |
| RMD-GIT-009 | TASK-009 | `feat/rmd-task-009-analysis` | `feat: implement RMD-TASK-009 analysis workflow` | not started | not started |
| RMD-GIT-010 | TASK-010 | `feat/rmd-task-010-gui` | `feat: implement RMD-TASK-010 desktop shell` | not started | not started |
| RMD-GIT-011 | TASK-011 | `test/rmd-task-011-nominal-72` | `test: complete RMD-TASK-011 nominal acceptance` | not started | not started |

若没有 remote：保持 local commits，PR/Merge 标记 `skipped: no remote`；不得假装已开 PR。

## 🛑 Stop Conditions

| ID | Condition | Required Action |
| --- | --- | --- |
| RMD-STOP-001 | TDD test 缺 oracle、或实现需要改变已冻结 analysis setting/科学阈值 | 停止实现，回到 TDD |
| RMD-STOP-002 | 实现需要修改 ADD lock boundary / 出现未记录 coupling | 停止，回到 ADD/MDD |
| RMD-STOP-003 | `TDD-TEST-401` worker-thread ZOS-API gate 失败/卡死 | 不继续 thread-owned session；只调整 MOD-008 orchestration placement，更新 MDD/TDD/RMD 后再实现 GUI |
| RMD-STOP-004 | `TDD-TEST-999` 未解除或任一 residual low/median/high calibration 失败 | 停在 TASK-007；禁止 TASK-008 正式 EDOF pair lock 和 Run72 |
| RMD-STOP-005 | 任何 downstream workflow 改变已冻结 A0/B0/C0/STD/residual/carrier hash | 停止；修复违反 lock contract 的代码 |
| RMD-STOP-006 | test/ruff 失败 | 不 commit/merge；修复或回到 MDD/TDD |
| RMD-STOP-007 | 第一次 push、PR merge、删除、覆盖真实项目文件 | 必须取得用户明确批准 |
| RMD-STOP-008 | git working tree 有无关改动、secret、`.env`、local DB/cache 或未计划 generated artifacts | 不提交；先隔离/ignore/询问 |
| RMD-STOP-009 | 3-config representative analysis 未通过 sampling/MTF cross-check | 禁止 Run72；先修 TASK-009 |
| RMD-STOP-010 | 用户要求新增患者级、多色、偏心/倾斜、并行等 MVP 外功能 | 放入 PARKING_LOT/新 URD 版本，不插入当前 task |

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
- [x] 第一次 push/merge 保留用户确认 checkpoint。
- [x] 未把 MVP 外科学鲁棒性工作混入实现路径。
- [ ] 用户接受本 Build Path。

**Result:** `RMD-0001 v1.1` 已达到 Build Path checkpoint；用户确认后才执行 RMD-TASK-001。
