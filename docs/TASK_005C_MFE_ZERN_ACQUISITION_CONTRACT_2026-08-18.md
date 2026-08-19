# TASK-005C — MFE ZERN 自动获取契约与实机等价性证据

> 状态：**docs-first implementation contract**。本文件记录 2026-08-18 人工 GUI 科学验证与随后 MFE `ZERN` 实机 spike 的结果，并冻结 TASK-005C 后续 production 实现应采用的最小 Zernike 获取路径。
>
> 本文件不修改 scientific baseline；`MVP_2026_v2`、Liou 处方、6 mm 校准孔径、546 nm、`C4^0=+0.258±0.005 µm`、IOL footprint、WFS/RAD/HOA SA 目标、EPD3/EPD5 主矩阵和 TDD-999 均保持不变。

## 1. 结论摘要

TASK-005C 目前已经把两个问题分开并分别解决：

1. **科学模型 / reference convention：PASS**
   - corrected Liou standard-eye scaffold；
   - `EPD=6.0 mm`；
   - `λ=0.546 µm`；
   - `IOL_ANT_REFERENCE` 后连续 `n≈1.336`；
   - OpticStudio Quick Focus 使用 `Wavefront Error`、`UseCentroid=False`；
   - GUI Zernike Standard Coefficients 在 best-focus diagnostic C 中得到：
     - `Z4 = +0.00434634 waves`；
     - `Z11 = +0.47360558 waves`；
     - `Z37 = +0.00025905 waves`；
     - `C4^0 = Z11 × 0.546 = +0.25858864668 µm`；
   - 因而满足冻结 scientific gate：`+0.258±0.005 µm`。

2. **自动获取路径：MFE ZERN 等价性 PASS**
   - 不创建 `Zernike Standard Coefficients` analysis；
   - 不访问 `AS_ZernikeStandardCoefficients` / `IAS_ZernikeStandardCoefficients`；
   - 使用 Merit Function Editor 的两个相邻 `ZERN` operands；
   - `Term=11` 与 `Term=37` 共同使 Standard Zernike fit 的最高阶为 37；
   - A/B/C 三个 GUI oracle 均被 MFE `ZERN` 复现，差值远小于 `1e-5 waves`。

因此 production TASK-005C **不得继续依赖当前会触发 Python.NET/ZemaxEngine 类型加载故障的 Zernike analysis settings 路径**；MVP production acquisition 应改用本文件冻结的 MFE `ZERN` 路径。

---

## 2. 实机环境与 Git provenance

验证环境：

```text
branch = feat/task-005c-standard-eye
head = 43a1659428775d6d7d35ae58e4514efb6d960e9d
OpticStudio = 2026 R1.00 / Premium
ZOS-API license = PremiumEdition
ZOS-API mode = Server
Python = 3.12.9
```

PR：

```text
https://github.com/Inspiration-Overflow/Cornea-EDOF-IOL-coupling/pull/22
```

在本文件建立时，PR #22 必须继续保持 Draft，直到 production code 按本契约实现并完成正式 TASK-005C 实机验证。

---

## 3. GUI 科学 oracle

三个 diagnostic `.zmx` 使用同一套 GUI Zernike Standard Coefficients 设置：

```text
Sampling = 32 × 32
Maximum Term = 37
Wavelength = 1
Field = 1
Ref OPD To Vertex = OFF
Surface = Image
Sx = 0
Sy = 0
Sr = 1
Epsilon = 0
OPD reference = chief ray
```

### 3.1 DIAG-A — fixed reference

GUI 输出：

```text
Z4  = -31.04766552 waves
Z11 =  +0.22875730 waves
Z37 =  +0.00007592 waves
```

A 是固定 anterior-cornea→IMAGE = 23.950 mm 的诊断参考面，不是 C40 scientific acceptance focus。

### 3.2 DIAG-B — paraxial diagnostic focus

GUI 输出：

```text
Z4  = +1.80814115 waves
Z11 = +0.48911744 waves
Z37 = +0.00027315 waves
```

B 是连续 `n≈1.336` 条件下的项目一阶旁轴诊断焦面，不是正式 best-focus definition。

GUI 测得的 `TASK005C_B_PARAXIAL_FOCUS_2.zmx` 与原始 B `.zmx` / 初始 B diagnostic 文件实机确认字节相同，因此本轮 B provenance 已解除歧义。

### 3.3 DIAG-C — Wavefront Error best focus

Quick Focus：

```text
criterion = Wavefront Error
UseCentroid = False
IOL_REF→IMAGE = 26.600571884912345 mm
```

GUI 输出：

```text
Z4  = +0.00434634 waves
Z11 = +0.47360558 waves
Z37 = +0.00025905 waves
```

换算：

```text
C40 = 0.47360558 × 0.546 µm
    = 0.25858864668 µm
```

因此：

```text
scientific C40 gate = PASS
```

这证明当前 Liou/Norrby `+0.258 µm` 可以继续作为 OpticStudio direct scientific gate；不需要降级成仅 provenance anchor，也不得为了适配旧 API 失败去调 Liou R/Q 或放宽容差。

---

## 4. MFE ZERN production acquisition contract

### 4.1 禁止路径

TASK-005C production C40 acquisition 不再使用：

```text
New_ZernikeStandardCoefficients()
AS_ZernikeStandardCoefficients
IAS_ZernikeStandardCoefficients
```

原因不是科学定义，而是该工作站上该 settings type 路径出现过可复现的 Python.NET / `ZemaxEngine.dll` native type-loading failure。

GUI Zernike Standard Coefficients 仍可作为人工/独立 cross-check，不作为 production API 路径。

### 4.2 Production MFE 设置

在 loaded lens 的 Merit Function Editor 中建立两个**相邻**临时 `ZERN` operands：

```text
row N:
  Type = ZERN
  Term = 11
  Wave = 1
  Samp = 1
  Field = 1
  Zernike Type = 1
  Epsilon = 0
  Vertex = 0

row N+1:
  Type = ZERN
  Term = 37
  Wave = 1
  Samp = 1
  Field = 1
  Zernike Type = 1
  Epsilon = 0
  Vertex = 0
```

项目冻结语义：

```text
Samp = 1       -> 32×32
Zernike Type=1 -> Standard
Vertex = 0     -> chief-ray OPD reference / Ref OPD To Vertex OFF
Wave = 1
Field = 1
Maximum fit term = 37, established by adjacent Term 11 + Term 37 ZERN operands
```

### 4.3 ZOS-API path verified on 2026 R1

实机 spike 已验证可用路径：

```text
MFE.InsertNewOperandAt(...)
MFE.GetOperandAt(...)
operand.ChangeType(MeritOperandType.ZERN)
set parameter cells Term/Wave/Samp/Field/Type/Epsilon/Vertex
MFE.CalculateMeritFunction()
read operand.Value
```

OpticStudio 2026 R1 的方法名是 `InsertNewOperandAt`。不得在 production 中使用未经该版本验证的 `InsertOperandAt`。

`GetOperandValue` 在该版本 API surface 中存在，但本轮未作为 production-equivalence evidence 使用；MVP 应优先复用已实机通过的“临时 MFE rows + CalculateMeritFunction + operand.Value”路径，不为追求更短代码切换到未经本轮实证的另一条 API。

### 4.4 Mutation / persistence rule

MFE ZERN rows 是**临时 acquisition state**：

- 不得保存进正式 lens artifact；
- C40 获取前后 optical lens file SHA-256 必须保持不变；
- acquisition 完成后清理临时 operands，或直接在不保存的 disposable/fresh session 中关闭 lens；
- production validation 不得因 MFE 获取过程改变 surface geometry、materials、EPD、wavelength、IMAGE 保存位置或 carrier state。

---

## 5. 实机等价性结果

### DIAG-C — blocking oracle

```text
GUI Z11 = 0.47360558
MFE Z11 = 0.4736063027853602
|delta| = 7.23e-07 waves  -> PASS

GUI Z37 = 0.00025905
MFE Z37 = 0.00026011052367169805
|delta| = 1.06e-06 waves  -> PASS
```

C `.zmx` SHA-256 before/after：

```text
a39d3ad8d20964120d578aaf451d6fe36d6508933ad001931860ebce7ecfaf80
```

完全不变。

### DIAG-A cross-check

```text
GUI Z11 = 0.22875730
MFE Z11 = 0.2287573036054908
|delta| = 3.61e-09 waves

GUI Z37 = 0.00007592
MFE Z37 = 0.00007592431802708115
|delta| = 4.32e-09 waves
```

PASS。

### DIAG-B cross-check

```text
GUI Z11 = 0.48911744
MFE Z11 = 0.4891174420997102
|delta| = 2.10e-09 waves

GUI Z37 = 0.00027315
MFE Z37 = 0.0002731506714183534
|delta| = 6.71e-10 waves
```

PASS。

因此：

```text
MFE_ZERN_EQUIVALENCE = PASS
```

MVP contract-test tolerance 冻结为：

```text
|MFE Z11 - GUI Z11| <= 1e-5 waves
|MFE Z37 - GUI Z37| <= 1e-5 waves
```

这里的 `1e-5 waves` 是 acquisition-equivalence engineering tolerance，不替代 scientific `C4^0 ±0.005 µm` gate。

---

## 6. Native warning handling

MFE spike 的成功和失败尝试在 Python 进程退出阶段都可能输出：

```text
*** FRU__delta_init(): Attempt to start when running!
```

本轮特征：

- 出现在结果已经成功读取之后 / process exit 阶段；
- 无 `FileLoadException`；
- 无 `ZemaxEngine.dll` imported-procedure failure；
- lens hash 不变；
- residual OpticStudio/Zemax process count = 0。

因此 production 不能把这条单独的 exit-time stderr 文本等同于 acquisition failure；但必须完整记录 native stderr/warnings 作为 provenance。

以下情况仍为 hard STOP / failure：

- ZERN operand 无法创建或求值；
- 返回非有限数值；
- `FileLoadException` / `ZemaxEngine.dll` type-loading failure；
- process 残留；
- lens hash 被意外修改；
- C40 scientific gate 不通过。

---

## 7. Production implementation requirements

下一轮 production code 修改必须是最小实现：

1. 新增或替换一个可复用的 MFE Standard-Zernike acquisition primitive；
2. TASK-005C C40 改用该 primitive；
3. 保留 Quick Focus `Wavefront Error` best-focus validation；
4. 保留 validation 后恢复 fixed saved IMAGE 的行为；
5. 不调用 Zernike Standard analysis object；
6. unit test 覆盖参数映射和 fail-closed 行为；
7. Zemax integration test 必须在真实 2026 R1 上验证：
   - `C40=+0.258±0.005 µm`；
   - `Z11` acquisition 可用；
   - `medium_index_after_iol_ref≈1.336`；
   - footprint 通过；
   - locked lens hash 在 validate-only 前后不变；
   - 无残留进程；
8. production 实现通过前，PR #22 继续 Draft。

### 7.1 正式 005C 的实施顺序

production 实现后，正式验证必须按以下顺序执行：

```text
candidate build in fresh process
→ fresh-process reload
→ geometry/index/footprint readback
→ Quick Focus(Wavefront Error, UseCentroid=False)
→ MFE ZERN Term11+Term37 acquisition
→ C40 scientific gate
→ restore fixed saved IMAGE state / do not persist acquisition state
→ register formal standard-eye artifact only on PASS
→ write validation CSV only on PASS
→ validate-only reload and verify optical-file hash unchanged
```

如果任一 gate 失败，仍不得产生正式 005C lock。

---

## 8. `.zmx` 文件格式问题

用户已确认 OpticStudio 2026 R1 GUI 推荐使用 `.zmx`，且 diagnostic GUI 工作流已经实际使用 `.zmx`。

但是本文件**不把 `.zos → .zmx` 迁移和 MFE-ZERN acquisition 修复混为同一改动**。文件格式迁移应作为紧随其后的独立 docs-first engineering revision，保留旧 `.zos` hash 作为历史 workstation evidence，再明确 current canonical artifact path/hash。

在该独立修订完成前，不得因为格式迁移问题改变本文件冻结的 ZERN acquisition 语义。

---

## 9. 当前 TASK-005C 状态

截至本文件：

```text
scientific standard-eye C40 definition = PASS
manual GUI C40 validation = PASS
MFE ZERN equivalence spike = PASS
production MFE-ZERN integration = PENDING
formal TASK-005C artifact/validation/lock = NOT YET CREATED
PR #22 = DRAFT / DO NOT MERGE
```

下一步：按本契约实现 production MFE-ZERN acquisition，完成真实 OpticStudio 2026 R1 formal TASK-005C validation；之后再单独进行 `.zmx` canonical artifact 格式修订。