# TASK-014 实现审核：顶点距换算、术后角膜构建与72配置执行器

日期：2026-08-20  
状态：**文档、处方层、ZOS builder、72-config runner 与离线 QA 全部完成；待本地 Windows/OpticStudio 正式 acquisition**

## 1. 审核结论

TASK-014 已完成“先文档、后代码”的 Web/GitHub 实现阶段，没有改写 frozen TASK-011/TASK-012。

核心屈光定义：

```text
legacy frozen TASK-011:
  direct corneal-plane treatment = -3.000000 D
  vertex conversion = none

TASK-014:
  spectacle sphere = -3.000000 D
  vertex distance = 12.000 mm
  corneal-plane distance treatment = -2.895752895753 D
```

新术后角膜身份：

```text
A0V12
B0V12
C0V12
```

旧 A0/B0/C0 不改名、不重算、不覆盖；TASK-014 是独立 extension。

---

## 2. Git 与回退状态

修订前精确回退锚点：

```text
pre-revision HEAD = fa401e2101023e6e409a5366f26f0da134b5476f
checkpoint branch = checkpoint/pre-vertex-correction-2026-08-20
pre-revision quality gate = run #132 / 32396661153 / success
```

完整记录：

```text
docs/ROLLBACK_CHECKPOINT_VERTEX_CORRECTION_2026-08-20.md
```

冻结 TASK-008/011/012 identity 保持：

```text
TASK-008 manifest_hash = 29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49
TASK-008 lock_set_hash = b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923
TASK-011 configs = 72
TASK-011 matched pairs = 36
TASK-011 through-focus rows = 1080
TASK-012 structured evidence = unchanged
```

PR #26 继续保持 Draft / open / unmerged。

---

## 3. Prescription contract

代码：

```text
src/whole_eye_mvp/task014_vertex_corrected_cornea.py
```

冻结 contract：

```text
contract_id = TASK014_SPECTACLE_M3_VERTEX12_v1
spectacle sphere = -3.00 D
vertex distance = 12.00 mm
corneal-plane treatment = -2.895752895753 D
legacy delta = +0.104247104247 D
```

固定关系：

```text
spectacle refraction
→ vertex-distance conversion
→ distance corneal treatment
→ A/B/C mechanism modulation
```

`ATC_M3_AL24477.source_refraction_d=-3.0` 仅是 Base/source-model phenotype 信息，不与 TASK-014 surgical prescription 相加。

---

## 4. Corrected cornea ZOS builder

新增：

```text
src/whole_eye_mvp/task014_cornea_zos.py
```

构建顺序：

```text
MAIN_CORNEA_LIOU_555_v1 reference
→ TASK014 vertex-corrected distance cornea
→ A0V12
→ B0V12
→ C0V12
```

### A0V12

- distance treatment = -2.895752895753 D；
- EOZ 继承 A0；
- 使用 Binary4；
- 实际 ZOS 求解 inner-zone conic，使 `ΔC4^0(6 mm) ≈ +0.13 µm`；
- 不复用 legacy A0 的已求 conic。

### B0V12

- distance treatment = -2.895752895753 D；
- 使用 Even Asphere；
- 继续冻结 B0.20 target = `+0.20 µm`；
- 在新的 distance baseline 上重新求 R4 coefficient；
- 不根据 IOL 结果重新选择 B0 target。

### C0V12

- distance treatment = -2.895752895753 D；
- central near diameter = 3.00 mm；
- prescription ADD = +1.75 D；
- OZ = 6.50 mm；
- transition = 0.75 mm；
- N = 8；
- ADD 仍为处方级输入，不强制等同于某一局部 ray-traced vergence。

reference、distance、A0V12/B0V12/C0V12 均保存为 `.zmx` 并进入模型索引。

---

## 5. TASK-014 extension identity

新增：

```text
src/whole_eye_mvp/task014_extension.py
```

固定规模：

```text
2 Base × 3 corrected cornea × 3 Platform = 18 carriers
18 carriers × MONO/EDOF × EPD3/EPD5 = 72 configs
36 matched MONO/EDOF pairs
72 × 15 = 1080 through-focus rows
```

每个 carrier lock 绑定：

- Base / corrected cornea / Platform；
- physical P/R/Q/CT/material/IOL position；
- frozen residual provenance；
- TASK-014 prescription-contract SHA；
- independent lock hash。

TASK-014 manifest/hash 不替代 TASK-008 frozen manifest/hash。

---

## 6. Carrier P→Q(P) 与 residual gate

新增：

```text
src/whole_eye_mvp/task014_zos.py
```

每个 `Base × corrected cornea × Platform`：

```text
actual eye Q=0 P/R solve
→ STD_IOL_EYE_2024 power-specific Q(P)
→ actual-eye P–Q recheck, max 2 cycles
→ final actual-eye R/Q replay
→ final standard-eye EPD6 SA replay
→ canonical physical carrier ZMX
```

不得从 legacy A0/B0/C0 carrier 复制 P/R/Q。

18个新 carrier 全部产生后，正式 EDOF acquisition 前执行 residual power-envelope gate：

```text
existing frozen platform min power
<= corrected carrier power
<= existing frozen platform max power
```

若任一超界：

- STOP；
- 不进入 EDOF production；
- 不修改 residual bytes；
- 先增加原 residual 在该 actual power 的 replay/污染/ray-health validation。

---

## 7. Production runner

新增：

```text
scripts/run_task_014_vertex_corrected_cornea.py
```

正式顺序：

```text
verify frozen TASK-008 / standard eye
→ build 5 cornea-layer ZMX files
→ solve and archive 6 Q=0 Base×Cornea start models
→ solve 18 P/Q carriers
→ residual power-envelope gate
→ build independent 72-config TASK-014 manifest
→ measure 36 residual-free paired-MONO EFFL references
→ run 72 TASK-009 production configs
→ validate ConfigResult
→ archive 72 config-specific ZMX files
→ write/validate MODEL_INDEX.csv
→ optional sanitized GitHub evidence
```

分析设置严格继承 TASK-009：

```text
NOMINAL_MAIN_FFT_MTF_555_v2
TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2
paired_residual_free_MONO_EFFL
sampling = 128
555 nm
EPD3 / EPD5
field = 0 deg
retina defocus +0.50 → -3.00 D
step = -0.25 D
15 planes
```

MONO/EDOF pair 唯一设计差异仍为 frozen EDOF residual。

---

## 8. Canonical ZMX 输出契约

**实现后的唯一权威目录**为：

```text
project_mvp_2026_v2_zmx/
└─ models/
   └─ task014_vertex_corrected/
      ├─ corneas/
      │  ├─ REFERENCE_CORNEA.zmx
      │  ├─ DISTANCE_CORNEA_VERTEX12.zmx
      │  ├─ CORNEA_A0V12.zmx
      │  ├─ CORNEA_B0V12.zmx
      │  └─ CORNEA_C0V12.zmx
      ├─ carriers/
      │  └─ CAR_<base>_<A0V12|B0V12|C0V12>_<platform>.zmx   # 18
      └─ runs/<run_id>/
         ├─ p0/
         │  └─ P0_<base>_<cornea>.zmx                       # 6
         ├─ pair_references/
         │  └─ <pair_key>.zmx                               # 36
         ├─ configs/
         │  └─ <config_id>.zmx                              # 72
         └─ MODEL_INDEX.csv
```

注意：早期 plan 中的 `task014_vertex_corrected_postop/` 是“建议目录”；本实现审核将上述 `task014_vertex_corrected/` 冻结为实际 canonical path，后续脚本、归档和审计均以此为准。

完整成功运行时，`MODEL_INDEX.csv` 预期至少包含：

```text
5 cornea-layer models
+ 6 Q=0 start models
+ 18 physical carriers
+ 36 pair references
+ 72 analyzed configs
= 137 indexed ZMX records
```

每个 analyzed config `.zmx` 在 production analysis 前写入自身 EPD3/EPD5 并 SaveAs，因此是 config-specific persisted snapshot；归档 SHA 必须与 `ConfigResult.model_hash_before` 一致。

---

## 9. GitHub evidence contract

成功后可写：

```text
docs/evidence/task014/TASK_014_EVIDENCE.json
docs/evidence/task014/TASK_014_CONFIG_RESULTS.csv
docs/evidence/task014/TASK_014_THROUGH_FOCUS.csv
docs/evidence/task014/TASK_014_PAIRED_DELTAS.csv
docs/evidence/task014/TASK_014_MODEL_INDEX.csv
```

GitHub evidence 不提交 `.zmx` binary，只记录结构化数值、project-relative path 与 SHA。

TASK-014 evidence 必须明确：

```text
source_task011_rerun = false
task011_structured_evidence_changed = false
rollback_checkpoint = checkpoint/pre-vertex-correction-2026-08-20
```

---

## 10. Offline tests / QA

新增测试：

```text
tests/unit/test_task014_vertex_corrected_cornea.py
tests/unit/test_task014_extension.py
```

覆盖：

1. spectacle↔corneal plane conversion roundtrip；
2. legacy baseline 仍为 direct `-3.00 D`；
3. A0V12/B0V12/C0V12 identity 和 target；
4. independent 18-carrier / 72-config / 36-pair manifest；
5. MONO 无 residual、EDOF 有完整 residual provenance；
6. legacy A0 identity 不允许进入 TASK-014 carrier；
7. residual power-envelope pass/fail-closed semantics。

ZOS implementation code baseline：

```text
f332da42a84832a088ff401023cdf75b226ba407
```

Offline quality gate：

```text
run #148
run_id = 32406684311
conclusion = success
pytest = 229 passed
ruff = PASS
compileall = PASS
uv lock --check = PASS
```

此前 run #146 的唯一失败原因是2个 Ruff import-order formatting errors；229 tests、compileall 和 lock 已通过。随后仅修 import formatting，科学逻辑未改变。

RMD Phase-C 状态同步：

```text
docs/RMD_TASK014_PHASE_C_ADDENDUM_2026-08-20.md
```

---

## 11. 当前尚未产生的事实

当前 Web/GitHub 环境没有运行 OpticStudio，因此以下数值**尚不存在**：

- A0V12/B0V12/C0V12 的真实 ZOS readback；
- 18个 corrected carrier 的实际 P/R/Q；
- residual power-envelope 实际 PASS/FAIL；
- 36个 pair-MONO EFFL；
- 72条 corrected-cornea MONO/EDOF 贯焦曲线；
- 1080个 TASK-014 through-focus rows。

不得在本地 acquisition 完成前把这些写入论文结果。

---

## 12. 本地执行命令

完整本地交接文件：

```text
docs/TASK_014_LOCAL_EXECUTION_HANDOFF_2026-08-20.md
```

核心命令：

```powershell
uv run python scripts/run_task_014_vertex_corrected_cornea.py `
  --project-dir "C:/Users/golde/code/inspiration-overflow/Cornea-EDOF-IOL-coupling/project_mvp_2026_v2_zmx" `
  --write-repo-evidence
```

若未设置环境变量，再加：

```text
--install-dir <OpticStudio install dir>
```

首次正式运行不应使用 `--overwrite-models`；该参数只用于明确授权的重建。

---

## 13. Local acceptance

必须全部满足：

```text
corrected cornea assets = 3/3
Q=0 start models = 6/6
physical carriers = 18/18
residual power-envelope = PASS
pair references = 36/36
completed configs = 72/72
failed configs = 0
through-focus rows = 1080
matched pairs = 36
config ZMX = 72/72
MODEL_INDEX path/SHA replay = PASS
model_archive_complete = true
acceptance_passed = true
```

随后才进入 Web evidence review。

---

## 14. 与 TASK-013 的最终关系

TASK-013 N0 本身无 myopic treatment，因此仍可独立运行。

临床屈光平面规范化后的完整研究层为：

```text
TASK-013 N0                         24 configs
TASK-014 A0V12/B0V12/C0V12         72 configs
------------------------------------------------
clinically normalized total         96 configs
```

而：

```text
TASK-013 N0 + frozen TASK-011 A0/B0/C0
```

只能作为 legacy engineering descriptive comparison，不能冒充上述 clinically normalized 96-config layer。

---

## 15. 当前结论

```text
legacy TASK-011/012 = unchanged / reproducible
rollback checkpoint = established
TASK-013 N0 code = ready / local optical acquisition pending
TASK-014 prescription contract = frozen
TASK-014 corrected-cornea ZOS builder = complete
TASK-014 18-carrier / 72-config runner = complete
TASK-014 ZMX archive/index contract = complete
TASK-014 offline QA = PASS
TASK-014 OpticStudio acquisition = NOT RUN
```
