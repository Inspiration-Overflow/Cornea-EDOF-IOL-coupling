# URD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **文档角色：** 用户需求文档（User Requirement Document, URD）。  
> **文档原则：** 本文件为独立、完整、自包含的 MVP 需求基线。实现人员不需要阅读任何旧版 URD、科学设计文档或讨论记录，即可理解本软件的研究目的、科学模型、实验矩阵、软件范围与验收条件。  
> **边界：** 本文件定义“软件必须完成什么、科学模型必须遵守什么、什么算成功”；内部模块拆分、类设计、具体 ZOS-API 调用方式和测试代码留给后续 ADD/MDD。

## Metadata

- project: Corneal Archetypes × Nondiffractive EDOF IOL Whole-Eye Zemax Automation
- document_id: URD-0001
- version: 1.4
- status: approved-for-ADD
- owner: project owner
- last_updated: 2026-08-18
- scope_level: MVP
- primary_platform: Windows
- optical_engine: Ansys Zemax OpticStudio 2026 R1, Sequential Mode
- automation: Python + ZOS-API
- user_interface: CustomTkinter 极简桌面 GUI
- primary_outputs: CSV + `.zos` + 图像
- architecture_impact_of_v1_4: none; existing ADD/MDD decomposition remains valid because only the standard-eye calibration condition changed

---

# 1. 项目目标

建立一个本地运行的研究自动化软件，通过 ZOS-API 可重复地生成、校验、冻结并运行以下机制研究：

\[
\boxed{
\text{A/B/C 角膜光学原型}
\times
\text{WFS/RAD/HOA 非衍射 EDOF IOL surrogate}
}
\]

软件的主要任务是减少人工逐个修改 Zemax 文件造成的错误和版本漂移，并形成可追溯的模型、配置、数值结果和图像结果。

MVP 的核心科学问题是：

> 在可控、共轴、单色的人工晶状体眼中，不同术后角膜光学结构与不同非衍射 EDOF IOL 机制如何共同改变最佳远焦成像质量、贯焦形态、焦深、PSF 和全眼高阶像差？

本项目是**机制性光学研究软件**，不是临床决策支持系统，不用于给具体患者推荐 IOL。

---

# 2. 科学模型基线

本节直接定义软件必须实现的科学模型。以下定义是本 URD 的组成部分，不依赖外部科学文档。

## 2.1 两个轴向人工晶状体眼基座

MVP 使用两个主研究基座。

### Base 1：`LB_AL2395`

正常轴长参考人工晶状体眼：

\[
\boxed{AL=23.950\ \mathrm{mm}}
\]

其轴向尺度取自 Liou–Brennan 类型正常眼参考，但主实验**不保留其天然角膜和天然晶状体**。

### Base 2：`ATC_M3_AL24477`

典型中度轴性近视参考人工晶状体眼：

\[
\boxed{AL=24.477\ \mathrm{mm}}
\]

其轴向尺度对应 Atchison Model 1 在术前球镜等效约 −3.00 D 时的典型眼轴。主实验同样不保留原模型天然角膜和天然晶状体。

### 两个基座的共同几何规则

两个基座除眼轴/后段传播长度外尽量保持相同：

- 相同 A0/B0/C0 角膜模块；
- 相同角膜厚度和后角膜定义；
- 后角膜至标准化 STOP：
  \[
  \boxed{3.15\ \mathrm{mm}}
  \]
- 后角膜至 IOL 前表面参考位置：
  \[
  \boxed{4.50\ \mathrm{mm}}
  \]
- IOL 倾斜 pivot 位于 IOL 几何中心；
- 房水和玻璃体 MVP 折射率约：
  \[
  n\approx1.336
  \]
- 轴上研究采用平面 IMAGE surface，其顶点位置由 AL 决定；
- 主实验 Field = 0°；
- 主实验保持角膜、STOP、IOL 共轴。

双基座的目的不是比较两种经典 schematic eye 谁更好，而是检查角膜—IOL 耦合趋势是否受眼轴背景明显影响。

---

## 2.2 三个冻结角膜原型

三个角膜都是旋转对称、机制导向的术后 surrogate。MVP 不模拟真实准分子激光逐脉冲消融过程。

共同要求：

\[
\frac{\partial z}{\partial\theta}=0
\]

因此 MVP 中：

- 不模拟角膜治疗区偏心；
- 不模拟治疗区倾斜；
- 不模拟瞳孔中心漂移；
- 不主动加入彗差或随机不规则像差；
- 主实验开始后不得为了某个 IOL 的结果重新调整 A0/B0/C0。

### A0：像差改变型近视术后准单焦角膜

A0 表示没有主动老视 EDOF/多焦设计、但具有普通近视角膜重塑后像差背景的远用主导角膜。

MVP nominal 目标：

\[
\boxed{T_{\rm cornea}=-3.00\ \mathrm{D}}
\]

\[
\boxed{D_{\rm EOZ}\approx5.0\ \mathrm{mm}}
\]

\[
\boxed{\Delta C_4^0(6\ \mathrm{mm})\approx+0.13\ \mu\mathrm{m}}
\]

优先采用 Binary Optic 4 的纯折射分区形式表示：

\[
\text{有效治疗区}\rightarrow\text{平滑过渡区}\rightarrow\text{未治疗周边}
\]

nominal A0 采用平滑版本，至少保持 sag 和一阶斜率的合理连续性。明显的 C1-edge 变体不属于首轮 MVP 主矩阵。

### B0：连续非球面/球差调制型角膜 EDOF

B 表示不设置显式中央近用功能区，而通过连续非球面和受控高阶像差形成单一连续展宽焦区的角膜 EDOF 原型。

MVP 固定：

\[
T_{\rm cornea}=-3.00\ \mathrm{D}
\]

\[
D_{\rm OZ}=6.00\ \mathrm{mm}
\]

第一轮实际扫描候选：

\[
\boxed{
\Delta C_4^0(6\ \mathrm{mm})=
+0.10,+0.15,+0.20,+0.25,+0.30\ \mu\mathrm{m}
}
\]

其中 +0.20 μm 只是机制锚点，不是预先指定的最终 B0。

B 使用连续 Even Asphere 或等价连续轴对称非球面实现。MVP 不把 \(C_6^0\) 作为独立优化自由度；实际产生的 \(C_6^0\) 作为派生结果记录。

### B0 的选择规则

B0 **必须由第一轮实际五点扫描确定**，不得预先指定；仍使用：

\[
CORNEA\_LOCK\_EYE=LB\_AL2395
\]

和平台独立的：

\[
REF\_MONO\_CORNEA\_LOCK.
\]

为避免“人工看曲线”导致不可复现，同时保持 MVP 简洁，B0 采用**确定性推荐 + 人工确认**：

1. 对 A0 和五个 B 候选，在 EPD3、EPD5 分别计算：
   \[
   Q_{\rm lock,p}(F)=\frac{1}{50}\int_0^{50}MTF(f,F)\,df,
   \]
   其中 \(f\) 的单位固定为 cycles/mm，\(p\in\{3,5\}\)。
2. 先用 A0 冻结两个绝对阈值：
   \[
   T_{\rm abs,p}=0.5\,Q_{A0,p,peak}.
   \]
3. 候选必须满足距离峰保留 gate：
   \[
   Q_{B,3,peak}/Q_{A0,3,peak}\ge0.80,
   \qquad
   Q_{B,5,peak}/Q_{A0,5,peak}\ge0.70.
   \]
4. 对通过距离 gate 的候选，用 \(Q_{\rm lock,p}\ge T_{\rm abs,p}\) 定义 `DOF_lock_abs`。明显、稳定的“远近双峰 + 深谷”候选由用户标记 `morphology_reject=true`，必须记录简短理由；MVP 不为此再引入复杂自动形态分类器。
5. 对剩余候选，软件按以下顺序给出**推荐 B0**：
   - EPD3 `DOF_lock_abs` 更大；
   - 若并列，EPD5 `DOF_lock_abs` 更大；
   - 再并列，EPD3 距离峰保留率更高；
   - 仍并列，选择较小的 \(|\Delta C_4^0|\)。
6. 用户确认推荐结果后写 B0 lock；若人工 override，必须填写 `selection_reason`。B0 lock 至少保存 candidate ID、scan hash、morphology 标记/理由、推荐排序和最终确认理由。

B0 冻结后不得根据 WFS/RAD/HOA 主结果回调。该流程仍只有五个候选，不引入多目标优化器。

### C0：中央近用型径向多焦角膜

C 表示不同径向位置承担不同视觉功能的中央近用型角膜。

C0 直接固定为处方驱动的 nominal 模型：

\[
\boxed{T_{\rm cornea}=-3.00\ \mathrm{D}}
\]

\[
\boxed{D_{\rm near}=3.00\ \mathrm{mm}}
\]

\[
\boxed{ADD_{\rm Rx}=+1.75\ \mathrm{D}}
\]

\[
\boxed{D_{\rm OZ}=6.50\ \mathrm{mm}}
\]

\[
\boxed{w_T=0.75\ \mathrm{mm}}
\]

其中 ADD 是**临床处方层面的输入量**，不是要求实际 ray-traced 中央—周边局部 vergence 差严格等于 +1.75 D。

径向功能结构为：

\[
\text{中央近用}\rightarrow\text{平滑过渡}\rightarrow\text{周边远用主导}
\]

中央半径：

\[
r_N=1.50\ \mathrm{mm}
\]

过渡结束半径：

\[
r_T=r_N+w_T=2.25\ \mathrm{mm}
\]

总光学区半径：

\[
r_{OZ}=3.25\ \mathrm{mm}
\]

建议使用五次 smoothstep 完成近用权重从 1 到 0 的平滑过渡。C0 不为获得更大的 DOF 或更漂亮的贯焦曲线而重新优化。

---

## 2.3 IOL 平台与标准模型眼

MVP 研究三种**非衍射 EDOF 机制 surrogate**：

1. `WFS`：波前塑形型；
2. `RAD`：连续径向屈光力调制型；
3. `HOA`：中央 4/6 阶高阶球差调制型。

Vivity、TECNIS PureSee、LuxSmart 只可作为公开机制锚点。软件、文件名、结果和报告不得把 surrogate 声称为商业产品精确制造处方。

### `STD_IOL_EYE_2024`

软件必须建立并复用一份固定工程标准人工晶状体眼：

\[
\boxed{STD\_IOL\_EYE\_2024}
\]

它只用于：

- IOL 基础球差设定；
- 对实际 carrier power 反求 conic；
- EDOF surrogate 的基础校准。

它不作为 LB/ATC 主全眼研究基座。

MVP 标准眼最小验收锚点统一在 **6.0 mm entrance pupil** 下定义：

- 模型角膜正球差目标：
  \[
  \boxed{C_4^0(6\ \mathrm{mm})\approx+0.258\ \mu\mathrm{m}}
  \]
- IOL 前表面附近实际光束覆盖：
  \[
  \boxed{D_{\rm IOL,footprint}(6\ \mathrm{mm})=5.15\pm0.10\ \mathrm{mm}}
  \]
- IOL 周围模型介质：
  \[
  \boxed{n=1.336}
  \]
- IOL 基础球差 / `Q(P)` 主校准孔径：
  \[
  \boxed{EPD_{\rm SA-cal}=6.0\ \mathrm{mm}}
  \]
- 单色校准波长约：
  \[
  \boxed{546\ \mathrm{nm}}
  \]

这里的 6 mm 是**标准眼设计/标定条件**，用于把角膜生理正球差、IOL 实际光束覆盖和平台基础球差放在同一瞳孔归一化条件下。它不同于主实验的性能评估瞳孔：72 个 nominal 配置仍只使用 EPD3 与 EPD5。3 mm 作为较小明视瞳孔保留在性能矩阵中，但不再承担 `SA_base` 或 `Q(P)` 的绝对球差设计标定，以避免小瞳孔本身较长景深与较弱球差表现混入 carrier 设计定义。

具体表面参数可由实现阶段选择合理的工程处方，但一旦该标准眼通过上述检查就必须冻结，所有平台后续共用同一份标准眼。

标准眼中的 IOL 基础球差必须相对于同几何、同 paraxial power 的：

\[
\boxed{ZERO\_HOA\_PARAXIAL\_REFERENCE}
\]

定义。该参考态保留 carrier 的 paraxial power/几何/材料/位置，但将 IOL 的 aspheric/HOA/residual 项置零。平台 `SA_base` 使用“候选 carrier 全眼 \(C_4^0\) − ZERO_HOA 参考态全眼 \(C_4^0\)”计算，而不是把某个孤立表面系数直接当作 IOL SA。候选 carrier 与 ZERO_HOA reference 必须在同一个 6 mm 标准眼校准状态下比较。

### 三个平台的基础球差目标

三类 IOL 不强制共享同一个基础 carrier，而保留平台特异基础球差；以下目标均定义于 `STD_IOL_EYE_2024`、EPD=6.0 mm、约 546 nm：

\[
\boxed{SA_{\rm base,WFS}^{STD}(6\ \mathrm{mm})\approx-0.20\ \mu\mathrm{m}}
\]

\[
\boxed{SA_{\rm base,RAD}^{STD}(6\ \mathrm{mm})\approx-0.27\ \mu\mathrm{m}}
\]

\[
\boxed{SA_{\rm base,HOA}^{STD}(6\ \mathrm{mm})\approx0}
\]

这些值是本项目的工程 surrogate 目标，不是孤立 IOL 表面的固定 Zernike 数值，也不是商业制造参数。

---

## 2.4 carrier power 与 conic 的 MVP 求解规则

对每个：

\[
Base_i\times Cornea_j\times Platform_k
\]

软件必须分别求实际 carrier：

\[
\boxed{P_{ijk}}
\]

并为这个实际 power 在 `STD_IOL_EYE_2024` 中求对应：

\[
\boxed{Q_k(P_{ijk})}
\]

不得把某一个 +20 D 或其他固定度数得到的 conic 机械复制到所有配置。

MVP 工程流程：

1. 加载 Base + Cornea；
2. 插入该 Platform 的基础材料、中心厚度和基础弯曲形式；
3. 暂设主要 conic 为 \(Q=0\)，不加入 EDOF residual；
4. 调整基础曲率，使单焦 carrier 的最佳远焦位于固定视网膜；
5. 得到当前 \(P_{ijk}\) 与基础几何；
6. 将该 carrier 放入 `STD_IOL_EYE_2024`，使用冻结的 6.0 mm 标准眼校准孔径；
7. 固定基础 power/几何，优化 conic，使相对于同 power `ZERO_HOA_PARAXIAL_REFERENCE` 的基础球差达到该平台 6 mm 目标；
8. 将 carrier 放回实际 Base + Cornea 检查远焦；
9. 若 conic 引起明显远焦偏移，允许进行 1–2 次小量工程回查：更新基础 power 后必须重新求对应 conic；
10. 满足合理远焦和基础球差要求后，冻结该 physical carrier。

MVP 不要求建立完整解析 \(Q(P)\) 数据库。

---

## 2.5 matched MONO / EDOF 配对规则

每个平台建立一个严格匹配的单焦 carrier 对照：

\[
MONO_{\rm WFS}=Carrier_{\rm WFS}
\]

\[
MONO_{\rm RAD}=Carrier_{\rm RAD}
\]

\[
MONO_{\rm HOA}=Carrier_{\rm HOA}
\]

对应 EDOF 状态：

\[
EDOF_k=Carrier_k+Residual_k(r)
\]

同一 `Base × Cornea × Platform` 中，MONO 和 EDOF 必须具有相同：

- carrier power；
- 基础曲率；
- conic；
- 中心厚度；
- 材料；
- 光学直径；
- IOL 前表面位置；
- tilt/decentration 状态。

唯一允许的光学设计差异是是否加入该平台冻结的 EDOF residual。

EDOF residual 在冻结时应去除不需要的 piston 和整体 defocus 成分，使其表示 EDOF 功能结构而不是重新定义基础 IOL 度数。

physical carrier 冻结后：

> **禁止为了让 EDOF 的远焦更漂亮而单独调整 EDOF power 或 conic。**

如果加入 residual 后最佳远焦发生小量变化，该变化作为：

\[
\boxed{\Delta F_{\rm residual}}
\]

记录为结果，而不重新设计一枚不同 carrier。

MVP 假设同一平台冻结 residual 可在本研究实际使用的 carrier power 范围内复用；若主实验后发现明显非物理失配，再作为后续扩展研究处理。

---

## 2.6 nominal 主实验矩阵

physical carrier 数量：

\[
2\ \text{bases}
\times3\ \text{corneas}
\times3\ \text{platforms}
=
\boxed{18}
\]

分析配置：

\[
2\ \text{bases}
\times3\ \text{corneas}
\times3\ \text{platforms}
\times2\ \text{optic states}
\times2\ \text{pupils}
=
\boxed{72}
\]

其中：

- Bases = `LB_AL2395`, `ATC_M3_AL24477`；
- Corneas = `A0`, `B0`, `C0`；
- Platforms = `WFS`, `RAD`, `HOA`；
- Optic States = `MONO`, `EDOF`；
- Pupils = `EPD3`, `EPD5`。

nominal 主实验统一：

\[
\boxed{\lambda=555\ \mathrm{nm}}
\]

并满足：

- IOL decentration = 0；
- IOL tilt = 0；
- 角膜、STOP、IOL 共轴；
- 不引入角膜治疗区偏心；
- 不引入瞳孔中心漂移；
- 不加入微单视额外 defocus target。

EPD3 与 EPD5 是**性能评估条件**而不是 standard-eye carrier SA calibration condition。EPD3 保留较小明视瞳孔下的实际性能与天然景深效应，EPD5 用于更充分暴露角膜/IOL 球差与 EDOF 机制；两者均不反向改变 6 mm 下冻结的 carrier 基础球差定义。

---

## 2.7 主要科学输出与比较原则

每个 nominal 配置至少需要获得：

- through-focus MTF；
- MTFa；
- 基于 Zemax 光学结果的 VSOTF / 视觉加权指标；
- Huygens PSF；
- 最佳远焦峰值质量；
- DOFrel 所需贯焦数据；
- DOFabs 所需贯焦数据；
- 全眼 \(C_4^0\)；
- 全眼 \(C_6^0\)；
- HOA RMS；
- 必要的 pupil / corneal / IOL footprint 记录；
- `ΔF_residual`。

全眼 Zernike 必须由完整全眼模型重新光线追迹后拟合，禁止用：

\[
C_{4,cornea}^0+SA_{IOL}^{STD}
\]

直接代替全眼球差。

主机制比较采用同一平台内配对差：

\[
\boxed{
\Delta M_{ijkp}
=
M(EDOF_k)-M(MONO_k)
}
\]

其中 \(M\) 可为 MTFa、VSOTF、DOF、distance peak、像差或其他已定义指标。

软件还可以输出 WFS、RAD、HOA 三个平台完整 surrogate 的绝对结果，但这些差异应解释为“平台特异 carrier + EDOF residual”的综合表现，不能全部归因于 residual 本身。

---

# 3. 目标用户

| ID | Role | Need |
| --- | --- | --- |
| URD-ROLE-001 | 光学研究者 / 项目负责人 | 通过少量 GUI 操作建立、验证、运行和重跑全套 Zemax MVP，而不是手工维护几十个配置。 |
| URD-ROLE-002 | 模型维护者 / 后续开发者 | 能追踪每个 `.zos` 和结果对应的输入参数、冻结参数和运行状态，并安全重跑失败阶段。 |

第一版主要面向单个研究者在单台 Windows 工作站使用。

---

# 4. 核心用户场景

| ID | Scenario | Expected Outcome |
| --- | --- | --- |
| URD-SCEN-001 | 启动软件并连接 OpticStudio | GUI 显示安装路径、连接状态和 API license 状态；成功后获得可用 Primary System。 |
| URD-SCEN-002 | Build | 建立/保存标准眼、两个主基座、REF_MONO、A0/B候选/C0 和 IOL surrogate 所需 Zemax 文件。 |
| URD-SCEN-003 | Validate | 执行关键几何、标准眼、carrier、pair 和配置完整性检查，明确显示 PASS/FAIL。 |
| URD-SCEN-004 | B0 first scan | 在 LB + REF_MONO 环境运行五个 B 候选，导出比较结果，由第一轮实际结果确定并锁定 B0。 |
| URD-SCEN-005 | Build carriers | 自动得到 18 个 `Base × Cornea × Platform` physical carrier locks。 |
| URD-SCEN-006 | Run nominal | 自动生成并运行 72 个 nominal 配置，导出 CSV、`.zos` 和图像。 |
| URD-SCEN-007 | Rerun | 选择失败阶段、单个 carrier 或单个 nominal 配置进行重跑，不必重新执行整套实验。 |
| URD-SCEN-008 | Audit | 从 CSV、`.zos`、图像和日志追溯任一结果的 Base、Cornea、Platform、Optic State、Pupil 和关键参数。 |

---

# 5. 极简 GUI 需求

MVP 必须提供基于 **CustomTkinter** 的极简桌面 GUI。GUI 是主要用户入口；不要求提供完整 CLI 产品体验。

GUI 只解决研究流程控制，不发展为复杂光学编辑器。

## 5.1 GUI 最小功能

主窗口至少包含：

1. **OpticStudio 安装路径**
   - 显示当前路径；
   - 可浏览或手动修改；
   - 默认支持：
     `C:\Program Files\Ansys Zemax OpticStudio 2026 R1.00`。

2. **项目目录**
   - 用户选择输出根目录；
   - `.zos`、CSV、图像和日志均保存于该项目目录下。

3. **操作选择**
   - `Build`
   - `Validate`
   - `B0 Scan / Lock`
   - `Build Carriers`
   - `Run 72 Nominal`
   - `Rerun Selected`

4. **重跑选择**
   - 可以选择阶段；
   - 可以选择单个配置 ID；
   - 失败记录可直接作为重跑目标。

5. **状态和进度**
   - 当前阶段；
   - 当前配置 ID；
   - completed / failed / remaining；
   - 简单进度条。

6. **日志区域**
   - 显示关键事件、PASS/FAIL、错误信息和输出位置；
   - 不要求复杂日志检索界面。

7. **运行控制**
   - Start；
   - Open Output Folder。
   - MVP 不提供 Pause/Cancel；失败后通过已有 Rerun 机制恢复，运行中的第二个长任务不得并发启动。

## 5.2 GUI 明确不做

MVP GUI 不提供：

- 在 GUI 内手工编辑完整 Lens Data Editor；
- 复杂二维/三维交互光学图；
- 多用户权限；
- 云端任务管理；
- 工作流拖拽编排；
- 患者数据库。

---

# 6. 功能需求

| ID | Requirement | Priority |
| --- | --- | --- |
| URD-REQ-001 | 软件必须通过 ZOS-API 创建新的 OpticStudio Application，取得 Primary System，并在程序结束时可靠关闭会话。 | must |
| URD-REQ-002 | 软件必须检查 OpticStudio 安装目录、ZOS-API 初始化和 API license；失败时明确报错，不继续生成伪成功结果。 | must |
| URD-REQ-003 | OpticStudio 安装目录必须可在 GUI 中配置；默认支持 2026 R1.00 常规安装路径。 | must |
| URD-REQ-004 | 软件必须使用 Sequential Mode 完成本 MVP 的模型生成和分析。 | must |
| URD-REQ-005 | 软件必须生成/保存 `LB_AL2395` 和 `ATC_M3_AL24477` 两个主基座，并检查 AL、STOP、IOL 参考位置和介质。 | must |
| URD-REQ-006 | 软件必须生成/保存 `STD_IOL_EYE_2024`，并在 6.0 mm entrance pupil 下校验 +0.258 μm 角膜球差目标、5.15±0.10 mm IOL footprint、n=1.336 和约 546 nm 校准条件；平台 IOL `SA_base` 与 `Q(P)` 必须在同一 6 mm 标准眼下相对 `ZERO_HOA_PARAXIAL_REFERENCE` 定义。 | must |
| URD-REQ-007 | 软件必须生成平台独立的 `REF_MONO_CORNEA_LOCK`，供 B0 first scan 使用；它不进入 72 配置。 | must |
| URD-REQ-008 | 软件必须生成并冻结 A0，其 nominal 科学目标符合本 URD 第 2.2 节。 | must |
| URD-REQ-009 | 软件必须生成五个 B 候选并在 `LB_AL2395 + REF_MONO_CORNEA_LOCK` 下完成第一轮扫描；按第 2.2 节 `Q_lock`/A0 阈值/gate/ranking 生成可复现推荐，用户确认或记录 override reason 后写入 B0 lock。 | must |
| URD-REQ-010 | 软件必须生成并冻结 C0，固定 `D_near=3.0 mm`、`ADD=+1.75 D`、`D_OZ=6.5 mm`、`w_T=0.75 mm`。 | must |
| URD-REQ-011 | A0/B0/C0 冻结后，主实验流程不得因 WFS/RAD/HOA 结果自动重新优化角膜。 | must |
| URD-REQ-012 | WFS/RAD/HOA 必须保留平台特异 carrier；其基础球差工程目标分别约 −0.20/−0.27/0 μm，并统一定义于 `STD_IOL_EYE_2024` 的 6.0 mm calibration pupil。 | must |
| URD-REQ-013 | 对每个 `Base × Cornea × Platform`，必须求独立的 `P_ijk`，并在标准眼求对应 `Q_k(P_ijk)`；不得跨 power 机械复制同一 conic。 | must |
| URD-REQ-014 | power–conic 求解允许少量工程回查，但 physical carrier 一旦冻结后不得因 EDOF residual 再单独改变 EDOF power/conic。 | must |
| URD-REQ-015 | 软件必须建立 `MONO_WFS/RAD/HOA` 与相应 EDOF 状态；同一平台 pair 的 carrier 参数必须完全相同，唯一设计差异为冻结 residual。 | must |
| URD-REQ-016 | EDOF residual 的冻结记录必须明确其平台 ID，并通过实际 payload 验证其 piston/global-defocus 去除；在真实 carrier 使用前还必须对每个平台实际 power 集合的 low/median/high 代表点完成跨 power 校准 gate；加入 residual 后的焦移以 `ΔF_residual` 输出。 | must |
| URD-REQ-017 | 软件必须生成恰好 18 个唯一 physical carrier locks。 | must |
| URD-REQ-018 | 软件必须生成恰好 72 个唯一 nominal analysis configurations。 | must |
| URD-REQ-019 | 72 个主配置必须全部为 555 nm、EPD 3/5 mm、centered、tilt=0、decentration=0、无角膜偏心、无微单视附加 defocus；EPD3/EPD5 只作为性能评估条件，不改变 6 mm carrier SA calibration。 | must |
| URD-REQ-020 | 软件必须使用 Zemax 作为光学计算和主要数值 oracle；贯焦只通过分析层的物方/入射 vergence 改变实现，固定 retina、IOL power/conic、ELP 和实体面型；VSOTF/视觉加权指标基于 Zemax 光学结果，不引入第二套光学传播引擎。 | must |
| URD-REQ-021 | 每个 nominal 配置至少保存 through-focus MTF、MTFa、VSOTF、Huygens PSF、最佳远焦、DOF 数据、全眼 C4^0/C6^0、HOA RMS 和关键 footprint；贯焦结果同时保存 retina-anchored 原始 vergence 轴与只用于曲线形态比较的 shape-recentered 轴，后者不得改变任何实体模型。 | must |
| URD-REQ-022 | 软件必须自动形成每个平台 `EDOF − MONO` 的 matched-pair 差值结果表。 | must |
| URD-REQ-023 | 主数据结果必须输出 CSV；关键模型/配置必须保存 `.zos`；关键光学结果必须导出图像。 | must |
| URD-REQ-024 | 软件必须保存运行日志，并使结果可追溯到 Base、Cornea、Platform、Optic State、Pupil、carrier power、conic 和对应 `.zos`。 | must |
| URD-REQ-025 | 任一关键步骤失败时必须将该任务标记为 failed，不得计入 completed；用户可通过 GUI 单独重跑。 | must |
| URD-REQ-026 | 相同输入、相同软件和 OpticStudio 版本下，重复运行应得到相同冻结参数和实质一致的主要数值结果。 | must |
| URD-REQ-027 | 所有界面、文件元数据和报告必须把 WFS/RAD/HOA 称为机制性 surrogate，不得声称是商业产品精确处方。 | must |
| URD-REQ-028 | 软件必须提供 CustomTkinter 极简 GUI，实现 Build / Validate / B0 Scan / Build Carriers / Run / Rerun、进度、日志和输出目录访问。 | must |

---

# 7. 输出要求

MVP 对外主要交付格式固定为：

\[
\boxed{CSV + .zos + 图像}
\]

日志可使用普通文本文件。

## 7.1 CSV

至少应形成：

- cornea lock / B0 scan 数据；
- physical carrier lock 表；
- 72-config manifest；
- nominal results；
- matched-pair `EDOF − MONO` results；
- validation summary；
- failed/rerun status。

CSV 必须包含稳定的配置 ID，不依赖人工从文件名猜测实验条件。

## 7.2 `.zos`

至少保存：

- `STD_IOL_EYE_2024`；
- 两个主基座；
- A0/B0/C0 锁定模型或可独立复现它们的关键 `.zos`；
- 18 个 physical carrier 的可追溯模型；
- 72 nominal 中需要留档的完整分析模型或确定性生成后的快照。

允许在后续设计阶段决定如何在“避免 72 份冗余文件”和“便于审计”之间取最简单方案，但用户必须能够从输出恢复任一 nominal 配置。

## 7.3 图像

至少导出关键 Zemax 结果图，包括：

- through-focus 曲线图；
- MTF 图；
- PSF 图；
- 必要的标准眼或验证图。

这些图像属于研究结果输出。投稿级重新排版、统计制图和论文图形设计不属于 MVP。

---

# 8. 验收条件

| ID | Related | Acceptance statement |
| --- | --- | --- |
| URD-AC-001 | REQ-001~003 | 有效安装路径和 API license 下，GUI 能成功连接 OpticStudio、取得 Primary System，并在结束时关闭 Application；无效路径/license 时明确失败。 |
| URD-AC-002 | REQ-005 | 两个主基座分别记录 AL=23.950 mm 和 24.477 mm，并满足 3.15 mm STOP、4.50 mm IOL 前表面参考位置的项目定义。 |
| URD-AC-003 | REQ-006 | `STD_IOL_EYE_2024` 的 validation CSV 显示 EPD=6.0 mm 校准状态、模型角膜 `C4^0≈+0.258 μm @ 6 mm`、IOL footprint `5.15±0.10 mm @ 6 mm`、介质 n=1.336、校准波长约 546 nm，并可构造同 power/geometry 的 `ZERO_HOA_PARAXIAL_REFERENCE`。 |
| URD-AC-004 | REQ-007~011 | 软件可生成 REF_MONO、A0、五个 B 候选、C0；B0 first scan 输出 `Q_lock`、A0 阈值、distance gates 和确定性推荐，用户确认/override reason 后锁定；主实验后 A0/B0/C0 lock 不变化。 |
| URD-AC-005 | REQ-010 | C0 lock 明确记录 3.0 mm 中央近用区、+1.75 D ADD、6.5 mm OZ 和 0.75 mm 过渡宽度。 |
| URD-AC-006 | REQ-012~014 | WFS/RAD/HOA carrier 在 6.0 mm standard-eye calibration pupil 下记录各自基础 SA target；每个实际 P_ijk 有对应求得 conic，程序不存在“所有 power 共用一个 Q”的静默路径。 |
| URD-AC-007 | REQ-015~016 | 任一 matched pair 中 MONO 与 EDOF 的 carrier power、R、Q、CT、材料、位置完全相同；EDOF residual 是唯一设计差异；residual payload 通过 piston/defocus 与 low/median/high power gate；输出包含 ΔF_residual。 |
| URD-AC-008 | REQ-017 | physical carrier lock CSV 恰好包含 18 个唯一 `Base × Cornea × Platform` 组合。 |
| URD-AC-009 | REQ-018~019 | nominal manifest 恰好包含 72 个唯一配置，并且全部满足 555 nm、EPD3/EPD5、centered、tilt=0、decentration=0；其 EPD3/EPD5 仅用于性能评估。 |
| URD-AC-010 | REQ-020~022 | 每个成功配置都存在统一的 Zemax 光学结果；贯焦不改变实体模型，并同时输出 retina-anchored 与 shape-recentered 坐标；最终结果 CSV 可形成同平台 EDOF−MONO 配对差值。 |
| URD-AC-011 | REQ-021~024 | 成功配置存在 CSV 记录、可追溯 `.zos` 和对应关键图像，且能从配置 ID 找到 Base/Cornea/Platform/State/Pupil/carrier 参数。 |
| URD-AC-012 | REQ-025 | 人为制造一个配置失败后，GUI 显示 failed 而非 completed，并允许只重跑该配置。 |
| URD-AC-013 | REQ-026 | 相同输入和同一 OpticStudio 版本重复执行，离散锁定参数完全一致，主要分析数值仅有合理数值精度差异。 |
| URD-AC-014 | REQ-027 | 输出和 GUI 使用 `WFS-like / RAD-like / HOA-like surrogate` 或等价机制名称，不把模型标成商业产品精确处方。 |
| URD-AC-015 | REQ-028 | 用户无需编辑代码即可从 GUI 完成 Build、Validate、B0 Scan/Lock、Build Carriers、Run 72 和 Rerun Selected，并可看到基本进度、日志和输出目录。 |

---

# 9. Out of Scope

以下内容明确不阻塞 MVP：

| ID | Item | Reason |
| --- | --- | --- |
| URD-OOS-001 | 患者特异角膜地形图/断层数据导入、患者级 Grid Sag 重建 | 属于后续外部验证。 |
| URD-OOS-002 | 角膜治疗区偏心、瞳孔中心漂移的系统扫描 | MVP 先研究轴对称机制。 |
| URD-OOS-003 | IOL 偏心/倾斜稳健性正式矩阵 | 结构可预留，但不进入首轮 72 配置。 |
| URD-OOS-004 | 多色光、材料完整色散、LCA 系统分析 | 首轮使用单色机制隔离。 |
| URD-OOS-005 | 衍射型、多焦衍射级次或混合衍射 IOL | 会增加新的相位与能量分配变量。 |
| URD-OOS-006 | 精确逆向重建 Vivity/PureSee/LuxSmart 商业制造面型 | 本项目研究机制 surrogate。 |
| URD-OOS-007 | 临床 IOL 推荐、患者术式推荐、医疗器械决策支持 | 软件仅用于科研。 |
| URD-OOS-008 | 复杂 GUI、Web 服务、多人权限、云端/集群任务系统 | MVP 只需要极简本地 GUI。 |
| URD-OOS-009 | 投稿级统计图、论文自动撰写、自动临床结论生成 | 与 Zemax MVP 自动化分离。 |
| URD-OOS-010 | 为全部可能 power 预计算完整 Q(P) 数据库 | 只按本研究实际 power 求解。 |
| URD-OOS-011 | 为获得更漂亮的 3×3 结果而回调已冻结 A0/B0/C0、carrier 或 residual | 会破坏机制比较。 |
| URD-OOS-012 | B0 复杂多目标自动优化器 | 第一轮只需五个候选扫描并选择代表性 B0。 |
| URD-OOS-013 | C0 的 wT 优化 | MVP 直接固定 wT=0.75 mm。 |
| URD-OOS-014 | EDOF residual 随 power 变化的完整不确定性研究 | 首轮假设 residual 可在实际 power 范围复用。 |

---

# 10. 软件与研究约束

| ID | Type | Constraint |
| --- | --- | --- |
| URD-CON-001 | platform | MVP 在能够运行 Ansys Zemax OpticStudio 2026 R1 的 Windows 本地工作站运行。 |
| URD-CON-002 | license | 需要有效 ZOS-API license。 |
| URD-CON-003 | connection | ZOS-API 连接流程必须覆盖安装目录检查、NetHelper 初始化、ZOSAPI 加载、CreateNewApplication、license 检查、PrimarySystem 获取和显式关闭；具体类封装留给后续设计。 |
| URD-CON-004 | UI | GUI 使用 CustomTkinter，并保持极简。 |
| URD-CON-005 | optical engine | Zemax 是唯一主光学模拟引擎和分析 oracle；软件不引入第二套独立光学追迹引擎。 |
| URD-CON-006 | reproducibility | 每次运行必须记录程序版本、OpticStudio 版本、输入条件和冻结参数。 |
| URD-CON-007 | offline | 核心计算不依赖互联网服务。 |
| URD-CON-008 | simplicity | 优先可读、可调试、可重复，不为未来患者级建模、并行集群或复杂 GUI 预先增加框架。 |

---

# 11. Assumptions

| ID | Assumption | Review trigger |
| --- | --- | --- |
| URD-ASM-001 | 第一版由单个研究者在单台工作站使用。 | 出现多人协作或服务器需求。 |
| URD-ASM-002 | 默认 OpticStudio 版本为 2026 R1.00，安装路径可由 GUI 修改。 | 更换 OpticStudio 主版本。 |
| URD-ASM-003 | B0 由 +0.10～+0.30 μm 的五点第一轮扫描确定，人工确认代表性解即可。 | 五个候选均不能产生合理 B 原型。 |
| URD-ASM-004 | C0 过渡宽度固定 0.75 mm。 | 后续敏感性研究显示存在明显非物理问题。 |
| URD-ASM-005 | 冻结 EDOF residual 可跨本研究实际 carrier power 使用。 | 主实验出现明显 power-dependent 失配。 |
| URD-ASM-006 | 贯焦扫描具体范围、步长、DOFrel 比例、DOFabs 阈值、Zemax 分析采样等在 MDD/TDD 实现前固定即可，不需要扩展 URD。 | 进入具体分析实现。 |
| URD-ASM-007 | VSOTF/视觉加权结果以 Zemax 输出为光学数据源；若 OpticStudio 当前 API 不直接提供最终标量，可在程序内对 Zemax OTF 数据做确定性后处理，但不使用另一套光学模拟。 | MDD/TDD 确认具体 ZOS-API 能力。 |

---

# 12. 已关闭的需求决策

以下问题已经由项目负责人确认，不再作为 Open Questions：

| ID | Decision |
| --- | --- |
| URD-DEC-001 | MVP 使用 CustomTkinter 极简 GUI，而不是纯 CLI。 |
| URD-DEC-002 | 主要结果交付格式固定为 CSV + `.zos` + 图像。 |
| URD-DEC-003 | 光学分析以 Zemax 为主引擎和 oracle；VSOTF/视觉加权计算基于 Zemax 光学结果。 |
| URD-DEC-004 | B0 不预设 nominal 值，由第一轮五点实际扫描确定并冻结。 |
| URD-DEC-005 | C0 nominal `wT=0.75 mm`，不在 MVP 中继续优化。 |
| URD-DEC-006 | 主实验使用三套平台匹配 MONO controls，而不是一个共同球差中性单焦对照。 |
| URD-DEC-007 | nominal 主数据集为 18 physical carriers 和 72 analysis configurations。 |
| URD-DEC-008 | MVP 不实现 Pause/Cancel；长任务串行执行，失败恢复依赖任务/配置级 Rerun。 |
| URD-DEC-009 | `STD_IOL_EYE_2024` 的角膜 `C4^0`、IOL footprint、`SA_base` 与 `Q(P)`/`ZERO_HOA` 校准统一使用 6.0 mm entrance pupil；主实验 EPD3/EPD5 仅用于性能评估，不反向改变 carrier 设计。 |

---

# 13. URD Completion Gate

- [x] 目标用户已知。
- [x] MVP 科学问题和模型边界已内嵌于本 URD。
- [x] 两个轴向基座定义完整。
- [x] A0/B0/C0 的 nominal 规则与冻结规则完整。
- [x] `REF_MONO_CORNEA_LOCK` 的用途和边界明确。
- [x] `STD_IOL_EYE_2024` 的 MVP 验收锚点明确，且 6 mm 设计/标定条件与 EPD3/EPD5 性能条件已分离。
- [x] WFS/RAD/HOA 基础 carrier 与 SA 目标明确。
- [x] power–conic 规则和 matched MONO/EDOF 规则明确。
- [x] 18 physical carriers / 72 nominal configurations 明确。
- [x] 主分析输出和平台内 `EDOF − MONO` 比较明确。
- [x] CustomTkinter 极简 GUI 范围明确。
- [x] CSV + `.zos` + 图像输出明确。
- [x] Out of Scope 与后续扩展分离。
- [x] 原 Open Questions 与 standard-eye calibration pupil 决策已关闭。
- [x] 本次 v1.4 仅改变 standard-eye calibration 科学条件，不改变现有 ADD/MDD 架构拆分与 lock boundary。

## Checkpoint Result

\[
\boxed{URD\ APPROVED\ FOR\ ADD}
\]

本 URD 已作为独立、完整、自包含的 MVP 需求基线。后续 ADD/MDD/TDD 可以选择实现结构和具体 ZOS-API 调用方式，但不得静默改变本文件定义的科学模型、冻结规则、72 配置矩阵、matched-pair 原则或主要输出范围。如需改变这些内容，应先修订 URD 版本。