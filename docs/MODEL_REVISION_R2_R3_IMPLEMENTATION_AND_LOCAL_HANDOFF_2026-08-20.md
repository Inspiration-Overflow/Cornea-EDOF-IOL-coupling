# Model Revision R2/R3 — Web implementation and local OpticStudio handoff

> 日期：2026-08-20  
> 分支：`feat/model-revision-binary4-physical-pupil`  
> 状态：**WEB IMPLEMENTATION READY; LOCAL OPTICSTUDIO GATE REQUIRED**  
> 上游：`MODEL_REVISION_R0_CONTRACT_2026-08-20.md`、`MODEL_REVISION_R1_SOURCE_LOCK_2026-08-20.md`

## 1. 本阶段边界

R2/R3 的 Web 端实现只新增 post-human-audit revision path，不修改旧 production path，也不覆盖任何已经冻结的 TASK-005B、TASK-007、TASK-013、TASK-014、TASK-015 artifact/evidence。

因此新版验证失败时可以整条 revision path 回退，不会污染旧科学状态。

本阶段本地 OpticStudio 只做一次合并批处理：

1. 建两个 revision base；
2. 在两套 base 上分别建立一个 A0、Q=0 的 analytical carrier；
3. 每个 analytical carrier 转换为 WFS/RAD/HOA 三种平台各自的 degenerate Binary 4 MONO；
4. 在实际 STOP 直径 3 mm 和 5 mm 下比较 analytical 与 Binary 4 MONO；
5. 输出一个统一 JSON evidence；
6. 任一 gate 失败立即 STOP，不开始 R4。

本阶段不拟合 EDoF，不生成 24 carriers，不运行 96-config。

## 2. R2 已实现的模型定义

### 2.1 物理瞳孔

revision path 使用：

```text
System Aperture = Float By Stop Size
STOP surface = 3
PUPIL_3: STOP Semi-Diameter = 1.5 mm
PUPIL_5: STOP Semi-Diameter = 2.5 mm
```

3/5 mm 从此表示 STOP 平面的实际物理直径，不是 ENPD。

### 2.2 clear semi-diameter

```text
anterior cornea = 5.0 mm
posterior cornea = 5.0 mm
IOL anterior = 3.0 mm
IOL posterior = 3.0 mm
retina = 5.0 mm
```

### 2.3 retina

Liou–Brennan：

```text
Standard
R = -12.000 mm
Q = 0
```

Atchison Model 1 @ SR=-3.00 D：

```text
Biconic
Rx = -12.628 mm
Ry = -12.732 mm
Qx = +0.192
Qy = +0.199
```

retina vertex 仍由冻结 AL 决定，不作为追焦自由度。

实现会在保存后重新读取，并确认 final retina 仍保持 IMAGE identity；不得因 surface type 转换而丢失最终像面身份。

## 3. R3 已实现的 degenerate Binary 4 MONO

三平台 zone topology 固定为：

```text
WFS anterior: 0/.55/.65/.87/1.05/3.00 mm
RAD posterior: 0/.50/.90/1.10/1.40/2.50/3.00 mm
HOA anterior: 0/.90/1.10/3.00 mm
```

MONO 转换规则：

```text
Na = 3
Np = 0
每区 diffraction order = 0
每区 R = analytical carrier R
每区 Q = analytical carrier Q
p^2 = 0
p^4 = 0
p^6 = 0
```

因此 R3 的 Binary 4 只是结构性退化表示；在开始 EDoF 拟合前必须证明它与 analytical carrier 光学等效。

## 4. R3 equivalence gate

每个：

```text
2 bases × 3 platform structures × 2 physical pupils = 12 comparisons
```

均比较：

- residual surface sag：0–3.0 mm，0.05 mm step；
- EFFL；
- C4^0；
- C6^0；
- native FFT MTF：0–100 cyc/mm，128 sampling。

默认初始等效阈值：

```text
max |Delta sag| <= 1e-6 mm
|Delta EFFL| <= 1e-6 mm
|Delta C4^0| <= 1e-6 um
|Delta C6^0| <= 1e-6 um
max |Delta FFT MTF| <= 1e-6
```

这些阈值是 degenerate representation 的数值等效阈值，不是临床阈值。如果真实 OpticStudio 的 surface implementation 产生稳定、可解释的数值底噪而不能达到该带宽，不允许本地静默放宽；必须把 evidence 返回 Web 端后再审查阈值。

native FFT MTF 只放在本地 revision diagnostic script 中，没有重新进入 production `src` analysis path，以维持仓库现有主分析政策。

## 5. 本地单批次命令

在 Windows / 本地 zcode 或 Codex 环境执行：

```powershell
git checkout feat/model-revision-binary4-physical-pupil
git pull --ff-only
uv sync --frozen
uv run pytest tests/unit
uv run python scripts/run_model_revision_r2_r3.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --overwrite
```

如果 `WHOLE_EYE_ZOS_INSTALL_DIR` 未配置，则在最后一条命令增加：

```powershell
--install-dir "<OpticStudio install directory>"
```

不需要分阶段人工打开每个 ZMX；脚本负责保存、reload、readback 和 gate。

## 6. 预期输出

统一目录：

```text
project_mvp_2026_v2_zmx/diagnostics/model_revision/r2_r3/
```

至少包含：

```text
R2_BASE_LB_AL2395.zmx
R2_BASE_ATC_M3_AL24477.zmx
R2_ANALYTICAL_Q0_LB_AL2395.zmx
R2_ANALYTICAL_Q0_ATC_M3_AL24477.zmx
R3_BINARY4_MONO_LB_AL2395_WFS.zmx
R3_BINARY4_MONO_LB_AL2395_RAD.zmx
R3_BINARY4_MONO_LB_AL2395_HOA.zmx
R3_BINARY4_MONO_ATC_M3_AL24477_WFS.zmx
R3_BINARY4_MONO_ATC_M3_AL24477_RAD.zmx
R3_BINARY4_MONO_ATC_M3_AL24477_HOA.zmx
MODEL_REVISION_R2_R3_EVIDENCE.json
```

JSON 会记录运行时 git HEAD、输入 A0 SHA256、模型 SHA256、revision geometry readback、Binary 4 zone readback 和 12 个 equivalence comparisons。

## 7. 必须 STOP 的情况

以下任何一项出现都停止，不进入 R4：

1. 安装版本不暴露 `FloatByStopSize`；
2. Biconic retina 的 `X Radius` / `X Conic` 参数头与预期不一致；
3. 保存/reload 后 retina 不再是 IMAGE；
4. 保存/reload 后 retina 参数、STOP、semi-diameter 不匹配 source lock；
5. Binary 4 surface 转换改变 IOL refractive index；
6. Binary 4 保存/reload 后 `Nz/Na/Np`、zone boundary、R/Q、order 或零 residual 系数不匹配；
7. 任一 analytical-vs-Binary4 equivalence metric 超阈值；
8. native FFT MTF API/数据结构与 2026 R1 预期不一致；
9. 脚本异常退出或 evidence `passed=false`。

本地不得通过修改 zone、retina、aperture type、阈值或分析设置来“让它过”。

## 8. 回传 Web 端的最小内容

如果 PASS，只需回传：

```text
- git HEAD
- git status
- run command
- MODEL_REVISION_R2_R3_EVIDENCE.json 的路径
- evidence passed=true
```

如果 FAIL，再追加：

```text
- 完整 traceback / STOP message
- evidence JSON（若已生成）
- 发生失败时涉及的 ZMX 路径
```

不需要逐个 ZMX 截图或逐模型人工汇报。只有 evidence 暴露出 ZOS-API 语义不确定时，Web 端才会指定一个最小人工检查点。

## 9. 下一 gate

R2/R3 evidence 经 Web 端审核通过后，才设计并执行 R4：

```text
WFS / RAD / HOA 各 1 个代表性 mechanism-fit pilot
```

R4 仍会作为一个合并本地批次，不回到高频交互模式。
