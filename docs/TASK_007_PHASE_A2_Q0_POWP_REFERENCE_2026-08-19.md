# TASK-007 Phase A.2 — Q=0 ZERO_HOA reference、POWP 与代表性 Q(P) 验证

> 日期：2026-08-19  
> 状态：**Web 端定义与实现完成；待本地离线回归和 OpticStudio 实机验证**  
> 基线：`MVP_2026_v2`  
> 分支：`feat/task-007-iol-residuals`

## 1. Phase A.1 已知事实

Phase A.1 已在 OpticStudio 2026 R1 实机通过：

- `LB_AL2395 + A0` 的 Q=0 controlled carrier：`P≈25.2586646 D`；
- `ATC_M3_AL24477 + A0` 的 Q=0 controlled carrier：`P≈23.2763171 D`；
- 两者 fixed-retina Quick Focus residual 均小于既有 `0.001 mm` gate；
- ZOS-API 确认存在 `Paraxial` surface，且 `Par1=Focal Length`、`Par2=OPD Mode`。

A.1 的 Paraxial surface capability 只保留为历史 API evidence。**A.2 production reference 不使用 Paraxial surface。**

## 2. 为什么不引入 Paraxial surface

当前 URD/TDD 对 `ZERO_HOA_PARAXIAL_REFERENCE` 的实质要求是：

1. 与 candidate carrier 保持相同 paraxial power；
2. 保持相同基础曲率/中心厚度/材料/IOL 位置；
3. 把 IOL 的 aspheric / HOA / residual 项置零；
4. 在同一 `STD_IOL_EYE_2024`、EPD6、约 546 nm 状态下比较 C4。

因此最简单且物理身份最干净的 reference 是：

```text
same physical carrier
same R_ant / R_post
same CT
same n
same IOL position
anterior Q = 0
posterior Q = 0
residual = 0
```

也就是说，`ZERO_HOA_PARAXIAL_REFERENCE` 中的 `PARAXIAL` 指的是**一阶光焦度身份匹配**，不是 OpticStudio `Paraxial` surface type。

这样避免额外引入理想薄透镜、额外 power split 或新的参考几何。

## 3. SA_base 的数值定义

对一个已由实际眼 P-solve 得到的 physical carrier，先把它放入冻结的：

```text
STD_IOL_EYE_2024
EPD = 6.0 mm
lambda ≈ 546 nm
```

定义 Q=0 physical reference 的全眼球差：

```text
C40_ref = C40(STD eye + same physical carrier, Q=0, residual=0)
```

对候选 Q：

```text
C40_q = C40(STD eye + same physical carrier, Q=q, residual=0)
```

平台基础球差定义为 matched difference：

```text
SA_base(q) = C40_q - C40_ref
```

然后求：

```text
WFS-like : SA_base = -0.20 ± 0.01 µm
RAD-like : SA_base = -0.27 ± 0.01 µm
HOA-like : SA_base =  0.00 ± 0.01 µm
```

内部 Q solver 采用更紧的 `±0.005 µm` 收敛目标，保存后重新 LoadFile 的正式 replay 仍按既有 `±0.01 µm` scientific-anchor gate。

## 4. POWP 的角色

Phase A.2 新增 MFE `POWP` readback。

使用条件：

```text
Surf = IOL posterior surface
Wave = 1
Hx = 0
Hy = 0
Px = 0
Py = 0
Data = 0  # spherical power, D
```

它读取的是**从系统物面到 IOL 后表面折射后为止的整体 optical power**，不是一枚孤立 IOL 的名义度数。

因此本项目不把该 POWP 绝对值替代 `P_ijk`。它只用作同一 standard-eye matched comparison：

```text
DeltaPOWP(q) = POWP(candidate q) - POWP(reference Q=0)
```

因为 reference/candidate 的上游标准眼、R、CT、n、位置全部相同，`DeltaPOWP` 用于验证改变 Q 时是否意外改变了一阶 power identity。

Phase A.2 只记录真实 `DeltaPOWP`，**暂不事后发明 acceptance threshold**。Web 端先审核代表性 WFS/RAD/HOA 实测值，再决定 full-18 gate 是否需要显式数值 tolerance。

## 5. Q solver

对代表性 `LB + A0` source carrier：

1. 建 Q=0 physical reference；
2. 读取 reference C40 和 POWP；
3. 对 WFS/RAD/HOA 分别扫描/二分 Q；
4. 每个 Q evaluation 都读取 C40 和 POWP；
5. 达到内部 `|SA_base-target| <= 0.005 µm` 后保存 `.zmx`；
6. 重新 LoadFile；
7. 重放 C40 与 POWP；
8. 保存后 `SA_base` 必须满足 `±0.01 µm`；
9. C40 solve-vs-replay repeatability 仍要求 `<=0.001 µm`。

HOA-like 的基础 carrier target 为 0，因此若 Q=0 reference 本身满足 matched-difference target，Q solver 应自然返回 `Q=0`；不得为了让 HOA carrier“看起来更复杂”而强制非零 Q。

## 6. P–Q actual-eye round-trip

每个平台 Q 解出后，把相同 P/R carrier 放回 Phase A.1 的 `LB+A0` actual-eye 文件，只修改 anterior Q：

```text
posterior Q = 0
retina fixed
EPD = 3 mm
```

用 Wavefront Quick Focus 测 fixed retina 相对最佳焦点的 shift，并换算 IOL 后介质中的等效 vergence shift：

```text
DeltaV = n * 1000 * (1 / L_best - 1 / L_fixed)
```

现有工程 recheck trigger 保持：

```text
|DeltaV| >= 0.125 D
```

达到 trigger 只标记 `P_Q_recheck_required=true`。Phase A.2 **不自动修改 P 或重新求 Q**；由 Web 审核后决定是否进入允许的 1–2 次 P–Q 回查。

## 7. GitHub evidence handoff

为了避免把完整本地实验数据塞进 ZCode AI 上下文，A.2 probe 支持：

```text
--write-repo-evidence
```

成功后额外生成：

```text
docs/evidence/task007/phase_a2/TASK_007_A2_EVIDENCE.json
docs/evidence/task007/phase_a2/TASK_007_A2_SUMMARY.csv
```

这两个文件：

- 只保存结构化关键结果、hash 和 settings；
- 不保存 `.zmx`；
- 不保存机器绝对路径；
- 可提交到当前 TASK 分支供 Web 端 GitHub connector 直接读取；
- `evidence_only=true`；
- `formal_artifact=false`；
- `tdd_999_cleared=false`。

GitHub evidence 只是版本化诊断证据，不等于 scientific lock。

## 8. Phase A.2 STOP 边界

本轮不做：

- 18-carrier 全批量；
- residual Grid Sag；
- residual amplitude 调整；
- low/median/high residual calibration；
- formal carrier/residual/pair lock；
- TASK-008；
- Run72。

A.2 实机完成后必须返回 Web 审核：

1. POWP cell header 是否与 runner contract 匹配；
2. Q=0 reference / 三个平台 candidate 的 C40；
3. WFS/RAD/HOA Q；
4. 三个平台 `DeltaPOWP`；
5. 三个平台 P–Q actual-eye shift；
6. 是否触发 `0.125 D` recheck；
7. 保存后 replay；
8. GitHub evidence commit SHA/path/hash。

只有代表性 A.2 通过后，才扩展到完整 18 carrier。
