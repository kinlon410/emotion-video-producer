# Codex Daily Iteration Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the repository-side operating contract for Codex scheduled daily iteration so future automated runs can consistently choose one task, verify it, and open a branch plus PR.

**Architecture:** Add repository instructions and templates instead of building a separate runtime. The implementation updates the repo root instruction file, introduces a PR template, adds automation documentation, and creates a lightweight state file for run tracking.

**Tech Stack:** Markdown, GitHub pull request templates

---

### Task 1: Add Repository Protocol

**Files:**
- Create: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-06-02-codex-daily-iteration-design.md`

- [ ] **Step 1: Write the failing validation check**

Expected behavior: the repository should contain an `AGENTS.md` file with a dedicated `daily iteration protocol` section describing context gathering, task selection, mode decision, verification, and PR conventions.

- [ ] **Step 2: Run validation to verify the file is missing**

Run: `test -f AGENTS.md`
Expected: exit code `1`

- [ ] **Step 3: Write the minimal implementation**

Create `AGENTS.md` with:
- project-level instructions for Codex scheduled runs
- a `daily iteration protocol` section matching the approved design
- one-task-per-run, `code` vs `plan`, and verification rules

Also update the design spec if self-review reveals any mismatch with the concrete repository protocol.

- [ ] **Step 4: Run validation to verify the file now exists**

Run: `test -f AGENTS.md`
Expected: exit code `0`

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md docs/superpowers/specs/2026-06-02-codex-daily-iteration-design.md
git commit -m "docs: add codex daily iteration protocol"
```

### Task 2: Add Codex Daily PR Template

**Files:**
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Write the failing validation check**

Expected behavior: the repository should contain a PR template tailored for Codex daily runs and plan fallbacks.

- [ ] **Step 2: Run validation to verify the file is missing**

Run: `test -f .github/pull_request_template.md`
Expected: exit code `1`

- [ ] **Step 3: Write the minimal implementation**

Create `.github/pull_request_template.md` with sections for:
- selected task
- why it was chosen
- execution mode
- files changed
- verification
- risks
- plan fallback explanation when applicable

- [ ] **Step 4: Run validation to verify the file now exists**

Run: `test -f .github/pull_request_template.md`
Expected: exit code `0`

- [ ] **Step 5: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "docs: add codex daily pull request template"
```

### Task 3: Add Automation Docs and State File

**Files:**
- Create: `docs/automation/daily-iteration.md`
- Create: `docs/automation/daily-iteration-state.md`

- [ ] **Step 1: Write the failing validation check**

Expected behavior: the repository should document the daily iteration workflow and carry a state file that the next run can update.

- [ ] **Step 2: Run validation to verify the files are missing**

Run: `test -f docs/automation/daily-iteration.md && test -f docs/automation/daily-iteration-state.md`
Expected: exit code `1`

- [ ] **Step 3: Write the minimal implementation**

Create `docs/automation/daily-iteration.md` with:
- purpose
- required context
- task selection rules
- `code` vs `plan` mode behavior
- verification and failure handling
- reviewer expectations

Create `docs/automation/daily-iteration-state.md` with:
- last run date placeholder
- task title placeholder
- mode placeholder
- PR placeholder
- outcome placeholder

- [ ] **Step 4: Run validation to verify the files now exist**

Run: `test -f docs/automation/daily-iteration.md && test -f docs/automation/daily-iteration-state.md`
Expected: exit code `0`

- [ ] **Step 5: Commit**

```bash
git add docs/automation/daily-iteration.md docs/automation/daily-iteration-state.md
git commit -m "docs: add codex daily automation docs"
```

### Task 4: Verify the Bootstrap End-to-End

**Files:**
- Verify: `AGENTS.md`
- Verify: `.github/pull_request_template.md`
- Verify: `docs/automation/daily-iteration.md`
- Verify: `docs/automation/daily-iteration-state.md`

- [ ] **Step 1: Run formatting-safe validation**

Run: `git diff --check`
Expected: exit code `0`

- [ ] **Step 2: Review the new protocol surface**

Run: `sed -n '1,240p' AGENTS.md && sed -n '1,220p' .github/pull_request_template.md && sed -n '1,260p' docs/automation/daily-iteration.md && sed -n '1,160p' docs/automation/daily-iteration-state.md`
Expected: the files match the approved design and use repository-specific paths and rules.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md .github/pull_request_template.md docs/automation/daily-iteration.md docs/automation/daily-iteration-state.md
git commit -m "docs: bootstrap codex daily iteration workflow"
```
