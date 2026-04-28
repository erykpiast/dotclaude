---
description: Wait for CI on the current PR to finish (all green, or first failure)
allowed-tools: Bash(gh:*), Bash(git:*), Bash(~/.claude/commands/ci/wait-checks.sh:*)
category: workflow
argument-hint: "[check name substring, e.g. tests | preview deployment]"
---

# Wait for CI

Block until CI on the current PR reaches a terminal state, then report.

Modes:
- **No argument** — wait for the entire CI suite. Returns on either all-green or the first check failure.
- **With argument** (`$ARGUMENTS`) — wait only for checks whose names contain the argument (case-insensitive substring). Returns when every matching check is done (pass or fail).

The argument is interpolated into a shell command, so it must not contain shell metacharacters (quotes, `$`, backticks, `\`). Plain words and spaces are fine: `tests`, `preview deployment`, `e2e`.

## Step 1 — Confirm there is a PR

Run:

```
gh pr view --json number,headRefName,url 2>/dev/null
```

If this errors or returns nothing, report `No PR for the current branch.` and stop.

## Step 2 — Wait

CI runs can take >10 minutes, so always launch the wait command with `run_in_background: true` and let the runtime notify you when it exits. Then read the output and proceed.

### Case A — `$ARGUMENTS` is empty

Run in background:

```
gh pr checks --watch --fail-fast --interval 30
```

Exit codes from `gh pr checks`:
- `0` — all checks passed.
- `1` — at least one check failed (or `--fail-fast` short-circuited).
- `8` — still pending (shouldn't happen with `--watch`, but treat as inconclusive).

When the background task completes, read its output. Then run `gh pr checks` once more (without `--watch`) to grab the final summary table for the report.

### Case B — `$ARGUMENTS` is non-empty

Run the polling helper in background:

```
~/.claude/commands/ci/wait-checks.sh "$ARGUMENTS"
```

The script polls every 30s and prints a tab-separated `BUCKET<TAB>NAME<TAB>LINK` line per matching check on exit. Its exit codes:
- `0` — all matching checks completed without failure.
- `1` — at least one matching check failed or was cancelled.
- `2` — no checks reported on the PR after one grace poll, no checks matched the query, or `gh pr checks` failed.
- `3` — timed out after 60 minutes; partial state is printed.

## Step 3 — Report

Keep the report tight:

- ✅ Green: list each completed check with its bucket and link.
- ❌ Failed: list the failing check(s) with link(s) and suggest `/ci:fix`.
- ⚠️ No match (Case B only): show the list of available check names so the user can retry.

Do not summarize what was just done beyond that.
