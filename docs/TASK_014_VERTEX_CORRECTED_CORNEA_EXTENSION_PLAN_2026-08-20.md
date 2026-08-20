# TASK-014 顶点距规范化术后角膜扩展计划

日期：2026-08-20  
任务 ID：`TASK-014-VERTEX-CORRECTED-POSTOP-CORNEA`  
状态：**scientific contract frozen；implementation ready；OpticStudio acquisition pending**

## 1. 目的

Legacy TASK-011 的 A0/B0/C0 使用 direct corneal-plane `-3.00 D` engineering treatment。TASK-014 不改写这些 frozen 结果，而是新增一个显式顶点距换算的临床屈光平面扩展。

## 2. 冻结处方

```text
contract_id = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane treatment = -2.895752895753 D
```

换算：

\[
F_c=\frac{F_s}{1-dF_s}
\]

12 mm 是本 MVP 的冻结工程约定，不宣称所有患者均为12 mm。若未来研究10/14 mm，应新建 sensitivity identity，不修改本 contract。

## 3. Corrected cornea IDs

```text
A0V12 = corrected distance baseline + A0 mechanism
B0V12 = corrected distance baseline + frozen B0.20 mechanism
C0V12 = corrected distance baseline + central-near +1.75 D prescription ADD
```

冻结细节：

```text
A0V12: EOZ ≈ 5.0 mm, ΔC4^0(6 mm) ≈ +0.13 µm
B0V12: continuous aspheric EDOF, ΔC4^0 target = +0.20 µm
C0V12: near diameter 3.00 mm, ADD +1.75 D, OZ 6.50 mm, transition 0.75 mm, N=8
```

不得因为 IOL 结果重新选择 B0 target 或改变 ADD。

## 4. Base 与 surgical prescription 正交

```text
Base phenotype:
  LB_AL2395
  ATC_M3_AL24477

standardized surgical challenge:
  spectacle -3.00 D @ 12 mm
  corneal plane -2.895752895753 D
```

`ATC_M3_AL24477.source_refraction_d=-3.0` 只是来源表型信息，不与 TASK-014 treatment 相加。

## 5. Matrix

```text
2 Base × 3 corrected corneas × 3 Platform = 18 carriers
18 × MONO/EDOF × EPD3/EPD5 = 72 configs
36 matched pairs
1080 through-focus rows
```

与 accepted TASK-013 合并后才形成 clinically normalized 96-config layer：

```text
N0 / A0V12 / B0V12 / C0V12
× WFS / RAD / HOA
× MONO / EDOF
× EPD3 / EPD5
× LB / ATC
= 96 configs
```

Frozen TASK-011 72 configs 继续作为 legacy engineering factorial 独立保留。

## 6. Carrier route

每个 `Base × corrected cornea × Platform` 独立：

```text
actual eye Q=0 P/R solve
→ STD_IOL_EYE_2024 power-specific Q(P)
→ actual-eye P–Q recheck max2
→ final actual-eye replay
→ standard-eye EPD6 SA replay
→ canonical carrier ZMX + SHA
```

不得从 legacy carrier 复制 P/R/Q。

## 7. Residual coverage 与 validation

Historical power envelope 只表示 existing validation coverage：

```text
within_existing_coverage
extension_validation_required
```

越界不自动 STOP。

每个 carrier 第一次进入 EDOF materialization 前，必须通过 shared schema-v2 exact-carrier validator：

```text
standard eye EPD6:
  |piston| <= 0.010 µm
  |global defocus| <= 0.125 D

actual eye EPD5:
  MONO ray health PASS
  EDOF ray health PASS
```

Actual-eye SSAG Mode-0 piston/defocus 只作 diagnostic。禁止修改 residual bytes/hash/shape 或建立 RAD 专用阈值。

同一 exact carrier SHA + residual SHA 的 validation PASS 可缓存复用，避免两个 pupil 重复验证。

## 8. Production contract

完全继承 TASK-009：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
sampling = 128
555 nm
EPD3 / EPD5
field = 0°
defocus = +0.50 → -3.00 D
step = -0.25 D
15 planes
frequency scale = paired_residual_free_MONO_EFFL
```

MONO/EDOF pair 唯一设计差异仍为 frozen residual。

## 9. Canonical archive

实际唯一目录：

```text
project_mvp_2026_v2_zmx/models/task014_vertex_corrected/
```

结构：

```text
corneas/                  # 5
carriers/                 # 18
residual_validations/     # diagnostics/provenance
runs/<run_id>/p0/         # 6
runs/<run_id>/pair_references/  # 36
runs/<run_id>/configs/    # 72
runs/<run_id>/MODEL_INDEX.csv
```

Primary MODEL_INDEX：

```text
5 + 6 + 18 + 36 + 72 = 137 records
```

Validation ZMX 不并入137。

## 10. Acceptance

Local acquisition acceptance 要求：

```text
cornea-layer models = 5
Q0 starts = 6
physical carriers = 18
exact-carrier validation enforced before each first EDOF materialization
pair references = 36
configs = 72/72
failed = 0
TF rows = 1080
matched pairs = 36
MODEL_INDEX = 137
archive integrity = PASS
```

本地 `acceptance_passed=true` 只表示 acquisition/archive 完整，不是 final scientific lock。

任何 out-of-coverage carrier 完成 numerical validation 后仍需 Web mechanism review。

## 11. STOP

立即停止，如果：

- corrected cornea build/target solve fail；
- carrier P–Q recheck >2；
- standard-eye SA replay fail；
- residual SHA mismatch；
- standard-eye residual low-order hard gate fail；
- actual-eye MONO/EDOF ray-health fail；
- pair-MONO EFFL invalid；
- config EPD/SHA/archive mismatch；
- 需要改 frozen science 才能继续。

以下不是单独 STOP：

```text
carrier outside historical power coverage
actual-eye SSAG diagnostic piston/defocus outside numerical tolerance
```

## 12. 当前下一步

TASK-014 不需要等待 TASK-013 重跑；TASK-013 已完成 local acquisition。当前只需：

```text
current HEAD offline QA PASS
→ local TASK-014 acquisition
→ Web review
```

不再增加新的模型层、阈值、优化器或执行框架。