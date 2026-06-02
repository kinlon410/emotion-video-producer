# Repository Instructions

## CodeGraph

This project has CodeGraph MCP tools available for structural code exploration.

- Use `codegraph_search` to find symbols by name.
- Use `codegraph_context` for focused task context.
- Use `codegraph_files` before broad file exploration.
- Use `codegraph_callers`, `codegraph_callees`, and `codegraph_impact` for dependency questions.
- Use native text search only for literal strings, comments, or after opening a known file.

If CodeGraph is not initialized, ask before attempting to initialize it.

## Daily Iteration Protocol

Codex scheduled runs for this repository must follow this protocol.

### Goal

On each scheduled run, choose exactly one worthwhile task, then open either:

- a `code` PR containing a validated implementation
- a `plan` PR containing an actionable implementation plan when safe coding is not justified

### Required Context

Before choosing a task, inspect at least:

- `README.md`
- `TODOS.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- this `AGENTS.md`
- recent git history
- branch status
- relevant code and tests in affected areas
- `docs/automation/daily-iteration-state.md` if present

### Task Selection Order

Prioritize tasks in this order:

1. Weak or missing behavior protection:
   - missing tests
   - obvious validation gaps
   - documented behavior that is absent or incomplete
2. Bounded, useful improvements:
   - small feature completions
   - bug fixes
   - CLI or UI usability improvements
   - focused test additions around risky code
3. Follow-up work near recent commits:
   - unfinished edges
   - doc and code mismatches

Avoid tasks that depend on:

- secrets or live external credentials
- deployment or infrastructure access
- billing, auth, or permission changes without safe local verification
- large, unclear refactors
- behavior that cannot be meaningfully verified in this repository

### Mode Decision

Choose `code` mode only when:

- task boundaries are clear
- expected behavior is inferable from code and docs
- local verification is available
- the change is reasonably contained
- no privileged external system is required

Choose `plan` mode when:

- implementation would rely on guesswork
- the task spans multiple large subsystems
- local verification is unavailable
- secrets, external accounts, or production-like access are required
- unattended changes would carry high silent-regression risk

### Execution Rules

- Produce at most one PR per scheduled run.
- Do not open both a code PR and a plan PR in the same run.
- If code verification fails and cannot be repaired safely in the run, downgrade to `plan` mode.
- Do not repeat the previous run's task class without a clear repo-specific reason.

### Verification Rules

For `code` mode:

- run the narrowest meaningful local verification for the touched area
- read the full output before claiming success
- do not open an implementation PR if verification is failing

For `plan` mode:

- ensure the plan references real files, real constraints, and real validation paths in this repo

### Branch and PR Conventions

Branch names:

- `codex/daily-code-YYYYMMDD-<slug>`
- `codex/daily-plan-YYYYMMDD-<slug>`

PR titles:

- `[codex daily] <short task title>`
- `[codex daily plan] <short task title>`

PR bodies should use `.github/pull_request_template.md`.

### State Tracking

After preparing a PR, update `docs/automation/daily-iteration-state.md` with:

- run date
- selected task
- mode
- PR reference
- short outcome summary
