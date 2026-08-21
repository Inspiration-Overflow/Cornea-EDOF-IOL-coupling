# TASK-013 顶点距修订补充说明

日期：2026-08-20  
状态：**生效；本文件优先于 TASK-013 原计划中关于“完整96配置”与直接合并解释的表述**

## 1. 原因

在 TASK-013 N0 代码完成但尚未执行 OpticStudio acquisition 后，重新审核发现：frozen TASK-011 的 A0/B0/C0 使用的是**角膜平面直接 −3.00 D engineering treatment**，并未从“框架镜 −3.00 D”经过顶点距换算。

因此，为避免把 N0 与 legacy A0/B0/C0 拼接后误称为“临床屈光平面规范化”的96配置数据集，现对 TASK-013 的使用边界作如下修订。

## 2. TASK-013 本身仍有效

TASK-013 继续只负责：

```text
N0 = native / untreated reference cornea
2 Base × 3 Platform × MONO/EDOF × EPD3/5
= 24 configs
```

N0 没有角膜近视治疗，因此 TASK-013 的 N0 构建不因 vertex correction 而失效。

TASK-013 的以下内容均继续有效：

- 6个 N0 physical carriers；
- 12个 matched pairs；
- 360个 through-focus rows；
- residual power-envelope gate；
- TASK-009 production MTF settings；
- canonical `.zmx` archive / `MODEL_INDEX.csv`；
- 不修改 TASK-008/011/012 frozen identities。

## 3. 对原 TASK-013 “96 configurations”表述的修正

原计划中：

```text
TASK-013 N0 24
+ frozen TASK-011 A0/B0/C0 72
= 96
```

仍可作为**legacy engineering descriptive comparison**，但不得标注为：

- clinically normalized pre-/post-refractive dataset；
- spectacle -3.00 D corrected postoperative dataset；
- 同一明确顶点距处方层下的 N0/A0/B0/C0 全矩阵。

新的临床屈光平面规范化96配置，应定义为：

```text
TASK-013 N0 = 24 configs
+
TASK-014 A0V12/B0V12/C0V12 = 72 configs
=
96 configs
```

TASK-014 规范见：

```text
docs/TASK_014_VERTEX_CORRECTED_CORNEA_EXTENSION_PLAN_2026-08-20.md
```

## 4. 全贯焦补充材料的使用规则

在 TASK-014 尚未完成之前：

- 可以画 frozen TASK-011 的72条术后曲线；
- 可以在 TASK-013 完成后画 N0 的24条曲线；
- 可以并列展示，但必须标注二者 treatment provenance 不同；
- 不应把二者合并成“统一临床规范化4×3主图”而不加说明。

待 TASK-014 完成并通过 Web review 后，优先用：

```text
N0 / A0V12 / B0V12 / C0V12
```

生成最终 clinically normalized 4×3 through-focus supplement。

## 5. Git / rollback

本修订前状态：

```text
pre-revision HEAD = fa401e2101023e6e409a5366f26f0da134b5476f
checkpoint branch = checkpoint/pre-vertex-correction-2026-08-20
```

完整旧设定记录：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

该历史状态不得删除，以便后续复核 vertex distance、屈光平面或研究解释时回退比较。
