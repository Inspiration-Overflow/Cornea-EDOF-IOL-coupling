# TASK-005D Phase A 实机结果审核

日期：2026-08-19  
分支：`feat/task-005d-cornea-lock-assets`

## 结论

Phase A 的基础角膜构造可以接受，继续保留当前科学处方，不回调 A/B/C 的 nominal 定义。

- A0：`ΔC40=+0.13295 µm`，命中 `+0.13 µm` 目标。
- B0.10–B0.30：五个候选全部命中各自目标，且所需 `r^4` 系数和 achieved ΔC40 随候选目标单调增加。
- C0：N4/N8/N16 的 C40 已明显收敛；N8→N16 仅变化约 `-0.000259 µm`，nominal N8 对当前 MVP 足够。
- 所有输出仍为 diagnostics，`formal_artifact=false`，不创建正式角膜 lock。

## 关键实机读回

```text
reference C40 = +0.2573993720 µm
distance  C40 = +0.2121152862 µm

A0
  target ΔC40   = +0.130000 µm
  achieved ΔC40 = +0.132946 µm
  inner conic   = -0.1125
  Z37           = +0.120897 waves

B0.10  achieved=+0.102282 µm  r4=0.000069375
B0.15  achieved=+0.148644 µm  r4=0.000091250
B0.20  achieved=+0.200208 µm  r4=0.000115625
B0.25  achieved=+0.246397 µm  r4=0.000137500
B0.30  achieved=+0.299086 µm  r4=0.000162500

C0 N4  ΔC40=-0.554434 µm
C0 N8  ΔC40=-0.555631 µm
C0 N16 ΔC40=-0.555890 µm
N4→N8  =-0.001197 µm
N8→N16 =-0.000259 µm
```

## 进入 Phase B 前的唯一附加检查

A0 是后续 B0 排序的参考阈值，而当前 A0 的高阶径向项 `Z37≈0.121 waves` 明显高于连续 Even-Asphere B 候选。因此在跑 204 组 Huygens MTF 之前，只增加一次低成本的 A0 Binary4 离散检查：

```text
transition slices = 4 / 8 / 16
```

该检查固定 Phase A 已校准的 `inner_conic=-0.1125`，只观察 achieved ΔC40 和 Z37 随离散加密是否趋于稳定；不为每个 N 重新求 conic，也不新增 hard scientific threshold。

如果 N8→N16 已基本稳定，则继续使用 nominal N8 并进入 Phase B。若不稳定，再在 Web 端修订 A0 数值实现；本地不人工调参。

## 实机路径问题

Phase A 首次使用相对 `--project-dir` 时暴露了 OpticStudio 原生 `SaveAs` 与 Python cwd 对相对路径解释不一致的问题。绝对路径重跑后 Phase A 全部 PASS。

Web 端已将 005D 两个入口脚本统一改为 `project_dir.resolve()`，后续本地继续可传相对项目目录。该问题属于路径工程 bug，不改变本次成功实机光学结果。
