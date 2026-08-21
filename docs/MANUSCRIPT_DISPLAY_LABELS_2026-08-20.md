# 投稿展示标签规范 — 读者术语与工程 ID 分离

> 状态：presentation contract。仅改变读者可见的标签，不改变任何科学变量、内部 ID、CSV、config identity、模型文件名或 provenance。当前中文稿以中文学术名称为主；英文名称仅用于英文稿、英文图或首次术语对应。

## 1. 原则

工程 ID 用于机器、证据链和可重复性；论文标签用于读者理解。两者不得混为一层。Evidence / CSV / config / manifest 中继续保留冻结内部 ID；正文、图题、图例、坐标轴、正文表格和图注优先使用具有明确光学含义的名称；内部 ID 只在 Methods 或补充材料首次定义时括号注明一次；文件名可继续保留内部 ID，以维持稳定路径和机器可追踪性。

## 2. 基础眼

| Internal ID | 中文正文标签 | English label |
| --- | --- | --- |
| `LB_AL2395` | Liou–Brennan 模型眼（眼轴 23.95 mm） | Liou–Brennan model eye (AL 23.95 mm) |
| `ATC_M3_AL24477` | Atchison −3 D 近视模型眼（眼轴 24.48 mm） | Atchison myopic model eye (−3 D; AL 24.48 mm) |

正文不再单独使用 `LB`、`ATC` 作为读者可见标签。

## 3. 角膜光学表型

| Internal ID | 中文正文标签 | English label |
| --- | --- | --- |
| `N0` | 未治疗参照角膜 | Untreated reference cornea |
| `A0V12` | 近视术后准单焦角膜 | Post-myopic quasi-monofocal cornea |
| `B0V12` | 连续非球面角膜延焦原型 | Continuous-aspheric corneal EDoF phenotype |
| `C0V12` | 中央近用径向多焦角膜 | Central-near radial multifocal cornea |

`V12` 属于工程 provenance：三个术后角膜均由镜片平面 −3.00 D、12 mm 顶点距换算至角膜平面 −2.895752895753 D。该信息在 Methods 说明，不要求在每张图的角膜标签中重复。

## 4. 人工晶状体延焦机制

| Internal ID | 中文正文标签 | English label |
| --- | --- | --- |
| `WFS` | 波前塑形型延焦 | Wavefront-shaping EDoF |
| `RAD` | 径向屈光力调制型延焦 | Radial-power-modulation EDoF |
| `HOA` | 高阶像差调制型延焦 | Higher-order-aberration EDoF |

这些仍是 mechanism surrogates，不是商业人工晶状体名称，也不用于产品排名。

## 5. 瞳孔与光学状态

| Internal ID | 中文正文标签 | English label |
| --- | --- | --- |
| `EPD3` / `3.0` | 3 mm 瞳孔 | 3-mm pupil |
| `EPD5` / `5.0` | 5 mm 瞳孔 | 5-mm pupil |
| `MONO` | 匹配单焦对照 | Matched monofocal control |
| `EDOF` | EDoF 状态 | EDoF state |

读者可见图中不再以 `EPD3`、`EPD5`、`MONO` 作为唯一标签。

## 6. 指标标签

正文优先写出含义，再保留标准缩写：`ΔDOF50` 表述为 DOF50 改变量（EDoF − 匹配单焦对照）；`ΔMTFa@0D` 表述为 0 D 处 MTFa 改变量；`ΔTF MTFa mean` 表述为全贯焦窗口平均 MTFa 改变量；`ΔC4⁰ / ΔC6⁰` 表述为完整眼 C4⁰ / C6⁰ 改变量。定义一次后可继续使用 DOF50、MTFa、C4⁰、C6⁰ 等标准光学缩写。

## 7. 边界删失展示

`lower_bound` 必须翻译为“DOF50 为下界”或在数值前使用“≥”；`peak_search_censored=true` 必须翻译为“距离峰值受搜索窗边界限制”。不得仅显示内部枚举值 `lower_bound` 或 `peak_search_censored` 而不解释。

## 8. 适用范围

该规范适用于 48 张 raw through-focus supplementary figures、24 张 summary figures、5 张 manuscript main figures、Table 1、Supplementary Tables S1/S2 的展示列，以及 assembled manuscript 正文和图注。内部 frozen IDs、结果数值、曲线、censor policy、focus window、residual 和模型 identity 均保持不变。
