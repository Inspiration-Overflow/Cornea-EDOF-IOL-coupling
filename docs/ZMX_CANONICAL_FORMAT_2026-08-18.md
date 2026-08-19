# OpticStudio `.zmx` 规范文件格式迁移

> 状态：**工程实现契约**。本文件只改变 OpticStudio lens 文件的规范扩展名，不改变任何科学模型、科学 baseline、阈值、锁定参数或实验矩阵。

## 1. 决策

从本修订开始，项目**新生成的 OpticStudio lens 文件统一使用 `.zmx`**。

适用范围包括：

- `BASE_LB_PSEUDOPHAKIC.zmx`
- `BASE_ATC_M3_PSEUDOPHAKIC.zmx`
- `STD_IOL_EYE_2024.zmx`
- 后续 A0/B0/C0、carrier、matched pair 和 nominal configuration 的 OpticStudio lens 文件
- 临时或人工诊断脚本新生成的 lens 文件

依据是当前 Ansys OpticStudio 文件规范：`.ZOS` 文件格式已经完成弃用收尾；当前 GUI 与 ZOS-API 的保存/另存为工作流以 `.ZMX` 为 lens data 文件格式。

## 2. 不改变的内容

本修改**不是科学 baseline 修改**。以下全部保持不变：

- `MVP_2026_v2`
- 两个 005B 基座的科学几何定义
- `STD_IOL_EYE_2024` 的 Liou/Norrby 角膜定义
- EPD = 6 mm、λ ≈ 546 nm
- `C4^0 = +0.258 ± 0.005 µm`
- IOL footprint `5.15 ± 0.10 mm`
- WFS/RAD/HOA 基础 SA 目标
- 主实验 EPD3/EPD5
- TDD-999

文件扩展名变化不触发新的 `ScientificBaseline` ID。

## 3. 已锁定 `.zos` 的处理

现有 `project_mvp_2026_v2` 中已经正式锁定的 `.zos` 文件**不原地改名、不改写、不替换 lock hash**。

它们继续作为 TASK-005B / TASK-005C 的历史实机证据，包括此前已经验证的 SHA-256。

原因很简单：锁定资产的 path/hash 本身就是 provenance；为了文件扩展名去改写既有 lock 没有科学收益，反而会破坏可追溯性。

## 4. 后续活动项目目录

后续正式科学资产从一个新的项目目录继续：

```text
project_mvp_2026_v2_zmx
```

该目录仍使用：

```text
baseline_id = MVP_2026_v2
```

首次本地实机初始化时只需重新生成并验证：

1. 两个 TASK-005B 基座 `.zmx`
2. TASK-005C `STD_IOL_EYE_2024.zmx`

随后新的 A/B/C、carrier 和 Run72 工作都在该 `.zmx` 项目目录继续。

旧 `project_mvp_2026_v2` 不删除。

## 5. 代码规则

生产代码中：

- `BaseAssetPrescription.relative_path` 必须以 `.zmx` 结束；
- 005B 两个 canonical asset path 改为 `.zmx`；
- `STD_IOL_EYE_2024` canonical path 改为 `.zmx`；
- 005C fresh-process candidate 使用 `.zmx`；
- 手工诊断脚本若再次使用，也生成 `.zmx`；
- 不增加 `.zos/.zmx` 双格式自动迁移框架；
- 不增加解锁/替换既有 formal lock 的功能。

这是 MVP 所需的最小改动。

## 6. 测试规则

离线测试至少确认：

- 005B prescription path 使用 `.zmx`；
- standard-eye canonical path 使用 `.zmx`；
- `.zos` 不能再作为新 base prescription 的 canonical path。

本地 OpticStudio 只做不可替代的最小验证：

- fresh `project_mvp_2026_v2_zmx` 能生成、reload、validate 两个 005B `.zmx`；
- 能生成、reload、validate `STD_IOL_EYE_2024.zmx`；
- 005C 的 Z11/Z37/C40/footprint 等科学结果保持与已通过的 `.zos` production 结果一致到原有容差。

不要求新 `.zmx` 与旧 `.zos` SHA-256 相同；文件序列化格式变化后 hash 只用于各自项目内的 lock/provenance。

## 7. 旧文档中的 `.zos`

旧 STOP 记录、历史审计和既有实机证据中的 `.zos` 字样保留原样，因为它们描述的是当时真实生成的文件。

对于 URD/TDD/RMD 中把 `.zos` 当作**未来输出格式**的表述，本文件从本修订开始覆盖其“文件扩展名”这一点；其科学、功能和可追溯性要求不变。后续文档正常修订时再逐步把这些表述统一为 `.zmx`，无需为纯格式变更制造大规模版本级联。
