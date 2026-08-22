# Correct final-review output paths

- task_id: `r6-r7-r5-2-final-review-path-fix-20260822`
- repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- frozen base commit: `1249c25b76f6775a3b13401062e49d5cb7c7deb2`
- task branch: `delegate/r6-r7-r5-2-final-review-path-fix-20260822`
- result contract: `.delegate/r6-r7-r5-2-final-review-path-fix-20260822/result.json`

## Instruction

The preceding Web task produced valid-looking final review content, but used output filenames that
did not match its manifest's authorized paths. This corrective task is only for making the output
paths conform. Read the two existing documents and the preceding result contract, then write exact
content-preserving copies at the authorized output paths below. Do not change their scientific
content, do not change code, do not run OpticStudio, and do not modify the preceding branch.

The preceding result commit is `1249c25b76f6775a3b13401062e49d5cb7c7deb2`. Its existing files are:

- `docs/R5_2_R6_R7_FINAL_VALIDATION_REVIEW_2026-08-22.md`
- `docs/MANUSCRIPT_R5_2_R6_R7_RESULTS_ADDENDUM_2026-08-22.md`
- `.delegate/r6-r7-r5-2-final-review-20260822/result.json`

Copy the exact content of the first two files to the authorized names. Do not invent a new review,
add claims, or rewrite numerical results. The new result.json must point only to the corrected
output refs and use this task's task ID and dispatch commit. Do not put the result commit SHA in
result.json.

## Authorized read paths

- `docs/R5_2_R6_R7_FINAL_VALIDATION_REVIEW_2026-08-22.md`
- `docs/MANUSCRIPT_R5_2_R6_R7_RESULTS_ADDENDUM_2026-08-22.md`
- `.delegate/r6-r7-r5-2-final-review-20260822/result.json`

## Authorized write paths

- `.delegate/r6-r7-r5-2-final-review-path-fix-20260822/`
- `docs/R6_R7_R5_2_FINAL_VALIDATION_REVIEW_2026-08-22.md`
- `docs/MANUSCRIPT_R5_2_RESULTS_ADDENDUM_2026-08-22.md`

## Acceptance criteria

1. The two corrected files exist at exactly the authorized paths and have byte-identical content
   to their corresponding preceding files.
2. No source, test, manuscript draft, default branch, or preceding task branch is modified.
3. The result.json task ID, repository, task branch, dispatch commit, and output refs match this
   task; it contains a concise limitation that the preceding task was rejected for path mismatch
   and this task only corrected paths.
4. Reply only with a compact receipt containing task_id, repository, task_branch, result_commit,
   result_ref, summary, and limitations.
