# TASK-014 实现审核：顶点距换算与术后角膜处方层

日期：2026-08-20  
状态：**Phase A/B 完成并通过离线质量门；OpticStudio corrected-cornea acquisition 尚未执行**

## 1. 审核结论

本次修订已经完成“先文档、后代码”的第一阶段目标，并且没有改写 frozen TASK-011/TASK-012。

核心变化为：

```text
legacy:
  direct corneal-plane treatment = -3.000000 D
  vertex conversion = none

TASK-014:
  spectacle sphere = -3.000000 D
  vertex distance = 12.000 mm
  corneal-plane distance treatment = -2.895752895753 D
```

新处方层使用独立角膜身份：

```text
A0V12
B0V12
C0V12
```

旧 A0/B0/C0 不改名、不重算、不覆盖。

---

## 2. Git 与回退状态

修订前：

```text
pre-revision HEAD = fa401e2101023e6e409a5366f26f0da134b5476f
checkpoint branch = checkpoint/pre-vertex-correction-2026-08-20
pre-revision quality gate = run #132 / 32396661153 / success
```

完整旧状态：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

本次 prescription-layer 代码完成后的语义提交：

```text
167dbf562314c9949285b2ac9cf271e03a1b33d2
```

RMD/执行路线同步后：

```text
6492f3d229c8ff74cac42e96d6ff01427f2c9b1a
```

PR #26 继续保持 Draft / open / unmerged。

---

## 3. 新增文档

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
docs/TASK_013_VERTEX_CORRECTION_ADDENDUM_2026-08-20.md
docs/TASK_014_VERTEX_CORRECTED_CORNEA_EXTENSION_PLAN_2026-08-20.md
docs/TASK_014_IMPLEMENTATION_REVIEW_2026-08-20.md
```

`docs/RMD.md` 已升级至 v2.0，并同时记录：

- legacy −3.00 D direct-corneal-plane treatment；
- pre-revision checkpoint；
- TASK-013 N0 边界；
- TASK-014 vertex-corrected contract；
- 新旧96配置数据层的解释差异；
- STOP 条件。

---

## 4. 新增代码

### 4.1 Prescription / vertex conversion

```text
src/whole_eye_mvp/task014_vertex_corrected_cornea.py
```

实现：

```text
spectacle_to_cornea_plane_d()
cornea_to_spectacle_plane_d()
VertexCorrectedRxContract
TASK014_RX_CONTRACT
task014_cornea_prescriptions()
task014_prescription_snapshot()
```

固定 contract：

```text
TASK014_SPECTACLE_M3_VERTEX12_v1
```

### 4.2 Offline inspector

```text
scripts/inspect_task_014_vertex_corrected_prescriptions.py
```

该脚本完全不使用 OpticStudio，用于在任何本地 optical acquisition 前打印/保存处方快照。

### 4.3 Unit tests

```text
tests/unit/test_task014_vertex_corrected_cornea.py
```

检查：

1. −3.00 D @12 mm → −2.895752895753 D；
2. corneal→spectacle roundtrip 回到 −3.00 D；
3. legacy baseline 仍为 A/B/C `treatment_d=-3.00 D`；
4. 新 prescription IDs 为 A0V12/B0V12/C0V12；
5. A0 target +0.13 µm、B0 target +0.20 µm、C0 ADD +1.75 D 均保持；
6. 参考角膜与新 distance baseline 的厚角膜计算可复算。

---

## 5. 数值快照

由项目现有厚角膜公式得到：

```text
reference cornea equivalent power
= 42.251148573823 D

TASK014 corneal-plane distance treatment
= -2.895752895753 D

vertex-corrected distance corneal power
= 39.355395678070 D

vertex-corrected distance anterior radius
= 8.263362674865 mm

legacy-to-new treatment delta
= +0.104247104247 D
```

这些是处方/几何公式输出，不是新的 OpticStudio through-focus 结果。

---

## 6. Base semantics

新代码明确保持：

```text
Base phenotype
!= surgical prescription
```

即：

- `ATC_M3_AL24477.source_refraction_d=-3.0` 继续只是来源模型/表型信息；
- TASK-014 的 `preoperative_spectacle_sphere_d=-3.0` 是标准化手术处方输入；
- 两者不得相加；
- 两个 Base 均接受相同 standardized surgical prescription，使 Base 继续作为正交 sensitivity factor。

---

## 7. TASK-013 解释边界同步

TASK-013 N0 本身不需要近视 treatment，因此仍可按原计划执行24配置 acquisition。

但：

```text
TASK-013 N0 + frozen TASK-011 A0/B0/C0
```

只能称为 legacy engineering descriptive comparison。

最终 clinically normalized 4-cornea dataset 必须是：

```text
TASK-013 N0                 24 configs
TASK-014 A0V12/B0V12/C0V12 72 configs
----------------------------------------
                             96 configs
```

---

## 8. 离线质量门

代码/测试语义提交：

```text
167dbf562314c9949285b2ac9cf271e03a1b33d2
```

对应 Offline quality gate：

```text
run #138
run_id = 32401703882
conclusion = success
```

RMD 同步后的 head：

```text
6492f3d229c8ff74cac42e96d6ff01427f2c9b1a
```

对应 Offline quality gate：

```text
run #139
run_id = 32401836324
conclusion = success
```

最终检查：

```text
pytest = 224 passed
ruff = PASS
compileall = PASS
uv lock --check = PASS
```

---

## 9. 尚未完成的部分

本次没有伪造或提前产生新的 optical results。

仍待后续：

```text
TASK-013 local N0 acquisition
TASK-013 Web evidence review
TASK-014 corrected-cornea ZOS builders
TASK-014 18 corrected P/Q carriers
TASK-014 residual power-envelope/replay gate
TASK-014 36 pair references
TASK-014 72 production configs / 1080 TF rows
TASK-014 exact ZMX archive
TASK-014 Web evidence review
```

只有上述 TASK-014 optical layer 完成后，才能把 A0V12/B0V12/C0V12 写入最终 clinically normalized through-focus supplement。

---

## 10. 当前结论

```text
legacy TASK-011/012 = unchanged / reproducible
rollback checkpoint = established
TASK-013 N0 = still valid / optical run pending
TASK-014 vertex prescription contract = frozen
TASK-014 pure Python implementation = complete
TASK-014 offline QA = PASS
TASK-014 optical acquisition = NOT RUN
```
