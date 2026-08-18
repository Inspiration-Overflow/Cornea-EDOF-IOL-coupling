# TDD — 角膜屈光术后 × 非衍射 EDOF IOL Zemax 自动化研究软件

> **Check Plan / Test-Driven Document。** 目标不是增加测试数量，而是让少量关键 oracle 能发现“模型做错、指标算错、72 个结果漏跑”。来源：`URD-0001 v1.3`、`ADD-0001 v1.4`、`MDD-0001 v1.3`。

## Metadata

- document_id: TDD-0001
- version: 1.2
- status: ready-for-final-review
- source_docs: URD-0001 v1.3, ADD-0001 v1.4, MDD-0001 v1.3
- last_updated: 2026-08-17
- target_test_runner: pytest
- optical_integration_environment: Windows + OpticStudio 2026 R1 + valid ZOS-API license

## Test Decisions

| ID | Decision |
| --- | --- |
| DEC-001 | `DOF_abs` 在 MVP 中统一使用 `VSOTF ≥ 0.10` 作为**工程比较阈值**，不解释为临床视力阈值；改变该阈值必须产生新 settings ID 并重跑受影响批次。 |

## Frozen Analysis Settings

| Item | `CORNEA_LOCK_B0_555_v1` | `NOMINAL_MAIN_555_v1` |
| --- | --- | --- |
| wavelength | 555 nm | 555 nm |
| pupil | EPD3 用于选择；EPD5 只做合理性/数值检查 | EPD3、EPD5 都进入正式矩阵 |
| through-focus | `+0.50 → −3.50 D` | `+0.50 → −3.00 D` |
| step | 0.25 D；17 planes | 0.25 D；15 planes |
| distance peak | VSOTF 在 `[-0.50,+0.50] D` 内最大；并列时先选最小 `|D|`，再选较大 signed D | 同左 |
| DOF_rel | 含 distance peak 的连续区间，`VSOTF ≥ 0.50 × distance_peak` | 同左 |
| DOF_abs | 含 distance peak 的连续区间，`VSOTF ≥ 0.10` | 同左 |
| threshold crossing | 相邻采样点线性插值；不外推；记录 `far_censored/near_censored` | 同左 |

正式 B0 lock 和 Run72 开始后不得根据结果改变对应 settings；改变即新 ID、新批次。

### B0 Lock Metric / Recommendation

B0 不使用主实验的 `VSOTF≥0.10` 作为选择阈值。对 EPD3/EPD5：

\[
Q_{\rm lock,p}(F)=\frac1{50}\int_0^{50}MTF(f,F)\,df,\qquad f:\mathrm{cycles/mm}
\]

\[
T_{\rm abs,p}=0.5Q_{A0,p,peak}.
\]

候选必须先满足 EPD3 distance retention ≥80%、EPD5 ≥70%。用户只负责把明显稳定的“双峰 + 深谷”候选标记为 morphology reject 并写理由；剩余候选按 `DOF_lock_abs(EPD3) → DOF_lock_abs(EPD5) → EPD3 distance retention → smaller |ΔC4|` 排序。软件给出推荐，用户确认；override 必须写 reason。

## Canonical Optical Metric Pipeline

唯一主路径：

```text
Zemax Huygens PSF
→ centered-array deterministic FFT
→ complex OTF
→ radial MTF / through-focus MTF / MTFa / VSOTF
```

规则：

- Huygens PSF nominal：pupil `128×128`；image `256×256`；image delta `0.5 µm`。
- `defocus_retina_d` 只通过 Zemax analysis-layer 的物方/入射 vergence 改变实现；retina position、IOL power/conic、ELP、角膜/IOL实体面型在整条贯焦中保持不变。
- `defocus_shape_d = defocus_retina_d − distance_peak_retina_d`；只用于 DOF/AUC/flatness/曲线形态比较，不修改 `.zos`，`ΔF_residual` 始终使用 retina-anchored frame。
- 若 distance peak 搜索结果落在 `[-0.50,+0.50] D` 的任一边界，记录 `peak_search_censored=True`，不得声称已找到完整内部峰。
- FFT 前保持 Zemax 图像几何中心为零点，**不得把 PSF peak 重新居中**。对称 zero-pad 到每维 4× 后，固定使用 `OTF = fftshift(fft2(ifftshift(PSF_padded)))`，并除以中心复数 DC bin 归一化。
- `MTF=|OTF|`；径向平均使用 1 cpd annular bins，0–60 cpd；贯焦 CSV 固定保存 10/20/30/40/50/60 cpd。
- `MTFa = (1/60)∫_0^60 rMTF(f)df`，采用 1-cpd grid 的 trapezoidal integration；这是项目工程指标。
- `CSF_N(f)=2.6(0.0192+0.114f)exp(-(0.114f)^1.1)`，`f` 为 cycles/degree。
- `VSOTF = Re[∬ CSF_N·OTF dfxdfy] / ∬ CSF_N·OTF_DL dfxdfy`，二维积分仅取 `sqrt(fx²+fy²)≤60 cpd`。
- 同瞳孔 diffraction-limited reference 使用圆孔理论 OTF：`OTF_DL=(2/π)[acos(ν)-νsqrt(1-ν²)]`，`ν=f/fc`，`0≤ν≤1`；`fc=(EPD/λ)tan(1°)` cpd。
- Zemax Huygens MTF 不是第二条生产路径，只在少量 reference config 上交叉验证 PSF→FFT 实现。
- VSOTF 采用 **complex OTF 的实部**；不得用 `|OTF|` 代替，否则会退化为 VSMTF 类指标。

Metric provenance：VSOTF 的 complex-OTF/real-part 定义遵循 Cheng–Bradley–Thibos 的 visual Strehl 系列工作及 Iskander 对 VSOTF 计算性质的分析；OTF 由归一化 PSF Fourier transform 得到。60 cpd、MTFa 和 `DOF_abs=0.10` 是本项目预先固定的 MVP 比较规则。

## Tolerance Policy

| Type | MVP rule |
| --- | --- |
| scientific anchor | STD corneal `C4^0 ±0.005 µm`；carrier SA target `±0.01 µm`；A0 `ΔC4^0 ±0.02 µm`、EOZ `±0.20 mm` |
| construction | 明确几何输入通常 `±0.001 mm`；介质 index `±1e-6` |
| convergence | MTFa/VSOTF 相对变化 `≤2%`；distance peak shift `≤0.25 D`；strict PSF outer-10% energy `≤0.5%` |
| repeatability | MTFa/VSOTF 相对变化 `≤0.1%`；C4/C6 `≤0.001 µm`；distance-peak grid sample 相同 |
| arithmetic | synthetic pure-math oracle 默认 `atol≤1e-10` |

scientific-anchor tolerance 是 MVP 工程验收带，不代表临床容差；后续若改变，必须版本化 baseline/settings。

## Acceptance Tests

| ID | Source AC | Scenario | Oracle |
| --- | --- | --- | --- |
| TDD-TEST-001 | URD-AC-001 | ZOS-API connection | valid path/license → non-null `PrimarySystem`、Sequential Mode、显式 close；bad path/license → typed failure 且无 completed run |
| TDD-TEST-002 | URD-AC-002 | 双基座 | AL=`23.950/24.477±0.001 mm`；post-cornea→STOP=`3.150±0.001 mm`；→IOL ant=`4.500±0.001 mm`；aqueous/vitreous=`1.336±1e-6` |
| TDD-TEST-003 | URD-AC-003 | `STD_IOL_EYE_2024` | corneal `C4^0=+0.258±0.005 µm`；IOL footprint `5.15±0.10 mm`；n=`1.336±1e-6`；aperture=`3.000±0.001 mm`；λ=`546±1 nm`；`ZERO_HOA_PARAXIAL_REFERENCE` 与待测 carrier 保持同 paraxial power/geometry/material/position，且其 IOL-induced SA reference=`0±0.005 µm` |
| TDD-TEST-004 | URD-AC-004 | A0/B candidate/B0/REF lock | A0：`T=-3D`、EOZ=`5.0±0.2 mm`、`ΔC4^0=+0.13±0.02 µm`、central flattening、`numerical_convergence_status=PASS`；B：achieved `ΔC4^0={0.10,0.15,0.20,0.25,0.30}±0.01 µm`，全部来自 `LB_AL2395+REF_MONO+CORNEA_LOCK_B0_555_v1`；软件输出 A0-derived thresholds、80/70% distance gates、DOF_lock_abs 与 deterministic rank；REF residual=null/platform-independent/不进72；B0 lock 保存 morphology decisions、rank、scan hash、selection reason；若 override recommendation，reason 必须非空 |
| TDD-TEST-005 | URD-AC-005 | C0 construction | `D_near=3.000±0.001 mm`、`ADD=+1.750±0.001D`、`OZ=6.500±0.001 mm`、`wT=0.750±0.001 mm`；r≤1.5 mm near、r≥2.25 mm far；quintic transition 端点 value/1st/2nd derivative 连续；采样 sag finite；`numerical_convergence_status=PASS` |
| TDD-TEST-006 | URD-AC-006 | power-specific `Q(P)` | 每个 18 carrier 回放至 STD eye，以自身 `P_ijk,Q_ijk`，并相对同 power/geometry 的 `ZERO_HOA_PARAXIAL_REFERENCE` 重算 IOL-induced SA：WFS=`−0.20±0.01 µm`、RAD=`−0.27±0.01 µm`、HOA=`0.00±0.01 µm`；`q_source_power_d == P_ijk`；**不要求不同 power 的 Q 数值必须不同** |
| TDD-TEST-007 | URD-AC-007 | matched MONO/EDOF | pair 的 power/R_ant/R_post/Q/CT/material/IOL position/carrier_id exact equal；MONO residual=null；EDOF residual platform-match；residual calibration record 包含 low/median/high actual-power gate；`ΔF_residual` 非空且来自 retina-anchored frame |
| TDD-TEST-008 | URD-AC-008 | 18 carriers | count=18；unique(`base,cornea,platform`)=18；2×3×3 全覆盖 |
| TDD-TEST-009 | URD-AC-009 | 72 manifest | count=72；unique config IDs=72；λ=555；EPD∈{3,5}；field=0；cornea/IOL decentration=0；IOL tilt=0；micro-monovision defocus=0 |
| TDD-TEST-010 | URD-AC-010 | single pair analysis | 每 config 有 15-plane TF、10/20/30/40/50/60-cpd MTF、MTFa、VSOTF、3 PSF、C4/C6/HOA；每 TF row 同时有 `defocus_retina_d` 与 `defocus_shape_d`；贯焦前后实体模型 hash/retina/IOL/ELP 不变；paired scalar=`EDOF−MONO` 与直接减法 `atol≤1e-10` |
| TDD-TEST-011 | URD-AC-011 | result traceability | config ID 可追到 carrier ID、P、Q、base/cornea/platform/state/pupil；存在 `.zos`、through-focus plot、MTF plot、3 PSF images；cornea/STOP/IOL footprint 均存在，IOL footprint≤其 optical diameter，且无 unintended-vignetting flag |
| TDD-TEST-012 | URD-AC-012 | failure/rerun | parameterized 注入 1 个 carrier-stage failure 与 1 个 config export failure：failed target 不计 completed；其他完成结果不回滚；Rerun 只重跑 selected target，生成新 run_id |
| TDD-TEST-013 | URD-AC-013 | repeatability | 同 program/OpticStudio/baseline/settings/manifest/lock set：locks+manifest hashes exact；MTFa/VSOTF ≤0.1% relative；C4/C6 ≤0.001 µm；distance-peak grid sample 相同 |
| TDD-TEST-014 | URD-AC-014 | surrogate naming | user-visible model IDs/labels 只能是 WFS-like/RAD-like/HOA-like surrogate 或批准中文等价；商业名不得作为模型 ID |
| TDD-TEST-015 | URD-AC-015 | GUI smoke | GUI 可完成 Build→Validate→B0 Scan/Lock→Carriers→Run72→Rerun；install path/project path/progress/log/output-folder 可见；不要求 Pause/Cancel |
| TDD-TEST-016 | URD-AC-010,011 | final nominal completeness | 正式 main batch：`completed configs=72`、`matched pairs=36`、`through_focus rows=72×15=1080`、无 duplicate ID、无 silent missing config |

## Contract Tests

| ID | Interface | Oracle |
| --- | --- | --- |
| TDD-TEST-101 | MDD-API-001 | valid returns Sequential `PrimarySystem` and always closes；bad path/license raises typed error；license failure closes before raise |
| TDD-TEST-102 | MDD-API-002 | writable matching project opens；unwritable/baseline mismatch fails without changing metadata |
| TDD-TEST-103 | MDD-API-003 | new artifact indexes after successful write；same-hash lock retry=no-op；different-hash same ID=`LockedArtifactConflict` |
| TDD-TEST-104 | MDD-API-004 | residual absent 仍可完成 core Build 但 `carrier_ready=False`；core validation fail → no corresponding lock |
| TDD-TEST-105 | MDD-API-005 | read-only validate 前后 locked `.zos` hash exact；missing/tampered lock → failed finding |
| TDD-TEST-106 | MDD-API-006 | complete B0 scan 必有 A0+5 candidates、17 planes/EPD3 + valid EPD5；`T_abs,p=0.5×A0 peak`、80/70% gates、DOF_lock_abs 和 rank 可从 CSV 独立重算；任一 candidate 失败 → action failed、已成功 artifact 保留、不可 lock |
| TDD-TEST-107 | MDD-API-007 | complete scan + valid candidate + morphology decisions 可写唯一 B0 lock；确认推荐项允许标准 reason；override 必须显式 reason；unknown/incomplete/missing-reason/conflict → no write |
| TDD-TEST-108 | MDD-API-008 | valid input → each platform residual 先通过 low/median/high actual-power calibration record，再得到 exactly 18 locks；missing residual/gate fail/pair mismatch/SA revalidation failure → affected formal lock 不产生 |
| TDD-TEST-109 | MDD-API-009 | valid 18 locks → stable 18/72 manifests；17 locks/duplicate key → no formal manifest |
| TDD-TEST-110 | MDD-API-010 | defocus sweep 只改变 analysis vergence；实体 `.zos`/retina/IOL/ELP hashes 稳定；shape axis 可由 retina axis 和 distance peak 精确重算；mandatory artifacts before completed；invalid selection/export fail/rerun behavior 同 contract |
| TDD-TEST-111 | MDD-API-011 | required controls exist；GUI module does not import raw ZOSAPI；GUI init failure creates no success record |
| TDD-TEST-112 | MDD-API-012 | idle submit starts exactly one action；busy second request rejected；workflow exception→failed event+log；no completed event |

## Metric / Numerical Oracle Tests

| ID | Protects | Oracle |
| --- | --- | --- |
| TDD-TEST-201 | two settings grids | B0 vector exactly 17 points `+0.50…−3.50`；main exactly 15 points `+0.50…−3.00`；step `−0.25D`；serialization IDs distinct/stable |
| TDD-TEST-202 | PSF→complex OTF | 使用固定 `fftshift(fft2(ifftshift(...)))`：centered delta PSF → OTF≡1；one-pixel shifted delta keeps `|OTF|=1` 且出现解析可预测的线性 phase ramp，证明没有 peak-recenter/shift-convention 错误 |
| TDD-TEST-203 | VSOTF endpoints | `OTF=OTF_DL` → `VSOTF=1±1e-10`；zero OTF → `0±1e-10` |
| TDD-TEST-204 | phase-sensitive VSOTF golden | `docs/fixtures/COMPLEX_OTF_GOLDEN_3x3_v1.json` 的完整 3×3 complex matrix：VSOTF=`0.4411441499±1e-10`；VSMTF=`0.5325191642±1e-10`；若实现使用 `|OTF|` 代替 complex OTF 必失败 |
| TDD-TEST-205 | MTFa | synthetic radial MTF≡0.5 on 0–60 cpd → MTFa=`0.5±1e-10` |
| TDD-TEST-206 | distance-peak tie/censor | equal maxima at −0.25/+0.25 D → +0.25 D；若 0 D 同高 → 0 D；若唯一最大值位于 −0.50 或 +0.50 D 搜索边界，`peak_search_censored=True` |
| TDD-TEST-207 | DOF interpolation | synthetic linear threshold crossing → analytic crossing `±1e-10D`；分别验证 relative 50% 与 DEC-001 absolute 0.10 |
| TDD-TEST-208 | DOF edge/empty | threshold 到 scan edge 仍满足 → 不外推且相应 censored flag=true；若 distance peak<0.10，则 `DOF_abs` 为空/0 且 `below_absolute_threshold=True`，不是分析失败 |
| TDD-TEST-209 | Huygens sampling convergence | 3 个代表困难配置用 nominal `128/256/0.5µm` 与 strict `256/512/0.25µm`（同 128µm image window）比较：MTFa/VSOTF ≤2%、peak shift≤0.25D；strict PSF outer-10% energy≤0.5% |
| TDD-TEST-210 | whole-eye Zernike convention | synthetic wavefront=`defocus+C4+C6+known n3..6 HOA`，在 EPD3/EPD5 分别验证：piston/tip/tilt/defocus removed；C4/C6 `±0.005µm`；HOA RMS 等于 injected n3..6 RMS；reference center 不变 |
| TDD-TEST-211 | retinal frequency scale | known EFL fixture：`mm_per_degree=EFL·tan(1°)`，FFT cycles/mm→cpd arithmetic `atol≤1e-10` |
| TDD-TEST-212 | matched delta | synthetic rows 每个 numeric delta=`edof−mono` `atol≤1e-10` |

`COMPLEX_OTF_GOLDEN_3x3_v1` 的 source-of-truth 同时保存在 `docs/fixtures/COMPLEX_OTF_GOLDEN_3x3_v1.json`。行是 `fy=[-30,0,+30]`、列是 `fx=[-30,0,+30]` cpd，矩阵为：

\[
\begin{bmatrix}
0.162090692-0.252441295i & 0.460530497-0.194709171i & 0.243847348+0.251074632i\\
0.458905312-0.386530612i & 1+0i & 0.458905312+0.386530612i\\
0.243847348-0.251074632i & 0.460530497+0.194709171i & 0.162090692+0.252441295i
\end{bmatrix}
\]

fixture 明确规定 `OTF_DL=1` 于这 9 个离散点，并按同一离散 measure 计算 numerator/denominator；golden 数值来自固定 fixture 文件，待测实现不得在运行时重新生成“期望答案”。

## Negative / Boundary Tests

| ID | Case | Expected oracle |
| --- | --- | --- |
| TDD-TEST-301 | locked `.zos` 被篡改 | 下游前 hash check 失败 |
| TDD-TEST-302 | residual payload 缺失 | core Build 可完成；Validate `carrier_ready=False`；Build Carriers refuses |
| TDD-TEST-303 | residual platform/hash 错、payload piston/global-defocus 实测超 tolerance，或 low/median/high power gate 未完成 | no formal residual lock；metadata `defocus_removed=true` 单独不能通过 |
| TDD-TEST-304 | 5-point 未完成就 Lock B0 | rejected；no B0 lock |
| TDD-TEST-305 | 某 carrier 被替换为错误 power 的 Q | 回放 STD eye 后 achieved SA 超 tolerance → key validation fail；不以“Q 是否和别人相同”作为 oracle |
| TDD-TEST-306 | EDOF branch 改 carrier power/Q | pair invariant fails before lock |
| TDD-TEST-307 | duplicate config ID | manifest rejected |
| TDD-TEST-308 | distance peak 本身低于 absolute threshold | 合法结果：`DOF_abs=0/empty + below_absolute_threshold=True` |
| TDD-TEST-309 | mandatory image/CSV write denied | config failed；no completed row |
| TDD-TEST-310 | selection 含 manifest 外 ID | reject before Zemax |
| TDD-TEST-311 | GUI/report 把商业产品名当模型 ID | naming test fails |
| TDD-TEST-312 | busy 时再次 Run | second long action not started；busy feedback |
| TDD-TEST-313 | RunEnvironment 缺 program_version / opticstudio_version / baseline_id / settings_id / manifest_hash / lock_set_hash 任一项 | formal action cannot be completed |
| TDD-TEST-314 | CSV required column 缺失/额外未知 schema version | explicit schema error；no silent coercion |
| TDD-TEST-315 | project path 含 spaces/Unicode | store/build round-trip succeeds；metadata keeps relative paths |

## Environment / Integration Gates

| ID | Gate | Oracle |
| --- | --- | --- |
| TDD-TEST-401 | GUI-like worker thread ZOS-API | connect→PrimarySystem→New(False)→read→close 无 exception/hang；若失败，RMD 禁止 thread-owned session，改 orchestration placement |
| TDD-TEST-402 | Huygens PSF API | reference `.zos` 返回 expected image shape、finite values、positive total energy |
| TDD-TEST-403 | independent MTF cross-check | 3 representative configs 的 PSF-FFT radial MTF 与 Zemax Huygens MTF 在 10/30/50 cpd 的 relative difference ≤2%；生产数据仍只走 PSF→FFT |
| TDD-TEST-404 | offline + state durability | outbound network disabled 时运行 3 representative configs；重启 app 后 completed/failed state、RunEnvironment、artifact refs 可恢复 |

## Regression Tests

| ID | Protects | Oracle |
| --- | --- | --- |
| TDD-TEST-501 | scientific lock boundary | Assets/B0/Carrier 下游 workflow 不改变任何上游 lock hash |
| TDD-TEST-502 | experiment identity | golden carrier/config key sets 始终 exactly 18/72，除非 URD 版本改变 |
| TDD-TEST-503 | settings freeze | `CORNEA_LOCK_B0_555_v1` 与 `NOMINAL_MAIN_555_v1` serialization hash 稳定 |
| TDD-TEST-504 | surrogate naming | UI/report/export refactor 后禁止的 exact-product-as-model strings 仍为 0 |
| TDD-TEST-505 | trace coverage | 每个 `URD-AC-*`、`MDD-API-*` 至少链接 1 个 `TDD-TEST-*` |

## Deferred Test

| ID | Reason | STOP trigger |
| --- | --- | --- |
| TDD-TEST-999 | 三个平台 residual 的完整科学 payload 尚未提供；当前不能用 metadata flag 代替实际光学校准 | 实现 `MDD-API-008 Build Carriers` 前必须提供 versioned WFS/RAD/HOA payload，冻结 piston/global-defocus 数值 tolerance，并对**每个平台实际 carrier powers 的 low/median/high 代表点**完成 residual 校准 oracle；三项均通过后才能解除，不得先进入真实 carrier/Run72 |

## Execution Groups

- `unit`：store/manifest/metric math/GUI mock/path/schema 等不需 Zemax 的测试。
- `zemax`：真实 Session、Assets/B0/Carrier/Analysis、sampling、MTF cross-check、lock/hash integration。
- `gui`：GUI control/busy/naming/full-flow smoke。
- 每个测试函数只使用明确 marker；不再用“001–013 excluding...”这类范围表达。
- pre-merge command：`uv run pytest tests/unit`；Zemax workstation 必须同时满足 `uv run pytest tests/zemax`。Zemax 测试直接按目录收集，避免未选中的 GUI/数值库测试模块进入 ZOS-API 原生进程。

## TDD Completion Gate

- [x] URD-AC-001~015 均有明确 acceptance oracle；另有 72/36 final completeness。
- [x] MDD-API-001~012 均有 contract test。
- [x] A/B/C 不只检查“文件存在”，而有最小科学/构造放行 oracle。
- [x] B0 与 nominal main settings 分离；B0 使用 A0-derived Q_lock 阈值/距离 gate/确定性推荐 + 人工确认。
- [x] MTF/MTFa/VSOTF 只有一条 canonical production pipeline；FFT shift convention 与完整 complex golden fixture 均已冻结，并有 Zemax MTF 交叉检查。
- [x] `Q(P)` 通过 STD-eye achieved-SA 回放验证，而不是仅检查 CSV 字段。
- [x] tolerance 被分成 scientific/construction/convergence/repeatability/arithmetic 五类。
- [x] 72 configs / 36 matched pairs / 1080 TF rows 有 end-to-end completeness oracle。
- [x] 未加入患者级、多色、偏心/倾斜、全矩阵 convergence、阈值敏感性或复杂 GUI。
- [x] retina-anchored / shape-recentered 双坐标和 analysis-vergence 贯焦因果边界已冻结。
- [x] `ZERO_HOA_PARAXIAL_REFERENCE` 已进入标准眼/carrier oracle。
- [x] residual scientific payload + low/median/high actual-power calibration 仍是唯一显式 STOP gate。

**Result:** `TDD-0001 v1.2` 已完成基线一致性小修；测试 ID 数量不增加，进入 RMD 前只需最终审核。
