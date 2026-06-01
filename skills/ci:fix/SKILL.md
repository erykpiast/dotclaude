---
description: Fix failing CI checks by analyzing errors and amending the responsible commit
allowed-tools: Bash(gh:*), Bash(git:*), Bash(pnpm:*), Bash(npm:*), Bash(npx:*), Bash(yarn:*), Read, Edit, MultiEdit, Grep, Glob, Agent
category: workflow
---

# Fix CI

Fix the most recent failing CI run for the current PR by analyzing errors, applying fixes, and amending the commit that caused the failure.

## Current State
!`git log --oneline -5 2>/dev/null`
!`gh pr checks --fail 2>/dev/null | head -20`

## Process

### 1. Identify the Failing CI Run

Fetch the most recent CI run for the current PR:

```
gh pr checks
```

If multiple checks failed, process them in dependency order (e.g., lint before build before test).

### 2. Get the Full Error Logs

For each failing check, fetch the logs:

```
gh run view <run-id> --log-failed
```

If that's too noisy, narrow down to the specific failed job:

```
gh run view <run-id> --log-failed --job <job-id>
```

Extract the actual error messages — strip CI boilerplate, timestamps, and framework noise. Focus on:
- Error messages and stack traces
- File paths and line numbers
- Exit codes and failing commands

### 3. Analyze the Root Cause

For each error:
1. Read the failing file(s) to understand the context
2. Determine the category: type error, lint violation, test failure, build error, dependency issue, etc.
3. Identify the **root cause** — often one error cascades into many

### 4. Find the Responsible Commit

Determine which commit introduced the failure:

```
git log --oneline main..HEAD
```

For each failing file, check which commit last touched it:

```
git log --oneline -1 -- <file-path>
```

If multiple commits contribute to a single failure, attribute it to the **earliest** one (since later commits may depend on it).

Map each fix to its responsible commit. Group fixes by commit.

### 5. Apply Fixes

Fix all identified issues. After fixing, run the same checks locally to verify:
- **Lint errors**: Run the project's lint command
- **Type errors**: Run the project's typecheck command
- **Test failures**: Run the specific failing tests
- **Build errors**: Run the project's build command

### 6. Amend the Responsible Commits

**If all fixes belong to the most recent commit (HEAD):**

Stage the fixes and amend directly:
```
git add <fixed-files>
git commit --amend --no-edit
```

**If fixes belong to different commits, use autosquash:**

For each responsible commit, create a fixup commit:
```
git add <fixed-files-for-this-commit>
git commit --fixup=<commit-sha>
```

Then rebase to squash them in:
```
GIT_SEQUENCE_EDITOR=: git rebase --autosquash <base-commit>~1
```

Where `<base-commit>` is the earliest commit being fixed.

**Important:** `GIT_SEQUENCE_EDITOR=:` makes the rebase non-interactive (`:` is a no-op editor), which is required since Claude Code cannot use interactive editors.

### 7. Force Push

After amending, the branch history has changed and requires a force push:

```
git push --force-with-lease
```

Use `--force-with-lease` (not `--force`) to avoid overwriting someone else's pushes.

### 8. Verify

Check that CI passes on the updated push:

```
gh pr checks --watch
```

If it fails again, go back to step 2 with the new failure.

## Edge Cases

- **Flaky tests**: If a test failure looks unrelated to any commit on this branch (e.g., network timeouts, race conditions), re-run the check instead of fixing: `gh run rerun <run-id> --failed`
- **Base branch drift**: If CI fails due to changes in main that conflict, suggest rebasing first rather than fixing in the feature branch
- **Environment issues**: If the failure is about missing secrets, permissions, or CI config — report to the user rather than attempting a fix
