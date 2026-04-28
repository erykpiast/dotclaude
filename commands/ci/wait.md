---
description: Wait for CI on the current PR to finish (all green, or first failure)
allowed-tools: Bash(gh:*), Bash(git:*), Bash(~/.claude/commands/ci/wait-checks.sh:*)
category: workflow
argument-hint: "[check name substring, e.g. tests | preview deployment]"
---

# Wait for CI

Block until CI on the current PR reaches a terminal state, then report.

**Always launch the waiting command with `run_in_background: true`.** A foreground Bash call would freeze the conversation for the entire CI run; running in the background keeps the session interactive and the runtime will notify you when the process exits. This applies to both modes below — never run the wait in the foreground.

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

Run the polling helper in background (`run_in_background: true`) so the user can keep using the conversation. After kicking off the background task, return control to the user with a short note (e.g. "Waiting for CI in the background — I'll report when it finishes."). Do not poll, sleep, or block; the runtime will notify you when the background task exits, and only then proceed to Step 3.

```
~/.claude/commands/ci/wait-checks.sh "$ARGUMENTS"
```

The script handles both modes uniformly: an empty `$ARGUMENTS` matches every check (every name contains the empty string), so all checks are tracked. Do **not** use `gh pr checks --watch` directly — it exits immediately when no checks have been registered yet, which is the common case right after a push.

The script polls every 30s and prints a tab-separated `BUCKET<TAB>NAME<TAB>LINK` line per tracked check on exit. Its exit codes:
- `0` — all tracked checks completed without failure.
- `1` — at least one tracked check failed or was cancelled.
- `2` — no checks reported on the PR after one grace poll, no checks matched the query, or `gh pr checks` failed.
- `3` — timed out after 60 minutes; partial state is printed.

## Step 3 — Report

Keep the report tight:

- ✅ Green: list each completed check with its bucket and link.
- ❌ Failed: list the failing check(s) with link(s) and suggest `/ci:fix`.
- ⚠️ No match (Case B only): show the list of available check names so the user can retry.

Do not summarize what was just done beyond that.
