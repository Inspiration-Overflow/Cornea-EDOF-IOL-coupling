# TASK-009 主分析架构冻结：FFT MTF / MTFa-only MVP

日期：2026-08-19  
状态：Web scientific/analysis definition frozen；local implementation and OpticStudio validation pending

## 1. 决定

从 TASK-009 起，MVP 主分析彻底移除以下路径：

- Huygens PSF；
- Huygens MTF；
- PSF → 自行 FFT → complex OTF；
- complex OTF；
- VSOTF / VSMTF；
- 任何以 Huygens 或 complex OTF 为 Run72 前置条件的测试。

这些路径不保留为 fallback、optional production path 或隐藏备用实现。历史 commit / evidence 可以保留 provenance，但 active source、active URD/MDD/TDD/RMD 与后续 TASK-009/Run72 不得重新依赖它们。

OpticStudio 官方 FFT MTF 是基于 pupil data FFT 的 diffraction MTF 计算，并允许选择 sampling、wavelength、field、maximum frequency 等设置。本项目当前 MVP 为 field=0、共轴、无 tilt/decentration 的旋转对称系统，因此直接以 OpticStudio FFT MTF 作为主 diffraction image-quality oracle。

## 2. 新主生产路径

唯一主生产链：

```text
OpticStudio FFT MTF
→ sagittal/tangential MTF acquisition
→ MTFavg(f) = [MTFsag(f)+MTFtan(f)]/2
→ cycles/mm → cycles/degree
→ 0..60 cpd common grid
→ MTFa + fixed-frequency MTF
→ through-focus distance peak / DOF50 / TF-MTFa mean
→ MONO vs EDOF paired deltas
```

不再从 PSF 反算 MTF。

## 3. Analysis settings version

新增 active settings：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
```

冻结内容：

- wavelength = 555 nm；
- pupils = EPD 3 mm / 5 mm；
- field = 0°；
- through-focus retina-anchored vergence grid = +0.50 → -3.00 D，step=-0.25 D，共 15 planes；
- nominal FFT MTF pupil sampling candidate = 128×128；
- TASK-009 convergence comparison = 64×64 / 128×128 / 256×256；
- output comparison frequency domain = 0..60 cycles/degree；
- common post-processing frequency grid = 1 cpd；
- fixed reported frequencies = 10/20/30/40/50/60 cpd；
- no polarization for MVP；
- sagittal/tangential modulation response is acquired; no real/imaginary/phase OTF output is required.

128×128 remains a production candidate until TASK-009 real OpticStudio convergence passes. If it fails, the settings ID must version again before Run72.

## 4. Frequency conversion

OpticStudio FFT MTF frequency output is treated in cycles/mm. For each physical configuration, convert using the actual image angular scale:

\[
mm/degree = EFL_{mm}\tan(1^\circ)
\]

\[
f_{cpd}=f_{cyc/mm}(mm/degree)
\]

Backend must acquire enough FFT-MTF frequency range to cover at least 60 cpd after conversion. It must not silently extrapolate beyond the OpticStudio output domain.

The common 0..60 cpd, 1-cpd grid is obtained by deterministic interpolation of the averaged sagittal/tangential modulation curve. Interpolation is allowed only inside acquired frequency support.

## 5. MTFa

定义：

\[
MTF_{avg}(f)=\frac{MTF_{sag}(f)+MTF_{tan}(f)}{2}
\]

\[
\boxed{MTFa(F)=\frac{1}{60}\int_0^{60}MTF_{avg}(f,F)\,df}
\]

采用 1-cpd common grid 的 trapezoidal integration。

MTFa 是 TASK-009 / Run72 的主标量成像质量指标。

## 6. 距离峰

在 retina-anchored vergence：

\[
F\in[-0.50,+0.50]D
\]

内，以 MTFa 最大值定义 distance peak。

并列规则维持既有项目规则：

1. 最小 |F|；
2. 再并列选择较大的 signed F。

若峰落在 ±0.50 D 搜索边界，记录 `peak_search_censored=true`。

## 7. DOF50

废除旧的 `DOF_abs = VSOTF >= 0.10`。

主实验不引入新的 absolute MTFa threshold。

定义 distance-anchored DOF50：

\[
T_{50}=0.5\times MTFa_{distance\ peak}
\]

从 distance peak 出发，取满足

\[
MTFa(F)\ge T_{50}
\]

且包含 distance peak 的连续区间；阈值 crossing 使用相邻 0.25-D sample 线性插值。

保存：

- `dof50_far_d`；
- `dof50_near_d`；
- `dof50_width_d`；
- far/near censor flags。

该定义确保焦深始终锚定远用峰，而不是由一个可能更高的近用峰重新定义。

## 8. Through-focus MTFa mean

为补充 DOF50，记录全冻结扫描范围内的平均贯焦质量：

\[
\boxed{
TF\_MTFa\_mean=
\frac{1}{3.5D}\int_{-3.00}^{+0.50}MTFa(F)\,dF
}
\]

采用 retina-anchored grid 的 trapezoidal integration。

这不是新的 gate threshold，只是连续 summary metric。

## 9. 每个配置正式输出

至少保存：

- 15-plane retina-anchored defocus；
- shape-recentered defocus；
- MTFa per plane；
- MTF10/20/30/40/50/60 per plane；
- distance peak defocus；
- distance peak MTFa；
- MTFa at 0 D；
- DOF50 far/near/width/censor flags；
- TF_MTFa_mean；
- C4^0；
- C6^0；
- HOA RMS；
- cornea/STOP/IOL footprints；
- residual-induced `DeltaF_residual` through matched EDOF−MONO distance-peak difference；
- model/hash/retina/IOL/ELP invariants。

PSF image is not a mandatory MVP artifact.

## 10. Matched-pair primary deltas

EDOF − MONO 至少包括：

- distance_peak_retina_d；
- distance_peak_mtfa；
- mtfa_at_zero_d；
- dof50_width_d；
- tf_mtfa_mean；
- C4^0；
- C6^0；
- HOA RMS。

其中：

```text
DeltaF_residual = distance_peak_retina_d(EDOF) - distance_peak_retina_d(MONO)
```

始终使用 retina-anchored frame。

## 11. TASK-009 sampling convergence

TASK-009 不再验证 PSF/complex-OTF pipeline。

对三个代表性 EDOF physical configurations 比较 FFT MTF sampling 64/128/256。

128→256 必须同时满足现有项目 convergence policy：

- distance-peak MTFa relative change <= 2%；
- TF_MTFa_mean relative change <= 2%；
- distance peak shift <= 0.25 D；
- DOF50 width change <= 0.25 D。

不使用已删除的 PSF outer-energy、VSOTF convergence 条件。

TASK-009 repeatability gate：

- same sampling rerun distance-peak grid sample identical；
- distance-peak MTFa relative change <= 0.1%；
- TF_MTFa_mean relative change <= 0.1%；
- C4/C6 repeatability <= 0.001 µm。

## 12. TASK-009 representative set

为了覆盖两个 base、三个 cornea、三个 platform 和两种 pupil，本轮冻结三个代表 pair keys：

1. `LB_AL2395 × A0 × WFS × EPD3`；
2. `ATC_M3_AL24477 × B0 × RAD × EPD5`；
3. `ATC_M3_AL24477 × C0 × HOA × EPD5`。

sampling convergence 只需跑三者的 EDOF config；production-setting integration 则跑每个 pair 的 MONO+EDOF，共 6 configs，用于确认 matched-pair output 与 `DeltaF_residual`。

## 13. TASK-009 独立数值交叉检查

不使用 Huygens MTF。

对上述三个代表配置，使用 OpticStudio 的另一条 FFT-family oracle 做少量核对：

- 主生产 acquisition：FFT MTF Analysis；
- cross-check：MFE `MTFA`，Grid=1（使用 MTF-analysis grid algorithm），在有限固定频率点比较 sagittal/tangential average / MTFa consistency。

该 cross-check 仅发现 API/data extraction/unit conversion 错误，不替代主 FFT MTF Analysis，也不成为第二条生产路径。

如果实际 ZOS-API 对 `Grid=1` 的 MFE MTFA 行为与官方说明/实机 header 不一致，允许 TASK-009 改用同一 FFT MTF Analysis 的独立 text-data export/readback 检查；不得重新引入 Huygens。

## 14. 对既有 TASK-007/008 的影响

本修订只改变尚未执行的主分析 metric/acquisition 层：

- 不改变 A0/B0.20/C0；
- 不改变 18 physical carrier locks；
- 不改变 3 residual locks；
- 不改变 72-config manifest identity；
- 不改变 TASK-007/008 hashes；
- 不需要重跑 OpticStudio carrier/residual calibration；
- Run72 尚未开始，因此没有正式主实验结果需要重跑。

TASK-008 manifest 可以继续使用；TASK-009/analysis run environment 必须引用新的 `NOMINAL_MAIN_FFT_MTF_555_v2` settings ID。

## 15. Active-spec prohibition

完成迁移后，以下 active files 不得再把 Huygens / complex OTF / VSOTF 定义为主分析组成部分：

- `docs/URD.md`
- `docs/ADD.md`
- `docs/MDD.md`
- `docs/TDD.md`
- `docs/RMD.md`
- `docs/RMD_EXECUTION_STATUS.md`
- `src/whole_eye_mvp/domain.py`
- `src/whole_eye_mvp/metrics.py`
- `src/whole_eye_mvp/analysis.py`
- TASK-009/Run72 source/tests。

历史 changelog/evidence 中的旧术语只作为 provenance，不具有 active authority。
