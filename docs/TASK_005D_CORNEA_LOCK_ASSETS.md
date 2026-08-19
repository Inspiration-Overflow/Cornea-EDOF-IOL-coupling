# TASK-005D — 角膜冻结资产实现契约

> 状态：**Web 端实现完成第一阶段，等待最小 OpticStudio 实机诊断**。本任务补齐 TASK-005 剩余角膜冻结链；不提前进入正式 EDOF carrier/pair lock，也不运行 Run72。

## 1. 目标

在任何 WFS/RAD/HOA 主实验结果参与之前，建立用于角膜冻结的最小确定性链条：

1. 明确的主实验共同物理角膜底座；
2. A0、五个 B 候选和 C0 的冻结处方；
3. 可由 OpticStudio 直接构造/求解的 A/B/C diagnostic 模型；
4. 平台独立 `REF_MONO_CORNEA_LOCK`；
5. 真实五候选 B0 scan，并复用既有 `b0.py` 排序规则。

所有 005D 输出在用户确认前都保持 `formal_artifact=false`，不得写正式角膜 lock。

## 2. 设计来源

科学语义以项目已定稿文档为准：

- `zemax_corneal_archetypes_ABC_design_v1_5.md`
- `cornea_lock_analysis_protocol_v1_1.md`
- 当前仓库 `URD-0001 v1.4` / `TDD-0001 v1.3`

冻结规则：

- 只在 `LB_AL2395` 中选择/冻结 A0/B0/C0；
- 使用平台独立 `REF_MONO_CORNEA_LOCK`；
- ATC-M3 只在角膜冻结后进入主实验；
- A0 是像差改变型准单焦；
- B 是连续 Even Asphere / 受控球差延焦；
- C0 是临床 ADD 驱动的中央近用径向多焦；
- B0 不根据 WFS/RAD/HOA 主实验结果回调。

## 3. 主实验共同角膜底座

005B 的两个角膜面只是重合参考面，因此 005D 显式定义：

```text
MAIN_CORNEA_LIOU_555_v1
λ = 555 nm
anterior reference R/Q = +7.77 mm / -0.18
central thickness = 0.50 mm
posterior R/Q = +6.40 mm / -0.60
cornea n = 1.376
post-cornea aqueous n = 1.336
```

该 scaffold 与 `STD_IOL_EYE_2024` 用途不同，单独命名和版本化。第一阶段固定后角膜，只改变前表面。

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

该值只作为 A/B/C 的共同 distance 起点；最终表面仍由 OpticStudio 光线追迹评价。

## 4. A0

冻结处方：

```text
candidate_id = A0
surface family = Binary Optic 4
T = -3.00 D
EOZ ≈ 5.0 mm
target ΔC40(6 mm) = +0.13 µm
```

当前实现：

- `r ≤ 2.50 mm`：−3 D distance 主治疗区；
- `2.50 < r < 3.25 mm`：0.75 mm 径向 quintic 平滑过渡的 Binary4 数值逼近；
- nominal transition slices = 8；
- `3.25 < r ≤ 4.00 mm`：Liou reference 未治疗周边；
- 所有 Binary4 zone 为纯折射，`diffraction order=0`；
- 唯一主动标定自由度仍是内区 conic；
- OpticStudio 自动求到 `ΔC40≈+0.13 µm`。

0.75 mm 和 8 slices 是 **A0 的数值实现参数**，不是新增 scientific-baseline 变量。若首次实机表型/收敛不合理，再在 Web 端修订；本地不人工调 zone。

## 5. B 五候选

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

当前实现只使用第一个不改变 paraxial power 的 `r^4` Even-Asphere 自由度调节 C40；C60 不主动控制，只作为后续派生结果记录。

`ΔC40` 指固定后角膜后，前后表面联合 ray trace 的总角膜模块变化量。

## 6. C0

固定处方：

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

这里 `ADD_Rx=+1.75D` 是**目标处方层设计输入**。最终实际局部/环带会聚、C40/C60、MTF/PSF 都由物理表面 ray trace 输出；不要求 `ADD_Rx = ΔV_ray-traced`。

Binary4 nominal 使用 8 个 transition slices，并同时生成 4/8/16 三个版本作为第一阶段离散检查。`2.25→3.25 mm` 保留明确远用主导环带。

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

1. 在该候选 LB 冻结眼中，用 Wavefront Quick Focus 自动求 symmetric radius，使固定视网膜 focus shift 接近 0；
2. 将同一 radius 放入 `STD_IOL_EYE_2024`，自动求 shared conic，使 IOL-induced C40 接近 0；
3. 回到候选 LB 眼再解一次 radius；
4. 最多两轮，不能自动无限迭代。

LB diagnostic 中两面明确设 `SemiDiameter=3.0 mm`。`REF_MONO` 只服务角膜冻结，不进入 72 配置。

## 8. B0 真实 scan

冻结设置继续使用 `CORNEA_LOCK_B0_555_v1`：

```text
λ = 555 nm
EPD = 3 mm + 5 mm
defocus = +0.50 → -3.50 D
step = 0.25 D
17 planes
```

每个 defocus 点只临时改变 OBJECT vergence，角膜、IOL、ELP、IMAGE 均不动。0 D 直接复用模型保存的 nominal infinity OBJECT 状态。

B0 专用指标：

\[
Q_{lock,p}(F)=\frac{1}{50}\int_0^{50}MTF(f,F)df,
\]

`f` 使用 cycles/mm。Huygens MTF 计算到 60 cycles/mm，再插值/积分到冻结的 50 cycles/mm。

采样：

```text
pupil sampling = 128×128
image sampling = 256×256
image delta = 0.5 µm
```

五个候选的真实曲线直接喂给既有 `rank_b0_candidates()`；软件不自动替代人工 morphology 判断。第一次 scan 输出 recommendation，但保持：

```text
morphology_review_pending = true
selection_locked = false
```

用户看完曲线/形态后才允许正式 B0 lock。

## 9. 当前代码与输出

主要模块：

```text
src/whole_eye_mvp/cornea_assets.py
src/whole_eye_mvp/cornea_zos.py
src/whole_eye_mvp/cornea_candidates_zos.py
src/whole_eye_mvp/ref_mono.py
src/whole_eye_mvp/ref_mono_zos.py
src/whole_eye_mvp/ref_mono_calibration.py
src/whole_eye_mvp/ref_mono_coupled.py
src/whole_eye_mvp/zos/huygens_mtf.py
src/whole_eye_mvp/b0_zos.py
```

本地只保留两条主要执行脚本：

```text
scripts/build_task_005d_cornea_candidates.py
scripts/run_task_005d_b0_scan.py
```

第一条自动写：

```text
project_mvp_2026_v2_zmx/diagnostics/task005d/corneas/
  TASK_005D_CORNEA_CANDIDATES.json
```

第二条自动写：

```text
project_mvp_2026_v2_zmx/diagnostics/task005d/b0_scan/
  TASK_006_B0_REAL_SCAN.json
```

两者都只是 diagnostics，不写正式 lock。

## 10. 分阶段实机策略

为了降低本地思维负担，不一次跑完整长流程。

### Phase A — 先只构建角膜候选

本地仅运行：

```powershell
uv run python scripts/build_task_005d_cornea_candidates.py `
  --project-dir project_mvp_2026_v2_zmx `
  --baseline-id MVP_2026_v2
```

然后只回传：

```text
HEAD
PASS/FAIL
TASK_005D_CORNEA_CANDIDATES.json path
native hard error if any
residual OpticStudio/Zemax process count
```

Web 端读取 JSON、审核 A/B achieved ΔC40 与 C0 4/8/16 结果，再决定是否进入 Phase B。

### Phase B — 只有 Phase A 通过才跑 B0 scan

本地只运行：

```powershell
uv run python scripts/run_task_005d_b0_scan.py `
  --project-dir project_mvp_2026_v2_zmx `
  --baseline-id MVP_2026_v2
```

然后只回传结果 JSON 路径。Web 端负责分析曲线、排序和 morphology review。

## 11. 尚未完成

在实机结果回来前仍不得宣称：

- A0/B0/C0 已正式冻结；
- `REF_MONO_CORNEA_LOCK` 已形成正式 lock；
- B0 已最终确认；
- 角膜 assets 已可进入 carrier/Run72。

也不在本任务中处理正式 EDOF carrier/pair locks。

## 12. 参考依据

- Liou H-L, Brennan NA. *Anatomically accurate, finite model eye for optical modeling*. JOSA A. 1997;14:1684–1695.
- Ciolino JB, et al. *Long-term stability of the posterior cornea after laser in situ keratomileusis*. J Cataract Refract Surg. 2007;33:1366–1370.
- Ansys OpticStudio User Guide, Binary Optic 4 / Huygens MTF.
- 项目文档 `zemax_corneal_archetypes_ABC_design_v1_5.md`。
- 项目文档 `cornea_lock_analysis_protocol_v1_1.md`。
