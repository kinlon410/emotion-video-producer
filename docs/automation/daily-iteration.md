# Codex Daily Iteration

## Purpose

This repository uses Codex scheduled tasks to perform one daily iteration at a time. Each run should create either:

- a validated code PR for one bounded task
- a plan PR when direct implementation is not safe or verifiable

The goal is steady, reviewable progress rather than forced churn.

## Required Context

Each run should inspect:

- `README.md`
- `TODOS.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
- recent git history
- current branch status
- the relevant code and tests for candidate tasks
- `docs/automation/daily-iteration-state.md`

## Task Selection Rules

Prefer tasks that are both valuable and bounded:

1. weak or missing tests around important behavior
2. validation gaps or obvious bug fixes
3. documented behavior that is absent or incomplete
4. small, useful feature completions
5. recent-change follow-up work with clear local verification

Do not force direct code changes when the task depends on secrets, external accounts, deployment access, or broad guesswork.

## Mode Rules

### `code`

Use `code` mode only when:

- expected behavior can be inferred from the repository
- affected files are reasonably contained
- meaningful local verification exists
- no privileged external system is required

### `plan`

Use `plan` mode when:

- the task is too ambiguous
- the task spans multiple large subsystems
- verification cannot be run locally
- the change requires secrets or live service access
- unattended implementation risk is too high

## Execution Rules

- one run selects one task
- one run opens at most one PR
- a failed code verification should trigger repair or downgrade to `plan`
- PRs should use the repository PR template
- update the state file after the run outcome is known

## Reviewer Expectations

Reviewers should check:

- whether the selected task was worth the daily slot
- whether `code` vs `plan` mode was chosen correctly
- whether verification was appropriate for the touched files
- whether follow-up risk is described honestly

## Failure Handling

If no safe code change can be completed, produce a plan PR. If even a plan cannot be grounded in repository reality, stop without unrelated edits and report the blocker in the run output.
