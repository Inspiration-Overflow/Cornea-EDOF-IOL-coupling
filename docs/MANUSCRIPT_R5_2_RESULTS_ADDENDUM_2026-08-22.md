# 稿件结果补充：R5.2 与 R6/R7 载体/机制验证 — 2026-08-22

> 本补充用于记录主研究生产前的 R5.2 power-portability 与 R6/R7 serialized carrier/mechanism validation。它不是主研究结果矩阵的替代，也不建立新的 scientific lock。

## 可纳入 Methods / Validation subsection 的文字

在正式主研究生产之前，我们对冻结的 R5.2 IOL 机制处方进行了独立的载体可移植性与序列化验证。该验证包含24个 physical carrier，覆盖两个基础模型眼、四种角膜状态（N0、A0、B0、C0）和三类 IOL 机制 surrogate（WFS-like、RAD-like、HOA-like）。这一24-carrier集合属于 R6/R7 carrier/mechanism validation 空间，目的在于检验冻结 residual 在实际功率载体上的重放、Binary4 序列化、几何与机制一致性；不等同于后续主研究配置矩阵。

对于 HOA-like，R5.2 保留 R5.1 的 power-normalized conic 规则，并以 +20.0 D、carrier radius `12.357387811201875 mm` 为冻结参考。active zone 1 与 zone 2 的 native A6 按固定顺序逐区确定，使各 active-zone 外边界处完整的 `EDOF−MONO` Binary4 sag difference 与 +20 D 参考保持一致。完整 sag 包含精确 conic sag、native A4/A6 以及 Binary4 自动 C0 offset；zone 2 在 zone 1 更新后求解，因此第二个边界条件包含已更新的 zone-1 C0 状态。HOA-like 使用冻结的 `q_ant=0` carrier contract；+20 D 处方保持既有 R5.1 prescription 不变，WFS-like 与 RAD-like 继续沿用既有 R5.1/R5 prescription。R5.2 的 A6 选择不读取 mechanism gate 输出，不使用 optimizer、least-squares refit 或 automatic power-specific refit。

## 可纳入 Results 的文字

完成的 R6/R7 本地序列化 evidence 包含全部24个预期 carrier。三个平台的 carrier power 范围均为 `15.01660005067162–25.030159135314852 D`，evidence 所记录的 `median_lower_d` 均为 `20.012738203961458 D`。

九项预设 local validation checks 全部通过：24/24 carrier 完整存在、standard-eye spherical-aberration replay 通过、WFS-like/HOA-like serialized mechanism fidelity 通过、RAD-like real-POWP identity regression 通过、global defocus 通过、实际眼3 mm和5 mm pupil ray health 通过、Binary4 geometry 通过、预选 low/median/high full standard-eye audit 通过，并且总体 `local_r6_r7_passed=true`。因此，冻结的 R5.2 prescription 在本次24-carrier R6/R7 validation space 内满足预设的序列化载体/机制验证合同。

这些结果应与较早的 analytical precheck 明确区分。Analytical precheck 检验的是 R5.2 确定性 A6 规则、完整边界 sag invariant、C0 顺序以及离线 mechanism proxy；本段报告的结果则来自随后完成的本地 serialized R6/R7 validation。前者提供规则层面的预检，后者提供实际 R6/R7 序列化路径的验证证据，二者不能互相替代。

## 可纳入 Discussion / Reproducibility note 的文字

本次 R6/R7 验证支持将 R5.2 作为后续研究所使用的冻结 HOA-like power-portability 规则：其 zone-1→zone-2 顺序、`q_ant=0`、WFS/RAD identity 以及禁止 gate-feedback/optimizer refit 的约束在源代码与完成版 evidence 中一致。该验证的作用是确认载体与机制层面的可重放性，而不是评价不同角膜×IOL 组合的临床优劣，也不是新的主研究效应分析。

用于最终审查的 evidence JSON SHA-256 为 `1ebf196d51d68e5d6f573a36c9fd398d705ebaf9d63b7ad49c70670c432ce06f`。任务 dispatch 记录该 evidence 的 `artifact_sha256` 映射包含340项，并已在 dispatch 前由本地 orchestrator 独立匹配。Evidence 自身标记 `formal_artifact=false`，因此这一完整性记录应被理解为 R6/R7 验证的可追溯证据，而不是后续生产阶段的正式 artifact。

R6/R7 evidence 同时明确保持 progression lock：`manual_web_review_required=true`、`automatic_progression_allowed=false`，且 `next_gate="STOP for Web R6/R7 review; R8 remains locked"`。因此，24-carrier validation 的通过只支持本阶段的验证结论，不构成自动进入 R8 或 96-config production 的授权。

## 稿件整合边界

本补充可作为 Methods 中的“预生产机制验证”、Results 中的“R5.2/R6-R7 validation”以及 Discussion/Reproducibility 中的验证说明使用。整合时应保留以下边界：

- 不把 N0/A0/B0/C0 的24-carrier validation space 写成主研究效应矩阵；
- 不把 analytical precheck 写成 OpticStudio serialized validation；
- 不把本阶段的 PASS 写成 R8/96-config production 已执行或已放行；
- 不把 `formal_artifact=false` 的 R6/R7 evidence 描述为后续阶段正式生产 artifact；
- 不从本次验证推导新的临床疗效、商业 IOL 排名或患者级选择结论。
