# R5.2 R6/R7 最终验证审查 — 2026-08-22

## 1. 审查范围与证据来源

本审查对应任务 `r6-r7-r5-2-final-review-20260822`，仓库为 `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`，dispatch commit 为 `8f287ba5e0ccafb01db17a60a8edabccc2cad4ff`。冻结的 R5.2 实现 commit 为 `a1870b10b326fe96be66919cad987fbcc58f0bc3`。

本次最终审查的数值依据为任务随附的：

`.delegate/r6-r7-r5-2-final-review-20260822/inputs/MODEL_REVISION_R6_R7_EVIDENCE.json`

任务合同记录的该 evidence JSON SHA-256 为：

`1ebf196d51d68e5d6f573a36c9fd398d705ebaf9d63b7ad49c70670c432ce06f`

其 phase 为 `R6/R7 carrier/mechanism validation`，`formal_artifact=false`、`pilot=false`。因此，本文件审查的是完成后的 R6/R7 载体与机制序列化验证证据，而不是新的正式生产 artifact，也不是 R8/96-config 主研究生产。

ChatGPT Web 在本任务中没有运行 OpticStudio、没有恢复或修改许可证、没有更改代码，也没有生成新的光学模型。此前本地审查中记录的 ZOS-API license blocker 已由本任务合同说明为本地环境随后恢复；本次 Web 审查仅评价 dispatch 中提供的完成版 evidence 与冻结源代码是否一致。

## 2. 源代码与 evidence 合同性

审查未发现 source/evidence 不一致。

### 2.1 R5.2 HOA A6 确定性规则

`src/whole_eye_mvp/revision_r5_2.py` 与 evidence 中的 `r5_2_hoa_a6_rule` 一致：

- 先应用冻结的 R5.1 HOA conic 归一化规则；
- +20.0 D 为参考功率；
- 参考 carrier radius 为 `12.357387811201875 mm`；
- 仅 HOA active zone 1 和 zone 2 的 native A6 随 carrier 求解；
- 求解顺序固定为 `zone 1 -> zone 2`；
- 完整边界 sag 包含精确 conic sag、native A4/A6 以及 Binary4 自动 C0 offset；
- zone 2 在 zone 1 已更新后求解，因此使用更新后的 zone-1 C0 状态；
- HOA 要求 `q_ant=0`；
- +20 D 路径直接返回冻结 R5.1 prescription，从而保持既有 +20 D prescription bit-identical；
- WFS/RAD 直接沿用 R5.1，因此保持既有 R5.1/R5 prescription；
- 求解是直接的 affine equation solve，不读取 mechanism gate 输出，不使用 optimizer 或 least-squares refit。

Evidence 对上述关键约束明确记录：`zone_order=[1,2]`、`r5_2_hoa_q_ant_required=0.0`、`gate_feedback_used=false`、`optimizer_used=false`、`automatic_power_specific_refit_allowed=false`。

### 2.2 R6 生产验证路径

`src/whole_eye_mvp/revision_r6_zos.py` 的 EDOF prescription 入口使用 `r5_2_zones_for_carrier`。MONO 与 EDOF 分别从 analytical carrier 构建并独立序列化为 Binary4；序列化后执行 zone readback/replay、C0 continuity、minimum conic radicand、mechanism readback、RAD real POWP（RAD 平台）、实际眼 3/5 mm ray health，以及被选中的 full standard audit。

`scripts/run_model_revision_r6_r7.py` 的 evidence metadata 与随附 JSON 一致，并明确：

- carrier space 为 `2 base × 4 cornea (N0/A0/B0/C0) × 3 platform`；
- expected carrier count 为 24；
- 不允许 EDOF 独立 P/Q callback；
- 不允许 automatic power-specific refit；
- MTF 不参与 mechanism fit；
- global defocus tolerance 为 `0.125 D`；
- 本阶段完成后仍需 Web review，不自动进入 R8。

`tests/unit/test_revision_r5_2_lock.py` 继续覆盖 +20 D identity、WFS/RAD identity、8 个已知 HOA carrier 的确定性 A6、两处完整边界 sag invariant、zone-2 使用更新 zone-1 C0 的敏感性检查、`q_ant=0`、非法输入、拓扑/非 A6 项保持以及既有 analytical mechanism gate。

## 3. 24-carrier 序列化验证结果

Evidence 中 `all_24_carriers_present=true`，与冻结的 24-carrier 空间一致。

### 3.1 平台功率范围

Evidence 对三个平台报告相同的 carrier power 范围：

| Platform | min_d | median_lower_d | max_d |
|---|---:|---:|---:|
| WFS | 15.01660005067162 | 20.012738203961458 | 25.030159135314852 |
| RAD | 15.01660005067162 | 20.012738203961458 | 25.030159135314852 |
| HOA | 15.01660005067162 | 20.012738203961458 | 25.030159135314852 |

这里保留 evidence 原字段名 `median_lower_d`，不将其改写为统计学意义上的一般“中位数”。

### 3.2 九项 local checks

Evidence 中九项预设 local checks 全部为 `true`：

| Local check | Result |
|---|---|
| `all_24_carriers_present` | true |
| `standard_eye_sa_all_passed` | true |
| `wfs_hoa_serialized_mechanism_all_passed` | true |
| `rad_real_powp_identity_regression_all_passed` | true |
| `global_defocus_all_passed` | true |
| `actual_eye_3_5mm_ray_health_all_passed` | true |
| `binary4_geometry_all_passed` | true |
| `selected_low_median_high_full_standard_audit_all_passed` | true |
| `local_r6_r7_passed` | true |

因此，按随附 evidence 的定义，完整 R6/R7 24-carrier carrier/mechanism validation 通过。

## 4. Analytical precheck 与 serialized local validation 的区分

必须区分两层证据：

1. **Analytical/source-level precheck**：R5.2 的 direct affine A6 rule、完整 boundary sag invariant、C0 顺序、已知 carrier A6 与 analytical mechanism proxy 已由源代码/单元测试和此前 Web source review 检查；这一层不等同于 OpticStudio 序列化验证。
2. **Serialized local validation**：本次 dispatch 提供的完成版 R6/R7 evidence 来自本地 OpticStudio 路径，并报告 24 个 carrier 均进入验证、九项 local checks 全部通过。

本次最终审查的作用是确认第二层证据与第一层冻结规则、生产路径和 metadata 相互一致，而不是把 analytical precheck 重新解释为 serialized result。

## 5. Evidence 与 artifact 完整性记录

任务合同记录：

- evidence JSON SHA-256：`1ebf196d51d68e5d6f573a36c9fd398d705ebaf9d63b7ad49c70670c432ce06f`；
- evidence 的 `artifact_sha256` 映射包含 **340** 个 artifact hashes；
- 这 340 个 hash 已由本地 orchestrator 在 dispatch 前独立匹配。

Web 审查能够读取 evidence JSON 中的 `artifact_sha256` 映射，但本任务没有访问或重新哈希本地二进制 artifacts，因此这里将 340 项及其独立匹配状态作为 dispatch contract 提供的完整性记录，而不声称 Web 再次完成了文件级 rehash。

同时，evidence 自身标记 `formal_artifact=false`。这不影响其作为本任务 R6/R7 最终审查输入的地位，但不应把它描述为 R8/96-config 的正式生产 artifact。

## 6. R8 锁定状态与审查结论

Evidence 的 progression 字段必须按字面解释：

- `manual_web_review_required=true`
- `automatic_progression_allowed=false`
- `next_gate="STOP for Web R6/R7 review; R8 remains locked"`

因此，本审查的 disposition 为：

**R6/R7 R5.2 24-carrier carrier/mechanism validation evidence review PASS；R8 仍锁定，不构成自动进入 R8 或 96-config production 的授权。**

没有发现需要修改 R5.2 源代码、R6/R7 runner、gate threshold、target curve、mechanism slack 或测试的缺陷。

## 7. 限制

- ChatGPT Web 本次没有运行 OpticStudio，也没有进行任何许可证操作；serialized validation 的执行事实来自 dispatch 提供的本地 evidence。
- 本次没有修改代码，也没有运行 R8/96-config production。
- Evidence 标记为 `formal_artifact=false`；本审查不把它提升为其他阶段的正式 artifact。
- Web 没有重新哈希本地二进制 artifact；340 项 artifact hash 的数量及 dispatch 前独立匹配状态来自任务合同。
- `docs/MANUSCRIPT_SCIENTIFIC_QC.md` 虽列于 authorized read paths，但在 dispatch commit `8f287ba5e0ccafb01db17a60a8edabccc2cad4ff` 返回 404，因此无法纳入本次稿件一致性复核；没有使用仓库外副本替代。
