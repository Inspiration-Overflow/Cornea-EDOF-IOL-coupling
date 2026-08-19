# TASK-005D — B0 MTF 采集方法修订

日期：2026-08-19  
状态：**文档与 Web 端代码已按本文实现；等待 Phase B.1 最小 MTFA 实机 probe。**

## 1. 决定

TASK-005D 的 B0 五候选真实扫描不再以 Huygens MTF Analysis / `AS_HuygensMtf` 作为生产采集路径。

B0 生产采集改为：

```text
OpticStudio Merit Function Editor
→ MTFA diffraction MTF operand
→ Grid = 0 fast sparse single-frequency algorithm
→ 0, 5, 10, ..., 50 cycles/mm
→ trapezoidal integration
→ Q_lock
```

本修订只替换 **MTF acquisition primitive**。A/B/C 光学处方、REF_MONO、B0 defocus grid、EPD、Q_lock 定义、distance-retention gates 和 `rank_b0_candidates()` 均不改变。

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

本任务只需要候选间稳定的相对 `Q_lock`、distance retention 和 DOF 排序，不需要把高成本 Huygens Analysis 作为每个 defocus plane 的默认生产方法。

## 3. 官方算法依据

Ansys OpticStudio User Guide 对 `MTFA` 的定义：

- `MTFA` 为弧矢与子午 diffraction MTF 的平均值；
- `Grid=0` 是推荐的快速、稀疏采样单频算法；
- 该算法与完整 MTF Analysis 不同，因为只计算单一空间频率，通常快得多；
- `Grid=1` 才使用与 MTF Analysis 对应的网格算法；
- 当 MTF 合理（官方举例 >5%）时，`Grid=0` 通常比 grid algorithm 更快；
- 对 MTFA/MTFS/MTFT，`Data Type=0` 返回 modulation amplitude。

OpticStudio 对 FFT Through Focus MTF 也明确说明，其快速算法与 `MTFA, Grid=0` 使用同一路径。

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
Wave = 1
Field = 1
Grid = 0
Data Type = 0  # modulation amplitude
Freq = 0..50 cycles/mm, step 5
```

`Samp` 使用固定生产采样级别，但在第一次正式长扫描前只做一次最小 sampling convergence probe 后冻结。遵循 OpticStudio 官方建议：从较低 sampling 增加，直到结果变化小于项目需要的精度；不追求对 B0 排序没有意义的极端精度。

所有临时 MTFA operands 必须：

1. 在计算前记录原 MFE row count；
2. 插入后验证 operand type / 参数；
3. 一次 `CalculateMeritFunction()` 计算同一 plane 的全部 11 个频率；
4. 读取每个 operand 的 `Value`；
5. `finally` 删除临时 operands；
6. 验证 MFE row count 恢复；
7. 不保存 lens，仅恢复 OBJECT thickness。

不得增加 GETMTF / FFT-MTF Analysis / Huygens Analysis fallback。失败时 fail closed。

## 6. 频率离散与积分

在 0–50 cycles/mm 的 5 cycles/mm 网格上直接使用梯形积分：

\[
Q_{lock}=\frac{1}{50}\sum_i \frac{MTF_i+MTF_{i+1}}{2}(f_{i+1}-f_i).
\]

这一层为纯 Python 数学，不调用 OpticStudio。

### 6.1 最小频率步长 sanity check

只在两个代表状态检查一次：

```text
A0
B0.20
```

比较：

```text
5 cycles/mm step
vs
2.5 cycles/mm step
```

目的仅确认 `Q_lock` 和 B0 选择结论对频率离散不敏感。若差异对候选排序无实质影响，则生产固定 5 cycles/mm，不继续加密。

该检查不增加新的科学 gate，不用于回调角膜处方。

## 7. Sampling 最小收敛检查

同样只在少数代表 plane 做一次 MTFA `Samp` 收敛检查，不对 204 个状态重复做 sampling study。

原则：

- 使用 OpticStudio MTFA 的离散 sampling index；
- 比较相邻 sampling level 的 `Q_lock`；
- 达到足够稳定后冻结最小可接受 sampling；
- 如果 MTFA 返回 0 或明显非物理值，视为 sampling 不足或 runtime failure，不自动改科学参数。

最终实际冻结的 `Samp` 数值必须由一次真实工作站 probe 记录进 Phase B 证据文档，再运行全量 scan。

## 8. B0 排序规则完全不变

继续复用既有 `rank_b0_candidates()`：

```text
A0 EPD3 peak → 50% Q_lock threshold
A0 EPD5 peak → 50% Q_lock threshold
B distance retention gate:
  EPD3 >= 80%
  EPD5 >= 70%
```

符合 gate 的候选继续按既有顺序比较：

1. EPD3 absolute-threshold DOF；
2. EPD5 absolute-threshold DOF；
3. EPD3 distance retention；
4. |ΔC40|。

Morphology 仍由人工审核：

```text
morphology_review_pending = true
selection_locked = false
```

脚本不得自动创建正式 B0 lock。

## 9. Huygens 的新角色

Huygens 不再作为 B0 或未来 Run72 的默认生产采集器。

保留用途：在后续 3 个代表性正式配置上做独立 cross-check，用来验证主生产 FFT/diffraction-MTF 路径没有对本项目产生有意义的偏差。

也就是说：

```text
B0 selection        → MTFA Grid=0
main production MTF → FFT/diffraction-MTF path
representative QA   → Huygens cross-check only
```

这与 RMD 原本要求的“代表配置独立 MTF cross-check”一致，同时显著减少 ZOS-API settings-type 暴露和运行时间。

## 10. 旧 Huygens / PSF→Python FFT 路线

Phase B STOP 后曾实现 `Huygens PSF → Python FFT → MTF` 作为临时备用路线。经本次设计复核，该路线不再作为 TASK-005D 的目标生产实现：OpticStudio 已提供更简单的 MFE `MTFA` diffraction-MTF operand，没有必要在本任务中自行重建 MTF pipeline。

本 PR 中仅服务 TASK-005D 的以下旧路线代码现已删除：

```text
scripts/probe_task_005d_huygens_psf.py
src/whole_eye_mvp/zos/huygens_mtf.py
src/whole_eye_mvp/zos/huygens_psf_mtf.py
tests/unit/test_zos_huygens_mtf.py
tests/unit/test_zos_huygens_psf_mtf.py
```

通用 `HuygensPsfRunner` 基础设施保留，供后续真正需要代表配置 Huygens cross-check 时独立使用；它不属于 B0 production path。

## 11. 版本与 provenance

原 `CORNEA_LOCK_B0_555_v1` 对应首次 Huygens-MTF 设计，并已有明确 Phase B STOP 证据。

新的 MTFA production acquisition 记录为：

```text
CORNEA_LOCK_B0_555_v2
```

该变更是角膜冻结分析协议版本更新，不改变 `MVP_2026_v2` 的眼模型 scientific baseline。正式 B0 尚未锁定，因此无需迁移既有 B0 lock。

Web 端已完成：

```text
MFE MTFA primitive
Q_lock trapezoidal integration
v2 settings/provenance
B0 acquisition switch
ranking provenance switch
unit tests
Phase B.1 probe script
full Phase B v2 output isolation
obsolete TASK-005D Huygens fallback cleanup
```

## 12. 下一步

当前只剩实机 Phase B.1：

1. 同步当前 branch；
2. 运行 `scripts/probe_task_005d_mtfa.py`；
3. A0/B0.20、EPD3/EPD5、0D/-1.5D；
4. 比较 `Samp=2/3/4`；
5. 比较 frequency step `5 vs 2.5 cycles/mm`；
6. Web 端根据结果冻结实际 `Samp`；
7. 冻结后才重新运行完整 Phase B；
8. 用户审核最终 B0 后才允许形成正式角膜 lock。

## 参考

- Ansys OpticStudio User Guide, **MTF Data** — MTFA/MTFS/MTFT operands and `Grid=0` fast sparse algorithm.
- Ansys OpticStudio User Guide, **FFT Through Focus MTF** — fast calculation uses the same algorithm as `MTFA, Grid=0`.
- `docs/TASK_005D_PHASE_B_STOP_2026-08-19.md`.
- `docs/TASK_005D_CORNEA_LOCK_ASSETS.md`.
