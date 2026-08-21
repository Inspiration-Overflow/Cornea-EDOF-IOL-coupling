# TASK-007 Phase A.2 审核与 Phase A.3 P–Q 回查定义

> 日期：2026-08-19  
> 基线：`MVP_2026_v2`  
> 分支：`feat/task-007-iol-residuals`  
> A.2 evidence：`docs/evidence/task007/phase_a2/TASK_007_A2_EVIDENCE.json`

## 1. A.2 审核结论

Phase A.2 判定 **PASS**。

代表性 source carrier：

```text
LB_AL2395 + A0
P = 25.25866463479957 D
R_ant = +9.77576192316701 mm
R_post = -9.77576192316701 mm
```

Q=0 physical ZERO_HOA reference：

```text
C40 = +0.5099655621632307 µm
POWP = 47.57852095160946 D
```

三平台代表解：

| Platform | Q | target SA (µm) | replay SA (µm) | ΔPOWP (D) | actual-eye vergence shift (D) | recheck |
|---|---:|---:|---:|---:|---:|---|
| WFS | -4.0 | -0.20 | -0.195674 | -0.000388 | -0.232030 | yes |
| RAD | -6.0 | -0.27 | -0.268786 | -0.000582 | -0.342024 | yes |
| HOA | 0.0 | 0.00 | 0.000000 | 0.000000 | -0.001899 | no |

三平台 saved-file C40 replay repeatability 均为 0.000 µm，全部满足现有 `<=0.001 µm` repeatability gate；SA replay 全部满足 `±0.01 µm` scientific-anchor gate。

## 2. POWP 的解释

WFS/RAD 的 `ΔPOWP` 只有约 `-0.0004/-0.0006 D`。

本项目不新增 post-hoc `ΔPOWP` acceptance threshold，原因是：

1. Q=0 reference 与 Q candidate 的 R、CT、材料、位置完全相同；
2. conic 不改变轴上 paraxial surface curvature，因此一阶 paraxial carrier power 在解析定义上保持不变；
3. POWP 在本项目中只是标准眼 matched diagnostic，用于确认数值实现没有出现明显的一阶 power 漂移；
4. A.2 实测差值已接近毫屈光度量级，不构成 WFS/RAD 实际眼 `-0.23/-0.34 D` 最佳焦点变化的解释。

因此 A.2 的实际眼远焦移动应解释为 **Q 改变高阶波前结构后，minimum-RMS-wavefront best focus 改变**，不是 carrier paraxial power 被 POWP 证实发生了相当幅度的变化。

## 3. 为什么需要 A.3

URD 允许在 conic 引起明显实际眼远焦偏移时进行 1–2 次工程回查：

```text
P solve -> Q(P) -> actual-eye focus recheck
```

A.2 中：

```text
WFS |ΔV| = 0.232 D >= 0.125 D
RAD |ΔV| = 0.342 D >= 0.125 D
```

因此 WFS/RAD 必须进入回查；HOA 不进入。

## 4. A.3 回查算法

仅对代表性 `LB+A0` 的 WFS/RAD：

### Cycle n

1. 从当前 `(R_n, Q_n)` 开始；
2. 在 actual eye、固定 retina、EPD3 下固定：
   - anterior Q = `Q_n`；
   - posterior Q = 0；
3. 只调整 symmetric biconvex radius `R`，直到 Wavefront Quick Focus residual：

```text
|focus_shift| <= 0.001 mm
```

得到新的：

```text
R_{n+1}
P_{n+1}
```

4. 在 `STD_IOL_EYE_2024`、EPD6、约 546 nm 下，以 `P_{n+1}` 重新求：

```text
Q_{n+1}
```

使 matched SA 满足对应平台目标；
5. 保存后重放 Q=0 reference 与 Q candidate：
   - SA replay `±0.01 µm`；
   - C40 solve/replay `<=0.001 µm`；
   - POWP 继续作为 diagnostic 记录；
6. 将 `(P_{n+1},Q_{n+1})` 放回 actual eye；
7. 若：

```text
|ΔV| < 0.125 D
```

则该平台代表性 P–Q 回查收敛；
8. 否则最多进入第二轮；
9. 第二轮后仍 `>=0.125 D` 则 STOP，不扩展 full-18。

## 5. 重要实现边界

现有 `solve_ref_mono_radius_mm()` 不能直接用于非零 Q 的回查，因为其内部 radius setter 会把前后两个 surface conic 设置为相同值。

TASK-007 正式 carrier 定义要求：

```text
anterior Q = platform-specific Q
posterior Q = 0
```

因此 A.3 已新增专用 radius solver，明确在所有 trial radius 上保持：

```text
R_ant = +R
R_post = -R
Q_ant = current Q
Q_post = 0
```

这不是新的科学自由度，只是保护现有 carrier 定义。

## 6. GitHub evidence

A.3 使用和 A.2 相同的 evidence handoff 原则。

成功后只提交：

```text
docs/evidence/task007/phase_a3/TASK_007_A3_EVIDENCE.json
docs/evidence/task007/phase_a3/TASK_007_A3_SUMMARY.csv
```

本地 `.zmx` 和完整 diagnostics 不进入 Git。

Evidence 保持：

```text
evidence_only = true
formal_artifact = false
tdd_999_cleared = false
```

## 7. A.3 后的决策

若 WFS/RAD 都在最多两轮内收敛：

- Web 端冻结 full-18 的统一 P–Q 算法；
- 下一步一次性对 18 个 `Base×Cornea×Platform` 求 provisional carrier；
- 然后再进入 residual physical payload/readback 与 low/median/high actual-power calibration。

若任一代表平台两轮仍不收敛：

- STOP；
- 不进入 18-carrier 批量；
- 不增加第三轮；
- 不修改 0.125 D trigger；
- 回 Web 端重新审核 carrier/Q 数值定义。
