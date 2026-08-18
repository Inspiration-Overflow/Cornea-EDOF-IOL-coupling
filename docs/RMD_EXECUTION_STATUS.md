# RMD 执行状态

> `RMD-0001` 的执行伴随记录。`docs/RMD.md` 继续作为实现顺序、STOP 条件和验收规则的来源；本文件记录截至 2026-08-18 的真实代码/实机状态，不重新定义科学规范。

## 当前结论

当前仓库已经在本机 **OpticStudio 2026 R1.00 + Premium license** 下完成第一批 ZOS-API 适配：主线程与 worker thread 会话、三种顺序面型实际参数列、Huygens PSF 网格读取、Zernike Standard 系数读取均已通过真实运行。TASK-005B 的两个轴向基座已在当时的 `MVP_2026_v1` baseline 下生成、回读、验证并登记本地 lock。

2026-08-18 在 TASK-005C 设计复核中，项目负责人决定把 `STD_IOL_EYE_2024` 的 carrier 基础球差 / `Q(P)` 校准瞳孔由 3 mm 修订为 **6 mm**；主实验 EPD3/EPD5 不变。该修改改变了 `ScientificBaseline.standard_eye_spec.aperture_mm`，因此当前科学 baseline 正式升级为：

```text
MVP_2026_v2
```

`ProjectStore` 继续对完整 scientific baseline 计算 hash，并拒绝“同 baseline ID、不同内容”。项目不会为了复用旧目录而跳过该检查。

因此当前资产状态必须区分：

- `MVP_2026_v1` 的两个 TASK-005B `.zos` / SHA / validation CSV：**保留为历史实机证据，仍证明 005B 轴向几何实现正确**；
- `MVP_2026_v2` 的正式科学链：**尚未在 OpticStudio 工作站生成**；Codex 下一次验证必须在新 project 目录先重新生成/登记两枚相同几何的 005B base locks，再生成 005C standard-eye lock；
- 旧 v1 project 不删除、不覆盖、不原地迁移。

A0/B0/C0、当前 v2 标准眼、carrier/residual、三代表配置和 Run72 均仍未正式实机执行。

---

## 已完成的 ZOS-API / pre-science hardening

根据独立 code review 已完成两轮基础加固：

- Binary 4 不写 OpticStudio 计算型 `Par4`；
- Huygens PSF 增加 shape/spacing/center/intensity 契约；
- Huygens/Zernike 采集参数进入 frozen settings hash；
- Python.NET/ZOS DLL bootstrap 进程级幂等；
- 新建光学系统显式 `MakeSequential()`；
- 单个 Python 进程只创建一个 OpticStudio application，逻辑 session 串行租用，进程退出时关闭一次；
- Zemax 总 gate 按测试文件使用独立 Python.NET 进程。

详细见：

- `docs/audit/code_review_hardening_2026-08-17.md`
- `docs/audit/zosapi_pre_science_hardening_2026-08-18.md`

### TASK-005B v1 最后一次实机验证

```text
pytest tests/unit                         -> 98 passed
python scripts/run_zemax_gates.py         -> 7 passed
ruff check .                              -> PASS
python -m compileall -q src tests scripts -> PASS
uv lock --check                           -> PASS
```

v1 正式本地资产历史证据：

```text
BASE_LB_PSEUDOPHAKIC.zos
SHA-256 3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c

BASE_ATC_M3_PSEUDOPHAKIC.zos
SHA-256 217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c

TASK_005B_BASE_VALIDATION.csv
SHA-256 3b7373fce0a1dd8c4ff944055a0d430d4b97946e9479f6997e622450e37ae18f
```

这些 SHA **不升级为 v2 lock**；v2 重新生成时以几何/readback oracle 为准，不要求文件字节 hash 与 v1 完全相同。

---

## TASK-005C Web 端当前状态

Draft PR：**#22 `feat: prepare TASK-005C standard eye for OpticStudio validation`**。

文档已先于代码完成修订：

- `URD-0001 v1.4`：standard-eye `C4^0`、IOL footprint、`SA_base`、`Q(P)`/`ZERO_HOA` 统一 EPD=6 mm；主实验 EPD3/EPD5 不变；
- `TDD-0001 v1.3`：对应 TDD-TEST-003 / 006 / 305 统一 6 mm oracle；
- `RMD-0001 v1.3`：执行规则同步；
- `docs/TASK_005C_STANDARD_EYE_IMPLEMENTATION.md`：记录文献依据、v2 baseline、v1/v2 资产边界与 Codex 执行包。

随后代码已按文档修订，但**尚未获得本地 OpticStudio 测试结果**：

- `BASELINE_STANDARD_EYE_SPEC.aperture_mm = 6.0`；
- `CURRENT_SCIENTIFIC_BASELINE_ID = MVP_2026_v2`；
- `NOMINAL_MAIN_555_v1.pupils_mm` 与 `CORNEA_LOCK_B0_555_v1.pupils_mm` 继续为 `(3.0, 5.0)`；
- `STD_IOL_EYE_2024.zos` 构建保存态定义为 EPD=6 mm；
- 6 mm 下测 `C4^0=+0.258±0.005 µm` 与 IOL footprint=`5.15±0.10 mm`；
- `ZERO_HOA` identity 记录 standard-eye calibration pupil=6 mm、wavelength≈546 nm；
- 005B/005C CLI 默认使用 `MVP_2026_v2`；
- 单元测试增加“6 mm calibration 与 EPD3/EPD5 performance 不混用”及 baseline hash regression。

PR #22 继续保持 Draft；在 Codex 实机证据返回前不得 merge。

---

## 当前执行注意事项

- `uv.lock` 已生成；上一正式实机分支通过 `uv lock --check`，005C 新代码仍需重跑。
- 2026 R1.00 把 `ZOSAPI_NetHelper.dll`、`ZOSAPI.dll`、`ZOSAPI_Interfaces.dll` 放在安装根目录；session 同时保留旧版 `ZOS-API/Libraries` 布局支持。
- CLR/ZOS assembly load 在同一 Python process 内只初始化一次；后续逻辑 session 必须复用同一 OpticStudio install identity。切换安装目录必须使用新 Python process。
- 本机 Zemax 总 gate 使用 `uv run python scripts/run_zemax_gates.py`；不同测试文件不放入同一个 CLR 进程。
- 父集成分支个别成功会话曾在 stderr 出现 `FRU__delta_init(): Attempt to start when running!`；后续长流程继续记录 native stderr。
- GUI display smoke、Huygens MTF 交叉验证、Prescription Data 等仍待后续 task。

---

## RMD task 状态

| RMD task | 当前状态 | 本地 OpticStudio 阶段仍需完成 |
| --- | --- | --- |
| TASK-001 Project Setup | **完成并加固** | 保持 locked-env 检查 |
| TASK-002 ZOS session | **实机通过**：2026 R1、process-idempotent bootstrap、process-singleton application、worker/stress gate 通过 | 长批次继续观察原生 stderr |
| TASK-003 Domain + ProjectStore | **离线完成并加固**：完整 baseline hash / schema / provenance；当前 v2 版本化继续复用该 fail-closed 机制 | 在 v2 real project 再做一次集成回放 |
| TASK-004 metric engine | **离线完成**：complex OTF、MTF、MTFa、VSOTF、DOF 等 | 用真实 Huygens PSF/MTF 做 TDD-209/403 |
| TASK-005 scientific assets | **005A 完成；005B v1 实机完成；005C Web 修订完成待实机** | 新建 v2 project → 重新登记 005B 双 base → build/validate `STD_IOL_EYE_2024` 6 mm → 后续 REF_MONO/A0/B/C/Coordinate Return |
| TASK-006 B0 | **算法完成并加固** | TASK-005 完成后运行真实五点 B scan；人工 morphology decision；写 B0 lock |
| TASK-007 carrier science gate | **fail-closed 门控完成** | 在 6 mm STD eye 实际求 18 P/Q；ZERO_HOA achieved-SA 回放；3 residual payload；tolerance policy；low/median/high 校准；解除 TDD-999 |
| TASK-008 carrier/pair + manifest | **生成器完成** | TASK-007 通过后生成正式 18 lock、36 pair、72 manifest |
| TASK-009 analysis | **API smoke/hardening 完成** | footprint/Prescription/Huygens MTF；3 代表配置；sampling/MTF cross-check |
| TASK-010 GUI | **scaffold/thread boundary 已复核** | GUI display/full-flow smoke |
| TASK-011 nominal acceptance | **验收判定器完成** | 只有 TASK-009 代表配置通过后运行 Run72/repeatability |

---

## 仍然有效的 STOP 条件

1. PR #22 的 005C 新代码在本地 OpticStudio 通过前不得 merge。
2. 不得通过修改/忽略 baseline hash 来把 v2 scientific contents 写入旧 `MVP_2026_v1` project；必须使用新 v2 project。
3. 若 6 mm standard-eye validation 只有改回 3 mm 或改变 `+0.258 / −0.20 / −0.27 / 0.00 µm` 才能通过，立即返回 Web 科学审查。
4. `TDD-TEST-999` 未解除前，不允许生成正式 EDOF carrier/pair locks，也不允许 Run72。
5. 3 个代表配置未通过 sampling convergence 与独立 MTF cross-check 前，不允许 Run72。
6. A0/B0/C0、STD eye、residual 或 carrier 一旦正式 lock，任何下游流程不得改其 hash。
7. 合成测试数据只用于代码合同，不能进入正式 locks/manifests/论文结果。

---

## 下一次 Codex 执行入口

在 `feat/task-005c-standard-eye` 最新提交上，使用新的目录，例如：

```powershell
$P = "project_mvp_2026_v2"

uv sync
uv run pytest tests/unit/test_standard_eye.py -vv
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check

uv run python scripts/build_task_005b_base_assets.py --project-dir $P --baseline-id MVP_2026_v2
uv run python scripts/build_task_005b_base_assets.py --project-dir $P --baseline-id MVP_2026_v2 --validate-only

uv run pytest tests/zemax/test_zos_standard_eye.py -vv
uv run python scripts/run_zemax_gates.py

uv run python scripts/build_task_005c_standard_eye.py --project-dir $P --baseline-id MVP_2026_v2
uv run python scripts/build_task_005c_standard_eye.py --project-dir $P --baseline-id MVP_2026_v2 --validate-only
```

本文件当前状态含义：**v1 的 TASK-005B 实机证据保留有效；当前正式 scientific baseline 已升级为 v2；005C 文档与 Web 代码已完成 6 mm 修订，但 v2 双基座登记和 standard-eye 实机验证尚未执行。**