# TASK-014 框架镜屈光度顶点距换算后的术后角膜扩展计划

日期：2026-08-20  
状态：**科学定义冻结；先完成文档与纯代码处方层，OpticStudio acquisition 尚未执行**  
任务 ID：`TASK-014-VERTEX-CORRECTED-POSTOP-CORNEA`

## 1. 变更原因

既有 `MVP_2026_v2` 中 A0/B0/C0 的 `treatment_d=-3.00 D` 被代码直接解释为：

```text
术后角膜等效屈光力 = 参考角膜等效屈光力 - 3.00 D
```

该 frozen 设定没有显式的框架镜平面，也没有 vertex-distance conversion。

临床上若“术前近视 -3.00 D”指框架镜处方，则角膜屈光手术的远用矫正量应先换算到角膜平面，再在该远用矫正基础上叠加 A/B/C 的像差或老视调制。

因此 TASK-014 新建一个独立、可追溯的处方层，不静默修改既有 TASK-011/TASK-012。

---

## 2. 修订前状态与 Git 回退锚点

本次修订前的精确状态记录在：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

关键 Git 锚点：

```text
active branch at revision start = feat/task-011-run72
pre-revision HEAD = fa401e2101023e6e409a5366f26f0da134b5476f
checkpoint branch = checkpoint/pre-vertex-correction-2026-08-20
PR = #26, Draft / open / unmerged
PR base = feat/task-009-fft-mtf-main
```

修订前最新离线质量门：

```text
Offline quality gate run #132
run_id = 32396661153
conclusion = success
```

如果本次处方层设计后续被证实有问题，应以该 checkpoint 作为比较/恢复基线，而不是覆盖新的 evidence。

---

## 3. 旧 frozen 结果的正式语义

TASK-008/011/012 保持原样：

```text
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-011 configs = 72
TASK-011 pairs = 36
TASK-011 TF rows = 1080
TASK-012 structured evidence = unchanged
```

旧 A0/B0/C0 必须继续解释为：

> **direct corneal-plane −3.00 D engineering treatment**

其结果仍可用于原来的机制 factorial 和论文历史分析，但不得无条件写成“框架镜 −3.00 D 经顶点距换算后的术后角膜”。

---

## 4. 新处方契约

### 4.1 Contract identity

```text
contract_id = TASK014_SPECTACLE_M3_VERTEX12_v1
preoperative_spectacle_sphere_d = -3.00 D
vertex_distance_mm = 12.00 mm
cylinder = 0 D
axis = N/A
```

12 mm 是本扩展的**冻结工程建模约定**，不是声称所有患者均具有12 mm实际顶点距。若后续需要10/12/14 mm敏感性，应另建 sensitivity identity，不修改本 contract。

### 4.2 框架镜到角膜平面换算

采用：

\[
F_c=\frac{F_s}{1-dF_s}
\]

其中：

- \(F_s\)：框架镜平面球镜屈光度；
- \(d\)：框架镜后顶点至角膜平面距离，单位 m；
- \(F_c\)：角膜平面等效矫正量。

对本 contract：

```text
Fs = -3.000000 D
d  = 0.012000 m
Fc = -2.895752895753 D
```

因此相对于 legacy direct -3.00 D treatment，新治疗量少负：

```text
Delta = +0.104247104247 D
```

---

## 5. 参考角膜与远用矫正

公共参考角膜仍为：

```text
MAIN_CORNEA_LIOU_555_v1
Rant = 7.77 mm
Qant = -0.18
CT = 0.50 mm
Rpost = 6.40 mm
Qpost = -0.60
ncornea = 1.376
naqueous = 1.336
```

按现有厚角膜等效屈光力公式：

```text
reference equivalent corneal power ≈ 42.251148573823 D
```

新远用角膜基线：

```text
42.251148573823 - 2.895752895753
= 39.355395678070 D
```

对应在保持后表面、厚度和材料不变时的前表面基础半径约为：

```text
Rant,distance ≈ 8.263362674865 mm
```

这些数值由代码公式确定，正式 optical asset 仍需由 OpticStudio/ZOS-API 构建并 readback。

---

## 6. 新术后角膜身份

为避免与 frozen A0/B0/C0 混淆，新扩展不复用旧 ID：

```text
A0V12 = A0 mechanism under TASK014_SPECTACLE_M3_VERTEX12_v1
B0V12 = B0.20 mechanism under TASK014_SPECTACLE_M3_VERTEX12_v1
C0V12 = C0 mechanism under TASK014_SPECTACLE_M3_VERTEX12_v1
```

### A0V12

```text
distance treatment = -2.895752895753 D
EOZ ≈ 5.0 mm
Delta C4^0(6 mm) target ≈ +0.13 µm
```

### B0V12

```text
distance treatment = -2.895752895753 D
continuous aspheric EDOF
Delta C4^0(6 mm) target = +0.20 µm
```

B0 机制仍锁定在原 `B0.20` 的像差目标，不根据 IOL 结果重新选择。

### C0V12

```text
distance treatment = -2.895752895753 D
central near diameter = 3.00 mm
prescription ADD = +1.75 D
OZ = 6.50 mm
transition width = 0.75 mm
N = 8
```

C0V12 的 +1.75 D 是在已经完成远用近视矫正的 distance baseline 上叠加的处方级近用设计输入。

---

## 7. Base phenotype 与手术处方正交

本研究继续把 Base 作为解剖/光学敏感性因素，而不把 `BaseId` 直接等同于某一患者的完整术前处方历史。

```text
Base phenotype:
  LB_AL2395
  ATC_M3_AL24477

standardized surgical prescription challenge:
  spectacle sphere = -3.00 D
  vertex = 12 mm
  corneal-plane distance correction = -2.895752895753 D
```

因此 A0V12/B0V12/C0V12 在两个 Base 上使用同一标准化处方层，使 Base 差异继续作为正交 sensitivity factor。

特别说明：

- `ATC_M3_AL24477.source_refraction_d=-3.0` 是来源模型/表型信息；
- `TASK014 preoperative_spectacle_sphere_d=-3.0` 是标准化手术处方输入；
- 两者不能在代码中相加，也不能把其中一个隐式当作另一个；
- 不存在“先保留 -3 D 未矫正近视，再额外做 -2.896 D 角膜治疗”的双重离焦。

---

## 8. TASK-013 N0 与 TASK-014 的关系

TASK-013 仍只负责：

```text
N0 = native / untreated reference cornea
2 Base × 3 Platform × MONO/EDOF × EPD3/5
= 24 configs
```

N0 本身没有 myopic treatment，TASK-013 不需要 vertex conversion 才能建立未治疗角膜数据。

但是：

> **在临床屈光平面已经规范化的4角膜比较中，不应把 TASK-013 N0 与 frozen TASK-011 A0/B0/C0 直接拼接后称为“完整临床规范化96配置”。**

新的 clinically normalized 4-cornea dataset 应来自：

```text
TASK-013 N0: 24 configs
+
TASK-014 A0V12/B0V12/C0V12: 72 configs
=
96 configs
```

而 frozen TASK-011 72 configs 继续作为 legacy engineering baseline 独立保留。

---

## 9. TASK-014 预期研究矩阵

### Physical carriers

```text
2 Base × 3 corrected postoperative corneas × 3 Platform
= 18 new physical carriers
```

### Nominal configurations

```text
18 carriers × 2 optic states × 2 pupils
= 72 new configs
```

对应：

```text
36 matched MONO/EDOF pairs
1080 through-focus rows
```

与 TASK-013 合并后的 clinically normalized research layer：

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configs
```

---

## 10. IOL、分析与 residual 规则不变

TASK-014 必须继续使用：

```text
STD_IOL_EYE_2024
power-specific Q(P)
matched MONO / EDOF carrier identity
frozen WFS/RAD/HOA residual bytes/hash
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
sampling = 128
555 nm
EPD3 / EPD5
retina-anchored defocus +0.50 → -3.00 D
15 planes
```

因 corrected cornea 会产生新的 IOL carrier powers，仍须执行 residual power-envelope/replay gate；不得假定 legacy 18 carriers 的 residual calibration 自动覆盖新 power。

---

## 11. ZMX 输出契约

TASK-014 每个光学实体同样必须保留 `.zmx`。

固定目录建议：

```text
project_mvp_2026_v2_zmx/
└─ models/
   └─ task014_vertex_corrected_postop/
      ├─ corneas/
      │  ├─ CORNEA_A0V12.zmx
      │  ├─ CORNEA_B0V12.zmx
      │  └─ CORNEA_C0V12.zmx
      ├─ carriers/
      │  └─ CAR_<base>_<A0V12|B0V12|C0V12>_<platform>.zmx   # 18
      └─ runs/<run_id>/
         ├─ pair_references/<pair_key>.zmx                  # 36
         ├─ configs/<config_id>.zmx                         # 72
         └─ MODEL_INDEX.csv
```

每个 config `.zmx` 必须持久化其 EPD 并与 production analyzed model SHA 绑定。

---

## 12. 代码实现顺序

```text
Phase A — 文档与 rollback checkpoint
  COMPLETE

Phase B — 纯 Python prescription layer
  spectacle↔corneal-plane conversion
  → TASK014 contract
  → A0V12/B0V12/C0V12 prescriptions
  → unit tests
  → offline quality gate

Phase C — OpticStudio asset/runner implementation
  corrected cornea builders
  → 18 P/Q carriers
  → residual envelope/replay gate
  → 36 pair references
  → 72 configs
  → exact ZMX archive

Phase D — local acquisition + Web review
  72/36/1080 reconstruction
  → combine with accepted TASK-013 N0
  → clinically normalized 4×3 through-focus supplement
```

本轮修订至少完成 Phase A/B；Phase C/D 在后续本地光学执行前必须再次代码审核。

---

## 13. STOP 条件

立即停止，如果出现：

- 需要改写 frozen `BASELINE_CORNEA_SPECS` 才能实现新处方；
- 新代码改变旧 `distance_corrected_cornea_power_d()` 对 legacy A0/B0/C0 的输出；
- TASK-008/011/012 hash/evidence 发生变化；
- 把 `ATC.source_refraction_d` 与 TASK014 surgical prescription 数值相加；
- 把旧 A0/B0/C0 静默重命名为 A0V12/B0V12/C0V12；
- 不经过新的 carrier-power gate 就复用 frozen residual；
- 为使新结果靠近旧结果而调整 vertex distance、B0 target、ADD 或分析窗口。

## 14. 解释原则

本次修订的核心不是让数值变化更大或更小，而是让屈光平面定义闭合：

> **框架镜处方负责定义术前近视矫正需求；顶点距负责将其转换到角膜平面；A/B/C 只负责在已完成远用矫正的角膜基线上加入各自的像差/老视空间调制；Base phenotype 继续作为独立的解剖敏感性因素。**
