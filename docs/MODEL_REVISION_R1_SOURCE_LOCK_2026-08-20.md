# Model Revision R1 — Retina / Binary-4 mechanism source lock

> 日期：2026-08-20  
> 状态：**R1 SOURCE LOCKED FOR R2/R3 IMPLEMENTATION**  
> 分支：`feat/model-revision-binary4-physical-pupil`  
> 上游合同：`MODEL_REVISION_R0_CONTRACT_2026-08-20.md`  
> 原则：区分“外部来源直接支持的事实/参数”与“本项目 surrogate 设计选择”。不把后者包装成商业产品制造处方。

## 1. RETINA_LB_SOURCE_LOCK

### 1.1 模型身份

Primary source：

H.-L. Liou, N. A. Brennan. *Anatomically accurate, finite model eye for optical modeling*. Journal of the Optical Society of America A. 1997;14(8):1684-1695. DOI: `10.1364/JOSAA.14.001684`.

- Optica primary article: https://opg.optica.org/josaa/abstract.cfm?uri=josaa-14-8-1684
- DOI: https://doi.org/10.1364/JOSAA.14.001684

Primary article confirms the finite schematic eye identity, equivalent power `60.35 D`, axial length `23.95 mm`, and the structural prescription in its tables. The publisher page does not expose the retinal radius as a standalone row in Table 6 because the table enumerates the refracting structure up to the vitreous segment rather than an additional refracting retinal interface.

### 1.2 Retinal geometry triangulation

The retinal geometry used in established Liou–Brennan implementations is consistently a spherical image surface of radius `12 mm`:

1. Ansys OpticStudio official tutorial, *How to model the human eye in OpticStudio*, explicitly builds the Liou–Brennan retina as:

```text
Surface 8
Comment = Retina
Radius = -12 mm
Semi-Diameter = 5 mm
```

https://optics.ansys.com/hc/en-us/articles/42661744367763-How-to-model-the-human-eye-in-OpticStudio

2. Wahl et al., *Does the foveal shape influence the image formation in human eyes?*, Advanced Optical Technologies 2017, states that in the original Liou–Brennan model the retinal surface is assumed to be a pure spherical surface with radius of curvature `12 mm`, and tabulates the retina as `-12.00 mm` in its sequential prescription.

https://doi.org/10.1515/aot-2017-0043

3. Multiple later optical implementations reproduce the same `12 mm` spherical retinal curvature.

### 1.3 Frozen implementation value

For the project sequential sign convention already used by the OpticStudio reference implementation:

```text
RETINA_LB_SOURCE_LOCK
surface_type = Standard
radius_mm = -12.000
conic = 0.0
semi_diameter_mm = 5.000
axial_length_anchor_mm = 23.950
```

Confidence: **LOCKED**.

Important boundary: retinal curvature is restored, but the retinal vertex remains at the frozen axial-length anchor. Retina is not a focus solve variable.

## 2. RETINA_ATC_M3_SOURCE_LOCK

### 2.1 Primary source

D. A. Atchison. *Optical models for human myopic eyes*. Vision Research. 2006;46(14):2236-2250. DOI: `10.1016/j.visres.2006.01.004`.

- DOI: https://doi.org/10.1016/j.visres.2006.01.004
- PubMed: https://pubmed.ncbi.nlm.nih.gov/16494919/

Primary article defines two refractive-error-dependent models and states that retinal vertex curvature and asphericity vary with spectacle refraction. Model 1 is centered/coaxial; Model 2 adds lens tilt and retinal tilt/decentration. The project uses Model 1.

### 2.2 Exact Model-1 retinal equations

Atchison's later review reproduces Table 1 of the 2006 model and gives the retinal equations explicitly:

David A. Atchison, Larry N. Thibos. *Optical models of the human eye*. Clinical and Experimental Optometry. 2016. DOI: `10.1111/cxo.12352`.

https://doi.org/10.1111/cxo.12352

For spectacle refraction `SR` in diopters:

```text
Rx_mm = -12.91 - 0.094*SR
Ry_mm = -12.72 + 0.004*SR
Qx    = +0.27 + 0.026*SR
Qy    = +0.25 + 0.017*SR
```

A separate Zemax/Atchison implementation literature also represents this retinal surface as `Biconic`, consistent with separate x/y radius and asphericity.

### 2.3 SR = -3.00 D substitution

Project sample:

```text
SR = -3.00 D
```

Therefore:

```text
Rx = -12.91 - 0.094*(-3) = -12.628 mm
Ry = -12.72 + 0.004*(-3) = -12.732 mm
Qx = +0.27 + 0.026*(-3) = +0.192
Qy = +0.25 + 0.017*(-3) = +0.199
```

These values agree, to rounding, with later ray-tracing implementations of the Atchison myopic model (`Rx≈-12.62`, `Ry≈-12.73`, `Qx≈0.192`, `Qy≈0.20`).

### 2.4 Frozen implementation record

```text
RETINA_ATC_M3_SOURCE_LOCK
source_model = Atchison_2006_Model_1
source_SR_D = -3.00
surface_type = Biconic
Rx_mm = -12.628
Ry_mm = -12.732
Qx = +0.192
Qy = +0.199
semi_diameter_mm = 5.000
axial_length_anchor_mm = 24.477
```

Confidence: **LOCKED**.

Model 1's “centered” condition does not mean the retina must be rotationally symmetric. Here it means the surface is not decentered/tilted; the x/y biconic shape is retained.

## 3. WFS_SOURCE_LOCK

### 3.1 Primary mechanism source

US 9,968,440 B2, *Ophthalmic lens having an extended depth of focus*.

https://patents.google.com/patent/US9968440B2/en

Table 1 provides the representative phase-shift geometry:

```text
r1 = 0.55 mm
r2 = 0.65 mm
r3 = 0.87 mm
r4 = 1.05 mm
r5 = 1.11 mm
r6 = 3.00 mm
Delta1 = -1.02 um
Delta2 = +0.59 um
```

The patent describes the full optic as base profile plus a phase-shift component, and also gives distinct base curvatures/conics/asphere coefficients for inner/outer base regions in one embodiment.

### 3.2 What this project inherits

The project deliberately inherits only the **phase-shift residual mechanism**, because carrier spherical aberration is independently controlled by project `Q(P)`.

Therefore R0's WFS Binary 4 boundaries are:

```text
0 / 0.55 / 0.65 / 0.87 / 1.05 / 3.00 mm
```

`r5=1.11 mm` remains source provenance but is not an active extra zone in the simplified residual-only surrogate. This is a **project design choice**, not a claim that the patent has no optical boundary at 1.11 mm.

Frozen target continues to come from the existing deterministic `wfs_raw_surface_sag_um()` / normalized residual pipeline, not from final MTF.

Status: **LOCKED**.

## 4. RAD_SOURCE_LOCK

### 4.1 Primary mechanism source

US 2022/0287825 A1, *Refractive extended depth of focus intraocular lens, and methods of use and manufacture*.

https://patents.google.com/patent/US20220287825A1/en

Table 3 gives a continuous radial-power example:

| Zone | r_i–r_e (mm) | S (D) | A (D) | CosOrder |
| --- | --- | ---: | ---: | ---: |
| 1 | 0.00–0.50 | -0.25 | 0.00 | 1 |
| 2 | 0.50–0.90 | -0.25 | -3.25 | 1 |
| 3 | 0.90–1.10 | +3.00 | +3.25 | 1 |
| 4 | 1.10–1.40 | -0.25 | -0.25 | 1 |
| 5 | 1.40–2.50 | 0.00 | 0.00 | 1 |

The patent defines these zones as a continuous cosine-based power profile. The current repository's `RAD_PATENT_ZONES` reproduces these Table-3 numbers exactly.

### 4.2 Project extension to the physical optic

The public Table-3 example ends at 2.50 mm radius. The controlled project optic is 3.00 mm radius. Therefore:

```text
2.50–3.00 mm relative power = 0 D
```

is a project neutral-periphery extension, already present in the current residual seed implementation.

R0 Binary 4 boundaries are frozen as:

```text
0 / 0.50 / 0.90 / 1.10 / 1.40 / 2.50 / 3.00 mm
```

Primary fit target is `P_target(r)`, with POWP/local spherical power as the main OpticStudio readback. Sag is supporting geometry evidence, not the sole target.

Status: **LOCKED**.

## 5. HOA_SOURCE_LOCK

### 5.1 Opposite-sign C4/C6 mechanism

Two adaptive-optics studies by Bénard, López-Gil and Legras support the mechanism-level premise that opposite-sign fourth- and sixth-order spherical aberration can enlarge subjective depth of focus more than same-sign combinations:

1. Bénard Y, López-Gil N, Legras R. *Subjective depth of field in presence of 4th-order and 6th-order Zernike spherical aberration using adaptive optics technology*. J Cataract Refract Surg. 2010;36(12):2129-2138. DOI: `10.1016/j.jcrs.2010.07.022`.
2. Bénard Y, López-Gil N, Legras R. *Optimizing the subjective depth-of-focus with combinations of fourth- and sixth-order spherical aberration*. Vision Research. 2011;51:2471-2477. DOI: `10.1016/j.visres.2011.10.003`.

The 2011 study explicitly reports the largest tested DoF for an opposite-sign SA4/SA6 combination and concludes that opposite signs can substantially increase DoF for larger pupils.

### 5.2 Bench-derived numerical seed

Borkenstein AF, Borkenstein EM, Luedtke H, Schmid R. *Optical Bench Analysis of 2 Depth of Focus Intraocular Lenses*. Biomed Hub. 2021;6:77-85. DOI: `10.1159/000519139`.

https://pmc.ncbi.nlm.nih.gov/articles/PMC8613612/

Wavefront bench measurements at `546 nm` report, for the centrally modulated LuxSmart optic:

```text
Z4^0 ≈ -0.49 lambda
Z6^0 ≈ +0.46 lambda
Z8^0 ≈ -0.25 lambda
```

and an aberration-neutral outer periphery.

At 546 nm, the current project seed converts the retained 4/6 terms to:

```text
C4_seed = -0.49 * 0.546 = -0.26754 um
C6_seed = +0.46 * 0.546 = +0.25116 um
```

### 5.3 Deliberate surrogate simplification

The external bench source also reports a non-zero Z8 term. The project **deliberately excludes Z8 and higher terms** so the HOA-like surrogate isolates the opposite-sign 4th/6th-order mechanism and does not become a commercial surface reconstruction.

The following are project-defined surrogate geometry, not direct manufacturer dimensions:

```text
Zernike normalization radius = 1.00 mm
core = 0–0.90 mm
transition = 0.90–1.10 mm
neutral periphery = 1.10–3.00 mm
```

The bench paper describes a centrally confined HOA modulation and neutral outer periphery, but it does not establish the project's exact 0.90/1.10 mm boundaries as a manufacturing prescription.

R0 Binary 4 boundaries:

```text
0 / 0.90 / 1.10 / 3.00 mm
```

Primary target remains project frozen OPD + achieved C4/C6 sign/magnitude behavior, not final through-focus MTF.

Status: **LOCKED AS A MECHANISM SURROGATE**.

## 6. BINARY4_SURFACE_BEHAVIOR_SOURCE_LOCK

Primary software reference: Ansys OpticStudio User Guide, `Binary 4`.

https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v251/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Binary_4.html

The current help documents that Binary Optic 4:

- supports a variable number of concentric radial zones;
- gives each zone an independent radial aperture, radius, conic, diffraction order, even-asphere terms and optional diffractive phase data;
- uses each zone's aperture to normalize its polynomial coordinates;
- automatically offsets each successive zone in sag so sag is continuous at zone boundaries;
- allows `Np=0`;
- supports up to 60 zones and 20 aspheric/phase terms within the overall extra-data limit.

For this project, freeze:

```text
Np = 0
M_j = 0 for all zones
Na = 3
native p^2 coefficient = 0 for all zones
native p^4 / p^6 are the only polynomial sag freedoms
```

This is the software-level reason R0 treats C0 as a hard/readback condition and C1 slope continuity as a separate diagnostic.

Status: **LOCKED**.

## 7. Source-derived vs project-defined matrix

| Item | External source directly supports | Project-defined decision |
| --- | --- | --- |
| Liou retina | spherical retina, R≈12 mm in established Liou implementations | Zemax sign `-12 mm`, SD=5 mm in project stack |
| Atchison retina | SR-dependent x/y radius and asphericity; centered Model 1 | use exact SR=-3D sample, Biconic surface, SD=5 mm |
| WFS | phase-shift radii and step heights in patent embodiment | residual-only inheritance; omit active 1.11-mm base-zone split |
| RAD | Table-3 zone radii and cosine power parameters | neutral 2.50–3.00 mm extension on 6-mm optic |
| HOA | opposite-sign 4/6 mechanism; bench -0.49λ/+0.46λ and neutral outer behavior | omit Z8+; choose 0.90/1.10-mm core/transition surrogate |
| Binary 4 | multi-zone independent R/Q/asphere + automatic sag continuity | Np=0, M=0, p2=0, only p4/p6 allowed |

## 8. R1 exit conditions

R1 is complete when the implementation may rely on the following without further literature lookup:

```text
LB retina      = Standard R -12.000 mm, Q 0
ATC_M3 retina  = Biconic Rx -12.628, Ry -12.732, Qx +0.192, Qy +0.199
WFS boundaries = 0/.55/.65/.87/1.05/3.00 mm
RAD boundaries = 0/.50/.90/1.10/1.40/2.50/3.00 mm
HOA boundaries = 0/.90/1.10/3.00 mm
Binary4        = Np 0, all M 0, Na 3, p2 fixed 0
```

No OpticStudio execution has been performed in R1. The next phase is R2/R3 implementation and offline test preparation; the first local OpticStudio handoff should be bundled as one phase-gate package rather than issued as multiple micro-runs.