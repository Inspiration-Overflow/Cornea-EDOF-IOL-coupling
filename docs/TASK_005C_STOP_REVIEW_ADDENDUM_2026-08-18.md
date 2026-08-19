# TASK-005C STOP 复核补充 — 连续介质与 best-focus 映射

> 本文补充并**部分修正** `TASK_005C_STOP_REVIEW_2026-08-18.md` 的初步结论。
>
> 新的独立代码审查发现，在决定是否把 Norrby `+0.258 µm` 降级为纯 provenance anchor 之前，必须先修复一个更直接的处方实现错误：当前 `IOL_ANT_REFERENCE` dummy plane 后没有继续维持 `n=1.336`，从而在 formal standard-eye scaffold 中引入了非预期的 `1.336 → AIR` 平面介质跳变。

## 1. 新发现

OpticStudio Sequential LDE 的 `Material` 列定义**当前 surface 到下一 surface 之间的介质**。Ansys 官方 Lens Data Editor 文档明确如此描述。

当前 005C 实现：

```text
CORNEA_ANT        Material = cornea 1.376
CORNEA_POST       Material = medium 1.336
IOL_ANT_REFERENCE Material = blank
IMAGE_REFERENCE
```

因此实际传播是：

```text
cornea → n=1.336 → IOL_ANT_REFERENCE → AIR → IMAGE
```

而不是角膜文献 `c[4,0]` 计算所需的：

```text
cornea → n=1.336 continuously
```

`IOL_ANT_REFERENCE` 在 005C 只是 carrier 插入位置的**无光焦度参考面**，在尚未插入 IOL 时不应制造一个额外折射界面。

官方 LDE 语义：

- `https://optics.ansys.com/hc/en-us/articles/42661252179987-How-to-design-a-singlet-lens-Part-1-Setup`

该文档将 Material 定义为“separating the current surface from the next”的 material type。

## 2. 对首次失败结果的重新解释

首次实机结果：

- saved IMAGE: `C4^0 = 0.276491 µm`
- 把 IMAGE 移到按连续 aqueous 计算的 paraxial focus: `C4^0 = 0.385937 µm`

后一结果不能用于否定 Liou/Norrby `0.258`，因为代码计算的 paraxial focus 假设 posterior cornea 后一直处于 `n=1.336`，而实际 Zemax scaffold 在 `IOL_ANT_REFERENCE` 后已经进入 AIR。也就是说：

> **计算焦点所假设的介质链与实际 `.zos` 的介质链不一致。**

因此 `0.385937 µm` 首先是一个实现不一致诊断，而不是“paraxial focus reference 本身不适用”的充分证据。

## 3. Norrby best-focus 的更精确映射

Norrby 原文说明 Q ↔ `c[4,0]` 使用 OSLO EDU real-ray tracing，并采用 OSLO EDU 的 **best focus criterion**。OSLO 用户指南说明其 `Autofocus - minimize RMS OPD` 会移动 image plane 以最小化 on-axis monochromatic RMS optical-path difference。

OpticStudio 提供直接对应的 **Quick Focus → Wavefront Error** criterion。Ansys Help 明确说明：

- Quick Focus 调整 image 前一 surface 的 thickness；
- `Wavefront Error` criterion 聚焦到 RMS wavefront error 最小的 image surface。

官方来源：

- `https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Quick_Focus.html`
- `https://optics.ansys.com/hc/en-us/articles/42661773562899-Sample-code-for-ZOS-API-users`
- `https://optics.ansys.com/hc/en-us/articles/42661747915539-ZOS-API-using-Python-NET`

因此下一轮不再使用“手工 paraxial focus”作为 Norrby oracle，而是优先使用：

```text
continuous n=1.336 after posterior cornea
EPD = 6 mm
λ ≈ 546 nm
field = 0
Quick Focus criterion = Wavefront Error
then Zernike Standard C4^0
```

## 4. 修订决策

在上述修复和实机复测完成前：

1. **保留** `+0.258±0.005 µm` 作为待验证的正式 005C scientific gate；
2. **不调** Liou radii/Q 来追 0.258；
3. **不再使用** current paraxial-focus mutation 作为正式 reference mapping；
4. `IOL_ANT_REFERENCE` 在空 scaffold 中必须继续 `n=1.336`，不得产生 dummy refractive interface；
5. C40 oracle 改为 `Quick Focus / Wavefront Error` 对应 Norrby/OSLO minimum-RMS-OPD best focus；
6. formal saved standard eye 仍保持固定 IMAGE reference，不把 Quick Focus 后的位置保存；best-focus mutation 仅用于 C40 validation；
7. 如果修正连续介质 + RMS-wavefront best focus 后仍不能达到 `0.258±0.005 µm`，再回到 Web 端决定是否将 0.258 改为 convention-specific literature anchor。

## 5. Zernike lifecycle

首次测试还观察到同进程：

```text
New prescription → Zernike analysis
```

可能触发 `FRU__delta_init` / `ZemaxEngine.dll` 原生错误；独立加载既有文件的 Zernike test 可以通过。

因此下一轮验证应尽量把 C40 oracle放在 **fresh Python/OpticStudio process 中只读加载已经保存的 temporary standard-eye file** 后执行。若 Web 端代码暂时无法完全自动化这一进程边界，Codex 可以做最小 API/runtime 适配，但不得改变 6 mm、546 nm、Liou prescription、Quick Focus Wavefront criterion 或 `0.258±0.005 µm` target。

## 6. 当前 STOP

- TASK-005B v2: PASS
- TASK-005C: STOP
- PR #22: Draft
- `STD_IOL_EYE_2024`: not locked
- baseline: `MVP_2026_v2` unchanged

本文的“先修连续介质 + RMS-wavefront best focus，再判断 0.258 gate”优先于前一 STOP review 中“立即降级 0.258 gate”的建议。