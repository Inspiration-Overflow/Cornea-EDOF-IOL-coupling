# Claimed task

## Objective

Implement, with local Codex as the code-execution agent and ChatGPT Web as the review/acceptance counterpart, the supplemental experiment plan for the corneal presbyopia correction × non-diffractive EDOF IOL coupling study without expanding the frozen MVP scope.

The concrete implementation target is to support two supplemental experiment branches and their derived analyses:

1. Re-run the existing 96 configurations with an expanded through-focus sweep of +1.00 D to -5.00 D in 0.125 D steps (49 planes) and a far-focus peak search restricted to -1.00 D to +1.00 D.
2. Add only the 24 central-near radial multifocal-cornea configurations using the distance-component-anchored IOL calibration strategy: temporarily set the +1.75 D central near add to zero for IOL base-power solving and mechanism-specific base spherical-aberration calibration, freeze the IOL carrier, restore the +1.75 D near add, then prohibit any further IOL power adjustment or refocus before computing matched monofocal and EDOF states.

Derived analyses should use those generated through-focus data only: relative 30%/50%/70% depth of focus, untreated-reference-anchored common threshold, 30 cycles/degree through-focus curves, and per-eye/per-pupil/per-mechanism difference-in-differences for corneal-background modulation of the EDOF effect. Boundary censoring must remain explicit rather than numerically imputed.

## Division of work

- **Local Codex:** inspect the permitted repository implementation context, make the code/config/test changes required for the supplemental experiment workflow, run only approved local/offline checks, and report diffs/results for review.
- **ChatGPT Web:** preserve the experimental contract, review implementation choices and diffs against the frozen study design, help define/inspect tests and output invariants, judge anomalous results, and perform stage acceptance. ChatGPT Web should not silently broaden the experiment matrix or alter frozen model assumptions.

## Expected inputs

- The existing repository at the authorized task/base state.
- The conversation-approved supplemental experiment specification `角膜老视矫正_EDOF_IOL_补充实验方案.md`.
- Existing frozen model definitions and production outputs for the 2 eyes × 4 corneas × 3 IOL mechanisms × 2 IOL states × 2 pupils matrix.

## Expected outputs

For the eventual implementation task, the workflow should be capable of producing:

- expanded through-focus configuration-level data for the original 96 configurations;
- 24 distance-component-anchored central-near radial multifocal-cornea configuration outputs using the same expanded sampling;
- matched-pair summaries including relative 30%/50%/70% depth of focus, 0 D quality, best far-focus peak quality, and censoring state;
- a comparison table for the two central-near-cornea IOL calibration strategies;
- data needed for the four predefined supplemental figures and the stated difference-in-differences analysis.

This delegated claim task itself must only create `CLAIMED_TASK.md` and `result.json`; it must not implement or run the optical experiments.

## Acceptance criteria

- Existing frozen main analysis, corneal designs, EDOF structures, model eyes, materials/geometries, pupils, and shared monofocal/EDOF carrier rules remain unchanged.
- The original 96 configurations use exactly +1.00 D to -5.00 D at 0.125 D spacing, with far-focus peak search limited to ±1.00 D.
- The distance-component-anchored branch is limited to the central-near radial multifocal cornea and exactly 24 configurations.
- After restoring the +1.75 D near add, no autofocus, refocus, IOL power solve, or carrier re-optimization is allowed.
- Matched monofocal and EDOF states share the same frozen IOL carrier; the EDOF structure is the only state difference.
- Relative-threshold, common-threshold, 30 cycles/degree, and difference-in-differences analyses are derived from existing supplemental sweep data and do not trigger extra Zemax/OpticStudio runs.
- Residual depth-of-focus boundary censoring at -5.00 D is reported as censoring; the sweep is not extended further solely to eliminate remaining censored cases.
- No new model eyes, corneal designs, parameter scans, decentration/tilt, astigmatism, tear film, chromatic, binocular, neural, or patient-level variables are added.

## Unresolved questions or blockers

No blocker is present in the conversation for claiming the task. Implementation-specific repository locations, APIs, and exact test commands should be resolved by local Codex from the authorized repository context before changing source code; any conflict with the frozen experimental rules should be returned to ChatGPT Web for review rather than guessed.
