# Task contract: R8 final manuscript drafting and scientific review

- task_id: `r8-manuscript-finalization-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `4d5e2ccf7e9e17319542b4062781ac7100d9489e`
- task branch: `delegate/r8-manuscript-finalization-20260822`
- transport: `github_direct`

## Objective

Write and review a reader-facing final manuscript grounded in the accepted R8 96-config
OpticStudio production evidence and the committed R8 offline integration. Preserve the scientific
scope: this is a computational whole-eye optical study, not a clinical outcome study. Do not
reuse the older Task015 numerical results where R8 results are available.

The final manuscript must include, in plain technical language:

- title, abstract, introduction, methods, results, discussion, limitations, conclusion, data/code
  availability, and a concise references/notation section if the existing drafts require it;
- exact R8 design and acquisition facts: 96 configs, 48 MONO/EDOF pairs, 1440 through-focus rows,
  2 bases × 4 corneal states × 3 platform surrogates × 2 pupils × 2 optic states, 3/5-mm physical
  pupils, 15 retinal-defocus planes from +0.50 to −3.00 D, MFE MTFA Grid=1 at production sampling
  128, and the paired residual-free MONO EFFL frequency scale;
- exact R8 results from the committed analysis evidence: 25 exact, 19 lower-bound, 3 upper-bound,
  and 1 indeterminate DOF50 pair effects; 9 peak-window-censored pairs; ΔMTFa(0 D) negative in
  48/48 pairs; Δthrough-focus MTFa mean negative in 48/48 pairs; mean ΔDOF50 = 0.16694 D with
  6 negative and 42 positive pair effects, with censoring handled explicitly;
- the R5.2/R6/R7 Binary4 model provenance, copy-on-write acquisition, no residual reapplication,
  no carrier rebuild, no IOL refit, entity fingerprint integrity, and the distinction between
  local R8 acquisition PASS and the still-required manual Web scientific review gate;
- table and figure captions that point to the committed R8 evidence and figures without claiming
  more than the evidence supports;
- a final scientific QC document listing numerical, factorial, through-focus reconstruction,
  paired-delta, artifact-hash, entity-integrity, figure, and wording checks.

Use the existing manuscript drafts for structure and background, but revise numerical claims to R8.
Do not invent clinical subjects, visual-acuity outcomes, statistical tests, confidence intervals,
or external validation. Do not call the R8 run clinically validated.

## Constraints

- Do not run OpticStudio or change runtime evidence.
- Do not modify the default branch, preceding branches, source code, or accepted Task015 evidence.
- Work only in this repository, this task branch, and the declared paths.
- Read R8 production evidence and R8 offline analysis evidence from GitHub before drafting.
- Write substantive outputs directly to the task branch and commit them. Do not paste full files or
  use attachments/ZIPs.

## Expected outputs

- `docs/MANUSCRIPT_FINAL_R8_2026-08-22.md`
- `docs/MANUSCRIPT_R8_SCIENTIFIC_QC_2026-08-22.md`
- `docs/MANUSCRIPT_R8_FIGURE_TABLE_PLAN_2026-08-22.md`
- `.delegate/r8-manuscript-finalization-20260822/result.json`
