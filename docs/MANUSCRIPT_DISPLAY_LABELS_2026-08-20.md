# 投稿展示标签规范 — 读者术语与工程 ID 分离

> 状态：presentation contract。仅改变读者可见的标签，不改变任何科学变量、内部 ID、CSV、config identity、模型文件名或 provenance。

## 1. 原则

工程 ID 用于机器、证据链和可重复性；论文标签用于读者理解。两者不得混为一层。

因此：

- evidence / CSV / config / manifest 中继续保留冻结内部 ID；
- 图题、图例、坐标轴、正文表格、图注和正文叙述优先使用具有明确光学含义的名称；
- 内部 ID 只在 Methods 或补充材料首次定义时括号注明一次，后续不作为主要称谓；
- 文件名可继续保留内部 ID，以维持稳定路径和机器可追踪性。

## 2. 基础眼

| Internal ID | Reader-facing English label | 中文标签 |
| --- | --- | --- |
| `LB_AL2395` | Liou–Brennan model eye (AL 23.95 mm) | Liou–Brennan 模型眼（眼轴 23.95 mm） |
| `ATC_M3_AL24477` | Atchison myopic model eye (−3 D; AL 24.48 mm) | Atchison −3 D 近视模型眼（眼轴 24.48 mm） |

正文不再单独使用 `LB`、`ATC` 作为读者可见标签。

## 3. 角膜光学表型

| Internal ID | Reader-facing English label | 中文标签 |
| --- | --- | --- |
| `N0` | Untreated reference cornea | 未治疗参照角膜 |
| `A0V12` | Post-myopic quasi-monofocal cornea | 近视术后准单焦角膜 |
| `B0V12` | Continuous-aspheric corneal EDoF | 连续非球面角膜延焦 |
| `C0V12` | Central-near radial multifocal cornea | 中央近用径向多焦角膜 |

`V12` 属于工程 provenance：三个术后角膜均由镜片平面 −3.00 D、12 mm 顶点距换算至角膜平面 −2.895752895753 D。该信息在 Methods 说明，不要求在每张图的角膜标签中重复。

## 4. IOL 延焦机制

| Internal ID | Reader-facing English label | 中文标签 |
| --- | --- | --- |
| `WFS` | Wavefront-shaping EDoF | 波前塑形型延焦 |
| `RAD` | Radial-power-modulation EDoF | 径向屈光力调制型延焦 |
| `HOA` | Higher-order-aberration EDoF | 高阶像差调制型延焦 |

这些仍是 mechanism surrogates，不是商业 IOL 名称，也不用于产品排名。

## 5. 瞳孔与光学状态

| Internal ID | Reader-facing label |
| --- | --- |
| `EPD3` / `3.0` | 3-mm pupil / 3 mm 瞳孔 |
| `EPD5` / `5.0` | 5-mm pupil / 5 mm 瞳孔 |
| `MONO` | Matched monofocal control / 匹配单焦点对照 |
| `EDOF` | EDoF mechanism / 延焦机制 |

读者可见图中不再以 `EPD3`、`EPD5`、`MONO` 作为唯一标签。

## 6. 指标标签

优先写出含义，再保留标准缩写：

- `ΔDOF50` → `Change in DOF50 (EDoF − matched monofocal)`；
- `ΔMTFa@0D` → `Change in MTFa at 0 D (EDoF − matched monofocal)`；
- `ΔTF MTFa mean` → `Change in mean through-focus MTFa`；
- `ΔC4⁰ / ΔC6⁰` → `Change in whole-eye C4⁰ / C6⁰`。

正文中定义一次后可继续使用 DOF50、MTFa、C4⁰、C6⁰ 等标准光学缩写。

## 7. Censoring 展示

读者标签应直接表达含义：

- `lower_bound` → `DOF50 is a lower bound` / `DOF50 为下界`；
- `peak_search_censored=true` → `distance peak is search-window censored` / `距离峰值受搜索窗边界限制`。

不得仅显示内部枚举值 `lower_bound` 或 `peak_search_censored` 而不解释。

## 8. 适用范围

该规范适用于：

- 48 张 raw through-focus supplementary figures；
- 24 张 summary figures；
- 5 张 manuscript main figures；
- Table 1、Supplementary Tables S1/S2 的展示列；
- assembled manuscript 正文和图注。

内部 frozen IDs、结果数值、曲线、censor policy、focus window、residual 和模型 identity 均保持不变。
