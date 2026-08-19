# TASK-005D Phase A.1 — A0 Binary4 离散收敛审核

日期：2026-08-19

## 结论

A0 nominal `transition slices = 8` 对当前 MVP 已达到足够的数值稳定性，保留 Phase A 已确定的 A0 设计，不再增加 N32、不重新优化 conic，也不修改科学处方。

本检查固定 Phase A 已求得的：

```text
inner conic = -0.1125
```

只改变 Binary4 平滑过渡离散：

```text
N = 4 / 8 / 16
```

因此差异反映离散加密本身，而不是重新调参后的拟合差异。

## 实机差异

```text
ΔC40 N4→N8  = -0.006945142143590932 µm
ΔC40 N8→N16 = -0.00013411031566068488 µm

Z37 N4→N8   = -0.00531121997280791 waves
Z37 N8→N16  = +0.001907062548949831 waves
```

从 N8 到 N16，`ΔC40` 变化已缩小到约 `1.34e-4 µm`，Z37 变化约 `1.91e-3 waves`。对本机制导向 MVP，这已经足以说明 N8 不再受粗离散主导。

## 决定

- A0 nominal 继续使用 8 个 transition slices；
- `T=-3 D / EOZ≈5 mm / ΔC40≈+0.13 µm` 定义不变；
- Phase A 得到的 `inner conic=-0.1125` 保留；
- 不新增硬阈值；
- 不做 N32；
- 可以进入 Phase B 的真实 `REF_MONO + B0` Huygens MTF 扫描。

本检查仍为 diagnostic evidence，不创建正式角膜 lock。
