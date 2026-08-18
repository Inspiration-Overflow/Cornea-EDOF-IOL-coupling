# TASK-005C — `STD_IOL_EYE_2024` 与 `ZERO_HOA_PARAXIAL_REFERENCE` 实施规格

> 状态：**科学文档已修订为 6 mm calibration；代码随后按本文修订，之后等待 Codex / OpticStudio 2026 R1 实机验证。**
>
> 本文是 RMD-TASK-005 的 005C 子阶段实施规格。它执行 `URD-0001 v1.4` 与 `TDD-0001 v1.3`，不重新定义主实验矩阵。

## 1. 本阶段目标

TASK-005C 只完成两件事：

1. 建立并锁定项目内部统一 IOL 标准眼：`STD_IOL_EYE_2024`；
2. 冻结 `ZERO_HOA_PARAXIAL_REFERENCE` 的 power-specific 身份与匹配规则，为 TASK-007 的 `Q(P)` 球差标定提供零点。

本阶段**不**建立 WFS/RAD/HOA 的正式 18 个 carrier，不生成 EDOF residual，不生成 pair/manifest，也不解除 `TDD-TEST-999`。

`STD_IOL_EYE_2024` 是本项目内部工程模型名，不是 ISO 标准中的正式模型眼处方。

---

## 2. 本次修订的核心决定

此前草案把 `3 mm` 作为 carrier 的标准眼主校准孔径。经项目负责人复核与文献回查，本定义修订为：

\[
\boxed{EPD_{SA-cal}=6.0\ \mathrm{mm}}
\]

从本版本开始，以下四项统一在 **6.0 mm entrance pupil** 下定义和验证：

1. 标准眼模型角膜球差：`C4^0 ≈ +0.258 µm`；
2. IOL 前表面参考面的实际光束 footprint：`5.15 ± 0.10 mm`；
3. WFS/RAD/HOA carrier 的 `SA_base`；
4. actual carrier 与 `ZERO_HOA(P)` 的差分，以及 `Q(P)` 求解。

主实验不变：

\[
\boxed{EPD3\ +\ EPD5}
\]

其中 EPD3/EPD5 是**性能评估条件**，不是 carrier 基础球差设计条件。

### 为什么不再用 3 mm 做 `SA_base` 标定

本项目要区分两个问题：

- **设计/标定问题：** IOL 为代表性角膜球差提供多少补偿；
- **性能问题：** 在较小与较大实际瞳孔下，整眼 MTF、PSF、焦深和 HOA 如何表现。

小瞳孔本身会减少高阶像差暴露并增加光学焦深。如果把绝对 `SA_base` 目标也固定在 3 mm，就会把小瞳孔效应混入 carrier 的设计定义，并可能要求不必要地激进的 conic 才达到同一个绝对 `C4^0` 数值。

因此本项目采用：

```text
6 mm  = standard-eye design / SA calibration space
3/5 mm = nominal whole-eye performance space
```

这不增加实验矩阵，只澄清两个瞳孔角色。

---

## 3. 文献依据

### 3.1 Norrby 2007：Liou 角膜球差明确按 6 mm entrance pupil 比较

Norrby, Piers, Campbell & van der Mooren 在 *Applied Optics* 2007 的原始论文中比较多种模型角膜。Liou 两面角膜参数为：

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

论文表注明确说明：对已知 Q 的模型，`C4^0` 按 **6 mm entrance pupil** 计算以便比较。

原始来源：

S. Norrby, P. Piers, C. Campbell, M. van der Mooren. *Model eyes for evaluation of intraocular lenses*. Applied Optics. 2007;46(26):6595–6605. DOI: `10.1364/AO.46.006595`.

### 3.2 非球面 IOL 的标称负球差也具有明显 pupil dependence

Jeon 等对伪晶状体眼的临床波前研究指出：HOYA NY-60 的原始负球差 `−0.18 µm` 对应约 `5.6 mm` 瞳孔，TECNIS ZCB00 的 `−0.27 µm` 对应约 `6.1 mm` 瞳孔；当瞳孔缩小到约 3.5 mm 时，非球面 IOL 球差补偿效应显著减弱。

原始来源：

S. Jeon et al. *Change in efficiency of aspheric intraocular lenses based on pupil diameter*. American Journal of Ophthalmology. 2013;155(3):492–498.e2. DOI: `10.1016/j.ajo.2012.09.024`.

这并不表示本项目的 WFS/RAD surrogate 等同于这些商业 IOL；它只支持一个方法学结论：**绝对球差补偿值必须绑定瞳孔大小，不能把大瞳孔语境的目标不加区分地搬到 3 mm。**

### 3.3 3 mm 仍然是有价值的性能条件

现代 EDOF / enhanced-monofocal bench 研究常比较 3.0 mm 与 4.5 mm 等不同 pupil openings，结果表明 pupil size 会明显改变 through-focus energy distribution 和远/中距离表现。因此本项目继续保留 EPD3，同时用 EPD5 暴露更明显的 pupil-dependent mechanism。

例：

*Through-Focus Response of Extended Depth of Focus Intraocular Lenses* 使用 3.0 mm 与 4.5 mm pupil openings 比较多种 EDOF/enhanced-monofocal IOL。

本项目不把文献的 4.5 mm 直接复制进主矩阵；已有 EPD5 继续作为较大瞳孔性能条件，避免无必要改动 72-config design。

---

## 4. `STD_IOL_EYE_2024` 的冻结角色

`STD_IOL_EYE_2024` 只服务于：

- 标准角膜球差 reference；
- carrier `SA_base` 定义；
- actual-power `Q(P)` 求解；
- `ZERO_HOA(P)` 差分；
- 后续 surrogate 的基础校准。

它**不是** LB/ATC 主研究眼，不进入 72-config nominal analysis matrix。

### 4.1 固定光学条件

正式 standard-eye calibration state：

| 项目 | 冻结值 |
| --- | ---: |
| entrance pupil diameter | `6.000 mm` |
| wavelength | `≈546 nm` |
| field | `0°` |
| surrounding medium | `n=1.336` |
| corneal C40 target | `+0.258 ±0.005 µm @ 6 mm` |
| IOL-plane real-ray footprint | `5.15 ±0.10 mm @ 6 mm` |

正式 `.zos` 保存状态也使用 `EPD=6.0 mm`。不再保存为 3 mm 后通过临时切换进行 carrier calibration。

---

## 5. Zemax 工程处方

### 5.1 表面顺序

除 OBJECT 外，模板使用四个表面：

| Surface | Comment | Radius / Q | Thickness to next | Medium after |
| ---: | --- | --- | --- | --- |
| 1 | `STD_CORNEA_ANT` | `R=+7.77 mm, Q=-0.18` | `0.500 mm` | cornea `n=1.376 @ 546 nm` |
| 2 | `STD_CORNEA_POST` | `R=+6.40 mm, Q=-0.60` | 见 5.2 | aqueous `n=1.336 @ 546 nm` |
| 3 | `IOL_ANT_REFERENCE` | plane | 到 IMAGE 的固定参考距离 | aqueous |
| 4 | `IMAGE_REFERENCE` | plane | — | IMAGE |

其他条件：

- OBJECT：infinity；
- Field：`0°`；
- 单色：`546 nm`；
- system aperture type：Entrance Pupil Diameter；
- 文件保存 EPD：`6.0 mm`；
- STOP：Surface 1（前角膜）；
- IMAGE：平面固定参考面。

### 5.2 IOL reference plane 的工程起点

URD/TDD 冻结的是 `5.15 ± 0.10 mm` real-ray footprint，并没有事先冻结标准眼 IOL 的轴向距离。

因此实现使用可重算的 paraxial seed：

1. 6 mm entrance pupil 上缘 `y0=3.0 mm`；
2. reduced-angle paraxial trace 通过 Liou 两面角膜；
3. 求后角膜之后的距离 `d`，使 IOL reference plane 上半径为 `5.15/2=2.575 mm`。

解析起点约：

`d ≈ 3.92355 mm`

该距离只是工程 seed，**不是科学 oracle**。

正式验收只认 OpticStudio real-ray footprint：

`5.15 ± 0.10 mm`。

若实机 real-ray 显示 seed 有偏差，Codex 可在不改变 5.15 mm target 的前提下，将实现层距离改成确定性 real-ray solve 的结果；必须回传准确距离与 commit，不得为了保留 `3.92355 mm` 而牺牲 footprint target。

### 5.3 IMAGE reference

模板暂以正常眼尺度提供稳定固定 IMAGE reference；它不把 `STD_IOL_EYE_2024` 声称为完整 Liou–Brennan 解剖眼。

角膜自身 `C4^0` 验证可在只读验证过程中临时使用角膜 paraxial focus / 一致的 reference sphere，测完恢复正式模型状态且不保存。这样角膜 oracle 不被 carrier 的固定 IMAGE reference 污染。

---

## 6. 6 mm 验证规则

### 6.1 角膜 C40

在 `EPD=6.0 mm`、`λ≈546 nm`、field 0° 下：

1. 使用已有 Zernike Standard acquisition contract；
2. 在适合角膜单独球差比较的焦面/reference sphere 上读取 OSA/ANSI `Z11 = C4^0`；
3. 要求：

`+0.258 ± 0.005 µm`。

不得通过任意调整 Liou `R/Q` 来追测试数值。若失败，先检查：

- entrance pupil 是否确为 6 mm；
- Zernike normalization/reference；
- 波长；
- surface radius sign / conic / material；
- image/reference sphere。

只有确认不是 Zemax 定义映射问题后，才回 Web 端重新审查科学定义。

### 6.2 IOL footprint

同一 6 mm standard-eye geometry 下，使用 ZOS-API normalized unpolarized real batch ray trace：

- field = 0；
- pupil coordinate `Py=-1` 与 `Py=+1`；
- trace endpoint = `IOL_ANT_REFERENCE`；
- 无 vignette / ray error；
- footprint = 两条边缘光线在该面的 y-intercept 差。

要求：

`5.15 ± 0.10 mm`。

该数值是 IOL plane 的实际 beam footprint，不是 IOL optical diameter。

---

## 7. `ZERO_HOA_PARAXIAL_REFERENCE`

### 7.1 不建立固定 +20 D 文件

`ZERO_HOA_PARAXIAL_REFERENCE` 是 **power-specific numerical reference**。

对每个实际 carrier `P_ijk`，TASK-007 必须生成对应：

`ZERO_HOA(P_ijk)`。

005C 不创建一个固定 +20 D 文件让所有 carrier 共用。

### 7.2 身份匹配

`ZeroHoaReferenceRecord` 必须与 actual carrier 保持：

- carrier ID；
- paraxial power；
- anterior/posterior radius metadata；
- center thickness metadata；
- material metadata；
- IOL reference position。

其 optical model 标记为：

`ideal_paraxial_zero_hoa`

实际 reference 只保留指定一阶 power，不引入 aspheric/HOA/residual。

### 7.3 标准眼 SA 定义

TASK-007 对任一 carrier：

`SA_IOL_STD(P,Q) = C4_eye_STD(actual carrier) - C4_eye_STD(ZERO_HOA(P))`

两次分析必须完全共享：

- 同一 `STD_IOL_EYE_2024` locked file/hash；
- `EPD=6.0 mm`；
- `λ≈546 nm`；
- field/reference axis；
- carrier power identity；
- IOL reference plane。

平台目标：

- WFS：`−0.20 ±0.01 µm @ 6 mm`；
- RAD：`−0.27 ±0.01 µm @ 6 mm`；
- HOA：`0.00 ±0.01 µm @ 6 mm`。

这些仍是项目内部 surrogate 目标，不声称是商业 IOL 制造参数。

---

## 8. 与主实验 EPD3/EPD5 的关系

标准眼 6 mm calibration **不会新增 nominal 配置**。

主实验仍是：

`2 bases × 3 corneas × 3 platforms × 2 optic states × 2 pupils = 72`

pupils 仍为：

- `EPD3`；
- `EPD5`。

解释规则：

- EPD3：较小明视瞳孔性能，允许其天然较长焦深真实存在；
- EPD5：较大瞳孔性能，更充分暴露角膜/IOL 球差与 residual 机制；
- 两者均读取已经在 6 mm standard-eye calibration 下冻结的 carrier；
- 不允许根据 EPD3/EPD5 主结果重新求 `Q(P)` 或改变 carrier `SA_base`。

---

## 9. 代码修订范围

文档冻结后，Web 代码只做以下必要修改：

- `src/whole_eye_mvp/standard_eye.py`
  - saved calibration aperture：`3.0 → 6.0 mm`；
  - 去除“验证后恢复 3 mm”的旧语义；
  - C40 / footprint 继续在 6 mm 验证；
  - `ZeroHoaReferenceRecord` 明确携带/验证 6 mm calibration identity。
- `tests/unit/test_standard_eye.py`
  - standard-eye aperture oracle 改为 6 mm；
  - 增加 EPD3/EPD5 与 standard-eye calibration 解耦测试。
- `tests/zemax/test_zos_standard_eye.py`
  - saved/reloaded `.zos` 必须读取 EPD=6 mm；
  - validate-only 前后 hash exact。
- `scripts/build_task_005c_standard_eye.py`
  - 输出/validation payload 使用 6 mm calibration semantics。
- TASK-007 carrier code只在需要时补 calibration identity；005C 不提前实现 18 carrier solve。

不修改：

- 005B 两个 base locks；
- A0/B/C 科学定义；
- B0 EPD3/EPD5 selection；
- main 72 manifest；
- residual policy；
- TDD-999。

---

## 10. Codex / OpticStudio 实机验证包

代码修订完成后，在同一 branch 运行：

```powershell
uv sync
uv run pytest tests/unit/test_standard_eye.py -vv
uv run pytest tests/unit
uv run ruff check .
uv run python -m compileall -q src tests scripts
uv lock --check

uv run pytest tests/zemax/test_zos_standard_eye.py -vv
uv run python scripts/run_zemax_gates.py

uv run python scripts/build_task_005c_standard_eye.py --project-dir project
uv run python scripts/build_task_005c_standard_eye.py --project-dir project --validate-only
```

必须回传：

- branch / commit；
- OpticStudio version/license；
- unit / Zemax gate 数量；
- `STD_IOL_EYE_2024.zos` SHA-256；
- validation CSV SHA-256；
- saved/reloaded EPD=`6.000 mm`；
- wavelength ≈`546 nm`；
- corneal `C4^0=+0.258±0.005 µm @ 6 mm`；
- IOL footprint=`5.15±0.10 mm @ 6 mm`；
- cornea `n=1.376`、surrounding medium `n=1.336`；
- exact posterior-cornea→IOL-reference distance；
- validate-only 前后 `.zos` hash unchanged；
- stderr/native warning。

---

## 11. STOP 条件

Codex 必须停止并回 Web，如果出现以下任一情况：

1. 必须把 EPD 改回 3 mm 才能让 `C4^0` 或 `SA_base` 通过；
2. 必须改变 `+0.258 / −0.20 / −0.27 / 0.00 µm` 科学 target；
3. 必须改变主实验 EPD3/EPD5；
4. Liou 角膜处方在确认 Zernike/reference mapping 正确后仍不能满足 oracle；
5. footprint target 与合理 real-ray geometry 无法同时满足；
6. 需要改变 lock boundary 或 TDD-999 才能继续。

允许的本地最小适配仅包括：

- ZOS-API member / enum 差异；
- batch ray trace 调用方式；
- Zernike analysis settings 映射；
- reference-plane 临时测量实现；
- 为满足**既定 5.15 mm footprint target**而把 paraxial seed 改成确定性 real-ray solved distance。

---

## 12. 完成条件

TASK-005C 只有在以下全部满足后才完成：

- [x] URD v1.4 已冻结 6 mm standard-eye calibration；
- [x] TDD v1.3 已冻结对应 oracle；
- [x] RMD v1.3 已同步执行条件；
- [ ] Web 代码/测试全部改为 6 mm；
- [ ] unit / Ruff / compileall / uv lock check PASS；
- [ ] real OpticStudio 005C gate PASS；
- [ ] formal `.zos` 与 validation CSV 生成并 hash；
- [ ] validate-only 独立进程回载且 hash unchanged；
- [ ] Web 独立审核本地证据；
- [ ] PR #22 ready for review → squash merge。

完成 005C 后才进入下一科学资产阶段。