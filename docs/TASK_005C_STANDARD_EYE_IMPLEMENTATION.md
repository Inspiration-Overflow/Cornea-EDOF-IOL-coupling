# TASK-005C — `STD_IOL_EYE_2024` 与 `ZERO_HOA_PARAXIAL_REFERENCE` 实施规格

> 状态：**Web 实现完成，等待 Codex / OpticStudio 2026 R1 实机验证**。
>
> 本文是 RMD-TASK-005 的 005C 子阶段实施规格。它不修改既有科学数值锁，只把已经冻结但容易混淆的标准眼验收条件转成可执行的 Zemax 处方、测试条件和失败规则。

## 1. 本阶段目标

TASK-005C 只完成两件事：

1. 建立并锁定项目内部统一 IOL 标准眼：`STD_IOL_EYE_2024`；
2. 冻结 `ZERO_HOA_PARAXIAL_REFERENCE` 的 power-specific 身份与匹配规则，为 TASK-007 的 `Q(P)` 球差标定提供零点。

本阶段**不**建立 WFS/RAD/HOA 的正式 18 个 carrier，不生成 EDOF residual，不生成 pair/manifest，也不解除 `TDD-TEST-999`。

`STD_IOL_EYE_2024` 是本项目内部工程模型名，不是 ISO 标准中的正式模型名称，也不应在论文或报告中表述为“ISO 规定的标准眼处方”。

---

## 2. 权威依据与项目边界

### 2.1 ISO / FDA 只定义技术方向，不直接提供本项目处方

当前国际标准为：

- ISO 11979-2:2024, *Ophthalmic implants — Intraocular lenses — Part 2: Optical properties and test methods*, Edition 3, 2024-10；
- FDA 已以 Recognition No. **10-137** 完整认可 ISO 11979-2:2024，Date of Entry 2025-05-26。

官方来源：

- ISO: `https://www.iso.org/standard/86607.html`
- FDA: `https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/detail.cfm?standard__identification_no=46072`

因此本项目沿用当前 IOL 光学性能测试体系的标准化方向，但以下 Liou 角膜、具体轴向几何以及 `ZERO_HOA` 数值参考均属于**项目工程定义**。

### 2.2 生理正球差角膜依据

Norrby, Piers, Campbell & van der Mooren 2007 在 *Applied Optics* 的原始论文中汇总多种模型角膜。其 Table 1 对 Liou 两面角膜给出：

| 参数 | 值 |
| --- | ---: |
| 前角膜半径 | `+7.77 mm` |
| 前角膜 Q | `-0.18` |
| 角膜厚度 | `0.50 mm` |
| 后角膜半径 | `+6.40 mm` |
| 后角膜 Q | `-0.60` |
| 角膜折射率 | `1.376` |
| 房水折射率 | `1.336` |
| `C4^0` | `+0.258 µm` |

论文脚注明确说明表中 `C4^0` 的模型间比较按 **6 mm entrance pupil** 计算。

原始来源：

S. Norrby, P. Piers, C. Campbell, M. van der Mooren. *Model eyes for evaluation of intraocular lenses*. Applied Optics. 2007;46(26):6595–6605. DOI: `10.1364/AO.46.006595`.

Holladay–Piers 2002 的方法学依据继续成立：IOL 非球面设计应在带有代表性角膜球差的模型眼中作为系统目标优化，而不是把孤立 IOL 的一个表面系数直接当成全眼球差。

原始来源：

J. T. Holladay, P. A. Piers, G. Koranyi, M. van der Mooren, N. E. S. Norrby. *A new intraocular lens design to reduce spherical aberration of pseudophakic eyes*. J Refract Surg. 2002;18(6):683–691. DOI: `10.3928/1081-597X-20021101-04`.

---

## 3. 关键澄清：6 mm、5.15 mm 与 3 mm 是三个不同量

项目此前已经冻结：

- 模型角膜：`C4^0 = +0.258 ± 0.005 µm`；
- IOL 前表面光束覆盖：`5.15 ± 0.10 mm`；
- carrier 主标准校准孔径：`3.000 ± 0.001 mm`；
- 波长：`546 ± 1 nm`；
- IOL 周围介质：`n = 1.336 ± 1e-6`。

这里不能把这些量当成同一个“孔径”。TASK-005C 固定如下操作化解释：

### 3.1 角膜球差 / IOL footprint 几何验证态

使用：

`Entrance Pupil Diameter = 6.0 mm`

在同一个标准眼几何中同时检查：

- Liou 模型角膜 `C4^0 = +0.258 ± 0.005 µm`；
- IOL reference plane 的实际 real-ray footprint `= 5.15 ± 0.10 mm`。

这是因为 `+0.258 µm` 的权威来源本身对应 6 mm entrance pupil。

### 3.2 carrier 标准校准态

正式保存的 `STD_IOL_EYE_2024.zos` 默认：

`Entrance Pupil Diameter = 3.0 mm`

该 3 mm 条件用于后续 TASK-007 的 physical carrier ↔ `ZERO_HOA_PARAXIAL_REFERENCE` 标准眼球差差分与 `Q(P)` 求解。

因此：

`6 mm corneal-SA/footprint gate != 3 mm carrier calibration aperture`

验证程序临时切换到 6 mm 做角膜/footprint 测量，完成后恢复 3 mm，且不保存临时状态。

---

## 4. `STD_IOL_EYE_2024` Zemax 处方

### 4.1 表面顺序

除 OBJECT 外，正式模板使用四个表面：

| Surface | Comment | Radius / Q | Thickness to next | Medium after |
| ---: | --- | --- | --- | --- |
| 1 | `STD_CORNEA_ANT` | `R=+7.77 mm, Q=-0.18` | `0.500 mm` | cornea `n=1.376 @ 546 nm` |
| 2 | `STD_CORNEA_POST` | `R=+6.40 mm, Q=-0.60` | 见 4.2 | aqueous `n=1.336 @ 546 nm` |
| 3 | `IOL_ANT_REFERENCE` | plane | 到 IMAGE 的固定参考距离 | aqueous |
| 4 | `IMAGE_REFERENCE` | plane | — | IMAGE |

其他冻结条件：

- OBJECT：infinity；
- Field：`0°`；
- 单色：`546 nm`；
- system aperture type：Entrance Pupil Diameter；
- 文件保存默认 EPD：`3.0 mm`；
- STOP：Surface 1（前角膜）；
- IMAGE：平面固定参考面。

### 4.2 IOL reference plane 的初始工程位置

当前 URD/TDD 冻结的是 `5.15 ± 0.10 mm` footprint，而没有冻结一个标准眼 IOL 轴向距离。因此 Web 实现不凭空把某个距离升级为科学锁，而采用一个**可重算的工程构建规则**：

1. 以 6 mm entrance pupil 的上缘 paraxial ray：`y0=3.0 mm`；
2. 用 reduced-angle paraxial trace 通过上述 Liou 两面角膜；
3. 求后角膜之后的距离 `d`，使 IOL reference plane 上半径为 `5.15/2=2.575 mm`。

当前解析结果约为：

`d = 3.92355 mm`

这是**构建起点而不是验收 oracle**。正式验收只认 OpticStudio real-ray footprint：

`5.15 ± 0.10 mm`。

若实机真实光线显示该 paraxial 起点略有偏差，允许 Codex 仅在保持科学 target 不变的前提下，把这一实现层距离改成 real-ray solve 的确定性结果，并回传 Web 端审查后再锁定。不得为了保留 `3.92355 mm` 而牺牲 footprint target。

### 4.3 IMAGE reference

当前模板把前角膜顶点到 `IMAGE_REFERENCE` 的工程参考轴长设为：

`23.950 mm`

其目的只是提供稳定、正常眼尺度的固定 Zernike 参考几何，并方便后续 carrier/reference 在同一 image/reference sphere 下作差。它不是把 `STD_IOL_EYE_2024` 声称成完整 Liou–Brennan 解剖眼，也不是主实验 Base。

这个实现层距离不进入既有 `ScientificBaseline` hash；一旦 005C 实机验证通过并正式锁定 `.zos`，则由该 `.zos` hash 固定，不再静默改变。

---

## 5. Zernike 与 footprint 验证规则

### 5.1 角膜 C4

验证时：

1. 加载正式/临时标准眼；
2. 临时把 EPD 从 3 mm 改为 6 mm；
3. 使用已有 Zernike Standard acquisition contract；
4. 读取 OSA/ANSI `Z11 = C4^0`；
5. 要求：`+0.258 ± 0.005 µm`；
6. 恢复 EPD=3 mm，不保存临时改变。

不得通过调整已选定的 Liou `R/Q` 来“追着测试数值跑”。若 C4 不符合，优先检查：

- EPD 是否真的是 6 mm entrance pupil；
- Zernike normalization/reference 是否一致；
- 波长是否约 546 nm；
- surface sign / conic / material index 是否正确；
- image/reference sphere 的 OpticStudio 设置是否造成定义差异。

只有确认不是实现/规范映射问题后，才回 Web 端重新审查科学定义。

### 5.2 IOL footprint

同一个 6 mm 验证态下，使用 ZOS-API normalized unpolarized real batch ray trace：

- field = 0；
- pupil coordinate `Py=-1` 与 `Py=+1`；
- trace endpoint = `IOL_ANT_REFERENCE`；
- 无 vignette / ray error；
- footprint = 两条边缘光线在该面的 y-intercept 差。

要求：

`5.15 ± 0.10 mm`。

该数值是 IOL plane 的实际 beam footprint，不是 3 mm carrier calibration aperture，也不是 IOL optical diameter。

---

## 6. `ZERO_HOA_PARAXIAL_REFERENCE`

### 6.1 不建立一个固定 +20 D 参考文件

`ZERO_HOA_PARAXIAL_REFERENCE` 是 **power-specific numerical reference**。

对于每个实际 carrier `P_ijk`，后续 TASK-007 必须生成对应的：

`ZERO_HOA(P_ijk)`。

因此 005C 不创建一个固定 power 的 `.zos` 并让所有 carrier 共用。

### 6.2 身份匹配契约

Web 端现已实现 `ZeroHoaReferenceRecord`。它从实际 `ProvisionalCarrier` 复制并要求 exact match：

- carrier ID；
- paraxial power；
- anterior/posterior radius metadata；
- center thickness metadata；
- material metadata；
- IOL reference position。

其 optical model 固定标记为：

`ideal_paraxial_zero_hoa`

这里需要区分两层含义：

- **身份/包络 metadata** 与 physical carrier 一致，用于防止 reference 误配；
- **实际光学作用**由同一参考平面上的理想 paraxial element 提供，只保留规定的一阶 power，不引入 aspheric/HOA/residual。

因此 `ZERO_HOA` 不是另一枚物理 IOL，也不进入 72-config manifest。

### 6.3 后续标准眼 SA 定义

TASK-007 对任一 carrier：

`SA_IOL_STD(P,Q) = C4_eye_STD(actual carrier) - C4_eye_STD(ZERO_HOA(P))`

两次分析必须使用相同：

- `STD_IOL_EYE_2024` locked file/hash；
- 3 mm calibration aperture；
- 546 nm；
- field/reference axis；
- carrier power identity；
- reference plane。

WFS/RAD/HOA 的 `-0.20 / -0.27 / 0.00 µm` 仍然是项目内部的 standard-eye equivalent SA targets，不声称是 ISO 对孤立 IOL SA 的规范性定义。

---

## 7. 代码实现

本分支新增：

- `src/whole_eye_mvp/standard_eye.py`
  - 标准眼工程处方；
  - paraxial IOL-plane 起始距离求解；
  - build / readback / real-ray footprint / Zernike C4 validation；
  - create-once project artifact + SHA lock；
  - `ZERO_HOA` power-specific identity contract。
- `tests/unit/test_standard_eye.py`
  - Liou cornea处方；
  - 6 mm 与 3 mm 条件分离；
  - paraxial geometry deterministic；
  - validation fail-closed；
  - `ZERO_HOA` carrier metadata mismatch rejection。
- `tests/zemax/test_zos_standard_eye.py`
  - 独立进程 build；
  - 正式 target readback；
  - read-only reload；
  - SHA 不被 validate-only 改写。
- `scripts/build_task_005c_standard_eye.py`
  - build / `--validate-only` CLI。
- `scripts/run_zemax_gates.py`
  - 新增 005C gate；仍保持每个 Zemax test file 一个独立 Python.NET process。

本阶段没有修改 `BaselineStandardEyeSpec` 字段，因此既有 scientific baseline serialization/hash 不因“补充 6 mm 操作条件”而改变；005B 正式 base locks 不应因此失效。

---

## 8. Codex / OpticStudio 实机执行顺序

从最新远端分支开始，不沿用旧 005B 工作分支：

```powershell
git fetch origin
git switch feat/task-005c-standard-eye
git pull --ff-only
uv sync
```

先跑纯 Python：

```powershell
uv run pytest tests/unit/test_standard_eye.py -vv
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check
```

再跑 005C 单项实机：

```powershell
uv run pytest tests/zemax/test_zos_standard_eye.py -vv
```

若单项通过，再跑总 gate：

```powershell
uv run python scripts/run_zemax_gates.py
```

正式本地项目构建：

```powershell
uv run python scripts/build_task_005c_standard_eye.py --project-dir project
```

随后必须用新 Python/OpticStudio 进程只读复核：

```powershell
uv run python scripts/build_task_005c_standard_eye.py --project-dir project --validate-only
```

记录：

- `STD_IOL_EYE_2024.zos` SHA-256；
- validation CSV SHA-256；
- 6 mm `C4^0`；
- 6 mm IOL footprint；
- 3 mm saved calibration aperture；
- 546 nm medium readback；
- exact IOL reference distance；
- validate-only 前后 `.zos` hash；
- unit / Zemax / Ruff / compileall / lock-check 结果。

---

## 9. 本地允许的最小修订边界

Codex 可直接修正：

- ZOS-API enum/property 名称差异；
- Python.NET out-parameter / `ReadNextResult()` tuple 映射；
- BatchRayTrace resource close 方式；
- OpticStudio 2026 R1 对 SystemData aperture 的实际 API 映射；
- 为满足既定 `5.15 ± 0.10 mm` real-ray footprint 而把 paraxial `3.92355 mm` 起点替换为确定性 real-ray solve 结果。

Codex **不得**自行改变：

- `C4^0 = +0.258 ± 0.005 µm`；
- C4 权威 normalization pupil = 6 mm；
- carrier 主校准 aperture = 3 mm；
- footprint target `5.15 ± 0.10 mm`；
- `n=1.336`；
- `λ≈546 nm`；
- Liou 角膜 `R/Q`；
- `ZERO_HOA` power-specific 原则；
- WFS/RAD/HOA 后续 SA targets。

若上述冻结项之一必须改变才能让实机结果通过，按 RMD STOP 规则返回 Web 端，不做本地“调到能过”。

---

## 10. TASK-005C 完成条件

只有同时满足以下条件，Web 端才把 005C 标为完成并合并到 `main`：

1. unit tests 全通过；
2. `test_zos_standard_eye.py` 实机通过；
3. 总 `run_zemax_gates.py` 通过；
4. `C4^0_6mm = +0.258 ± 0.005 µm`；
5. `IOL footprint_6mm = 5.15 ± 0.10 mm`；
6. 正式 `.zos` 保存状态为 EPD 3 mm、λ≈546 nm、field=0；
7. medium index 符合 `1.336 ± 1e-6`；
8. 正式 `.zos` / validation CSV 有可追溯 SHA-256；
9. 独立进程 validate-only 不改变 `.zos` hash；
10. Web 独立审核无科学定义漂移。

完成 005C 后，下一阶段才进入：

**TASK-005D：共同角膜参考模型 + `REF_MONO_CORNEA_LOCK`**。
