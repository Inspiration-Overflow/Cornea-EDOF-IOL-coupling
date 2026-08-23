# Model Revision R2/R3 — Web 端独立审核

> 日期：2026-08-21  
> 分支：`feat/model-revision-binary4-physical-pupil`  
> 本地执行 HEAD：`f88a8e27e8a96b2852c648dde04649ecbefa34c9`  
> 审核结论：**R2/R3 ACCEPT；允许进入 R4 pilot 的 Web 端设计与实现**  
> PR 状态：继续保持 draft；R4/R5 完成前不得合并

## 1. 输入证据

本次审核基于本地 Codex 完整执行：

```text
phase = MODEL-REVISION-R2-R3
schema_version = 2
baseline_id = MVP_2026_v2
code_commit = f88a8e27e8a96b2852c648dde04649ecbefa34c9
passed = true
```

本地工作树干净，单元测试 `244 passed`。本次 run 从 R2 revised base 开始完整重建，没有从第一次 native FFT 失败位置断点续跑。

canonical evidence 位于本地：

```text
project_mvp_2026_v2_zmx/diagnostics/model_revision/r2_r3/
  MODEL_REVISION_R2_R3_EVIDENCE.json
```

聊天中回传的 JSON 仅作为审核副本；正式归档时以本地实际 JSON 文件字节与 SHA-256 为准。

## 2. R2 geometry 审核

### 2.1 physical STOP

两套 revised base 与完整 carrier 均回读：

```text
Aperture Type = FloatByStopSize
STOP surface = 3
3 mm physical pupil -> STOP Semi-Diameter = 1.5 mm
```

符合 R0 合同。

### 2.2 clear semi-diameter

完整 analytical carrier 回读：

```text
anterior cornea = 5.0 mm
posterior cornea = 5.0 mm
IOL anterior = 3.0 mm
IOL posterior = 3.0 mm
retina = 5.0 mm
```

R2 base scaffold 中 `iol_post_semi_diameter_mm = null` 是因为该阶段尚未插入完整双面 IOL；进入 analytical carrier 后 posterior IOL 已明确回读为 3.0 mm，因此不构成缺陷。

### 2.3 retina

Liou–Brennan：

```text
IMAGE identity = true
Surface = Standard
Ry = -12.000 mm
Qy = 0
```

Atchison Model 1 @ SR=-3 D：

```text
IMAGE identity = true
Surface = Biconic
Ry = -12.732 mm
Qy = +0.199
Rx = -12.628 mm
Qx = +0.192
```

均与 R1 source lock 一致。

## 3. analytical Q0 carrier 审核

本阶段只要求建立可用于 R3 退化等效验证的 Q=0 analytical carrier，不把其度数当作 R4 representative carrier。

回读：

```text
LB_AL2395:
  Rant = +9.82075967655328 mm
  Rpost = -9.82075967655328 mm
  power = 25.14343454261801 D
  Qant/Qpost = 0/0
  AL = 23.950 mm

ATC_M3_AL24477:
  Rant = +10.6607177397636 mm
  Rpost = -10.6607177397636 mm
  power = 23.17030863309223 D
  Qant/Qpost = 0/0
  AL = 24.477 mm
```

两者保持 symmetric biconvex、固定 retina 与固定 AL，focus residual 只有约 0.5–0.6 µm 的 image-space 数量级，满足本阶段 scaffold 目的。

## 4. Binary Optic 4 structural readback

6 个 degenerate Binary4 MONO 均成功保存、reload 并读回。

冻结 topology：

```text
WFS: 0/.55/.65/.87/1.05/3.00 mm, anterior
RAD: 0/.50/.90/1.10/1.40/2.50/3.00 mm, posterior
HOA: 0/.90/1.10/3.00 mm, anterior
```

共同结构：

```text
Na = 3
Np = 0
M_j = 0
p2 = 0
p4 = 0
p6 = 0
zone R/Q = analytical carrier R/Q
```

代码在保存后对 Nz/Na/Np、boundary、R/Q、order、p2/p4/p6 和 IOL refractive index 都执行 hard readback；因此进入 equivalence comparison 前已经通过结构 gate。

## 5. 12 组 analytical ↔ degenerate Binary4 equivalence

覆盖：

```text
2 bases × 3 platform topology × 2 physical pupils = 12 comparisons
```

12/12 均 `passed=true`，且 `findings=[]`。

跨全部 12 组的最大误差为：

```text
max |Δsag|      = 1.5160095401256513e-13 mm
max |ΔEFFL|     = 5.861977570020827e-13 mm
max |ΔC4^0|     = 1.0413336859471656e-12 µm
max |ΔC6^0|     = 6.706683819412973e-13 µm
max |Δgrid MTF| = 5.725975249504245e-12
```

对应 gate 均为 `1e-6`。实际误差比门槛低约 6 个数量级以上，可解释为序列化/浮点层面的数值底噪，而不是有意义的光学差异。

因此 R3 的核心命题成立：

> 在固定 topology、Np=0、M=0、p2/p4/p6=0、每区 R/Q 等于 analytical carrier 时，Binary Optic 4 MONO 与原 analytical carrier 在本项目所需精度内等效。

## 6. MTF backend exception 的审核结论

第一次本地 run 在 `New_FftMtf()` 处因 OpticStudio 2026 R1 / Python.NET 无法创建 `AS_FftMtf/AS_Base` 而硬失败。该失败发生在 revised bases、analytical carriers 与首个 Binary4 MONO 已成功生成之后。

修订后只替换 acquisition backend：

```text
MFE MTFA/MTFS/MTFT
Grid = 1
sampling = 128
frequency = 0–100 cyc/mm, 5 cyc/mm step
Data Type = modulation
```

并明确记录：

```text
native_fft_analysis_used = false
```

此变更不修改模型几何、机制、瞳孔、retina、Binary4 topology 或 equivalence tolerance，因此接受为工作站/API 兼容性例外，而不是科学合同变更。

R4 及后续 revision path 的 MTF audit 继续使用这条已验证的 MFE Grid=1 路径，禁止重新引入 `AS_FftMtf` 依赖。

## 7. 聊天回传副本的字段省略

聊天中回传的长 JSON 副本里，少数重复零值字段/重复 tolerance 字段被省略，例如个别 zone 的 `alpha_p6_native` 和部分 ATC comparison 的 `grid_mtf_tolerance`。

当前 HEAD 的生成代码中这些字段由 dataclass `asdict()` 与统一 comparison payload 固定产生；同时 structural hard gate 已直接读取并验证 p6=0。故本审核将该现象判断为聊天/Codex 长文本回传层的呈现省略，而不是 canonical 本地 evidence 文件缺字段。

处理原则：

1. 不因此重跑 R2/R3；
2. 本地实际 JSON 是 canonical evidence；
3. 在 post-human-audit dataset 正式 freeze 前，应把实际 JSON 文件连同 SHA-256 纳入归档，而不是从聊天文本重建。

## 8. Web 决策

```text
R2 physical-pupil / retina geometry     ACCEPT
R3 Binary4 structural replay            ACCEPT
R3 analytical equivalence               ACCEPT
MTF acquisition compatibility exception ACCEPT
R2/R3 overall                           ACCEPT
```

允许进入：

```text
R4 = representative ~+20 D mechanism-fit pilot
```

但仍不允许：

```text
24-carrier expansion
96-config rerun
PR merge
```

R4 必须继续遵守 mechanism-first：先拟合 WFS/RAD/HOA source-locked mechanism，再做 geometry / standard-eye / MTF sanity；不得以 MTF 反向优化机制参数。
