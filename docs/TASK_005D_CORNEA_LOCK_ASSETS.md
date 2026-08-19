# TASK-005D — 角膜冻结资产实现契约

> 状态：**Phase A / A.1 / B.1 实机 PASS；Phase B 的原 Huygens-MTF API 路径 STOP；B0 生产采集已冻结为 MFE MTFA Grid=0、Samp=3、5 cycles/mm；等待完整五候选 scan 与 morphology review。** 本任务补齐 TASK-005 剩余角膜冻结链；不提前进入正式 EDOF carrier/pair lock，也不运行 Run72。

## 1. 目标

在任何 WFS/RAD/HOA 主实验结果参与之前，建立用于角膜冻结的最小确定性链条：

1. 明确主实验共同物理角膜底座；
2. 建立 A0、五个 B 候选和 C0 的冻结处方；
3. 由 OpticStudio 构造并验证 A/B/C diagnostic 模型；
4. 为 A0 和每个 B 候选建立平台独立 `REF_MONO_CORNEA_LOCK`；
5. 在 LB + REF_MONO 中完成真实五候选 B0 scan；
6. 对五候选做显式人工 morphology review；
7. 复用既有 `b0.py` 排序规则重新排序，用户审核后才允许锁定 B0。

完整五候选 scan 完成前均保持：

```text
formal_artifact = false
selection_locked = false
```

只有 morphology review 完整、reviewed rank 生成并由用户确认后，才允许通过 ProjectStore 写不可变 `B0_LOCK`。

## 2. 科学来源与冻结规则

科学语义以项目已定稿资料和当前 URD/TDD 为准：

- `zemax_corneal_archetypes_ABC_design_v1_5.md`
- `cornea_lock_analysis_protocol_v1_1.md`
- `URD-0001 v1.4`
- `TDD-0001 v1.4`

冻结规则：

- A0/B0/C0 只在 `LB_AL2395` 中选择和冻结；
- 使用平台独立 `REF_MONO_CORNEA_LOCK`；
- ATC-M3 只在角膜冻结后进入主实验；
- A0 为像差改变型准单焦；
- B 为连续 Even Asphere / 受控球差延焦；
- C0 为临床 ADD 驱动的中央近用径向多焦；
- B0 不得根据 WFS/RAD/HOA 主实验结果回调。

## 3. 主实验共同角膜底座

005B 的两个角膜面只是重合模块参考面。005D 显式使用共同物理 scaffold：

```text
MAIN_CORNEA_LIOU_555_v1
λ = 555 nm
anterior reference R/Q = +7.77 mm / -0.18
central thickness = 0.50 mm
posterior R/Q = +6.40 mm / -0.60
cornea n = 1.376
post-cornea aqueous n = 1.336
```

该 scaffold 与 `STD_IOL_EYE_2024` 用途不同，单独命名和版本化。MVP 固定后角膜，只改变前表面。

### 3.1 −3 D 共同远用基线

厚角膜一阶等效屈光力：

\[
F=F_1+F_2-\frac{t}{n_c}F_1F_2.
\]

得到：

```text
F_reference = 42.251148573823 D
F_distance  = 39.251148573823 D
R_ant,distance = 8.282294760256 mm
```

该值只作为 A/B/C 的共同 distance 起点；最终表面均由 OpticStudio 光线追迹评价。

## 4. A0

冻结处方：

```text
candidate_id = A0
surface family = Binary Optic 4
T = -3.00 D
EOZ ≈ 5.0 mm
target ΔC40(6 mm) = +0.13 µm
```

数值实现：

- `r ≤ 2.50 mm`：−3 D distance 主治疗区；
- `2.50 < r < 3.25 mm`：0.75 mm 径向 quintic 平滑过渡的 Binary4 数值逼近；
- nominal transition slices = 8；
- `3.25 < r ≤ 4.00 mm`：Liou reference 未治疗周边；
- Binary4 zones 为纯折射，`diffraction order=0`；
- 唯一主动标定自由度为内区 conic；
- 目标 `ΔC40≈+0.13 µm`。

Phase A 实机：

```text
achieved ΔC40 = +0.1329457134 µm
inner conic = -0.1125
Z37 = +0.1208970247 waves
```

Phase A.1 固定 `inner_conic=-0.1125`，仅比较 N4/N8/N16：

```text
ΔC40 N8→N16 = -0.0001341103 µm
Z37  N8→N16 = +0.0019070625 waves
```

结论：nominal N8 对当前 MVP 足够稳定；不增加 N32，不重新调 conic，不改变 `−3D / EOZ≈5 mm / ΔC40≈+0.13 µm` 的科学定义。

## 5. B 五候选

冻结候选：

```text
B0.10  ΔC40 = +0.10 µm
B0.15  ΔC40 = +0.15 µm
B0.20  ΔC40 = +0.20 µm
B0.25  ΔC40 = +0.25 µm
B0.30  ΔC40 = +0.30 µm

T = -3.00 D
OZ = 6.00 mm
surface family = Even Asphere
```

只使用第一个不改变 paraxial power 的 `r^4` Even-Asphere 自由度调节 C40；C60 不主动控制，只记录为派生结果。

Phase A 实机 achieved ΔC40：

```text
B0.10 = +0.1022823683 µm
B0.15 = +0.1486436926 µm
B0.20 = +0.2002078217 µm
B0.25 = +0.2463973195 µm
B0.30 = +0.2990855153 µm
```

所需 `r^4` 系数随目标单调增加，五个候选均通过构造容差。`ΔC40` 表示固定后角膜条件下、前后表面联合 ray trace 的总角膜模块变化量。

## 6. C0

冻结处方：

```text
candidate_id = C0
surface family = Binary Optic 4
T = -3.00 D
near diameter = 3.00 mm
ADD_Rx = +1.75 D
transition width = 0.75 mm
OZ = 6.50 mm
```

径向位置：

```text
rN = 1.50 mm
rT = 2.25 mm
rOZ = 3.25 mm
```

设计分布：

\[
P_{C,design}(r)=P_{distance}+ADD_{Rx}G(r),
\]

\[
G(r)=
\begin{cases}
1,&r\le r_N\\
1-S(t),&r_N<r<r_T\\
0,&r\ge r_T
\end{cases}
\]

\[
S(t)=10t^3-15t^4+6t^5.
\]

`ADD_Rx=+1.75 D` 是处方层设计输入。实际局部/环带会聚、C40/C60、MTF/PSF 均由物理表面 ray trace 输出；不要求 `ADD_Rx = ΔV_ray-traced`。

Phase A 离散检查：

```text
C0 N4  ΔC40 = -0.5544338655 µm
C0 N8  ΔC40 = -0.5556305062 µm
C0 N16 ΔC40 = -0.5558898842 µm
N4→N8  = -0.0011966407 µm
N8→N16 = -0.0002593781 µm
```

结论：nominal N8 对当前 MVP 足够稳定。`2.25→3.25 mm` 保留明确远用主导环带。

## 7. REF_MONO_CORNEA_LOCK

```text
platform-independent monofocal
no EDOF residual
surrounding n ≈ 1.336
IOL n ≈ 1.46
CT ≈ 1.0 mm
optic diameter = 6.0 mm
simple symmetric biconvex bending
IOL anterior vertex = 4.50 mm behind posterior cornea
coaxial, no decentration/tilt
```

对 A0 和每个 B 候选分别：

1. 在候选 LB 冻结眼中用 Wavefront Quick Focus 自动求 symmetric radius，使固定视网膜 focus shift 接近 0；
2. 将同一 radius 放入 `STD_IOL_EYE_2024`，自动求 shared conic，使 IOL-induced C40 接近 0；
3. 回到候选 LB 眼再解一次 radius；
4. 最多两轮，禁止无限迭代。

LB diagnostic 中两面 `SemiDiameter=3.0 mm`。`REF_MONO` 只服务角膜冻结，不进入 72 配置。

Phase B.0 实机已证明 A0 的候选特异 REF_MONO 可以成功构建；失败发生在之后的 Huygens-MTF analysis settings 类型创建阶段，不属于 REF_MONO 光学求解失败。Phase B.1 中 A0 与 B0.20 的 candidate-specific REF_MONO 也成功用于 MTFA probe。

## 8. B0 真实 scan

### 8.1 光学条件

分析协议版本：

```text
CORNEA_LOCK_B0_555_v2
```

冻结光学条件：

```text
λ = 555 nm
EPD = 3 mm + 5 mm
defocus = +0.50 → -3.50 D
step = 0.25 D
17 planes
field = 0
```

每个 defocus 点只临时改变 OBJECT vergence；角膜、IOL、ELP、IMAGE 均不动。0 D 使用模型保存的 nominal infinity OBJECT 状态。

### 8.2 Q_lock 定义

\[
Q_{lock,p}(F)=\frac{1}{50}\int_0^{50}MTF(f,F)df.
\]

`f` 使用 cycles/mm。

### 8.3 生产 MTF acquisition：MFE MTFA

B0 不再使用 Huygens MTF Analysis / `AS_HuygensMtf`。

每个 defocus plane 使用 Merit Function Editor `MTFA` diffraction-MTF operand，生产频率网格：

```text
0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50 cycles/mm
```

冻结 operand 语义：

```text
operand = MTFA
Samp = 3
Wave = 1
Field = 1
Grid = 0
Data Type = 0  # modulation amplitude
```

`Grid=0` 使用 OpticStudio 的快速、稀疏单频 diffraction-MTF 算法。它不是几何 MTF，也不是自行实现 FFT。

同一 plane 的 11 个 MTFA rows 相邻插入，一次 `CalculateMeritFunction()` 计算，随后读取每个 `Value`。临时 rows 必须在 `finally` 删除并验证 MFE row count 恢复；不得 Save lens。

### 8.4 Phase B.1 频率与 sampling 冻结

Phase B.1 代表状态：

```text
A0 + B0.20
EPD3 + EPD5
0 D / -1.5 D
Samp = 2 / 3 / 4
frequency step = 5 / 2.5 cycles/mm
```

实测最大绝对 `Q_lock` 差异：

```text
Samp 2→3      0.00221683
Samp 3→4      0.00067564
5→2.5 cyc/mm  0.00492149
```

据此冻结：

```text
production Samp = 3
production frequency step = 5 cycles/mm
```

该决定是工程参数冻结，不新增自动 convergence threshold，不要求重跑 Phase B.1，也不对完整 204 个状态重复 convergence study。

权威记录：

```text
docs/TASK_005D_PHASE_B1_MTFA_PROBE_REVIEW_2026-08-19.md
```

### 8.5 Full-scan Phase B.1 evidence gate

完整五候选 scan 运行前必须读取既有：

```text
diagnostics/task005d/b0_mtfa_probe/TASK_005D_MTFA_PROBE.json
```

并验证：

- runtime acquisition 成功；
- probe settings 与当前 `CORNEA_LOCK_B0_555_v2` 完全一致；
- `Samp=2/3/4` 与 `5 vs 2.5 cycles/mm` 证据存在；
- 汇总差异均为有限非负值。

旧 probe JSON 的 `passed=true` 只作为 `runtime_passed=true` 的兼容别名，不被解释为脚本内部自动收敛阈值。

### 8.6 排序与 morphology review

五个候选的真实曲线首先交给既有 `rank_b0_candidates()`，形成**未经过 morphology 审核的初步 deterministic recommendation**。

A0 定义 50% `Q_lock` absolute threshold；B 的 distance-retention gate：

```text
EPD3 >= 80% of A0 distance peak
EPD5 >= 70% of A0 distance peak
```

通过 gate 的候选按：

1. EPD3 absolute-threshold DOF；
2. EPD5 absolute-threshold DOF；
3. EPD3 distance retention；
4. |ΔC40|。

full scan 输出必须保持：

```text
morphology_review_pending = true
selection_locked = false
```

随后用户对五候选逐一提供：

```text
candidate_id
reject = true/false
reason = <required when reject=true>
```

软件用原始实机曲线和全部 morphology decisions 重新调用同一 `rank_b0_candidates()`。因此 reviewed scan hash 会包含 morphology flags/reasons；如果人工排除了初步 rank #1，recommendation 会按同一确定性规则自动更新。

最后用户确认 reviewed recommendation，或明确写 override reason，才允许通过 ProjectStore 生成不可变 `B0_LOCK`。

## 9. TASK-005D 与主实验 Huygens 的边界

Phase B.0 的问题是 `AS_HuygensMtf` settings type 在本工作站触发 Python.NET / `ZemaxEngine.dll` hard failure。因此 TASK-005D/B0 production 不再重试 Huygens MTF Analysis。

本任务只冻结：

```text
B0 production → MFE MTFA Grid=0
```

它**不改变 TASK-009/Run72 的主实验 acquisition**。主实验仍服从 TDD v1.4：

```text
Huygens PSF
→ deterministic FFT
→ complex OTF
→ radial MTF / MTFa / VSOTF
```

`HuygensPsfRunner` 保留。后续三代表配置的 sampling convergence 和独立 MTF cross-check 在 TASK-009 决定，不把一次 `AS_HuygensMtf` failure 外推为 Huygens PSF 不可用。

Phase B STOP 后曾实现 `Huygens PSF → Python FFT` 作为 TASK-005D B0 备用路线；该 fallback 已废弃，因为 MFE `MTFA` 对 B0 更简单。此决定不删除主实验所需的通用 Huygens PSF 基础设施。

## 10. 当前代码与输出

当前主要模块：

```text
src/whole_eye_mvp/cornea_assets.py
src/whole_eye_mvp/cornea_zos.py
src/whole_eye_mvp/cornea_candidates_zos.py
src/whole_eye_mvp/ref_mono.py
src/whole_eye_mvp/ref_mono_zos.py
src/whole_eye_mvp/ref_mono_calibration.py
src/whole_eye_mvp/ref_mono_coupled.py
src/whole_eye_mvp/b0.py
src/whole_eye_mvp/b0_zos.py
src/whole_eye_mvp/b0_probe.py
src/whole_eye_mvp/b0_review.py
```

脚本：

```text
scripts/build_task_005d_cornea_candidates.py
scripts/run_task_005d_a0_convergence.py
scripts/probe_task_005d_mtfa.py
scripts/run_task_005d_b0_scan.py
scripts/review_task_005d_b0.py
```

证据文档：

```text
docs/TASK_005D_PHASE_A_REVIEW_2026-08-19.md
docs/TASK_005D_PHASE_A1_REVIEW_2026-08-19.md
docs/TASK_005D_PHASE_B_STOP_2026-08-19.md
docs/TASK_005D_PHASE_B1_MTFA_PROBE_REVIEW_2026-08-19.md
docs/TASK_005D_B0_MTF_ACQUISITION_REVISION_2026-08-19.md
```

full scan 结果仍是 diagnostic/provisional；只有 `review_task_005d_b0.py` 在全部 morphology decisions 和最终选择已提供后才写正式不可变 B0 lock。

## 11. 实机执行顺序

### Phase A — PASS

A/B/C 构造与 MFE-ZERN readback 已完成。

### Phase A.1 — PASS

A0 fixed-conic N4/N8/N16 已证明 nominal N8 足够稳定。

### Phase B.0 — 原 Huygens production path STOP

A0 REF_MONO 构建成功；首次 Huygens MTF analysis settings type 创建触发 `FileLoadException / ZemaxEngine.dll`。不得重复尝试。

### Phase B.1 — PASS

MFE MTFA runtime/API 路径成功；A0/B0.20、EPD3/EPD5、0D/-1.5D 的 `Samp=2/3/4` 和 frequency-step 5/2.5 evidence 已取得。生产冻结 `Samp=3`、5 cycles/mm。无需重跑。

### Phase B.2 — 当前下一步：完整 B0 scan

执行：

```text
scripts/run_task_005d_b0_scan.py
```

只在 Phase B.1 evidence gate 通过后运行 A0 + 五个 B、EPD3/EPD5、17 plane 的完整 MTFA scan。输出必须带 clean Git commit、baseline、OpticStudio installation、probe evidence summary 和输入资产 SHA-256 provenance。

### Phase B.3 — morphology review / rerank / lock

完整 scan 后：

1. 用户审核五候选真实曲线；
2. 五候选 morphology decisions 必须完整；
3. `scripts/review_task_005d_b0.py` 使用原始曲线重新排序；
4. 用户确认 recommendation，或写 override reason；
5. ProjectStore 写不可变 `locks/B0_LOCK.json`；
6. B0 lock 后才允许进入 carrier 科学阶段。

## 12. 尚未完成

仍不得宣称：

- B0 已最终确认；
- `B0_LOCK` 已生成；
- A0/B0/C0 已作为完整三原型集合进入正式 carrier 阶段；
- 角膜 assets 已可进入正式 carrier/Run72。

A0、五个 B 候选、C0 的处方与实机构造证据已经稳定；当前缺口只剩完整 B0 scan 和随后的人为 morphology review/lock。

也不在本任务中处理正式 EDOF carrier/pair locks。

## 13. 参考依据

- Liou H-L, Brennan NA. *Anatomically accurate, finite model eye for optical modeling*. JOSA A. 1997;14:1684–1695.
- Ciolino JB, et al. *Long-term stability of the posterior cornea after laser in situ keratomileusis*. J Cataract Refract Surg. 2007;33:1366–1370.
- Ansys OpticStudio User Guide, **MTF Data** — MTFA/MTFS/MTFT 与 `Grid=0` fast sparse algorithm.
- Ansys OpticStudio User Guide, **FFT Through Focus MTF** — fast calculation 与 `MTFA, Grid=0` 的关系。
- Ansys OpticStudio User Guide, Binary Optic 4.
- 项目文档 `zemax_corneal_archetypes_ABC_design_v1_5.md`。
- 项目文档 `cornea_lock_analysis_protocol_v1_1.md`。
