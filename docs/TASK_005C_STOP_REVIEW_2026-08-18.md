# TASK-005C 实机 STOP 复核 — 2026-08-18

> 状态：**STOP confirmed；PR #22 必须保持 Draft，不得合并。**
>
> 本文记录 `feat/task-005c-standard-eye@c6ce2bd01ba4f4b4e518bcbc12c75806aa9dfd78` 在 OpticStudio 2026 R1.00 Premium 上的首次 TASK-005C 实机验证结果、根因复核与修订方向。本文先冻结修订原则，再允许修改代码；不得通过调角膜 Q、改 6 mm pupil、放宽 `BaselineMismatch` 或移动 IMAGE 去“追”一个数值。

## 1. 实机证据

环境：

- branch: `feat/task-005c-standard-eye`
- commit: `c6ce2bd01ba4f4b4e518bcbc12c75806aa9dfd78`
- OpticStudio: `2026 R1.00`, Premium
- Python: `3.12.9`

离线检查：

- `tests/unit/test_standard_eye.py`: `5 passed`
- `tests/unit`: `103 passed`
- Ruff: PASS（本地修正一处 import ordering，未提交）
- compileall: PASS
- `uv lock --check`: PASS

TASK-005B 在 `MVP_2026_v2` 下重新生成并只读回载成功，且 SHA-256 与 v1 历史几何资产一致：

- `BASE_LB_PSEUDOPHAKIC.zos`: `3213828f34dcf6371af870af4c0d7cf085fcf4d8ec64d6d78929470a72f54c8c`
- `BASE_ATC_M3_PSEUDOPHAKIC.zos`: `217fc7417bd9ceaf6a8d69f48b33253b951204805bdae758d8eb94017c2e843c`
- `TASK_005B_BASE_VALIDATION.csv`: `3b7373fce0a1dd8c4ff944055a0d430d4b97946e9479f6997e622450e37ae18f`

TASK-005C 已通过的实测项：

- entrance pupil diameter: `6.000000 mm`
- wavelength: `546.000000 nm`
- IOL-reference footprint: `5.221083 mm`，位于 `5.15±0.10 mm`
- cornea index: `1.376000`
- surrounding medium index: `1.336000`
- posterior-cornea → IOL-reference: `3.923547862 mm`

阻断项：

- 在标准眼保存状态，OpticStudio Zernike Standard `C4^0 = 0.276491 µm`
- 把 IMAGE 移到当前代码计算的角膜 paraxial focus 后，`C4^0 = 0.385937 µm`
- 二者均不满足旧的直接 gate `0.258±0.005 µm`

同一进程中新建处方后再启动 Zernike analysis 还可能触发：

```text
FRU__delta_init(): Attempt to start when running!
FileLoadException: A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

独立既有 Zernike 实机测试可通过，因此当前证据不支持“OpticStudio 安装损坏”；问题集中于 005C 的 Zernike/reference-plane 定义映射以及新建系统后同进程的 analysis lifecycle。

本次失败后：

- 未生成/登记 `STD_IOL_EYE_2024.zos`
- 未生成/登记 TASK-005C validation CSV
- 未生成 TASK-005C lock
- 临时诊断 `.zos` 已删除
- 残留 OpticStudio/Zemax 进程为 0
- v2 正式目录只保留已经通过的 005B 资产

## 2. 文献复核：`+0.258 µm` 的真实含义

Norrby et al., *Applied Optics* 2007, DOI `10.1364/AO.46.006595` 的 Table 1 对 Liou 两面角膜给出：

- anterior radius `7.77 mm`
- anterior Q `−0.18`
- thickness `0.50 mm`
- posterior radius `6.40 mm`
- posterior Q `−0.60`
- corneal RI `1.376`
- aqueous RI `1.336`
- `c[4,0] = +0.258 µm`

表下注明该 `c[4,0]` 为 **6 mm entrance pupil** 下用于模型比较的 Zernike spherical-aberration coefficient。

更关键的是原文方法部分说明：Q ↔ `c[4,0]` 的换算使用 **OSLO EDU real-ray tracing**，采用 **OSLO EDU 的 best-focus criterion**，单色折射率约对应 `546 nm`；OSLO 输出的非归一化第 8 项再换算为归一化 `c[4,0]`。因此：

> `+0.258 µm` 是 **Liou/Norrby + OSLO best-focus/convention** 下的文献锚点，并不等价于“任意软件、任意 IMAGE/reference sphere 下的 Zernike Standard term 11 必须直接等于 0.258”。

原始论文页面：

- `https://opg.optica.org/ao/abstract.cfm?uri=ao-46-26-6595`

## 3. OpticStudio reference-plane 复核

Ansys 官方文档说明，OpticStudio 默认 `Reference OPD = Exit Pupil`。对 focal system，它使用位于 exit pupil 的 spherical reference；光线先追到 image surface，再回传到 exit pupil 计算 wavefront error。改变 OPD reference 或 image focus 会改变 wavefront error。

因此当前 005C 把 IMAGE 强行移到“角膜 paraxial focus”并不能复现 Norrby/OSLO 的 best-focus convention，而且实测 `0.385937 µm` 已直接否定这一映射。

官方来源：

- `https://optics.ansys.com/hc/en-us/articles/43071050784147-How-do-OPD-Reference-settings-in-System-Explorer-Advanced-section-affect-wavefront-calculation`
- `https://optics.ansys.com/hc/en-us/articles/43071071800467-How-to-model-a-black-box-optical-system-using-Zernike-coefficients`

Ansys 还明确说明 Zernike coefficient 是对系统 wavefront error 的拟合，wavefront data 位于 exit pupil；因此 coefficient 必须与 pupil、field、wavelength 和 reference convention 绑定。

## 4. 根因判断

### 4.1 科学根因

旧 005C 把两件不同的事错误地绑定成一个数值 gate：

1. **文献处方锚点**：Liou/Norrby 角膜在 OSLO best-focus convention 下 `c[4,0]=+0.258 µm @ 6 mm`；
2. **项目 OpticStudio oracle**：OpticStudio Zernike Standard 在本项目固定 reference convention 下得到的 Z11。

当前实机结果证明两者不能直接视为同一 oracle。

### 4.2 工程根因

005C build path 在同一 Python/OpticStudio process 中执行：

```text
New system → write prescription → Zernike analysis
```

会偶发触发原生 `ZemaxEngine.dll`/FRU lifecycle 错误；而独立加载既有文件的 Zernike test 可以通过。005C 不应为了一个非正式 gate 把 formal asset build 绑定在这一高风险同进程 analysis 顺序上。

## 5. 修订后的科学规则

### RULE-005C-1 — 保留 Liou/Norrby 处方，不调 Q 追数值

`STD_IOL_EYE_2024` 的两面角膜继续固定：

```text
R1 = +7.77 mm
Q1 = -0.18
CT = 0.50 mm
R2 = +6.40 mm
Q2 = -0.60
n_cornea = 1.376
n_medium = 1.336
```

`+0.258 µm @ 6 mm` 保留为**文献 provenance anchor**。禁止通过改变 Liou 处方使 OpticStudio Z11 人为命中 0.258。

### RULE-005C-2 — 005C formal gate 不再要求 Zemax Z11 = 0.258±0.005

005C formal acceptance 改为：

- exact Liou prescription above；
- EPD `6.000±0.001 mm`；
- λ `546±1 nm`；
- IOL-reference footprint `5.15±0.10 mm`；
- medium `1.336±1e-6`；
- cornea `1.376±1e-6`；
- deterministic posterior-cornea → IOL-reference geometry；
- saved/reloaded `.zos` hash unchanged；
- no unintended vignetting / wrong field / wrong stop semantics。

OpticStudio corneal Z11 可以作为**diagnostic/provenance value**记录，但不得在 005C 中与 Norrby `0.258` 做直接 pass/fail 比较。

### RULE-005C-3 — 删除“移动到 paraxial focus 再量 C40”的正式路径

005C 不再修改 IMAGE 去复现 Norrby值。正式 `.zos` 保存和验证始终保持其固定 IMAGE reference；不存在临时 paraxial-focus mutation。

### RULE-005C-4 — TASK-007 的 `SA_base` 仍是强数值 gate，但必须做 matched differential

对每个 actual carrier power `P_ijk`：

```text
candidate(P,Q) @ fixed STD eye
minus
ZERO_HOA(P) @ the same fixed STD eye
```

两次 Zernike measurement 必须完全共享：

- EPD = 6.0 mm
- λ ≈ 546 nm
- field
- image surface / OPD reference convention
- pupil centering/normalization
- carrier paraxial power、geometry、material、position

并且**candidate 与 ZERO_HOA 不得分别 refocus**。`SA_base` 的正式 oracle 只使用：

\[
\Delta C_4^0 = C_{4,candidate}^0 - C_{4,ZERO\_HOA}^0
\]

目标仍为：

- WFS `−0.20±0.01 µm`
- RAD `−0.27±0.01 µm`
- HOA `0.00±0.01 µm`

这样 reference-sphere / corneal baseline 的共同偏置进入两边并在 matched differential 中消除；项目不把孤立的绝对 OpticStudio Z11 当作 IOL SA。

### RULE-005C-5 — Zernike lifecycle 与 formal asset build 解耦

005C 的 `.zos` 构建/锁定不得依赖“同进程新建处方后立刻启动 Zernike analysis”。如需记录 standard-eye Z11 diagnostic，必须在**独立 fresh process 只读加载已保存文件**后执行；其失败不能伪造 formal 005C PASS，但也不再作为 `0.258` 数值科学 gate。

TASK-007 的正式 matched-differential Zernike gate则必须在可重复的 fresh-process/read-only workflow 下验证后才能解除相应 STOP。

## 6. Baseline 版本

本次修订**不改变任何 frozen scientific numeric value**：6 mm、546 nm、Liou prescription、5.15±0.10 mm、WFS/RAD/HOA SA targets 均不变。

因此继续使用：

```text
MVP_2026_v2
```

不创建 `v3`。变化的是 `0.258` 的**oracle interpretation/reference convention**，而不是 `ScientificBaseline` dataclass 的数值内容。`ProjectStore` baseline hash contract 不修改。

## 7. 下一实现顺序

1. 先同步 URD/TDD/RMD/005C 实施文档，使 `0.258` 明确成为 literature anchor，而不是 direct Zemax-Z11 gate；
2. 删除 005C 中 temporary paraxial-focus C40 measurement 与 direct tolerance gate；
3. 保留/加强 prescription、EPD、λ、footprint、index、hash readback gates；
4. 005C build/validate 不启动 Zernike analysis；
5. 如保留 C40 diagnostic，只在 fresh subprocess 只读加载后测量并记录；
6. Codex 在原 `project_mvp_2026_v2` 目录上重跑 005C；不得覆盖已经 lock 的 005B；
7. 005C 通过后仍不进入 carrier formal lock；TASK-007 必须实现 matched `candidate − ZERO_HOA(P)` 6-mm differential gate。

## 8. STOP 状态

截至本文：

- PR #22 = Draft
- TASK-005B v2 = PASS
- TASK-005C = STOP / revision required
- `STD_IOL_EYE_2024` = not generated / not locked
- TDD-999 = unchanged
- Run72 = blocked

不得合并 PR #22，直到本文的文档和代码修订完成并由 OpticStudio 实机重新验证。