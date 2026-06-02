# Codex Daily Iteration Design

## Goal

Use Codex scheduled tasks to analyze this repository once per day, select exactly one worthwhile development task, execute it when safe, and publish the result as a branch plus pull request. When safe execution is not possible, Codex should publish a plan PR instead of forcing a code change.

## Non-Goals

- Running autonomous development logic inside GitHub Actions
- Merging pull requests automatically
- Completing multiple tasks in a single daily run
- Guaranteeing changes in areas that require external credentials, production access, or manual product decisions

## Constraints

- The scheduler is Codex scheduled tasks, not GitHub Actions.
- Each run may produce at most one PR.
- Codex may choose between a code PR and a plan PR.
- Branch creation, commits, and PR creation happen from the Codex task run.
- The system should prefer useful progress over arbitrary daily churn.

## Daily Run Flow

1. Codex starts in the repository on a daily schedule.
2. Codex gathers project context from a fixed set of files and repository metadata.
3. Codex identifies candidate tasks and ranks them by value, clarity, and verifiability.
4. Codex selects exactly one task.
5. Codex decides execution mode:
   - `code`: implement the task, verify it locally, create branch, commit, and open PR
   - `plan`: write an implementation plan explaining the task and why it was not auto-implemented, then create branch, commit, and open PR
6. Codex records the outcome so the next run can avoid repetition.

## Required Context Inputs

Every daily run should inspect these sources before choosing a task:

- `README.md`
- `TODOS.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
- recent git history
- current branch status
- relevant code under `core/`, `agent/`, `web/`, `tests/`, and other touched modules

The run should also inspect any repo-local automation notes or state files created for the daily iteration system.

## Task Selection Rules

Codex should prioritize tasks in this order:

1. Broken or weakly defended behavior:
   - missing or weak tests near important code
   - obvious validation gaps
   - documented functionality that is absent or incomplete
2. High-value, bounded improvements:
   - small feature completions
   - bug fixes
   - CLI or UI usability improvements
   - test coverage additions around risky code
3. Follow-up work created by recent commits:
   - unfinished edges near the latest changes
   - inconsistencies between docs and implementation

Codex should avoid selecting tasks that depend on:

- secrets or real external credentials
- deployment or infrastructure access
- billing, auth, or permission changes with no safe local verification
- broad refactors with unclear boundaries
- changes that cannot be meaningfully validated in the repository

## Mode Decision

Codex should choose `code` mode only when all of the following are true:

- the task boundary is clear
- the expected behavior is inferable from existing code and docs
- the affected surface area is reasonably contained
- there is at least one concrete local verification step
- the change does not require privileged external systems

Codex should choose `plan` mode when any of the following are true:

- implementation would rely on guesswork
- the task spans multiple large subsystems
- verification cannot be done locally
- the task needs secrets, external accounts, or production-like access
- the risk of silent regression is too high for unattended execution

## Branch, Commit, and PR Conventions

Suggested branch naming:

- `codex/daily-code-YYYYMMDD-<slug>`
- `codex/daily-plan-YYYYMMDD-<slug>`

Suggested commit message prefixes:

- `feat:`
- `fix:`
- `test:`
- `docs:`
- `plan:`

Suggested PR title formats:

- `[codex daily] <short task title>`
- `[codex daily plan] <short task title>`

## Pull Request Requirements

Each PR should include:

- the selected daily task
- why Codex chose it
- whether the PR is `code` or `plan`
- files changed
- verification performed
- known risks
- if `plan`: why the task was not safely auto-implemented

## Repository Changes Needed

### 1. `AGENTS.md`

Add a `daily iteration protocol` section that defines:

- required context gathering
- task selection order
- code vs plan decision rules
- branch naming
- PR title and body format
- mandatory verification before opening a PR
- requirement to avoid repeating the previous run's task class without a good reason

### 2. PR Template

Add a pull request template for Codex daily runs under `.github/` so generated PRs are structurally consistent.

### 3. Automation Docs

Add `docs/automation/daily-iteration.md` describing:

- purpose
- run flow
- decision rules
- failure behavior
- operator expectations for review and merge

### 4. State Tracking

Add a lightweight repo-local state file such as `docs/automation/daily-iteration-state.md` to capture:

- date of last run
- chosen task
- mode used
- PR link or identifier
- short outcome summary

This state file helps reduce repeated task selection across consecutive runs.

## Failure Behavior

If Codex cannot safely produce a valid code PR, it should still try to produce a plan PR. If neither code nor a plan can be produced cleanly, the run should stop without modifying unrelated files and report the blocker in the task output.

## Verification Rules

For `code` mode, Codex must run only the narrowest meaningful verification available, such as:

- targeted `pytest` cases
- small module-level tests
- repo checks tied to the changed files

If verification fails, Codex should not push the code as a finished implementation PR. It should either fix the failure within the same run or downgrade to a plan PR.

For `plan` mode, Codex must verify that the written plan maps to real files and real repo constraints rather than generic advice.

## Risks

- Repetitive or low-value task selection if prompts are too loose
- Noisy PRs if branch and PR conventions are not standardized
- False confidence if a code change passes narrow tests but misses broader regressions
- Drift between the automation protocol in docs and the instructions Codex actually follows

## Mitigations

- Keep the selection protocol explicit in `AGENTS.md`
- Require one-task-per-run output discipline
- Require local verification or downgrade to plan mode
- Record previous outcomes in a repo-local state file
- Keep PR template fields mandatory enough to make weak runs obvious during review

## Implementation Direction

This design intentionally keeps the execution engine lightweight. The main control surface is repository instructions and templates that shape Codex scheduled task behavior. Initial implementation should focus on:

1. repository protocol updates
2. PR template support
3. automation docs
4. state tracking

After those are in place, the Codex scheduled task can run against the repository with a stable operating contract.
