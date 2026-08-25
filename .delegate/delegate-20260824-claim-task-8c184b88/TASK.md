# Delegated task

## Task ID

`delegate-20260824-claim-task-8c184b88`

## Instruction

Use the existing authorized ChatGPT Web conversation supplied by the user to determine the
current concrete work objective for this repository. Treat the latest task assignment and
acceptance criteria in that conversation as authoritative. Do not start implementation, modify
source code, run an unapproved live regression test, merge branches, or modify the default branch.

Write a concise task brief to
`.delegate/delegate-20260824-claim-task-8c184b88/CLAIMED_TASK.md` containing:

1. the objective;
2. the requested division of work between local Codex and ChatGPT Web;
3. expected inputs and outputs;
4. acceptance criteria;
5. unresolved questions or blockers, if any.

If the conversation does not contain a concrete task, state that fact explicitly instead of
inventing one. Then write `.delegate/delegate-20260824-claim-task-8c184b88/result.json` using the
manifest contract, commit both output files on this task branch, and reply with only the compact
receipt described in the dispatch protocol.

## Scope constraints

- Repository: `Inspiration-Overflow/Cornea-EDOF-IOL-coupling`
- Task branch: `delegate/delegate-20260824-claim-task-8c184b88`
- Read paths: `README.md`, `pyproject.toml`, and `docs/`
- Write paths: `.delegate/delegate-20260824-claim-task-8c184b88/CLAIMED_TASK.md` and
  `.delegate/delegate-20260824-claim-task-8c184b88/result.json`
- Do not use chat attachments, ZIP files, or paste substantive file contents into chat.

## Acceptance criteria

- The task brief is grounded in the existing conversation and does not invent a task.
- The result record matches the task ID, repository, task branch, and dispatch commit.
- The result commit is reachable from the task branch and changes only authorized paths.
