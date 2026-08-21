# 顶点距修订前状态与 Git 回退检查点

日期：2026-08-20  
用途：在引入“框架镜平面屈光度 → 角膜平面治疗量”转换之前，固定记录当前科学设定、代码状态和可回退 Git 锚点。

## 1. 修订前 Git 状态

```text
repository = Inspiration-Overflow/Cornea-EDOF-IOL-coupling
active branch = feat/task-011-run72
PR = #26
PR state = Draft / open / unmerged
PR base = feat/task-009-fft-mtf-main
pre-revision HEAD = fa401e2101023e6e409a5366f26f0da134b5476f
pre-revision checkpoint branch = checkpoint/pre-vertex-correction-2026-08-20
```

对应最近一次离线质量门：

```text
Offline quality gate run #132
run_id = 32396661153
conclusion = success
```

该 checkpoint 分支只用于回退/比较，不作为新的开发分支。

## 2. 修订前科学设定的真实含义

### 2.1 Base eye

```text
LB_AL2395
  source_refraction_d = None
  AL = 23.950 mm

ATC_M3_AL24477
  source_refraction_d = -3.00 D
  AL = 24.477 mm
```

`ATC_M3_AL24477.source_refraction_d = -3.00 D` 是 Atchison 近视来源/基础眼表型信息；当前 frozen 主矩阵没有在眼前放置一片 -3.00 D 框架镜。

### 2.2 Frozen A0/B0/C0 treatment

修订前 `MVP_2026_v2` 中三个术后角膜均写为：

```text
A0 treatment_d = -3.00 D
B0 treatment_d = -3.00 D
C0 treatment_d = -3.00 D
```

代码实际执行：

```text
postoperative distance corneal equivalent power
= reference corneal equivalent power + treatment_d
```

即直接把角膜等效屈光力降低 3.00 D。

**修订前没有 vertex-distance 参数，也没有把 spectacle-plane -3.00 D 转换到 corneal plane。**

因此，现有 TASK-011/TASK-012 的 A0/B0/C0 应严格解释为：

> `direct corneal-plane -3.00 D engineering treatment` 下的冻结机制研究结果。

不能在不加限定的情况下重新解释为“临床框架镜 -3.00 D 经顶点距换算后的术后角膜”。

### 2.3 Base 与 treatment 的关系

Frozen Run72 把 Base phenotype 与 corneal prototype 作为正交实验因素：

```text
LB / ATC
× A0 / B0 / C0
```

因此相同的 `treatment_d=-3.00 D` 同时施加于 LB 和 ATC 两个 Base。该设计属于工程机制 factorial，不等同于逐患者的真实术前屈光史重建。

## 3. 修订前冻结结果不得被覆盖

以下仍为只读历史事实：

```text
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-011 formal configs = 72
TASK-011 matched pairs = 36
TASK-011 through-focus rows = 1080
TASK-012 structured evidence = unchanged
```

顶点距修订不得：

- 修改旧 `BASELINE_CORNEA_SPECS` 后声称旧 TASK-011 自动获得了新含义；
- 覆盖 TASK-008/011/012 evidence；
- 重写旧 manifest/hash；
- 用新治疗量替换旧 `.zmx` 后仍沿用旧 config/result identity。

## 4. TASK-013 在修订前的状态

在 `fa401e2...`：

```text
TASK-013 documents = frozen
TASK-013 offline implementation/tests = complete
TASK-013 OpticStudio acquisition = NOT RUN
N0 numerical optical results = DO NOT EXIST YET
```

TASK-013 仅新增 `N0 = native / untreated reference cornea`，未改变 A0/B0/C0 的 -3.00 D direct-corneal-plane treatment。

因此当前正处于适合修订的窗口：可以在 N0 正式 acquisition 前补充新的屈光处方/顶点距契约，而不需要撤销任何已产生的 N0 数值结果。

## 5. 回退方式

如后续发现本次顶点距/处方层设计存在问题，首先保留当前开发分支证据，再比较：

```text
checkpoint/pre-vertex-correction-2026-08-20
```

其精确提交为：

```text
fa401e2101023e6e409a5366f26f0da134b5476f
```

需要本地完全回退时，可在确认无未保存工作后使用该 commit/branch 创建新的恢复分支；不建议直接覆盖已形成的新 evidence。

## 6. 本次修订目标

后续新扩展应显式分离：

```text
Base phenotype
× preoperative spectacle refraction prescription
× vertex distance
→ corneal-plane distance correction
→ A/B/C presbyopic / aberration modulation
```

旧 frozen Run72 保留为 legacy engineering baseline；新的临床屈光平面规范使用新的 task/identity/provenance，不静默替换旧结果。
