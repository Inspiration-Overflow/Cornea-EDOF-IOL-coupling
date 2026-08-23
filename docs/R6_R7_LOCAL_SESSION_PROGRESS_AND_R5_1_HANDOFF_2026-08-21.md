# R6/R7 本地会话进度与 R5.1 交接 — 2026-08-21

> 状态：本地自主会话（Web 协作暂停中）。本文件为进度快照与恢复工作的交接记录。
> 起点HEAD：`73ed3da75f69b8365420c202c2942cfe338fb766`（Web reviewed）
> 当前HEAD：`21681949b71268959452a9efe21b194f55431ea7`

## 1. 本地提交清单（7 个，均在 reviewed HEAD 之上）

| commit | 内容 |
|---|---|
| `1ab2d58` | scaffold 校验接受冻结 R2/R3 旧命名 `CORNEA_POST_REF` |
| `d8d0f85` | 接受 N0 冻结零厚度角膜参考槽（TASK-005A 设计），零槽用裸轴向地标 |
| `13c5002` | REF_MONO 半径 bracket 几何扩展（平角膜参考眼所需半径超出原 bracket） |
| `178f833` | R6 defocus gate 改为记录而非中止（对齐"写 evidence + exit 2"合同） |
| `6a535a4` | validation 循环 per-carrier 失败隔离（任何 carrier 失败不再丢整批 evidence） |
| `d1b71c9` | **N0 source 改为冻结 Liou native 角膜**（`MAIN_CORNEA_LIOU_555_v1`，新模块 `revision_r6_native.py`） |
| `2168194` | **R5.1 HOA conic 功率缩放**（保 r⁴ sag 项不变，见 §4） |

离线 gate：275→297 passed（新增 32 个回归测试），ruff / compileall / `uv lock --check` 全绿。

## 2. 关键科学结论（R6/R7 24-carrier，canonical evidence）

Evidence：`project_mvp_2026_v2_zmx/diagnostics/model_revision/r6_r7/MODEL_REVISION_R6_R7_EVIDENCE.json`
（code_commit `2168194`，SHA256 `7315d3f0e9a631d0439281ef8c2023e567ff51aeb06e448b0df17e0e005553cb`，308 artifacts；diagnostics 目录不入 git，本地保留）

功率范围（N0 修复后）：WFS 19.20–25.43 D，RAD 19.37–25.55 D，HOA 18.89–25.14 D。

local_checks（9 项中 8 项通过，唯一剩余失败加粗）：

```
all_24_carriers_present                          = true
standard_eye_sa_all_passed                       = true
rad_real_powp_identity_regression_all_passed     = true   (8/8，RMS 0.586–0.597 D / max 1.511–1.525 D，
                                                            与 R4.2 +20D 参考 0.586/1.512 逐位级一致)
global_defocus_all_passed                        = true   (R5.1 后全过)
actual_eye_3_5mm_ray_health_all_passed           = true
binary4_geometry_all_passed                      = true   (R5.1 后无 radicand 崩溃)
selected_low_median_high_full_standard_audit...  = true
wfs_hoa_serialized_mechanism_all_passed          = false  ← 唯一剩余失败
local_r6_r7_passed                               = false
```

WFS 8/8 机制全绿；RAD 8/8 POWP 全绿（R5 移植对 WFS/RAD 全功率带成立，16/16）。

## 3. 剩余问题：HOA 机制 slack（6/8 超 2.5% RMS）

| carrier | 功率 D | RMS% (≤2.5) | max% (≤6.25) | defocus D |
|---|---|---|---|---|
| ATC C0 | 20.71 | **1.79 ✓** | 3.24 ✓ | −0.013 |
| LB N0 | 20.87 | **2.02 ✓** | 3.31 ✓ | −0.016 |
| ATC N0 | 18.89 | 2.73 ✗ | 5.53 ✓ | +0.022 |
| LB C0 | 22.69 | 4.79 ✗ | 6.32 ✗(边缘) | −0.042 |
| ATC B0 | 22.87 | 5.04 ✗ | 6.67 ✗ | −0.044 |
| ATC A0 | 23.17 | 5.44 ✗ | 7.23 ✗ | −0.049 |
| LB B0 | 24.85 | 7.51 ✗ | 10.16 ✗ | −0.066 |
| LB A0 | 25.14 | 7.84 ✗ | 10.63 ✗ | −0.069 |

（对比 R5.1 之前：RMS 5.6–41.4%、max 11.0–58.0%、LB A0/B0 构建崩溃。）

## 4. R5.1 设计记录（已实现于 `revision_r5_lock.py`，freeze id `R5_1_FREEZE_ID`）

机制读数目标为**功率无关固定 OPD 曲线**；端口处方中唯一功率耦合项是 zone conic 的 r⁴ sag 系数
`(1+Q_z)/(8·R_z³) − 1/(8·R_base³)`（dc 的 r²/2 项与 native a4/a6 的 r⁴/r⁶ 项均功率解耦）。
R5.1 规则：HOA 各 active zone 的 dq(P) 反解为使该四阶系数等于 +20 D 冻结值；dc/a4/a6 不变；
WFS/RAD 路径逐位不变。已知余项：精确 conic sag 的 r⁶ 系数 ∝ R⁻⁵ 且 Q² 加权，随功率增长——
这是剩余 2.7–7.8% 误差的主要来源。

已知 cosmetic 缺口：evidence 的 `r5_freeze_id` 字段仍记 `R5-2026-08-21`（runner 用旧常量），数值与行为不受影响。

## 5. 恢复工作的三个选项（未决策）

1. **R5.2：把不变量扩展到 r⁶ 项**（双条件：zone 外缘处精确 sag 差匹配 + 四阶匹配；或引入每 zone 第二自由度）。预期可压低高功率端误差；风险：低功率段可能过约束。
2. **接受 2.5%→ ~8% 的 HOA slack 修订**（记录为 R5.1 移植精度），24-carrier 判 PASS。
3. **HOA power-specific refit**（解除 power-independent 约束）——工程量最大。

建议先做 1 的解析预检（离线推算 r⁶ 修正后 8 carrier 的预期 RMS）再定。

## 6. 复现命令

```bash
uv sync --frozen && uv run pytest tests/unit          # 297 passed
uv run python scripts/run_model_revision_r6_r7.py \
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" \
  --overwrite --install-dir "C:/Program Files/Ansys Zemax OpticStudio 2026 R1.00"
```

R8 / 96-config production 未解锁；所有冻结科学量的变更仅限本文档记录的 R5.1（用户 2026-08-21 授权选项 b）。
