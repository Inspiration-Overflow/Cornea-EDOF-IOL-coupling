# 本地 OpticStudio 联调与验收顺序

本清单用于最后一次 Windows + Ansys Zemax OpticStudio 本地调试。按顺序执行，不跳过 science gate。

## 0. 环境固定

在仓库根目录：

```powershell
git pull origin main
uv lock
uv sync
uv run ruff check .
uv run pytest tests/unit
```

要求：

- 提交 `uv.lock`；
- unit tests 全通过；
- ruff 全通过；
- 记录 Python、程序版本、OpticStudio 版本。

设置 OpticStudio 安装目录，例如：

```powershell
$env:WHOLE_EYE_ZOS_INSTALL_DIR = "C:\Program Files\Ansys Zemax OpticStudio 2026 R1.00"
```

实际路径以本机安装为准。

## 1. Session 与线程风险闸门

```powershell
uv run pytest tests/zemax -m zemax -k "session or worker_thread"
```

Zemax 测试必须直接从 `tests/zemax` 收集。本机在收集完整测试树后再用 `-m zemax`
筛选时，ZOS-API 原生进程可能以 `0xc0000139` 退出；直接收集 Zemax 目录的同一批测试通过。

验证：

- 能取得 `PrimarySystem`；
- license 有效；
- Sequential Mode 正常；
- context 退出后关闭；
- GUI-like worker thread 不 hang。

若 worker-thread gate 失败，不继续 thread-owned session；只调整 GUI/workflow orchestration placement，不改科学模块。

## 2. ZOS-API 面型与 analysis-specific 映射

仓库已经提供：

- `whole_eye_mvp.zos.session`：会话生命周期；
- `whole_eye_mvp.zos.primitives.SequentialEditor`：顺序模式基础编辑；
- `whole_eye_mvp.zos.primitives.SystemAnalysisRunner`：通用 analysis lifecycle；
- `whole_eye_mvp.zos.analyses`：Huygens PSF 与 Zernike Standard 的专用设置、结果复制和校验。

本机已用 2026 R1.00 的临时顺序系统确认：

- Binary 4 的 zone、asphere、phase `ParN` 映射；
- Even Asphere 的 2 阶至 16 阶参数列；
- Coordinate Break 的偏心、倾斜和 order 参数列；
- Huygens PSF 的采样、图像间隔、归一化和结果网格复制；
- Zernike Standard Coefficients 的 UTF-16 文本输出及 Z1…Zmax 严格解析。

仍待确认和实现：Coordinate Return、footprint、Prescription Data、Huygens MTF 专用接口。

不要在未验证参数列含义时把猜测写成正式模型。

当前 API smoke 回归命令：

```powershell
uv run pytest tests/zemax
```

## 3. TASK-005：基础科学资产

依次建立并保存：

1. 原始 Liou–Brennan / Atchison M3 验证文件；
2. `BASE_LB_PSEUDOPHAKIC.zos`；
3. `BASE_ATC_M3_PSEUDOPHAKIC.zos`；
4. `STD_IOL_EYE_2024.zos` + `ZERO_HOA_PARAXIAL_REFERENCE`；
5. `REF_MONO_CORNEA_LOCK`；
6. A0；
7. B 五个候选；
8. C0。

必须验证 RMD/TDD 的轴长、STOP、IOL 位置、标准眼 C4、footprint、介质、C0 transition 和数值收敛要求。

## 4. TASK-006：真实 B0 扫描与冻结

固定：

- `LB_AL2395 + REF_MONO_CORNEA_LOCK`；
- 555 nm；
- EPD3 主选择，EPD5 检查；
- +0.50 → −3.50 D，0.25 D step。

把真实 Q_lock 曲线交给现有 `rank_b0_candidates()`；人工只负责 morphology reject/理由和最终确认/override reason。写 B0 lock 后不得根据 EDOF 主结果回调。

## 5. TASK-007：carrier / residual science gate

先求 18 个 provisional carrier：

1. 实际 Base × Cornea 中以 Q=0、residual=0 求 P；
2. `STD_IOL_EYE_2024` 中按实际 P 求 Q；
3. 回实际眼做 1–2 次 P–Q 检查；
4. 以 ZERO_HOA reference 回放 achieved SA。

目标：

- WFS `−0.20 ± 0.01 µm`；
- RAD `−0.27 ± 0.01 µm`；
- HOA `0.00 ± 0.01 µm`。

然后提供 versioned WFS/RAD/HOA residual payload，验证：

- payload hash；
- piston removed；
- global defocus removed；
- 每个平台实际 power 范围的 low/median/high 三点校准。

全部通过后才解除 `TDD-TEST-999`。

## 6. TASK-008：正式 locks 与 manifest

把真实：

- 18 validated carriers；
- 3 validated residuals；
- 每个 carrier 的 `ΔF_residual`；

交给 `finalize_carrier_locks()` / `finalize_and_export_manifests()`。

验收：

- 18 unique carrier locks；
- 72 unique configs；
- 36 matched pairs；
- `physical_carriers.csv` / `nominal_72.csv` / manifest hash 可重复。

## 7. TASK-009：先跑 3 个代表配置

不要先跑 72。

先完成：

- Huygens PSF 128×128 pupil / 256×256 image / 0.5 µm delta；
- strict 256×256 / 512×512 / 0.25 µm convergence；
- PSF → complex OTF → MTF/MTFa/VSOTF；
- whole-eye C4/C6/HOA；
- cornea/STOP/IOL footprints；
- Huygens MTF 10/30/50 cpd 独立 cross-check。

只有 sampling convergence、outer-energy、MTF cross-check 都通过，才进入 Run72。

## 8. TASK-010：GUI smoke

检查：

- Build；
- Validate；
- B0 Scan / Lock；
- Build Carriers；
- Run72；
- Rerun；
- install path / project path / progress / log / output 可见；
- busy 时不启动第二个 long action；
- workflow error 只显示 failed，不显示 completed。

## 9. TASK-011：真实 Run72

满足所有前置 gate 后运行正式 72 configs。

最终必须满足：

```text
completed configs = 72
matched pairs     = 36
through-focus rows = 1080
```

并进行重复性复跑：

- MTFa / VSOTF ≤ 0.1% relative difference；
- C4 / C6 ≤ 0.001 µm；
- distance-peak grid sample 相同；
- manifest / lock hashes 不变。

任何单配置失败都保留其他成功结果；修复后只用 Rerun 重跑失败目标，并生成新的 `run_id`。
