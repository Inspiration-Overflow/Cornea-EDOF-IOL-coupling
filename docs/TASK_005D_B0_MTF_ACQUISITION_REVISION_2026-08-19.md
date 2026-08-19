# TASK-005D — B0 MTF 采集方法修订

日期：2026-08-19  
状态：**Phase B.1 实机 PASS；生产 `Samp=3`、5 cycles/mm 已冻结；等待完整五候选 B0 scan。**

## 1. 决定

TASK-005D 的 B0 五候选真实扫描不再以 Huygens MTF Analysis / `AS_HuygensMtf` 作为生产采集路径。

B0 生产采集改为：

```text
OpticStudio Merit Function Editor
→ MTFA diffraction MTF operand
→ Grid = 0 fast sparse single-frequency algorithm
→ Samp = 3
→ 0, 5, 10, ..., 50 cycles/mm
→ trapezoidal integration
→ Q_lock
```

本修订只替换 **B0 MTF acquisition primitive**。A/B/C 光学处方、REF_MONO、B0 defocus grid、EPD、Q_lock 定义、distance-retention gates 和 `rank_b0_candidates()` 均不改变。

## 2. 修订原因

Phase B 首次实机运行在 A0 的候选特异 REF_MONO 已成功建立后，首次创建 Huygens MTF analysis settings 类型时触发：

```text
Failed to create Python type for ZemaxUI.ZOSAPI.Analysis.Mtf.AS_HuygensMtf
...
System.IO.FileLoadException:
A procedure imported by 'ZemaxEngine.dll' could not be loaded.
```

该失败与 TASK-005C 曾遇到的 `AS_ZernikeStandardCoefficients` 属于同类 Python.NET / ZemaxEngine settings-type 问题。继续重试 `AS_HuygensMtf` 没有工程价值。

同时，B0 冻结场景本身是：

```text
555 nm
field 0
coaxial
rotationally symmetric
no decentration / tilt
A0 or continuous Even-Asphere B cornea
simple symmetric REF_MONO
```

本任务只需要候选间稳定的相对 `Q_lock`、distance retention 和 DOF 排序，不需要把 Huygens MTF Analysis 作为每个 defocus plane 的默认生产方法。

## 3. 官方算法依据

Ansys OpticStudio User Guide 对 `MTFA` 的定义：

- `MTFA` 为弧矢与子午 diffraction MTF 的平均值；
- `Grid=0` 是推荐的快速、稀疏采样单频算法；
- 该算法与完整 MTF Analysis 不同，因为只计算单一空间频率，通常快得多；
- `Grid=1` 才使用与 MTF Analysis 对应的网格算法；
- 当 MTF 合理（官方举例 >5%）时，`Grid=0` 通常比 grid algorithm 更快；
- 对 MTFA/MTFS/MTFT，`Data Type=0` 返回 modulation amplitude。

OpticStudio 对 FFT Through Focus MTF 也说明其快速算法与 `MTFA, Grid=0` 使用相同算法族。

因此本修订不是自定义 MTF 算法，也不是用几何 MTF 替代 diffraction MTF；而是使用 OpticStudio 自带的快速 diffraction MTF operand。

## 4. 冻结的 B0 光学条件不变

继续使用：

```text
λ = 555 nm
EPD = 3 mm + 5 mm
defocus = +0.50 → -3.50 D
step = 0.25 D
17 planes
field = 0
REF_MONO candidate-specific
retina / IOL / ELP fixed during through-focus scan
```

0 D 继续使用模型保存的 nominal infinity OBJECT 状态。非零 defocus 只临时改变 OBJECT vergence。

## 5. 新的 Q_lock 采集定义

B0 指标仍为：

\[
Q_{lock,p}(F)=\frac{1}{50}\int_0^{50}MTF(f,F)\,df.
\]

生产频率网格：

```text
0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50 cycles/mm
```

每个 defocus plane 一次性在 MFE 插入相邻 MTFA operands，统一设置：

```text
operand = MTFA
Samp = 3
Wave = 1
Field = 1
Grid = 0
Data Type = 0  # modulation amplitude
Freq = 0..50 cycles/mm, step 5
```

所有临时 MTFA operands 必须：

1. 在计算前记录原 MFE row count；
2. 插入后验证 operand type / 参数；
3. 一次 `CalculateMeritFunction()` 计算同一 plane 的全部 11 个频率；
4. 读取每个 operand 的 `Value`；
5. `finally` 删除临时 operands；
6. 验证 MFE row count 恢复；
7. 不保存 lens，仅恢复 OBJECT thickness。

不得增加 GETMTF / FFT-MTF Analysis / Huygens MTF Analysis fallback。失败时 fail closed。

## 6. 频率离散与积分

在 0–50 cycles/mm 的 5 cycles/mm 网格上直接使用梯形积分：

\[
Q_{lock}=\frac{1}{50}\sum_i \frac{MTF_i+MTF_{i+1}}{2}(f_{i+1}-f_i).
\]

这一层为纯 Python 数学，不调用 OpticStudio。

### 6.1 Phase B.1 频率步长 sanity check

代表状态：

```text
A0
B0.20
EPD3 + EPD5
0 D / -1.5 D
```

比较：

```text
5 cycles/mm step
vs
2.5 cycles/mm step
```

实测最大绝对 `Q_lock` 差异：

```text
0.00492149
```

据此生产固定 5 cycles/mm，不继续加密。该检查不增加新的科学 gate，不用于回调角膜处方。

## 7. Sampling 实机检查与冻结

Phase B.1 在同一组代表状态比较：

```text
Samp = 2 / 3 / 4
```

实测最大绝对 `Q_lock` 差异：

```text
Samp 2 → 3 = 0.00221683
Samp 3 → 4 = 0.00067564
```

项目据此冻结：

```text
production Samp = 3
```

该决定的角色是工程参数冻结，不把上述实测差异定义成新的自动 convergence threshold，也不要求对 204 个完整状态重复 sampling study。

权威 Phase B.1 记录：

```text
docs/TASK_005D_PHASE_B1_MTFA_PROBE_REVIEW_2026-08-19.md
```

既有 Phase B.1 无需重跑。本次一致性修订没有改变实机已验证的 MFE MTFA primitive、Q_lock 数学或光学条件。

## 8. B0 排序与人工 morphology 审核

继续复用既有 `rank_b0_candidates()`：

```text
A0 EPD3 peak → 50% Q_lock threshold
A0 EPD5 peak → 50% Q_lock threshold
B distance retention gate:
  EPD3 >= 80%
  EPD5 >= 70%
```

符合 gate 的候选按既有顺序比较：

1. EPD3 absolute-threshold DOF；
2. EPD5 absolute-threshold DOF；
3. EPD3 distance retention；
4. |ΔC40|。

完整实机 scan 首先固定：

```text
morphology_review_pending = true
selection_locked = false
```

此时的 recommendation 只是**未经过人工形态审核的初步 deterministic recommendation**。

五条真实曲线生成后，用户必须对五候选分别给出 morphology decision。明显稳定的“双峰 + 深谷”候选标记 `morphology_reject=true` 并写理由；随后软件使用原始实机曲线重新调用同一 `rank_b0_candidates()`，形成新的 reviewed scan hash 和 recommendation。该 review/re-rank/lock 步骤为纯 Python，不重新调用 OpticStudio。

最终 B0 lock 必须与以下内容一起保存：

- 五候选 morphology decisions；
- reviewed rank；
- source scan hash；
- reviewed scan hash；
- recommendation；
- 最终 candidate；
- selection reason；
- override 标记。

## 9. Huygens 的范围

本修订只处理 TASK-005D/B0 的 `AS_HuygensMtf` production failure。

因此：

```text
B0 selection → MFE MTFA Grid=0
```

**不由本文件重新定义 TASK-009/Run72 的主实验 acquisition。** 主实验继续服从当前 TDD 的：

```text
Huygens PSF
→ deterministic FFT
→ complex OTF
→ radial MTF / MTFa / VSOTF
```

后续三代表配置的 sampling 与独立 MTF cross-check 仍在 TASK-009 处理。一次 `AS_HuygensMtf` settings-type failure 不能外推为 `HuygensPsfRunner` 不可用。

## 10. 旧 Huygens / PSF→Python FFT 备用路线

Phase B STOP 后曾实现 `Huygens PSF → Python FFT → MTF` 作为 TASK-005D 的临时备用恢复路线。经设计复核，该路线不作为 B0 production fallback：OpticStudio 已提供更简单的 MFE `MTFA` diffraction-MTF operand，没有必要在 B0 锁定任务中自行重建 MTF pipeline。

本 PR 中仅服务 TASK-005D fallback 的以下旧路线代码已删除：

```text
scripts/probe_task_005d_huygens_psf.py
src/whole_eye_mvp/zos/huygens_mtf.py
src/whole_eye_mvp/zos/huygens_psf_mtf.py
tests/unit/test_zos_huygens_mtf.py
tests/unit/test_zos_huygens_psf_mtf.py
```

通用 `HuygensPsfRunner` 基础设施保留给 TASK-009 主实验/代表配置验证；它不属于 B0 production path。

## 11. 版本与 provenance

原 `CORNEA_LOCK_B0_555_v1` 对应首次 Huygens-MTF 设计，并已有明确 Phase B STOP 证据。

当前 production acquisition：

```text
CORNEA_LOCK_B0_555_v2
Samp = 3
frequency step = 5 cycles/mm
```

该变更是角膜冻结分析协议版本更新，不改变 `MVP_2026_v2` 的眼模型 scientific baseline。正式 B0 尚未锁定，因此无需迁移既有 B0 lock。

完整五候选 scan 现在还必须保存最小 provenance：

- clean Git commit；
- baseline ID；
- OpticStudio installation path/label；
- Phase B.1 evidence summary；
- standard eye、reference cornea、A0/B candidate 与生成 REF_MONO 的 SHA-256。

## 12. 当前下一步

允许执行：

```text
scripts/run_task_005d_b0_scan.py
```

full scan 会先验证 Phase B.1 evidence 与当前 v2 settings 完全一致；缺失或漂移则 fail closed。

完成五候选 scan 后：

1. 审核五条 EPD3/EPD5 `Q_lock` 曲线；
2. 为每个候选给出 morphology decision；
3. 使用 `scripts/review_task_005d_b0.py` 重新排序；
4. 用户确认 recommendation，或明确写 override reason；
5. 生成不可变 `B0_LOCK`；
6. B0 lock 之后才允许进入正式 carrier 科学阶段。

## 参考

- Ansys OpticStudio User Guide, **MTF Data** — MTFA/MTFS/MTFT operands and `Grid=0` fast sparse algorithm.
- Ansys OpticStudio User Guide, **FFT Through Focus MTF** — fast calculation uses the same algorithm family as `MTFA, Grid=0`.
- `docs/TASK_005D_PHASE_B_STOP_2026-08-19.md`.
- `docs/TASK_005D_PHASE_B1_MTFA_PROBE_REVIEW_2026-08-19.md`.
- `docs/TASK_005D_CORNEA_LOCK_ASSETS.md`.
