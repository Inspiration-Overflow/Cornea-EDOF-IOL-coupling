# TASK-005D — 角膜冻结资产实现契约

> 状态：**实现中**。本任务补齐 TASK-005 剩余的角膜冻结链；不提前进入正式 EDOF carrier/pair lock，也不运行 Run72。

## 1. 目标

在任何 WFS/RAD/HOA 主实验结果参与之前，建立用于角膜冻结的最小确定性链条：

1. 一个明确的主实验共同物理角膜底座；
2. A0、五个 B 候选和 C0 的冻结处方；
3. 后续可由 OpticStudio 实机实现的 A/B/C 表面构造输入；
4. 平台独立 `REF_MONO_CORNEA_LOCK` 的接口位置。

B0 的排序/锁定算法已经存在于 `src/whole_eye_mvp/b0.py`，本任务不再设计第二套 B0 算法。

## 2. 设计来源

A/B/C 的科学语义以项目已经定稿的以下文档为准：

- `zemax_corneal_archetypes_ABC_design_v1_5.md`
- `cornea_lock_analysis_protocol_v1_1.md`
- 当前仓库 `URD-0001 v1.4` / `TDD-0001 v1.3`

其中冻结规则为：

- 只在 `LB_AL2395` 中选择/冻结 A0/B0/C0；
- 使用平台独立的 `REF_MONO_CORNEA_LOCK`；
- ATC-M3 只在角膜冻结后进入主实验；
- A0 是像差改变型准单焦；
- B 是连续 Even Asphere / 受控球差延焦；
- C0 是临床 ADD 驱动的中央近用径向多焦。

## 3. 主实验共同角膜底座

此前 005B 只冻结了两个**重合的角膜参考面**，故 A/B/C 的物理中心厚度和后表面不能从 005B 自动推断。

005D 显式新增一个独立于标准眼命名空间的工程底座：

```text
MAIN_CORNEA_LIOU_555_v1
```

参数：

```text
λ = 555 nm
anterior reference R = +7.77 mm
anterior reference Q = -0.18
central thickness = 0.50 mm
posterior R = +6.40 mm
posterior Q = -0.60
cornea n = 1.376
post-cornea aqueous n = 1.336
```

这些数值采用 Liou–Brennan 1997 模型角膜作为共同 scaffold。Liou–Brennan 原模型本身明确面向包括屈光手术在内的光学建模；其结构参数表给出 0.50 mm 角膜厚度及上述折射率。前后表面 asphericity 采用项目已长期使用、并在后续 Liou-Brennan 实现中一致报道的 `-0.18/-0.60`。

**该 scaffold 与 `STD_IOL_EYE_2024` 是两个不同用途的工程对象。** 两者数值相近不意味着主实验角膜“继承标准眼”；005D 将其单独命名、单独版本化并在后续 A/B/C 资产 hash 中形成 provenance。

第一阶段固定后角膜，只修改前表面。长期 LASIK 后表面研究显示在规范手术范围内后表面总体稳定，因此把后表面固定作为本机制研究 MVP 的工程近似是合理的；这不是对所有真实患者的普遍生物力学结论。

### 3.1 −3 D 共同远用基线

先用厚角膜一阶等效屈光力建立 A/B/C 的共同 distance baseline：

\[
F=F_1+F_2-\frac{t}{n_c}F_1F_2.
\]

Liou 参考角膜在上述参数下：

```text
F_reference = 42.251148573823 D
```

标准化近视治疗 `T=-3.00 D` 后：

```text
F_distance = 39.251148573823 D
```

在固定后表面、厚度和折射率条件下反解得到前表面基线：

```text
R_ant,distance = 8.282294760256 mm
```

这只是**一阶远用基线**，不是 A0/B0/C0 的最终完整表面，也不替代后续 Zemax 光线追迹、C40 标定或 IOL power 求解。

## 4. A0 冻结处方

```text
candidate_id = A0
surface family = Binary Optic 4
T = -3.00 D
EOZ ≈ 5.0 mm
target ΔC40(6 mm) = +0.13 µm
```

实现原则：

- 以后表面固定的总角膜模块为评价对象；
- 前表面从共同 −3 D distance baseline 出发；
- Binary 4 只使用折射 sag，自身不引入衍射相位；
- 实机调节使总角膜 `ΔC40(6 mm)` 达到 `+0.13±0.02 µm`；
- EOZ、中央变平和基本 zone/sampling convergence 同时检查。

当前 Web 端不预先编造 Binary 4 的最终 zone 参数；它们由一次最小实机求解后写回正式构造记录。

## 5. B 候选冻结处方

五个第一阶段候选：

```text
B0.10  ΔC40 = +0.10 µm
B0.15  ΔC40 = +0.15 µm
B0.20  ΔC40 = +0.20 µm
B0.25  ΔC40 = +0.25 µm
B0.30  ΔC40 = +0.30 µm
```

共同条件：

```text
T = -3.00 D
OZ = 6.00 mm
surface family = Even Asphere
```

`ΔC40` 指**固定后角膜时前后表面联合光线追迹得到的总角膜模块变化量**。第一阶段不主动把 C60 作为优化自由度；C60 只记录为派生结果。

五个候选建立后，由既有 `b0.py` 在 `LB_AL2395 + REF_MONO_CORNEA_LOCK` 中使用真实 EPD3/EPD5 曲线完成排序；不得根据 WFS/RAD/HOA 主实验结果选择 B0。

## 6. C0 冻结处方

C0 直接固定，不做 nominal 性能优化：

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

临床 ADD 保持为处方层面的输入变量。设计目标功率写为：

\[
P_{C,design}(r)=P_{distance}+ADD_{Rx}G(r),
\]

其中：

\[
G(r)=
\begin{cases}
1,&r\le r_N\\
1-S(t),&r_N<r<r_T\\
0,&r\ge r_T
\end{cases}
\]

\[
S(t)=10t^3-15t^4+6t^5,
\qquad
t=\frac{r-r_N}{r_T-r_N}.
\]

该 quintic 在两端 value、1st derivative、2nd derivative 连续。`r=2.25→3.25 mm` 保留明确的远用主导环带。

按共同厚角膜 scaffold 的一阶换算：

```text
central target power ≈ 41.001148573823 D
central target front radius ≈ 7.975550558942 mm
far target front radius ≈ 8.282294760256 mm
```

这些是构造目标，不把 `+1.75 D` 重新解释为某一径向位置的临床可测局部角膜屈光力。

## 7. REF_MONO_CORNEA_LOCK

角膜冻结参考 IOL 仍按既定协议：

```text
platform-independent monofocal
no EDOF residual
surrounding n ≈ 1.336
IOL n ≈ 1.46
CT ≈ 1.0 mm
optic diameter = 6.0 mm
simple biconvex bending
IOL anterior vertex = 4.50 mm behind posterior cornea
coaxial, no decentration/tilt
```

对每个角膜候选，基础 power 调整到固定视网膜的远焦；再在 `STD_IOL_EYE_2024` 中把参考 IOL 调到近球差中性。若 conic 引起明显焦移，只允许一次简单 power–conic 回查。

**本任务不会把 REF_MONO 当作第四个研究平台，也不会让它进入 72 配置。**

## 8. 当前代码边界

`src/whole_eye_mvp/cornea_assets.py` 目前只冻结：

- `MAIN_CORNEA_LIOU_555_v1`；
- 厚角膜一阶 power/radius 换算；
- A0 + 五个 B 候选 + C0 的精确处方集合；
- C0 quintic radial design。

尚未宣称完成：

- A0 Binary 4 最终 zone 参数；
- 五个 B 的 Even Asphere 实机系数；
- C0 Binary 4 最终离散 zone 数/参数；
- `REF_MONO_CORNEA_LOCK` 的真实 power/conic；
- A/B/C 的实机 C40/C60、MTF/PSF、convergence；
- B0 正式选择/锁定。

这些必须来自 OpticStudio 实机，不在 Web 端伪造。

## 9. 下一步最小执行顺序

Web 端继续完成实际 `.zmx` 构造器和实机输入脚本；本地只执行不可替代的 OpticStudio 求解/读回：

1. 生成共同 −3 D distance cornea scaffold；
2. 建 `REF_MONO_CORNEA_LOCK`；
3. A0 调到目标 ΔC40；
4. 五个 B 调到各自 ΔC40；
5. C0 建立并做基本离散 convergence；
6. 获取 A0 + 五个 B 的 EPD3/EPD5 lock curves；
7. 既有 `b0.py` 给出 B0 recommendation，再由用户确认。

在此之前不进入正式 EDOF carrier/pair lock，也不运行 Run72。

## 10. 参考依据

- Liou H-L, Brennan NA. *Anatomically accurate, finite model eye for optical modeling*. JOSA A. 1997;14:1684–1695. DOI: 10.1364/JOSAA.14.001684.
- Ciolino JB, et al. *Long-term stability of the posterior cornea after laser in situ keratomileusis*. J Cataract Refract Surg. 2007;33:1366–1370. DOI: 10.1016/j.jcrs.2007.04.016.
- Ansys OpticStudio User Guide, Binary Optic 4 surface definition: multiple concentric refractive/aspheric zones and automatic sag offset for boundary continuity.
- 项目文档 `zemax_corneal_archetypes_ABC_design_v1_5.md`。
- 项目文档 `cornea_lock_analysis_protocol_v1_1.md`。
